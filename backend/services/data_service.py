"""
Data service: wraps demo_data.generator without any Streamlit dependency.
Orgs are cached in a plain dict so the cache can be cleared or overwritten at runtime.
"""

import sys
from pathlib import Path

# Ensure repo root is importable regardless of working directory
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import dataclasses

import numpy as np
import pandas as pd

from backend.services.scoring import impact_for
from demo_data.generator import DemoGenerator, GeneratedOrg
from demo_data.scenarios import load_scenario

# Module-level org cache: (scenario_id, org_size) → GeneratedOrg
_org_cache: dict[tuple[str, str], GeneratedOrg] = {}


def get_org(scenario_id: str, org_size: str) -> GeneratedOrg:
    """Return a cached org, generating it on first access."""
    key = (scenario_id, org_size)
    if key not in _org_cache:
        _org_cache[key] = DemoGenerator(scenario_id=scenario_id, org_size=org_size).generate()
    return _org_cache[key]


def reset_cache() -> int:
    """Evict all cached orgs. Returns the number of entries cleared."""
    count = len(_org_cache)
    _org_cache.clear()
    return count


def generate_org_with_params(
    scenario_id: str,
    org_size: str,
    seed: int,
    org_name_override: str | None,
    nexus_fraction_override: float,
    budget_variance_override: float,
) -> GeneratedOrg:
    """Generate a synthetic org with custom parameters and store it in the cache."""
    base    = load_scenario(scenario_id)
    patched = dataclasses.replace(
        base,
        nexus_employee_fraction=nexus_fraction_override,
        total_budget_variance=budget_variance_override,
    )

    gen          = DemoGenerator(scenario_id=scenario_id, org_size=org_size, seed=seed)
    gen.scenario = patched
    org          = gen.generate()

    if org_name_override:
        org = dataclasses.replace(org, org_name=org_name_override)

    _org_cache[(scenario_id, org_size)] = org
    return org


# ---------------------------------------------------------------------------
# Dashboard aggregation
# ---------------------------------------------------------------------------

def build_dashboard_data(scenario: str, size: str) -> dict:
    org = get_org(scenario.upper(), size.lower())
    emp_df  = org.employees
    team_df = org.teams

    # ── Per-employee derived metrics (impact + attrition proxy) ────────────
    rng = np.random.default_rng(42)

    # Impact score: shared 4-component model (KPI · network · skills · cost)
    sal_rank = emp_df["annual_salary"].rank(pct=True)
    rng.normal(0, 5, len(emp_df))  # former impact noise: keeps the draws below unchanged
    emp_df = emp_df.copy()
    emp_df["impact_score"] = impact_for(emp_df, org)

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
    team_name_map = dict(zip(team_df["team_id"], team_df["team_name"], strict=False))
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

_LEADER_LEVELS = frozenset({"lead", "director", "exec"})


def _constraint_groups(
    org: GeneratedOrg, candidate_ids: set[str],
) -> tuple[dict[str, list[str]], dict[str, list[str]], dict[str, str]]:
    """Build the coverage groups the simulation can enforce.

    Returns (team_leaders, skill_holders, skill_names), keyed by team_id /
    skill_id, listing candidate short IDs. Groups with no candidate are left
    out: a team with no available leader cannot be constrained to keep one.
    """
    emp = org.employees
    short = emp["employee_id"].astype(str).str[:8].str.upper()
    full_to_short = dict(zip(emp["employee_id"].astype(str), short, strict=True))

    team_leaders: dict[str, list[str]] = {}
    is_leader = emp["seniority_level"].isin(_LEADER_LEVELS)
    for sid, team, lead in zip(short, emp["team_id"].astype(str), is_leader, strict=True):
        if lead and sid in candidate_ids:
            team_leaders.setdefault(team, []).append(sid)

    critical = org.skills[org.skills["is_critical"].astype(bool)]
    skill_names = dict(zip(critical["skill_id"].astype(str), critical["skill_name"], strict=True))
    skill_holders: dict[str, list[str]] = {}
    es = org.employee_skills
    es = es[es["skill_id"].astype(str).isin(skill_names)]
    for eid, skill in zip(es["employee_id"].astype(str), es["skill_id"].astype(str), strict=True):
        sid = full_to_short.get(eid)
        if sid in candidate_ids:
            skill_holders.setdefault(skill, []).append(sid)
    return team_leaders, skill_holders, skill_names


DEFAULT_HEADCOUNT_COST = 10.0  # impact-percentile points charged per retained person


def _impact_percentiles(employees: list[dict]) -> dict[str, float]:
    """Impact rank within the whole org as a 0-100 percentile (ties share the average rank).

    Raw impact scores cluster in a narrow band (~25-75), so summing them rewards
    headcount over impact. Percentiles spread people evenly across 0-100.
    """
    scores = pd.Series({e["employee_id"]: e["impact_score"] for e in employees}, dtype=float)
    return (scores.rank(pct=True) * 100).round(2).to_dict()


def _solve_retention(
    candidates: list[dict],
    budget: float,
    retain_set: set[str],
    groups: list[list[str]],
    weights: dict[str, float],
    headcount_cost: float,
) -> tuple[bool, set[str]]:
    """Maximize Σ (weight_i − headcount_cost)·x_i under the budget; each group needs >= 1 retained.

    weight is the employee's impact percentile (0-100). headcount_cost is a fixed charge
    per person kept, in the same units, so headcount is never free: someone ranked below
    it is only kept when a constraint or an override requires it, even if budget remains.

    Uses PuLP/CBC when available, otherwise a greedy heuristic that first covers every
    group with its cheapest member, then fills by net value per dollar.
    """
    try:
        import pulp  # type: ignore
    except ImportError:
        return _greedy_retention(candidates, budget, retain_set, groups, weights, headcount_cost)

    prob = pulp.LpProblem("retention", pulp.LpMaximize)
    x = {e["employee_id"]: pulp.LpVariable(f"x_{i}", cat="Binary") for i, e in enumerate(candidates)}
    prob += pulp.lpSum((weights[eid] - headcount_cost) * var for eid, var in x.items())
    prob += pulp.lpSum(e["annual_salary"] * x[e["employee_id"]] for e in candidates) <= budget
    for eid in retain_set & x.keys():
        prob += x[eid] == 1
    for members in groups:
        prob += pulp.lpSum(x[m] for m in members) >= 1

    status = prob.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=8))
    if pulp.LpStatus[status] != "Optimal":
        return False, set()
    return True, {eid for eid, var in x.items() if (pulp.value(var) or 0) > 0.5}


def _greedy_retention(
    candidates: list[dict], budget: float, retain_set: set[str], groups: list[list[str]],
    weights: dict[str, float], headcount_cost: float,
) -> tuple[bool, set[str]]:
    by_id = {e["employee_id"]: e for e in candidates}
    retained = {eid for eid in retain_set if eid in by_id}
    for members in groups:
        if not retained.intersection(members):
            retained.add(min(members, key=lambda m: by_id[m]["annual_salary"]))
    spent = sum(by_id[eid]["annual_salary"] for eid in retained)
    if spent > budget:
        return False, set()
    def net(e: dict) -> float:
        return weights[e["employee_id"]] - headcount_cost

    for e in sorted(candidates, key=lambda e: net(e) / max(e["annual_salary"], 1), reverse=True):
        if net(e) <= 0:
            break  # everyone after this one is worth less than a seat costs
        if e["employee_id"] not in retained and spent + e["annual_salary"] <= budget:
            retained.add(e["employee_id"])
            spent += e["annual_salary"]
    return True, retained


def _coverage(groups: dict[str, list[str]], retained: set[str]) -> tuple[int, list[str]]:
    uncovered = [k for k, members in groups.items() if not retained.intersection(members)]
    return len(groups) - len(uncovered), uncovered


def run_simulation(
    scenario: str,
    size: str,
    budget_pct: float,
    force_retain: list[str],
    exclude: list[str],
    leadership_constraint: bool,
    skills_constraint: bool,
    headcount_cost: float = DEFAULT_HEADCOUNT_COST,
) -> dict:
    """Retention ILP: maximize rank-weighted impact within budget, honoring overrides and constraints.

    - Objective: Σ (impact_percentile_i − headcount_cost)·x_i (see _solve_retention).
    - leadership_constraint: every team that has an available leader keeps at least one.
    - skills_constraint: every critical skill that has an available holder keeps at least one.
    """
    dashboard = build_dashboard_data(scenario, size)
    employees = dashboard["employee_table"]
    total_budget = dashboard["total_budget"] * (budget_pct / 100.0)

    exclude_set = {e.upper() for e in exclude}
    retain_set  = {r.upper() for r in force_retain}
    candidates  = [e for e in employees if e["employee_id"] not in exclude_set]
    weights     = _impact_percentiles(employees)  # ranked over the whole org, before exclusions

    team_leaders, skill_holders, skill_names = _constraint_groups(
        get_org(scenario, size), {e["employee_id"] for e in candidates},
    )
    active = {
        "leadership": list(team_leaders.values()) if leadership_constraint else [],
        "skills":     list(skill_holders.values()) if skills_constraint else [],
    }

    feasible, retained_ids = _solve_retention(
        candidates, total_budget, retain_set, active["leadership"] + active["skills"],
        weights, headcount_cost,
    )

    infeasibility_reason = None
    if not feasible:
        # Diagnose: which enabled constraint, dropped on its own, makes the budget work?
        culprits = [
            label for key, label in (("leadership", "leadership coverage"), ("skills", "critical skills coverage"))
            if active[key] and _solve_retention(
                candidates, total_budget, retain_set,
                [g for k, gs in active.items() if k != key for g in gs],
                weights, headcount_cost,
            )[0]
        ]
        if culprits:
            with_overrides = " together with the force-retained employees" if retain_set else ""
            fewer = ", protect fewer employees," if retain_set else ""
            infeasibility_reason = (
                f"The budget cannot cover {' and '.join(culprits)}{with_overrides}. "
                f"Increase the budget{fewer} or relax {' or '.join(culprits)}."
            )
        else:
            infeasibility_reason = (
                "No feasible solution within this budget. The force-retained employees alone may exceed it; "
                "increase the budget or protect fewer employees."
            )

    lead_covered, lead_gaps   = _coverage(team_leaders, retained_ids)
    skill_covered, skill_gaps = _coverage(skill_holders, retained_ids)
    constraints = {
        "leadership": {
            "enabled":   leadership_constraint,
            "covered":   lead_covered,
            "total":     len(team_leaders),
            "uncovered": sorted(lead_gaps),
        },
        "critical_skills": {
            "enabled":   skills_constraint,
            "covered":   skill_covered,
            "total":     len(skill_holders),
            "uncovered": sorted(skill_names[s] for s in skill_gaps),
        },
    }

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
            "impact_percentile": weights[e["employee_id"]],
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
        "constraints":         constraints,
        "objective": {
            "weighting":      "impact_percentile",
            "headcount_cost": headcount_cost,
        },
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


# ---------------------------------------------------------------------------
# Forecasting
# ---------------------------------------------------------------------------

def build_forecast_data(scenario: str, size: str) -> dict:
    """Run Prophet/linear budget and headcount forecasts."""
    from forecasting.budget_forecaster import forecast_budget

    org = get_org(scenario.upper(), size.lower())
    emp_df = org.employees.copy()
    emp_df["total_cost"] = emp_df["annual_salary"]

    result = forecast_budget(emp_df, dept_col="department", cost_col="total_cost")

    def _series(s) -> dict:
        hist = s.history.copy()
        fc   = s.forecast.copy()
        hist["ds"] = hist["ds"].dt.strftime("%Y-%m-%d")
        fc["ds"]   = fc["ds"].dt.strftime("%Y-%m-%d")
        return {
            "label":    s.label,
            "metric":   s.metric,
            "model":    s.model,
            "mape":     round(s.mape, 2),
            "history":  hist.to_dict("records"),
            "forecast": fc.round(2).to_dict("records"),
        }

    return {
        "generated_at":  result.generated_at,
        "total_spend":   _series(result.total_spend),
        "headcount":     _series(result.headcount) if result.headcount else None,
        "by_department": [_series(s) for s in result.by_department],
    }


def build_montecarlo_data(scenario: str, size: str) -> dict:
    """Run Monte Carlo budget stress test (2 000 simulations)."""
    import pandas as pd

    from forecasting.monte_carlo import run_monte_carlo

    org = get_org(scenario.upper(), size.lower())
    emp_df = org.employees.copy()
    emp_df["total_cost"] = emp_df["annual_salary"]
    annual_budget = float(org.teams["annual_budget"].sum())

    # Per-employee attrition risk (0-100) — same heuristic as the dashboard
    rng          = np.random.default_rng(42)
    sal_rank     = emp_df["annual_salary"].rank(pct=True)
    sal_inv_rank = 1 - sal_rank
    nexus_retain = emp_df["_is_nexus"].astype(float) * 0.15
    attr_raw     = sal_inv_rank * 0.6 + rng.uniform(0, 0.4, len(emp_df)) - nexus_retain
    attrition_df = pd.DataFrame({
        "employee_id":    emp_df["employee_id"].values,
        "attrition_risk": np.clip(attr_raw * 100, 1.0, 99.0),
    })

    result = run_monte_carlo(
        employee_df=emp_df,
        annual_budget=annual_budget,
        attrition_result=attrition_df,
        cost_col="total_cost",
        n_simulations=2000,
    )

    fan = result.fan_chart.copy()
    fan["ds"] = fan["ds"].dt.strftime("%Y-%m-%d")

    exc = result.exceedance_prob.copy()
    exc["ds"] = exc["ds"].dt.strftime("%Y-%m-%d")

    return {
        "n_simulations":            result.n_simulations,
        "annual_budget":            round(annual_budget, 2),
        "monthly_budget":           round(annual_budget / 12, 2),
        "prob_overspend_any_month": round(result.prob_overspend_any_month, 3),
        "final_month": {
            "p10":  round(result.final_month_p10, 2),
            "p50":  round(result.final_month_p50, 2),
            "p90":  round(result.final_month_p90, 2),
            "mean": round(result.final_month_mean, 2),
        },
        "fan_chart":       fan.round(2).to_dict("records"),
        "exceedance_prob": exc.round(4).to_dict("records"),
        "notes":           result.notes,
    }
