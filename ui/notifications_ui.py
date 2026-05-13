"""Notifications & Integrations UI — Sprint 8.

Four tabs:
  1. Notification Center  — in-app bell, filter, mark-read, bundling
  2. Workflow Monitor     — flow status, manual triggers, run history
  3. Integration Hub      — connector status, sync controls, field mapping
  4. Preferences          — per-user channel and frequency settings
"""

from __future__ import annotations

import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from notifications.engine import (
    NotificationPriority, NotificationType, get_notification_engine,
)
from workflows.engine import FlowState, TaskState, get_registry
import workflows.data_pipeline_flow   # noqa: F401 — registers on import
import workflows.model_retraining_flow  # noqa: F401
import workflows.report_generation_flow  # noqa: F401
from integration_hub.generic_api_connector import get_connector_registry
from integration_hub.base_connector import SyncMode


# ---------------------------------------------------------------------------
# Colour maps
# ---------------------------------------------------------------------------

_PRIORITY_COLORS = {
    NotificationPriority.LOW:      "#27B97C",
    NotificationPriority.MEDIUM:   "#C8982A",
    NotificationPriority.HIGH:     "#F07020",
    NotificationPriority.CRITICAL: "#B91C1C",
}

_TYPE_ICONS = {
    NotificationType.RISK_ALERT:      "🔴",
    NotificationType.WORKFLOW_STATUS: "⚙️",
    NotificationType.COLLABORATION:   "🤝",
    NotificationType.SYSTEM:          "🔧",
    NotificationType.MODEL_DRIFT:     "📊",
    NotificationType.BUDGET_ALERT:    "💰",
    NotificationType.ATTRITION_ALERT: "⚠️",
}

_FLOW_STATE_COLORS = {
    FlowState.COMPLETED: "#27B97C",
    FlowState.FAILED:    "#F07020",
    FlowState.RUNNING:   "#C8982A",
    FlowState.PENDING:   "#6B7280",
    FlowState.CRASHED:   "#B91C1C",
}

_TASK_STATE_ICONS = {
    TaskState.COMPLETED: "✓",
    TaskState.FAILED:    "✗",
    TaskState.RUNNING:   "→",
    TaskState.PENDING:   "·",
    TaskState.RETRYING:  "↺",
    TaskState.SKIPPED:   "—",
}


def _kpi(label: str, value: str, sub: str = "", color: str = "#003366") -> None:
    st.markdown(
        f"""
        <div style="background:#fff; border:1px solid #E5E7EB; border-radius:8px;
                    padding:16px 20px; border-top:3px solid {color};">
          <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:9px;
                      font-weight:700; letter-spacing:2px; text-transform:uppercase;
                      color:#6B7280;">{label}</div>
          <div style="font-family:'Fraunces',Georgia,serif; font-size:26px;
                      font-weight:300; color:#1C1C2E; margin:6px 0 4px;">{value}</div>
          <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:11px;
                      color:#9CA3AF;">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

def render() -> None:
    engine   = get_notification_engine()
    registry = get_registry()

    # Hero
    st.markdown(
        """
        <div style="background-color:#003366; background-image:
          linear-gradient(rgba(255,255,255,.025) 1px, transparent 1px),
          linear-gradient(90deg, rgba(255,255,255,.025) 1px, transparent 1px);
          background-size:48px 48px; padding:40px 48px 32px;">
          <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:9px;
                      font-weight:700; letter-spacing:4px; text-transform:uppercase;
                      color:rgba(255,255,255,0.4); margin-bottom:10px;">
            SPRINT 8 · NOTIFICATIONS, WORKFLOWS & INTEGRATIONS
          </div>
          <h1 style="font-family:'Fraunces',Georgia,serif; font-size:28px;
                     font-weight:300; color:#fff; margin:0 0 8px;">
            Notifications &amp; <em style="color:#E8C46A; font-style:italic;">Integration Hub</em>
          </h1>
          <p style="font-family:'Plus Jakarta Sans',sans-serif; font-size:13px;
                    color:rgba(255,255,255,0.6); margin:0; max-width:560px;">
            Smart alerts, workflow automation, and HRIS connector management.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs([
        "🔔  Notification Center",
        "⚙️  Workflow Monitor",
        "🔗  Integration Hub",
        "⚙  Preferences",
    ])

    with tab1:
        _render_notifications(engine)
    with tab2:
        _render_workflows(registry)
    with tab3:
        _render_integrations()
    with tab4:
        _render_preferences(engine)


# ---------------------------------------------------------------------------
# Tab 1 — Notification Center
# ---------------------------------------------------------------------------

def _render_notifications(engine) -> None:
    demo_user_id = "U001"

    total      = engine.stats().get("total", 0)
    unread     = engine.unread_count(demo_user_id)
    bundles    = engine.all_bundles()

    # KPIs
    cols = st.columns(4)
    with cols[0]: _kpi("Total Notifications", str(total),   "all time",       "#003366")
    with cols[1]: _kpi("Unread",              str(unread),  "pending review",  "#F07020")
    with cols[2]: _kpi("Bundles",             str(len(bundles)), "digested",   "#C8982A")
    with cols[3]: _kpi("Channels Active",     "3",          "in-app, email, webhook", "#27B97C")

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    # Actions row
    col_filter, col_type, col_actions = st.columns([2, 2, 1])
    with col_filter:
        priority_filter = st.selectbox(
            "Filter by priority",
            ["All", "Critical", "High", "Medium", "Low"],
            key="notif_priority",
        )
    with col_type:
        type_filter = st.selectbox(
            "Filter by type",
            ["All"] + [t.value for t in NotificationType],
            key="notif_type",
        )
    with col_actions:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("Mark all read", key="mark_all_read"):
            engine.mark_all_read(demo_user_id)
            st.rerun()

    # Bundle digests section
    if bundles:
        with st.expander(f"📦 {len(bundles)} bundled digest(s)", expanded=False):
            for bundle in bundles[:5]:
                st.markdown(
                    f"**{bundle.title}** — {bundle.summary}  \n"
                    f"`{bundle.bundle_id[:8]}` · "
                    f"{bundle.created_at.strftime('%H:%M') if hasattr(bundle.created_at, 'strftime') else ''}"
                )
                for n in bundle.notifications[:3]:
                    icon = _TYPE_ICONS.get(n.notification_type, "•")
                    st.markdown(
                        f"  {icon} _{n.title}_",
                        help=n.body,
                    )

    # Notifications list
    priority_map = {
        "Critical": NotificationPriority.CRITICAL,
        "High":     NotificationPriority.HIGH,
        "Medium":   NotificationPriority.MEDIUM,
        "Low":      NotificationPriority.LOW,
    }
    ntype_map = {t.value: t for t in NotificationType}

    notifications = engine.for_user(
        demo_user_id,
        limit=100,
    )

    # Apply filters
    if priority_filter != "All":
        pf = priority_map[priority_filter]
        notifications = [n for n in notifications if n.priority == pf]
    if type_filter != "All":
        tf = ntype_map[type_filter]
        notifications = [n for n in notifications if n.notification_type == tf]

    if not notifications:
        st.info("No notifications match the current filters.", icon="🔔")
        return

    for n in notifications:
        color     = _PRIORITY_COLORS.get(n.priority, "#6B7280")
        icon      = _TYPE_ICONS.get(n.notification_type, "•")
        is_read   = n.is_read_by(demo_user_id)
        bg        = "#F9FAFB" if is_read else "#fff"
        border_w  = "1px" if is_read else "2px"

        col_body, col_action = st.columns([9, 1])
        with col_body:
            st.markdown(
                f"""
                <div style="background:{bg}; border:{border_w} solid {color}33;
                            border-left:4px solid {color}; border-radius:8px;
                            padding:12px 16px; margin-bottom:8px;">
                  <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                    <span style="font-size:16px;">{icon}</span>
                    <span style="font-family:'Plus Jakarta Sans',sans-serif; font-size:13px;
                                 font-weight:{'400' if is_read else '600'}; color:#1C1C2E;">
                      {n.title}
                    </span>
                    <span style="font-family:'Plus Jakarta Sans',sans-serif; font-size:10px;
                                 background:{color}22; color:{color}; border:1px solid {color}44;
                                 border-radius:3px; padding:1px 6px; font-weight:600;">
                      {n.priority.value.upper()}
                    </span>
                    {'<span style="font-size:10px; color:#9CA3AF; margin-left:4px;">✓ read</span>' if is_read else ''}
                  </div>
                  <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:12px;
                               color:#4B5563; padding-left:28px; line-height:1.6;">{n.body}</div>
                  <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:10px;
                               color:#9CA3AF; padding-left:28px; margin-top:4px;">
                    {n.source} · {n.created_at.strftime("%Y-%m-%d %H:%M") if hasattr(n.created_at, "strftime") else ""}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_action:
            if not is_read:
                if st.button("✓", key=f"read_{n.notification_id}", help="Mark as read"):
                    engine.mark_read(n.notification_id, demo_user_id)
                    st.rerun()


# ---------------------------------------------------------------------------
# Tab 2 — Workflow Monitor
# ---------------------------------------------------------------------------

def _render_workflows(registry) -> None:
    st.markdown("### Workflow Monitor")

    flows = registry.all_flows()
    stats = registry.stats()

    # KPIs
    cols = st.columns(4)
    with cols[0]: _kpi("Registered Flows", str(stats["total_flows"]), "defined",   "#003366")
    with cols[1]: _kpi("Total Runs",       str(stats["total_runs"]),  "all time",  "#336699")
    with cols[2]: _kpi("Completed",        str(stats["completed"]),   "successful","#27B97C")
    with cols[3]: _kpi("Failed",           str(stats["failed"]),      "errored",   "#F07020")

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    # Flow cards + manual trigger
    st.markdown("#### Flows")
    for f in flows:
        last = f.last_run
        col_info, col_btn = st.columns([5, 1])
        with col_info:
            state_color = _FLOW_STATE_COLORS.get(
                last.state if last else FlowState.PENDING, "#6B7280"
            )
            last_status = last.state.value if last else "never run"
            last_dur    = f"{last.duration_s:.1f}s" if last else "—"
            last_ts     = last.started_at[:16].replace("T", " ") if last else "—"

            st.markdown(
                f"""
                <div style="background:#fff; border:1px solid #E5E7EB; border-radius:8px;
                            padding:14px 18px; margin-bottom:8px;
                            border-left:4px solid {state_color};">
                  <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:14px;
                               font-weight:600; color:#1C1C2E;">{f.flow_name}</div>
                  <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:11px;
                               color:#6B7280; margin-top:4px;">{f.description}</div>
                  <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:10px;
                               color:{state_color}; margin-top:6px; font-weight:600;">
                    {last_status.upper()} · {last_dur} · {last_ts}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_btn:
            st.markdown("<div style='height:22px'></div>", unsafe_allow_html=True)
            if st.button("▶ Run", key=f"run_{f.flow_name}", use_container_width=True):
                with st.spinner(f"Running '{f.flow_name}'…"):
                    run = f.run(triggered_by="manual")
                color = "#27B97C" if run.succeeded else "#F07020"
                icon  = "✓" if run.succeeded else "✗"
                st.markdown(
                    f'<p style="color:{color}; font-size:12px;">'
                    f'{icon} {run.summary()}</p>',
                    unsafe_allow_html=True,
                )

    # Run history table
    runs = registry.all_runs(limit=20)
    if runs:
        st.markdown("#### Recent Run History")
        run_rows = []
        for r in runs:
            run_rows.append({
                "Flow":       r.flow_name,
                "State":      r.state.value,
                "Duration":   f"{r.duration_s:.1f}s",
                "Tasks":      r.n_tasks,
                "Failed":     r.n_failed,
                "Started":    r.started_at[:16].replace("T", " "),
                "Triggered":  r.triggered_by,
            })
        df = pd.DataFrame(run_rows)
        st.dataframe(df, hide_index=True, use_container_width=True)

        # Task detail for last run per flow
        with st.expander("Task-level detail (last run per flow)", expanded=False):
            for f in flows:
                last = f.last_run
                if last and last.task_results:
                    st.markdown(f"**{f.flow_name}**")
                    rows = []
                    for t in last.task_results:
                        rows.append({
                            "Task":     t.task_name,
                            "State":    f"{_TASK_STATE_ICONS.get(t.state, '?')} {t.state.value}",
                            "Duration": f"{t.duration_s:.3f}s",
                            "Attempt":  t.attempt,
                            "Error":    t.error[:60] if t.error else "",
                        })
                    st.dataframe(pd.DataFrame(rows), hide_index=True,
                                 use_container_width=True)


# ---------------------------------------------------------------------------
# Tab 3 — Integration Hub
# ---------------------------------------------------------------------------

def _render_integrations() -> None:
    st.markdown("### Integration Hub")
    st.caption("Configure and manage HRIS/ERP connectors.")

    reg = get_connector_registry()
    connectors = reg.all()

    # Status KPIs
    connected = sum(1 for c in connectors
                    if c.status.value in ("connected", "configured"))
    cols = st.columns(3)
    with cols[0]: _kpi("Connectors",  str(len(connectors)), "registered", "#003366")
    with cols[1]: _kpi("Connected",   str(connected),       "operational","#27B97C")
    with cols[2]: _kpi("Sync Mode",   "Demo",               "incremental in prod", "#C8982A")

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    # Connector cards
    st.markdown("#### Configured Connectors")
    for connector in connectors:
        col_info, col_test, col_sync = st.columns([5, 1, 1])
        status_color = {
            "connected":    "#27B97C",
            "configured":   "#C8982A",
            "disconnected": "#6B7280",
            "error":        "#F07020",
        }.get(connector.status.value, "#6B7280")

        with col_info:
            st.markdown(
                f"""
                <div style="background:#fff; border:1px solid #E5E7EB; border-radius:8px;
                            padding:14px 18px; margin-bottom:8px;
                            border-left:4px solid {status_color};">
                  <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:14px;
                               font-weight:600; color:#1C1C2E;">{connector.name}</div>
                  <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:11px;
                               color:#6B7280;">{connector.source_system}</div>
                  <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:10px;
                               color:{status_color}; font-weight:600; margin-top:4px;">
                    {connector.status.value.upper()} · Last sync: {connector.last_sync_at or 'Never'}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_test:
            st.markdown("<div style='height:22px'></div>", unsafe_allow_html=True)
            if st.button("Test", key=f"test_{connector.name}", use_container_width=True):
                ok, msg = connector.test_connection()
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

        with col_sync:
            st.markdown("<div style='height:22px'></div>", unsafe_allow_html=True)
            if st.button("Sync", key=f"sync_{connector.name}", use_container_width=True):
                with st.spinner("Syncing…"):
                    result = connector.sync(mode=SyncMode.INCREMENTAL)
                if result.success:
                    st.success(
                        f"Synced {result.records_fetched} records in {result.duration_s:.1f}s"
                    )
                else:
                    st.error(f"Sync failed: {'; '.join(result.errors)}")

    # Field mapping explorer
    st.markdown("#### Field Mapping Reference")
    connector_name = st.selectbox(
        "Connector",
        [c.name for c in connectors],
        key="mapping_connector",
    )
    selected = reg.get(connector_name)
    if selected:
        mapping_rows = []
        for m in selected._schema.field_mappings:
            mapping_rows.append({
                "Source field":   m.source_field,
                "EIBO field":     m.target_field,
                "Transform":      m.transform or "—",
                "Default":        str(m.default_value) if m.default_value is not None else "—",
                "Required":       "✓" if m.required else "—",
            })
        if mapping_rows:
            st.dataframe(
                pd.DataFrame(mapping_rows),
                hide_index=True,
                use_container_width=True,
            )

    # Add connector placeholder
    st.markdown("#### Add New Connector")
    st.info(
        "**Generic REST API connector** supports any HRIS with a JSON API. "
        "Configure authentication (Basic, Bearer, API key), field mappings, "
        "and sync schedule below.",
        icon="🔗",
    )
    with st.expander("Configure new connector", expanded=False):
        col_a, col_b = st.columns(2)
        with col_a:
            st.text_input("Connector name", placeholder="My HRIS", key="new_conn_name")
            st.text_input("Base URL", placeholder="https://api.myhris.com", key="new_conn_url")
            st.selectbox("Auth type", ["none", "basic", "bearer", "api_key"],
                         key="new_conn_auth")
        with col_b:
            st.text_input("Employees endpoint", value="/employees", key="new_conn_ep")
            st.text_input("Array key in response", placeholder="data",
                          key="new_conn_key",
                          help="Leave blank if response IS the array")
            st.selectbox("Sync frequency",
                         ["Manual only", "Hourly", "Daily", "Weekly"],
                         key="new_conn_freq")
        st.button("Save connector (demo — no-op)", key="save_new_conn",
                  help="In production this would persist the config to the database")


# ---------------------------------------------------------------------------
# Tab 4 — Preferences
# ---------------------------------------------------------------------------

def _render_preferences(engine) -> None:
    st.markdown("### Notification Preferences")
    st.caption("Configure how and when you receive notifications.")

    # Channel preferences
    st.markdown("#### Channels")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        in_app = st.toggle("In-app notifications", value=True, key="pref_inapp")
        st.caption("Always-on — cannot be disabled")
    with col_b:
        email = st.toggle("Email notifications", value=False, key="pref_email")
        if email:
            st.text_input("Email address", placeholder="you@company.com", key="pref_email_addr")
    with col_c:
        webhook = st.toggle("Webhook (Slack / Teams)", value=False, key="pref_webhook")
        if webhook:
            st.text_input("Webhook URL", placeholder="https://hooks.slack.com/…",
                          key="pref_webhook_url")

    # Per-type frequency
    st.markdown("#### Alert Frequency")
    st.caption("Control how often each alert type reaches you.")

    freq_options = ["Immediate", "Hourly digest", "Daily digest", "Disabled"]
    type_labels  = {
        NotificationType.ATTRITION_ALERT:   "Attrition alerts",
        NotificationType.RISK_ALERT:        "Risk alerts",
        NotificationType.BUDGET_ALERT:      "Budget alerts",
        NotificationType.MODEL_DRIFT:       "Model drift",
        NotificationType.WORKFLOW_STATUS:   "Workflow status",
        NotificationType.COLLABORATION:     "Collaboration events",
        NotificationType.SYSTEM:            "System events",
    }

    for ntype, label in type_labels.items():
        default = 0 if ntype in (NotificationType.ATTRITION_ALERT,
                                  NotificationType.RISK_ALERT) else 1
        st.selectbox(
            label,
            freq_options,
            index=default,
            key=f"pref_freq_{ntype.value}",
        )

    # Do-not-disturb
    st.markdown("#### Do Not Disturb")
    dnd = st.toggle("Enable Do Not Disturb", value=False, key="pref_dnd")
    if dnd:
        col_start, col_end = st.columns(2)
        with col_start:
            st.number_input("DND start hour (UTC)", 0, 23, 22, key="pref_dnd_start")
        with col_end:
            st.number_input("DND end hour (UTC)", 0, 23, 8, key="pref_dnd_end")
        st.caption("Critical alerts always bypass Do Not Disturb.")

    # Bundle window
    st.markdown("#### Smart Bundling")
    st.slider(
        "Bundle related alerts within",
        5, 60, 15, 5,
        format="%d min",
        key="pref_bundle_window",
    )
    st.caption(
        "Alerts of the same type arriving within this window are grouped into a single digest."
    )

    if st.button("Save preferences (demo — no-op)", type="primary", key="save_prefs"):
        st.success("Preferences saved.", icon="✓")
