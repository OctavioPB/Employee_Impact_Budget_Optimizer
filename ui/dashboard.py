"""Executive Dashboard — Sprint 2: Analytics Engine & Impact Scoring.

Layout:
  1. Dark hero section with 4 org-level KPI stats
  2. Budget vs Actual spend by department (bar chart)
  3. Treemap: cost distribution by team with impact overlay
  4. Impact score distribution + department comparison table
  5. Employee table with search/filter/sort
  6. Alert cards: nexus employees, over-budget teams, critical skill gaps
"""

import logging

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ui.data_loader import DashboardData, load_dashboard_data

logger = logging.getLogger(__name__)

# BRAND.md report colors — use in this order for multi-series charts
_COLORS = {
    "primary":  "#003366",
    "green":    "#27B97C",
    "purple":   "#7C4DBD",
    "orange":   "#F07020",
    "pink":     "#E05080",
    "gold":     "#C8982A",
    "gold_lt":  "#E8C46A",
    "light":    "#F4F6F9",
    "mid":      "#6B7280",
    "dark":     "#1C1C2E",
}

_CHART_COLORS = [
    _COLORS["primary"], _COLORS["green"], _COLORS["purple"],
    _COLORS["orange"], _COLORS["pink"],
]

_FONT_FAMILY = "'Plus Jakarta Sans', sans-serif"

_CHART_LAYOUT = dict(
    font_family=_FONT_FAMILY,
    font_color=_COLORS["dark"],
    paper_bgcolor=_COLORS["light"],
    plot_bgcolor="white",
    margin=dict(l=16, r=16, t=40, b=16),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def render() -> None:
    demo_mode: bool = st.session_state.get("demo_mode", True)
    scenario_id: str = st.session_state.get("demo_scenario", "A")
    size: str = st.session_state.get("demo_size", "medium")

    with st.spinner("Loading analytics data…"):
        try:
            data = load_dashboard_data(demo_mode, scenario_id, size)
        except NotImplementedError as exc:
            st.error(str(exc))
            return
        except RuntimeError as exc:
            st.error(str(exc))
            return

    _render_hero(data)
    _render_spend_and_treemap(data)
    _render_impact_and_dept_table(data)
    _render_trends(data)
    _render_employee_table(data)
    _render_alerts(data)


# ---------------------------------------------------------------------------
# 1. Dark hero section with KPI stats
# ---------------------------------------------------------------------------

def _render_hero(data: DashboardData) -> None:
    scenario_labels = {"A": "Growing Company", "B": "Restructuring", "C": "Merger Integration"}
    scenario_label = scenario_labels.get(data.scenario_id.upper(), data.scenario_id)

    variance_sign = "+" if data.budget_variance_pct >= 0 else ""
    variance_color = _COLORS["orange"] if data.budget_variance_pct > 5 else _COLORS["green"]

    st.markdown(
        f"""
        <div style="background-color:#003366;
          background-image:
            linear-gradient(rgba(255,255,255,.025) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,.025) 1px, transparent 1px);
          background-size:48px 48px;
          padding:56px 48px 40px;">
          <div style="max-width:1300px; margin:0 auto;">
            <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:10px;
                        font-weight:700; letter-spacing:4px; text-transform:uppercase;
                        color:rgba(255,255,255,0.35); margin-bottom:10px;">
              {data.org_size.upper()} ORG · SCENARIO {data.scenario_id} — {scenario_label}
            </div>
            <h1 style="font-family:'Fraunces',Georgia,serif; font-size:34px;
                       font-weight:300; color:#fff; margin:0 0 8px; line-height:1.2;">
              {data.org_name} —
              <em style="color:#E8C46A; font-style:italic;">Analytics Overview</em>
            </h1>
            <p style="font-family:'Plus Jakarta Sans',sans-serif; font-size:13px;
                      color:rgba(255,255,255,0.55); margin:0 0 36px; max-width:560px;
                      line-height:1.75;">
              Organizational intelligence computed from performance history,
              collaboration graph, and skill inventory.
              Scoring mode: <strong style="color:rgba(255,255,255,0.75);">{data.scoring_mode}</strong>.
            </p>

            <div style="display:flex; gap:40px; flex-wrap:wrap;">
              <div style="border-left:2px solid #C8982A; padding-left:18px;">
                <div style="font-family:'Fraunces',Georgia,serif; font-size:36px;
                            font-weight:300; color:#E8C46A; line-height:1;">
                  {data.total_headcount:,}
                </div>
                <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:12px;
                            color:rgba(255,255,255,0.5); margin-top:8px; line-height:1.55;">
                  Active Employees
                </div>
              </div>
              <div style="border-left:2px solid #C8982A; padding-left:18px;">
                <div style="font-family:'Fraunces',Georgia,serif; font-size:36px;
                            font-weight:300; color:#E8C46A; line-height:1;">
                  ${data.total_spend / 1_000_000:.1f}M
                </div>
                <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:12px;
                            color:rgba(255,255,255,0.5); margin-top:8px; line-height:1.55;">
                  Annual Payroll Spend
                </div>
              </div>
              <div style="border-left:2px solid #C8982A; padding-left:18px;">
                <div style="font-family:'Fraunces',Georgia,serif; font-size:36px;
                            font-weight:300; color:#E8C46A; line-height:1;">
                  {data.avg_impact_score:.1f}
                </div>
                <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:12px;
                            color:rgba(255,255,255,0.5); margin-top:8px; line-height:1.55;">
                  Avg Impact Score / 100
                </div>
              </div>
              <div style="border-left:2px solid #C8982A; padding-left:18px;">
                <div style="font-family:'Fraunces',Georgia,serif; font-size:36px;
                            font-weight:300; color:{variance_color}; line-height:1;">
                  {variance_sign}{data.budget_variance_pct:.1f}%
                </div>
                <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:12px;
                            color:rgba(255,255,255,0.5); margin-top:8px; line-height:1.55;">
                  Spend vs Budget
                </div>
              </div>
              <div style="border-left:2px solid #C8982A; padding-left:18px;">
                <div style="font-family:'Fraunces',Georgia,serif; font-size:36px;
                            font-weight:300; color:#E8C46A; line-height:1;">
                  {data.n_nexus_employees}
                </div>
                <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:12px;
                            color:rgba(255,255,255,0.5); margin-top:8px; line-height:1.55;">
                  Nexus Employees
                </div>
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# 2. Budget vs Actual + Treemap
# ---------------------------------------------------------------------------

def _render_spend_and_treemap(data: DashboardData) -> None:
    st.markdown(
        """
        <div style="height:1px; background:#E0EAF4; margin:0;"></div>
        <div style="max-width:1300px; margin:0 auto; padding:48px 48px 0;">
          <div style="display:inline-flex; align-items:center; gap:8px; margin-bottom:4px;
                      font-family:'Plus Jakarta Sans',sans-serif; font-size:9px; font-weight:500;
                      letter-spacing:4px; text-transform:uppercase; color:#C8982A;">
            <div style="width:24px; height:1px; background:#C8982A; flex-shrink:0;"></div>
            Budget Analysis
          </div>
          <h2 style="font-family:'Fraunces',Georgia,serif; font-size:22px; font-weight:300;
                     color:#0a1628; margin:0 0 4px;">
            Spend vs Budget by department
          </h2>
          <p style="font-family:'Plus Jakarta Sans',sans-serif; font-size:13px;
                    color:#6B7280; margin:0 0 24px; line-height:1.7;">
            Departments over budget are flagged — click a bar to drill down.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_left, col_right = st.columns([3, 2], gap="large")

    with col_left:
        _render_budget_bar_chart(data)

    with col_right:
        _render_treemap(data)

    st.markdown(
        "<div style='height:1px; background:#E0EAF4; margin:24px 48px;'></div>",
        unsafe_allow_html=True,
    )


def _render_budget_bar_chart(data: DashboardData) -> None:
    dept = data.dept_summary.copy()
    dept["over_budget"] = dept["budget_variance_pct"] > 10

    fig = go.Figure()

    fig.add_trace(go.Bar(
        name="Annual Budget",
        x=dept["department"],
        y=dept["annual_budget"] / 1_000,
        marker_color=_COLORS["primary"],
        opacity=0.6,
        hovertemplate="<b>%{x}</b><br>Budget: $%{y:,.0f}K<extra></extra>",
    ))

    fig.add_trace(go.Bar(
        name="Actual Spend",
        x=dept["department"],
        y=dept["total_spend"] / 1_000,
        marker_color=[
            _COLORS["orange"] if over else _COLORS["green"]
            for over in dept["over_budget"]
        ],
        hovertemplate="<b>%{x}</b><br>Spend: $%{y:,.0f}K<br>Variance: %{customdata:.1f}%<extra></extra>",
        customdata=dept["budget_variance_pct"],
    ))

    fig.update_layout(
        **_CHART_LAYOUT,
        barmode="group",
        yaxis_title="USD (thousands)",
        xaxis_tickangle=-30,
        height=340,
        title=dict(text="", font_size=1),
        showlegend=True,
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#E0EAF4", zeroline=False)

    st.plotly_chart(fig, use_container_width=True, key="budget_bar")

    # Legend note
    st.markdown(
        '<div style="font-family:\'Plus Jakarta Sans\',sans-serif; font-size:11px; '
        'color:#6B7280; padding:0 4px;">🟠 Over-budget (&gt;10%)  &nbsp;🟢 On-track</div>',
        unsafe_allow_html=True,
    )


def _render_treemap(data: DashboardData) -> None:
    team = data.team_summary.copy()
    team["label"] = team.apply(
        lambda r: f"{r['team_name']}<br>{r['headcount']} people", axis=1
    )
    team["total_spend_M"] = (team["total_spend"] / 1_000_000).round(2)
    team["avg_impact_display"] = team["avg_impact"].round(1)

    if team.empty:
        st.info("No team data available.")
        return

    fig = px.treemap(
        team,
        path=["department", "team_name"],
        values="total_spend",
        color="avg_impact",
        color_continuous_scale=[
            [0.0,  "#E0EAF4"],
            [0.5,  "#003366"],
            [1.0,  "#E8C46A"],
        ],
        color_continuous_midpoint=float(data.avg_impact_score),
        hover_data={"total_spend": ":$,.0f", "headcount": True, "avg_impact": ":.1f"},
        custom_data=["headcount", "avg_impact", "budget_variance_pct"],
    )

    fig.update_traces(
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Spend: $%{value:,.0f}<br>"
            "Headcount: %{customdata[0]}<br>"
            "Avg Impact: %{customdata[1]:.1f}<br>"
            "Budget Variance: %{customdata[2]:.1f}%<extra></extra>"
        ),
        textfont_size=11,
    )
    fig.update_layout(
        **_CHART_LAYOUT,
        height=340,
        coloraxis_colorbar=dict(
            title="Impact",
            thickness=12,
            len=0.7,
            tickfont_size=10,
        ),
    )

    st.plotly_chart(fig, use_container_width=True, key="treemap")


# ---------------------------------------------------------------------------
# 3. Impact score distribution + Department comparison table
# ---------------------------------------------------------------------------

def _render_impact_and_dept_table(data: DashboardData) -> None:
    st.markdown(
        """
        <div style="max-width:1300px; margin:0 auto; padding:0 48px 0;">
          <div style="display:inline-flex; align-items:center; gap:8px; margin-bottom:4px;
                      font-family:'Plus Jakarta Sans',sans-serif; font-size:9px; font-weight:500;
                      letter-spacing:4px; text-transform:uppercase; color:#C8982A;">
            <div style="width:24px; height:1px; background:#C8982A; flex-shrink:0;"></div>
            Impact Scoring
          </div>
          <h2 style="font-family:'Fraunces',Georgia,serif; font-size:22px; font-weight:300;
                     color:#0a1628; margin:0 0 4px;">
            Organizational <em style="font-style:italic;">impact landscape</em>
          </h2>
          <p style="font-family:'Plus Jakarta Sans',sans-serif; font-size:13px;
                    color:#6B7280; margin:0 0 24px; line-height:1.7;">
            Scores combine KPI performance (40%), collaboration network centrality (30%),
            skill criticality (20%), and replacement cost (10%).
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_left, col_right = st.columns([2, 3], gap="large")

    with col_left:
        _render_impact_histogram(data)

    with col_right:
        _render_dept_comparison_table(data)

    st.markdown(
        "<div style='height:1px; background:#E0EAF4; margin:24px 48px;'></div>",
        unsafe_allow_html=True,
    )


def _render_impact_histogram(data: DashboardData) -> None:
    scores = data.impact_scores["impact_score"].dropna()

    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=scores,
        nbinsx=20,
        marker_color=_COLORS["primary"],
        marker_line_color="white",
        marker_line_width=1,
        opacity=0.85,
        hovertemplate="Score: %{x:.0f}–%{x:.0f}<br>Count: %{y}<extra></extra>",
    ))

    # Median line
    median_val = float(scores.median())
    fig.add_vline(
        x=median_val,
        line_dash="dash",
        line_color=_COLORS["gold"],
        line_width=2,
        annotation_text=f"Median: {median_val:.0f}",
        annotation_position="top right",
        annotation_font_color=_COLORS["gold"],
        annotation_font_size=11,
    )

    fig.update_layout(
        **_CHART_LAYOUT,
        height=300,
        xaxis_title="Impact Score (0–100)",
        yaxis_title="Employees",
        showlegend=False,
    )
    fig.update_xaxes(range=[0, 100], showgrid=False)
    fig.update_yaxes(gridcolor="#E0EAF4", zeroline=False)

    st.plotly_chart(fig, use_container_width=True, key="impact_hist")


def _render_dept_comparison_table(data: DashboardData) -> None:
    dept = data.dept_summary[
        ["department", "headcount", "total_spend", "annual_budget",
         "budget_variance_pct", "avg_impact", "fragility_avg"]
    ].copy()

    dept.columns = [
        "Department", "Headcount", "Actual Spend", "Budget",
        "Variance %", "Avg Impact", "Team Fragility",
    ]

    # Formatting
    dept["Actual Spend"] = dept["Actual Spend"].apply(lambda v: f"${v/1_000_000:.2f}M")
    dept["Budget"] = dept["Budget"].apply(lambda v: f"${v/1_000_000:.2f}M")
    dept["Variance %"] = dept["Variance %"].apply(
        lambda v: f"+{v:.1f}%" if v > 0 else f"{v:.1f}%"
    )
    dept["Avg Impact"] = dept["Avg Impact"].apply(lambda v: f"{v:.1f}")
    dept["Team Fragility"] = dept["Team Fragility"].apply(
        lambda v: f"{'🔴' if v > 0.6 else '🟡' if v > 0.35 else '🟢'} {v:.2f}"
        if pd.notna(v) else "—"
    )

    st.markdown(
        """
        <style>
        [data-testid="stDataFrame"] thead tr th {
            background-color: #003366 !important;
            color: white !important;
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            font-size: 10px !important;
            font-weight: 700 !important;
            letter-spacing: 2px !important;
            text-transform: uppercase !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.dataframe(
        dept,
        use_container_width=True,
        hide_index=True,
        height=min(300, 36 + 35 * len(dept)),
    )


# ---------------------------------------------------------------------------
# 4. Quarterly trends
# ---------------------------------------------------------------------------

def _render_trends(data: DashboardData) -> None:
    if data.quarterly_spend.empty and data.quarterly_kpi.empty:
        return

    st.markdown(
        """
        <div style="max-width:1300px; margin:0 auto; padding:0 48px 0;">
          <div style="display:inline-flex; align-items:center; gap:8px; margin-bottom:4px;
                      font-family:'Plus Jakarta Sans',sans-serif; font-size:9px; font-weight:500;
                      letter-spacing:4px; text-transform:uppercase; color:#C8982A;">
            <div style="width:24px; height:1px; background:#C8982A; flex-shrink:0;"></div>
            Historical Trends
          </div>
          <h2 style="font-family:'Fraunces',Georgia,serif; font-size:22px; font-weight:300;
                     color:#0a1628; margin:0 0 24px;">
            Spend and performance over <em style="font-style:italic;">time</em>
          </h2>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_left, col_right = st.columns(2, gap="large")

    with col_left:
        _render_spend_trend(data)

    with col_right:
        _render_kpi_trend(data)

    st.markdown(
        "<div style='height:1px; background:#E0EAF4; margin:24px 48px;'></div>",
        unsafe_allow_html=True,
    )


def _render_spend_trend(data: DashboardData) -> None:
    if data.quarterly_spend.empty:
        return

    qs = data.quarterly_spend.copy()
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=qs["fiscal_period"], y=qs["total_budgeted"] / 1_000,
        name="Budgeted", mode="lines+markers",
        line=dict(color=_COLORS["primary"], width=2, dash="dash"),
        marker=dict(size=5),
        hovertemplate="%{x}<br>Budget: $%{y:,.0f}K<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=qs["fiscal_period"], y=qs["total_actual"] / 1_000,
        name="Actual", mode="lines+markers",
        line=dict(color=_COLORS["orange"], width=2),
        marker=dict(size=5),
        hovertemplate="%{x}<br>Actual: $%{y:,.0f}K<extra></extra>",
    ))

    fig.update_layout(
        **_CHART_LAYOUT,
        height=280,
        yaxis_title="USD (thousands)",
        xaxis_tickangle=-30,
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#E0EAF4", zeroline=False)
    st.plotly_chart(fig, use_container_width=True, key="spend_trend")


def _render_kpi_trend(data: DashboardData) -> None:
    if data.quarterly_kpi.empty:
        return

    qk = data.quarterly_kpi.copy()
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=qk["review_period"], y=qk["avg_kpi"].round(2),
        name="Avg KPI", mode="lines+markers",
        line=dict(color=_COLORS["green"], width=2),
        marker=dict(size=5),
        hovertemplate="%{x}<br>KPI: %{y:.2f}<extra></extra>",
    ))

    fig.add_hline(
        y=3.5, line_dash="dot", line_color=_COLORS["mid"],
        annotation_text="Target 3.5",
        annotation_position="right",
        annotation_font_size=10,
        annotation_font_color=_COLORS["mid"],
    )

    fig.update_layout(
        **_CHART_LAYOUT,
        height=280,
        yaxis_title="KPI Score (1–5)",
        xaxis_tickangle=-30,
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#E0EAF4", range=[1, 5], zeroline=False)
    st.plotly_chart(fig, use_container_width=True, key="kpi_trend")


# ---------------------------------------------------------------------------
# 5. Employee table
# ---------------------------------------------------------------------------

def _render_employee_table(data: DashboardData) -> None:
    st.markdown(
        """
        <div style="max-width:1300px; margin:0 auto; padding:0 48px 0;">
          <div style="display:inline-flex; align-items:center; gap:8px; margin-bottom:4px;
                      font-family:'Plus Jakarta Sans',sans-serif; font-size:9px; font-weight:500;
                      letter-spacing:4px; text-transform:uppercase; color:#C8982A;">
            <div style="width:24px; height:1px; background:#C8982A; flex-shrink:0;"></div>
            Employee Detail
          </div>
          <h2 style="font-family:'Fraunces',Georgia,serif; font-size:22px; font-weight:300;
                     color:#0a1628; margin:0 0 4px;">
            Workforce <em style="font-style:italic;">impact registry</em>
          </h2>
          <p style="font-family:'Plus Jakarta Sans',sans-serif; font-size:13px;
                    color:#6B7280; margin:0 0 16px; line-height:1.7;">
            Filter by department or search by name. Nexus employees are flagged with ★.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_search, col_dept, col_seniority, col_min_impact = st.columns([2, 2, 2, 1])

    table = data.employee_table.copy()

    with col_search:
        search = st.text_input("Search employee", placeholder="Name or role…", label_visibility="collapsed")

    with col_dept:
        dept_opts = ["All departments"] + sorted(table["department"].unique().tolist())
        dept_filter = st.selectbox("Department", dept_opts, label_visibility="collapsed")

    with col_seniority:
        seniority_order = ["All seniority", "junior", "mid", "senior", "lead", "director", "exec"]
        seniority_opts = ["All seniority"] + [
            s for s in seniority_order[1:] if s in table["seniority_level"].unique()
        ]
        seniority_filter = st.selectbox("Seniority", seniority_opts, label_visibility="collapsed")

    with col_min_impact:
        min_impact = st.number_input(
            "Min impact", min_value=0, max_value=100, value=0,
            label_visibility="collapsed",
        )

    # Apply filters
    if search:
        mask = (
            table["full_name"].str.contains(search, case=False, na=False)
            | table["role_title"].str.contains(search, case=False, na=False)
        )
        table = table[mask]

    if dept_filter != "All departments":
        table = table[table["department"] == dept_filter]

    if seniority_filter != "All seniority":
        table = table[table["seniority_level"] == seniority_filter]

    if min_impact > 0:
        table = table[table["impact_score"] >= min_impact]

    display = table[[
        "full_name", "role_title", "department", "seniority_level",
        "impact_score", "kpi_contribution", "network_contribution",
        "skills_contribution", "tenure_years", "is_nexus", "top_skill",
    ]].copy()

    display["full_name"] = display.apply(
        lambda r: f"★ {r['full_name']}" if r["is_nexus"] else r["full_name"], axis=1
    )
    display["impact_score"] = display["impact_score"].apply(lambda v: f"{v:.1f}")
    display["kpi_contribution"] = display["kpi_contribution"].apply(lambda v: f"{v:.1f}")
    display["network_contribution"] = display["network_contribution"].apply(lambda v: f"{v:.1f}")
    display["skills_contribution"] = display["skills_contribution"].apply(lambda v: f"{v:.1f}")
    display["tenure_years"] = display["tenure_years"].apply(lambda v: f"{v:.1f} yr")

    display.columns = [
        "Employee", "Role", "Department", "Seniority",
        "Impact ↓", "KPI", "Network", "Skills",
        "Tenure", "Nexus", "Top Skill",
    ]
    display = display.drop(columns=["Nexus"])

    st.markdown(
        f'<div style="font-family:\'Plus Jakarta Sans\',sans-serif; font-size:11px; '
        f'color:#6B7280; margin:0 0 8px 48px;">Showing {len(display):,} employees</div>',
        unsafe_allow_html=True,
    )

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        height=min(500, 40 + 35 * min(len(display), 14)),
    )

    st.markdown(
        "<div style='height:1px; background:#E0EAF4; margin:24px 48px;'></div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# 6. Alert cards
# ---------------------------------------------------------------------------

def _render_alerts(data: DashboardData) -> None:
    st.markdown(
        """
        <div style="max-width:1300px; margin:0 auto; padding:0 48px 48px;">
          <div style="display:inline-flex; align-items:center; gap:8px; margin-bottom:4px;
                      font-family:'Plus Jakarta Sans',sans-serif; font-size:9px; font-weight:500;
                      letter-spacing:4px; text-transform:uppercase; color:#C8982A;">
            <div style="width:24px; height:1px; background:#C8982A; flex-shrink:0;"></div>
            Alert Registry
          </div>
          <h2 style="font-family:'Fraunces',Georgia,serif; font-size:22px; font-weight:300;
                     color:#0a1628; margin:0 0 24px;">
            Organizational <em style="font-style:italic;">risk signals</em>
          </h2>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3, gap="medium")

    # Over-budget teams
    with col1:
        over_budget = data.team_summary[data.team_summary["budget_variance_pct"] > 10].head(5)
        _alert_card(
            label="Over-Budget Teams",
            count=len(over_budget),
            color="#F07020",
            items=[
                f"{r['team_name']} ({r['department']}): +{r['budget_variance_pct']:.1f}%"
                for _, r in over_budget.iterrows()
            ],
            footer="Teams with actual spend >10% above budget",
        )

    # Nexus employees
    with col2:
        nexus_table = data.employee_table[data.employee_table["is_nexus"]].head(5)
        _alert_card(
            label="Nexus Employees",
            count=data.n_nexus_employees,
            color="#7C4DBD",
            items=[
                f"{r['full_name']} — {r['department']} (Impact: {r['impact_score']:.0f})"
                for _, r in nexus_table.iterrows()
            ],
            footer="High-centrality individuals. Departure fragments the network.",
        )

    # High-fragility teams
    with col3:
        frag_df = pd.DataFrame(
            [(k, v) for k, v in data.team_fragility.items() if v > 0.6],
            columns=["team_id", "fragility"],
        ).sort_values("fragility", ascending=False).head(5)

        if not frag_df.empty:
            frag_named = frag_df.merge(
                data.teams[["team_id", "team_name", "department"]],
                on="team_id", how="left",
            )
            items = [
                f"{r['team_name']} ({r['department']}): fragility {r['fragility']:.2f}"
                for _, r in frag_named.iterrows()
            ]
        else:
            items = ["No high-fragility teams detected."]

        _alert_card(
            label="High-Fragility Teams",
            count=len(frag_df),
            color="#E03448",
            items=items,
            footer="Gini coefficient of betweenness centrality > 0.6.",
        )

    # Network + scoring metadata
    st.markdown(
        f"""
        <div style="max-width:1300px; margin:24px auto 0; padding:0 48px 48px;">
          <div style="background:#fff; border-left:3px solid #C8982A; border-radius:10px;
                      padding:20px 24px; box-shadow:0 1px 4px rgba(0,51,102,0.07);">
            <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:9px;
                        font-weight:700; letter-spacing:1.5px; text-transform:uppercase;
                        color:#C8982A; margin-bottom:8px;">Network Summary</div>
            <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:13px;
                        color:#475569; line-height:1.75;">
              Graph density: <strong>{data.graph_density:.4f}</strong> &nbsp;·&nbsp;
              Connected components: <strong>{data.n_components}</strong> &nbsp;·&nbsp;
              Nexus threshold: betweenness &gt; 0.70 or combined centrality ≥ 85th percentile &nbsp;·&nbsp;
              Scoring mode: <strong>{data.scoring_mode}</strong>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _alert_card(
    label: str,
    count: int,
    color: str,
    items: list[str],
    footer: str,
) -> None:
    """Render an alert card with count badge, items list, and footer note."""
    items_html = "".join(
        f'<li style="font-family:\'Plus Jakarta Sans\',sans-serif; font-size:12px; '
        f'color:#475569; line-height:2; padding:2px 0;">{item}</li>'
        for item in (items or ["No items."])
    )

    st.markdown(
        f"""
        <div style="background:#fff; border-radius:12px;
                    box-shadow:0 1px 4px rgba(0,51,102,0.08);
                    padding:24px; height:260px; overflow:hidden;">
          <div style="height:3px; background:{color}; border-radius:3px;
                      margin:-24px -24px 16px;"></div>
          <div style="display:flex; align-items:center; gap:12px; margin-bottom:12px;">
            <div style="font-family:'Fraunces',Georgia,serif; font-size:36px;
                        font-weight:300; color:{color}; line-height:1;">
              {count}
            </div>
            <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:10px;
                        font-weight:700; letter-spacing:2px; text-transform:uppercase;
                        color:{color};">
              {label}
            </div>
          </div>
          <ul style="list-style:none; margin:0; padding:0; overflow:hidden; max-height:120px;">
            {items_html}
          </ul>
          <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:10px;
                      color:#9CA3AF; margin-top:8px; line-height:1.5;">
            {footer}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
