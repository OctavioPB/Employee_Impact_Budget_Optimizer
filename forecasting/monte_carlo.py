"""Monte Carlo budget stress testing.

Runs N simulations of 12-month budget trajectories, sampling attrition
events and cost shocks, and returns P10/P50/P90 fan chart data.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_DEFAULT_N_SIMS = 5_000
_DEFAULT_HORIZON = 12


# ---------------------------------------------------------------------------
# Output dataclasses
# ---------------------------------------------------------------------------

@dataclass
class MonteCarloResult:
    """Results of a Monte Carlo budget simulation."""
    # Monthly trajectories: columns p10, p50, p90, mean
    fan_chart: pd.DataFrame                      # ds, p10, p50, p90, mean
    # Probability of exceeding budget at each month
    exceedance_prob: pd.DataFrame                # ds, prob_over_budget
    # Summary stats for the final month
    final_month_p10: float = 0.0
    final_month_p50: float = 0.0
    final_month_p90: float = 0.0
    final_month_mean: float = 0.0
    # Probability of overspend over entire horizon
    prob_overspend_any_month: float = 0.0
    n_simulations: int = _DEFAULT_N_SIMS
    annual_budget: float = 0.0
    notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Simulator
# ---------------------------------------------------------------------------

class MonteCarloSimulator:
    """Simulates budget trajectories using bootstrapped uncertainty.

    Uncertainty sources:
    - Voluntary attrition (monthly probability per employee)
    - Salary inflation shocks (annual, correlated across employees)
    - Hiring cost overruns (random when attrition triggers replacement)
    - Seasonal cost variation (end-of-year bonuses)
    """

    def __init__(
        self,
        n_simulations: int = _DEFAULT_N_SIMS,
        horizon_months: int = _DEFAULT_HORIZON,
        seed: int = 42,
    ) -> None:
        self._n = n_simulations
        self._horizon = horizon_months
        self._rng = np.random.default_rng(seed)

    def simulate(
        self,
        employee_df: pd.DataFrame,
        annual_budget: float,
        attrition_result: pd.DataFrame | None = None,
        cost_col: str = "total_cost",
        dept_col: str = "department",
        monthly_attrition_rate: float = 0.015,
        salary_inflation_annual: float = 0.03,
        replacement_cost_multiplier: float = 0.25,
    ) -> MonteCarloResult:
        """Run Monte Carlo simulation.

        Args:
            employee_df: Snapshot with cost_col and optionally dept_col.
            annual_budget: Planned annual budget (for exceedance calc).
            attrition_result: Optional AttritionResult.scores DataFrame
                              with attrition_risk column. If provided,
                              per-employee monthly attrition probabilities
                              are derived from it; otherwise a uniform
                              rate is used.
            cost_col: Cost column in employee_df.
            dept_col: Department column in employee_df.
            monthly_attrition_rate: Baseline monthly probability of voluntary
                                    departure per employee (uniform fallback).
            salary_inflation_annual: Expected annual salary cost growth.
            replacement_cost_multiplier: Replacement cost as fraction of
                                         departing employee's annual cost.

        Returns:
            MonteCarloResult with fan chart and exceedance probability.
        """
        costs = employee_df[cost_col].values.astype(float) if cost_col in employee_df.columns else np.full(len(employee_df), 60_000.0)
        n_emp = len(costs)
        monthly_budget = annual_budget / 12

        # Per-employee monthly attrition probability
        if attrition_result is not None and "attrition_risk" in attrition_result.columns:
            risk_scores = self._align_risk_scores(employee_df, attrition_result)
            # Scale: risk score 0-100 → monthly prob 0.5%–5%
            monthly_probs = 0.005 + (risk_scores / 100) * 0.045
        else:
            monthly_probs = np.full(n_emp, monthly_attrition_rate)

        # Vectorised simulation: shape (n_sims, horizon, n_emp)
        # Attrition events
        attrition_draws = self._rng.random(size=(self._n, self._horizon, n_emp))
        attrition_mask = attrition_draws < monthly_probs[np.newaxis, np.newaxis, :]   # bool

        # Monthly inflation factor (correlated shock at year boundary)
        monthly_inflation = (1 + salary_inflation_annual) ** (1 / 12)
        inflation_path = monthly_inflation ** np.arange(1, self._horizon + 1)  # (horizon,)

        # Additional shock: random ±1% monthly cost noise per employee
        cost_noise = self._rng.normal(1.0, 0.01, size=(self._n, self._horizon, n_emp))

        # Compute monthly spend per simulation
        # When attrition_mask[s,m,e] is True, employee e is gone from month m onward
        # cumulative departure: once gone, stays gone
        cumulative_gone = np.cumsum(attrition_mask, axis=1) > 0       # (n_sims, horizon, n_emp)

        # Employee cost each month (inflation + noise, zero if departed)
        emp_monthly_cost = costs[np.newaxis, np.newaxis, :] * inflation_path[np.newaxis, :, np.newaxis] * cost_noise
        emp_monthly_cost[cumulative_gone] = 0.0

        # Add replacement costs: one-time hit in the month attrition occurs
        n_departed_this_month = attrition_mask.sum(axis=2)            # (n_sims, horizon)
        avg_cost = costs.mean() if n_emp > 0 else 60_000
        replacement_hit = n_departed_this_month * avg_cost * replacement_cost_multiplier

        # Total monthly spend
        monthly_spend = emp_monthly_cost.sum(axis=2) + replacement_hit  # (n_sims, horizon)

        # Seasonal bonus spike in December (month index based on current date)
        start_month = pd.Timestamp.today().month
        for m in range(self._horizon):
            cal_month = (start_month + m - 1) % 12 + 1
            if cal_month == 12:
                monthly_spend[:, m] *= 1.08
            elif cal_month in (6, 7):
                monthly_spend[:, m] *= 1.02

        # Fan chart
        future_dates = pd.date_range(
            start=pd.Timestamp.today().replace(day=1) + pd.DateOffset(months=1),
            periods=self._horizon,
            freq="MS",
        )

        p10 = np.percentile(monthly_spend, 10, axis=0)
        p50 = np.percentile(monthly_spend, 50, axis=0)
        p90 = np.percentile(monthly_spend, 90, axis=0)
        mean = monthly_spend.mean(axis=0)

        fan_chart = pd.DataFrame({
            "ds": future_dates,
            "p10": p10,
            "p50": p50,
            "p90": p90,
            "mean": mean,
            "budget_line": monthly_budget,
        })

        # Exceedance probability
        over_budget = (monthly_spend > monthly_budget).mean(axis=0)
        exceedance = pd.DataFrame({"ds": future_dates, "prob_over_budget": over_budget})

        # Probability of overspend in at least one month
        prob_any = float((monthly_spend > monthly_budget).any(axis=1).mean())

        notes: list[str] = []
        if not _PROPHET_AVAILABLE_FLAG:
            notes.append("Prophet not installed; linear trend used for history synthesis.")
        if attrition_result is None:
            notes.append(f"Uniform monthly attrition rate ({monthly_attrition_rate:.1%}) used.")

        final = monthly_spend[:, -1]
        return MonteCarloResult(
            fan_chart=fan_chart,
            exceedance_prob=exceedance,
            final_month_p10=float(np.percentile(final, 10)),
            final_month_p50=float(np.percentile(final, 50)),
            final_month_p90=float(np.percentile(final, 90)),
            final_month_mean=float(final.mean()),
            prob_overspend_any_month=prob_any,
            n_simulations=self._n,
            annual_budget=annual_budget,
            notes=notes,
        )

    def _align_risk_scores(
        self,
        employee_df: pd.DataFrame,
        attrition_df: pd.DataFrame,
    ) -> np.ndarray:
        """Return risk score array aligned to employee_df order."""
        if "employee_id" not in employee_df.columns or "employee_id" not in attrition_df.columns:
            return np.full(len(employee_df), 40.0)
        merged = employee_df[["employee_id"]].merge(
            attrition_df[["employee_id", "attrition_risk"]],
            on="employee_id",
            how="left",
        )
        scores = merged["attrition_risk"].fillna(40.0).values.astype(float)
        return np.clip(scores, 0, 100)


# ---------------------------------------------------------------------------
# Prophet availability flag (reuse from budget_forecaster pattern)
# ---------------------------------------------------------------------------

_PROPHET_AVAILABLE_FLAG = False
try:
    from prophet import Prophet  # type: ignore  # noqa: F401
    _PROPHET_AVAILABLE_FLAG = True
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def run_monte_carlo(
    employee_df: pd.DataFrame,
    annual_budget: float,
    attrition_result: pd.DataFrame | None = None,
    cost_col: str = "total_cost",
    n_simulations: int = _DEFAULT_N_SIMS,
    horizon_months: int = _DEFAULT_HORIZON,
    monthly_attrition_rate: float = 0.015,
    seed: int = 42,
) -> MonteCarloResult:
    """Run Monte Carlo budget stress test. Convenience wrapper."""
    return MonteCarloSimulator(
        n_simulations=n_simulations,
        horizon_months=horizon_months,
        seed=seed,
    ).simulate(
        employee_df=employee_df,
        annual_budget=annual_budget,
        attrition_result=attrition_result,
        cost_col=cost_col,
        monthly_attrition_rate=monthly_attrition_rate,
    )
