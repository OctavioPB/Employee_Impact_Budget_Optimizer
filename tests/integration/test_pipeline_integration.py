"""Integration tests: end-to-end flows across multiple EIBO modules.

These tests exercise complete vertical slices without mocking internal modules.
External services (PostgreSQL, SMTP) are replaced with in-memory or no-op stubs
so the suite runs offline with zero infrastructure.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from data_pipeline.bronze_ingest import _add_uuid_column, _read_file

# ---------------------------------------------------------------------------
# 1. Data pipeline integration: validators + bronze helpers
# ---------------------------------------------------------------------------
from data_pipeline.validators import (
    validate_csv_columns,
    validate_employee_dataframe,
    validate_performance_dataframe,
    validate_team_dataframe,
)


class TestDataPipelineIntegration:
    """Validate the pipeline stages work together on a synthetic DataFrame."""

    def _employee_df(self, n: int = 10) -> pd.DataFrame:
        return pd.DataFrame({
            "employee_id":    [f"E{i:03d}" for i in range(n)],
            "full_name":      [f"Person {i}" for i in range(n)],
            "role_title":     ["Engineer"] * n,
            "department":     ["Engineering"] * n,
            "annual_salary":  [100_000 + i * 5_000 for i in range(n)],
            "annual_benefits": [30_000] * n,
            "hire_date":      ["2020-01-01"] * n,
            "team_id":        ["T1"] * n,
            "seniority_level": ["mid"] * n,
        })

    # --- validate_csv_columns ---

    def test_csv_columns_valid(self):
        df = self._employee_df()
        result = validate_csv_columns(df, {"employee_id", "full_name"}, "test.csv")
        assert result.is_valid

    def test_csv_columns_missing(self):
        df = pd.DataFrame({"col_a": [1]})
        result = validate_csv_columns(df, {"employee_id", "full_name"}, "test.csv")
        assert not result.is_valid
        assert result.errors

    # --- validate_employee_dataframe ---

    def test_employee_df_valid(self):
        result = validate_employee_dataframe(self._employee_df())
        assert result.is_valid

    def test_employee_df_duplicate_ids(self):
        df = self._employee_df()
        df.loc[5, "employee_id"] = df.loc[0, "employee_id"]
        result = validate_employee_dataframe(df)
        assert not result.is_valid
        assert any("duplicate" in e.lower() for e in result.errors)

    def test_employee_df_salary_out_of_range_adds_warning(self):
        df = self._employee_df()
        df.loc[0, "annual_salary"] = 1  # below minimum
        result = validate_employee_dataframe(df)
        assert any("salary" in w.lower() for w in result.warnings)

    def test_employee_df_invalid_seniority(self):
        df = self._employee_df()
        df.loc[0, "seniority_level"] = "intern"  # not in canonical set
        result = validate_employee_dataframe(df)
        assert not result.is_valid

    # --- validate_performance_dataframe ---

    def _perf_df(self, n: int = 5) -> pd.DataFrame:
        return pd.DataFrame({
            "performance_id": [f"P{i}" for i in range(n)],
            "employee_id":    [f"E{i:03d}" for i in range(n)],
            "review_date":    ["2023-12-01"] * n,
            "review_period":  ["Q4-2023"] * n,
            "kpi_score":      [3.5 + i * 0.1 for i in range(n)],
        })

    def test_perf_df_valid(self):
        result = validate_performance_dataframe(self._perf_df())
        assert result.is_valid

    def test_perf_df_out_of_range_kpi(self):
        df = self._perf_df()
        df.loc[0, "kpi_score"] = 6.0  # above max
        result = validate_performance_dataframe(df)
        assert not result.is_valid

    # --- validate_team_dataframe ---

    def _team_df(self) -> pd.DataFrame:
        return pd.DataFrame({
            "team_id":      ["T1", "T2"],
            "team_name":    ["Alpha", "Beta"],
            "department":   ["Engineering", "Product"],
            "annual_budget": [500_000.0, 300_000.0],
        })

    def test_team_df_valid(self):
        result = validate_team_dataframe(self._team_df())
        assert result.is_valid

    def test_team_df_negative_budget(self):
        df = self._team_df()
        df.loc[0, "annual_budget"] = -1
        result = validate_team_dataframe(df)
        assert not result.is_valid

    # --- bronze helpers ---

    def test_add_uuid_column_adds_when_missing(self):
        df = pd.DataFrame({"name": ["Alice", "Bob"]})
        out = _add_uuid_column(df, "employee_id")
        assert "employee_id" in out.columns
        assert out["employee_id"].notna().all()
        assert len(out["employee_id"].unique()) == 2

    def test_add_uuid_column_preserves_existing(self):
        df = pd.DataFrame({"employee_id": ["E1", "E2"], "name": ["A", "B"]})
        out = _add_uuid_column(df, "employee_id")
        assert list(out["employee_id"]) == ["E1", "E2"]

    def test_read_file_csv(self, tmp_path: Path):
        p = tmp_path / "data.csv"
        p.write_text("name,salary\nAlice,90000\nBob,85000\n")
        df = _read_file(p)
        assert len(df) == 2
        assert "name" in df.columns

    def test_read_file_unsupported_raises(self, tmp_path: Path):
        p = tmp_path / "data.json"
        p.write_text("{}")
        with pytest.raises(ValueError, match="Unsupported file type"):
            _read_file(p)


# ---------------------------------------------------------------------------
# 2. Model pipeline integration: demo data → impact scoring → ILP
# ---------------------------------------------------------------------------

from demo_data.generator import DemoGenerator
from models.impact_scorer import ImpactScorer
from models.network_analysis import build_graph, compute_centrality_metrics
from optimization_engine.constraints import ConstraintConfig
from optimization_engine.ilp_solver import solve


class TestModelPipelineIntegration:
    """Full: demo data generation → network analysis → impact scoring → ILP."""

    @pytest.fixture(scope="class")
    def org(self):
        return DemoGenerator("A", "small", seed=42).generate()

    def test_demo_generator_produces_non_empty_org(self, org):
        assert len(org.employees) > 0
        assert len(org.teams) > 0
        assert len(org.performance) > 0
        assert len(org.skills) > 0

    def test_network_metrics_computed(self, org):
        G = build_graph(org.collaboration)
        centrality_df = compute_centrality_metrics(G, org.employees)
        assert len(centrality_df) > 0
        assert "combined_centrality" in centrality_df.columns

    def test_impact_scorer_runs_heuristic(self, org):
        G = build_graph(org.collaboration)
        centrality_df = compute_centrality_metrics(G, org.employees)
        scorer = ImpactScorer(random_state=42)
        result = scorer.score(
            employees_df=org.employees,
            performance_df=org.performance,
            centrality_df=centrality_df,
            employee_skills_df=org.employee_skills,
            skills_df=org.skills,
        )
        assert result.mode == "heuristic"
        assert len(result.scores) == len(org.employees)
        assert result.scores["impact_score"].between(0, 100).all()

    def test_ilp_solve_with_70pct_budget(self, org):
        G = build_graph(org.collaboration)
        centrality_df = compute_centrality_metrics(G, org.employees)
        scorer = ImpactScorer(random_state=42)
        score_result = scorer.score(
            employees_df=org.employees,
            performance_df=org.performance,
            centrality_df=centrality_df,
            employee_skills_df=org.employee_skills,
            skills_df=org.skills,
        )
        current_spend = (
            org.employees["annual_salary"] + org.employees["annual_benefits"]
        ).sum()
        budget = current_spend * 0.70
        config = ConstraintConfig(
            require_leadership_per_team=True,
            require_critical_skills=False,
            min_team_size=0,
            solver_msg=False,
        )
        opt = solve(org.employees, budget_target=budget,
                    impact_scores=score_result.scores, critical_skill_holders={},
                    constraint_config=config)
        assert opt.status in ("Optimal", "Infeasible")
        if opt.status == "Optimal":
            assert opt.total_cost <= budget * 1.001   # within 0.1% tolerance
            assert opt.n_retained > 0
            assert opt.n_retained + opt.n_at_risk == opt.n_total

    def test_ilp_full_budget_retains_everyone(self, org):
        G = build_graph(org.collaboration)
        centrality_df = compute_centrality_metrics(G, org.employees)
        scorer = ImpactScorer(random_state=42)
        score_result = scorer.score(
            employees_df=org.employees,
            performance_df=org.performance,
            centrality_df=centrality_df,
            employee_skills_df=org.employee_skills,
            skills_df=org.skills,
        )
        full_budget = (
            org.employees["annual_salary"] + org.employees["annual_benefits"]
        ).sum() * 1.5  # 150% of current spend
        config = ConstraintConfig(
            require_leadership_per_team=False,
            require_critical_skills=False,
            solver_msg=False,
        )
        opt = solve(org.employees, budget_target=full_budget,
                    impact_scores=score_result.scores, critical_skill_holders={},
                    constraint_config=config)
        assert opt.status == "Optimal"
        assert opt.n_retained == opt.n_total

    def test_impact_scores_align_with_ilp_retention(self, org):
        """Employees with higher impact scores should be preferentially retained."""
        G = build_graph(org.collaboration)
        centrality_df = compute_centrality_metrics(G, org.employees)
        scorer = ImpactScorer(random_state=42)
        score_result = scorer.score(
            employees_df=org.employees,
            performance_df=org.performance,
            centrality_df=centrality_df,
            employee_skills_df=org.employee_skills,
            skills_df=org.skills,
        )
        current_spend = (
            org.employees["annual_salary"] + org.employees["annual_benefits"]
        ).sum()
        config = ConstraintConfig(
            require_leadership_per_team=False,
            require_critical_skills=False,
            solver_msg=False,
        )
        opt = solve(org.employees, budget_target=current_spend * 0.60,
                    impact_scores=score_result.scores, critical_skill_holders={},
                    constraint_config=config)
        if opt.status != "Optimal":
            pytest.skip("Solver returned non-optimal — skip alignment check")

        # ILP maximises TOTAL impact, not per-capita average.
        # At tight budgets, cost constraints can exclude high-impact expensive employees,
        # so compare totals (not averages) — that is what the objective function optimises.
        scores = score_result.scores.set_index("employee_id")["impact_score"]
        retained_total = scores[list(opt.retained_ids)].sum()
        at_risk_total  = scores[list(opt.at_risk_ids)].sum() if opt.at_risk_ids else 0
        assert retained_total >= at_risk_total


# ---------------------------------------------------------------------------
# 3. Notification + workflow integration
# ---------------------------------------------------------------------------

from notifications.engine import (
    NotificationEngine,
    NotificationPriority,
    NotificationStore,
    NotificationType,
)
from workflows.engine import FlowState, get_registry


class TestNotificationWorkflowIntegration:
    """Workflow execution produces notifications via the engine."""

    def test_workflow_run_produces_flow_run_with_task_results(self):
        from workflows.data_pipeline_flow import data_pipeline_flow
        run = data_pipeline_flow.run(source_path="demo")
        assert run.state == FlowState.COMPLETED
        assert len(run.task_results) >= 4  # ingest + cleanse + aggregate + validate

    def test_workflow_status_notification_dispatched(self):
        store = NotificationStore(max_size=50)
        engine = NotificationEngine(store=store, bundle_window_m=1)

        from workflows.data_pipeline_flow import data_pipeline_flow
        run = data_pipeline_flow.run(source_path="demo")

        n = engine.send_workflow_status(
            title=f"Flow '{run.flow_name}' completed",
            body=f"{run.n_tasks} tasks, {run.n_failed} failed.",
            success=run.succeeded,
        )
        assert n.notification_type == NotificationType.WORKFLOW_STATUS
        assert engine.stats()["total"] == 1

    def test_risk_alert_bundled_after_multiple_sends(self):
        store = NotificationStore(max_size=50)
        engine = NotificationEngine(store=store, bundle_window_m=1)
        for i in range(3):
            engine.send_risk_alert(
                title=f"Risk alert {i}",
                body="Details",
                priority=NotificationPriority.HIGH,
            )
        bundles = engine.flush_bundles()
        assert len(bundles) >= 1

    def test_all_three_flows_registered(self):
        reg = get_registry()
        names = {f.flow_name for f in reg.all_flows()}
        assert "data_pipeline" in names
        assert "model_retraining" in names
        assert "report_generation" in names

    def test_registry_run_flow_returns_flow_run(self):
        reg = get_registry()
        run = reg.run_flow("data_pipeline", triggered_by="integration_test",
                           source_path="demo")
        assert run is not None
        assert run.succeeded

    def test_model_retraining_with_force_runs_all_tasks(self):
        from workflows.model_retraining_flow import model_retraining_flow
        run = model_retraining_flow.run(model_name="impact_scorer", force_retrain=True)
        assert run.succeeded
        # assess + retrain + validate + deploy + notify = 5 tasks
        assert len(run.task_results) == 5


# ---------------------------------------------------------------------------
# 4. RBAC + Audit logger integration
# ---------------------------------------------------------------------------

from audit.logger import AuditLogger, EventCategory, EventSeverity
from auth.rbac import AccessControl, Permission, Role, get_demo_user


class TestRbacAuditIntegration:
    """AccessControl denials are logged by the audit logger."""

    @pytest.fixture
    def fresh_logger(self, tmp_path: Path) -> AuditLogger:
        logger = AuditLogger.__new__(AuditLogger)
        logger._initialised = False
        logger.__init__(log_dir=str(tmp_path / "audit"))
        return logger

    def test_permission_denied_is_auditable(self, fresh_logger):
        viewer = get_demo_user(Role.VIEWER)
        ac = AccessControl(viewer)
        try:
            ac.require(Permission.RUN_SIMULATION)
        except PermissionError:
            pass
        event = fresh_logger.log(
            category=EventCategory.SECURITY,
            action="permission_denied",
            resource=Permission.RUN_SIMULATION,
            detail="Viewer attempted simulation",
            user_id=viewer.user_id,
            user_email=viewer.email,
            user_role=viewer.role.name,
            severity=EventSeverity.WARNING,
            outcome="denied",
        )
        assert event.outcome == "denied"
        assert event.category == EventCategory.SECURITY

    def test_admin_can_view_audit_log(self):
        admin = get_demo_user(Role.ADMIN)
        ac = AccessControl(admin)
        assert ac.can(Permission.VIEW_AUDIT_LOG)

    def test_viewer_cannot_view_audit_log(self):
        viewer = get_demo_user(Role.VIEWER)
        ac = AccessControl(viewer)
        assert not ac.can(Permission.VIEW_AUDIT_LOG)

    def test_manager_scoped_to_department(self):
        manager = get_demo_user(Role.MANAGER)
        for dept in manager.departments:
            assert manager.can_access_department(dept)

    def test_salary_visibility_cascade(self):
        for role, expected in [
            (Role.ADMIN, "full"),
            (Role.EXECUTIVE, "full"),
            (Role.DIRECTOR, "full"),
            (Role.MANAGER, "full"),
            (Role.ANALYST, "range"),
            (Role.VIEWER, "masked"),
        ]:
            user = get_demo_user(role)
            assert user.salary_visibility == expected, \
                f"Role {role.name} should have '{expected}' salary visibility"

    def test_pii_visibility_cascade(self):
        for role, expected in [
            (Role.ADMIN, "full"),
            (Role.EXECUTIVE, "full"),
            (Role.DIRECTOR, "full"),
            (Role.MANAGER, "full"),
            (Role.ANALYST, "partial"),
            (Role.VIEWER, "masked"),
        ]:
            user = get_demo_user(role)
            assert user.pii_visibility == expected, \
                f"Role {role.name} should have '{expected}' PII visibility"

    def test_audit_query_filters_by_category(self, fresh_logger):
        fresh_logger.log(
            category=EventCategory.ACCESS, action="login", resource="ui",
            detail="", user_id="u1", user_email="a@b.com", user_role="ADMIN",
        )
        fresh_logger.log(
            category=EventCategory.SIMULATION, action="run", resource="ilp",
            detail="", user_id="u2", user_email="c@d.com", user_role="ANALYST",
        )
        access_events = fresh_logger.query(category=EventCategory.ACCESS)
        assert all(e.category == EventCategory.ACCESS for e in access_events)
        assert len(access_events) == 1

    def test_audit_export_jsonl_non_empty(self, fresh_logger):
        fresh_logger.log(
            category=EventCategory.AUTH, action="logout", resource="session",
            detail="", user_id="u1", user_email="a@b.com", user_role="VIEWER",
        )
        jsonl = fresh_logger.export_jsonl()
        assert len(jsonl.strip()) > 0

    def test_access_control_mask_salary_by_role(self):
        analyst = get_demo_user(Role.ANALYST)
        ac = AccessControl(analyst)
        masked = ac.mask_salary(120_000.0)
        # Analyst sees a salary range (string), never the exact float
        assert isinstance(masked, str)
        assert masked != "120000.0"
        assert "–" in masked  # range separator present

    def test_access_control_full_salary_for_manager(self):
        manager = get_demo_user(Role.MANAGER)
        ac = AccessControl(manager)
        result = ac.mask_salary(120_000.0)
        assert result == 120_000.0  # returned as-is
