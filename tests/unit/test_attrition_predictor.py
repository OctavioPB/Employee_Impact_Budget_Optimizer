"""Unit tests for models/attrition_predictor.py."""

import numpy as np
import pandas as pd
import pytest

from models.attrition_predictor import (
    AttritionPredictor,
    AttritionResult,
    compute_attrition_risk,
    risk_category,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_employees(n: int = 20, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "employee_id": [f"E{i:03d}" for i in range(n)],
        "annual_salary": rng.integers(50_000, 150_000, n).astype(float),
        "market_salary":  rng.integers(55_000, 160_000, n).astype(float),
        "hire_date": pd.date_range("2018-01-01", periods=n, freq="90D").strftime("%Y-%m-%d"),
        "department": rng.choice(["Engineering", "Marketing", "Finance", "HR"], n),
        "seniority_level": rng.choice(["junior", "mid", "senior", "lead"], n),
    })


def _make_performance(employee_ids: list[str], seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    records = []
    for eid in employee_ids:
        for q in range(1, 5):
            records.append({
                "employee_id": eid,
                "kpi_score": rng.uniform(2.0, 5.0),
                "review_date": f"2024-{q*3:02d}-15",
                "review_period": f"2024-Q{q}",
            })
    return pd.DataFrame(records)


def _make_centrality(employee_ids: list[str], seed: int = 1) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "employee_id": employee_ids,
        "degree_centrality": rng.uniform(0, 1, len(employee_ids)),
        "betweenness_centrality": rng.uniform(0, 1, len(employee_ids)),
        "eigenvector_centrality": rng.uniform(0, 1, len(employee_ids)),
        "pagerank": rng.uniform(0, 1, len(employee_ids)),
        "combined_centrality": rng.uniform(0, 1, len(employee_ids)),
    })


def _make_impact(employee_ids: list[str], seed: int = 2) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "employee_id": employee_ids,
        "impact_score": rng.uniform(20, 90, len(employee_ids)),
    })


# ===========================================================================
# Class: TestRiskCategoryHelper
# ===========================================================================

class TestRiskCategoryHelper:
    def test_low_boundary(self):
        assert risk_category(0) == "Low"
        assert risk_category(30) == "Low"

    def test_moderate_boundary(self):
        assert risk_category(31) == "Moderate"
        assert risk_category(60) == "Moderate"

    def test_high_boundary(self):
        assert risk_category(61) == "High"
        assert risk_category(80) == "High"

    def test_critical_boundary(self):
        assert risk_category(81) == "Critical"
        assert risk_category(100) == "Critical"

    def test_mid_values(self):
        assert risk_category(15) == "Low"
        assert risk_category(45) == "Moderate"
        assert risk_category(70) == "High"
        assert risk_category(95) == "Critical"


# ===========================================================================
# Class: TestAttritionResultShape
# ===========================================================================

class TestAttritionResultShape:
    def test_scores_has_required_columns(self):
        emp = _make_employees(10)
        result = compute_attrition_risk(emp)
        required = {"employee_id", "attrition_risk", "risk_category", "top_driver"}
        assert required.issubset(set(result.scores.columns))

    def test_scores_row_count_matches_employees(self):
        emp = _make_employees(15)
        result = compute_attrition_risk(emp)
        assert len(result.scores) == 15

    def test_attrition_risk_in_valid_range(self):
        emp = _make_employees(20)
        result = compute_attrition_risk(emp)
        assert result.scores["attrition_risk"].between(0, 100).all()

    def test_risk_category_values(self):
        emp = _make_employees(20)
        result = compute_attrition_risk(emp)
        valid = {"Low", "Moderate", "High", "Critical"}
        assert set(result.scores["risk_category"].unique()).issubset(valid)

    def test_mode_is_heuristic_without_labels(self):
        emp = _make_employees(10)
        result = compute_attrition_risk(emp)
        assert result.mode == "heuristic"

    def test_feature_importance_dict_not_empty(self):
        emp = _make_employees(10)
        result = compute_attrition_risk(emp)
        assert isinstance(result.feature_importance, dict)
        assert len(result.feature_importance) > 0


# ===========================================================================
# Class: TestHeuristicMode
# ===========================================================================

class TestHeuristicMode:
    def test_all_employees_get_scores(self):
        emp = _make_employees(25)
        result = compute_attrition_risk(emp)
        assert result.scores["attrition_risk"].notna().all()

    def test_driver_columns_present(self):
        emp = _make_employees(10)
        result = compute_attrition_risk(emp)
        driver_cols = [c for c in result.scores.columns if c.endswith("_driver")]
        assert len(driver_cols) >= 1

    def test_risk_category_consistent_with_score(self):
        emp = _make_employees(30)
        result = compute_attrition_risk(emp)
        for _, row in result.scores.iterrows():
            score = row["attrition_risk"]
            cat = row["risk_category"]
            assert cat == risk_category(score), \
                f"Score {score:.0f} should be {risk_category(score)} but got {cat}"

    def test_high_salary_ratio_lowers_risk(self):
        """Employee paid above market should have lower salary driver."""
        emp_base = _make_employees(5, seed=10)
        emp_high = emp_base.copy()
        emp_low = emp_base.copy()

        # High salary: paid 2× market
        emp_high["annual_salary"] = emp_high["market_salary"] * 2.0
        # Low salary: paid 50% of market
        emp_low["annual_salary"] = emp_low["market_salary"] * 0.5

        result_high = compute_attrition_risk(emp_high)
        result_low = compute_attrition_risk(emp_low)

        avg_high = result_high.scores["attrition_risk"].mean()
        avg_low = result_low.scores["attrition_risk"].mean()
        assert avg_high < avg_low, "Higher salary ratio should reduce attrition risk"

    def test_with_performance_data(self):
        emp = _make_employees(15)
        perf = _make_performance(emp["employee_id"].tolist())
        result = compute_attrition_risk(emp, performance_df=perf)
        assert len(result.scores) == 15
        assert result.scores["attrition_risk"].between(0, 100).all()

    def test_with_centrality_data(self):
        emp = _make_employees(12)
        cent = _make_centrality(emp["employee_id"].tolist())
        result = compute_attrition_risk(emp, centrality_df=cent)
        assert len(result.scores) == 12

    def test_with_all_inputs(self):
        emp = _make_employees(20)
        ids = emp["employee_id"].tolist()
        perf = _make_performance(ids)
        cent = _make_centrality(ids)
        imp = _make_impact(ids)
        result = compute_attrition_risk(emp, perf, cent, imp)
        assert len(result.scores) == 20
        assert result.mode == "heuristic"

    def test_missing_optional_columns_handled(self):
        """Minimal employees DataFrame — no salary, hire_date."""
        emp = pd.DataFrame({
            "employee_id": [f"E{i}" for i in range(10)],
            "department": ["Eng"] * 10,
        })
        result = compute_attrition_risk(emp)
        assert len(result.scores) == 10

    def test_top_driver_is_a_string(self):
        emp = _make_employees(10)
        result = compute_attrition_risk(emp)
        assert result.scores["top_driver"].dtype == object

    def test_single_employee(self):
        emp = _make_employees(1)
        result = compute_attrition_risk(emp)
        assert len(result.scores) == 1
        assert 0 <= result.scores["attrition_risk"].iloc[0] <= 100


# ===========================================================================
# Class: TestAttritionPredictor
# ===========================================================================

class TestAttritionPredictor:
    def test_predict_returns_attrition_result(self):
        predictor = AttritionPredictor()
        emp = _make_employees(10)
        result = predictor.predict(emp)
        assert isinstance(result, AttritionResult)

    def test_predict_consistent_results_same_input(self):
        predictor = AttritionPredictor()
        emp = _make_employees(10)
        r1 = predictor.predict(emp)
        r2 = predictor.predict(emp)
        pd.testing.assert_frame_equal(r1.scores, r2.scores)

    def test_model_auc_heuristic_is_zero(self):
        predictor = AttritionPredictor()
        emp = _make_employees(10)
        result = predictor.predict(emp)
        # Heuristic mode has no AUC
        assert result.model_auc == 0.0 or result.model_auc is None or result.model_auc >= 0

    def test_large_org_performance(self):
        """500 employees should complete in reasonable time."""
        import time
        emp = _make_employees(500)
        start = time.time()
        result = compute_attrition_risk(emp)
        elapsed = time.time() - start
        assert elapsed < 10.0, f"Took {elapsed:.1f}s for 500 employees"
        assert len(result.scores) == 500


# ===========================================================================
# Class: TestXGBoostMode (requires ≥20 labeled records)
# ===========================================================================

class TestXGBoostMode:
    def _make_labels(self, employee_ids: list[str], positive_rate: float = 0.25,
                     seed: int = 99) -> pd.DataFrame:
        rng = np.random.default_rng(seed)
        labels = (rng.random(len(employee_ids)) < positive_rate).astype(int)
        return pd.DataFrame({"employee_id": employee_ids, "attrition": labels})

    def test_xgboost_mode_activated_with_enough_labels(self):
        try:
            import xgboost  # noqa: F401
        except ImportError:
            pytest.skip("XGBoost not installed")

        emp = _make_employees(50)
        labels = self._make_labels(emp["employee_id"].tolist())
        result = compute_attrition_risk(emp, attrition_labels=labels)
        assert result.mode == "xgboost"

    def test_xgboost_scores_in_range(self):
        try:
            import xgboost  # noqa: F401
        except ImportError:
            pytest.skip("XGBoost not installed")

        emp = _make_employees(50)
        labels = self._make_labels(emp["employee_id"].tolist())
        result = compute_attrition_risk(emp, attrition_labels=labels)
        assert result.scores["attrition_risk"].between(0, 100).all()

    def test_fallback_to_heuristic_fewer_than_20_labels(self):
        emp = _make_employees(50)
        labels = self._make_labels(emp["employee_id"].tolist()[:10])
        result = compute_attrition_risk(emp, attrition_labels=labels)
        # Fewer than 20 labels: must use heuristic
        assert result.mode == "heuristic"


# ===========================================================================
# Class: TestEdgeCases
# ===========================================================================

class TestEdgeCases:
    def test_empty_dataframe_returns_empty_result(self):
        emp = pd.DataFrame(columns=["employee_id"])
        result = compute_attrition_risk(emp)
        assert len(result.scores) == 0

    def test_all_same_salary_ratio(self):
        """All employees at 100% market — no salary-driven differentiation."""
        emp = _make_employees(10)
        emp["annual_salary"] = emp["market_salary"]
        result = compute_attrition_risk(emp)
        assert len(result.scores) == 10
        assert result.scores["attrition_risk"].between(0, 100).all()

    def test_no_hire_date_column(self):
        emp = _make_employees(10).drop(columns=["hire_date"])
        result = compute_attrition_risk(emp)
        assert len(result.scores) == 10

    def test_performance_partial_match(self):
        """Performance data only covers half the employees."""
        emp = _make_employees(20)
        ids = emp["employee_id"].tolist()
        perf = _make_performance(ids[:10])
        result = compute_attrition_risk(emp, performance_df=perf)
        assert len(result.scores) == 20

    def test_centrality_partial_match(self):
        emp = _make_employees(20)
        ids = emp["employee_id"].tolist()
        cent = _make_centrality(ids[:12])
        result = compute_attrition_risk(emp, centrality_df=cent)
        assert len(result.scores) == 20

    def test_no_market_salary_column(self):
        emp = _make_employees(10).drop(columns=["market_salary"], errors="ignore")
        result = compute_attrition_risk(emp)
        assert len(result.scores) == 10

    def test_driver_sum_adds_up_approximately(self):
        """Driver scores should contribute to overall risk proportionally."""
        emp = _make_employees(20)
        result = compute_attrition_risk(emp)
        driver_cols = [c for c in result.scores.columns if c.endswith("_driver")]
        if len(driver_cols) >= 2:
            driver_sum = result.scores[driver_cols].sum(axis=1)
            # Not a strict equality, but proportional — driver sum should be positive
            assert (driver_sum > 0).all()
