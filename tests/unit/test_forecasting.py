"""Unit tests for forecasting/budget_forecaster.py and forecasting/monte_carlo.py."""

import numpy as np
import pandas as pd
import pytest

from forecasting.budget_forecaster import (
    BudgetForecaster,
    BudgetForecastResult,
    ForecastSeries,
    forecast_budget,
)
from forecasting.monte_carlo import (
    MonteCarloResult,
    MonteCarloSimulator,
    run_monte_carlo,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_employees(n: int = 50, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "employee_id": [f"E{i:03d}" for i in range(n)],
        "department": rng.choice(["Engineering", "Marketing", "Finance", "HR"], n),
        "total_cost": rng.uniform(60_000, 180_000, n),
        "hire_date": pd.date_range("2019-01-01", periods=n, freq="30D").strftime("%Y-%m-%d"),
    })


def _make_attrition_scores(employee_ids: list[str], seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "employee_id": employee_ids,
        "attrition_risk": rng.uniform(10, 80, len(employee_ids)),
    })


# ===========================================================================
# Class: TestBudgetForecasterShape
# ===========================================================================

class TestBudgetForecasterShape:
    def test_returns_budget_forecast_result(self):
        emp = _make_employees(20)
        result = forecast_budget(emp)
        assert isinstance(result, BudgetForecastResult)

    def test_total_spend_series_present(self):
        emp = _make_employees(20)
        result = forecast_budget(emp)
        assert isinstance(result.total_spend, ForecastSeries)

    def test_forecast_has_12_months(self):
        emp = _make_employees(20)
        result = forecast_budget(emp)
        assert len(result.total_spend.forecast) == 12

    def test_forecast_columns_present(self):
        emp = _make_employees(20)
        result = forecast_budget(emp)
        fc = result.total_spend.forecast
        required = {"ds", "yhat", "yhat_lower_80", "yhat_upper_80",
                    "yhat_lower_95", "yhat_upper_95"}
        assert required.issubset(set(fc.columns))

    def test_forecast_yhat_nonnegative(self):
        emp = _make_employees(20)
        result = forecast_budget(emp)
        assert (result.total_spend.forecast["yhat"] >= 0).all()

    def test_forecast_ci_ordering(self):
        """Lower bound ≤ yhat ≤ upper bound for 80% CI."""
        emp = _make_employees(20)
        result = forecast_budget(emp)
        fc = result.total_spend.forecast
        assert (fc["yhat_lower_80"] <= fc["yhat"]).all()
        assert (fc["yhat"] <= fc["yhat_upper_80"]).all()

    def test_95_ci_wider_than_80_ci(self):
        emp = _make_employees(20)
        result = forecast_budget(emp)
        fc = result.total_spend.forecast
        width_80 = (fc["yhat_upper_80"] - fc["yhat_lower_80"]).mean()
        width_95 = (fc["yhat_upper_95"] - fc["yhat_lower_95"]).mean()
        assert width_95 >= width_80, "95% CI should be wider than 80% CI"

    def test_by_department_series_present(self):
        emp = _make_employees(40)
        result = forecast_budget(emp)
        assert len(result.by_department) > 0

    def test_each_dept_series_has_12_months(self):
        emp = _make_employees(40)
        result = forecast_budget(emp)
        for series in result.by_department:
            assert len(series.forecast) == 12

    def test_headcount_forecast_present(self):
        emp = _make_employees(20)
        result = forecast_budget(emp)
        assert result.headcount is not None

    def test_summary_df_property(self):
        emp = _make_employees(20)
        result = forecast_budget(emp)
        sdf = result.summary_df
        assert "ds" in sdf.columns
        assert "yhat" in sdf.columns

    def test_generated_at_is_set(self):
        emp = _make_employees(20)
        result = forecast_budget(emp)
        assert len(result.generated_at) > 0


# ===========================================================================
# Class: TestBudgetForecasterContent
# ===========================================================================

class TestBudgetForecasterContent:
    def test_forecast_dates_are_future(self):
        emp = _make_employees(20)
        result = forecast_budget(emp)
        fc = result.total_spend.forecast
        today = pd.Timestamp.today().normalize()
        assert (fc["ds"] > today).all()

    def test_forecast_dates_monotonically_increasing(self):
        emp = _make_employees(20)
        result = forecast_budget(emp)
        fc = result.total_spend.forecast
        diffs = fc["ds"].diff().dropna()
        assert (diffs > pd.Timedelta(0)).all()

    def test_history_matches_employee_cost_order_of_magnitude(self):
        emp = _make_employees(50)
        # The budget forecaster treats total_cost as a monthly baseline, so
        # avg monthly history ≈ total_cost.sum() (within seasonal noise ±15%)
        result = forecast_budget(emp)
        hist = result.total_spend.history
        avg_monthly_hist = hist["y"].mean()
        total_monthly_baseline = emp["total_cost"].sum()
        assert avg_monthly_hist > total_monthly_baseline * 0.70
        assert avg_monthly_hist < total_monthly_baseline * 1.30

    def test_department_labels_match_input(self):
        emp = _make_employees(40)
        depts = sorted(emp["department"].unique())
        result = forecast_budget(emp)
        series_labels = sorted(s.label for s in result.by_department)
        assert series_labels == depts

    def test_model_field_is_valid_string(self):
        emp = _make_employees(20)
        result = forecast_budget(emp)
        assert result.total_spend.model in {"prophet", "linear"}

    def test_mape_is_nonnegative(self):
        emp = _make_employees(20)
        result = forecast_budget(emp)
        assert result.total_spend.mape >= 0


# ===========================================================================
# Class: TestBudgetForecasterEdgeCases
# ===========================================================================

class TestBudgetForecasterEdgeCases:
    def test_single_employee(self):
        emp = _make_employees(1)
        result = forecast_budget(emp)
        assert len(result.total_spend.forecast) == 12

    def test_missing_department_column(self):
        emp = _make_employees(10).drop(columns=["department"])
        result = forecast_budget(emp)
        assert len(result.total_spend.forecast) == 12
        assert result.by_department == []

    def test_missing_cost_column_uses_fallback(self):
        emp = _make_employees(10).drop(columns=["total_cost"])
        # Should not raise
        result = forecast_budget(emp)
        assert isinstance(result, BudgetForecastResult)

    def test_custom_horizon(self):
        emp = _make_employees(20)
        result = forecast_budget(emp, forecast_months=6)
        assert len(result.total_spend.forecast) == 6

    def test_custom_history_months(self):
        emp = _make_employees(20)
        forecaster = BudgetForecaster(history_months=12)
        result = forecaster.forecast(emp)
        assert len(result.total_spend.history) == 12


# ===========================================================================
# Class: TestMonteCarloShape
# ===========================================================================

class TestMonteCarloShape:
    def test_returns_monte_carlo_result(self):
        emp = _make_employees(30)
        result = run_monte_carlo(emp, annual_budget=3_000_000)
        assert isinstance(result, MonteCarloResult)

    def test_fan_chart_has_horizon_rows(self):
        emp = _make_employees(30)
        result = run_monte_carlo(emp, annual_budget=3_000_000, horizon_months=12)
        assert len(result.fan_chart) == 12

    def test_fan_chart_columns(self):
        emp = _make_employees(30)
        result = run_monte_carlo(emp, annual_budget=3_000_000)
        required = {"ds", "p10", "p50", "p90", "mean", "budget_line"}
        assert required.issubset(set(result.fan_chart.columns))

    def test_percentile_ordering(self):
        """P10 ≤ P50 ≤ P90 for every month."""
        emp = _make_employees(30)
        result = run_monte_carlo(emp, annual_budget=3_000_000)
        fc = result.fan_chart
        assert (fc["p10"] <= fc["p50"]).all()
        assert (fc["p50"] <= fc["p90"]).all()

    def test_exceedance_prob_in_0_1(self):
        emp = _make_employees(30)
        result = run_monte_carlo(emp, annual_budget=3_000_000)
        assert result.exceedance_prob["prob_over_budget"].between(0, 1).all()

    def test_overall_prob_in_0_1(self):
        emp = _make_employees(30)
        result = run_monte_carlo(emp, annual_budget=3_000_000)
        assert 0 <= result.prob_overspend_any_month <= 1

    def test_n_simulations_recorded(self):
        emp = _make_employees(10)
        result = run_monte_carlo(emp, annual_budget=1_000_000, n_simulations=100)
        assert result.n_simulations == 100

    def test_annual_budget_recorded(self):
        emp = _make_employees(10)
        budget = 2_500_000.0
        result = run_monte_carlo(emp, annual_budget=budget)
        assert result.annual_budget == budget


# ===========================================================================
# Class: TestMonteCarloContent
# ===========================================================================

class TestMonteCarloContent:
    def test_zero_budget_high_exceedance(self):
        """Budget of $0 → every simulation exceeds budget."""
        emp = _make_employees(20)
        result = run_monte_carlo(emp, annual_budget=1.0, n_simulations=200)
        assert result.prob_overspend_any_month > 0.95

    def test_very_large_budget_low_exceedance(self):
        """Budget 10× monthly spend × 12 → very low exceedance.

        The simulator treats total_cost as a monthly figure; the annual budget
        must be set relative to total_cost.sum() (monthly) × 12 × multiplier.
        """
        emp = _make_employees(20)
        monthly_baseline = emp["total_cost"].sum()   # simulator treats this as monthly
        result = run_monte_carlo(
            emp, annual_budget=monthly_baseline * 12 * 10, n_simulations=200
        )
        assert result.prob_overspend_any_month < 0.05

    def test_high_attrition_reduces_final_month_spend(self):
        """High attrition → fewer employees on payroll → lower final-month spend.

        Salary savings from departures outweigh replacement costs (25% of cost),
        so by month 12, high-attrition orgs have lower P50 than low-attrition.
        """
        emp = _make_employees(30, seed=11)
        ids = emp["employee_id"].tolist()

        low_risk = _make_attrition_scores(ids, seed=20)
        low_risk["attrition_risk"] = 5.0     # near-zero monthly departure prob

        high_risk = _make_attrition_scores(ids, seed=20)
        high_risk["attrition_risk"] = 90.0   # very high departure prob

        budget = emp["total_cost"].sum() * 12
        r_low = run_monte_carlo(emp, annual_budget=budget, attrition_result=low_risk,
                                n_simulations=1000, seed=42)
        r_high = run_monte_carlo(emp, annual_budget=budget, attrition_result=high_risk,
                                 n_simulations=1000, seed=42)

        # With ~90% monthly departure, by month 12 most employees are gone
        assert r_high.final_month_p50 < r_low.final_month_p50, \
            "High attrition should reduce month-12 P50 (fewer employees on payroll)"

    def test_reproducible_with_same_seed(self):
        """Same seed → same P10/P50/P90 values (dates are wall-clock, so skip)."""
        emp = _make_employees(20)
        r1 = run_monte_carlo(emp, annual_budget=2_000_000, seed=42, n_simulations=100)
        r2 = run_monte_carlo(emp, annual_budget=2_000_000, seed=42, n_simulations=100)
        numeric_cols = ["p10", "p50", "p90", "mean"]
        pd.testing.assert_frame_equal(
            r1.fan_chart[numeric_cols].reset_index(drop=True),
            r2.fan_chart[numeric_cols].reset_index(drop=True),
        )

    def test_different_seeds_give_different_results(self):
        emp = _make_employees(20)
        r1 = run_monte_carlo(emp, annual_budget=2_000_000, seed=1, n_simulations=100)
        r2 = run_monte_carlo(emp, annual_budget=2_000_000, seed=2, n_simulations=100)
        assert not r1.fan_chart["p50"].equals(r2.fan_chart["p50"])

    def test_final_month_percentiles_in_order(self):
        emp = _make_employees(20)
        r = run_monte_carlo(emp, annual_budget=2_000_000, n_simulations=500)
        assert r.final_month_p10 <= r.final_month_p50
        assert r.final_month_p50 <= r.final_month_p90

    def test_mean_between_p10_and_p90(self):
        emp = _make_employees(20)
        r = run_monte_carlo(emp, annual_budget=2_000_000, n_simulations=500)
        fc = r.fan_chart
        # Mean should generally lie between P10 and P90
        assert (fc["mean"] >= fc["p10"] * 0.8).all()
        assert (fc["mean"] <= fc["p90"] * 1.2).all()


# ===========================================================================
# Class: TestMonteCarloEdgeCases
# ===========================================================================

class TestMonteCarloEdgeCases:
    def test_single_employee(self):
        emp = _make_employees(1)
        result = run_monte_carlo(emp, annual_budget=200_000, n_simulations=100)
        assert isinstance(result, MonteCarloResult)

    def test_custom_horizon(self):
        emp = _make_employees(20)
        result = run_monte_carlo(emp, annual_budget=1_000_000, horizon_months=6,
                                 n_simulations=100)
        assert len(result.fan_chart) == 6

    def test_missing_cost_column(self):
        emp = _make_employees(10).drop(columns=["total_cost"])
        result = run_monte_carlo(emp, annual_budget=500_000, n_simulations=50)
        assert isinstance(result, MonteCarloResult)

    def test_attrition_scores_missing_employee_uses_default(self):
        emp = _make_employees(20)
        partial_atr = _make_attrition_scores(emp["employee_id"].tolist()[:5])
        result = run_monte_carlo(emp, annual_budget=2_000_000,
                                 attrition_result=partial_atr, n_simulations=100)
        assert isinstance(result, MonteCarloResult)

    def test_notes_list_is_list(self):
        emp = _make_employees(20)
        result = run_monte_carlo(emp, annual_budget=2_000_000, n_simulations=50)
        assert isinstance(result.notes, list)
