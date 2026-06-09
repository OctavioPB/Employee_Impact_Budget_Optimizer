"""Organizational Health Index — Sprint 18.

Computes a composite OHI (0–100) across six sub-dimensions:
  Financial Health (20%), Talent Risk (20%), Knowledge Resilience (20%),
  Leadership Pipeline (15%), Compensation Equity (15%), Collaboration Density (10%).

Produces:
  - 24-month synthetic time series with event annotations + 6-month forecast
  - Department-level OHI breakdown
  - Decision impact preview: OHI delta across budget retention scenarios
  - Synthetic industry benchmark P25/P50/P75 bands per sub-index
"""

import sys
from datetime import date, timedelta
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import numpy as np
import pandas as pd

from backend.services.data_service import get_org

# ── Weights ───────────────────────────────────────────────────────────────────

_WEIGHTS: dict[str, float] = {
    "financial_health":      0.20,
    "talent_risk":           0.20,
    "knowledge_resilience":  0.20,
    "leadership_pipeline":   0.15,
    "compensation_equity":   0.15,
    "collaboration_density": 0.10,
}
assert abs(sum(_WEIGHTS.values()) - 1.0) < 1e-9

_LABELS: dict[str, str] = {
    "financial_health":      "Financial Health",
    "talent_risk":           "Talent Risk",
    "knowledge_resilience":  "Knowledge Resilience",
    "leadership_pipeline":   "Leadership Pipeline",
    "compensation_equity":   "Compensation Equity",
    "collaboration_density": "Collaboration Density",
}

_LEADER_LEVELS = {"lead", "director", "exec"}
_SEN_RANK      = {"junior": 1, "mid": 2, "senior": 3, "lead": 4, "director": 5, "exec": 6}


# ── Shared helpers ────────────────────────────────────────────────────────────

def _add_scores(df: pd.DataFrame) -> pd.DataFrame:
    rng      = np.random.default_rng(42)
    sal_rank = df["annual_salary"].rank(pct=True)
    nexus_b  = df["_is_nexus"].astype(float) * 15
    noise    = rng.normal(0, 5, len(df))
    df       = df.copy()
    df["impact_score"] = np.clip(sal_rank * 70 + nexus_b + noise, 0, 100).round(1)
    sal_inv  = 1 - sal_rank
    nexus_r  = df["_is_nexus"].astype(float) * 0.15
    attr_raw = sal_inv * 0.6 + rng.uniform(0, 0.4, len(df)) - nexus_r
    df["attrition_risk"] = np.clip(attr_raw, 0.01, 0.99).round(3)
    return df


def _gini(values: np.ndarray) -> float:
    arr = np.sort(np.abs(values.astype(float)))
    n   = len(arr)
    if n == 0 or arr.sum() == 0:
        return 0.0
    idx = np.arange(1, n + 1)
    return float(2 * (idx * arr).sum() / (n * arr.sum()) - (n + 1) / n)


def _grade(score: float) -> str:
    return "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 55 else "D" if score >= 40 else "F"


def _clamp(v: float) -> float:
    return float(np.clip(v, 0.0, 100.0))


# ── Sub-index computations ────────────────────────────────────────────────────

def _financial_health(df: pd.DataFrame) -> dict:
    total_cost   = float(df["annual_salary"].sum() + df["annual_benefits"].sum())
    total_impact = float(df["impact_score"].sum()) or 1.0
    cost_per_impact = total_cost / total_impact

    # Lower cost-per-impact is better; normalise around a mid-market reference
    ref_low, ref_high = 8_000, 25_000
    cost_efficiency = _clamp((ref_high - cost_per_impact) / (ref_high - ref_low) * 100)

    # Salary predictability: inverse Gini of salaries within each role-seniority cohort
    gini_vals: list[float] = []
    for _, grp in df.groupby(["department", "seniority_level"]):
        if len(grp) >= 2:
            gini_vals.append(_gini(grp["annual_salary"].values))
    avg_gini = float(np.mean(gini_vals)) if gini_vals else 0.2
    budget_predictability = _clamp((1 - avg_gini) * 100)

    # Benefits coverage ratio (benefits / salary; healthy ~18-25%)
    benefits_ratio = df["annual_benefits"].sum() / max(df["annual_salary"].sum(), 1)
    benefits_score = _clamp(100 - abs(benefits_ratio - 0.215) * 400)

    overall = _clamp(cost_efficiency * 0.45 + budget_predictability * 0.35 + benefits_score * 0.20)
    return {
        "score": round(overall, 1),
        "components": {
            "cost_efficiency":      round(cost_efficiency, 1),
            "budget_predictability": round(budget_predictability, 1),
            "benefits_coverage":    round(benefits_score, 1),
        },
        "labels": {
            "cost_efficiency":      "Cost per Impact Unit",
            "budget_predictability": "Intra-Cohort Salary Consistency",
            "benefits_coverage":    "Benefits Coverage Ratio",
        },
        "detail": f"${cost_per_impact:,.0f} per impact point · {benefits_ratio*100:.1f}% benefits/salary ratio",
    }


def _talent_risk(df: pd.DataFrame) -> dict:
    avg_risk = float(df["attrition_risk"].mean())
    risk_score = _clamp((1 - avg_risk) * 100)

    # Concentration: high-impact employees at high risk (positive correlation = bad)
    corr = df["impact_score"].corr(df["attrition_risk"])
    concentration_score = _clamp((1 - max(0.0, float(corr))) * 100)

    # High-risk headcount ratio (attrition_risk ≥ 0.6)
    high_risk_ratio = float((df["attrition_risk"] >= 0.6).mean())
    ratio_score = _clamp((1 - high_risk_ratio) * 100)

    # Nexus employees at risk
    nexus_at_risk = float(
        df[df["_is_nexus"]]["attrition_risk"].mean()
    ) if df["_is_nexus"].any() else 0.0
    nexus_score = _clamp((1 - nexus_at_risk) * 100)

    overall = _clamp(
        risk_score * 0.35 + concentration_score * 0.30 +
        ratio_score * 0.20 + nexus_score * 0.15
    )
    return {
        "score": round(overall, 1),
        "components": {
            "avg_attrition_risk":    round(risk_score, 1),
            "risk_concentration":    round(concentration_score, 1),
            "high_risk_headcount":   round(ratio_score, 1),
            "nexus_protection":      round(nexus_score, 1),
        },
        "labels": {
            "avg_attrition_risk":    "Average Retention Stability",
            "risk_concentration":    "Risk/Impact Concentration",
            "high_risk_headcount":   "Low-Risk Headcount Ratio",
            "nexus_protection":      "Nexus Employee Stability",
        },
        "detail": f"{avg_risk*100:.1f}% avg departure prob · {high_risk_ratio*100:.0f}% high-risk headcount",
    }


def _knowledge_resilience(df: pd.DataFrame) -> dict:
    # Skill coverage: fraction of role types with ≥2 holders
    role_counts = df["role_title"].value_counts()
    covered     = int((role_counts >= 2).sum())
    total_roles = max(len(role_counts), 1)
    skill_coverage = _clamp(covered / total_roles * 100)

    # Knowledge redundancy: fraction of depts with ≥2 senior+ employees
    senior_levels = {"senior", "lead", "director", "exec"}
    dept_senior = df[df["seniority_level"].isin(senior_levels)].groupby("department").size()
    covered_depts = int((dept_senior >= 2).sum())
    total_depts   = len(df["department"].unique())
    knowledge_redundancy = _clamp(covered_depts / max(total_depts, 1) * 100)

    # SKH risk (Single Knowledge Holders): employees sole-holder of their role in dept
    df2 = df.copy()
    df2["_dept_role_key"] = df2["department"] + "_" + df2["role_title"]
    key_counts = df2["_dept_role_key"].value_counts()
    skh_count  = int((key_counts == 1).sum())
    skh_score  = _clamp(max(0, 100 - skh_count * 8))

    overall = _clamp(skill_coverage * 0.40 + knowledge_redundancy * 0.35 + skh_score * 0.25)
    return {
        "score": round(overall, 1),
        "components": {
            "skill_coverage":       round(skill_coverage, 1),
            "knowledge_redundancy": round(knowledge_redundancy, 1),
            "skh_risk":             round(skh_score, 1),
        },
        "labels": {
            "skill_coverage":       "Role Coverage (≥2 holders)",
            "knowledge_redundancy": "Senior Depth Per Department",
            "skh_risk":             "Single-Knowledge-Holder Risk",
        },
        "detail": f"{covered}/{total_roles} roles with ≥2 holders · {skh_count} single knowledge holders",
    }


def _leadership_pipeline(df: pd.DataFrame) -> dict:
    leaders = df[df["seniority_level"].isin(_LEADER_LEVELS)]
    if len(leaders) == 0:
        return {
            "score": 50.0,
            "components": {"succession_depth": 50.0, "leader_ratio": 50.0, "cross_dept_coverage": 50.0},
            "labels": {"succession_depth": "Succession Depth", "leader_ratio": "Leader-to-Employee Ratio", "cross_dept_coverage": "Cross-Dept Coverage"},
            "detail": "No leadership roles identified",
        }

    # Succession depth: for each leader, count potential next-level successors in same dept
    depths: list[int] = []
    for _, ldr in leaders.iterrows():
        ldr_rank  = _SEN_RANK.get(str(ldr["seniority_level"]), 4)
        successors = df[
            (df["department"] == ldr["department"]) &
            (df["seniority_level"].map(lambda s: _SEN_RANK.get(str(s), 1)) == ldr_rank - 1)
        ]
        depths.append(min(len(successors), 3))  # cap at 3 for scoring

    avg_depth   = float(np.mean(depths)) if depths else 0.0
    depth_score = _clamp(avg_depth / 3 * 100)

    # Leader ratio: leaders / total employees (healthy ≈ 10-20%)
    leader_ratio = len(leaders) / max(len(df), 1)
    ratio_score  = _clamp(100 - abs(leader_ratio - 0.15) * 400)

    # Cross-department coverage: fraction of depts with ≥1 leader
    depts_with_leader = df[df["seniority_level"].isin(_LEADER_LEVELS)]["department"].nunique()
    total_depts       = df["department"].nunique()
    cross_score       = _clamp(depts_with_leader / max(total_depts, 1) * 100)

    overall = _clamp(depth_score * 0.50 + ratio_score * 0.25 + cross_score * 0.25)
    return {
        "score": round(overall, 1),
        "components": {
            "succession_depth":   round(depth_score, 1),
            "leader_ratio":       round(ratio_score, 1),
            "cross_dept_coverage": round(cross_score, 1),
        },
        "labels": {
            "succession_depth":    "Succession Readiness",
            "leader_ratio":        "Leadership Density",
            "cross_dept_coverage": "Cross-Department Coverage",
        },
        "detail": f"{len(leaders)} leaders · avg {avg_depth:.1f} successors per role · {depts_with_leader}/{total_depts} depts covered",
    }


def _compensation_equity(df: pd.DataFrame) -> dict:
    # Intra-cohort pay equity: Gini within (dept, seniority) groups
    gini_vals: list[float] = []
    for _, grp in df.groupby(["department", "seniority_level"]):
        if len(grp) >= 2:
            gini_vals.append(_gini(grp["annual_salary"].values))
    avg_gini    = float(np.mean(gini_vals)) if gini_vals else 0.3
    equity_score = _clamp((1 - avg_gini * 1.5) * 100)

    # Market positioning: fraction of employees within 85-115% of dept-seniority median
    in_band_pct: list[float] = []
    for _, grp in df.groupby(["department", "seniority_level"]):
        if len(grp) == 0:
            continue
        med = grp["annual_salary"].median()
        in_band = ((grp["annual_salary"] >= med * 0.85) & (grp["annual_salary"] <= med * 1.15)).mean()
        in_band_pct.append(float(in_band))
    market_score = _clamp(float(np.mean(in_band_pct)) * 100) if in_band_pct else 70.0

    # Pay-for-performance: correlation between salary percentile and impact score (positive = good)
    sal_rank = df["annual_salary"].rank(pct=True)
    corr_pfp = float(sal_rank.corr(df["impact_score"]))
    pfp_score = _clamp(max(0.0, corr_pfp) * 100)

    overall = _clamp(equity_score * 0.40 + market_score * 0.35 + pfp_score * 0.25)
    return {
        "score": round(overall, 1),
        "components": {
            "intra_cohort_equity": round(equity_score, 1),
            "market_positioning":  round(market_score, 1),
            "pay_for_performance": round(pfp_score, 1),
        },
        "labels": {
            "intra_cohort_equity": "Intra-Cohort Pay Equity",
            "market_positioning":  "Market Band Positioning",
            "pay_for_performance": "Pay-for-Performance Alignment",
        },
        "detail": f"Avg cohort Gini {avg_gini:.2f} · {float(np.mean(in_band_pct))*100:.0f}% at-market · PfP r={corr_pfp:.2f}",
    }


def _collaboration_density(df: pd.DataFrame) -> dict:
    # Nexus density: a healthy share is 5-15% of workforce
    nexus_ratio = float(df["_is_nexus"].mean())
    if nexus_ratio == 0:
        nexus_score = 40.0  # no nexus employees = fragile
    else:
        nexus_score = _clamp(100 - abs(nexus_ratio - 0.10) * 500)

    # Team size distribution: lower CV of team sizes = healthier
    if "team_id" in df.columns:
        team_sizes = df.groupby("team_id").size()
        if len(team_sizes) >= 2:
            cv = float(team_sizes.std() / max(team_sizes.mean(), 1))
            team_score = _clamp((1 - min(cv, 1.0)) * 100)
        else:
            team_score = 70.0
    else:
        team_score = 70.0

    # Cross-functional coverage: unique depts / total employees ratio (low is siloed)
    dept_count  = df["department"].nunique()
    dept_score  = _clamp(min(dept_count / 5, 1.0) * 100)

    # High-impact connectivity: nexus employees span multiple departments
    nexus_df = df[df["_is_nexus"]]
    if len(nexus_df) > 0:
        nexus_dept_span = nexus_df["department"].nunique() / max(dept_count, 1)
        span_score      = _clamp(nexus_dept_span * 100)
    else:
        span_score = 40.0

    overall = _clamp(nexus_score * 0.30 + team_score * 0.30 + dept_score * 0.20 + span_score * 0.20)
    return {
        "score": round(overall, 1),
        "components": {
            "nexus_density":    round(nexus_score, 1),
            "team_balance":     round(team_score, 1),
            "dept_coverage":    round(dept_score, 1),
            "cross_functional": round(span_score, 1),
        },
        "labels": {
            "nexus_density":    "Network Connector Density",
            "team_balance":     "Team Size Balance",
            "dept_coverage":    "Departmental Diversity",
            "cross_functional": "Nexus Cross-Dept Span",
        },
        "detail": f"{nexus_ratio*100:.1f}% nexus employees · {dept_count} departments · {len(nexus_df)} network connectors",
    }


# ── OHI composite ─────────────────────────────────────────────────────────────

def _compute_ohi(df: pd.DataFrame) -> dict:
    sub = {
        "financial_health":      _financial_health(df),
        "talent_risk":           _talent_risk(df),
        "knowledge_resilience":  _knowledge_resilience(df),
        "leadership_pipeline":   _leadership_pipeline(df),
        "compensation_equity":   _compensation_equity(df),
        "collaboration_density": _collaboration_density(df),
    }
    overall = sum(_WEIGHTS[k] * sub[k]["score"] for k in _WEIGHTS)
    for key in sub:
        sub[key]["weight"]  = _WEIGHTS[key]
        sub[key]["label"]   = _LABELS[key]
        sub[key]["grade"]   = _grade(sub[key]["score"])
    return {"overall": round(overall, 1), "grade": _grade(overall), "sub_indices": sub}


# ── 24-month time series ──────────────────────────────────────────────────────

_EVENTS = [
    (21, "Market expansion"),
    (15, "Leadership transition"),
    (9,  "Reorg Q3"),
    (4,  "Compensation review"),
    (2,  "L&D cohort"),
]


def _ohi_time_series(current_ohi: float, rng: np.random.Generator) -> list[dict]:
    """Generate 24 months of synthetic OHI history + 6 months forecast."""
    event_map = {e[0]: e[1] for e in _EVENTS}
    today   = date.today().replace(day=1)

    # Build 24-month history via biased random walk
    n_hist  = 24
    scores  = [0.0] * (n_hist + 1)
    # Start slightly below current, drift up
    scores[0] = _clamp(current_ohi - rng.uniform(8, 18))
    for i in range(1, n_hist + 1):
        drift = rng.normal(0.4, 1.8)                        # slight upward bias
        event_boost = 2.0 if event_map.get(n_hist + 1 - i) else 0.0
        scores[i] = _clamp(scores[i - 1] + drift + event_boost)
    scores[n_hist] = current_ohi  # pin the last point to actual

    # 6-month forecast: extrapolate slope with widening uncertainty
    recent_slope = (scores[n_hist] - scores[n_hist - 3]) / 3
    forecast_scores: list[float] = []
    for k in range(1, 7):
        base = current_ohi + recent_slope * k
        noise = rng.normal(0, k * 0.5)
        forecast_scores.append(_clamp(base + noise))

    records: list[dict] = []
    for i in range(n_hist):
        month_date = today - timedelta(days=30 * (n_hist - i))
        records.append({
            "month":       month_date.strftime("%b %Y"),
            "score":       round(scores[i], 1),
            "is_forecast": False,
            "event":       event_map.get(n_hist - i),
        })
    # Current month (actual)
    records.append({
        "month":       today.strftime("%b %Y"),
        "score":       round(current_ohi, 1),
        "is_forecast": False,
        "event":       None,
    })
    # 6-month forecast
    for k, fscore in enumerate(forecast_scores):
        month_date = today + timedelta(days=30 * (k + 1))
        records.append({
            "month":       month_date.strftime("%b %Y"),
            "score":       round(fscore, 1),
            "is_forecast": True,
            "event":       None,
        })

    return records


# ── Department OHI ────────────────────────────────────────────────────────────

def _dept_ohi(df: pd.DataFrame) -> list[dict]:
    rows: list[dict] = []
    for dept, grp in df.groupby("department"):
        if len(grp) < 2:
            continue
        sub_ohi = _compute_ohi(grp.reset_index(drop=True))
        rows.append({
            "department":  str(dept),
            "score":       sub_ohi["overall"],
            "grade":       sub_ohi["grade"],
            "headcount":   len(grp),
            "nexus_count": int(grp["_is_nexus"].sum()),
            "avg_impact":  round(float(grp["impact_score"].mean()), 1),
            "avg_attrition": round(float(grp["attrition_risk"].mean()), 3),
            "sub_scores":  {k: v["score"] for k, v in sub_ohi["sub_indices"].items()},
        })
    rows.sort(key=lambda r: r["score"])
    return rows


# ── Decision impact preview ───────────────────────────────────────────────────

def _decision_preview(df: pd.DataFrame, base_ohi: float) -> list[dict]:
    """OHI at each budget retention level (50% → 100% of headcount)."""
    n = len(df)
    df_sorted = df.sort_values("impact_score", ascending=False).reset_index(drop=True)
    points: list[dict] = []
    for pct_int in range(50, 105, 10):
        pct   = pct_int / 100
        n_ret = max(2, int(n * pct))
        sub_df = df_sorted.iloc[:n_ret].reset_index(drop=True)
        try:
            sub_ohi = _compute_ohi(sub_df)["overall"]
        except Exception:
            sub_ohi = base_ohi
        savings_pct = round((1 - pct) * 100, 0)
        points.append({
            "retention_pct": pct_int,
            "budget_savings_pct": savings_pct,
            "ohi":           round(sub_ohi, 1),
            "ohi_delta":     round(sub_ohi - base_ohi, 1),
            "n_retained":    n_ret,
        })
    return points


# ── Synthetic benchmarks ──────────────────────────────────────────────────────

_BENCHMARK_PARAMS: dict[str, dict[str, tuple[float, float]]] = {
    # org_size → sub_index → (p50_mean, std)
    "small": {
        "financial_health":      (58, 12),
        "talent_risk":           (54, 14),
        "knowledge_resilience":  (52, 13),
        "leadership_pipeline":   (55, 11),
        "compensation_equity":   (61, 10),
        "collaboration_density": (57, 13),
    },
    "medium": {
        "financial_health":      (65, 10),
        "talent_risk":           (62, 11),
        "knowledge_resilience":  (67, 10),
        "leadership_pipeline":   (66, 9),
        "compensation_equity":   (68, 9),
        "collaboration_density": (64, 11),
    },
    "large": {
        "financial_health":      (71, 8),
        "talent_risk":           (68, 9),
        "knowledge_resilience":  (73, 8),
        "leadership_pipeline":   (72, 7),
        "compensation_equity":   (74, 8),
        "collaboration_density": (70, 9),
    },
}


def _benchmarks(size: str) -> dict:
    params  = _BENCHMARK_PARAMS.get(size, _BENCHMARK_PARAMS["small"])
    comparators = {"small": 142, "medium": 89, "large": 47}.get(size, 100)
    bands: dict[str, dict] = {}
    for key, (p50, std) in params.items():
        bands[key] = {
            "p25": round(max(0, p50 - std), 1),
            "p50": round(p50, 1),
            "p75": round(min(100, p50 + std), 1),
            "label": _LABELS[key],
        }
    return {
        "org_size":    size,
        "comparators": comparators,
        "source":      "Synthetic comparators — not real industry data",
        "sub_indices": bands,
    }


# ── Alert ─────────────────────────────────────────────────────────────────────

def _check_alert(trend: list[dict]) -> dict | None:
    """Return alert dict if OHI dropped >5 pts in the last 90 days (≈3 months)."""
    actual = [t for t in trend if not t["is_forecast"]]
    if len(actual) < 4:
        return None
    recent_delta = actual[-1]["score"] - actual[-4]["score"]
    if recent_delta <= -5:
        return {
            "type":    "ohi_drop",
            "message": f"OHI dropped {abs(recent_delta):.1f} points in the last 90 days",
            "severity": "critical" if recent_delta <= -10 else "high",
        }
    return None


# ── Main entry point ──────────────────────────────────────────────────────────

def build_ohi_data(scenario: str, size: str) -> dict:
    org = get_org(scenario, size)
    df  = _add_scores(org.employees.copy().reset_index(drop=True))
    rng = np.random.default_rng(18)

    ohi_result = _compute_ohi(df)
    current    = ohi_result["overall"]

    trend      = _ohi_time_series(current, rng)
    alert      = _check_alert(trend)
    dept_rows  = _dept_ohi(df)
    preview    = _decision_preview(df, current)
    benchmark  = _benchmarks(size)

    # 90-day trend delta
    actual      = [t for t in trend if not t["is_forecast"]]
    delta_90d   = round(actual[-1]["score"] - actual[-4]["score"], 1) if len(actual) >= 4 else 0.0
    trend_dir   = "improving" if delta_90d > 1 else "declining" if delta_90d < -1 else "stable"

    summary = {
        "overall":         current,
        "grade":           ohi_result["grade"],
        "trend_direction": trend_dir,
        "trend_delta_90d": delta_90d,
        "n_employees":     len(df),
        "nexus_count":     int(df["_is_nexus"].sum()),
        "alert":           alert is not None,
    }

    return {
        "summary":           summary,
        "sub_indices":       ohi_result["sub_indices"],
        "dept_ohi":          dept_rows,
        "trend":             trend,
        "benchmark":         benchmark,
        "decision_preview":  preview,
        "alert":             alert,
    }
