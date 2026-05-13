"""Sprint 4 — Drill-Down, Graphs & Interactive Exploration.

Navigation: Organization → Department → Team → Employee
Plus: a standalone Graph Explorer view.

Session-state keys (all prefixed dd_ to avoid collision with simulator):
    dd_view:      "org" | "dept" | "team" | "employee" | "graph"
    dd_dept:      selected department name (str | None)
    dd_team:      selected team_id (str | None)
    dd_employee:  selected employee_id (str | None)
    dd_sim_status: dict[employee_id → status] — injected from simulator if available
"""

import logging

import networkx as nx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ui.components.brand import hero_section
from ui.components.graph_viz import (
    build_org_graph,
    filter_graph_to_scope,
    render_network_graph,
    status_legend_html,
)
from ui.components.profile_card import render_employee_profile
from ui.components.exports import (
    df_to_csv_bytes,
    generate_pdf_summary,
    tables_to_excel_bytes,
)
from ui.data_loader import DashboardData, load_dashboard_data

logger = logging.getLogger(__name__)

# BRAND palette
_NAVY  = "#003366"
_GOLD  = "#C8982A"
_GREEN = "#27B97C"
_ORANGE = "#F07020"
_LIGHT = "#F4F6F9"

_CHART_SERIES = [_NAVY, _GREEN, "#7C4DBD", _ORANGE]


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------

_DEFAULTS: dict = {
    "dd_view":     "org",
    "dd_dept":     None,
    "dd_team":     None,
    "dd_employee": None,
    "dd_sim_status": {},
}


def _init() -> None:
    for k, v in _DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _nav_to(view: str, dept=None, team=None, employee=None) -> None:
    st.session_state.dd_view = view
    if dept is not None:
        st.session_state.dd_dept = dept
    if team is not None:
        st.session_state.dd_team = team
    if employee is not None:
        st.session_state.dd_employee = employee
    st.rerun()


def _go_back() -> None:
    view = st.session_state.dd_view
    if view == "employee":
        st.session_state.dd_view = "team"
    elif view == "team":
        st.session_state.dd_view = "dept"
    elif view in ("dept", "graph"):
        st.session_state.dd_view = "org"
    else:
        st.session_state.dd_view = "org"
    st.rerun()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def render() -> None:
    _init()

    data = load_dashboard_data(
        demo_mode=st.session_state.get("demo_mode", True),
        scenario_id=st.session_state.get("demo_scenario", "A"),
        size=st.session_state.get("demo_size", "medium"),
    )

    _render_breadcrumb()
    _render_export_bar(data)

    view = st.session_state.dd_view

    if view == "org":
        _render_org_view(data)
    elif view == "dept":
        _render_dept_view(data, str(st.session_state.dd_dept or ""))
    elif view == "team":
        _render_team_view(data, str(st.session_state.dd_team or ""))
    elif view == "employee":
        _render_employee_view(data, str(st.session_state.dd_employee or ""))
    elif view == "graph":
        _render_graph_view(data)
    else:
        _render_org_view(data)


# ---------------------------------------------------------------------------
# Breadcrumb navigation
# ---------------------------------------------------------------------------

def _render_breadcrumb() -> None:
    view = st.session_state.dd_view
    dept = st.session_state.dd_dept
    team_id = st.session_state.dd_team
    employee_id = st.session_state.dd_employee

    crumbs = [("Organization", "org")]
    if view in ("dept", "team", "employee") and dept:
        crumbs.append((dept, "dept"))
    if view in ("team", "employee") and team_id:
        crumbs.append((f"Team {team_id}", "team"))
    if view == "employee" and employee_id:
        crumbs.append((employee_id[:10], "employee"))
    if view == "graph":
        crumbs.append(("Graph Explorer", "graph"))

    parts = []
    for label, target_view in crumbs[:-1]:
        parts.append(f'<span style="cursor:pointer;color:{_GOLD};font-weight:500;">{label}</span>')
        parts.append('<span style="color:rgba(0,51,102,0.3);margin:0 8px;">›</span>')
    parts.append(
        f'<span style="color:{_NAVY};font-weight:600;">{crumbs[-1][0]}</span>'
    )

    nav_html = "".join(parts)
    col_crumb, col_back = st.columns([5, 1])
    with col_crumb:
        st.markdown(
            f'<div style="font-family:\'Plus Jakarta Sans\',sans-serif;font-size:11px;'
            f'padding:10px 0 4px;">{nav_html}</div>',
            unsafe_allow_html=True,
        )
    with col_back:
        if view != "org":
            if st.button("← Back", key="dd_back", use_container_width=True):
                _go_back()


# ---------------------------------------------------------------------------
# Export bar (always visible)
# ---------------------------------------------------------------------------

def _render_export_bar(data: DashboardData) -> None:
    with st.expander("📥  Export Data", expanded=False):
        cols = st.columns(3)
        with cols[0]:
            csv_bytes = df_to_csv_bytes(data.employee_table)
            st.download_button(
                "Download Employee CSV",
                data=csv_bytes,
                file_name="eibo_employees.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with cols[1]:
            xlsx_bytes = tables_to_excel_bytes({
                "Employees": data.employee_table,
                "Department Summary": data.dept_summary,
                "Team Summary": data.team_summary,
            })
            st.download_button(
                "Download Excel Report",
                data=xlsx_bytes,
                file_name="eibo_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        with cols[2]:
            pdf_bytes = generate_pdf_summary(
                org_name=data.org_name,
                scenario_id=data.scenario_id,
                total_spend=data.total_spend,
                total_budget=data.total_budget,
                n_employees=data.total_headcount,
                avg_impact=data.avg_impact_score,
                n_nexus=data.n_nexus_employees,
                dept_summary=data.dept_summary,
                top_impact_employees=data.employee_table.head(10),
            )
            st.download_button(
                "Download Executive PDF",
                data=pdf_bytes,
                file_name="eibo_executive_summary.pdf",
                mime="application/pdf",
                use_container_width=True,
            )


# ---------------------------------------------------------------------------
# View 1: Organization overview
# ---------------------------------------------------------------------------

def _render_org_view(data: DashboardData) -> None:
    hero_section(
        label="Sprint 4 · Drill-Down Explorer",
        title=f"Organizational Overview — {data.org_name}",
        italic_word=data.org_name,
        subtitle=(
            f"Navigate from organization to individual. Click a department card to explore "
            f"teams, cost/impact quadrants, and full employee profiles."
        ),
        stats=[
            (f"{data.total_headcount:,}", "Total Headcount"),
            (f"${data.total_spend/1_000_000:.1f}M", "Annual Payroll"),
            (f"{data.avg_impact_score:.0f}", "Avg Impact Score"),
            (f"{data.n_nexus_employees}", "Nexus Employees"),
        ],
    )

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    # Graph explorer button
    cols_top = st.columns([5, 1])
    with cols_top[0]:
        st.markdown(
            f'<div style="font-family:\'Plus Jakarta Sans\',sans-serif;font-size:9px;'
            f'font-weight:700;letter-spacing:3px;text-transform:uppercase;'
            f'color:{_GOLD};padding:0 0 12px;">DEPARTMENTS</div>',
            unsafe_allow_html=True,
        )
    with cols_top[1]:
        if st.button("🕸  Graph Explorer", key="dd_graph_btn", use_container_width=True):
            _nav_to("graph")

    _render_dept_cards(data)

    st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)
    _render_cost_impact_scatter_org(data)


def _render_dept_cards(data: DashboardData) -> None:
    if data.dept_summary.empty:
        st.info("No department data available.")
        return

    dept_df = data.dept_summary.copy()
    n_cols = 3
    rows = [dept_df.iloc[i:i + n_cols] for i in range(0, len(dept_df), n_cols)]

    for row_slice in rows:
        cols = st.columns(n_cols)
        for col_idx, (_, dept_row) in enumerate(row_slice.iterrows()):
            dept = str(dept_row["department"])
            headcount = int(dept_row.get("headcount", 0))
            spend = float(dept_row.get("total_spend", 0))
            budget = float(dept_row.get("annual_budget", 0))
            variance = float(dept_row.get("budget_variance_pct", 0))
            impact = float(dept_row.get("avg_impact", 0))
            fragility = float(dept_row.get("fragility_avg", 0))

            var_color = _ORANGE if variance > 5 else (_GOLD if variance > -5 else _GREEN)
            var_sign = "+" if variance >= 0 else ""
            frag_color = _ORANGE if fragility > 0.6 else (_GOLD if fragility > 0.3 else _GREEN)

            with cols[col_idx]:
                st.markdown(
                    f"""
                    <div style="background:#fff;border-radius:10px;padding:20px 22px;
                                box-shadow:0 1px 4px rgba(0,51,102,0.08);
                                border-top:3px solid {_GOLD};margin-bottom:12px;">
                      <div style="font-family:'Plus Jakarta Sans',sans-serif;font-size:9px;
                                  font-weight:700;letter-spacing:3px;text-transform:uppercase;
                                  color:{_GOLD};margin-bottom:6px;">DEPARTMENT</div>
                      <div style="font-family:'Fraunces',Georgia,serif;font-size:18px;
                                  font-weight:300;color:{_NAVY};margin-bottom:12px;">{dept}</div>
                      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
                        <div>
                          <div style="font-family:'Plus Jakarta Sans',sans-serif;
                                      font-size:16px;font-weight:600;color:{_NAVY};">
                            {headcount}</div>
                          <div style="font-family:'Plus Jakarta Sans',sans-serif;
                                      font-size:9px;color:#6B7280;">Headcount</div>
                        </div>
                        <div>
                          <div style="font-family:'Plus Jakarta Sans',sans-serif;
                                      font-size:16px;font-weight:600;color:{_NAVY};">
                            ${spend/1_000_000:.2f}M</div>
                          <div style="font-family:'Plus Jakarta Sans',sans-serif;
                                      font-size:9px;color:#6B7280;">Spend</div>
                        </div>
                        <div>
                          <div style="font-family:'Plus Jakarta Sans',sans-serif;
                                      font-size:16px;font-weight:600;color:{var_color};">
                            {var_sign}{variance:.1f}%</div>
                          <div style="font-family:'Plus Jakarta Sans',sans-serif;
                                      font-size:9px;color:#6B7280;">Budget Variance</div>
                        </div>
                        <div>
                          <div style="font-family:'Plus Jakarta Sans',sans-serif;
                                      font-size:16px;font-weight:600;color:{_NAVY};">
                            {impact:.1f}</div>
                          <div style="font-family:'Plus Jakarta Sans',sans-serif;
                                      font-size:9px;color:#6B7280;">Avg Impact</div>
                        </div>
                      </div>
                      <div style="margin-top:10px;">
                        <span style="font-family:'Plus Jakarta Sans',sans-serif;font-size:9px;
                                     color:{frag_color};">Team Fragility: {fragility:.2f}</span>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button(f"Explore {dept} →", key=f"dd_dept_{dept}",
                             use_container_width=True):
                    _nav_to("dept", dept=dept)


def _render_cost_impact_scatter_org(data: DashboardData) -> None:
    if data.employee_table.empty:
        return
    st.markdown(
        f'<div style="font-family:\'Plus Jakarta Sans\',sans-serif;font-size:9px;'
        f'font-weight:700;letter-spacing:3px;text-transform:uppercase;'
        f'color:{_GOLD};margin-bottom:8px;">COST vs IMPACT — ALL EMPLOYEES</div>',
        unsafe_allow_html=True,
    )
    _render_cost_impact_scatter(data.employee_table, data.nexus_ids, key_suffix="org")


# ---------------------------------------------------------------------------
# View 2: Department
# ---------------------------------------------------------------------------

def _render_dept_view(data: DashboardData, dept: str) -> None:
    if not dept:
        _nav_to("org")
        return

    dept_row_df = data.dept_summary[data.dept_summary["department"] == dept]
    if dept_row_df.empty:
        st.warning(f"Department '{dept}' not found.")
        _nav_to("org")
        return

    dept_row = dept_row_df.iloc[0]
    headcount = int(dept_row.get("headcount", 0))
    spend = float(dept_row.get("total_spend", 0))
    variance = float(dept_row.get("budget_variance_pct", 0))
    impact = float(dept_row.get("avg_impact", 0))

    hero_section(
        label=f"Department · {dept}",
        title=f"{dept} — Team Overview",
        italic_word="Team Overview",
        subtitle=f"{headcount} employees · ${spend/1_000_000:.2f}M payroll · {impact:.1f} avg impact",
        stats=[
            (f"{headcount}", "Employees"),
            (f"${spend/1_000_000:.2f}M", "Annual Payroll"),
            (f"{'+' if variance>=0 else ''}{variance:.1f}%", "vs Budget"),
            (f"{impact:.1f}", "Avg Impact"),
        ],
    )

    # Team scatter
    dept_emp = data.employee_table[data.employee_table["department"] == dept].copy()
    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    if not dept_emp.empty:
        st.markdown(
            f'<div style="font-family:\'Plus Jakarta Sans\',sans-serif;font-size:9px;'
            f'font-weight:700;letter-spacing:3px;text-transform:uppercase;'
            f'color:{_GOLD};margin-bottom:8px;">COST vs IMPACT — {dept.upper()} EMPLOYEES</div>',
            unsafe_allow_html=True,
        )
        _render_cost_impact_scatter(dept_emp, data.nexus_ids, key_suffix=f"dept_{dept}")

    # Teams table
    dept_teams = data.team_summary[data.team_summary["department"] == dept].copy()
    if not dept_teams.empty:
        st.markdown(
            f'<div style="font-family:\'Plus Jakarta Sans\',sans-serif;font-size:9px;'
            f'font-weight:700;letter-spacing:3px;text-transform:uppercase;'
            f'color:{_GOLD};margin:20px 0 8px;">TEAMS IN {dept.upper()}</div>',
            unsafe_allow_html=True,
        )
        for _, team_row in dept_teams.iterrows():
            team_id   = str(team_row["team_id"])
            team_name = str(team_row.get("team_name", team_id))
            t_hc      = int(team_row.get("headcount", 0))
            t_spend   = float(team_row.get("total_spend", 0))
            t_var     = float(team_row.get("budget_variance_pct", 0))
            t_impact  = float(team_row.get("avg_impact", 0))
            t_frag    = float(team_row.get("fragility", 0))

            var_color = _ORANGE if t_var > 5 else (_GOLD if t_var > -5 else _GREEN)
            var_sign  = "+" if t_var >= 0 else ""
            frag_icon = "🔴" if t_frag > 0.6 else ("🟡" if t_frag > 0.3 else "🟢")

            col_info, col_btn = st.columns([5, 1])
            with col_info:
                st.markdown(
                    f'<div style="background:#fff;border-radius:8px;padding:14px 18px;'
                    f'box-shadow:0 1px 3px rgba(0,51,102,0.06);'
                    f'border-left:3px solid {_GOLD};margin-bottom:8px;">'
                    f'<b style="font-family:\'Plus Jakarta Sans\',sans-serif;font-size:13px;'
                    f'color:{_NAVY};">{team_name}</b>'
                    f'<span style="font-family:\'Plus Jakarta Sans\',sans-serif;font-size:10px;'
                    f'color:#6B7280;margin-left:12px;">{t_hc} people · '
                    f'${t_spend/1_000:.0f}K spend · '
                    f'<span style="color:{var_color};">{var_sign}{t_var:.1f}% budget</span> · '
                    f'{t_impact:.1f} impact · {frag_icon} fragility {t_frag:.2f}'
                    f'</span></div>',
                    unsafe_allow_html=True,
                )
            with col_btn:
                if st.button(f"Explore →", key=f"dd_team_{team_id}",
                             use_container_width=True):
                    _nav_to("team", dept=dept, team=team_id)

    # Dept-level network graph (scoped to this dept)
    _render_dept_graph(data, dept)


def _render_dept_graph(data: DashboardData, dept: str) -> None:
    dept_emp_ids = set(
        data.employee_table.loc[data.employee_table["department"] == dept, "employee_id"]
    )
    if not dept_emp_ids:
        return

    G = _get_or_build_graph(data)
    G_scope = filter_graph_to_scope(G, dept_emp_ids, max_nodes=60)

    st.markdown(
        f'<div style="font-family:\'Plus Jakarta Sans\',sans-serif;font-size:9px;'
        f'font-weight:700;letter-spacing:3px;text-transform:uppercase;'
        f'color:{_GOLD};margin:20px 0 8px;">{dept.upper()} COLLABORATION NETWORK</div>',
        unsafe_allow_html=True,
    )
    st.markdown(status_legend_html(), unsafe_allow_html=True)
    fig = render_network_graph(
        graph=G_scope,
        employee_table=data.employee_table,
        nexus_ids=data.nexus_ids,
        simulation_status=st.session_state.get("dd_sim_status", {}),
        title=f"{dept} — Collaboration Network",
        height=420,
    )
    st.plotly_chart(fig, use_container_width=True,
                    config={"displayModeBar": True,
                            "modeBarButtonsToRemove": ["select2d", "lasso2d"]})


# ---------------------------------------------------------------------------
# View 3: Team
# ---------------------------------------------------------------------------

def _render_team_view(data: DashboardData, team_id: str) -> None:
    if not team_id:
        _nav_to("org")
        return

    team_row_df = data.team_summary[data.team_summary["team_id"] == team_id]
    if team_row_df.empty:
        st.warning(f"Team '{team_id}' not found.")
        _nav_to("org")
        return

    team_row = team_row_df.iloc[0]
    team_name = str(team_row.get("team_name", team_id))
    dept      = str(team_row.get("department", ""))
    t_hc      = int(team_row.get("headcount", 0))
    t_spend   = float(team_row.get("total_spend", 0))
    t_var     = float(team_row.get("budget_variance_pct", 0))
    t_impact  = float(team_row.get("avg_impact", 0))
    t_frag    = float(team_row.get("fragility", 0))

    hero_section(
        label=f"{dept} · Team View",
        title=f"{team_name} — Employee Breakdown",
        italic_word="Employee Breakdown",
        subtitle=(
            f"{t_hc} employees · ${t_spend/1_000:.0f}K spend · "
            f"{t_impact:.1f} avg impact · {t_var:+.1f}% vs budget"
        ),
        stats=[
            (f"{t_hc}", "Team Size"),
            (f"${t_spend/1_000:.0f}K", "Annual Spend"),
            (f"{t_impact:.1f}", "Avg Impact"),
            (f"{t_frag:.2f}", "Team Fragility"),
        ],
    )

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    team_emp = data.employee_table[data.employee_table["team_id"] == team_id].copy()

    # Cost/Impact scatter with quadrant labels
    if not team_emp.empty:
        st.markdown(
            f'<div style="font-family:\'Plus Jakarta Sans\',sans-serif;font-size:9px;'
            f'font-weight:700;letter-spacing:3px;text-transform:uppercase;'
            f'color:{_GOLD};margin-bottom:8px;">COST vs IMPACT — {team_name.upper()}</div>',
            unsafe_allow_html=True,
        )
        _render_cost_impact_scatter(
            team_emp, data.nexus_ids, key_suffix=f"team_{team_id}",
            show_quadrants=True, on_click_navigate=True, data=data,
        )

    # Employee table for this team
    st.markdown(
        f'<div style="font-family:\'Plus Jakarta Sans\',sans-serif;font-size:9px;'
        f'font-weight:700;letter-spacing:3px;text-transform:uppercase;'
        f'color:{_GOLD};margin:16px 0 8px;">TEAM MEMBERS</div>',
        unsafe_allow_html=True,
    )
    _render_team_member_table(team_emp, data.nexus_ids)


def _render_team_member_table(team_emp: pd.DataFrame, nexus_ids: set[str]) -> None:
    if team_emp.empty:
        st.info("No employees in this team.")
        return

    display = team_emp[[
        "employee_id", "full_name", "role_title", "seniority_level",
        "impact_score", "total_cost", "tenure_years", "top_skill",
    ]].copy()
    display["★ Nexus"] = display["employee_id"].isin(nexus_ids).map({True: "★", False: ""})
    display["impact_score"] = display["impact_score"].round(1)
    display["total_cost"] = display["total_cost"].apply(lambda v: f"${v:,.0f}")
    display["tenure_years"] = display["tenure_years"].round(1)

    display = display.rename(columns={
        "full_name":      "Name",
        "role_title":     "Role",
        "seniority_level":"Seniority",
        "impact_score":   "Impact",
        "total_cost":     "Total Cost",
        "tenure_years":   "Tenure (yr)",
        "top_skill":      "Top Skill",
    })

    selected_rows = st.dataframe(
        display.drop(columns=["employee_id"]),
        use_container_width=True,
        height=min(400, 56 + len(display) * 35),
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    if selected_rows and selected_rows.get("selection", {}).get("rows"):
        row_idx = selected_rows["selection"]["rows"][0]
        emp_id = display.iloc[row_idx]["employee_id"]
        _nav_to("employee", employee=emp_id)


# ---------------------------------------------------------------------------
# View 4: Individual employee profile
# ---------------------------------------------------------------------------

def _render_employee_view(data: DashboardData, employee_id: str) -> None:
    if not employee_id:
        _nav_to("org")
        return

    if data.employee_table.empty or employee_id not in set(data.employee_table["employee_id"]):
        st.warning(f"Employee '{employee_id}' not found.")
        _nav_to("org")
        return

    G = _get_or_build_graph(data)
    critical_holders = _build_critical_skill_holders(data)

    render_employee_profile(
        employee_id=employee_id,
        employee_table=data.employee_table,
        impact_scores=data.impact_scores,
        performance_df=data.performance,
        employee_skills_df=data.employee_skills,
        skills_df=data.skills,
        collaboration_graph=G,
        nexus_ids=data.nexus_ids,
        critical_skill_holders=critical_holders,
        dept_summary=data.dept_summary,
    )

    # Quick navigate to other employees
    emp_row = data.employee_table[data.employee_table["employee_id"] == employee_id].iloc[0]
    team_id = str(emp_row.get("team_id", ""))
    if team_id:
        team_emp = data.employee_table[
            (data.employee_table["team_id"] == team_id) &
            (data.employee_table["employee_id"] != employee_id)
        ].head(5)
        if not team_emp.empty:
            st.markdown(
                f'<div style="font-family:\'Plus Jakarta Sans\',sans-serif;font-size:9px;'
                f'font-weight:700;letter-spacing:3px;text-transform:uppercase;'
                f'color:{_GOLD};margin:20px 0 8px;">OTHER TEAM MEMBERS</div>',
                unsafe_allow_html=True,
            )
            cols = st.columns(min(len(team_emp), 5))
            for i, (_, row) in enumerate(team_emp.iterrows()):
                with cols[i]:
                    if st.button(
                        f"{row['full_name'][:18]}\n{row['impact_score']:.0f} impact",
                        key=f"dd_peer_{row['employee_id']}",
                        use_container_width=True,
                    ):
                        _nav_to("employee", employee=row["employee_id"])


# ---------------------------------------------------------------------------
# View 5: Graph Explorer
# ---------------------------------------------------------------------------

def _render_graph_view(data: DashboardData) -> None:
    hero_section(
        label="Graph Explorer",
        title="Collaboration Network",
        italic_word="Network",
        subtitle=(
            "Interactive visualization of collaboration relationships. Node size = impact score. "
            "Color = simulation status or nexus designation."
        ),
    )

    G = _get_or_build_graph(data)
    total_nodes = len(G.nodes)

    col_filter, col_depth = st.columns([2, 1])
    with col_filter:
        all_depts = sorted(data.employee_table["department"].unique().tolist())
        selected_depts = st.multiselect(
            "Filter by department",
            options=all_depts,
            default=[],
            key="dd_graph_dept_filter",
            placeholder="All departments (may be slow for large orgs)",
        )
    with col_depth:
        max_nodes = st.slider("Max nodes", min_value=20, max_value=150, value=80,
                              step=10, key="dd_graph_max_nodes")

    if selected_depts:
        scope_ids = set(
            data.employee_table.loc[
                data.employee_table["department"].isin(selected_depts), "employee_id"
            ]
        )
    else:
        scope_ids = set(G.nodes)

    G_scope = filter_graph_to_scope(G, scope_ids, max_nodes=max_nodes)
    nodes_shown = len(G_scope.nodes)

    if total_nodes > max_nodes and not selected_depts:
        st.info(
            f"Showing top {nodes_shown} of {total_nodes} employees by degree centrality. "
            "Use the department filter or reduce max nodes to explore specific sub-networks.",
            icon="ℹ️",
        )

    st.markdown(status_legend_html(), unsafe_allow_html=True)
    fig = render_network_graph(
        graph=G_scope,
        employee_table=data.employee_table,
        nexus_ids=data.nexus_ids,
        simulation_status=st.session_state.get("dd_sim_status", {}),
        title=(
            f"Collaboration Network — "
            f"{', '.join(selected_depts) if selected_depts else 'All Departments'}"
        ),
        height=620,
    )
    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "displayModeBar": True,
            "modeBarButtonsToRemove": ["select2d", "lasso2d"],
            "scrollZoom": True,
        },
    )

    # Graph metrics
    if nodes_shown > 0:
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            st.metric("Nodes shown", nodes_shown)
        with col_m2:
            st.metric("Edges shown", len(G_scope.edges))
        with col_m3:
            density = nx.density(G_scope) if nodes_shown > 1 else 0
            st.metric("Network Density", f"{density:.3f}")
        with col_m4:
            n_comp = nx.number_connected_components(G_scope)
            st.metric("Components", n_comp)


# ---------------------------------------------------------------------------
# Shared visualizations
# ---------------------------------------------------------------------------

def _render_cost_impact_scatter(
    emp_df: pd.DataFrame,
    nexus_ids: set[str],
    key_suffix: str = "",
    show_quadrants: bool = False,
    on_click_navigate: bool = False,
    data: DashboardData | None = None,
) -> None:
    """Cost vs Impact scatter plot with optional quadrant labels."""
    if emp_df.empty:
        st.info("No employee data to display.")
        return

    df = emp_df.copy()
    df["total_cost"] = pd.to_numeric(df["total_cost"].replace(r"[\$,]", "", regex=True),
                                      errors="coerce").fillna(0)
    df["impact_score"] = pd.to_numeric(df["impact_score"], errors="coerce").fillna(0)

    median_cost   = float(df["total_cost"].median())
    median_impact = float(df["impact_score"].median())

    colors = df["employee_id"].map(
        lambda eid: "#C8982A" if eid in nexus_ids else _NAVY
    ).tolist()

    hover = [
        f"<b>{row.get('full_name','')}</b><br>"
        f"{row.get('role_title','')}<br>"
        f"Impact: {row.get('impact_score',0):.1f}<br>"
        f"Cost: ${row.get('total_cost',0):,.0f}"
        for _, row in df.iterrows()
    ]

    fig = go.Figure(go.Scatter(
        x=df["total_cost"].tolist(),
        y=df["impact_score"].tolist(),
        mode="markers",
        marker=dict(size=8, color=colors, opacity=0.78,
                    line=dict(width=1, color="#fff")),
        hovertemplate="%{customdata}<extra></extra>",
        customdata=hover,
        text=df["full_name"].str.split().str[0].tolist(),
    ))

    if show_quadrants:
        for x_pos, y_pos, text in [
            (0.02, 0.98, "High Impact<br>Low Cost"),
            (0.98, 0.98, "High Impact<br>High Cost"),
            (0.02, 0.02, "Low Impact<br>Low Cost"),
            (0.98, 0.02, "Low Impact<br>High Cost"),
        ]:
            fig.add_annotation(
                xref="paper", yref="paper",
                x=x_pos, y=y_pos,
                text=f'<span style="font-size:9px;color:rgba(0,51,102,0.3);">{text}</span>',
                showarrow=False,
            )
        fig.add_vline(x=median_cost, line=dict(dash="dot", color="rgba(0,51,102,0.2)", width=1))
        fig.add_hline(y=median_impact, line=dict(dash="dot", color="rgba(0,51,102,0.2)", width=1))

    fig.update_layout(
        height=340,
        margin=dict(l=40, r=20, t=16, b=40),
        xaxis=dict(title="Annual Cost ($)", tickformat="$,.0f",
                   tickfont=dict(size=9, color="#6B7280")),
        yaxis=dict(title="Impact Score", range=[0, 105],
                   tickfont=dict(size=9, color="#6B7280")),
        paper_bgcolor=_LIGHT,
        plot_bgcolor="#fff",
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, key=f"scatter_{key_suffix}",
                    config={"displayModeBar": False})

    if on_click_navigate and data is not None and not df.empty:
        selected_name = st.selectbox(
            "Click chart point or select employee to view profile:",
            options=["— select —"] + df["full_name"].tolist(),
            key=f"dd_scatter_select_{key_suffix}",
        )
        if selected_name != "— select —":
            sel_row = df[df["full_name"] == selected_name]
            if not sel_row.empty:
                emp_id = str(sel_row.iloc[0]["employee_id"])
                _nav_to("employee", employee=emp_id)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False, ttl=3600)
def _cached_build_graph(
    collab_source: tuple, collab_target: tuple,
    collab_rel: tuple, collab_weight: tuple,
) -> nx.Graph:
    """Cache the graph build; keyed on edge tuples for reproducibility."""
    df = pd.DataFrame({
        "source_id": list(collab_source),
        "target_id": list(collab_target),
        "relationship_type": list(collab_rel),
        "interaction_weight": list(collab_weight),
    })
    return build_org_graph(df)


def _get_or_build_graph(data: DashboardData) -> nx.Graph:
    """Build (or retrieve cached) the full collaboration graph."""
    if "dd_graph" not in st.session_state:
        # Store in session state to survive reruns within the same session
        st.session_state.dd_graph = build_org_graph(
            # Access via data loader — the loader already holds the generated data
            # We reconstruct from centrality + teams (collaboration df not in DashboardData)
            # For demo, rebuild from scratch (cached by load_dashboard_data)
            _get_collaboration_df(data)
        )
    return st.session_state.dd_graph


def _get_collaboration_df(data: DashboardData) -> pd.DataFrame:
    """Re-generate collaboration edges from DemoGenerator for the current session."""
    try:
        from demo_data.generator import DemoGenerator
        gen = DemoGenerator(
            scenario_id=st.session_state.get("demo_scenario", "A"),
            size=st.session_state.get("demo_size", "medium"),
        )
        org = gen.generate()
        return org.collaboration
    except Exception:
        logger.warning("Could not regenerate collaboration data; using empty graph.")
        return pd.DataFrame(
            columns=["source_id", "target_id", "relationship_type", "interaction_weight"]
        )


def _build_critical_skill_holders(data: DashboardData) -> dict[str, list[str]]:
    """Build skill_id → [employee_ids] for critical skills only."""
    if data.skills.empty or data.employee_skills.empty:
        return {}
    critical_skills = data.skills[data.skills["is_critical"] == True]["skill_id"].tolist()
    result: dict[str, list[str]] = {}
    for skill_id in critical_skills:
        holders = data.employee_skills[
            data.employee_skills["skill_id"] == skill_id
        ]["employee_id"].tolist()
        if holders:
            result[skill_id] = holders
    return result
