"""Workforce Resilience Stress Testing — Sprint 15.

Implements:
  - Six-dimension Resilience Score (skill coverage, leadership depth,
    knowledge redundancy, network robustness, attrition concentration,
    team size buffer) with configurable weights
  - Five disruption scenario types: targeted departure, department shock,
    competitive poaching, leadership vacuum, skill crisis
  - Three-round cascade simulation driven by nexus/leadership pressure
  - Cascade amplifier identification (which primary departure triggers most secondary)
  - Intervention roadmap ranked by score_improvement / cost ROI
  - Department-level resilience breakdown
  - Synthetic 12-month resilience trend
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import numpy as np
import pandas as pd

from backend.services.data_service import get_org

# ── Seniority ranking ─────────────────────────────────────────────────────────
_SEN_RANK: dict[str, int] = {
    "junior": 1, "mid": 2, "senior": 3, "lead": 4, "director": 5, "exec": 6,
}
_LEADER_LEVELS = {"lead", "director", "exec"}

# ── Weights for the six sub-dimensions ───────────────────────────────────────
_WEIGHTS: dict[str, float] = {
    "skill_coverage":         0.20,
    "leadership_depth":       0.15,
    "knowledge_redundancy":   0.20,
    "network_robustness":     0.15,
    "attrition_concentration":0.15,
    "team_size_buffer":       0.15,
}
assert abs(sum(_WEIGHTS.values()) - 1.0) < 1e-9, "Weights must sum to 1.0"

_SCENARIO_LABELS: dict[str, str] = {
    "targeted_departure":  "Targeted Departure",
    "department_shock":    "Department Shock",
    "competitive_poaching":"Competitive Poaching",
    "leadership_vacuum":   "Leadership Vacuum",
    "skill_crisis":        "Skill Crisis",
}

_MIN_VIABLE_TEAM = 3       # minimum employees per team
_CASCADE_THRESHOLD = 0.75  # attrition_risk + pressure must exceed this to cascade


# ── Score helpers ─────────────────────────────────────────────────────────────

def _add_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Replicate impact_score + attrition_risk from data_service (same seed)."""
    rng        = np.random.default_rng(42)
    sal_rank   = df["annual_salary"].rank(pct=True)
    nexus_b    = df["_is_nexus"].astype(float) * 15
    noise      = rng.normal(0, 5, len(df))
    df         = df.copy()
    df["impact_score"] = np.clip(sal_rank * 70 + nexus_b + noise, 0, 100).round(1)

    sal_inv    = 1 - sal_rank
    nexus_r    = df["_is_nexus"].astype(float) * 0.15
    attr_raw   = sal_inv * 0.6 + rng.uniform(0, 0.4, len(df)) - nexus_r
    df["attrition_risk"] = np.clip(attr_raw, 0.01, 0.99).round(3)
    return df


def _gini(values: np.ndarray) -> float:
    """Gini coefficient of an array; 0 = perfect equality, 1 = maximum inequality."""
    if len(values) == 0:
        return 0.0
    arr = np.sort(np.abs(values.astype(float)))
    n   = len(arr)
    idx = np.arange(1, n + 1)
    return float((2 * (idx * arr).sum() / (n * arr.sum()) - (n + 1) / n)) if arr.sum() > 0 else 0.0


# ── Resilience sub-scores ─────────────────────────────────────────────────────

def _compute_resilience_score(df: pd.DataFrame) -> dict:
    """Return dict with overall, sub_scores, weights, grade."""

    # ── 1. Skill coverage ─────────────────────────────────────────────────────
    # Use role_title as skill proxy: coverage = % of role types with ≥2 holders
    skill_counts  = df["role_title"].value_counts()
    covered       = int((skill_counts >= 2).sum())
    total_skills  = max(len(skill_counts), 1)
    skill_coverage = min(100.0, covered / total_skills * 100)

    # ── 2. Leadership depth ───────────────────────────────────────────────────
    leaders = df[df["seniority_level"].isin(_LEADER_LEVELS)]
    if len(leaders) == 0:
        leadership_depth = 50.0
    else:
        depth2 = 0
        for _, ldr in leaders.iterrows():
            ldr_rank = _SEN_RANK.get(str(ldr["seniority_level"]), 4)
            successors = df[
                (df["department"] == ldr["department"]) &
                (df["seniority_level"].map(lambda s: _SEN_RANK.get(str(s), 1)) == ldr_rank - 1)
            ]
            if len(successors) >= 2:
                depth2 += 1
        leadership_depth = min(100.0, depth2 / len(leaders) * 100)

    # ── 3. Knowledge redundancy ───────────────────────────────────────────────
    # Per dept: fraction of role_titles with ≥2 holders
    dept_scores: list[float] = []
    for _, ddf in df.groupby("department"):
        dc = ddf["role_title"].value_counts()
        dept_scores.append((dc >= 2).sum() / max(len(dc), 1))
    knowledge_redundancy = min(100.0, float(np.mean(dept_scores)) * 100) if dept_scores else 50.0

    # ── 4. Network robustness ─────────────────────────────────────────────────
    nexus_df = df[df["_is_nexus"]]
    if len(nexus_df) == 0:
        network_robustness = 90.0
    else:
        depts_with_nexus = nexus_df["department"].nunique()
        total_depts      = df["department"].nunique()
        nexus_per_dept   = nexus_df.groupby("department").size().values.astype(float)
        gini_n           = _gini(nexus_per_dept)
        coverage         = depts_with_nexus / max(total_depts, 1)
        network_robustness = min(100.0, max(10.0, coverage * (1.0 - gini_n) * 100 + 15.0))

    # ── 5. Attrition concentration (inverse Gini) ─────────────────────────────
    gini_attr = _gini(df["attrition_risk"].values)
    attrition_concentration = min(100.0, max(0.0, (1.0 - gini_attr) * 100))

    # ── 6. Team size buffer ───────────────────────────────────────────────────
    team_sizes    = df.groupby("team_id").size()
    buf_threshold = _MIN_VIABLE_TEAM * 1.20
    teams_with_buf = int((team_sizes > buf_threshold).sum())
    team_size_buffer = min(100.0, teams_with_buf / max(len(team_sizes), 1) * 100)

    sub_scores = {
        "skill_coverage":          round(skill_coverage, 1),
        "leadership_depth":        round(leadership_depth, 1),
        "knowledge_redundancy":    round(knowledge_redundancy, 1),
        "network_robustness":      round(network_robustness, 1),
        "attrition_concentration": round(attrition_concentration, 1),
        "team_size_buffer":        round(team_size_buffer, 1),
    }
    overall = sum(sub_scores[k] * _WEIGHTS[k] for k in _WEIGHTS)
    grade   = "A" if overall >= 80 else "B" if overall >= 65 else "C" if overall >= 50 else "D" if overall >= 35 else "F"

    return {
        "overall":    round(overall, 1),
        "sub_scores": sub_scores,
        "weights":    _WEIGHTS,
        "grade":      grade,
    }


def _dept_resilience(df: pd.DataFrame) -> list[dict]:
    rows: list[dict] = []
    for dept, ddf in df.groupby("department"):
        rs = _compute_resilience_score(ddf)
        rows.append({
            "department":  str(dept),
            "overall":     rs["overall"],
            "headcount":   len(ddf),
            "nexus_count": int(ddf["_is_nexus"].sum()),
            "at_risk_count": int((ddf["attrition_risk"] > 0.6).sum()),
            "sub_scores":  rs["sub_scores"],
            "grade":       rs["grade"],
        })
    rows.sort(key=lambda r: r["overall"])
    return rows


# ── Cascade simulation ────────────────────────────────────────────────────────

def _cascade_simulation(
    df: pd.DataFrame,
    primary_ids: set,
    max_rounds: int = 3,
) -> list[dict]:
    """Simulate cascade departures up to max_rounds."""
    remaining     = df[~df["employee_id"].isin(primary_ids)].copy()
    prev_wave_ids = set(primary_ids)
    all_rounds: list[dict] = []

    for round_num in range(1, max_rounds + 1):
        if remaining.empty or not prev_wave_ids:
            break

        prev_wave = df[df["employee_id"].isin(prev_wave_ids)]
        pressure  = pd.Series(0.0, index=remaining.index)

        for _, dep in prev_wave.iterrows():
            dep_dept    = dep["department"]
            dep_is_nexus = bool(dep["_is_nexus"])
            dep_rank    = _SEN_RANK.get(str(dep.get("seniority_level", "mid")), 2)
            same_dept   = remaining["department"] == dep_dept

            if dep_is_nexus:
                pressure[same_dept] += 0.28
            if dep_rank >= 4:                       # lead / director / exec
                direct_reports = same_dept & (
                    remaining["seniority_level"].map(
                        lambda s: _SEN_RANK.get(str(s), 1)
                    ) < dep_rank
                )
                pressure[direct_reports] += 0.22
            impact_contrib = float(dep.get("impact_score", 50)) / 100.0 * 0.05
            pressure[same_dept] += impact_contrib

        departed_mask = (remaining["attrition_risk"] + pressure) > _CASCADE_THRESHOLD
        triggered     = remaining[departed_mask]
        if triggered.empty:
            break

        round_emps: list[dict] = []
        for _, emp in triggered.iterrows():
            p      = float(pressure.loc[emp.name])
            if p >= 0.28:
                reason = "nexus departure pressure"
            elif p >= 0.22:
                reason = "leadership vacuum effect"
            else:
                reason = "general cascade"
            round_emps.append({
                "employee_id":    str(emp["employee_id"]),
                "full_name":      str(emp["full_name"]),
                "department":     str(emp["department"]),
                "role_title":     str(emp.get("role_title", "")),
                "impact_score":   float(emp["impact_score"]),
                "attrition_risk": float(emp["attrition_risk"]),
                "is_nexus":       bool(emp["_is_nexus"]),
                "departure_round": round_num,
                "trigger_reason": reason,
            })

        all_rounds.append({"round": round_num, "count": len(round_emps), "employees": round_emps})
        prev_wave_ids = {e["employee_id"] for e in round_emps}
        remaining = remaining[~remaining["employee_id"].isin(prev_wave_ids)]

    return all_rounds


def _compute_amplifiers(df: pd.DataFrame, primary_df: pd.DataFrame) -> list[dict]:
    """For each primary employee, count secondary departures they'd trigger solo."""
    results: list[dict] = []
    for _, emp in primary_df.head(8).iterrows():
        solo_rounds = _cascade_simulation(df, {emp["employee_id"]})
        secondary   = sum(r["count"] for r in solo_rounds)
        results.append({
            "employee_id":         str(emp["employee_id"]),
            "full_name":           str(emp["full_name"]),
            "department":          str(emp["department"]),
            "is_nexus":            bool(emp["_is_nexus"]),
            "impact_score":        float(emp["impact_score"]),
            "secondary_triggered": secondary,
        })
    results.sort(key=lambda a: -a["secondary_triggered"])
    return results[:5]


# ── Disruption scenario runner ────────────────────────────────────────────────

def run_disruption_scenario(
    df: pd.DataFrame,
    scenario_type: str,
    params: dict,
) -> dict:
    """Run a named disruption scenario and return full result including cascade."""
    if scenario_type not in _SCENARIO_LABELS:
        raise ValueError(f"Unknown scenario_type: {scenario_type!r}")

    # ── Select primary departed ───────────────────────────────────────────────
    if scenario_type == "targeted_departure":
        n          = max(1, int(params.get("n", 5)))
        primary_df = df.nlargest(n, "impact_score")

    elif scenario_type == "department_shock":
        dept      = str(params.get("department", df["department"].iloc[0]))
        pct       = float(params.get("pct", 0.30))
        dept_df   = df[df["department"] == dept]
        n         = max(1, int(len(dept_df) * pct))
        primary_df = dept_df.sample(n=min(n, len(dept_df)), random_state=42)

    elif scenario_type == "competitive_poaching":
        thresh     = float(params.get("impact_threshold", 65.0))
        n          = int(params.get("n", 8))
        primary_df = df[df["impact_score"] >= thresh].nlargest(n, "impact_score")
        if primary_df.empty:
            primary_df = df.nlargest(max(1, n), "impact_score")

    elif scenario_type == "leadership_vacuum":
        scope_dept = params.get("department", None)
        mask       = df["seniority_level"].isin(_LEADER_LEVELS)
        if scope_dept:
            mask &= df["department"] == str(scope_dept)
        primary_df = df[mask]
        if primary_df.empty:
            primary_df = df.nlargest(3, "impact_score")

    elif scenario_type == "skill_crisis":
        skill      = str(params.get("skill", df["role_title"].value_counts().index[0]))
        primary_df = df[df["role_title"] == skill]
        if primary_df.empty:
            primary_df = df.nlargest(2, "impact_score")

    else:
        raise ValueError(f"Unknown scenario_type: {scenario_type!r}")

    primary_ids = set(primary_df["employee_id"].tolist())

    # ── Cascade ───────────────────────────────────────────────────────────────
    cascade_rounds = _cascade_simulation(df, primary_ids)
    secondary_ids: set = set()
    for r in cascade_rounds:
        secondary_ids |= {e["employee_id"] for e in r["employees"]}

    all_departed = primary_ids | secondary_ids
    total_departed = len(all_departed)
    cascade_multiplier = round(total_departed / max(len(primary_ids), 1), 2)

    # ── Metrics ───────────────────────────────────────────────────────────────
    departed_df    = df[df["employee_id"].isin(all_departed)]
    financial_impact = int(departed_df["annual_salary"].sum() * 1.5)

    skill_holders = df.groupby("role_title")["employee_id"].apply(set).to_dict()
    orphaned_skills = [
        skill for skill, holders in skill_holders.items()
        if holders.issubset(all_departed) and len(holders) > 0
    ]

    team_sizes_after = df[~df["employee_id"].isin(all_departed)].groupby("team_id").size()
    all_teams        = df["team_id"].unique()
    teams_below = [
        str(t) for t in all_teams
        if team_sizes_after.get(t, 0) < _MIN_VIABLE_TEAM
    ]

    resilience_before  = _compute_resilience_score(df)["overall"]
    df_after           = df[~df["employee_id"].isin(all_departed)]
    resilience_after   = _compute_resilience_score(df_after)["overall"] if len(df_after) > 5 else 0.0

    amplifiers = _compute_amplifiers(df, primary_df)

    # ── Primary employee list ─────────────────────────────────────────────────
    primary_list = [
        {
            "employee_id":    str(r["employee_id"]),
            "full_name":      str(r["full_name"]),
            "department":     str(r["department"]),
            "role_title":     str(r.get("role_title", "")),
            "impact_score":   float(r["impact_score"]),
            "attrition_risk": float(r["attrition_risk"]),
            "is_nexus":       bool(r["_is_nexus"]),
            "departure_round": 0,
            "trigger_reason": "primary (scenario trigger)",
        }
        for _, r in primary_df.iterrows()
    ]

    return {
        "scenario_type":      scenario_type,
        "scenario_label":     _SCENARIO_LABELS[scenario_type],
        "params":             {k: str(v) if not isinstance(v, (int, float, bool)) else v for k, v in params.items()},
        "primary_count":      len(primary_ids),
        "total_departed":     total_departed,
        "cascade_multiplier": cascade_multiplier,
        "financial_impact":   financial_impact,
        "orphaned_skills":    orphaned_skills[:12],
        "teams_below_minimum": teams_below[:10],
        "resilience_before":  round(resilience_before, 1),
        "resilience_after":   round(resilience_after, 1),
        "resilience_delta":   round(resilience_after - resilience_before, 1),
        "cascade_rounds":     cascade_rounds,
        "primary_employees":  primary_list,
        "cascade_amplifiers": amplifiers,
    }


# ── Intervention roadmap ──────────────────────────────────────────────────────

def _compute_interventions(df: pd.DataFrame, resilience: dict) -> list[dict]:
    sub = resilience["sub_scores"]
    interventions: list[dict] = []

    def _add(dimension: str, label: str, description: str,
             cost: int, improvement: float, timeline_months: int) -> None:
        score = sub[dimension]
        if score >= 80:
            return
        priority = (
            "critical" if score < 45 else
            "high"     if score < 60 else
            "medium"   if score < 75 else
            "low"
        )
        interventions.append({
            "dimension":        dimension,
            "dimension_label":  label,
            "description":      description,
            "current_score":    score,
            "cost":             cost,
            "score_improvement": round(improvement, 1),
            "priority":         priority,
            "timeline_months":  timeline_months,
            "roi":              round(improvement / max(cost / 10_000, 0.1), 2),
        })

    gap = max(0.0, 75.0 - sub["skill_coverage"])
    _add("skill_coverage", "Skill Coverage",
         f"Cross-train {max(1, int(gap/6)+1)} employees on under-represented top skills; "
         "run peer-learning rotations within affected departments.",
         int(max(1, int(gap / 6) + 1) * 7_500), min(gap * 0.65, 18.0), 3)

    gap = max(0.0, 75.0 - sub["leadership_depth"])
    _add("leadership_depth", "Leadership Depth",
         "Identify high-potential senior employees as Director-track candidates; "
         "initiate formal succession accelerator program.",
         int(gap * 1_300 + 5_000), min(gap * 0.55, 15.0), 6)

    gap = max(0.0, 75.0 - sub["knowledge_redundancy"])
    _add("knowledge_redundancy", "Knowledge Redundancy",
         "Pair single-knowledge-holders with backup learners; "
         "schedule structured knowledge transfer sessions (4 hrs/week).",
         int(gap * 900 + 3_000), min(gap * 0.60, 16.0), 4)

    gap = max(0.0, 75.0 - sub["network_robustness"])
    _add("network_robustness", "Network Robustness",
         "Redistribute nexus employees' responsibilities across multiple teams; "
         "rotate cross-department collaboration assignments.",
         int(gap * 600 + 4_000), min(gap * 0.50, 12.0), 5)

    gap = max(0.0, 75.0 - sub["attrition_concentration"])
    _add("attrition_concentration", "Attrition Distribution",
         "Address concentrated flight-risk factors (compensation, stagnation, leadership) "
         "in highest-risk cohort through targeted retention interventions.",
         int(gap * 1_100 + 6_000), min(gap * 0.58, 14.0), 4)

    gap = max(0.0, 75.0 - sub["team_size_buffer"])
    _add("team_size_buffer", "Team Size Buffer",
         "Hire to bring undersized teams above viable threshold; "
         "consider internal transfers before external recruitment.",
         int(gap * 2_000 + 8_000), min(gap * 0.70, 20.0), 6)

    interventions.sort(key=lambda iv: -iv["roi"])
    return interventions


# ── Synthetic resilience trend ────────────────────────────────────────────────

def _resilience_trend(current: float) -> list[dict]:
    rng    = np.random.default_rng(77)
    points: list[dict] = []
    score  = current - rng.uniform(3, 8)       # start slightly lower 12 mo ago
    for i in range(12, 0, -1):
        dt = datetime.now() - timedelta(days=30 * i)
        points.append({"month": dt.strftime("%Y-%m"), "score": round(float(np.clip(score, 0, 100)), 1)})
        score += rng.normal(0.5, 1.8)           # slight improving trend
    return points


# ── Disruption presets ────────────────────────────────────────────────────────

def _build_presets(df: pd.DataFrame) -> list[dict]:
    top_dept  = str(df["department"].value_counts().index[0])
    top_role  = str(df["role_title"].value_counts().index[0])
    return [
        {
            "label":  "Top 5 High-Impact Depart",
            "type":   "targeted_departure",
            "params": {"n": 5},
        },
        {
            "label":  f"{top_dept} — 30% Dept Shock",
            "type":   "department_shock",
            "params": {"department": top_dept, "pct": 0.30},
        },
        {
            "label":  "Competitive Poaching (Impact ≥65)",
            "type":   "competitive_poaching",
            "params": {"impact_threshold": 65.0, "n": 8},
        },
        {
            "label":  "All Leaders Vacate",
            "type":   "leadership_vacuum",
            "params": {},
        },
        {
            "label":  f"Role Crisis — {top_role}",
            "type":   "skill_crisis",
            "params": {"skill": top_role},
        },
    ]


# ── Main entry point ──────────────────────────────────────────────────────────

def build_resilience_data(scenario: str, size: str) -> dict:
    org = get_org(scenario.upper(), size.lower())
    df  = _add_scores(org.employees.copy().reset_index(drop=True))

    org_resilience = _compute_resilience_score(df)
    dept_res       = _dept_resilience(df)
    interventions  = _compute_interventions(df, org_resilience)
    presets        = _build_presets(df)
    trend          = _resilience_trend(org_resilience["overall"])

    # Cascade amplifier at org level (top 5 by impact score)
    amplifiers = _compute_amplifiers(df, df.nlargest(5, "impact_score"))
    top_amp    = amplifiers[0]["full_name"] if amplifiers else "N/A"

    return {
        "summary": {
            "total_employees":   len(df),
            "overall_resilience": org_resilience["overall"],
            "grade":             org_resilience["grade"],
            "nexus_count":       int(df["_is_nexus"].sum()),
            "at_risk_teams":     int(
                (df.groupby("team_id")["attrition_risk"].mean() > 0.5).sum()
            ),
            "top_cascade_amplifier": top_amp,
            "intervention_count": len(interventions),
        },
        "org_resilience":   org_resilience,
        "dept_resilience":  dept_res,
        "interventions":    interventions,
        "disruption_presets": presets,
        "trend":            trend,
    }
