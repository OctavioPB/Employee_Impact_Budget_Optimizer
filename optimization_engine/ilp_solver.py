"""ILP-based workforce optimization using PuLP (CBC solver).

Mathematical formulation
------------------------
Variables:   x_i ∈ {0, 1}  for each employee i
             1 = retained in simulation, 0 = not retained

Objective:   Maximize Σ (impact_score_i × x_i)

Constraints:
  C1  Budget:        Σ (cost_i × x_i) ≤ budget_target
  C2  Leadership:    Σ (x_i | i ∈ team t, seniority ∈ LEADERSHIP_LEVELS) ≥ 1  ∀ team t
  C3  Skills:        Σ (x_i | i holds critical skill j) ≥ 1  ∀ critical skill j
  C4  Min team size: Σ (x_i | i ∈ team t) ≥ min_team_size  ∀ team t  (optional)
  C5  Succession:    Σ (x_i | i holds critical skill j) ≥ succession_depth + 1  (optional)
  C6  Force retain:  x_i = 1  for each i in force_retain
  C7  Exclude:       x_i = 0  for each i in exclude
"""

import logging
import time
from dataclasses import dataclass

import pandas as pd
import pulp

from optimization_engine.constraints import (
    LEADERSHIP_LEVELS,
    ConstraintConfig,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class OptimizationResult:
    """Full output of a single ILP solve."""

    status: str
    """'Optimal', 'Infeasible', 'Timeout', 'Unbounded', or 'Empty'."""

    retained_ids: set[str]
    at_risk_ids: set[str]

    total_impact: float
    total_cost: float
    budget_target: float
    current_spend: float

    budget_savings: float
    """current_spend - total_cost  (positive = money saved)."""

    savings_pct: float
    """budget_savings / current_spend * 100."""

    avg_impact_retained: float
    avg_impact_baseline: float
    """Impact average before optimization (all employees)."""

    n_retained: int
    n_at_risk: int
    n_total: int

    critical_skills_preserved: list[str]
    critical_skills_lost: list[str]

    teams_with_no_leader: list[str]
    team_impact_change: dict[str, float]
    """team_id → (avg_impact_retained - avg_impact_all)."""

    knowledge_loss_score: float
    """Fraction of total impact score held by at-risk employees."""

    infeasibility_reason: str | None
    solver_time_ms: float

    force_retain_count: int
    exclude_count: int

    @property
    def is_feasible(self) -> bool:
        return self.status == "Optimal"

    @property
    def impact_delta(self) -> float:
        """avg_impact_retained - avg_impact_baseline (negative = worse)."""
        return round(self.avg_impact_retained - self.avg_impact_baseline, 2)


# ---------------------------------------------------------------------------
# Main solve function
# ---------------------------------------------------------------------------

def solve(
    employees: pd.DataFrame,
    budget_target: float,
    impact_scores: pd.DataFrame,
    critical_skill_holders: dict[str, list[str]],
    constraint_config: ConstraintConfig | None = None,
    force_retain: set[str] | None = None,
    exclude: set[str] | None = None,
) -> OptimizationResult:
    """Solve the workforce optimization ILP.

    Args:
        employees: Active employees with columns employee_id, team_id,
                   seniority_level, annual_salary, annual_benefits.
        budget_target: Maximum allowable annual payroll (salary + benefits).
        impact_scores: DataFrame with employee_id, impact_score (0–100).
        critical_skill_holders: skill_id → [employee_ids who hold it].
        constraint_config: Active constraint flags.
        force_retain: Employee IDs that must be retained (x_i = 1).
        exclude: Employee IDs that cannot be retained (x_i = 0).

    Returns:
        OptimizationResult with retained/at-risk sets and full metrics.
    """
    if constraint_config is None:
        constraint_config = ConstraintConfig()
    force_retain = set(force_retain or [])
    exclude = set(exclude or [])

    t0 = time.perf_counter()

    emp = _prepare(employees, impact_scores)
    if emp.empty:
        return _empty_result(budget_target)

    emp_ids = emp["employee_id"].tolist()
    impact_dict: dict[str, float] = dict(zip(emp["employee_id"], emp["impact_score"], strict=False))
    cost_dict: dict[str, float] = dict(zip(emp["employee_id"], emp["total_cost"], strict=False))
    seniority_dict: dict[str, str] = dict(zip(emp["employee_id"], emp["seniority_level"], strict=False))
    team_dict: dict[str, str] = dict(zip(emp["employee_id"], emp["team_id"], strict=False))

    teams_to_emp: dict[str, list[str]] = {}
    for eid in emp_ids:
        teams_to_emp.setdefault(str(team_dict[eid]), []).append(eid)

    current_spend = sum(cost_dict.values())
    avg_impact_baseline = sum(impact_dict.values()) / len(emp_ids) if emp_ids else 0.0

    # ------------------------------------------------------------------
    # Build PuLP problem
    # ------------------------------------------------------------------
    prob = pulp.LpProblem("EIBO_workforce_optimization", pulp.LpMaximize)

    # Decision variables — PuLP names must be valid identifiers, so we index them
    var_names = {eid: f"x{i}" for i, eid in enumerate(emp_ids)}
    x: dict[str, pulp.LpVariable] = {
        eid: pulp.LpVariable(var_names[eid], cat="Binary")
        for eid in emp_ids
    }

    # Objective
    prob += pulp.lpSum(impact_dict[i] * x[i] for i in emp_ids), "total_impact"

    # C1 — Budget
    prob += (
        pulp.lpSum(cost_dict[i] * x[i] for i in emp_ids) <= budget_target,
        "C1_budget",
    )

    # C2 — Leadership per team
    if constraint_config.require_leadership_per_team:
        for tid, members in teams_to_emp.items():
            available_leaders = [
                i for i in members
                if seniority_dict.get(i) in LEADERSHIP_LEVELS and i not in exclude
            ]
            if available_leaders:
                prob += (
                    pulp.lpSum(x[i] for i in available_leaders) >= 1,
                    f"C2_leader_{tid}",
                )

    # C3 — Critical skill coverage (+ C5 succession if enabled)
    min_holders = 1 + max(0, constraint_config.succession_depth)
    if constraint_config.require_critical_skills:
        for skill_id, holders in critical_skill_holders.items():
            available = [h for h in holders if h in x and h not in exclude]
            if available:
                rhs = min(min_holders, len(available))
                prob += (
                    pulp.lpSum(x[h] for h in available) >= rhs,
                    f"C3_skill_{skill_id[:20]}",
                )

    # C4 — Minimum team size
    if constraint_config.min_team_size > 0:
        for tid, members in teams_to_emp.items():
            available = [i for i in members if i not in exclude]
            rhs = min(constraint_config.min_team_size, len(available))
            if rhs > 0:
                prob += (
                    pulp.lpSum(x[i] for i in available) >= rhs,
                    f"C4_minteam_{tid}",
                )

    # C6 — Force retain
    for eid in force_retain:
        if eid in x:
            prob += x[eid] == 1, f"C6_fr_{var_names[eid]}"

    # C7 — Exclude
    for eid in exclude:
        if eid in x:
            prob += x[eid] == 0, f"C7_ex_{var_names[eid]}"

    # ------------------------------------------------------------------
    # Solve
    # ------------------------------------------------------------------
    solver = pulp.PULP_CBC_CMD(
        msg=constraint_config.solver_msg,
        timeLimit=constraint_config.time_limit_seconds,
    )
    prob.solve(solver)
    solver_time_ms = (time.perf_counter() - t0) * 1000
    status_str = pulp.LpStatus[prob.status]

    if status_str != "Optimal":
        return _infeasible_result(
            status=status_str,
            budget_target=budget_target,
            current_spend=current_spend,
            avg_impact_baseline=avg_impact_baseline,
            solver_time_ms=solver_time_ms,
            force_retain=force_retain,
            exclude=exclude,
            emp=emp,
            cost_dict=cost_dict,
            seniority_dict=seniority_dict,
            teams_to_emp=teams_to_emp,
            critical_skill_holders=critical_skill_holders,
            n_total=len(emp_ids),
        )

    # ------------------------------------------------------------------
    # Extract solution
    # ------------------------------------------------------------------
    retained_ids = {
        eid for eid in emp_ids
        if (val := x[eid].varValue) is not None and val > 0.5
    }
    at_risk_ids = set(emp_ids) - retained_ids

    total_impact = sum(impact_dict[i] for i in retained_ids)
    total_cost = sum(cost_dict[i] for i in retained_ids)
    budget_savings = current_spend - total_cost
    savings_pct = budget_savings / current_spend * 100 if current_spend > 0 else 0.0
    avg_impact_retained = total_impact / len(retained_ids) if retained_ids else 0.0
    knowledge_loss = sum(impact_dict[i] for i in at_risk_ids)
    knowledge_loss_score = (
        knowledge_loss / sum(impact_dict.values())
        if sum(impact_dict.values()) > 0 else 0.0
    )

    # Critical skills preserved / lost
    preserved, lost = [], []
    for skill_id, holders in critical_skill_holders.items():
        (preserved if any(h in retained_ids for h in holders) else lost).append(skill_id)

    # Teams with no leader
    teams_no_leader = [
        tid for tid, members in teams_to_emp.items()
        if not any(
            i in retained_ids and seniority_dict.get(i) in LEADERSHIP_LEVELS
            for i in members
        )
    ]

    # Per-team impact delta
    team_impact_change: dict[str, float] = {}
    for tid, members in teams_to_emp.items():
        all_impact = [impact_dict[i] for i in members]
        ret_impact = [impact_dict[i] for i in members if i in retained_ids]
        avg_all = sum(all_impact) / len(all_impact) if all_impact else 0.0
        avg_ret = sum(ret_impact) / len(ret_impact) if ret_impact else 0.0
        team_impact_change[tid] = round(avg_ret - avg_all, 2)

    logger.info(
        "ILP: %s | retained=%d/%d | cost=$%.0fK | savings=$%.0fK (%.1f%%) | t=%.0fms",
        status_str, len(retained_ids), len(emp_ids),
        total_cost / 1_000, budget_savings / 1_000, savings_pct, solver_time_ms,
    )

    return OptimizationResult(
        status=status_str,
        retained_ids=retained_ids,
        at_risk_ids=at_risk_ids,
        total_impact=round(total_impact, 2),
        total_cost=round(total_cost, 2),
        budget_target=budget_target,
        current_spend=round(current_spend, 2),
        budget_savings=round(budget_savings, 2),
        savings_pct=round(savings_pct, 2),
        avg_impact_retained=round(avg_impact_retained, 2),
        avg_impact_baseline=round(avg_impact_baseline, 2),
        n_retained=len(retained_ids),
        n_at_risk=len(at_risk_ids),
        n_total=len(emp_ids),
        critical_skills_preserved=preserved,
        critical_skills_lost=lost,
        teams_with_no_leader=teams_no_leader,
        team_impact_change=team_impact_change,
        knowledge_loss_score=round(knowledge_loss_score, 4),
        infeasibility_reason=None,
        solver_time_ms=round(solver_time_ms, 1),
        force_retain_count=len(force_retain & set(emp_ids)),
        exclude_count=len(exclude & set(emp_ids)),
    )


# ---------------------------------------------------------------------------
# Infeasibility diagnosis
# ---------------------------------------------------------------------------

def diagnose_infeasibility(
    employees: pd.DataFrame,
    budget_target: float,
    impact_scores: pd.DataFrame,
    critical_skill_holders: dict[str, list[str]],
    force_retain: set[str],
    exclude: set[str],
    constraint_config: ConstraintConfig,
) -> list[str]:
    """Return a list of human-readable infeasibility causes.

    Tries progressively relaxed solves to identify the binding constraint.
    """
    causes: list[str] = []

    emp = _prepare(employees, impact_scores)
    if emp.empty:
        return ["No employees available to optimize."]

    cost_dict = dict(zip(emp["employee_id"], emp["total_cost"], strict=False))
    seniority_dict = dict(zip(emp["employee_id"], emp["seniority_level"], strict=False))
    team_dict = dict(zip(emp["employee_id"], emp["team_id"], strict=False))

    # Check 1: force-retain cost exceeds budget
    fr_cost = sum(cost_dict.get(eid, 0.0) for eid in force_retain if eid in cost_dict)
    if fr_cost > budget_target:
        causes.append(
            f"Force-retained employees cost ${fr_cost/1_000_000:.2f}M, "
            f"exceeding the budget target of ${budget_target/1_000_000:.2f}M. "
            "Remove some Force Retain overrides or increase the budget."
        )

    # Check 2: critical skills fully excluded
    if constraint_config.require_critical_skills:
        for skill_id, holders in critical_skill_holders.items():
            available = [h for h in holders if h not in exclude and h in cost_dict]
            if not available:
                causes.append(
                    f"Critical skill '{skill_id}' has no available holders "
                    "(all holders are excluded or missing from the dataset). "
                    "Remove the Exclude override or disable the skills constraint."
                )

    # Check 3: teams with all leaders excluded
    if constraint_config.require_leadership_per_team:
        teams_to_emp: dict[str, list[str]] = {}
        for eid in emp["employee_id"]:
            teams_to_emp.setdefault(str(team_dict[eid]), []).append(eid)
        for tid, members in teams_to_emp.items():
            leaders = [i for i in members if seniority_dict.get(i) in LEADERSHIP_LEVELS]
            available_leaders = [i for i in leaders if i not in exclude]
            if leaders and not available_leaders:
                causes.append(
                    f"Team '{tid}' has all its leaders marked as excluded. "
                    "Remove the Exclude override for at least one leader."
                )

    if not causes:
        causes.append(
            "The solver could not find a feasible solution with the current constraints. "
            "Try: (1) increasing the budget, (2) disabling the leadership or skills constraint, "
            "or (3) removing manual overrides."
        )

    return causes


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _prepare(employees: pd.DataFrame, impact_scores: pd.DataFrame) -> pd.DataFrame:
    emp = employees[
        ["employee_id", "team_id", "seniority_level",
         "annual_salary", "annual_benefits"]
    ].copy()
    emp = emp.merge(
        impact_scores[["employee_id", "impact_score"]], on="employee_id", how="left"
    )
    emp["impact_score"] = pd.to_numeric(emp["impact_score"], errors="coerce").fillna(0.0)
    emp["total_cost"] = emp["annual_salary"] + emp["annual_benefits"]
    emp["team_id"] = emp["team_id"].astype(str)
    emp["seniority_level"] = emp["seniority_level"].fillna("mid")
    return emp


def _empty_result(budget_target: float) -> OptimizationResult:
    return OptimizationResult(
        status="Empty",
        retained_ids=set(), at_risk_ids=set(),
        total_impact=0.0, total_cost=0.0,
        budget_target=budget_target, current_spend=0.0,
        budget_savings=0.0, savings_pct=0.0,
        avg_impact_retained=0.0, avg_impact_baseline=0.0,
        n_retained=0, n_at_risk=0, n_total=0,
        critical_skills_preserved=[], critical_skills_lost=[],
        teams_with_no_leader=[], team_impact_change={},
        knowledge_loss_score=0.0,
        infeasibility_reason="No employees provided.",
        solver_time_ms=0.0,
        force_retain_count=0, exclude_count=0,
    )


def _infeasible_result(
    status: str,
    budget_target: float,
    current_spend: float,
    avg_impact_baseline: float,
    solver_time_ms: float,
    force_retain: set[str],
    exclude: set[str],
    emp: pd.DataFrame,
    cost_dict: dict[str, float],
    seniority_dict: dict[str, str],
    teams_to_emp: dict[str, list[str]],
    critical_skill_holders: dict[str, list[str]],
    n_total: int,
) -> OptimizationResult:
    # Quick diagnosis without a full ConstraintConfig re-run
    causes: list[str] = []

    fr_cost = sum(cost_dict.get(eid, 0.0) for eid in force_retain)
    if fr_cost > budget_target:
        causes.append(
            f"Force-retained employees cost ${fr_cost/1_000_000:.2f}M > "
            f"budget target ${budget_target/1_000_000:.2f}M."
        )
    for skill_id, holders in critical_skill_holders.items():
        if not any(h for h in holders if h not in exclude and h in cost_dict):
            causes.append(f"Critical skill '{skill_id}' has no available holders.")
    for tid, members in teams_to_emp.items():
        leaders = [i for i in members if seniority_dict.get(i) in LEADERSHIP_LEVELS]
        if leaders and not any(i for i in leaders if i not in exclude):
            causes.append(f"Team '{tid}' has all leaders excluded.")

    reason = " | ".join(causes) if causes else (
        "Infeasible: constraints cannot all be satisfied simultaneously. "
        "Increase budget, disable a constraint, or remove overrides."
    )

    logger.warning("ILP infeasible (%s): %s", status, reason)

    return OptimizationResult(
        status=status,
        retained_ids=set(), at_risk_ids=set(emp["employee_id"].tolist()),
        total_impact=0.0, total_cost=0.0,
        budget_target=budget_target, current_spend=round(current_spend, 2),
        budget_savings=0.0, savings_pct=0.0,
        avg_impact_retained=0.0, avg_impact_baseline=round(avg_impact_baseline, 2),
        n_retained=0, n_at_risk=n_total, n_total=n_total,
        critical_skills_preserved=[], critical_skills_lost=list(critical_skill_holders.keys()),
        teams_with_no_leader=list(teams_to_emp.keys()),
        team_impact_change={},
        knowledge_loss_score=1.0,
        infeasibility_reason=reason,
        solver_time_ms=round(solver_time_ms, 1),
        force_retain_count=len(force_retain),
        exclude_count=len(exclude),
    )
