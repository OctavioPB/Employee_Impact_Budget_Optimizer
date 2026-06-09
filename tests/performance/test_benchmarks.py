"""Performance benchmark tests for EIBO critical paths.

Tests measure actual wall-clock time against defined thresholds.
All thresholds are intentionally generous to avoid flakiness on CI.

Run with:
    pytest tests/performance/ -v --tb=short
"""

from __future__ import annotations

import time

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _elapsed(fn, *args, **kwargs) -> tuple:
    """Return (result, elapsed_seconds)."""
    t0 = time.perf_counter()
    result = fn(*args, **kwargs)
    return result, time.perf_counter() - t0


# ---------------------------------------------------------------------------
# Fixtures: pre-generated org data (class-scoped for speed)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def small_org():
    from demo_data.generator import DemoGenerator
    return DemoGenerator("A", "small", seed=42).generate()


@pytest.fixture(scope="module")
def small_centrality(small_org):
    from models.network_analysis import build_graph, compute_centrality_metrics
    G = build_graph(small_org.collaboration)
    # compute_centrality_metrics returns a plain DataFrame
    return compute_centrality_metrics(G, small_org.employees)


@pytest.fixture(scope="module")
def small_scores(small_org, small_centrality):
    from models.impact_scorer import ImpactScorer
    scorer = ImpactScorer(random_state=42)
    return scorer.score(
        employees_df=small_org.employees,
        performance_df=small_org.performance,
        centrality_df=small_centrality,  # already a DataFrame
        employee_skills_df=small_org.employee_skills,
        skills_df=small_org.skills,
    )


# ---------------------------------------------------------------------------
# 1. Demo data generation benchmarks
# ---------------------------------------------------------------------------

class TestDemoGeneratorPerformance:
    _THRESHOLD_SMALL_S  = 5.0   # small org ≤ 5 seconds
    _THRESHOLD_MEDIUM_S = 30.0  # medium org ≤ 30 seconds

    def test_small_org_generation_speed(self):
        from demo_data.generator import DemoGenerator
        _, elapsed = _elapsed(DemoGenerator("A", "small", seed=42).generate)
        assert elapsed < self._THRESHOLD_SMALL_S, \
            f"Small org generation took {elapsed:.2f}s (threshold {self._THRESHOLD_SMALL_S}s)"

    def test_small_org_reproducible(self):
        from demo_data.generator import DemoGenerator
        org1 = DemoGenerator("A", "small", seed=42).generate()
        org2 = DemoGenerator("A", "small", seed=42).generate()
        assert len(org1.employees) == len(org2.employees)
        assert list(org1.employees["employee_id"]) == list(org2.employees["employee_id"])

    def test_scenario_b_generation_speed(self):
        from demo_data.generator import DemoGenerator
        _, elapsed = _elapsed(DemoGenerator("B", "small", seed=42).generate)
        assert elapsed < self._THRESHOLD_SMALL_S

    def test_scenario_c_generation_speed(self):
        from demo_data.generator import DemoGenerator
        _, elapsed = _elapsed(DemoGenerator("C", "small", seed=42).generate)
        assert elapsed < self._THRESHOLD_SMALL_S


# ---------------------------------------------------------------------------
# 2. Network analysis benchmarks
# ---------------------------------------------------------------------------

class TestNetworkAnalysisPerformance:
    _THRESHOLD_GRAPH_S    = 3.0
    _THRESHOLD_METRICS_S  = 5.0

    def test_graph_build_speed(self, small_org):
        from models.network_analysis import build_graph
        _, elapsed = _elapsed(build_graph, small_org.collaboration)
        assert elapsed < self._THRESHOLD_GRAPH_S, \
            f"Graph build took {elapsed:.2f}s (threshold {self._THRESHOLD_GRAPH_S}s)"

    def test_centrality_metrics_speed(self, small_org):
        from models.network_analysis import build_graph, compute_centrality_metrics
        G = build_graph(small_org.collaboration)
        _, elapsed = _elapsed(compute_centrality_metrics, G, small_org.employees)
        assert elapsed < self._THRESHOLD_METRICS_S, \
            f"Centrality metrics took {elapsed:.2f}s (threshold {self._THRESHOLD_METRICS_S}s)"

    def test_metrics_output_size(self, small_org, small_centrality):
        # small_centrality is the centrality DataFrame directly
        assert len(small_centrality) == len(small_org.employees)


# ---------------------------------------------------------------------------
# 3. Impact scoring benchmarks
# ---------------------------------------------------------------------------

class TestImpactScorerPerformance:
    _THRESHOLD_SCORE_S = 5.0

    def test_heuristic_scoring_speed(self, small_org, small_centrality):
        from models.impact_scorer import ImpactScorer
        scorer = ImpactScorer(random_state=42)
        _, elapsed = _elapsed(
            scorer.score,
            employees_df=small_org.employees,
            performance_df=small_org.performance,
            centrality_df=small_centrality,  # plain DataFrame
            employee_skills_df=small_org.employee_skills,
            skills_df=small_org.skills,
        )
        assert elapsed < self._THRESHOLD_SCORE_S, \
            f"Impact scoring took {elapsed:.2f}s (threshold {self._THRESHOLD_SCORE_S}s)"

    def test_all_scores_in_range(self, small_scores):
        assert small_scores.scores["impact_score"].between(0, 100).all()

    def test_no_null_scores(self, small_scores):
        assert not small_scores.scores["impact_score"].isna().any()

    def test_score_distribution_is_spread(self, small_scores):
        std = small_scores.scores["impact_score"].std()
        assert std > 1.0, f"Impact scores have suspiciously low variance: std={std:.2f}"


# ---------------------------------------------------------------------------
# 4. ILP solver benchmarks
# ---------------------------------------------------------------------------

class TestILPSolverPerformance:
    _THRESHOLD_SOLVE_S = 10.0  # 10s for small org

    def test_solve_70pct_budget_speed(self, small_org, small_scores):
        from optimization_engine.constraints import ConstraintConfig
        from optimization_engine.ilp_solver import solve
        current_spend = (
            small_org.employees["annual_salary"] + small_org.employees["annual_benefits"]
        ).sum()
        config = ConstraintConfig(
            require_leadership_per_team=False,
            require_critical_skills=False,
            solver_msg=False,
        )
        _, elapsed = _elapsed(
            solve, small_org.employees,
            current_spend * 0.70, small_scores.scores, {}, config
        )
        assert elapsed < self._THRESHOLD_SOLVE_S, \
            f"ILP solve took {elapsed:.2f}s (threshold {self._THRESHOLD_SOLVE_S}s)"

    def test_solve_returns_valid_result(self, small_org, small_scores):
        from optimization_engine.constraints import ConstraintConfig
        from optimization_engine.ilp_solver import solve
        current_spend = (
            small_org.employees["annual_salary"] + small_org.employees["annual_benefits"]
        ).sum()
        config = ConstraintConfig(
            require_leadership_per_team=False,
            require_critical_skills=False,
            solver_msg=False,
        )
        result = solve(small_org.employees,
                       budget_target=current_spend * 0.70,
                       impact_scores=small_scores.scores,
                       critical_skill_holders={},
                       constraint_config=config)
        assert result.status in ("Optimal", "Infeasible", "Timeout")
        assert result.n_total == len(small_org.employees)

    def test_solve_100pct_budget_is_fast(self, small_org, small_scores):
        from optimization_engine.constraints import ConstraintConfig
        from optimization_engine.ilp_solver import solve
        full_spend = (
            small_org.employees["annual_salary"] + small_org.employees["annual_benefits"]
        ).sum()
        config = ConstraintConfig(
            require_leadership_per_team=False,
            require_critical_skills=False,
            solver_msg=False,
        )
        _, elapsed = _elapsed(
            solve, small_org.employees, full_spend, small_scores.scores, {}, config
        )
        assert elapsed < self._THRESHOLD_SOLVE_S


# ---------------------------------------------------------------------------
# 5. Attrition predictor benchmarks
# ---------------------------------------------------------------------------

class TestAttritionPredictorPerformance:
    _THRESHOLD_PREDICT_S = 5.0

    def test_heuristic_prediction_speed(self, small_org, small_scores):
        from models.attrition_predictor import AttritionPredictor
        predictor = AttritionPredictor()
        _, elapsed = _elapsed(
            predictor.predict,
            employees_df=small_org.employees,
            performance_df=small_org.performance,
            impact_scores_df=small_scores.scores,
        )
        assert elapsed < self._THRESHOLD_PREDICT_S, \
            f"Attrition prediction took {elapsed:.2f}s (threshold {self._THRESHOLD_PREDICT_S}s)"

    def test_all_predictions_in_range(self, small_org, small_scores):
        from models.attrition_predictor import AttritionPredictor
        predictor = AttritionPredictor()
        result = predictor.predict(
            employees_df=small_org.employees,
            performance_df=small_org.performance,
            impact_scores_df=small_scores.scores,
        )
        assert result.scores["attrition_risk"].between(0, 100).all()

    def test_risk_categories_assigned(self, small_org, small_scores):
        from models.attrition_predictor import AttritionPredictor
        predictor = AttritionPredictor()
        result = predictor.predict(
            employees_df=small_org.employees,
            performance_df=small_org.performance,
            impact_scores_df=small_scores.scores,
        )
        valid_categories = {"Low Risk", "Moderate Risk", "High Risk", "Critical Risk"}
        assert set(result.scores["risk_category"].unique()).issubset(valid_categories)


# ---------------------------------------------------------------------------
# 6. Workflow engine benchmarks
# ---------------------------------------------------------------------------

class TestWorkflowPerformance:
    _THRESHOLD_PIPELINE_S = 5.0   # data pipeline flow
    _THRESHOLD_RETRAIN_S  = 5.0   # model retraining flow
    _THRESHOLD_REPORT_S   = 3.0   # report generation flow

    def test_data_pipeline_flow_speed(self):
        from workflows.data_pipeline_flow import data_pipeline_flow
        _, elapsed = _elapsed(data_pipeline_flow.run, source_path="demo")
        assert elapsed < self._THRESHOLD_PIPELINE_S

    def test_model_retraining_flow_speed(self):
        from workflows.model_retraining_flow import model_retraining_flow
        _, elapsed = _elapsed(
            model_retraining_flow.run, model_name="impact_scorer", force_retrain=True
        )
        assert elapsed < self._THRESHOLD_RETRAIN_S

    def test_report_generation_flow_speed(self):
        from workflows.report_generation_flow import report_generation_flow
        _, elapsed = _elapsed(
            report_generation_flow.run, report_type="weekly_risk"
        )
        assert elapsed < self._THRESHOLD_REPORT_S
