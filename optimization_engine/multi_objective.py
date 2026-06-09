"""Multi-objective optimization: Pareto frontier for budget vs impact trade-offs.

Computes the efficient frontier by parametrically varying the budget constraint
and collecting (cost, impact) pairs.  Each point on the frontier represents a
solution where no further cost reduction is possible without losing impact.
"""

import logging
from dataclasses import dataclass

import pandas as pd

from optimization_engine.constraints import ConstraintConfig
from optimization_engine.ilp_solver import OptimizationResult, solve

logger = logging.getLogger(__name__)

# Budget fraction sweep: from 50 % to 120 % of current spend in 13 steps
_PARETO_FRACTIONS = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85,
                     0.90, 0.95, 1.00, 1.05, 1.10, 1.15, 1.20]


@dataclass
class ParetoPoint:
    budget_fraction: float  # relative to current_spend
    budget_target: float
    total_cost: float
    total_impact: float
    n_retained: int
    savings_pct: float
    status: str


@dataclass
class ParetoFrontier:
    points: list[ParetoPoint]
    current_spend: float
    """Original spend (budget_fraction = 1.0 reference)."""

    @property
    def as_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame([
            {
                "Budget %": f"{p.budget_fraction*100:.0f}%",
                "Budget Target ($M)": round(p.budget_target / 1_000_000, 2),
                "Optimized Cost ($M)": round(p.total_cost / 1_000_000, 2),
                "Impact Score": round(p.total_impact, 1),
                "Retained": p.n_retained,
                "Savings %": round(p.savings_pct, 1),
                "Status": p.status,
            }
            for p in self.points
        ])

    @property
    def feasible_points(self) -> list[ParetoPoint]:
        return [p for p in self.points if p.status == "Optimal"]


def compute_pareto_frontier(
    employees: pd.DataFrame,
    current_spend: float,
    impact_scores: pd.DataFrame,
    critical_skill_holders: dict[str, list[str]],
    constraint_config: ConstraintConfig | None = None,
    force_retain: set[str] | None = None,
    exclude: set[str] | None = None,
    fractions: list[float] | None = None,
) -> ParetoFrontier:
    """Compute the Pareto frontier by solving the ILP at each budget fraction.

    Args:
        employees: Active employee DataFrame.
        current_spend: Total current annual payroll (salary + benefits).
        impact_scores: DataFrame with employee_id, impact_score.
        critical_skill_holders: skill_id → [employee_ids].
        constraint_config: Shared constraint settings for all solves.
        force_retain: Employee IDs always retained.
        exclude: Employee IDs never retained.
        fractions: Budget fractions to evaluate (defaults to _PARETO_FRACTIONS).

    Returns:
        ParetoFrontier with one ParetoPoint per fraction evaluated.
    """
    if fractions is None:
        fractions = _PARETO_FRACTIONS
    if constraint_config is None:
        constraint_config = ConstraintConfig()
    force_retain = set(force_retain or [])
    exclude = set(exclude or [])

    # Use a fast-solve config for frontier sweeps (shorter time limit)
    sweep_config = ConstraintConfig(
        require_leadership_per_team=constraint_config.require_leadership_per_team,
        require_critical_skills=constraint_config.require_critical_skills,
        min_team_size=constraint_config.min_team_size,
        succession_depth=0,  # skip succession for speed
        time_limit_seconds=15,
        solver_msg=False,
    )

    points: list[ParetoPoint] = []
    for frac in fractions:
        budget_target = current_spend * frac
        result: OptimizationResult = solve(
            employees=employees,
            budget_target=budget_target,
            impact_scores=impact_scores,
            critical_skill_holders=critical_skill_holders,
            constraint_config=sweep_config,
            force_retain=force_retain,
            exclude=exclude,
        )
        points.append(ParetoPoint(
            budget_fraction=frac,
            budget_target=budget_target,
            total_cost=result.total_cost,
            total_impact=result.total_impact,
            n_retained=result.n_retained,
            savings_pct=result.savings_pct,
            status=result.status,
        ))
        logger.debug(
            "Pareto %.0f%%: %s | impact=%.1f | retained=%d",
            frac * 100, result.status, result.total_impact, result.n_retained,
        )

    logger.info(
        "Pareto frontier: %d points computed, %d feasible",
        len(points),
        sum(1 for p in points if p.status == "Optimal"),
    )

    return ParetoFrontier(points=points, current_spend=current_spend)


def find_minimum_viable_budget(
    pareto: ParetoFrontier,
    min_impact_threshold: float | None = None,
) -> float | None:
    """Return the lowest budget fraction where the ILP is feasible.

    If min_impact_threshold is set, also requires total_impact >= threshold.
    """
    feasible = pareto.feasible_points
    if min_impact_threshold is not None:
        feasible = [p for p in feasible if p.total_impact >= min_impact_threshold]
    if not feasible:
        return None
    return min(p.budget_fraction for p in feasible)
