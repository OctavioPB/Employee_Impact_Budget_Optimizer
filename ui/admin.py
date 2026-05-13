"""Admin Panel — system configuration, user management, audit, and health.

Accessible only to Admin-role users. Four tabs:
  1. Users & Roles
  2. Audit Trail
  3. System Health
  4. Compliance Reports
"""

from __future__ import annotations

import datetime
import json
import platform
import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from auth.rbac import (
    DEMO_USERS, AccessControl, Permission, Role, User,
    _ROLE_DESCRIPTIONS, _ROLE_PERMISSIONS,
)
from audit.compliance_reports import ComplianceReportGenerator
from audit.logger import EventCategory, EventSeverity, get_audit_logger, log_admin
from audit.trail_viewer import TrailViewer


# ---------------------------------------------------------------------------
# Helper — colours
# ---------------------------------------------------------------------------

_ROLE_COLORS = {
    Role.VIEWER:    "#6B7280",
    Role.ANALYST:   "#336699",
    Role.MANAGER:   "#27B97C",
    Role.DIRECTOR:  "#7C4DBD",
    Role.EXECUTIVE: "#C8982A",
    Role.ADMIN:     "#F07020",
}

_SEVERITY_COLORS = {
    "info":     "#27B97C",
    "warning":  "#C8982A",
    "critical": "#F07020",
}

_OUTCOME_COLORS = {
    "success": "#27B97C",
    "failure": "#F07020",
    "blocked": "#C8982A",
}


def _badge(label: str, color: str) -> str:
    return (
        f'<span style="background:{color}22; color:{color}; '
        f'border:1px solid {color}66; border-radius:4px; '
        f'padding:2px 8px; font-size:10px; font-weight:600; '
        f'font-family:\'Plus Jakarta Sans\',sans-serif;">{label}</span>'
    )


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
    viewer = TrailViewer()
    audit  = get_audit_logger()

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
            SPRINT 7 · ENTERPRISE READINESS
          </div>
          <h1 style="font-family:'Fraunces',Georgia,serif; font-size:28px;
                     font-weight:300; color:#fff; margin:0 0 8px;">
            Admin <em style="color:#E8C46A; font-style:italic;">Panel</em>
          </h1>
          <p style="font-family:'Plus Jakarta Sans',sans-serif; font-size:13px;
                    color:rgba(255,255,255,0.6); margin:0; max-width:560px;">
            User management, audit trail, system health, and compliance reports.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs([
        "👥  Users & Roles",
        "🔍  Audit Trail",
        "🩺  System Health",
        "📋  Compliance",
    ])

    with tab1:
        _render_users()
    with tab2:
        _render_audit(viewer)
    with tab3:
        _render_health(audit)
    with tab4:
        _render_compliance()


# ---------------------------------------------------------------------------
# Tab 1 — Users & Roles
# ---------------------------------------------------------------------------

def _render_users() -> None:
    st.markdown("### Users & Role Management")
    st.caption(
        "RBAC enforces data-level isolation. Salary and PII visibility "
        "are automatically scoped to each role."
    )

    # Role reference table
    with st.expander("Role hierarchy & permissions reference", expanded=False):
        role_rows = []
        for role in Role:
            perms = _ROLE_PERMISSIONS[role]
            role_rows.append({
                "Role":         role.label,
                "Level":        role.value,
                "Description":  role.description,
                "Salary view":  (
                    "Full" if Permission.VIEW_SALARY_FULL in perms
                    else "Range" if Permission.VIEW_SALARY_RANGE in perms
                    else "Masked"
                ),
                "PII view":     (
                    "Full" if Permission.VIEW_PII_FULL in perms
                    else "Partial" if Permission.VIEW_PII_PARTIAL in perms
                    else "Masked"
                ),
                "Simulation":   "✓" if Permission.RUN_SIMULATION in perms else "—",
                "Override":     "✓" if Permission.OVERRIDE_DECISION in perms else "—",
                "Org-wide":     "✓" if Permission.ORG_WIDE_ACCESS in perms else "—",
                "Admin":        "✓" if Permission.MANAGE_USERS in perms else "—",
            })
        st.dataframe(
            pd.DataFrame(role_rows),
            hide_index=True,
            use_container_width=True,
        )

    st.markdown("#### Active Users")

    # KPI row
    cols = st.columns(4)
    active_users  = [u for u in DEMO_USERS if u.is_active]
    admin_count   = sum(1 for u in active_users if u.role == Role.ADMIN)
    exec_count    = sum(1 for u in active_users if u.role >= Role.DIRECTOR)
    analyst_count = sum(1 for u in active_users if u.role <= Role.ANALYST)

    with cols[0]: _kpi("Total Users",      str(len(DEMO_USERS)),  "registered",      "#003366")
    with cols[1]: _kpi("Active",           str(len(active_users)), "accounts",        "#27B97C")
    with cols[2]: _kpi("Admins",           str(admin_count),      "with full access", "#F07020")
    with cols[3]: _kpi("Analysts / Viewers", str(analyst_count),  "read-oriented",   "#C8982A")

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    # User table
    user_rows = []
    for u in DEMO_USERS:
        color = _ROLE_COLORS.get(u.role, "#6B7280")
        user_rows.append({
            "User ID":    u.user_id,
            "Name":       u.full_name,
            "Email":      u.email,
            "Role":       u.role.label,
            "Dept Scope": ", ".join(u.departments) if u.departments else "All departments",
            "Active":     "✓" if u.is_active else "✗",
        })

    st.dataframe(
        pd.DataFrame(user_rows),
        hide_index=True,
        use_container_width=True,
        column_config={
            "Role": st.column_config.TextColumn("Role"),
            "Active": st.column_config.TextColumn("Active"),
        },
    )

    st.info(
        "**Demo mode:** User management is read-only. In production, invite users "
        "via OAuth2/OIDC (Google Workspace, Azure AD, Okta) or local auth.",
        icon="ℹ️",
    )

    # Permission drill-down
    st.markdown("#### Permission Inspector")
    selected_role_name = st.selectbox(
        "Select a role to inspect its permissions",
        options=[r.label for r in Role],
        key="role_inspector",
    )
    selected_role = Role.from_string(selected_role_name)
    perms = sorted(_ROLE_PERMISSIONS[selected_role])

    perm_cols = st.columns(3)
    for i, perm in enumerate(perms):
        with perm_cols[i % 3]:
            st.markdown(
                f'<div style="font-family:\'Plus Jakarta Sans\',sans-serif; '
                f'font-size:11px; color:#27B97C; padding:2px 0;">✓ {perm}</div>',
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Tab 2 — Audit Trail
# ---------------------------------------------------------------------------

def _render_audit(viewer: TrailViewer) -> None:
    st.markdown("### Audit Trail Viewer")

    # Filters row
    col_cat, col_out, col_sev, col_hours = st.columns([2, 1.5, 1.5, 1.5])
    with col_cat:
        cat_options = ["All"] + [c.value for c in EventCategory]
        selected_cat = st.selectbox("Category", cat_options, key="audit_cat")
    with col_out:
        selected_out = st.selectbox("Outcome", ["All", "success", "failure", "blocked"],
                                    key="audit_out")
    with col_sev:
        selected_sev = st.selectbox("Severity", ["All", "info", "warning", "critical"],
                                    key="audit_sev")
    with col_hours:
        hours_back = st.selectbox("Time window", [1, 6, 24, 72, 168],
                                   format_func=lambda h: f"Last {h}h", key="audit_hours")

    search_term = st.text_input(
        "Search (user email or action)", placeholder="e.g. morgan@demo.eibo",
        key="audit_search",
    )

    df = viewer.events_df(
        category   = EventCategory(selected_cat) if selected_cat != "All" else None,
        outcome    = selected_out if selected_out != "All" else None,
        severity   = EventSeverity(selected_sev) if selected_sev != "All" else None,
        user_email = search_term.strip() if search_term else None,
        hours_back = hours_back,
        limit      = 500,
    )

    # Summary KPIs
    stats = viewer.stats()
    kpi_cols = st.columns(4)
    with kpi_cols[0]: _kpi("Total Events",    str(stats["total_events"]), "in buffer",       "#003366")
    with kpi_cols[1]: _kpi("This Window",     str(len(df)),               f"last {hours_back}h", "#336699")
    with kpi_cols[2]: _kpi("Failures",        str(stats.get("failure_count", 0)), "blocked/denied", "#F07020")
    with kpi_cols[3]: _kpi("Unique Users",    str(df["user_email"].nunique()) if not df.empty else "0", "active", "#27B97C")

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    # Event volume chart
    if not df.empty:
        volume_df = viewer.event_volume_by_hour(hours_back=hours_back)
        if not volume_df.empty:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=volume_df["hour"],
                y=volume_df["count"],
                marker_color="#003366",
                name="Events",
            ))
            fig.update_layout(
                title="Event volume over time",
                height=200,
                margin=dict(l=0, r=0, t=36, b=0),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor="#F3F4F6"),
            )
            st.plotly_chart(fig, use_container_width=True, key="audit_volume_chart")

    # Events table
    if df.empty:
        st.info("No events match the current filters.", icon="ℹ️")
    else:
        display_df = df[[
            "timestamp", "category", "severity", "user_email",
            "user_role", "action", "resource", "outcome"
        ]].copy()
        display_df["timestamp"] = display_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")

        st.dataframe(
            display_df,
            hide_index=True,
            use_container_width=True,
            height=350,
        )

        # Export
        csv_data = viewer.export_csv(hours_back=hours_back)
        st.download_button(
            label="Export audit log (CSV)",
            data=csv_data,
            file_name=f"eibo_audit_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            key="audit_export_btn",
        )

    # Activity by user
    st.markdown("#### Activity by User")
    activity = viewer.activity_by_user(hours_back=hours_back)
    if activity.empty:
        st.caption("No activity in this window.")
    else:
        activity["last_active"] = pd.to_datetime(activity["last_active"]).dt.strftime("%H:%M:%S")
        st.dataframe(activity, hide_index=True, use_container_width=True)


# ---------------------------------------------------------------------------
# Tab 3 — System Health
# ---------------------------------------------------------------------------

def _render_health(audit) -> None:
    st.markdown("### System Health Dashboard")

    # Service status
    services = [
        ("Streamlit UI",        True,  "v" + st.__version__),
        ("RBAC Engine",         True,  "in-process"),
        ("Audit Logger",        True,  f"{audit.stats()['total_events']} events buffered"),
        ("Demo Data Generator", True,  "ready"),
        ("ILP Solver (PuLP)",   _check_import("pulp"),   _get_version("pulp")),
        ("ML Engine (sklearn)", _check_import("sklearn"), _get_version("sklearn")),
        ("Forecasting (Prophet)", _check_import("prophet"), _get_version("prophet")),
        ("Network (NetworkX)",  _check_import("networkx"), _get_version("networkx")),
        ("PostgreSQL (psycopg2)", _check_import("psycopg2"), "connector ready"),
        ("XGBoost",             _check_import("xgboost"), _get_version("xgboost")),
    ]

    st.markdown("#### Service Status")
    svc_cols = st.columns(2)
    for i, (name, ok, detail) in enumerate(services):
        color  = "#27B97C" if ok else "#F07020"
        icon   = "●" if ok else "○"
        status = "Operational" if ok else "Unavailable"
        with svc_cols[i % 2]:
            st.markdown(
                f'<div style="background:#fff; border:1px solid #E5E7EB; border-radius:6px; '
                f'padding:10px 14px; margin-bottom:8px; display:flex; align-items:center; gap:10px;">'
                f'<span style="color:{color}; font-size:14px;">{icon}</span>'
                f'<div>'
                f'<div style="font-family:\'Plus Jakarta Sans\',sans-serif; font-size:12px; '
                f'font-weight:600; color:#1C1C2E;">{name}</div>'
                f'<div style="font-family:\'Plus Jakarta Sans\',sans-serif; font-size:10px; '
                f'color:#6B7280;">{status} · {detail}</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

    # Runtime info
    st.markdown("#### Runtime Environment")
    env_df = pd.DataFrame([
        {"Property": "Python version",    "Value": sys.version.split(" ")[0]},
        {"Property": "Platform",          "Value": platform.platform()},
        {"Property": "Streamlit version", "Value": st.__version__},
        {"Property": "Audit buffer size", "Value": str(audit.stats()["buffer_capacity"])},
        {"Property": "Events in buffer",  "Value": str(audit.stats()["total_events"])},
    ])
    st.dataframe(env_df, hide_index=True, use_container_width=True)

    # Audit event breakdown
    stats = audit.stats()
    if stats["total_events"] > 0:
        st.markdown("#### Audit Event Breakdown")
        cat_data = stats.get("by_category", {})
        if cat_data:
            fig = go.Figure(go.Bar(
                x=list(cat_data.keys()),
                y=list(cat_data.values()),
                marker_color=["#003366", "#336699", "#27B97C", "#C8982A",
                              "#F07020", "#7C4DBD", "#6B7280"][:len(cat_data)],
            ))
            fig.update_layout(
                title="Events by category",
                height=220,
                margin=dict(l=0, r=0, t=36, b=0),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor="#F3F4F6"),
            )
            st.plotly_chart(fig, use_container_width=True, key="health_cat_chart")

    # Configuration panel
    st.markdown("#### Platform Configuration")
    with st.expander("Session & security settings", expanded=False):
        col_a, col_b = st.columns(2)
        with col_a:
            timeout = st.slider("Session timeout (minutes)", 15, 480, 60, 15,
                                key="cfg_timeout")
            st.caption(f"Current: {timeout} min — applied to new sessions")
        with col_b:
            max_export = st.number_input("Max export rows", 100, 100_000, 10_000, 100,
                                          key="cfg_max_export")
            st.caption(f"Limit: {max_export:,} rows per CSV export")

    with st.expander("Data retention policy", expanded=False):
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.number_input("Audit log retention (days)",   30, 730, 365, 30, key="ret_audit")
        with col_b:
            st.number_input("Simulation history (days)",    7,  365,  90, 7,  key="ret_sim")
        with col_c:
            st.number_input("Personal data archival (days)", 90, 3650, 365, 90, key="ret_pii")
        st.info(
            "Retention policy changes take effect on the next scheduled purge cycle.",
            icon="ℹ️",
        )


# ---------------------------------------------------------------------------
# Tab 4 — Compliance Reports
# ---------------------------------------------------------------------------

def _render_compliance() -> None:
    st.markdown("### Compliance & Regulatory Reports")
    gen = ComplianceReportGenerator()

    report_type = st.radio(
        "Report type",
        ["GDPR Data Processing", "Data Access Summary", "Model Decision Impact"],
        horizontal=True,
        key="compliance_type",
    )

    days_back = st.slider(
        "Report window (days)", 1, 90,
        30 if report_type != "Data Access Summary" else 7,
        key="compliance_days",
    )

    if st.button("Generate report", type="primary", key="gen_report_btn"):
        with st.spinner("Generating…"):
            if report_type == "GDPR Data Processing":
                report = gen.gdpr_data_processing_report(days_back)
            elif report_type == "Data Access Summary":
                report = gen.access_summary_report(days_back)
            else:
                report = gen.model_decision_report(days_back)

        md = report.to_markdown()

        st.success(f"Report generated: **{report.title}**", icon="✓")

        st.download_button(
            label="Download report (Markdown)",
            data=md,
            file_name=(
                f"eibo_compliance_{report_type.lower().replace(' ', '_')}_"
                f"{datetime.datetime.utcnow().strftime('%Y%m%d')}.md"
            ),
            mime="text/markdown",
            key="compliance_dl_btn",
        )

        # Preview each section
        for sec in report.sections:
            with st.expander(sec["heading"], expanded=False):
                content = sec["content"]
                if isinstance(content, pd.DataFrame):
                    if content.empty:
                        st.caption("No data available.")
                    else:
                        st.dataframe(content, hide_index=True, use_container_width=True)
                else:
                    st.markdown(content)
    else:
        st.info(
            "Select report type and window above, then click **Generate report** to preview "
            "and download the compliance document.",
            icon="📋",
        )

    # GDPR info
    st.markdown("---")
    st.markdown("#### Compliance Posture")
    posture_items = [
        ("Data localisation",   True,  "All processing on-premises; no data leaves infrastructure"),
        ("Encryption at rest",  True,  "PostgreSQL transparent data encryption (configurable)"),
        ("Access logging",      True,  "All access events captured in immutable audit log"),
        ("Right of access",     True,  "HR Admins can export individual data on request"),
        ("Right to erasure",    True,  "Anonymisation pipeline available for long-term archival"),
        ("Human-in-the-loop",   True,  "No automated HR decisions; all recommendations require human confirmation"),
        ("Algorithmic bias",    True,  "Fairness audit runs monthly; SHAP attribution for all ML scores"),
        ("Data minimisation",   True,  "Only HR data required for workforce analysis is collected"),
    ]

    for label, ok, detail in posture_items:
        icon  = "✓" if ok else "✗"
        color = "#27B97C" if ok else "#F07020"
        st.markdown(
            f'<div style="font-family:\'Plus Jakarta Sans\',sans-serif; font-size:12px; '
            f'padding:5px 0; border-bottom:1px solid #F3F4F6;">'
            f'<span style="color:{color}; font-weight:700;">{icon}</span> '
            f'<strong>{label}</strong> — {detail}</div>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _check_import(module: str) -> bool:
    try:
        __import__(module)
        return True
    except ImportError:
        return False


def _get_version(module: str) -> str:
    try:
        mod = __import__(module)
        return "v" + getattr(mod, "__version__", "?")
    except ImportError:
        return "not installed"
