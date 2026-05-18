"""
Data service: wraps demo_data.generator without any Streamlit dependency.
Uses functools.lru_cache so each (scenario, size) pair is generated once per process.
"""

import sys
import os
from functools import lru_cache
from pathlib import Path

# Ensure repo root is importable regardless of working directory
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import numpy as np

from demo_data.generator import DemoGenerator, GeneratedOrg


@lru_cache(maxsize=9)  # 3 scenarios × 3 sizes
def get_org(scenario_id: str, org_size: str) -> GeneratedOrg:
    """Generate (or return cached) a synthetic org for the given scenario and size."""
    return DemoGenerator(scenario_id=scenario_id, org_size=org_size).generate()


# ---------------------------------------------------------------------------
# Dashboard aggregation
# ---------------------------------------------------------------------------

def build_dashboard_data(scenario: str, size: str) -> dict:
    org = get_org(scenario.upper(), size.lower())
    emp_df  = org.employees
    team_df = org.teams

    # ── Per-employee derived metrics (impact + attrition proxy) ────────────
    rng = np.random.default_rng(42)

    # Impact score: 0-100 heuristic (salary rank + nexus flag + tenure proxy)
    sal_rank = emp_df["annual_salary"].rank(pct=True)
    nexus_bonus = emp_df["_is_nexus"].astype(float) * 15
    noise = rng.normal(0, 5, len(emp_df))
    impact_raw = sal_rank * 70 + nexus_bonus + noise
    emp_df = emp_df.copy()
    emp_df["impact_score"] = np.clip(impact_raw, 0, 100).round(1)

    # Attrition risk: 0-1 heuristic
    sal_inv_rank = 1 - sal_rank
    nexus_retain = emp_df["_is_nexus"].astype(float) * 0.15
    attr_raw = sal_inv_rank * 0.6 + rng.uniform(0, 0.4, len(emp_df)) - nexus_retain
    emp_df["attrition_risk"] = np.clip(attr_raw, 0.01, 0.99).round(3)

    # KPI proxy: average = 3.5, vary by seniority
    kpi_base = {"junior": 3.0, "mid": 3.4, "senior": 3.7, "lead": 3.8, "director": 3.9, "exec": 4.0}
    emp_df["avg_kpi"] = [kpi_base.get(s, 3.4) + float(rng.normal(0, 0.2)) for s in emp_df["seniority_level"]]
    emp_df["avg_kpi"] = np.clip(emp_df["avg_kpi"], 1.0, 5.0).round(2)

    # Top skill (pick one from dept skill list)
    from demo_data.generator import _DEPT_SKILLS
    def pick_skill(dept: str) -> str:
        skills = _DEPT_SKILLS.get(dept, ["Problem Solving"])
        return skills[int(rng.integers(0, len(skills)))]
    emp_df["top_skill"] = [pick_skill(d) for d in emp_df["department"]]

    # Merge team name
    team_name_map = dict(zip(team_df["team_id"], team_df["team_name"]))
    emp_df["team_name"] = emp_df["team_id"].map(team_name_map).fillna("Unassigned")

    # ── Department summary ─────────────────────────────────────────────────
    dept_groups = emp_df.groupby("department")
    dept_budget_map = team_df.groupby("department")["annual_budget"].sum().to_dict()

    dept_rows = []
    for dept, grp in dept_groups:
        total_spend   = float(grp["annual_salary"].sum())
        annual_budget = float(dept_budget_map.get(dept, total_spend))
        variance_pct  = ((total_spend - annual_budget) / annual_budget * 100) if annual_budget else 0
        fragility     = float(grp["_is_nexus"].mean()) * 2  # simplified fragility
        dept_rows.append({
            "department":          dept,
            "headcount":           len(grp),
            "total_spend":         round(total_spend, 2),
            "annual_budget":       round(annual_budget, 2),
            "budget_variance_pct": round(variance_pct, 2),
            "avg_impact":          round(float(grp["impact_score"].mean()), 1),
            "avg_kpi":             round(float(grp["avg_kpi"].mean()), 2),
            "fragility_avg":       round(min(fragility, 1.0), 3),
        })

    # ── Employee table ─────────────────────────────────────────────────────
    emp_rows = []
    for _, row in emp_df.iterrows():
        emp_rows.append({
            "employee_id":    str(row["employee_id"])[:8].upper(),
            "full_name":      row["full_name"],
            "role_title":     row["role_title"],
            "department":     row["department"],
            "team_name":      row["team_name"],
            "annual_salary":  int(row["annual_salary"]),
            "impact_score":   float(row["impact_score"]),
            "attrition_risk": float(row["attrition_risk"]),
            "is_nexus":       bool(row["_is_nexus"]),
            "top_skill":      str(row["top_skill"]),
            "avg_kpi":        float(row["avg_kpi"]),
        })

    # ── Top-level stats ────────────────────────────────────────────────────
    total_spend  = float(emp_df["annual_salary"].sum())
    total_budget = float(team_df["annual_budget"].sum())
    return {
        "org_name":            org.org_name,
        "scenario_id":         org.scenario_id,
        "org_size":            org.org_size,
        "total_headcount":     len(emp_df),
        "total_spend":         round(total_spend, 2),
        "total_budget":        round(total_budget, 2),
        "avg_impact_score":    round(float(emp_df["impact_score"].mean()), 1),
        "budget_variance_pct": round((total_spend - total_budget) / total_budget * 100, 2) if total_budget else 0,
        "n_nexus_employees":   int(emp_df["_is_nexus"].sum()),
        "n_at_risk_teams":     int((emp_df.groupby("team_name")["attrition_risk"].mean() >= 0.6).sum()),
        "scoring_mode":        "demo_heuristic",
        "dept_summary":        dept_rows,
        "employee_table":      emp_rows,
    }


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

def run_simulation(
    scenario: str,
    size: str,
    budget_pct: float,
    force_retain: list[str],
    exclude: list[str],
    leadership_constraint: bool,
    skills_constraint: bool,
) -> dict:
    """Simple ILP-lite simulation (PuLP if available, greedy fallback)."""
    dashboard = build_dashboard_data(scenario, size)
    employees = dashboard["employee_table"]
    total_budget = dashboard["total_budget"] * (budget_pct / 100.0)

    # Exclude set
    exclude_set = set(e.upper() for e in exclude)
    retain_set  = set(r.upper() for r in force_retain)

    candidates = [e for e in employees if e["employee_id"] not in exclude_set]

    # Attempt ILP with PuLP
    try:
        import pulp  # type: ignore
        prob = pulp.LpProblem("retention", pulp.LpMaximize)
        x = {e["employee_id"]: pulp.LpVariable(f"x_{i}", cat="Binary") for i, e in enumerate(candidates)}

        # Objective: maximize total impact
        prob += pulp.lpSum(e["impact_score"] * x[e["employee_id"]] for e in candidates)

        # Budget constraint
        prob += pulp.lpSum(e["annual_salary"] * x[e["employee_id"]] for e in candidates) <= total_budget

        # Force-retain
        for e in candidates:
            if e["employee_id"] in retain_set:
                prob += x[e["employee_id"]] == 1

        solver = pulp.PULP_CBC_CMD(msg=0, timeLimit=8)
        status = prob.solve(solver)
        feasible = pulp.LpStatus[status] == "Optimal"

        infeasibility_reason = None
        if not feasible:
            infeasibility_reason = "No feasible solution found within the budget and constraints. Try increasing the budget or relaxing constraints."

        retained_ids = {eid for eid, var in x.items() if pulp.value(var) == 1} if feasible else set()

    except ImportError:
        # Greedy fallback: sort by impact/salary ratio, fill budget
        feasible = True
        infeasibility_reason = None
        retained_ids: set[str] = set()
        sorted_cands = sorted(
            candidates,
            key=lambda e: (e["employee_id"] in retain_set, e["impact_score"] / max(e["annual_salary"], 1)),
            reverse=True,
        )
        remaining = total_budget
        for e in sorted_cands:
            if e["employee_id"] in retain_set or e["annual_salary"] <= remaining:
                retained_ids.add(e["employee_id"])
                remaining -= e["annual_salary"]

    result_employees = []
    for e in candidates:
        retained = e["employee_id"] in retained_ids
        result_employees.append({
            "employee_id":  e["employee_id"],
            "full_name":    e["full_name"],
            "department":   e["department"],
            "role_title":   e["role_title"],
            "annual_salary":e["annual_salary"],
            "impact_score": e["impact_score"],
            "is_nexus":     e["is_nexus"],
            "retained":     retained,
            "override":     e["employee_id"] in retain_set,
        })

    retained_emps  = [e for e in result_employees if e["retained"]]
    not_retained   = [e for e in result_employees if not e["retained"]]
    total_retained = sum(e["annual_salary"] for e in retained_emps)
    total_at_risk  = sum(e["annual_salary"] for e in not_retained)
    budget_used    = (total_retained / total_budget * 100) if total_budget else 0

    return {
        "retained_count":      len(retained_emps),
        "at_risk_count":       len(not_retained),
        "total_retained_cost": total_retained,
        "total_at_risk_cost":  total_at_risk,
        "budget_used_pct":     round(budget_used, 2),
        "total_impact":        round(sum(e["impact_score"] for e in retained_emps), 1),
        "employees":           result_employees,
        "feasible":            feasible,
        "infeasibility_reason": infeasibility_reason,
    }


# ---------------------------------------------------------------------------
# Predictive / attrition
# ---------------------------------------------------------------------------

_ATTRITION_DRIVERS = [
    "Below-market compensation",
    "Limited growth trajectory",
    "High workload concentration",
    "Low team engagement scores",
    "Manager relationship friction",
    "Tenure milestone (3/5/10 yr)",
    "External market demand for skill",
    "Skill underutilization",
]

def build_attrition_data(scenario: str, size: str) -> dict:
    dashboard = build_dashboard_data(scenario, size)
    employees = dashboard["employee_table"]

    rng = np.random.default_rng(7)
    result = []
    for emp in employees:
        risk = emp["attrition_risk"]
        cat  = (
            "Critical" if risk >= 0.70 else
            "High"     if risk >= 0.50 else
            "Moderate" if risk >= 0.30 else
            "Low"
        )
        driver_idx = int(rng.integers(0, len(_ATTRITION_DRIVERS)))
        result.append({
            "employee_id":    emp["employee_id"],
            "full_name":      emp["full_name"],
            "department":     emp["department"],
            "role_title":     emp["role_title"],
            "attrition_risk": round(risk, 3),
            "risk_category":  cat,
            "top_driver":     _ATTRITION_DRIVERS[driver_idx],
        })

    risks = [e["attrition_risk"] for e in result]
    return {
        "high_risk_count":     sum(1 for e in result if e["risk_category"] in ("High", "Critical")),
        "critical_risk_count": sum(1 for e in result if e["risk_category"] == "Critical"),
        "avg_risk":            round(float(np.mean(risks)), 3),
        "employees":           result,
    }


# ---------------------------------------------------------------------------
# Notifications (static demo)
# ---------------------------------------------------------------------------

_DEMO_NOTIFICATIONS = [
    {
        "id": "n1",
        "title": "Critical Attrition Risk Detected",
        "body": "3 employees in Engineering are flagged Critical risk this month. Recommend scheduling retention conversations.",
        "severity": "critical",
        "created_at": "2026-05-18T09:00:00",
        "read": False,
    },
    {
        "id": "n2",
        "title": "Budget Variance Alert — Sales",
        "body": "Sales department is running 12.4% over annual budget. Current trajectory exceeds allocation by Q3.",
        "severity": "warning",
        "created_at": "2026-05-17T14:30:00",
        "read": False,
    },
    {
        "id": "n3",
        "title": "Model Retrained Successfully",
        "body": "Monthly attrition model retraining completed. AUROC improved from 0.81 to 0.84. SHAP feature ranks updated.",
        "severity": "info",
        "created_at": "2026-05-16T08:00:00",
        "read": True,
    },
    {
        "id": "n4",
        "title": "Nexus Employee Departure Risk",
        "body": "EMP-00A4 (Engineering Nexus) shows High attrition risk. Departure would isolate 14 downstream collaborators.",
        "severity": "warning",
        "created_at": "2026-05-15T11:15:00",
        "read": False,
    },
    {
        "id": "n5",
        "title": "Simulation Saved — Scenario B Review",
        "body": "CFO saved a simulation at 75% budget targeting Scenario B. 42 employees not retained in simulation.",
        "severity": "info",
        "created_at": "2026-05-14T16:45:00",
        "read": True,
    },
]

_read_state: dict[str, bool] = {n["id"]: n["read"] for n in _DEMO_NOTIFICATIONS}  # type: ignore[index]


def get_notifications() -> list[dict]:
    return [
        {**n, "read": _read_state.get(n["id"], n["read"])}  # type: ignore[arg-type]
        for n in _DEMO_NOTIFICATIONS
    ]


def mark_notification_read(notification_id: str) -> bool:
    if notification_id in _read_state:
        _read_state[notification_id] = True
        return True
    return False
