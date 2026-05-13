"""Budget sensitivity analysis: how recommendations change at ±5 %, ±10 %, ±20 %.

Runs a lightweight ILP solve for each delta level and returns a structured
comparison table showing impact, headcount, and cost at each budget point.
"""

import logging
from dataclasses import dataclass

import pandas as pd

from optimization_engine.constraints import ConstraintConfig
from optimization_engine.ilp_solver import OptimizationResult, solve

logger = logging.getLogger(__name__)

# Standard sensitivity deltas (relative to a base budget target)
_DEFAULT_DELTAS = [-0.20, -0.10, -0.05, 0.00, +0.05, +0.10, +0.20]


@dataclass
class SensitivityRow:
    delta_pct: float          # e.g. -0.10 means 10 % below base
    budget_target: float
    status: str
    n_retained: int
    total_impact: float
    total_cost: float
    savings_pct: float
    skills_lost: int
    teams_no_leader: int


@dataclass
class SensitivityReport:
    base_budget: float
    rows: list[SensitivityRow]

    @property
    def as_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame([
            {
                "Budget Change": f"{'+' if r.delta_pct >= 0 else ''}{r.delta_pct*100:.0f}%",
                "Budget Target ($M)": round(r.budget_target / 1_000_000, 2),
                "Status": r.status,
                "Retained": r.n_retained,
                "Total Impact": round(r.total_impact, 1),
                "Optimized Cost ($M)": round(r.total_cost / 1_000_000, 2),
                "Savings %": round(r.savings_pct, 1),
                "Skills Lost": r.skills_lost,
                "Teams w/o Leader": r.teams_no_leader,
            }
            for r in self.rows
        ])

    @property
    def base_row(self) -> SensitivityRow | None:
        """Row corresponding to delta == 0 (no change)."""
        for row in self.rows:
            if abs(row.delta_pct) < 1e-6:
                return row
        return None

    def impact_delta_at(self, delta_pct: float) -> float | None:
        """Return change in total impact vs the base budget row."""
        base = self.base_row
        if base is None:
            return None
        for row in self.rows:
            if abs(row.delta_pct - delta_pct) < 1e-6:
                return row.total_impact - base.total_impact
        return None


def run_sensitivity(
    employees: pd.DataFrame,
    base_budget: float,
    impact_scores: pd.DataFrame,
    critical_skill_holders: dict[str, list[str]],
    constraint_config: ConstraintConfig | None = None,
    force_retain: set[str] | None = None,
    exclude: set[str] | None = None,
    deltas: list[float] | None = None,
) -> SensitivityReport:
    """Solve ILP at each budget delta and return a SensitivityReport.

    Args:
        employees: Active employee DataFrame.
        base_budget: The reference budget (slider value or 90 % of current spend).
        impact_scores: DataFrame with employee_id, impact_score.
        critical_skill_holders: skill_id → [employee_ids].
        constraint_config: Shared constraint settings.
        force_retain: Employee IDs always retained.
        exclude: Employee IDs never retained.
        deltas: Budget deltas to evaluate relative to base_budget.
                Defaults to [-20 %, -10 %, -5 %, 0 %, +5 %, +10 %, +20 %].

    Returns:
        SensitivityReport with one row per delta level.
    """
    if deltas is None:
        deltas = _DEFAULT_DELTAS
    if constraint_config is None:
        constraint_config = ConstraintConfig()

    fast_config = ConstraintConfig(
        require_leadership_per_team=constraint_config.require_leadership_per_team,
        require_critical_skills=constraint_config.require_critical_skills,
        min_team_size=constraint_config.min_team_size,
        succession_depth=0,
        time_limit_seconds=15,
        solver_msg=False,
    )

    rows: list[SensitivityRow] = []
    for delta in deltas:
        budget_target = base_budget * (1.0 + delta)
        result: OptimizationResult = solve(
            employees=employees,
            budget_target=budget_target,
            impact_scores=impact_scores,
            critical_skill_holders=critical_skill_holders,
            constraint_config=fast_config,
            force_retain=force_retain or set(),
            exclude=exclude or set(),
        )
        rows.append(SensitivityRow(
            delta_pct=delta,
            budget_target=budget_target,
            status=result.status,
            n_retained=result.n_retained,
            total_impact=result.total_impact,
            total_cost=result.total_cost,
            savings_pct=result.savings_pct,
            skills_lost=len(result.critical_skills_lost),
            teams_no_leader=len(result.teams_with_no_leader),
        ))
        logger.debug(
            "Sensitivity Δ%+.0f%%: %s | retained=%d | impact=%.1f",
            delta * 100, result.status, result.n_retained, result.total_impact,
        )

    logger.info("Sensitivity analysis: %d budget levels evaluated", len(rows))
    return SensitivityReport(base_budget=base_budget, rows=rows)
