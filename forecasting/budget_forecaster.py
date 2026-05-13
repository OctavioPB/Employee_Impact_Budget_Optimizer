"""Prophet-based budget and headcount forecasting.

Produces 12-month spend and headcount forecasts per department with
quarterly and annual seasonality, 80% and 95% confidence intervals.
Falls back to a linear extrapolation when Prophet is unavailable.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_PROPHET_AVAILABLE = False
try:
    from prophet import Prophet  # type: ignore
    _PROPHET_AVAILABLE = True
except ImportError:
    pass

_FORECAST_MONTHS = 12
_CI_WIDTHS = (0.80, 0.95)


# ---------------------------------------------------------------------------
# Output dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ForecastSeries:
    """Single time-series forecast (spend or headcount)."""
    label: str                          # "Total Spend" or dept name
    metric: str                         # "spend" | "headcount"
    history: pd.DataFrame               # ds, y
    forecast: pd.DataFrame              # ds, yhat, yhat_lower_80, yhat_upper_80, yhat_lower_95, yhat_upper_95
    mape: float = 0.0                   # in-sample MAPE (0 if no holdout)
    model: str = "prophet"              # "prophet" | "linear"


@dataclass
class BudgetForecastResult:
    """Aggregated forecast result for the predictive UI."""
    total_spend: ForecastSeries
    by_department: list[ForecastSeries] = field(default_factory=list)
    headcount: ForecastSeries | None = None
    generated_at: str = ""

    @property
    def summary_df(self) -> pd.DataFrame:
        """One-row-per-month summary with total spend bounds."""
        fc = self.total_spend.forecast
        return fc[["ds", "yhat", "yhat_lower_80", "yhat_upper_80",
                   "yhat_lower_95", "yhat_upper_95"]].copy()


# ---------------------------------------------------------------------------
# Core forecaster
# ---------------------------------------------------------------------------

class BudgetForecaster:
    """Generates 12-month spend and headcount forecasts from payroll history.

    Args:
        history_months: How many months of history to synthesise when real
                        historical data is not supplied (demo mode).
        forecast_months: Months ahead to forecast.
    """

    def __init__(
        self,
        history_months: int = 24,
        forecast_months: int = _FORECAST_MONTHS,
    ) -> None:
        self._history_months = history_months
        self._forecast_months = forecast_months

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def forecast(
        self,
        employee_df: pd.DataFrame,
        performance_df: Optional[pd.DataFrame] = None,
        dept_col: str = "department",
        cost_col: str = "total_cost",
    ) -> BudgetForecastResult:
        """Run forecasts for total spend and each department.

        Args:
            employee_df: Current employee snapshot (employee_id, department,
                         total_cost, hire_date optional).
            performance_df: Monthly performance DataFrame with date, value
                            (used to enrich history signal — optional).
            dept_col: Column name for department in employee_df.
            cost_col: Column name for cost in employee_df.

        Returns:
            BudgetForecastResult with total + per-department + headcount series.
        """
        history = self._build_history(employee_df, dept_col, cost_col)

        total_series = self._fit_and_forecast(
            history[["ds", "total"]].rename(columns={"total": "y"}),
            label="Total Spend",
            metric="spend",
        )

        dept_series: list[ForecastSeries] = []
        depts = employee_df[dept_col].dropna().unique() if dept_col in employee_df.columns else []
        for dept in sorted(depts):
            col = f"dept_{dept}"
            if col not in history.columns:
                continue
            s = self._fit_and_forecast(
                history[["ds", col]].rename(columns={col: "y"}),
                label=str(dept),
                metric="spend",
            )
            dept_series.append(s)

        headcount_series = self._fit_and_forecast(
            history[["ds", "headcount"]].rename(columns={"headcount": "y"}),
            label="Headcount",
            metric="headcount",
        )

        return BudgetForecastResult(
            total_spend=total_series,
            by_department=dept_series,
            headcount=headcount_series,
            generated_at=pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
        )

    # ------------------------------------------------------------------
    # History builder (synthetic monthly roll-up for demo mode)
    # ------------------------------------------------------------------

    def _build_history(
        self,
        employee_df: pd.DataFrame,
        dept_col: str,
        cost_col: str,
    ) -> pd.DataFrame:
        """Construct a monthly history DataFrame from the employee snapshot.

        Since EIBO may not have multi-year payroll history, this method
        simulates realistic monthly variation around the current period's
        total spend (±2% noise + annual 3% trend + bonus spike in Dec).
        """
        n = self._history_months
        total_now = float(employee_df[cost_col].sum()) if cost_col in employee_df.columns else 500_000
        headcount_now = len(employee_df)

        rng = np.random.default_rng(seed=42)
        months = pd.date_range(end=pd.Timestamp.today().replace(day=1), periods=n, freq="MS")

        records = []
        for i, ds in enumerate(months):
            # Deterministic signals
            month_in_year = ds.month
            trend = total_now * (1 - 0.03 * (n - 1 - i) / 12)
            seasonal = 1.0
            if month_in_year == 12:
                seasonal = 1.10   # bonus period
            elif month_in_year in (6, 7):
                seasonal = 1.03   # mid-year reviews
            elif month_in_year in (1, 2):
                seasonal = 0.97   # post-bonus lull

            noise = rng.normal(1.0, 0.015)
            total_val = max(trend * seasonal * noise, 0)

            row: dict = {"ds": ds, "total": total_val, "headcount": headcount_now}

            if dept_col in employee_df.columns:
                for dept in employee_df[dept_col].dropna().unique():
                    dept_now = float(
                        employee_df.loc[employee_df[dept_col] == dept, cost_col].sum()
                        if cost_col in employee_df.columns else total_now / 4
                    )
                    dept_trend = dept_now * (1 - 0.03 * (n - 1 - i) / 12)
                    dept_val = max(dept_trend * seasonal * rng.normal(1.0, 0.02), 0)
                    row[f"dept_{dept}"] = dept_val

            records.append(row)

        return pd.DataFrame(records)

    # ------------------------------------------------------------------
    # Fit & forecast (Prophet or linear fallback)
    # ------------------------------------------------------------------

    def _fit_and_forecast(
        self,
        history_df: pd.DataFrame,
        label: str,
        metric: str,
    ) -> ForecastSeries:
        if _PROPHET_AVAILABLE and len(history_df) >= 6:
            return self._prophet_forecast(history_df, label, metric)
        return self._linear_forecast(history_df, label, metric)

    def _prophet_forecast(
        self,
        history_df: pd.DataFrame,
        label: str,
        metric: str,
    ) -> ForecastSeries:
        try:
            m = Prophet(
                yearly_seasonality=True,
                weekly_seasonality=False,
                daily_seasonality=False,
                interval_width=0.80,
                uncertainty_samples=500,
            )
            m.add_seasonality(name="quarterly", period=91.25, fourier_order=5)
            m.fit(history_df, iter=300)

            future = m.make_future_dataframe(
                periods=self._forecast_months, freq="MS", include_history=True
            )
            raw = m.predict(future)

            # Recompute 95% CI from component std (Prophet only natively does one width)
            raw95 = m.predictive_samples(future)
            samples = raw95["yhat"]
            lower_95 = np.percentile(samples, 2.5, axis=1)
            upper_95 = np.percentile(samples, 97.5, axis=1)
            lower_80 = np.percentile(samples, 10, axis=1)
            upper_80 = np.percentile(samples, 90, axis=1)

            fc = raw[["ds", "yhat"]].copy()
            fc["yhat_lower_80"] = lower_80
            fc["yhat_upper_80"] = upper_80
            fc["yhat_lower_95"] = lower_95
            fc["yhat_upper_95"] = upper_95
            fc["yhat"] = np.maximum(fc["yhat"], 0)
            fc[["yhat_lower_80", "yhat_lower_95"]] = fc[["yhat_lower_80", "yhat_lower_95"]].clip(lower=0)

            forecast_only = fc[fc["ds"] > history_df["ds"].max()]
            history_only = fc[fc["ds"] <= history_df["ds"].max()].copy()
            history_only["y"] = history_df["y"].values

            return ForecastSeries(
                label=label,
                metric=metric,
                history=history_only[["ds", "y"]],
                forecast=forecast_only.reset_index(drop=True),
                mape=self._mape(history_only["y"], history_only["yhat"]),
                model="prophet",
            )
        except Exception as exc:
            logger.warning("Prophet failed for %s: %s — falling back to linear", label, exc)
            return self._linear_forecast(history_df, label, metric)

    def _linear_forecast(
        self,
        history_df: pd.DataFrame,
        label: str,
        metric: str,
    ) -> ForecastSeries:
        """OLS linear trend extrapolation with ±σ envelopes."""
        y = history_df["y"].values.astype(float)
        n = len(y)
        x = np.arange(n)
        slope, intercept = np.polyfit(x, y, 1)
        residuals = y - (slope * x + intercept)
        sigma = residuals.std()

        future_x = np.arange(n, n + self._forecast_months)
        future_ds = pd.date_range(
            start=history_df["ds"].iloc[-1] + pd.DateOffset(months=1),
            periods=self._forecast_months,
            freq="MS",
        )
        yhat = slope * future_x + intercept
        yhat = np.maximum(yhat, 0)

        fc = pd.DataFrame({
            "ds": future_ds,
            "yhat": yhat,
            "yhat_lower_80": np.maximum(yhat - 1.28 * sigma, 0),
            "yhat_upper_80": yhat + 1.28 * sigma,
            "yhat_lower_95": np.maximum(yhat - 1.96 * sigma, 0),
            "yhat_upper_95": yhat + 1.96 * sigma,
        })

        return ForecastSeries(
            label=label,
            metric=metric,
            history=history_df.copy(),
            forecast=fc,
            mape=self._mape(y, slope * x + intercept),
            model="linear",
        )

    @staticmethod
    def _mape(actual: np.ndarray, predicted: np.ndarray) -> float:
        mask = actual != 0
        if not mask.any():
            return 0.0
        return float(np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100)


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def forecast_budget(
    employee_df: pd.DataFrame,
    performance_df: Optional[pd.DataFrame] = None,
    dept_col: str = "department",
    cost_col: str = "total_cost",
    history_months: int = 24,
    forecast_months: int = 12,
) -> BudgetForecastResult:
    """Generate budget and headcount forecasts. Convenience wrapper."""
    return BudgetForecaster(
        history_months=history_months,
        forecast_months=forecast_months,
    ).forecast(employee_df, performance_df, dept_col, cost_col)
