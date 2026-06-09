"""Learning & Development Investment Optimizer — Sprint 16.

Implements:
  - 15-program training catalog across 5 tracks
  - Training effectiveness model (impact delta, attrition reduction, proficiency gain)
    keyed on learning velocity inferred from seniority + seeded noise
  - L&D budget optimization via PuLP ILP (y_{i,t} binary variables)
  - Pareto frontier: sweep budget split between retention and L&D
  - Skill gap analysis: role coverage < 2 holders triggers gap record
  - Synthetic ROI history (12 past cohorts, predicted vs actual)
"""

import sys
from datetime import date, timedelta
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import numpy as np
import pandas as pd
from pulp import (  # type: ignore[import-untyped]
    PULP_CBC_CMD,
    LpBinary,
    LpMaximize,
    LpProblem,
    LpVariable,
    lpSum,
)
from pulp import (
    value as lp_value,
)

from backend.services.data_service import get_org

# ── Training catalog ──────────────────────────────────────────────────────────

TRAINING_CATALOG: list[dict] = [
    # Technical track
    {
        "id": "tech_python_ml",     "name": "Python for Machine Learning",
        "track": "Technical",       "target_skill": "Machine Learning",
        "cost": 2500,               "duration_weeks": 8,
        "proficiency_gain": 22,     "prerequisites": [],       "capacity": 20,
    },
    {
        "id": "tech_data_eng",      "name": "Data Engineering Foundations",
        "track": "Technical",       "target_skill": "Data Engineering",
        "cost": 3000,               "duration_weeks": 10,
        "proficiency_gain": 25,     "prerequisites": [],       "capacity": 20,
    },
    {
        "id": "tech_cloud",         "name": "Cloud Architecture (AWS/GCP)",
        "track": "Technical",       "target_skill": "Cloud Infrastructure",
        "cost": 4500,               "duration_weeks": 12,
        "proficiency_gain": 30,     "prerequisites": [],       "capacity": 15,
    },
    {
        "id": "tech_security",      "name": "Cybersecurity Fundamentals",
        "track": "Technical",       "target_skill": "Security",
        "cost": 3500,               "duration_weeks": 8,
        "proficiency_gain": 22,     "prerequisites": [],       "capacity": 20,
    },
    {
        "id": "tech_devops",        "name": "DevOps & CI/CD Practices",
        "track": "Technical",       "target_skill": "DevOps",
        "cost": 2800,               "duration_weeks": 6,
        "proficiency_gain": 18,     "prerequisites": [],       "capacity": 25,
    },
    # Data & Analytics track
    {
        "id": "data_analytics",     "name": "Advanced Data Analytics",
        "track": "Data & Analytics","target_skill": "Data Analytics",
        "cost": 2000,               "duration_weeks": 6,
        "proficiency_gain": 20,     "prerequisites": [],       "capacity": 30,
    },
    {
        "id": "data_viz",           "name": "Data Visualization & Storytelling",
        "track": "Data & Analytics","target_skill": "Data Visualization",
        "cost": 1500,               "duration_weeks": 4,
        "proficiency_gain": 15,     "prerequisites": [],       "capacity": 30,
    },
    {
        "id": "data_ai",            "name": "AI & LLM Integration",
        "track": "Data & Analytics","target_skill": "Artificial Intelligence",
        "cost": 5000,               "duration_weeks": 10,
        "proficiency_gain": 28,     "prerequisites": ["tech_python_ml"],
        "capacity": 10,
    },
    # Leadership track
    {
        "id": "lead_mgmt",          "name": "People Management Essentials",
        "track": "Leadership",      "target_skill": "People Management",
        "cost": 3000,               "duration_weeks": 8,
        "proficiency_gain": 25,     "prerequisites": [],       "capacity": 20,
    },
    {
        "id": "lead_exec",          "name": "Executive Presence & Strategy",
        "track": "Leadership",      "target_skill": "Strategic Leadership",
        "cost": 5500,               "duration_weeks": 12,
        "proficiency_gain": 30,     "prerequisites": ["lead_mgmt"],
        "capacity": 10,
    },
    {
        "id": "lead_conflict",      "name": "Conflict Resolution & Negotiation",
        "track": "Leadership",      "target_skill": "Conflict Resolution",
        "cost": 2200,               "duration_weeks": 4,
        "proficiency_gain": 18,     "prerequisites": [],       "capacity": 25,
    },
    # Product & Business track
    {
        "id": "biz_pm",             "name": "Product Management Certification",
        "track": "Product & Business","target_skill": "Product Management",
        "cost": 3800,               "duration_weeks": 10,
        "proficiency_gain": 28,     "prerequisites": [],       "capacity": 15,
    },
    {
        "id": "biz_finance",        "name": "Financial Acumen for Managers",
        "track": "Product & Business","target_skill": "Financial Analysis",
        "cost": 2500,               "duration_weeks": 6,
        "proficiency_gain": 20,     "prerequisites": [],       "capacity": 20,
    },
    # Communication track
    {
        "id": "comm_public",        "name": "Public Speaking & Presentation",
        "track": "Communication",   "target_skill": "Communication",
        "cost": 1800,               "duration_weeks": 4,
        "proficiency_gain": 18,     "prerequisites": [],       "capacity": 30,
    },
    {
        "id": "comm_writing",       "name": "Business Writing & Documentation",
        "track": "Communication",   "target_skill": "Technical Writing",
        "cost": 1200,               "duration_weeks": 3,
        "proficiency_gain": 15,     "prerequisites": [],       "capacity": 30,
    },
]

_CATALOG_BY_ID: dict[str, dict] = {p["id"]: p for p in TRAINING_CATALOG}

# Track → departments that benefit most
_TRACK_RELEVANCE: dict[str, dict[str, float]] = {
    "Technical":        {"Engineering": 1.0, "Data Science": 0.95, "Product": 0.8,
                         "Marketing": 0.5, "Sales": 0.4, "Finance": 0.5,
                         "HR": 0.4, "Operations": 0.6},
    "Data & Analytics": {"Data Science": 1.0, "Engineering": 0.85, "Product": 0.8,
                         "Finance": 0.75, "Marketing": 0.7, "Operations": 0.7,
                         "Sales": 0.55, "HR": 0.5},
    "Leadership":       {"default": 0.8},   # applies to seniority, not dept
    "Product & Business":{"Product": 1.0, "Marketing": 0.9, "Finance": 0.85,
                          "Sales": 0.85, "Engineering": 0.7, "Operations": 0.8,
                          "HR": 0.75, "Data Science": 0.7},
    "Communication":    {"default": 0.85},  # universal benefit
}

_SEN_VELOCITY: dict[str, float] = {
    "junior": 0.85, "mid": 0.90, "senior": 0.80,
    "lead": 0.72, "director": 0.65, "exec": 0.55,
}
_LEADER_LEVELS = {"lead", "director", "exec"}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _add_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Replicate impact_score + attrition_risk (same seed as resilience_service)."""
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


def _compute_learning_velocity(df: pd.DataFrame, rng: np.random.Generator) -> pd.Series:
    base = df["seniority_level"].map(lambda s: _SEN_VELOCITY.get(str(s).lower(), 0.75))
    noise = rng.normal(0, 0.05, len(df))
    return np.clip(base + noise, 0.3, 1.0).round(3)


def _track_relevance(program: dict, dept: str, seniority: str) -> float:
    track = program["track"]
    if track == "Leadership":
        if seniority in _LEADER_LEVELS:
            return 1.0
        return 0.70
    if track == "Communication":
        return _TRACK_RELEVANCE["Communication"]["default"]
    table = _TRACK_RELEVANCE.get(track, {})
    return table.get(dept, 0.60)


def _effectiveness(program: dict, dept: str, seniority: str,
                   velocity: float, attrition_risk: float, salary: float) -> dict:
    relevance     = _track_relevance(program, dept, seniority)
    prof_gain     = program["proficiency_gain"] * velocity * relevance
    impact_delta  = round((prof_gain / 100) * 12.0 * relevance, 2)
    attr_red      = round(program["proficiency_gain"] * 0.0025 * (1 + attrition_risk), 4)
    cost          = program["cost"]
    annual_gain   = impact_delta * salary / 100
    roi           = round(annual_gain / cost, 3) if cost > 0 else 0.0
    return {
        "proficiency_gain":     round(prof_gain, 1),
        "impact_delta":         impact_delta,
        "attrition_reduction":  attr_red,
        "roi":                  roi,
    }


# ── L&D ILP ───────────────────────────────────────────────────────────────────

def run_ld_optimization(
    df: pd.DataFrame,
    budget: float,
    max_per_employee: int = 2,
    close_gaps: bool = False,
) -> dict:
    """Solve L&D allocation via PuLP ILP. Returns optimization result dict."""
    rng      = np.random.default_rng(16)
    df       = _add_scores(df.copy().reset_index(drop=True))
    velocity = _compute_learning_velocity(df, rng)
    df["learning_velocity"] = velocity

    # Cap at top 150 employees by L&D priority to keep solver fast
    df["_ld_priority"] = df["attrition_risk"] * (1.0 - df["impact_score"] / 100) * velocity
    if len(df) > 150:
        df = df.nlargest(150, "_ld_priority").reset_index(drop=True)

    emp_ids = df["employee_id"].tolist()
    prog_ids = [p["id"] for p in TRAINING_CATALOG]

    # Pre-compute effectiveness for all (emp, prog) pairs
    eff: dict[tuple, dict] = {}
    for _, row in df.iterrows():
        for prog in TRAINING_CATALOG:
            eff[(row["employee_id"], prog["id"])] = _effectiveness(
                prog,
                str(row.get("department", "")),
                str(row.get("seniority_level", "mid")),
                float(row["learning_velocity"]),
                float(row["attrition_risk"]),
                float(row["annual_salary"]),
            )

    # PuLP model
    prob = LpProblem("ld_optimize", LpMaximize)
    y    = {(i, t): LpVariable(f"y_{i}_{t}", cat=LpBinary)
            for i in emp_ids for t in prog_ids}

    # Objective: impact_delta weighted 0.7 + attrition_reduction scaled to comparable units
    prob += lpSum(
        (eff[(i, t)]["impact_delta"] * 0.7 + eff[(i, t)]["attrition_reduction"] * 8)
        * y[(i, t)]
        for i in emp_ids for t in prog_ids
    )

    # Budget constraint
    prob += lpSum(
        _CATALOG_BY_ID[t]["cost"] * y[(i, t)]
        for i in emp_ids for t in prog_ids
    ) <= budget

    # Capacity: each employee ≤ max_per_employee programs
    for i in emp_ids:
        prob += lpSum(y[(i, t)] for t in prog_ids) <= max_per_employee

    # Skill gap closure: ensure at least 1 person per critical gap program (optional)
    if close_gaps:
        gap_progs = _critical_gap_programs(df)
        for prog_id in gap_progs:
            if prog_id in prog_ids:
                prob += lpSum(y[(i, prog_id)] for i in emp_ids) >= 1

    prob.solve(PULP_CBC_CMD(msg=0))
    status = prob.status

    allocations: list[dict] = []
    total_cost  = 0.0
    total_impact_gain = 0.0
    total_attr_red    = 0.0

    for _, row in df.iterrows():
        i = row["employee_id"]
        for prog in TRAINING_CATALOG:
            t = prog["id"]
            if y.get((i, t)) and lp_value(y[(i, t)]) > 0.5:
                e = eff[(i, t)]
                allocations.append({
                    "employee_id":        i,
                    "full_name":          str(row["full_name"]),
                    "department":         str(row.get("department", "")),
                    "role_title":         str(row.get("role_title", "")),
                    "seniority_level":    str(row.get("seniority_level", "")),
                    "impact_score":       float(row["impact_score"]),
                    "attrition_risk":     float(row["attrition_risk"]),
                    "learning_velocity":  float(row["learning_velocity"]),
                    "program_id":         t,
                    "program_name":       prog["name"],
                    "track":              prog["track"],
                    "cost":               prog["cost"],
                    "duration_weeks":     prog["duration_weeks"],
                    "impact_delta":       e["impact_delta"],
                    "attrition_reduction":e["attrition_reduction"],
                    "roi":                e["roi"],
                })
                total_cost       += prog["cost"]
                total_impact_gain += e["impact_delta"]
                total_attr_red    += e["attrition_reduction"]

    unique_emps = len({a["employee_id"] for a in allocations})

    return {
        "budget":                     budget,
        "budget_used":                round(total_cost, 2),
        "total_allocations":          len(allocations),
        "unique_employees":           unique_emps,
        "expected_impact_gain":       round(total_impact_gain, 2),
        "expected_attrition_reduction": round(total_attr_red, 4),
        "gap_closures":               len(_critical_gap_programs(df)) if close_gaps else 0,
        "allocations":                allocations,
        "status":                     "Optimal" if status == 1 else "Feasible",
    }


def _critical_gap_programs(df: pd.DataFrame) -> list[str]:
    """Return program IDs that address skill gaps (roles with < 2 holders)."""
    role_counts = df["role_title"].value_counts()
    gap_roles   = set(role_counts[role_counts < 2].index)
    # Map gaps to programs via target_skill keyword matching
    progs = []
    for prog in TRAINING_CATALOG:
        skill = prog["target_skill"].lower()
        for role in gap_roles:
            if any(kw in role.lower() for kw in skill.split()):
                progs.append(prog["id"])
                break
    return list(set(progs))


# ── Pareto frontier ───────────────────────────────────────────────────────────

def compute_pareto_frontier(df: pd.DataFrame, total_budget: float, n_points: int = 8) -> list[dict]:
    """Sweep L&D/retention split from 0% to 100% L&D and record combined outcomes."""
    df = _add_scores(df.copy().reset_index(drop=True))
    df_sorted = df.sort_values("impact_score", ascending=False).reset_index(drop=True)

    # Pre-sort employees by descending impact score for greedy retention
    emp_costs   = df_sorted["annual_salary"].values + df_sorted["annual_benefits"].values
    emp_impacts = df_sorted["impact_score"].values

    rng      = np.random.default_rng(16)
    velocity = _compute_learning_velocity(df, rng)
    df["learning_velocity"] = velocity

    # Max L&D impact achievable (all budget to L&D)
    max_ld_result = run_ld_optimization(df, total_budget, max_per_employee=2)
    max_ld_gain   = max_ld_result["expected_impact_gain"] or 1.0

    # Max retention impact achievable (all budget to retention)
    retained_cost = 0.0
    retained_impact = 0.0
    for cost, impact in zip(emp_costs, emp_impacts, strict=False):
        if retained_cost + cost <= total_budget:
            retained_cost   += cost
            retained_impact += impact
    max_ret_impact = retained_impact or 1.0

    points: list[dict] = []
    for k in range(n_points):
        ld_pct  = k / (n_points - 1)         # 0 → 1.0
        ret_pct = 1.0 - ld_pct
        ld_bud  = total_budget * ld_pct
        ret_bud = total_budget * ret_pct

        # Retention: greedy
        r_cost = 0.0
        r_imp  = 0.0
        for cost, impact in zip(emp_costs, emp_impacts, strict=False):
            if r_cost + cost <= ret_bud:
                r_cost += cost
                r_imp  += impact

        # L&D: quick ILP (or skip if ld_bud too small)
        if ld_bud >= 1200:
            ld_res  = run_ld_optimization(df, ld_bud, max_per_employee=2)
            ld_gain = ld_res["expected_impact_gain"]
        else:
            ld_gain = 0.0

        # Combined score: normalize to [0,100] range
        combined = round(
            (r_imp / max_ret_impact * 50) + (ld_gain / max_ld_gain * 50), 2
        )

        points.append({
            "ld_pct":            round(ld_pct * 100, 1),
            "retention_pct":     round(ret_pct * 100, 1),
            "ld_budget":         round(ld_bud, 0),
            "retention_budget":  round(ret_bud, 0),
            "retention_impact":  round(r_imp, 1),
            "ld_impact_gain":    round(ld_gain, 2),
            "combined_score":    combined,
        })

    return points


# ── Skill gap analysis ────────────────────────────────────────────────────────

def _compute_skill_gaps(df: pd.DataFrame) -> list[dict]:
    """Identify role gaps per department and map to training programs."""
    gaps: list[dict] = []
    for dept, grp in df.groupby("department"):
        role_counts = grp["role_title"].value_counts()
        for role, cnt in role_counts.items():
            if cnt >= 2:
                continue
            severity = "critical" if cnt == 0 else "high" if df[df["role_title"] == role]["attrition_risk"].mean() > 0.6 else "medium"
            # Find matching programs
            role_kws  = str(role).lower().split()
            rec_progs = [
                p["name"] for p in TRAINING_CATALOG
                if any(kw in p["target_skill"].lower() or kw in p["name"].lower()
                       for kw in role_kws)
            ][:2]
            internal = len(rec_progs) > 0
            est_cost = sum(
                p["cost"] for p in TRAINING_CATALOG
                if p["name"] in rec_progs
            )
            gaps.append({
                "department":           str(dept),
                "skill":                str(role),
                "current_holders":      int(cnt),
                "required_holders":     2,
                "gap_severity":         severity,
                "recommended_programs": rec_progs,
                "internal_closeable":   internal,
                "estimated_cost":       est_cost,
                "affected_employees":   len(grp),
            })
    # Sort: critical first, then high
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    gaps.sort(key=lambda g: order.get(g["gap_severity"], 4))
    return gaps[:30]  # cap at 30 for display


# ── Synthetic ROI history ─────────────────────────────────────────────────────

def _synthetic_roi_history(rng: np.random.Generator, n_employees: int) -> list[dict]:
    """Generate 12 synthetic past training cohort records."""
    programs = [p for p in TRAINING_CATALOG if not p["prerequisites"]][:12]
    today    = date.today()
    records: list[dict] = []

    for i, prog in enumerate(programs):
        completion = today - timedelta(days=(i + 1) * 30)
        participants = max(2, int(n_employees * rng.uniform(0.03, 0.10)))
        predicted_roi = round(rng.uniform(1.5, 3.2), 2)
        actual_roi    = round(predicted_roi * rng.uniform(0.75, 1.30), 2)
        delta_ratio   = actual_roi / predicted_roi
        status = (
            "above_forecast" if delta_ratio > 1.10
            else "below_forecast" if delta_ratio < 0.90
            else "on_target"
        )
        records.append({
            "id":                str(i + 1),
            "program_name":      prog["name"],
            "track":             prog["track"],
            "completion_month":  completion.strftime("%b %Y"),
            "participants":      participants,
            "total_cost":        participants * prog["cost"],
            "predicted_roi":     predicted_roi,
            "actual_roi":        actual_roi,
            "avg_impact_delta":  round(prog["proficiency_gain"] * 0.10 * rng.uniform(0.8, 1.2), 2),
            "status":            status,
        })

    records.sort(key=lambda r: r["completion_month"], reverse=True)
    return records


# ── Employee preview matrix ───────────────────────────────────────────────────

def _employee_previews(df: pd.DataFrame, rng: np.random.Generator) -> list[dict]:
    """Top 20 employees by attrition risk × impact for training preview tab."""
    df = df.copy()
    velocity = _compute_learning_velocity(df, rng)
    df["learning_velocity"] = velocity
    df["_preview_score"] = df["attrition_risk"] * df["impact_score"] / 100
    sample = df.nlargest(20, "_preview_score").reset_index(drop=True)

    previews: list[dict] = []
    for _, row in sample.iterrows():
        programs_eff: list[dict] = []
        for prog in TRAINING_CATALOG:
            e = _effectiveness(
                prog,
                str(row.get("department", "")),
                str(row.get("seniority_level", "mid")),
                float(row["learning_velocity"]),
                float(row["attrition_risk"]),
                float(row["annual_salary"]),
            )
            prereqs_met = all(
                df[(df["employee_id"] == row["employee_id"])].shape[0] >= 0
                for _ in prog["prerequisites"]  # simplified: always eligible in demo
            )
            programs_eff.append({
                "program_id":          prog["id"],
                "program_name":        prog["name"],
                "track":               prog["track"],
                "cost":                prog["cost"],
                "duration_weeks":      prog["duration_weeks"],
                "impact_delta":        e["impact_delta"],
                "attrition_reduction": e["attrition_reduction"],
                "proficiency_gain":    e["proficiency_gain"],
                "roi":                 e["roi"],
                "eligible":            prereqs_met,
            })
        programs_eff.sort(key=lambda p: p["roi"], reverse=True)

        previews.append({
            "employee_id":      str(row["employee_id"]),
            "full_name":        str(row["full_name"]),
            "department":       str(row.get("department", "")),
            "role_title":       str(row.get("role_title", "")),
            "seniority_level":  str(row.get("seniority_level", "")),
            "impact_score":     float(row["impact_score"]),
            "attrition_risk":   float(row["attrition_risk"]),
            "learning_velocity": float(row["learning_velocity"]),
            "programs":         programs_eff,
        })

    return previews


# ── Main entry point ──────────────────────────────────────────────────────────

def build_ld_data(scenario: str, size: str) -> dict:
    org = get_org(scenario, size)
    df  = _add_scores(org.employees.copy().reset_index(drop=True))

    rng      = np.random.default_rng(16)
    velocity = _compute_learning_velocity(df, rng)
    df["learning_velocity"] = velocity

    n_emp = len(df)

    # Default L&D budget: ~8% of total payroll
    total_payroll = float(df["annual_salary"].sum() + df["annual_benefits"].sum())
    default_budget = round(total_payroll * 0.08, -3)  # round to nearest 1000

    # Default optimization
    default_opt = run_ld_optimization(df, default_budget, max_per_employee=2)

    # Skill gaps
    skill_gaps = _compute_skill_gaps(df)
    critical_gaps = sum(1 for g in skill_gaps if g["gap_severity"] == "critical")

    # ROI history
    roi_history = _synthetic_roi_history(rng, n_emp)

    # Pareto frontier (uses 30% of total payroll as shared budget envelope)
    pareto_budget = round(total_payroll * 0.30, -3)
    pareto_points = compute_pareto_frontier(df, pareto_budget)

    # Employee previews
    previews = _employee_previews(df, np.random.default_rng(16))

    avg_velocity = round(float(df["learning_velocity"].mean()), 3)

    summary = {
        "total_employees":       n_emp,
        "catalog_size":          len(TRAINING_CATALOG),
        "skill_gaps":            len(skill_gaps),
        "critical_gaps":         critical_gaps,
        "avg_learning_velocity": avg_velocity,
        "default_budget":        default_budget,
        "expected_impact_gain":  default_opt["expected_impact_gain"],
    }

    return {
        "summary":              summary,
        "catalog":              TRAINING_CATALOG,
        "default_optimization": default_opt,
        "skill_gaps":           skill_gaps,
        "roi_history":          roi_history,
        "pareto_frontier":      pareto_points,
        "employee_previews":    previews,
    }
