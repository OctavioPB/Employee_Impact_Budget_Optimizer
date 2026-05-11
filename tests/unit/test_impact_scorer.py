"""Unit tests for models/impact_scorer.py."""

import numpy as np
import pandas as pd
import pytest

from models.impact_scorer import ImpactScorer, ScoringResult, compute_impact_scores


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_employees(n: int = 10) -> pd.DataFrame:
    today = pd.Timestamp.today()
    return pd.DataFrame({
        "employee_id": [f"e{i}" for i in range(n)],
        "department": ["Engineering"] * (n // 2) + ["Product"] * (n - n // 2),
        "team_id": [f"t{i % 3}" for i in range(n)],
        "annual_salary": [80_000 + i * 10_000 for i in range(n)],
        "annual_benefits": [24_000 + i * 3_000 for i in range(n)],
        "seniority_level": (["mid"] * 4 + ["senior"] * 3 + ["lead"] * 2 + ["junior"]) if n == 10
                           else ["mid"] * n,
        "hire_date": [(today - pd.Timedelta(days=365 * (1 + i % 5))).date().isoformat()
                      for i in range(n)],
    })


def _make_performance(employees: pd.DataFrame, n_quarters: int = 4) -> pd.DataFrame:
    rows = []
    base_date = pd.Timestamp("2024-01-01")
    for i, (_, emp) in enumerate(employees.iterrows()):
        for q in range(n_quarters):
            rows.append({
                "employee_id": emp["employee_id"],
                "kpi_score": 3.0 + (i % 3) * 0.5 + (q * 0.05),
                "review_date": (base_date + pd.DateOffset(months=q * 3)).date().isoformat(),
                "review_period": f"2024-Q{q+1}",
            })
    return pd.DataFrame(rows)


def _make_centrality(employees: pd.DataFrame) -> pd.DataFrame:
    n = len(employees)
    return pd.DataFrame({
        "employee_id": employees["employee_id"].tolist(),
        "degree_centrality": np.linspace(0.1, 0.9, n),
        "betweenness_centrality": np.linspace(0.0, 0.5, n),
        "eigenvector_centrality": np.linspace(0.1, 0.8, n),
        "pagerank": np.linspace(0.05, 0.15, n),
        "combined_centrality": np.linspace(0.1, 0.7, n),
    })


def _make_skills() -> pd.DataFrame:
    return pd.DataFrame({
        "skill_id": ["s1", "s2", "s3"],
        "skill_name": ["Python", "Kubernetes", "Communication"],
        "category": ["technical", "technical", "soft"],
        "is_critical": [False, True, False],
        "market_scarcity": [0.20, 0.50, 0.15],
    })


def _make_employee_skills(employees: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for i, eid in enumerate(employees["employee_id"]):
        skill = ["s1", "s2", "s3"][i % 3]
        rows.append({
            "employee_id": eid,
            "skill_id": skill,
            "proficiency": 0.5 + (i % 4) * 0.1,
            "is_primary": True,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# ImpactScorer — smoke test
# ---------------------------------------------------------------------------

class TestImpactScorerSmoke:
    def test_instantiation(self):
        scorer = ImpactScorer()
        assert scorer is not None

    def test_score_returns_scoring_result(self):
        employees = _make_employees()
        performance = _make_performance(employees)
        centrality = _make_centrality(employees)
        skills = _make_skills()
        emp_skills = _make_employee_skills(employees)

        scorer = ImpactScorer()
        result = scorer.score(employees, performance, centrality, emp_skills, skills)
        assert isinstance(result, ScoringResult)

    def test_heuristic_mode_selected_without_labels(self):
        employees = _make_employees()
        performance = _make_performance(employees)
        centrality = _make_centrality(employees)
        skills = _make_skills()
        emp_skills = _make_employee_skills(employees)

        result = ImpactScorer().score(employees, performance, centrality, emp_skills, skills)
        assert result.mode == "heuristic"


# ---------------------------------------------------------------------------
# Score range and structure
# ---------------------------------------------------------------------------

class TestScoreRange:
    def _run(self, n: int = 10) -> ScoringResult:
        employees = _make_employees(n)
        return compute_impact_scores(
            employees_df=employees,
            performance_df=_make_performance(employees),
            centrality_df=_make_centrality(employees),
            employee_skills_df=_make_employee_skills(employees),
            skills_df=_make_skills(),
        )

    def test_impact_score_in_0_100(self):
        result = self._run()
        scores = result.scores["impact_score"]
        assert (scores >= 0).all() and (scores <= 100).all()

    def test_all_employees_receive_a_score(self):
        result = self._run(n=10)
        assert len(result.scores) == 10

    def test_no_nan_in_impact_score(self):
        result = self._run()
        assert result.scores["impact_score"].notna().all()

    def test_components_sum_to_impact_score(self):
        result = self._run()
        cols = ["kpi_contribution", "network_contribution",
                "skills_contribution", "cost_contribution"]
        component_sum = result.scores[cols].sum(axis=1)
        pd.testing.assert_series_equal(
            component_sum.round(1),
            result.scores["impact_score"].round(1),
            check_names=False,
        )

    def test_components_all_nonnegative(self):
        result = self._run()
        for col in ["kpi_contribution", "network_contribution",
                    "skills_contribution", "cost_contribution"]:
            assert (result.scores[col] >= 0).all(), f"Negative values in {col}"

    def test_confidence_in_unit_range(self):
        result = self._run()
        conf = result.scores["confidence"]
        assert (conf >= 0.0).all() and (conf <= 1.0).all()

    def test_feature_importance_empty_for_heuristic(self):
        result = self._run()
        assert result.mode == "heuristic"
        assert result.feature_importance == {}
        assert result.cv_accuracy == 0.0


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_no_performance_data(self):
        employees = _make_employees(5)
        result = compute_impact_scores(
            employees_df=employees,
            performance_df=pd.DataFrame(
                columns=["employee_id", "kpi_score", "review_date", "review_period"]
            ),
            centrality_df=_make_centrality(employees),
            employee_skills_df=_make_employee_skills(employees),
            skills_df=_make_skills(),
        )
        assert len(result.scores) == 5
        assert result.scores["impact_score"].between(0, 100).all()

    def test_no_skills_data(self):
        employees = _make_employees(5)
        result = compute_impact_scores(
            employees_df=employees,
            performance_df=_make_performance(employees),
            centrality_df=_make_centrality(employees),
            employee_skills_df=pd.DataFrame(
                columns=["employee_id", "skill_id", "proficiency", "is_primary"]
            ),
            skills_df=pd.DataFrame(
                columns=["skill_id", "skill_name", "category", "is_critical", "market_scarcity"]
            ),
        )
        assert len(result.scores) == 5
        assert result.scores["impact_score"].between(0, 100).all()

    def test_all_zero_network_centrality(self):
        employees = _make_employees(5)
        centrality = pd.DataFrame({
            "employee_id": employees["employee_id"].tolist(),
            "degree_centrality": [0.0] * 5,
            "betweenness_centrality": [0.0] * 5,
            "eigenvector_centrality": [0.0] * 5,
            "pagerank": [0.0] * 5,
            "combined_centrality": [0.0] * 5,
        })
        result = compute_impact_scores(
            employees_df=employees,
            performance_df=_make_performance(employees),
            centrality_df=centrality,
            employee_skills_df=_make_employee_skills(employees),
            skills_df=_make_skills(),
        )
        assert result.scores["network_contribution"].sum() == pytest.approx(0.0)
        # Other components still produce non-zero scores
        assert result.scores["impact_score"].sum() > 0

    def test_single_employee(self):
        employees = _make_employees(1)
        result = compute_impact_scores(
            employees_df=employees,
            performance_df=_make_performance(employees),
            centrality_df=_make_centrality(employees),
            employee_skills_df=_make_employee_skills(employees),
            skills_df=_make_skills(),
        )
        assert len(result.scores) == 1
        assert 0 <= result.scores["impact_score"].iloc[0] <= 100


# ---------------------------------------------------------------------------
# Random Forest mode
# ---------------------------------------------------------------------------

class TestRFMode:
    def test_rf_mode_when_labels_provided(self):
        employees = _make_employees(30)
        performance = _make_performance(employees)
        centrality = _make_centrality(employees)
        skills = _make_skills()
        emp_skills = _make_employee_skills(employees)

        labels = pd.Series(
            np.random.default_rng(42).integers(0, 2, size=30),
            index=employees["employee_id"],
        )

        scorer = ImpactScorer(random_state=42)
        result = scorer.score(employees, performance, centrality, emp_skills, skills, labels)

        assert result.mode == "random_forest"
        assert result.cv_accuracy > 0.0
        assert len(result.feature_importance) > 0

    def test_rf_scores_in_0_100(self):
        employees = _make_employees(30)
        performance = _make_performance(employees)
        centrality = _make_centrality(employees)
        skills = _make_skills()
        emp_skills = _make_employee_skills(employees)

        labels = pd.Series(
            np.random.default_rng(0).integers(0, 2, size=30),
            index=employees["employee_id"],
        )

        result = ImpactScorer(random_state=0).score(
            employees, performance, centrality, emp_skills, skills, labels
        )
        assert result.scores["impact_score"].between(0, 100).all()

    def test_fewer_than_20_labels_falls_back_to_heuristic(self):
        employees = _make_employees(15)
        performance = _make_performance(employees)
        centrality = _make_centrality(employees)
        skills = _make_skills()
        emp_skills = _make_employee_skills(employees)

        labels = pd.Series(
            np.ones(15, dtype=int),
            index=employees["employee_id"],
        )

        result = ImpactScorer().score(
            employees, performance, centrality, emp_skills, skills, labels
        )
        assert result.mode == "heuristic"
