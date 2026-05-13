"""Strategic Planning — Sprint 6.

Four-tab layout:
  Tab 1 — Future State Designer  : role builder, cost analysis, internal candidates
  Tab 2 — Skills Gap Analysis    : gap heatmap, build-vs-buy table
  Tab 3 — Transition Roadmap     : Gantt chart, phase cards, risk register
  Tab 4 — Strategy Comparison    : radar chart, scoring table, recommendation
"""

from __future__ import annotations

import logging

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ui.data_loader import DashboardData, load_dashboard_data

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Brand palette
# ---------------------------------------------------------------------------

_C = {
    "primary":  "#003366",
    "green":    "#27B97C",
    "purple":   "#7C4DBD",
    "orange":   "#F07020",
    "gold":     "#C8982A",
    "gold_lt":  "#E8C46A",
    "light":    "#F4F6F9",
    "mid":      "#6B7280",
    "dark":     "#1C1C2E",
    "white":    "#FFFFFF",
}
_FONT = "'Plus Jakarta Sans', sans-serif"

_SEVERITY_COLORS = {
    "Critical": "#7C4DBD",
    "High":     "#F07020",
    "Moderate": "#C8982A",
    "Low":      "#27B97C",
    "Covered":  "#27B97C",
}

_PHASE_COLORS = ["#003366", "#C8982A", "#27B97C"]

_REC_COLORS = {
    "Build":   "#27B97C",
    "Buy":     "#F07020",
    "Hybrid":  "#C8982A",
    "Covered": "#6B7280",
}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def render() -> None:
    demo_mode: bool = st.session_state.get("demo_mode", True)
    scenario_id: str = st.session_state.get("demo_scenario", "A")
    size: str = st.session_state.get("demo_size", "medium")

    with st.spinner("Loading strategic planning data…"):
        try:
            data = load_dashboard_data(demo_mode, scenario_id, size)
        except (NotImplementedError, RuntimeError) as exc:
            st.error(str(exc))
            return

    _render_hero(data)

    tab_future, tab_skills, tab_roadmap, tab_strategy = st.tabs([
        "🏗  Future State Designer",
        "📚  Skills Gap Analysis",
        "🗓  Transition Roadmap",
        "⚖  Strategy Comparison",
    ])

    with tab_future:
        _render_future_state_tab(data)

    with tab_skills:
        _render_skills_gap_tab(data)

    with tab_roadmap:
        _render_roadmap_tab(data)

    with tab_strategy:
        _render_strategy_comparison_tab(data)


# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------

def _render_hero(data: DashboardData) -> None:
    st.markdown(
        f"""
        <div style="background:#003366;background-image:
          linear-gradient(rgba(255,255,255,.025) 1px,transparent 1px),
          linear-gradient(90deg,rgba(255,255,255,.025) 1px,transparent 1px);
          background-size:48px 48px;padding:32px 40px 24px;">
          <div style="font-family:'Fraunces',Georgia,serif;font-size:9px;
                      letter-spacing:4px;text-transform:uppercase;
                      color:rgba(255,255,255,0.4);margin-bottom:6px;">Strategic Planning</div>
          <h1 style="font-family:'Fraunces',Georgia,serif;font-size:28px;
                     font-weight:300;color:#fff;margin:0 0 4px;">
            Workforce
            <em style="color:{_C['gold_lt']};font-style:italic;">Strategy Designer</em>
          </h1>
          <p style="font-family:{_FONT};font-size:13px;
                    color:rgba(255,255,255,0.55);margin:0;">
            {data.org_name} · {data.total_headcount:,} employees · Scenario {data.scenario_id}
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ===========================================================================
# TAB 1 — Future State Designer
# ===========================================================================

def _render_future_state_tab(data: DashboardData) -> None:
    from strategic_planner.future_state import (
        FutureStateDesign, ProposedRole, FutureStateAnalyzer, build_demo_design
    )

    st.markdown(
        f"<p style='font-family:{_FONT};font-size:13px;color:#6B7280;margin:12px 0 20px;'>"
        "Model a proposed future org structure — define teams, roles, and seniority mix. "
        "The analyser identifies internal candidates, flags hiring needs, and projects "
        "transition costs.</p>",
        unsafe_allow_html=True,
    )

    # --- Sidebar controls for the design ---
    col_controls, col_results = st.columns([2, 3], gap="large")

    with col_controls:
        st.markdown(
            "<h3 style='font-family:\"Fraunces\",Georgia,serif;font-size:16px;"
            "color:#003366;font-weight:300;margin-bottom:12px;'>"
            "Design Parameters</h3>",
            unsafe_allow_html=True,
        )

        design_name = st.text_input("Design name", value="2026 Target Structure")
        budget_envelope = st.number_input(
            "Annual budget envelope ($)",
            min_value=0,
            value=int(data.total_budget * 0.95) if data.total_budget > 0 else int(data.total_spend * 0.95),
            step=50_000,
            help="Set to 0 for unconstrained",
        )

        st.markdown("---")
        st.markdown(
            "<div style='font-family:\"Plus Jakarta Sans\",sans-serif;font-size:11px;"
            "color:#6B7280;margin-bottom:6px;'>Quick demo — load preset design:</div>",
            unsafe_allow_html=True,
        )
        if st.button("Load Demo Design", use_container_width=True):
            st.session_state["sp_demo_design"] = True

    with col_results:
        with st.spinner("Analysing future state…"):
            try:
                design = build_demo_design(data.org_size, data.scenario_id)
                design.name = design_name
                design.annual_budget_envelope = float(budget_envelope)

                analyser = FutureStateAnalyzer()
                fa = analyser.analyze(
                    design=design,
                    employees_df=data.employees,
                    employee_skills_df=data.employee_skills,
                    skills_df=data.skills,
                    current_total_spend=data.total_spend,
                )
                _render_future_state_result(fa, data)
            except Exception as exc:
                st.error(f"Future state analysis failed: {exc}")


def _render_future_state_result(fa, data: DashboardData) -> None:
    # KPI row
    delta_color = _C["orange"] if fa.delta_vs_current > 0 else _C["green"]
    delta_sign  = "+" if fa.delta_vs_current > 0 else ""
    cols = st.columns(4)
    _kpi(cols[0], "Annual Cost", f"${fa.estimated_annual_cost:,.0f}", "proposed",  _C["primary"])
    _kpi(cols[1], "vs Current",  f"{delta_sign}${abs(fa.delta_vs_current):,.0f}", "delta",  delta_color)
    _kpi(cols[2], "Internal Fills", str(fa.n_internal_fills), "employees", _C["purple"])
    _kpi(cols[3], "External Hires", str(fa.n_external_hires), "positions", _C["gold"])

    if fa.warnings:
        for w in fa.warnings:
            st.warning(w)

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    # Proposed structure table
    st.markdown(
        "<h4 style='font-family:\"Fraunces\",Georgia,serif;font-size:14px;"
        "color:#003366;font-weight:300;margin:16px 0 8px;'>"
        "Proposed Team Structure</h4>",
        unsafe_allow_html=True,
    )

    summary = fa.summary_df()
    if not summary.empty:
        summary_display = summary.copy()
        summary_display["est_salary"] = summary_display["est_salary"].map("${:,.0f}".format)
        summary_display["team_cost"]  = summary_display["team_cost"].map("${:,.0f}".format)
        summary_display.columns = ["Team", "Role", "Seniority", "Count", "Est. Salary/FTE", "Team Cost"]
        st.dataframe(summary_display, use_container_width=True, hide_index=True)

    # Cost treemap
    if not summary.empty:
        fig = go.Figure(go.Treemap(
            labels=summary["role"].tolist(),
            parents=summary["team"].tolist(),
            values=summary["team_cost"].tolist(),
            textinfo="label+value",
            texttemplate="%{label}<br>$%{value:,.0f}",
            marker_colorscale=[[0, "#E8F0FA"], [1, "#003366"]],
            hovertemplate="<b>%{label}</b><br>Team: %{parent}<br>Cost: $%{value:,.0f}<extra></extra>",
        ))
        fig.update_layout(
            height=280,
            margin=dict(l=0, r=0, t=8, b=8),
            paper_bgcolor=_C["light"],
            font=dict(family=_FONT, size=11),
        )
        st.plotly_chart(fig, use_container_width=True)

    # Internal candidates
    if fa.internal_fills:
        st.markdown(
            "<h4 style='font-family:\"Fraunces\",Georgia,serif;font-size:14px;"
            "color:#003366;font-weight:300;margin:16px 0 8px;'>"
            f"Internal Candidates ({len(fa.internal_fills)})</h4>",
            unsafe_allow_html=True,
        )
        cand_rows = []
        for c in fa.internal_fills[:10]:
            cand_rows.append({
                "Employee": c.full_name,
                "Current Role": c.current_role,
                "Proposed Role": c.proposed_role,
                "Match": f"{c.match_score:.0f}%",
                "Skill Gaps": ", ".join(c.skill_gap) if c.skill_gap else "None",
                "Training Cost": f"${c.training_cost:,.0f}" if c.training_cost > 0 else "—",
            })
        st.dataframe(pd.DataFrame(cand_rows), use_container_width=True, hide_index=True)

    # External hiring needs
    if fa.external_hiring_needs:
        st.markdown(
            "<h4 style='font-family:\"Fraunces\",Georgia,serif;font-size:14px;"
            "color:#003366;font-weight:300;margin:16px 0 8px;'>"
            f"External Hiring Needs ({fa.n_external_hires} positions)</h4>",
            unsafe_allow_html=True,
        )
        hire_rows = []
        for n in fa.external_hiring_needs:
            hire_rows.append({
                "Team": n.team_name,
                "Role": n.role_title,
                "Seniority": n.seniority_level.title(),
                "Count": n.count,
                "Annual Cost": f"${n.estimated_annual_cost:,.0f}",
                "Time to Hire": f"~{n.time_to_hire_months:.1f} mo",
            })
        st.dataframe(pd.DataFrame(hire_rows), use_container_width=True, hide_index=True)

    # Transition cost breakdown
    st.markdown(
        "<h4 style='font-family:\"Fraunces\",Georgia,serif;font-size:14px;"
        "color:#003366;font-weight:300;margin:16px 0 8px;'>"
        "Transition Cost Breakdown</h4>",
        unsafe_allow_html=True,
    )
    cost_items = [
        ("Severance", fa.severance_cost, _C["orange"]),
        ("Hiring Fees", fa.hiring_cost, _C["gold"]),
        ("Training", fa.training_cost, _C["purple"]),
    ]
    fig = go.Figure(go.Bar(
        x=[c[0] for c in cost_items],
        y=[c[1] for c in cost_items],
        marker_color=[c[2] for c in cost_items],
        text=[f"${c[1]:,.0f}" for c in cost_items],
        textposition="outside",
        hovertemplate="%{x}: $%{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        height=220,
        margin=dict(l=0, r=0, t=8, b=8),
        paper_bgcolor=_C["light"],
        plot_bgcolor="white",
        font=dict(family=_FONT, size=11),
        yaxis=dict(tickformat="$,.0f", gridcolor="#E0EAF4"),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        f"Total transition investment: **${fa.total_transition_cost:,.0f}** · "
        f"Estimated execution: **{fa.months_to_target} months**"
    )


# ===========================================================================
# TAB 2 — Skills Gap Analysis
# ===========================================================================

def _render_skills_gap_tab(data: DashboardData) -> None:
    from strategic_planner.skills_gap import (
        SkillsGapAnalyzer, build_demo_requirements
    )

    st.markdown(
        f"<p style='font-family:{_FONT};font-size:13px;color:#6B7280;margin:12px 0 20px;'>"
        "Compares current workforce skill coverage against 12–24 month requirements. "
        "For each gap, the Build vs Buy analysis compares upskilling cost against external hiring.</p>",
        unsafe_allow_html=True,
    )

    with st.spinner("Analysing skills gaps…"):
        try:
            requirements = build_demo_requirements(data.employees, data.skills)
            analyser = SkillsGapAnalyzer()
            sa = analyser.analyze(requirements, data.employees, data.employee_skills, data.skills)
            _render_skills_gap_result(sa)
        except Exception as exc:
            st.error(f"Skills gap analysis failed: {exc}")


def _render_skills_gap_result(sa) -> None:
    # KPI row
    n_gaps = sum(1 for g in sa.gaps if g.gap < 0)
    cols = st.columns(4)
    _kpi(cols[0], "Critical Gaps", str(sa.n_critical_gaps), "skills", _C["purple"])
    _kpi(cols[1], "Total Gaps",    str(n_gaps), "skills", _C["orange"])
    _kpi(cols[2], "Skills Covered", str(sa.n_covered), "of " + str(len(sa.gaps)), _C["green"])
    _kpi(cols[3], "Build Cost",  f"${sa.total_build_cost:,.0f}", "to upskill", _C["gold"])

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    # Gap heatmap: skill × severity
    col_heat, col_rec = st.columns([3, 2], gap="large")

    with col_heat:
        st.markdown(
            "<h3 style='font-family:\"Fraunces\",Georgia,serif;font-size:16px;"
            "color:#003366;font-weight:300;margin-bottom:8px;'>"
            "Skills Coverage Heatmap</h3>",
            unsafe_allow_html=True,
        )
        _render_gap_heatmap(sa)

    with col_rec:
        st.markdown(
            "<h3 style='font-family:\"Fraunces\",Georgia,serif;font-size:16px;"
            "color:#003366;font-weight:300;margin-bottom:8px;'>"
            "Build vs Buy Summary</h3>",
            unsafe_allow_html=True,
        )
        _render_build_vs_buy_chart(sa)

    # Detail table
    st.markdown(
        "<h3 style='font-family:\"Fraunces\",Georgia,serif;font-size:16px;"
        "color:#003366;font-weight:300;margin:16px 0 8px;'>"
        "Gap Detail by Skill</h3>",
        unsafe_allow_html=True,
    )
    _render_gap_detail_table(sa)

    # Adjacency candidates
    adjacency_gaps = [g for g in sa.gaps if g.adjacency_candidates]
    if adjacency_gaps:
        st.markdown(
            "<h3 style='font-family:\"Fraunces\",Georgia,serif;font-size:16px;"
            "color:#003366;font-weight:300;margin:16px 0 8px;'>"
            "Adjacency Upskilling Candidates</h3>",
            unsafe_allow_html=True,
        )
        for g in adjacency_gaps[:3]:
            with st.expander(f"{g.skill_name} — {len(g.adjacency_candidates)} candidate(s)", expanded=False):
                cand_rows = [{
                    "Employee": c.full_name,
                    "Adjacent Skills": ", ".join(c.current_skills),
                    "Adjacency Score": f"{c.adjacency_score:.0f}%",
                    "Training Months": f"{c.training_months:.1f}",
                    "Training Cost": f"${c.training_cost:,.0f}",
                } for c in g.adjacency_candidates]
                st.dataframe(pd.DataFrame(cand_rows), use_container_width=True, hide_index=True)


def _render_gap_heatmap(sa) -> None:
    skills = [g.skill_name for g in sa.gaps]
    coverages = [g.coverage_pct for g in sa.gaps]
    severities = [g.severity for g in sa.gaps]
    colors = [_SEVERITY_COLORS.get(s, _C["mid"]) for s in severities]

    fig = go.Figure(go.Bar(
        x=coverages,
        y=skills,
        orientation="h",
        marker_color=colors,
        text=[f"{c:.0f}%" for c in coverages],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Coverage: %{x:.0f}%<extra></extra>",
    ))
    fig.add_vline(x=100, line_dash="dash", line_color=_C["green"],
                  annotation_text="100% covered", annotation_font_size=10)
    fig.update_layout(
        height=max(280, len(skills) * 28 + 60),
        margin=dict(l=0, r=60, t=8, b=8),
        paper_bgcolor=_C["light"],
        plot_bgcolor="white",
        font=dict(family=_FONT, size=11),
        xaxis=dict(title="Coverage (%)", range=[0, 130], showgrid=True, gridcolor="#E0EAF4"),
        yaxis=dict(autorange="reversed"),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_build_vs_buy_chart(sa) -> None:
    gaps_with_shortage = [g for g in sa.gaps if g.gap < 0]
    if not gaps_with_shortage:
        st.success("No gaps requiring Build or Buy action.")
        return

    # Count recommendations
    from collections import Counter
    rec_counts = Counter(g.recommendation for g in gaps_with_shortage)

    fig = go.Figure(go.Pie(
        labels=list(rec_counts.keys()),
        values=list(rec_counts.values()),
        hole=0.55,
        marker_colors=[_REC_COLORS.get(k, _C["mid"]) for k in rec_counts.keys()],
        textinfo="label+value",
        textfont=dict(family=_FONT, size=11),
        hovertemplate="%{label}: %{value} skills<extra></extra>",
    ))
    fig.update_layout(
        height=220,
        margin=dict(l=0, r=0, t=8, b=8),
        paper_bgcolor=_C["light"],
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    col_b, col_h = st.columns(2)
    with col_b:
        st.metric("Total Build Cost", f"${sa.total_build_cost:,.0f}")
    with col_h:
        st.metric("Total Buy Cost", f"${sa.total_buy_cost:,.0f}")


def _render_gap_detail_table(sa) -> None:
    def _sev_badge(sev: str) -> str:
        color = _SEVERITY_COLORS.get(sev, _C["mid"])
        return f'<span style="background:{color}20;color:{color};padding:2px 8px;border-radius:4px;font-size:10px;font-weight:600;">{sev}</span>'

    def _rec_badge(rec: str) -> str:
        color = _REC_COLORS.get(rec, _C["mid"])
        return f'<span style="background:{color}20;color:{color};padding:2px 6px;border-radius:3px;font-size:10px;font-weight:600;">{rec}</span>'

    rows_html = ""
    for g in sa.gaps:
        gap_str = f"+{g.gap}" if g.gap >= 0 else str(g.gap)
        rows_html += (
            f"<tr style='border-bottom:1px solid #E0EAF4;'>"
            f"<td style='padding:8px 12px;font-weight:600;'>{g.skill_name}"
            f"{'<span style=\"color:#C8982A;margin-left:4px;\">★</span>' if g.is_critical else ''}</td>"
            f"<td style='padding:8px 12px;text-align:center;'>{g.required_headcount}</td>"
            f"<td style='padding:8px 12px;text-align:center;'>{g.current_holders}</td>"
            f"<td style='padding:8px 12px;text-align:center;'>{gap_str}</td>"
            f"<td style='padding:8px 12px;'>{_sev_badge(g.severity)}</td>"
            f"<td style='padding:8px 12px;'>{_rec_badge(g.recommendation)}</td>"
            f"<td style='padding:8px 12px;color:#6B7280;font-size:11px;'>"
            f"{'${:,.0f}'.format(min(g.build_cost_total, g.buy_cost_total)) if g.gap < 0 else '—'}</td>"
            f"</tr>"
        )

    st.markdown(
        f"""
        <div style="background:#fff;border-radius:8px;overflow:hidden;
                    box-shadow:0 1px 4px rgba(0,51,102,0.08);">
          <table style="width:100%;border-collapse:collapse;
                        font-family:{_FONT};font-size:12px;">
            <thead>
              <tr style="background:#003366;color:#fff;">
                <th style="padding:8px 12px;text-align:left;">Skill</th>
                <th style="padding:8px 12px;text-align:center;">Required</th>
                <th style="padding:8px 12px;text-align:center;">Current</th>
                <th style="padding:8px 12px;text-align:center;">Gap</th>
                <th style="padding:8px 12px;text-align:left;">Severity</th>
                <th style="padding:8px 12px;text-align:left;">Action</th>
                <th style="padding:8px 12px;text-align:left;">Est. Cost</th>
              </tr>
            </thead>
            <tbody>{rows_html}</tbody>
          </table>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ===========================================================================
# TAB 3 — Transition Roadmap
# ===========================================================================

def _render_roadmap_tab(data: DashboardData) -> None:
    from strategic_planner.future_state import build_demo_design, FutureStateAnalyzer
    from strategic_planner.skills_gap import SkillsGapAnalyzer, build_demo_requirements
    from strategic_planner.transition_planner import TransitionPlanner

    st.markdown(
        f"<p style='font-family:{_FONT};font-size:13px;color:#6B7280;margin:12px 0 20px;'>"
        "Phased 24-month roadmap from current state to target structure. "
        "Phase costs, action lists, risk register, and executive summary included.</p>",
        unsafe_allow_html=True,
    )

    with st.spinner("Generating transition roadmap…"):
        try:
            design = build_demo_design(data.org_size, data.scenario_id)
            fa = FutureStateAnalyzer().analyze(
                design, data.employees, data.employee_skills, data.skills, data.total_spend
            )
            requirements = build_demo_requirements(data.employees, data.skills)
            sa = SkillsGapAnalyzer().analyze(requirements, data.employees, data.employee_skills, data.skills)
            plan = TransitionPlanner().plan(fa, sa, data.employees, data.nexus_ids)
            _render_roadmap_result(plan, fa)
        except Exception as exc:
            st.error(f"Transition planning failed: {exc}")


def _render_roadmap_result(plan, fa) -> None:
    # Executive summary
    st.markdown(
        f"""
        <div style="background:#fff;border-radius:8px;padding:20px;
                    box-shadow:0 1px 4px rgba(0,51,102,0.08);margin-bottom:20px;
                    border-left:4px solid {_C['primary']};">
          <div style="font-family:'Fraunces',Georgia,serif;font-size:16px;
                      color:#003366;font-weight:300;margin-bottom:10px;">
            Executive Summary</div>
          <div style="font-family:{_FONT};font-size:13px;color:#374151;line-height:1.7;">
          {plan.executive_summary.replace("**", "<b>").replace("**", "</b>")}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # KPI row
    risk_color = {
        "High": _C["orange"], "Medium": _C["gold"], "Low": _C["green"]
    }.get(plan.knowledge_loss_risk, _C["mid"])
    cols = st.columns(4)
    _kpi(cols[0], "Total Transition Cost", f"${plan.total_transition_cost:,.0f}", "one-time", _C["primary"])
    _kpi(cols[1], "Timeline",  f"{plan.total_months} months", "to target", _C["purple"])
    _kpi(cols[2], "Knowledge Risk", plan.knowledge_loss_risk, "rating", risk_color)
    _kpi(cols[3], "Productivity Dip", f"{plan.productivity_dip_pct:.0f}%", "peak Phase 2", _C["orange"])

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    # Gantt chart
    st.markdown(
        "<h3 style='font-family:\"Fraunces\",Georgia,serif;font-size:16px;"
        "color:#003366;font-weight:300;margin-bottom:8px;'>Transition Timeline</h3>",
        unsafe_allow_html=True,
    )
    _render_gantt(plan)

    # Phase cards
    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
    phase_cols = st.columns(3)
    for i, (phase, col) in enumerate(zip(plan.phases, phase_cols)):
        with col:
            pcolor = _PHASE_COLORS[i % len(_PHASE_COLORS)]
            rcolor = {"High": _C["orange"], "Medium": _C["gold"], "Low": _C["green"]}.get(
                phase.risk_level, _C["mid"]
            )
            st.markdown(
                f"""
                <div style="background:#fff;border-radius:8px;padding:16px;
                            box-shadow:0 1px 4px rgba(0,51,102,0.08);
                            border-top:3px solid {pcolor};">
                  <div style="font-family:{_FONT};font-size:9px;font-weight:700;
                              letter-spacing:2px;text-transform:uppercase;
                              color:#6B7280;margin-bottom:4px;">
                    Months {phase.months_start}–{phase.months_end}</div>
                  <div style="font-family:'Fraunces',Georgia,serif;font-size:14px;
                              color:#003366;font-weight:300;margin-bottom:6px;">
                    {phase.name}</div>
                  <div style="font-family:{_FONT};font-size:11px;color:#6B7280;
                              margin-bottom:8px;">{phase.theme}</div>
                  <div style="font-family:{_FONT};font-size:12px;margin-bottom:4px;">
                    💰 <b>${phase.cost_estimate:,.0f}</b></div>
                  <div style="font-family:{_FONT};font-size:12px;margin-bottom:4px;">
                    📋 {phase.n_actions} actions</div>
                  <div style="font-family:{_FONT};font-size:11px;color:{rcolor};font-weight:600;">
                    Risk: {phase.risk_level}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Action plan
    st.markdown(
        "<h3 style='font-family:\"Fraunces\",Georgia,serif;font-size:16px;"
        "color:#003366;font-weight:300;margin:20px 0 8px;'>Action Plan</h3>",
        unsafe_allow_html=True,
    )

    action_df = plan.action_df
    if not action_df.empty:
        st.dataframe(action_df, use_container_width=True, hide_index=True)

    # Risk register
    if plan.risks:
        st.markdown(
            "<h3 style='font-family:\"Fraunces\",Georgia,serif;font-size:16px;"
            "color:#003366;font-weight:300;margin:20px 0 8px;'>Risk Register</h3>",
            unsafe_allow_html=True,
        )
        for risk in plan.risks:
            impact_color = {"High": _C["purple"], "Medium": _C["orange"], "Low": _C["gold"]}.get(
                risk.impact, _C["mid"]
            )
            st.markdown(
                f"""
                <div style="background:#fff;border-radius:8px;padding:14px;
                            margin-bottom:8px;box-shadow:0 1px 4px rgba(0,51,102,0.08);
                            border-left:3px solid {impact_color};">
                  <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
                    <span style="font-family:{_FONT};font-size:12px;font-weight:600;
                                 color:#003366;">{risk.category.replace('_',' ').title()}</span>
                    <span style="background:{impact_color}20;color:{impact_color};
                                 padding:1px 6px;border-radius:3px;font-size:10px;
                                 font-weight:600;">Impact: {risk.impact}</span>
                    <span style="background:#E0EAF420;color:#6B7280;
                                 padding:1px 6px;border-radius:3px;font-size:10px;">
                                 Prob: {risk.probability}</span>
                  </div>
                  <div style="font-family:{_FONT};font-size:12px;color:#374151;
                              margin-bottom:6px;">{risk.description}</div>
                  <div style="font-family:{_FONT};font-size:11px;color:#003366;
                              background:#E8F0FA;border-radius:4px;padding:5px 8px;">
                    💡 {risk.mitigation}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _render_gantt(plan) -> None:
    """Simple horizontal bar Gantt chart for the 3 phases."""
    fig = go.Figure()

    for i, phase in enumerate(plan.phases):
        color = _PHASE_COLORS[i % len(_PHASE_COLORS)]
        fig.add_trace(go.Bar(
            x=[phase.months_end - phase.months_start],
            y=[phase.name],
            base=[phase.months_start],
            orientation="h",
            marker_color=color,
            marker_opacity=0.85,
            text=f"${phase.cost_estimate:,.0f}",
            textposition="inside",
            insidetextanchor="middle",
            hovertemplate=(
                f"<b>{phase.name}</b><br>"
                f"Months {phase.months_start}–{phase.months_end}<br>"
                f"Cost: ${phase.cost_estimate:,.0f}<br>"
                f"Actions: {phase.n_actions}<br>"
                f"Risk: {phase.risk_level}<extra></extra>"
            ),
        ))

    fig.update_layout(
        height=180,
        barmode="stack",
        margin=dict(l=0, r=20, t=8, b=8),
        paper_bgcolor=_C["light"],
        plot_bgcolor="white",
        font=dict(family=_FONT, size=11),
        xaxis=dict(title="Month", dtick=3, showgrid=True, gridcolor="#E0EAF4"),
        yaxis=dict(autorange="reversed"),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)


# ===========================================================================
# TAB 4 — Strategy Comparison
# ===========================================================================

def _render_strategy_comparison_tab(data: DashboardData) -> None:
    from strategic_planner.strategy_comparator import (
        PRESET_STRATEGIES, compare_strategies
    )

    st.markdown(
        f"<p style='font-family:{_FONT};font-size:13px;color:#6B7280;margin:12px 0 20px;'>"
        "Compare four workforce strategy archetypes on cost, talent retention, "
        "innovation capacity, operational resilience, and speed to execute. "
        "Adjust priorities below to reflect your organisation's context.</p>",
        unsafe_allow_html=True,
    )

    # Priority sliders
    st.markdown(
        "<h3 style='font-family:\"Fraunces\",Georgia,serif;font-size:16px;"
        "color:#003366;font-weight:300;margin-bottom:8px;'>"
        "Organisational Priorities (0 = low, 10 = high)</h3>",
        unsafe_allow_html=True,
    )
    col1, col2, col3, col4, col5 = st.columns(5)
    w_cost       = col1.slider("Cost",       0, 10, 6)
    w_retention  = col2.slider("Retention",  0, 10, 5)
    w_innovation = col3.slider("Innovation", 0, 10, 4)
    w_resilience = col4.slider("Resilience", 0, 10, 3)
    w_speed      = col5.slider("Speed",      0, 10, 2)

    priorities = {
        "cost":       float(w_cost),
        "retention":  float(w_retention),
        "innovation": float(w_innovation),
        "resilience": float(w_resilience),
        "speed":      float(w_speed),
    }

    with st.spinner("Scoring strategies…"):
        try:
            result = compare_strategies(
                strategies=PRESET_STRATEGIES,
                current_annual_spend=data.total_spend,
                n_employees=data.total_headcount,
                avg_impact_score=data.avg_impact_score,
                n_nexus=data.n_nexus_employees,
                attrition_rate=0.12,
                org_priorities=priorities,
            )
            _render_strategy_result(result)
        except Exception as exc:
            st.error(f"Strategy comparison failed: {exc}")


def _render_strategy_result(result) -> None:
    # Recommendation banner
    winner = result.winner
    st.markdown(
        f"""
        <div style="background:{winner.color}18;border:1px solid {winner.color}40;
                    border-radius:8px;padding:16px 20px;margin-bottom:20px;">
          <div style="font-family:{_FONT};font-size:11px;font-weight:600;
                      color:{winner.color};letter-spacing:2px;
                      text-transform:uppercase;margin-bottom:4px;">
            Recommended Strategy</div>
          <div style="font-family:'Fraunces',Georgia,serif;font-size:18px;
                      color:#003366;font-weight:300;margin-bottom:6px;">
            {winner.strategy_name}</div>
          <div style="font-family:{_FONT};font-size:12px;color:#374151;line-height:1.6;">
            {result.recommendation_rationale}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Radar chart + score cards
    col_radar, col_cards = st.columns([3, 2], gap="large")

    with col_radar:
        st.markdown(
            "<h3 style='font-family:\"Fraunces\",Georgia,serif;font-size:16px;"
            "color:#003366;font-weight:300;margin-bottom:8px;'>"
            "Multi-Criteria Radar</h3>",
            unsafe_allow_html=True,
        )
        _render_radar_chart(result)

    with col_cards:
        st.markdown(
            "<h3 style='font-family:\"Fraunces\",Georgia,serif;font-size:16px;"
            "color:#003366;font-weight:300;margin-bottom:8px;'>"
            "Strategy Rankings</h3>",
            unsafe_allow_html=True,
        )
        for s in result.scores:
            _render_strategy_card(s)

    # Comparison table
    st.markdown(
        "<h3 style='font-family:\"Fraunces\",Georgia,serif;font-size:16px;"
        "color:#003366;font-weight:300;margin:20px 0 8px;'>"
        "Detailed Comparison</h3>",
        unsafe_allow_html=True,
    )
    df = result.comparison_df.drop(columns=["Color"], errors="ignore")
    df["2-Year Cost ($)"] = df["2-Year Cost ($)"].map(lambda x: f"${x:,.0f}")
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Export
    export_md = _build_strategy_export(result)
    with st.expander("Export strategic plan (.md)", expanded=False):
        st.markdown(export_md)
        st.download_button(
            "Download Strategic Plan",
            data=export_md.encode(),
            file_name=f"strategic_plan_{result.generated_at[:10]}.md",
            mime="text/markdown",
        )


def _render_radar_chart(result) -> None:
    dims = ["Cost", "Retention", "Innovation", "Resilience", "Speed"]
    attr_map = {
        "Cost": "cost_score",
        "Retention": "retention_score",
        "Innovation": "innovation_score",
        "Resilience": "resilience_score",
        "Speed": "speed_score",
    }

    fig = go.Figure()
    for s in result.scores:
        values = [getattr(s, attr_map[d]) for d in dims] + [getattr(s, attr_map[dims[0]])]
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=dims + [dims[0]],
            name=s.strategy_name,
            line=dict(color=s.color, width=2),
            fill="toself",
            fillcolor=s.color,
            opacity=0.15,
            hovertemplate=f"<b>{s.strategy_name}</b><br>%{{theta}}: %{{r:.0f}}<extra></extra>",
        ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(size=9)),
            angularaxis=dict(tickfont=dict(family=_FONT, size=11)),
        ),
        showlegend=True,
        height=360,
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor=_C["light"],
        legend=dict(orientation="h", y=-0.15, font=dict(family=_FONT, size=10)),
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_strategy_card(s) -> None:
    rank_icon = ["🥇", "🥈", "🥉", "4️⃣"][min(s.rank - 1, 3)]
    st.markdown(
        f"""
        <div style="background:#fff;border-radius:8px;padding:12px 14px;
                    margin-bottom:8px;box-shadow:0 1px 4px rgba(0,51,102,0.08);
                    border-left:3px solid {s.color};">
          <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
            <span style="font-size:14px;">{rank_icon}</span>
            <span style="font-family:{_FONT};font-size:12px;font-weight:600;
                         color:#003366;">{s.strategy_name}</span>
            <span style="margin-left:auto;font-family:'Fraunces',Georgia,serif;
                         font-size:18px;color:{s.color};font-weight:300;">
                         {s.overall_score:.0f}</span>
          </div>
          <div style="font-family:{_FONT};font-size:11px;color:#6B7280;margin-bottom:4px;">
            2yr cost: ${s.two_year_cost:,.0f} · {s.months_to_execute}mo to execute</div>
          <div style="font-family:{_FONT};font-size:10px;color:#374151;">
            {s.recommendation}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _build_strategy_export(result) -> str:
    lines = [
        f"# Strategic Workforce Plan",
        f"Generated: {result.generated_at}",
        "",
        f"## Recommended Strategy: {result.winner.strategy_name}",
        "",
        result.recommendation_rationale,
        "",
        "## Strategy Comparison",
        "",
    ]
    for s in result.scores:
        lines += [
            f"### {s.rank}. {s.strategy_name}",
            f"- **Overall Score**: {s.overall_score:.0f}/100",
            f"- **2-Year Cost**: ${s.two_year_cost:,.0f}",
            f"- **Retention Rate**: {s.retention_rate_projection:.0%}",
            f"- **Months to Execute**: {s.months_to_execute}",
            f"- **Assessment**: {s.recommendation}",
        ]
        if s.strengths:
            lines.append(f"- **Strengths**: {', '.join(s.strengths)}")
        if s.weaknesses:
            lines.append(f"- **Considerations**: {', '.join(s.weaknesses)}")
        lines.append("")

    lines += [
        "## Organisational Priority Weights",
        "",
    ]
    for k, v in result.org_priorities.items():
        lines.append(f"- **{k.title()}**: {v:.0%}")

    lines += ["", "---", "*Generated by EIBO Strategic Planning Module*"]
    return "\n".join(lines)


# ===========================================================================
# Shared helpers
# ===========================================================================

def _kpi(col, label: str, value: str, sub: str, color: str) -> None:
    with col:
        st.markdown(
            f"""
            <div style="background:#fff;border-radius:8px;padding:16px;
                        box-shadow:0 1px 4px rgba(0,51,102,0.08);
                        border-top:3px solid {color};">
              <div style="font-family:{_FONT};font-size:10px;color:#6B7280;
                          font-weight:600;text-transform:uppercase;
                          letter-spacing:1px;margin-bottom:4px;">{label}</div>
              <div style="font-family:'Fraunces',Georgia,serif;font-size:22px;
                          font-weight:300;color:{color};">{value}</div>
              <div style="font-family:{_FONT};font-size:10px;color:#9CA3AF;">{sub}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
