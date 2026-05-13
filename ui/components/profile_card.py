"""Individual employee profile card components for the drill-down explorer.

Each function returns either a Plotly figure or renders directly into Streamlit.
The profile orchestrator (render_employee_profile) calls all sub-components.
"""

import logging

import networkx as nx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

logger = logging.getLogger(__name__)

# BRAND.md palette
_NAVY    = "#003366"
_GOLD    = "#C8982A"
_GOLD_LT = "#E8C46A"
_GREEN   = "#27B97C"
_ORANGE  = "#F07020"
_PURPLE  = "#7C4DBD"
_GRAY    = "#6B7280"
_LIGHT   = "#F4F6F9"
_WHITE   = "#FFFFFF"

_CHART_SERIES = [_NAVY, _GREEN, _PURPLE, _ORANGE]

# Proficiency level labels
_PROFICIENCY_LABELS = {1: "Beginner", 2: "Developing", 3: "Proficient", 4: "Advanced", 5: "Expert"}
_PROFICIENCY_COLORS = {1: "#E0EAF4", 2: "#99BBDD", 3: "#336699", 4: "#1A4D80", 5: "#003366"}


# ---------------------------------------------------------------------------
# Profile header
# ---------------------------------------------------------------------------

def render_profile_header(
    emp_row: pd.Series,
    is_nexus: bool,
    is_critical_skill_holder: bool,
    is_single_point_of_failure: bool,
    department_avg_impact: float,
) -> None:
    """Render the employee header card with name, role, badges, and quick stats."""
    name = str(emp_row.get("full_name", "Unknown"))
    role = str(emp_row.get("role_title", ""))
    seniority = str(emp_row.get("seniority_level", "mid")).title()
    dept = str(emp_row.get("department", ""))
    location = str(emp_row.get("location", ""))
    tenure = float(emp_row.get("tenure_years", 0))
    impact = float(emp_row.get("impact_score", 0))
    salary = float(emp_row.get("annual_salary", 0))
    benefits = float(emp_row.get("annual_benefits", 0))
    total_cost = salary + benefits

    badges_html = ""
    if is_nexus:
        badges_html += (
            '<span style="background:#FEF8E7;color:#7A5000;border:1px solid #C8982A;'
            'border-radius:20px;padding:3px 10px;font-size:10px;font-weight:600;'
            'font-family:\'Plus Jakarta Sans\',sans-serif;margin-right:6px;">'
            '★ Organizational Nexus</span>'
        )
    if is_critical_skill_holder:
        badges_html += (
            '<span style="background:#E0EAF4;color:#001F4D;border:1px solid #336699;'
            'border-radius:20px;padding:3px 10px;font-size:10px;font-weight:600;'
            'font-family:\'Plus Jakarta Sans\',sans-serif;margin-right:6px;">'
            '◈ Critical Skill Holder</span>'
        )
    if is_single_point_of_failure:
        badges_html += (
            '<span style="background:#FEF0E6;color:#7A3800;border:1px solid #F07020;'
            'border-radius:20px;padding:3px 10px;font-size:10px;font-weight:600;'
            'font-family:\'Plus Jakarta Sans\',sans-serif;margin-right:6px;">'
            '⚠ Single Point of Failure</span>'
        )

    impact_vs_dept = impact - department_avg_impact
    impact_delta_color = _GREEN if impact_vs_dept >= 0 else _ORANGE
    impact_delta_sign = "+" if impact_vs_dept >= 0 else ""

    st.markdown(
        f"""
        <div style="background:{_NAVY};padding:28px 36px;border-radius:12px;
                    margin-bottom:20px;">
          <div style="font-family:'Plus Jakarta Sans',sans-serif;font-size:9px;
                      letter-spacing:3px;text-transform:uppercase;
                      color:rgba(255,255,255,0.4);margin-bottom:10px;">
            {dept} · {seniority} · {location}
          </div>
          <h2 style="font-family:'Fraunces',Georgia,serif;font-size:26px;
                     font-weight:300;color:#fff;margin:0 0 4px;">{name}</h2>
          <div style="font-family:'Plus Jakarta Sans',sans-serif;font-size:14px;
                      color:rgba(255,255,255,0.6);margin-bottom:14px;">{role}</div>
          <div style="margin-bottom:16px;">{badges_html}</div>
          <div style="display:flex;gap:36px;flex-wrap:wrap;">
            <div>
              <div style="font-family:'Fraunces',Georgia,serif;font-size:28px;
                           font-weight:300;color:{_GOLD_LT};">{impact:.0f}</div>
              <div style="font-family:'Plus Jakarta Sans',sans-serif;font-size:10px;
                           color:rgba(255,255,255,0.45);">Impact Score</div>
            </div>
            <div>
              <div style="font-family:'Fraunces',Georgia,serif;font-size:28px;
                           font-weight:300;color:{impact_delta_color};">
                {impact_delta_sign}{impact_vs_dept:.1f}</div>
              <div style="font-family:'Plus Jakarta Sans',sans-serif;font-size:10px;
                           color:rgba(255,255,255,0.45);">vs Dept Avg</div>
            </div>
            <div>
              <div style="font-family:'Fraunces',Georgia,serif;font-size:28px;
                           font-weight:300;color:{_GOLD_LT};">{tenure:.1f}y</div>
              <div style="font-family:'Plus Jakarta Sans',sans-serif;font-size:10px;
                           color:rgba(255,255,255,0.45);">Tenure</div>
            </div>
            <div>
              <div style="font-family:'Fraunces',Georgia,serif;font-size:28px;
                           font-weight:300;color:{_GOLD_LT};">${total_cost/1000:.0f}K</div>
              <div style="font-family:'Plus Jakarta Sans',sans-serif;font-size:10px;
                           color:rgba(255,255,255,0.45);">Annual Cost</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Impact score radar chart
# ---------------------------------------------------------------------------

def render_impact_radar(scores_row: pd.Series) -> go.Figure:
    """5-axis radar chart showing impact score component breakdown.

    Axes: KPI Performance, Network Influence, Skills Criticality,
          Cost Efficiency (inverted replacement cost), Confidence.
    """
    kpi  = float(scores_row.get("kpi_contribution",     0)) * 100
    net  = float(scores_row.get("network_contribution", 0)) * 100
    skl  = float(scores_row.get("skills_contribution",  0)) * 100
    cost = float(scores_row.get("cost_contribution",    0)) * 100
    conf = float(scores_row.get("confidence",           0.6)) * 100

    categories = ["KPI Performance", "Network Influence", "Skills Criticality",
                  "Cost Efficiency", "Confidence"]
    values = [kpi, net, skl, cost, conf]
    values_closed = values + [values[0]]
    categories_closed = categories + [categories[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values_closed,
        theta=categories_closed,
        fill="toself",
        fillcolor=f"rgba(0,51,102,0.15)",
        line=dict(color=_NAVY, width=2),
        name="Impact Components",
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(244,246,249,0.5)",
            radialaxis=dict(
                visible=True, range=[0, 100],
                tickfont=dict(size=8, color=_GRAY),
                tickvals=[0, 25, 50, 75, 100],
                gridcolor="rgba(0,51,102,0.1)",
            ),
            angularaxis=dict(
                tickfont=dict(family="Plus Jakarta Sans, sans-serif", size=10, color=_NAVY),
                linecolor="rgba(0,51,102,0.2)",
            ),
        ),
        showlegend=False,
        height=280,
        margin=dict(l=40, r=40, t=20, b=20),
        paper_bgcolor=_LIGHT,
    )
    return fig


# ---------------------------------------------------------------------------
# Skill matrix
# ---------------------------------------------------------------------------

def render_skill_matrix(
    employee_id: str,
    employee_skills_df: pd.DataFrame,
    skills_df: pd.DataFrame,
) -> go.Figure:
    """Horizontal bar chart of employee skills × proficiency level."""
    if employee_skills_df.empty or skills_df.empty:
        return _empty_chart("No skill data available.", 200)

    emp_skl = employee_skills_df[employee_skills_df["employee_id"] == employee_id].copy()
    if emp_skl.empty:
        return _empty_chart("No skills recorded for this employee.", 200)

    emp_skl = emp_skl.merge(
        skills_df[["skill_id", "skill_name", "category", "is_critical"]],
        on="skill_id",
        how="left",
    )
    emp_skl["proficiency"] = pd.to_numeric(emp_skl["proficiency"], errors="coerce").fillna(1)
    emp_skl = emp_skl.sort_values(["is_critical", "proficiency"], ascending=[False, False])

    colors = [
        (_GOLD if bool(row["is_critical"]) else _NAVY)
        for _, row in emp_skl.iterrows()
    ]

    proficiency_labels = emp_skl["proficiency"].map(
        lambda p: _PROFICIENCY_LABELS.get(int(p), str(int(p)))
    )

    fig = go.Figure(go.Bar(
        x=emp_skl["proficiency"].tolist(),
        y=emp_skl["skill_name"].tolist(),
        orientation="h",
        marker_color=colors,
        text=proficiency_labels.tolist(),
        textposition="inside",
        textfont=dict(family="Plus Jakarta Sans, sans-serif", size=9, color="#fff"),
        hovertemplate="<b>%{y}</b><br>Proficiency: %{text}<extra></extra>",
    ))
    fig.update_layout(
        xaxis=dict(range=[0, 5.5], tickvals=[1, 2, 3, 4, 5],
                   ticktext=["Beginner", "Developing", "Proficient", "Advanced", "Expert"],
                   tickfont=dict(size=8, color=_GRAY)),
        yaxis=dict(tickfont=dict(family="Plus Jakarta Sans, sans-serif", size=10, color=_NAVY)),
        height=max(200, len(emp_skl) * 30 + 60),
        margin=dict(l=140, r=20, t=16, b=40),
        paper_bgcolor=_LIGHT,
        plot_bgcolor=_WHITE,
        showlegend=False,
    )
    return fig


# ---------------------------------------------------------------------------
# Ego network (1-hop subgraph)
# ---------------------------------------------------------------------------

def render_ego_network(
    employee_id: str,
    G: nx.Graph,
    employee_table: pd.DataFrame,
    nexus_ids: set[str],
    radius: int = 1,
) -> go.Figure:
    """1-hop (or 2-hop) neighborhood graph centered on the employee."""
    if employee_id not in G:
        return _empty_chart("Employee has no recorded collaboration edges.", 300)

    ego = nx.ego_graph(G, employee_id, radius=radius, undirected=True)
    if len(ego.nodes) == 1:
        return _empty_chart("No collaborators in the current dataset.", 300)

    from ui.components.graph_viz import render_network_graph
    emp_subset = (
        employee_table[employee_table["employee_id"].isin(ego.nodes)]
        if not employee_table.empty else employee_table
    )
    fig = render_network_graph(
        graph=ego,
        employee_table=emp_subset,
        nexus_ids=nexus_ids,
        title=f"Collaboration Network ({len(ego.nodes)} employees)",
        height=340,
    )
    return fig


# ---------------------------------------------------------------------------
# Performance sparkline
# ---------------------------------------------------------------------------

def render_performance_sparkline(
    employee_id: str,
    performance_df: pd.DataFrame,
) -> go.Figure:
    """Quarterly KPI trend for a single employee."""
    if performance_df.empty:
        return _empty_chart("No performance data available.", 180)

    perf = performance_df[performance_df["employee_id"] == employee_id].copy()
    if perf.empty:
        return _empty_chart("No performance records for this employee.", 180)

    perf = perf.sort_values("review_date")
    perf["kpi_score"] = pd.to_numeric(perf["kpi_score"], errors="coerce")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=perf["review_period"].tolist() if "review_period" in perf else perf["review_date"].astype(str).tolist(),
        y=perf["kpi_score"].tolist(),
        mode="lines+markers",
        line=dict(color=_NAVY, width=2),
        marker=dict(size=6, color=_GOLD, line=dict(width=1.5, color=_NAVY)),
        fill="tozeroy",
        fillcolor="rgba(0,51,102,0.06)",
        name="KPI Score",
        hovertemplate="Period: %{x}<br>KPI: %{y:.2f}<extra></extra>",
    ))
    # Target line at 3.5
    fig.add_hline(y=3.5, line=dict(dash="dash", color=_GOLD, width=1),
                  annotation_text="Target 3.5", annotation_position="bottom right",
                  annotation_font_size=8)
    fig.update_layout(
        height=180,
        margin=dict(l=20, r=20, t=12, b=32),
        xaxis=dict(tickfont=dict(size=8, color=_GRAY)),
        yaxis=dict(range=[0, 5.2], tickfont=dict(size=8, color=_GRAY)),
        paper_bgcolor=_LIGHT,
        plot_bgcolor=_WHITE,
        showlegend=False,
    )
    return fig


# ---------------------------------------------------------------------------
# Cost breakdown
# ---------------------------------------------------------------------------

def render_cost_breakdown(emp_row: pd.Series) -> go.Figure:
    """Horizontal stacked bar: annual salary vs annual benefits."""
    salary   = float(emp_row.get("annual_salary",   0))
    benefits = float(emp_row.get("annual_benefits", 0))

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Base Salary",
        x=[salary],
        y=["Cost"],
        orientation="h",
        marker_color=_NAVY,
        text=f"${salary/1000:.0f}K",
        textposition="inside",
        textfont=dict(color="#fff", size=10),
        hovertemplate="Salary: $%{x:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Benefits",
        x=[benefits],
        y=["Cost"],
        orientation="h",
        marker_color=_GOLD,
        text=f"${benefits/1000:.0f}K",
        textposition="inside",
        textfont=dict(color="#fff", size=10),
        hovertemplate="Benefits: $%{x:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        barmode="stack",
        height=100,
        margin=dict(l=20, r=20, t=8, b=8),
        xaxis=dict(tickformat="$,.0f", tickfont=dict(size=8, color=_GRAY)),
        yaxis=dict(showticklabels=False),
        paper_bgcolor=_LIGHT,
        plot_bgcolor=_WHITE,
        legend=dict(orientation="h", y=1.3, font=dict(size=9)),
        showlegend=True,
    )
    return fig


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def render_employee_profile(
    employee_id: str,
    employee_table: pd.DataFrame,
    impact_scores: pd.DataFrame,
    performance_df: pd.DataFrame,
    employee_skills_df: pd.DataFrame,
    skills_df: pd.DataFrame,
    collaboration_graph: nx.Graph,
    nexus_ids: set[str],
    critical_skill_holders: dict[str, list[str]],
    dept_summary: pd.DataFrame,
) -> None:
    """Render the complete individual employee profile card."""
    emp_rows = employee_table[employee_table["employee_id"] == employee_id]
    if emp_rows.empty:
        st.warning("Employee not found in the current dataset.")
        return
    emp_row = emp_rows.iloc[0]

    # Determine badges
    is_nexus = employee_id in nexus_ids
    is_crit_holder = any(
        employee_id in holders
        for holders in critical_skill_holders.values()
    )
    # Single point of failure: is the ONLY holder of any critical skill
    is_spof = any(
        len(holders) == 1 and employee_id in holders
        for holders in critical_skill_holders.values()
    )

    dept = str(emp_row.get("department", ""))
    dept_avg = float(
        dept_summary.loc[dept_summary["department"] == dept, "avg_impact"].iloc[0]
        if not dept_summary.empty and dept in dept_summary["department"].values
        else 0
    )

    # Header
    render_profile_header(emp_row, is_nexus, is_crit_holder, is_spof, dept_avg)

    # Two-column layout: radar + skills
    scores_row = pd.Series()
    if not impact_scores.empty:
        sr = impact_scores[impact_scores["employee_id"] == employee_id]
        if not sr.empty:
            scores_row = sr.iloc[0]

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown(
            '<div style="font-family:\'Plus Jakarta Sans\',sans-serif;font-size:9px;'
            'font-weight:700;letter-spacing:3px;text-transform:uppercase;color:#C8982A;'
            'margin-bottom:8px;">IMPACT BREAKDOWN</div>',
            unsafe_allow_html=True,
        )
        if not scores_row.empty:
            st.plotly_chart(render_impact_radar(scores_row), use_container_width=True,
                            config={"displayModeBar": False})
        else:
            st.info("Impact component data not available.")

    with col_right:
        st.markdown(
            '<div style="font-family:\'Plus Jakarta Sans\',sans-serif;font-size:9px;'
            'font-weight:700;letter-spacing:3px;text-transform:uppercase;color:#C8982A;'
            'margin-bottom:8px;">SKILL MATRIX</div>',
            unsafe_allow_html=True,
        )
        st.plotly_chart(
            render_skill_matrix(employee_id, employee_skills_df, skills_df),
            use_container_width=True,
            config={"displayModeBar": False},
        )

    # Performance sparkline + cost breakdown
    col_a, col_b = st.columns([2, 1])
    with col_a:
        st.markdown(
            '<div style="font-family:\'Plus Jakarta Sans\',sans-serif;font-size:9px;'
            'font-weight:700;letter-spacing:3px;text-transform:uppercase;color:#C8982A;'
            'margin-bottom:8px;">KPI TREND</div>',
            unsafe_allow_html=True,
        )
        st.plotly_chart(
            render_performance_sparkline(employee_id, performance_df),
            use_container_width=True,
            config={"displayModeBar": False},
        )
    with col_b:
        st.markdown(
            '<div style="font-family:\'Plus Jakarta Sans\',sans-serif;font-size:9px;'
            'font-weight:700;letter-spacing:3px;text-transform:uppercase;color:#C8982A;'
            'margin-bottom:8px;">COST STRUCTURE</div>',
            unsafe_allow_html=True,
        )
        st.plotly_chart(
            render_cost_breakdown(emp_row),
            use_container_width=True,
            config={"displayModeBar": False},
        )

    # Ego network
    st.markdown(
        '<div style="font-family:\'Plus Jakarta Sans\',sans-serif;font-size:9px;'
        'font-weight:700;letter-spacing:3px;text-transform:uppercase;color:#C8982A;'
        'margin:16px 0 8px;">COLLABORATION NETWORK (1-hop)</div>',
        unsafe_allow_html=True,
    )
    st.plotly_chart(
        render_ego_network(employee_id, collaboration_graph, employee_table, nexus_ids),
        use_container_width=True,
        config={"displayModeBar": True, "modeBarButtonsToRemove": ["select2d", "lasso2d"]},
    )


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _empty_chart(message: str, height: int = 200) -> go.Figure:
    return go.Figure(
        layout=go.Layout(
            height=height,
            annotations=[dict(
                text=message,
                xref="paper", yref="paper", x=0.5, y=0.5,
                showarrow=False,
                font=dict(family="Plus Jakarta Sans, sans-serif", size=12, color=_GRAY),
            )],
            paper_bgcolor=_LIGHT,
            plot_bgcolor=_LIGHT,
            margin=dict(l=10, r=10, t=10, b=10),
        )
    )
