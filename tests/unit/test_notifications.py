"""Unit tests for Sprint 8: Notifications, Workflows & Integration Hub."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import httpx
import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Notification engine tests
# ---------------------------------------------------------------------------
from notifications.engine import (
    DeliveryStatus,
    Notification,
    NotificationBundle,
    NotificationBundler,
    NotificationEngine,
    NotificationPriority,
    NotificationStore,
    NotificationType,
    get_notification_engine,
)


def _make_notification(
    ntype: NotificationType = NotificationType.RISK_ALERT,
    priority: NotificationPriority = NotificationPriority.HIGH,
    user_ids: list[str] | None = None,
    bundle_key: str = "",
) -> Notification:
    from datetime import datetime
    return Notification(
        notification_id=str(uuid4()),
        notification_type=ntype,
        priority=priority,
        title="Test Notification",
        body="Test body text",
        source="test_suite",
        created_at=datetime.utcnow(),
        target_user_ids=user_ids or ["u1"],
        bundle_key=bundle_key,
    )


class TestNotification:
    def test_initial_status_pending(self):
        n = _make_notification()
        assert n.status == DeliveryStatus.PENDING

    def test_mark_read(self):
        n = _make_notification(user_ids=["u1", "u2"])
        n.mark_read("u1")
        assert n.is_read_by("u1")
        assert not n.is_read_by("u2")

    def test_mark_read_idempotent(self):
        n = _make_notification()
        n.mark_read("u1")
        n.mark_read("u1")
        assert len(n.read_by) == 1

    def test_is_read_by_unknown_user_false(self):
        n = _make_notification()
        assert not n.is_read_by("nobody")

    def test_all_priority_values_exist(self):
        for p in (NotificationPriority.LOW, NotificationPriority.MEDIUM,
                  NotificationPriority.HIGH, NotificationPriority.CRITICAL):
            n = _make_notification(priority=p)
            assert n.priority == p

    def test_all_types_exist(self):
        for t in NotificationType:
            n = _make_notification(ntype=t)
            assert n.notification_type == t

    def test_to_dict_contains_expected_keys(self):
        n = _make_notification()
        d = n.to_dict()
        for key in ("notification_id", "notification_type", "priority", "title", "body", "source"):
            assert key in d


class TestNotificationStore:
    def _fresh_store(self) -> NotificationStore:
        return NotificationStore(max_size=20)

    def test_add_and_retrieve(self):
        store = self._fresh_store()
        n = _make_notification(user_ids=["alice"])
        store.add(n)
        result = store.for_user("alice")
        assert any(x.notification_id == n.notification_id for x in result)

    def test_for_user_excludes_other_users(self):
        store = self._fresh_store()
        n_alice = _make_notification(user_ids=["alice"])
        n_bob = _make_notification(user_ids=["bob"])
        store.add(n_alice)
        store.add(n_bob)
        alice_notifs = store.for_user("alice")
        assert all("alice" in x.target_user_ids for x in alice_notifs)

    def test_unread_count_increments(self):
        store = self._fresh_store()
        store.add(_make_notification(user_ids=["u1"]))
        store.add(_make_notification(user_ids=["u1"]))
        assert store.unread_count("u1") == 2

    def test_mark_all_read(self):
        store = self._fresh_store()
        store.add(_make_notification(user_ids=["u1"]))
        store.add(_make_notification(user_ids=["u1"]))
        marked = store.mark_all_read("u1")
        assert marked == 2
        assert store.unread_count("u1") == 0

    def test_for_user_unread_only(self):
        store = self._fresh_store()
        n1 = _make_notification(user_ids=["u1"])
        n2 = _make_notification(user_ids=["u1"])
        store.add(n1)
        store.add(n2)
        n1.mark_read("u1")
        unread = store.for_user("u1", unread_only=True)
        assert all(not x.is_read_by("u1") for x in unread)
        assert len(unread) == 1

    def test_ring_buffer_evicts_oldest(self):
        store = NotificationStore(max_size=3)
        ids = []
        for _ in range(5):
            n = _make_notification(user_ids=["u1"])
            ids.append(n.notification_id)
            store.add(n)
        result_ids = {x.notification_id for x in store.for_user("u1")}
        assert ids[0] not in result_ids
        assert ids[1] not in result_ids
        assert ids[4] in result_ids

    def test_stats_returns_dict(self):
        store = self._fresh_store()
        store.add(_make_notification())
        s = store.stats()
        assert isinstance(s, dict)
        assert "total" in s

    def test_filter_by_type(self):
        store = self._fresh_store()
        n_risk = _make_notification(ntype=NotificationType.RISK_ALERT, user_ids=["u1"])
        n_sys = _make_notification(ntype=NotificationType.SYSTEM, user_ids=["u1"])
        store.add(n_risk)
        store.add(n_sys)
        results = store.for_user("u1", ntype=NotificationType.RISK_ALERT)
        assert all(x.notification_type == NotificationType.RISK_ALERT for x in results)

    def test_get_returns_notification_by_id(self):
        store = self._fresh_store()
        n = _make_notification()
        store.add(n)
        assert store.get(n.notification_id) is n

    def test_get_unknown_id_returns_none(self):
        store = self._fresh_store()
        assert store.get("nonexistent") is None

    def test_broadcast_visible_to_all_users(self):
        from datetime import datetime
        store = self._fresh_store()
        # target_user_ids=[] means broadcast — must be set directly, not via helper
        n = Notification(
            notification_id=str(uuid4()),
            notification_type=NotificationType.SYSTEM,
            priority=NotificationPriority.LOW,
            title="Broadcast",
            body="All users",
            source="test",
            created_at=datetime.utcnow(),
            target_user_ids=[],
        )
        store.add(n)
        assert any(x.notification_id == n.notification_id for x in store.for_user("any_user"))

    def test_duplicate_add_ignored(self):
        store = self._fresh_store()
        n = _make_notification(user_ids=["u1"])
        store.add(n)
        store.add(n)  # same object, same ID
        assert store.unread_count("u1") == 1


class TestNotificationBundler:
    def test_add_returns_none_always(self):
        bundler = NotificationBundler(window_minutes=1)
        n = _make_notification(bundle_key="risk:dept1")
        result = bundler.add(n)
        assert result is None

    def test_single_notification_no_bundle_on_flush(self):
        bundler = NotificationBundler(window_minutes=1)
        bundler.add(_make_notification(bundle_key="risk:dept1"))
        bundles = bundler.flush()
        assert bundles == []

    def test_two_notifications_same_key_bundles_on_flush(self):
        bundler = NotificationBundler(window_minutes=1)
        bundler.add(_make_notification(bundle_key="risk:dept1"))
        bundler.add(_make_notification(bundle_key="risk:dept1"))
        bundles = bundler.flush()
        assert len(bundles) == 1
        assert isinstance(bundles[0], NotificationBundle)

    def test_three_same_key_one_bundle(self):
        bundler = NotificationBundler(window_minutes=1)
        for _ in range(3):
            bundler.add(_make_notification(bundle_key="grp1"))
        bundles = bundler.flush()
        assert len(bundles) == 1
        assert len(bundles[0].notifications) == 3

    def test_different_keys_produce_separate_bundles(self):
        bundler = NotificationBundler(window_minutes=1)
        for _ in range(2):
            bundler.add(_make_notification(bundle_key="grp1"))
        for _ in range(2):
            bundler.add(_make_notification(bundle_key="grp2"))
        bundles = bundler.flush()
        assert len(bundles) == 2
        assert {b.bundle_key for b in bundles} == {"grp1", "grp2"}

    def test_flush_marks_notifications_as_bundled(self):
        bundler = NotificationBundler(window_minutes=1)
        n1 = _make_notification(bundle_key="grp1")
        n2 = _make_notification(bundle_key="grp1")
        bundler.add(n1)
        bundler.add(n2)
        bundler.flush()
        assert n1.status == DeliveryStatus.BUNDLED
        assert n2.status == DeliveryStatus.BUNDLED

    def test_flush_clears_pending(self):
        bundler = NotificationBundler(window_minutes=1)
        for _ in range(2):
            bundler.add(_make_notification(bundle_key="grp1"))
        bundler.flush()
        bundles2 = bundler.flush()
        assert bundles2 == []


class TestNotificationEngine:
    def _engine(self) -> NotificationEngine:
        store = NotificationStore(max_size=100)
        return NotificationEngine(store=store, bundle_window_m=1)

    def test_send_returns_notification(self):
        engine = self._engine()
        n = engine.send(
            ntype=NotificationType.SYSTEM,
            priority=NotificationPriority.LOW,
            title="Hello",
            body="World",
            source="test",
        )
        assert isinstance(n, Notification)
        assert n.title == "Hello"

    def test_send_risk_alert(self):
        engine = self._engine()
        n = engine.send_risk_alert(
            title="High attrition risk",
            body="3 employees flagged",
            priority=NotificationPriority.HIGH,
        )
        assert n.notification_type == NotificationType.RISK_ALERT

    def test_send_workflow_status_success(self):
        engine = self._engine()
        n = engine.send_workflow_status(title="Pipeline done", body="OK", success=True)
        assert n.notification_type == NotificationType.WORKFLOW_STATUS
        assert n.priority == NotificationPriority.LOW

    def test_send_workflow_status_failure(self):
        engine = self._engine()
        n = engine.send_workflow_status(title="Pipeline failed", body="Error", success=False)
        assert n.notification_type == NotificationType.WORKFLOW_STATUS
        assert n.priority == NotificationPriority.HIGH

    def test_for_user_returns_list(self):
        engine = self._engine()
        engine.send(NotificationType.SYSTEM, NotificationPriority.LOW,
                    "t", "b", "s", target_user_ids=["alice"])
        results = engine.for_user("alice")
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_unread_count_after_send(self):
        engine = self._engine()
        engine.send(NotificationType.SYSTEM, NotificationPriority.LOW,
                    "t", "b", "s", target_user_ids=["bob"])
        assert engine.unread_count("bob") >= 1

    def test_mark_read(self):
        engine = self._engine()
        n = engine.send(NotificationType.SYSTEM, NotificationPriority.LOW,
                        "t", "b", "s", target_user_ids=["carol"])
        ok = engine.mark_read(n.notification_id, "carol")
        assert ok
        assert engine.unread_count("carol") == 0

    def test_mark_read_unknown_id_returns_false(self):
        engine = self._engine()
        assert not engine.mark_read("nonexistent-id", "carol")

    def test_flush_bundles_returns_list(self):
        engine = self._engine()
        bundles = engine.flush_bundles()
        assert isinstance(bundles, list)

    def test_flush_bundles_bundles_same_type(self):
        engine = self._engine()
        for _ in range(3):
            engine.send(NotificationType.RISK_ALERT, NotificationPriority.HIGH,
                        "Alert", "body", "src", bundle_key="risk_alert")
        bundles = engine.flush_bundles()
        assert len(bundles) >= 1

    def test_get_notification_engine_singleton(self):
        e1 = get_notification_engine()
        e2 = get_notification_engine()
        assert e1 is e2

    def test_mark_all_read(self):
        engine = self._engine()
        engine.send(NotificationType.SYSTEM, NotificationPriority.LOW,
                    "t1", "b", "s", target_user_ids=["dave"])
        engine.send(NotificationType.SYSTEM, NotificationPriority.LOW,
                    "t2", "b", "s", target_user_ids=["dave"])
        count = engine.mark_all_read("dave")
        assert count == 2
        assert engine.unread_count("dave") == 0


# ---------------------------------------------------------------------------
# Email channel tests
# ---------------------------------------------------------------------------

from notifications.channels.email_channel import EmailChannel


class TestEmailChannel:
    def test_is_configured_false_without_smtp(self):
        ch = EmailChannel(smtp_host="", smtp_port=587, smtp_user="", smtp_password="")
        assert not ch.is_configured

    def test_is_configured_true_with_smtp(self):
        ch = EmailChannel(
            smtp_host="mail.example.com",
            smtp_port=587,
            smtp_user="user@example.com",
            smtp_password="secret",
        )
        assert ch.is_configured

    def test_deliver_no_recipients_is_noop(self):
        ch = EmailChannel(smtp_host="", smtp_port=587, smtp_user="", smtp_password="")
        n = _make_notification(user_ids=["u1"])
        # No user_email_map → _resolve_recipients returns [] → returns early
        ch.deliver(n)  # must not raise

    def test_deliver_simulated_logs(self, caplog):
        import logging
        ch = EmailChannel(
            smtp_host="",
            smtp_password="",
            smtp_user="",
            user_email_map={"u1": "alice@example.com"},
        )
        n = _make_notification(user_ids=["u1"])
        with caplog.at_level(logging.INFO):
            ch.deliver(n)
        assert any("simulated" in r.message.lower() or "alice" in r.message.lower()
                   for r in caplog.records)

    def test_deliver_configured_calls_smtp(self):
        ch = EmailChannel(
            smtp_host="mail.example.com",
            smtp_port=587,
            smtp_user="user@example.com",
            smtp_password="secret",
            user_email_map={"u1": "alice@example.com"},
        )
        n = _make_notification(user_ids=["u1"])
        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_server = MagicMock()
            mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_server.sendmail = MagicMock()
            ch.deliver(n)
            mock_smtp_cls.assert_called_once_with("mail.example.com", 587)

    def test_render_html_contains_title(self):
        ch = EmailChannel()
        n = _make_notification()
        n.title = "My Alert Title"
        html = ch._render_html(n)
        assert "My Alert Title" in html


# ---------------------------------------------------------------------------
# Webhook channel tests
# ---------------------------------------------------------------------------

from notifications.channels.webhook_channel import WebhookChannel


class TestWebhookChannel:
    def test_format_slack_payload_has_text(self):
        ch = WebhookChannel(url="https://hooks.slack.com/test", format="slack")
        n = _make_notification(priority=NotificationPriority.HIGH)
        payload = ch._build_payload(n)
        assert "text" in payload
        assert "attachments" in payload

    def test_format_teams_payload_has_type(self):
        ch = WebhookChannel(url="https://outlook.office.com/test", format="teams")
        n = _make_notification()
        payload = ch._build_payload(n)
        assert payload.get("@type") == "MessageCard"

    def test_format_generic_payload_is_notification_dict(self):
        ch = WebhookChannel(url="https://example.com/hook", format="generic")
        n = _make_notification()
        payload = ch._build_payload(n)
        assert "notification_id" in payload or "title" in payload

    def test_deliver_calls_httpx_post(self):
        ch = WebhookChannel(url="https://example.com/hook", format="generic")
        n = _make_notification()
        with patch("httpx.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.raise_for_status = MagicMock()
            mock_post.return_value = mock_resp
            ch.deliver(n)
            mock_post.assert_called_once()

    def test_deliver_raises_on_http_error(self):
        ch = WebhookChannel(url="https://example.com/hook", format="generic")
        n = _make_notification()
        with patch("httpx.post", side_effect=httpx.HTTPError("503")):
            with pytest.raises(httpx.HTTPError):
                ch.deliver(n)

    def test_deliver_bundle_calls_post(self):
        ch = WebhookChannel(url="https://example.com/hook", format="generic")
        from datetime import datetime
        bundle = NotificationBundle(
            bundle_id=str(uuid4()),
            bundle_key="grp",
            notifications=[_make_notification(), _make_notification()],
            created_at=datetime.utcnow(),
        )
        with patch("httpx.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_post.return_value = mock_resp
            ch.deliver_bundle(bundle)
            mock_post.assert_called_once()


# ---------------------------------------------------------------------------
# Workflow engine tests
# ---------------------------------------------------------------------------

from workflows.engine import (
    FlowRun,
    FlowState,
    TaskResult,
    _FlowWrapper,
    _TaskWrapper,
    flow,
    get_registry,
    task,
)


class TestTaskDecorator:
    def test_task_wraps_function(self):
        @task(name="my_task")
        def add(a: int, b: int) -> int:
            return a + b

        assert isinstance(add, _TaskWrapper)

    def test_task_run_returns_task_result(self):
        @task(name="add_task")
        def add(a: int, b: int) -> int:
            return a + b

        result = add.run(2, 3)
        assert isinstance(result, TaskResult)
        assert result.succeeded
        assert result.result == 5

    def test_task_result_on_exception(self):
        @task(name="fail_task")
        def fail():
            raise ValueError("boom")

        result = fail.run()
        assert result.failed
        assert "boom" in result.error

    def test_task_retries_on_failure(self):
        call_count = {"n": 0}

        @task(name="retry_task", retries=2, retry_delay=0.0)
        def flaky():
            call_count["n"] += 1
            if call_count["n"] < 3:
                raise RuntimeError("not yet")
            return "ok"

        result = flaky.run()
        assert result.succeeded
        assert call_count["n"] == 3

    def test_task_exhausts_retries(self):
        @task(name="always_fail", retries=1, retry_delay=0.0)
        def always_fail():
            raise RuntimeError("permanent failure")

        result = always_fail.run()
        assert result.failed

    def test_task_name_defaults_to_function_name(self):
        @task()
        def my_function():
            return 42

        assert my_function.task_name == "my_function"

    def test_task_result_has_duration(self):
        @task(name="timed_task")
        def noop():
            return None

        result = noop.run()
        assert result.duration_s >= 0.0

    def test_task_result_records_attempt_number(self):
        @task(name="first_attempt", retries=0)
        def simple():
            return 1

        result = simple.run()
        assert result.attempt == 1

    def test_task_callable_directly(self):
        @task(name="callable_task")
        def double(x: int) -> int:
            return x * 2

        result = double(5)
        assert isinstance(result, TaskResult)
        assert result.result == 10


class TestFlowDecorator:
    def test_flow_wraps_function(self):
        @flow(name="my_flow")
        def my_flow(_flow_run=None):
            pass

        assert isinstance(my_flow, _FlowWrapper)

    def test_flow_run_returns_flow_run(self):
        @flow(name="simple_flow")
        def simple(_flow_run=None):
            pass

        run = simple.run()
        assert isinstance(run, FlowRun)

    def test_flow_run_success(self):
        @flow(name="success_flow")
        def succeeds(_flow_run=None):
            pass

        run = succeeds.run()
        assert run.succeeded

    def test_flow_state_completed(self):
        @flow(name="completed_state_flow")
        def cf(_flow_run=None):
            pass

        run = cf.run()
        assert run.state == FlowState.COMPLETED

    def test_flow_run_failure_on_exception(self):
        @flow(name="fail_flow")
        def fails(_flow_run=None):
            raise RuntimeError("flow error")

        run = fails.run()
        assert not run.succeeded
        assert run.error

    def test_flow_run_history(self):
        @flow(name="history_flow")
        def hist(_flow_run=None):
            pass

        hist.run()
        hist.run()
        assert len(hist.run_history) == 2

    def test_last_run_none_before_run(self):
        @flow(name="last_run_flow")
        def lr(_flow_run=None):
            pass

        assert lr.last_run is None

    def test_last_run_set_after_run(self):
        @flow(name="last_run_after_flow")
        def lra(_flow_run=None):
            pass

        lra.run()
        assert isinstance(lra.last_run, FlowRun)

    def test_flow_run_records_triggered_by(self):
        @flow(name="triggered_flow")
        def tf(_flow_run=None):
            pass

        run = tf.run(triggered_by="scheduler")
        assert run.triggered_by == "scheduler"

    def test_flow_run_injects_flow_run(self):
        received = {}

        @flow(name="inject_test_flow")
        def itf(_flow_run: FlowRun | None = None):
            received["run"] = _flow_run

        itf.run()
        assert "run" in received
        assert isinstance(received["run"], FlowRun)


@pytest.fixture
def isolated_registry():
    """Save and restore the singleton WorkflowRegistry's flows around each test."""
    reg = get_registry()
    saved = dict(reg._flows)
    yield reg
    reg._flows.clear()
    reg._flows.update(saved)


class TestWorkflowRegistry:
    def test_register_and_all_flows(self, isolated_registry):
        @flow(name="reg_flow_test_xyz")
        def rf(_flow_run=None):
            pass

        isolated_registry.register(rf)
        assert any(f.flow_name == "reg_flow_test_xyz" for f in isolated_registry.all_flows())

    def test_run_flow_by_name(self, isolated_registry):
        @flow(name="runnable_flow_test_xyz")
        def runnf(_flow_run=None):
            pass

        isolated_registry.register(runnf)
        run = isolated_registry.run_flow("runnable_flow_test_xyz")
        assert run is not None
        assert run.succeeded

    def test_run_flow_unknown_name_returns_none(self, isolated_registry):
        run = isolated_registry.run_flow("does_not_exist_xyz")
        assert run is None

    def test_all_runs_returns_list(self, isolated_registry):
        @flow(name="all_runs_flow_test_xyz")
        def arf(_flow_run=None):
            pass

        isolated_registry.register(arf)
        isolated_registry.run_flow("all_runs_flow_test_xyz")
        runs = isolated_registry.all_runs()
        assert isinstance(runs, list)
        assert len(runs) >= 1

    def test_stats_returns_dict(self, isolated_registry):
        stats = isolated_registry.stats()
        assert isinstance(stats, dict)
        assert "total_flows" in stats

    def test_get_registry_singleton(self):
        r1 = get_registry()
        r2 = get_registry()
        assert r1 is r2

    def test_get_returns_registered_flow(self, isolated_registry):
        @flow(name="get_test_flow_xyz")
        def gtf(_flow_run=None):
            pass

        isolated_registry.register(gtf)
        assert isolated_registry.get("get_test_flow_xyz") is gtf

    def test_get_unknown_returns_none(self, isolated_registry):
        assert isolated_registry.get("nonexistent_xyz") is None


# ---------------------------------------------------------------------------
# Built-in workflow flows
# ---------------------------------------------------------------------------

from workflows.data_pipeline_flow import data_pipeline_flow
from workflows.model_retraining_flow import model_retraining_flow
from workflows.report_generation_flow import report_generation_flow


class TestDataPipelineFlow:
    def test_flow_is_registered(self):
        reg = get_registry()
        assert any(f.flow_name == data_pipeline_flow.flow_name for f in reg.all_flows())

    def test_run_with_demo_source(self):
        run = data_pipeline_flow.run(source_path="demo")
        assert isinstance(run, FlowRun)

    def test_run_produces_task_results(self):
        run = data_pipeline_flow.run(source_path="demo")
        assert isinstance(run.task_results, list)
        assert len(run.task_results) >= 1

    def test_successful_run_has_succeeded_true(self):
        run = data_pipeline_flow.run(source_path="demo")
        assert run.succeeded

    def test_run_records_duration(self):
        run = data_pipeline_flow.run(source_path="demo")
        assert run.duration_s >= 0.0


class TestModelRetrainingFlow:
    def test_flow_is_registered(self):
        reg = get_registry()
        assert any(f.flow_name == model_retraining_flow.flow_name for f in reg.all_flows())

    def test_run_with_force_retrain(self):
        run = model_retraining_flow.run(model_name="impact_model", force_retrain=True)
        assert isinstance(run, FlowRun)
        assert run.succeeded

    def test_run_without_force(self):
        run = model_retraining_flow.run(model_name="attrition_model", force_retrain=False)
        assert isinstance(run, FlowRun)

    def test_run_has_task_results(self):
        run = model_retraining_flow.run(force_retrain=True)
        assert isinstance(run.task_results, list)


class TestReportGenerationFlow:
    def test_flow_is_registered(self):
        reg = get_registry()
        assert any(f.flow_name == report_generation_flow.flow_name for f in reg.all_flows())

    def test_run_with_report_type(self):
        run = report_generation_flow.run(
            report_type="weekly_risk",
            recipients=["admin@company.com"],
        )
        assert isinstance(run, FlowRun)
        assert run.succeeded

    def test_run_without_recipients(self):
        run = report_generation_flow.run(report_type="model_performance")
        assert isinstance(run, FlowRun)

    def test_run_produces_task_results(self):
        run = report_generation_flow.run(report_type="gdpr_compliance")
        assert len(run.task_results) >= 1


# ---------------------------------------------------------------------------
# ConnectorSchema / FieldMapping
# ---------------------------------------------------------------------------

from integration_hub.base_connector import (
    ConnectorSchema,
    ConnectorStatus,
    FieldMapping,
    SyncMode,
    SyncResult,
)


class TestFieldMapping:
    def test_basic_mapping(self):
        m = FieldMapping(source_field="Name", target_field="full_name")
        assert m.source_field == "Name"
        assert m.target_field == "full_name"

    def test_required_flag(self):
        m = FieldMapping("id", "employee_id", required=True)
        assert m.required

    def test_transform_none_by_default(self):
        m = FieldMapping("x", "y")
        assert m.transform is None

    def test_default_value(self):
        m = FieldMapping("salary", "annual_salary", default_value=0.0)
        assert m.default_value == 0.0


class TestConnectorSchema:
    def _schema(self) -> ConnectorSchema:
        return ConnectorSchema(
            connector_name="TestSystem",
            source_system="TestHRIS",
            field_mappings=[
                FieldMapping("EmpID", "employee_id", required=True),
                FieldMapping("EmpName", "full_name"),
                FieldMapping("EmpEmail", "email", transform="lower"),
                FieldMapping("Salary", "annual_salary", transform="salary_usd", default_value=0.0),
                FieldMapping("StartDate", "hire_date", transform="date_iso"),
            ],
        )

    def test_apply_maps_fields(self):
        schema = self._schema()
        record = {"EmpID": "E001", "EmpName": "Alice", "EmpEmail": "Alice@CO.COM",
                  "Salary": "120,000", "StartDate": "2022-01-15"}
        out = schema.apply(record)
        assert out["employee_id"] == "E001"
        assert out["full_name"] == "Alice"

    def test_apply_lower_transform(self):
        schema = self._schema()
        record = {"EmpID": "E001", "EmpEmail": "ALICE@COMPANY.COM"}
        out = schema.apply(record)
        assert out["email"] == "alice@company.com"

    def test_apply_salary_usd_transform(self):
        schema = self._schema()
        record = {"EmpID": "E001", "Salary": "85,500.00"}
        out = schema.apply(record)
        assert out["annual_salary"] == pytest.approx(85500.0)

    def test_apply_salary_with_dollar_sign(self):
        schema = self._schema()
        record = {"EmpID": "E001", "Salary": "$72,000"}
        out = schema.apply(record)
        assert out["annual_salary"] == pytest.approx(72000.0)

    def test_apply_date_iso_truncates(self):
        schema = self._schema()
        record = {"EmpID": "E001", "StartDate": "2019-07-04T08:00:00Z"}
        out = schema.apply(record)
        assert out["hire_date"] == "2019-07-04"

    def test_apply_uses_default_value_for_missing_field(self):
        schema = self._schema()
        record = {"EmpID": "E001"}
        out = schema.apply(record)
        assert out.get("annual_salary") == 0.0

    def test_apply_required_field_missing_logs_warning(self, caplog):
        import logging
        schema = self._schema()
        with caplog.at_level(logging.WARNING):
            schema.apply({})
        assert any("required" in r.message.lower() or "missing" in r.message.lower()
                   for r in caplog.records)

    def test_apply_batch_returns_dataframe(self):
        schema = self._schema()
        records = [
            {"EmpID": "E001", "EmpName": "Alice"},
            {"EmpID": "E002", "EmpName": "Bob"},
        ]
        df = schema.apply_batch(records)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2

    def test_apply_batch_maps_ids(self):
        schema = self._schema()
        records = [{"EmpID": "E001"}, {"EmpID": "E002"}]
        df = schema.apply_batch(records)
        assert set(df["employee_id"]) == {"E001", "E002"}

    def test_transform_upper(self):
        schema = ConnectorSchema(
            connector_name="T", source_system="S",
            field_mappings=[FieldMapping("dept", "department", transform="upper")],
        )
        out = schema.apply({"dept": "engineering"})
        assert out["department"] == "ENGINEERING"

    def test_missing_optional_field_not_in_output(self):
        schema = self._schema()
        record = {"EmpID": "E001"}
        out = schema.apply(record)
        assert "full_name" not in out  # optional, no default


# ---------------------------------------------------------------------------
# WorkdayConnector
# ---------------------------------------------------------------------------

from integration_hub.workday_connector import WorkdayConnector


class TestWorkdayConnector:
    def test_connect_demo_mode(self):
        conn = WorkdayConnector()
        ok = conn.connect()
        assert ok

    def test_status_after_connect(self):
        conn = WorkdayConnector()
        conn.connect()
        assert conn.status == ConnectorStatus.CONNECTED

    def test_test_connection_demo_mode(self):
        conn = WorkdayConnector()
        ok, msg = conn.test_connection()
        assert ok
        assert "demo" in msg.lower() or "connected" in msg.lower()

    def test_fetch_employees_returns_list(self):
        conn = WorkdayConnector()
        records = conn.fetch_employees()
        assert isinstance(records, list)
        assert len(records) > 0

    def test_demo_records_have_required_fields(self):
        conn = WorkdayConnector()
        for r in conn.fetch_employees():
            assert "Worker_ID" in r
            assert "Worker_Name" in r

    def test_name_property(self):
        conn = WorkdayConnector()
        assert conn.name == "Workday"

    def test_sync_returns_sync_result(self):
        conn = WorkdayConnector()
        result = conn.sync(SyncMode.FULL)
        assert isinstance(result, SyncResult)
        assert result.success
        assert result.records_fetched > 0

    def test_sync_records_duration(self):
        conn = WorkdayConnector()
        result = conn.sync()
        assert result.duration_s >= 0.0

    def test_status_dict_structure(self):
        conn = WorkdayConnector()
        conn.connect()
        d = conn.status_dict()
        assert "connector" in d
        assert "status" in d

    def test_last_sync_at_none_before_sync(self):
        conn = WorkdayConnector()
        assert conn.last_sync_at is None

    def test_last_sync_at_set_after_sync(self):
        conn = WorkdayConnector()
        conn.sync()
        assert conn.last_sync_at is not None

    def test_fetch_performance_returns_empty_list(self):
        conn = WorkdayConnector()
        assert conn.fetch_performance() == []


# ---------------------------------------------------------------------------
# BambooHRConnector
# ---------------------------------------------------------------------------

from integration_hub.bamboohr_connector import BambooHRConnector


class TestBambooHRConnector:
    def test_connect_demo_mode(self):
        conn = BambooHRConnector()
        ok = conn.connect()
        assert ok

    def test_test_connection_no_credentials(self):
        conn = BambooHRConnector(subdomain="", api_key="")
        ok, msg = conn.test_connection()
        assert ok
        assert "demo" in msg.lower()

    def test_fetch_employees_returns_list(self):
        conn = BambooHRConnector()
        records = conn.fetch_employees()
        assert isinstance(records, list)
        assert len(records) > 0

    def test_demo_records_have_required_fields(self):
        conn = BambooHRConnector()
        for r in conn.fetch_employees():
            assert "id" in r
            assert "displayName" in r

    def test_name_property(self):
        conn = BambooHRConnector()
        assert conn.name == "BambooHR"

    def test_sync_demo_mode(self):
        conn = BambooHRConnector()
        result = conn.sync()
        assert isinstance(result, SyncResult)
        assert result.success

    def test_status_after_connect(self):
        conn = BambooHRConnector()
        conn.connect()
        assert conn.status == ConnectorStatus.CONNECTED


# ---------------------------------------------------------------------------
# GenericAPIConnector / ConnectorRegistry
# ---------------------------------------------------------------------------

from integration_hub.generic_api_connector import (
    ConnectorRegistry,
    GenericAPIConnector,
    get_connector_registry,
)


class TestGenericAPIConnector:
    def _make_connector(self, auth_type: str = "none") -> GenericAPIConnector:
        schema = ConnectorSchema(
            connector_name="TestAPI",
            source_system="TestSystem",
            field_mappings=[FieldMapping("id", "employee_id", required=True)],
        )
        return GenericAPIConnector(
            name="TestAPI",
            schema=schema,
            base_url="https://example.com",
            auth_type=auth_type,
        )

    def test_test_connection_success(self):
        conn = self._make_connector()
        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_get.return_value = mock_resp
            ok, _ = conn.test_connection()
            assert ok

    def test_fetch_employees_list_response(self):
        conn = self._make_connector()
        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = [{"id": "1"}, {"id": "2"}]
            mock_resp.status_code = 200
            mock_get.return_value = mock_resp
            records = conn.fetch_employees()
            assert isinstance(records, list)
            assert len(records) == 2

    def test_fetch_employees_with_list_key(self):
        schema = ConnectorSchema(
            connector_name="KeyedAPI",
            source_system="Keyed",
            field_mappings=[FieldMapping("id", "employee_id")],
        )
        conn = GenericAPIConnector(
            name="KeyedAPI", schema=schema,
            base_url="https://example.com", list_key="data",
        )
        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"data": [{"id": "a"}], "total": 1}
            mock_get.return_value = mock_resp
            records = conn.fetch_employees()
            assert len(records) == 1

    def test_build_auth_basic(self):
        conn = self._make_connector(auth_type="basic")
        conn._auth_cfg = {"username": "user", "password": "pass"}
        auth = conn._build_auth()
        assert auth == ("user", "pass")

    def test_build_auth_bearer_injects_header(self):
        conn = self._make_connector(auth_type="bearer")
        conn._auth_cfg = {"token": "mytoken"}
        conn._build_auth()
        assert conn._headers.get("Authorization") == "Bearer mytoken"

    def test_build_auth_api_key_injects_header(self):
        conn = self._make_connector(auth_type="api_key")
        conn._auth_cfg = {"header_name": "X-My-Key", "api_key": "secret123"}
        conn._build_auth()
        assert conn._headers.get("X-My-Key") == "secret123"

    def test_build_auth_none_returns_none(self):
        conn = self._make_connector(auth_type="none")
        auth = conn._build_auth()
        assert auth is None

    def test_fetch_employees_http_error_returns_empty(self):
        conn = self._make_connector()
        with patch("httpx.get", side_effect=Exception("network error")):
            records = conn.fetch_employees()
            assert records == []

    def test_connect_calls_test_connection(self):
        conn = self._make_connector()
        with patch.object(conn, "test_connection", return_value=(True, "OK")) as mock_tc:
            conn.connect()
            mock_tc.assert_called_once()


class TestConnectorRegistry:
    def test_register_and_get(self):
        reg = ConnectorRegistry()
        conn = WorkdayConnector()
        reg.register(conn)
        result = reg.get("Workday")
        assert result is conn

    def test_get_unknown_returns_none(self):
        reg = ConnectorRegistry()
        assert reg.get("NonExistent") is None

    def test_all_returns_list(self):
        reg = ConnectorRegistry()
        reg.register(WorkdayConnector())
        reg.register(BambooHRConnector())
        assert len(reg.all()) == 2

    def test_status_summary_structure(self):
        reg = ConnectorRegistry()
        reg.register(WorkdayConnector())
        summary = reg.status_summary()
        assert isinstance(summary, list)
        assert "connector" in summary[0]
        assert "status" in summary[0]

    def test_get_connector_registry_has_workday_and_bamboohr(self):
        reg = get_connector_registry()
        names = {c.name for c in reg.all()}
        assert "Workday" in names
        assert "BambooHR" in names

    def test_get_connector_registry_singleton(self):
        r1 = get_connector_registry()
        r2 = get_connector_registry()
        assert r1 is r2
