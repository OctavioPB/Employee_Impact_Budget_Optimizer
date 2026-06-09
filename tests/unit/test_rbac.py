"""Unit tests for auth/rbac.py, auth/session_manager.py,
audit/logger.py, audit/trail_viewer.py, and audit/compliance_reports.py.

Sprint 7 — Access Control, Audit & Enterprise Readiness.
"""

from __future__ import annotations

import pytest

from audit.compliance_reports import (
    ComplianceReport,
    ComplianceReportGenerator,
)
from audit.logger import (
    AuditEvent,
    AuditLogger,
    EventCategory,
    EventSeverity,
    log_access,
    log_admin,
    log_auth,
    log_export,
    log_override,
    log_security,
    log_simulation,
)
from audit.trail_viewer import TrailViewer
from auth.rbac import (
    _ROLE_PERMISSIONS,
    DEMO_USERS,
    AccessControl,
    Permission,
    Role,
    User,
    get_demo_user,
)

# ===========================================================================
# 1. Role definitions
# ===========================================================================

class TestRole:
    def test_role_ordering(self):
        assert Role.VIEWER < Role.ANALYST < Role.MANAGER
        assert Role.MANAGER < Role.DIRECTOR < Role.EXECUTIVE < Role.ADMIN

    def test_role_label(self):
        assert Role.VIEWER.label == "Viewer"
        assert Role.ADMIN.label == "Admin"

    def test_role_description_non_empty(self):
        for role in Role:
            assert len(role.description) > 10

    def test_from_string_case_insensitive(self):
        assert Role.from_string("viewer")  == Role.VIEWER
        assert Role.from_string("ADMIN")   == Role.ADMIN
        assert Role.from_string("Manager") == Role.MANAGER

    def test_from_string_invalid_raises(self):
        with pytest.raises(ValueError, match="Unknown role"):
            Role.from_string("superuser")

    def test_all_roles_have_permissions(self):
        for role in Role:
            assert len(_ROLE_PERMISSIONS[role]) > 0


# ===========================================================================
# 2. User & permission model
# ===========================================================================

class TestUser:
    def _make_user(self, role: Role, depts: list[str] | None = None) -> User:
        return User(
            user_id="U999", full_name="Test User",
            email="test@test.com", role=role,
            departments=depts or [],
        )

    def test_viewer_cannot_run_simulation(self):
        u = self._make_user(Role.VIEWER)
        assert not u.has_permission(Permission.RUN_SIMULATION)

    def test_analyst_can_run_simulation(self):
        u = self._make_user(Role.ANALYST)
        assert u.has_permission(Permission.RUN_SIMULATION)

    def test_manager_can_override(self):
        u = self._make_user(Role.MANAGER)
        assert u.has_permission(Permission.OVERRIDE_DECISION)

    def test_analyst_cannot_override(self):
        u = self._make_user(Role.ANALYST)
        assert not u.has_permission(Permission.OVERRIDE_DECISION)

    def test_admin_has_manage_users(self):
        u = self._make_user(Role.ADMIN)
        assert u.has_permission(Permission.MANAGE_USERS)

    def test_executive_lacks_manage_users(self):
        u = self._make_user(Role.EXECUTIVE)
        assert not u.has_permission(Permission.MANAGE_USERS)

    def test_salary_visibility_viewer_masked(self):
        u = self._make_user(Role.VIEWER)
        assert u.salary_visibility == "masked"

    def test_salary_visibility_analyst_range(self):
        u = self._make_user(Role.ANALYST)
        assert u.salary_visibility == "range"

    def test_salary_visibility_manager_full(self):
        u = self._make_user(Role.MANAGER)
        assert u.salary_visibility == "full"

    def test_pii_visibility_viewer_masked(self):
        u = self._make_user(Role.VIEWER)
        assert u.pii_visibility == "masked"

    def test_pii_visibility_manager_full(self):
        u = self._make_user(Role.MANAGER)
        assert u.pii_visibility == "full"

    def test_dept_access_scoped_manager(self):
        u = self._make_user(Role.MANAGER, ["Engineering"])
        assert u.can_access_department("Engineering")
        assert not u.can_access_department("Finance")

    def test_dept_access_org_wide_executive(self):
        u = self._make_user(Role.EXECUTIVE)
        assert u.can_access_department("Finance")
        assert u.can_access_department("Any Department")

    def test_dept_access_cross_dept_director(self):
        u = self._make_user(Role.DIRECTOR, ["Engineering", "Product"])
        assert u.can_access_department("Engineering")


# ===========================================================================
# 3. AccessControl
# ===========================================================================

class TestAccessControl:
    def _ac(self, role: Role, depts: list[str] | None = None) -> AccessControl:
        u = User("U1", "T", "t@t.com", role, departments=depts or [])
        return AccessControl(u)

    def test_can_returns_true_for_granted(self):
        ac = self._ac(Role.ADMIN)
        assert ac.can(Permission.MANAGE_USERS)

    def test_can_returns_false_for_denied(self):
        ac = self._ac(Role.VIEWER)
        assert not ac.can(Permission.MANAGE_USERS)

    def test_require_raises_permission_error(self):
        ac = self._ac(Role.VIEWER)
        with pytest.raises(PermissionError):
            ac.require(Permission.RUN_SIMULATION)

    def test_require_passes_for_granted(self):
        ac = self._ac(Role.ANALYST)
        ac.require(Permission.RUN_SIMULATION)  # should not raise

    def test_filter_departments_scoped(self):
        ac = self._ac(Role.MANAGER, ["Engineering"])
        result = ac.filter_departments(["Engineering", "Finance", "HR"])
        assert result == ["Engineering"]

    def test_filter_departments_org_wide(self):
        ac = self._ac(Role.EXECUTIVE)
        depts = ["Engineering", "Finance", "HR", "Marketing"]
        assert ac.filter_departments(depts) == depts

    def test_mask_salary_viewer_returns_stars(self):
        ac = self._ac(Role.VIEWER)
        assert ac.mask_salary(95_000) == "***"

    def test_mask_salary_analyst_returns_range(self):
        ac = self._ac(Role.ANALYST)
        result = ac.mask_salary(95_000)
        assert isinstance(result, str)
        assert "–" in result or "-" in result

    def test_mask_salary_manager_returns_float(self):
        ac = self._ac(Role.MANAGER)
        result = ac.mask_salary(95_000)
        assert result == 95_000

    def test_mask_pii_viewer_returns_short_id(self):
        ac = self._ac(Role.VIEWER)
        result = ac.mask_pii("Jane Doe", "EMP-12345")
        assert "Jane Doe" not in result

    def test_mask_pii_manager_returns_name(self):
        ac = self._ac(Role.MANAGER)
        result = ac.mask_pii("Jane Doe", "EMP-12345")
        assert result == "Jane Doe"

    def test_user_property(self):
        u = User("U1", "T", "t@t.com", Role.ANALYST)
        ac = AccessControl(u)
        assert ac.user is u


# ===========================================================================
# 4. Demo user registry
# ===========================================================================

class TestDemoUsers:
    def test_demo_users_list_non_empty(self):
        assert len(DEMO_USERS) >= 6

    def test_all_roles_represented(self):
        roles_present = {u.role for u in DEMO_USERS}
        for role in Role:
            assert role in roles_present, f"Role {role} missing from DEMO_USERS"

    def test_get_demo_user_returns_correct_role(self):
        for role in Role:
            u = get_demo_user(role)
            assert u.role == role

    def test_demo_users_have_valid_emails(self):
        for u in DEMO_USERS:
            assert "@" in u.email

    def test_demo_users_all_have_user_id(self):
        for u in DEMO_USERS:
            assert u.user_id


# ===========================================================================
# 5. AuditLogger
# ===========================================================================

@pytest.fixture
def fresh_logger(tmp_path) -> AuditLogger:
    """Return a fresh AuditLogger that does NOT share the singleton state."""
    al = AuditLogger.__new__(AuditLogger)
    al._initialised = False
    AuditLogger.__init__(al, log_dir=tmp_path / "audit", buffer_size=100)
    return al


class TestAuditLogger:
    def test_log_returns_audit_event(self, fresh_logger):
        event = fresh_logger.log(
            category=EventCategory.ACCESS,
            action="view_dashboard",
            resource="dashboard",
            detail="User viewed dashboard",
            user_id="U1", user_email="u@test.com", user_role="Analyst",
        )
        assert isinstance(event, AuditEvent)

    def test_event_has_all_fields(self, fresh_logger):
        event = fresh_logger.log(
            category=EventCategory.SIMULATION,
            action="run_simulation",
            resource="budget_scenario",
            detail="Budget cut simulation",
            user_id="U1", user_email="u@test.com", user_role="Manager",
        )
        assert event.event_id.startswith("EVT-")
        assert event.timestamp.endswith("Z")
        assert event.category == EventCategory.SIMULATION
        assert event.outcome == "success"

    def test_event_id_increments(self, fresh_logger):
        e1 = fresh_logger.log(EventCategory.ACCESS, "view", "r", "d",
                              "U1", "u@t.com", "Viewer")
        e2 = fresh_logger.log(EventCategory.ACCESS, "view", "r", "d",
                              "U1", "u@t.com", "Viewer")
        n1 = int(e1.event_id.split("-")[1])
        n2 = int(e2.event_id.split("-")[1])
        assert n2 == n1 + 1

    def test_query_by_category(self, fresh_logger):
        fresh_logger.log(EventCategory.ACCESS, "view", "r", "d",
                         "U1", "u@t.com", "Viewer")
        fresh_logger.log(EventCategory.EXPORT, "export", "r", "d",
                         "U2", "v@t.com", "Manager")
        results = fresh_logger.query(category=EventCategory.ACCESS)
        assert all(e.category == EventCategory.ACCESS for e in results)

    def test_query_by_user_email(self, fresh_logger):
        fresh_logger.log(EventCategory.ACCESS, "view", "r", "d",
                         "U1", "alice@t.com", "Analyst")
        fresh_logger.log(EventCategory.ACCESS, "view", "r", "d",
                         "U2", "bob@t.com", "Analyst")
        results = fresh_logger.query(user_email="alice@t.com")
        assert all(e.user_email == "alice@t.com" for e in results)

    def test_query_by_outcome(self, fresh_logger):
        fresh_logger.log(EventCategory.SECURITY, "blocked_access", "r", "d",
                         "U1", "u@t.com", "Viewer", outcome="blocked")
        fresh_logger.log(EventCategory.ACCESS, "view", "r", "d",
                         "U1", "u@t.com", "Viewer", outcome="success")
        blocked = fresh_logger.query(outcome="blocked")
        assert all(e.outcome == "blocked" for e in blocked)

    def test_recent_returns_latest_n(self, fresh_logger):
        for i in range(10):
            fresh_logger.log(EventCategory.ACCESS, f"action_{i}", "r", "d",
                             "U1", "u@t.com", "Viewer")
        recent = fresh_logger.recent(5)
        assert len(recent) == 5

    def test_stats_total_events(self, fresh_logger):
        for _ in range(3):
            fresh_logger.log(EventCategory.ACCESS, "view", "r", "d",
                             "U1", "u@t.com", "Viewer")
        s = fresh_logger.stats()
        assert s["total_events"] == 3

    def test_stats_by_category(self, fresh_logger):
        fresh_logger.log(EventCategory.ACCESS,     "view",  "r", "d",
                         "U1", "u@t.com", "Viewer")
        fresh_logger.log(EventCategory.SIMULATION, "run",   "r", "d",
                         "U1", "u@t.com", "Analyst")
        s = fresh_logger.stats()
        assert s["by_category"].get("access", 0) >= 1
        assert s["by_category"].get("simulation", 0) >= 1

    def test_export_jsonl_non_empty(self, fresh_logger):
        fresh_logger.log(EventCategory.ACCESS, "view", "r", "d",
                         "U1", "u@t.com", "Viewer")
        jsonl = fresh_logger.export_jsonl()
        assert len(jsonl) > 0

    def test_writes_to_file(self, fresh_logger, tmp_path):
        fresh_logger.log(EventCategory.AUTH, "login", "authentication", "login",
                         "U1", "u@t.com", "Viewer")
        log_file = fresh_logger._log_file
        assert log_file.exists()
        assert log_file.stat().st_size > 0

    def test_audit_event_to_dict(self, fresh_logger):
        e = fresh_logger.log(EventCategory.EXPORT, "export", "csv", "d",
                             "U1", "u@t.com", "Admin")
        d = e.to_dict()
        assert d["category"] == "export"
        assert d["event_id"] == e.event_id

    def test_audit_event_to_json_is_valid(self, fresh_logger):
        import json
        e = fresh_logger.log(EventCategory.ADMIN, "change_config", "config", "d",
                             "U1", "u@t.com", "Admin")
        parsed = json.loads(e.to_json())
        assert parsed["action"] == "change_config"


# ===========================================================================
# 6. Convenience log functions
# ===========================================================================

class TestConvenienceLoggers:
    def test_log_access(self, fresh_logger, monkeypatch):
        from audit import logger as lg
        monkeypatch.setattr(lg, "_audit", fresh_logger)
        e = log_access("U1", "u@t.com", "Viewer", "dashboard", "Viewed")
        assert e.category == EventCategory.ACCESS

    def test_log_simulation(self, fresh_logger, monkeypatch):
        from audit import logger as lg
        monkeypatch.setattr(lg, "_audit", fresh_logger)
        e = log_simulation("U1", "u@t.com", "Analyst", "scenario_A", "Ran sim")
        assert e.category == EventCategory.SIMULATION

    def test_log_override(self, fresh_logger, monkeypatch):
        from audit import logger as lg
        monkeypatch.setattr(lg, "_audit", fresh_logger)
        e = log_override("U1", "u@t.com", "Manager", "emp_123", "Force retain")
        assert e.category == EventCategory.OVERRIDE
        assert e.severity == EventSeverity.WARNING

    def test_log_export(self, fresh_logger, monkeypatch):
        from audit import logger as lg
        monkeypatch.setattr(lg, "_audit", fresh_logger)
        e = log_export("U1", "u@t.com", "Analyst", "results.csv", "Exported")
        assert e.category == EventCategory.EXPORT

    def test_log_auth_success(self, fresh_logger, monkeypatch):
        from audit import logger as lg
        monkeypatch.setattr(lg, "_audit", fresh_logger)
        e = log_auth("u@t.com", "login", outcome="success")
        assert e.severity == EventSeverity.INFO

    def test_log_auth_failure(self, fresh_logger, monkeypatch):
        from audit import logger as lg
        monkeypatch.setattr(lg, "_audit", fresh_logger)
        e = log_auth("u@t.com", "login", outcome="failure")
        assert e.severity == EventSeverity.WARNING

    def test_log_security(self, fresh_logger, monkeypatch):
        from audit import logger as lg
        monkeypatch.setattr(lg, "_audit", fresh_logger)
        e = log_security("U1", "u@t.com", "Viewer", "access_denied",
                         "salary_data", "Attempted salary access")
        assert e.category == EventCategory.SECURITY
        assert e.severity == EventSeverity.CRITICAL
        assert e.outcome == "blocked"

    def test_log_admin(self, fresh_logger, monkeypatch):
        from audit import logger as lg
        monkeypatch.setattr(lg, "_audit", fresh_logger)
        e = log_admin("U1", "u@t.com", "Admin", "change_role", "user_U2", "Role changed")
        assert e.category == EventCategory.ADMIN


# ===========================================================================
# 7. TrailViewer
# ===========================================================================

@pytest.fixture
def populated_viewer(tmp_path) -> TrailViewer:
    al = AuditLogger.__new__(AuditLogger)
    al._initialised = False
    AuditLogger.__init__(al, log_dir=tmp_path / "audit2", buffer_size=200)
    # Populate with varied events
    al.log(EventCategory.ACCESS,     "view",           "dashboard", "d", "U1", "a@t.com", "Analyst")
    al.log(EventCategory.ACCESS,     "view",           "employee",  "d", "U1", "a@t.com", "Analyst")
    al.log(EventCategory.SIMULATION, "run_simulation", "scenario_A","d", "U2", "b@t.com", "Manager")
    al.log(EventCategory.EXPORT,     "export",         "results",   "d", "U2", "b@t.com", "Manager")
    al.log(EventCategory.OVERRIDE,   "override",       "emp_123",   "d", "U3", "c@t.com", "Manager",
           severity=EventSeverity.WARNING)
    al.log(EventCategory.AUTH,       "login",          "auth",      "d", "U4", "d@t.com", "Admin")
    al.log(EventCategory.SECURITY,   "blocked",        "salary",    "d", "U5", "e@t.com", "Viewer",
           severity=EventSeverity.CRITICAL, outcome="blocked")
    return TrailViewer(al)


class TestTrailViewer:
    def test_events_df_has_correct_columns(self, populated_viewer):
        df = populated_viewer.events_df(limit=100)
        for col in ["timestamp", "category", "user_email", "action", "outcome"]:
            assert col in df.columns

    def test_events_df_filter_by_category(self, populated_viewer):
        df = populated_viewer.events_df(category=EventCategory.ACCESS)
        assert all(df["category"] == "access")

    def test_events_df_filter_by_outcome(self, populated_viewer):
        df = populated_viewer.events_df(outcome="blocked")
        assert all(df["outcome"] == "blocked")

    def test_recent_df_non_empty(self, populated_viewer):
        df = populated_viewer.recent_df(n=5)
        assert len(df) <= 5
        assert not df.empty

    def test_activity_by_user_has_columns(self, populated_viewer):
        df = populated_viewer.activity_by_user(hours_back=24)
        for col in ["user_email", "user_role", "event_count"]:
            assert col in df.columns

    def test_security_events_captures_blocked(self, populated_viewer):
        df = populated_viewer.security_events(hours_back=24)
        assert not df.empty
        assert all(df["category"] == "security")

    def test_failure_summary_returns_df(self, populated_viewer):
        df = populated_viewer.failure_summary(hours_back=24)
        assert isinstance(df, __import__("pandas").DataFrame)

    def test_export_csv_is_string(self, populated_viewer):
        csv = populated_viewer.export_csv(hours_back=24)
        assert isinstance(csv, str)
        assert "category" in csv

    def test_export_jsonl_is_string(self, populated_viewer):
        jsonl = populated_viewer.export_jsonl()
        assert isinstance(jsonl, str)

    def test_stats_non_zero(self, populated_viewer):
        s = populated_viewer.stats()
        assert s["total_events"] >= 7


# ===========================================================================
# 8. Compliance Reports
# ===========================================================================

@pytest.fixture
def report_gen(populated_viewer) -> ComplianceReportGenerator:
    return ComplianceReportGenerator(viewer=populated_viewer)


class TestComplianceReports:
    def test_gdpr_report_returns_compliance_report(self, report_gen):
        report = report_gen.gdpr_data_processing_report(days_back=7)
        assert isinstance(report, ComplianceReport)

    def test_gdpr_report_has_sections(self, report_gen):
        report = report_gen.gdpr_data_processing_report(days_back=7)
        assert len(report.sections) >= 4

    def test_gdpr_report_title_non_empty(self, report_gen):
        report = report_gen.gdpr_data_processing_report(days_back=7)
        assert "GDPR" in report.title

    def test_gdpr_report_to_markdown_is_string(self, report_gen):
        report = report_gen.gdpr_data_processing_report(days_back=7)
        md = report.to_markdown()
        assert isinstance(md, str)
        assert "# GDPR" in md

    def test_access_summary_report_returns_report(self, report_gen):
        report = report_gen.access_summary_report(days_back=7)
        assert isinstance(report, ComplianceReport)

    def test_access_summary_has_sections(self, report_gen):
        report = report_gen.access_summary_report(days_back=7)
        assert len(report.sections) >= 3

    def test_model_decision_report_returns_report(self, report_gen):
        report = report_gen.model_decision_report(days_back=7)
        assert isinstance(report, ComplianceReport)

    def test_model_decision_report_mentions_override(self, report_gen):
        report = report_gen.model_decision_report(days_back=7)
        md = report.to_markdown()
        assert "override" in md.lower() or "Override" in md

    def test_report_generated_at_non_empty(self, report_gen):
        report = report_gen.gdpr_data_processing_report(days_back=7)
        assert len(report.generated_at) > 0

    def test_convenience_wrapper_gdpr(self, populated_viewer, monkeypatch):
        import audit.compliance_reports as cr
        # Convenience functions use a fresh generator — just check they return ComplianceReport
        report = cr.generate_gdpr_report(days_back=1)
        assert isinstance(report, ComplianceReport)

    def test_convenience_wrapper_access(self):
        from audit.compliance_reports import generate_access_report
        report = generate_access_report(days_back=1)
        assert isinstance(report, ComplianceReport)

    def test_convenience_wrapper_model(self):
        from audit.compliance_reports import generate_model_report
        report = generate_model_report(days_back=1)
        assert isinstance(report, ComplianceReport)
