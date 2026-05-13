"""Predictive Analytics & Attrition Risk — Sprint 5.

Three-tab layout:
  Tab 1 — Attrition Risk   : heatmap, top at-risk table, retention recommendations
  Tab 2 — Budget Forecast  : Prophet fan chart, Monte Carlo stress test
  Tab 3 — Early Warning    : traffic-light dashboard, alert list, risk digest
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ui.data_loader import DashboardData, load_dashboard_data

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Brand palette (BRAND.md)
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

_RISK_COLORS = {
    "Low":      "#27B97C",
    "Moderate": "#C8982A",
    "High":     "#F07020",
    "Critical": "#7C4DBD",
}

_SEVERITY_COLORS = {
    "critical": "#7C4DBD",
    "high":     "#F07020",
    "moderate": "#C8982A",
    "low":      "#27B97C",
    "ok":       "#6B7280",
}

_SEVERITY_ICONS = {
    "critical": "🔴",
    "high":     "🟠",
    "moderate": "🟡",
    "low":      "🟢",
    "ok":       "⚪",
}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def render() -> None:
    demo_mode: bool = st.session_state.get("demo_mode", True)
    scenario_id: str = st.session_state.get("demo_scenario", "A")
    size: str = st.session_state.get("demo_size", "medium")

    with st.spinner("Loading predictive analytics…"):
        try:
            data = load_dashboard_data(demo_mode, scenario_id, size)
        except (NotImplementedError, RuntimeError) as exc:
            st.error(str(exc))
            return

    _render_hero(data)

    tab_attrition, tab_forecast, tab_warning = st.tabs([
        "🎯  Attrition Risk",
        "📈  Budget Forecast",
        "⚡  Early Warning",
    ])

    with tab_attrition:
        _render_attrition_tab(data)

    with tab_forecast:
        _render_forecast_tab(data)

    with tab_warning:
        _render_warning_tab(data)


# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------

def _render_hero(data: DashboardData) -> None:
    st.markdown(
        f"""
        <div style="background:#003366; background-image:
          linear-gradient(rgba(255,255,255,.025) 1px, transparent 1px),
          linear-gradient(90deg, rgba(255,255,255,.025) 1px, transparent 1px);
          background-size:48px 48px; padding:32px 40px 24px;">
          <div style="font-family:'Fraunces',Georgia,serif; font-size:9px;
                      font-weight:300; letter-spacing:4px; text-transform:uppercase;
                      color:rgba(255,255,255,0.4); margin-bottom:6px;">
            Predictive Analytics
          </div>
          <h1 style="font-family:'Fraunces',Georgia,serif; font-size:28px;
                     font-weight:300; color:#fff; margin:0 0 4px;">
            Workforce Intelligence &amp;
            <em style="color:{_C['gold_lt']}; font-style:italic;">Forecasting</em>
          </h1>
          <p style="font-family:{_FONT}; font-size:13px;
                    color:rgba(255,255,255,0.55); margin:0;">
            {data.org_name} · {data.total_headcount:,} employees · Scenario {data.scenario_id}
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ===========================================================================
# TAB 1 — Attrition Risk
# ===========================================================================

@st.cache_data(show_spinner=False, ttl=1800)
def _compute_attrition(_data_key: str, employee_df_json: str, perf_json: str,
                       centrality_json: str, impact_json: str) -> pd.DataFrame:
    """Cache-friendly wrapper: serialises DataFrames to JSON keys."""
    from models.attrition_predictor import compute_attrition_risk

    emp = pd.read_json(employee_df_json, orient="split")
    perf = pd.read_json(perf_json, orient="split") if perf_json else pd.DataFrame()
    cent = pd.read_json(centrality_json, orient="split") if centrality_json else pd.DataFrame()
    imp = pd.read_json(impact_json, orient="split") if impact_json else pd.DataFrame()

    result = compute_attrition_risk(emp, perf, cent, imp)
    return result.scores


def _render_attrition_tab(data: DashboardData) -> None:
    st.markdown(
        "<p style='font-family:\"Plus Jakarta Sans\",sans-serif; font-size:13px; "
        "color:#6B7280; margin:12px 0 20px;'>"
        "Attrition risk scores are computed from salary competitiveness, performance "
        "trends, tenure patterns, collaboration network position, and impact score. "
        "Model: <b>heuristic component scoring</b> with additive attribution.</p>",
        unsafe_allow_html=True,
    )

    cache_key = f"{data.scenario_id}_{data.org_size}"
    with st.spinner("Computing attrition risk scores…"):
        try:
            scores_df = _compute_attrition(
                cache_key,
                data.employees.to_json(orient="split"),
                data.performance.to_json(orient="split") if not data.performance.empty else "",
                data.centrality.to_json(orient="split") if not data.centrality.empty else "",
                data.impact_scores.to_json(orient="split") if not data.impact_scores.empty else "",
            )
        except Exception as exc:
            st.error(f"Could not compute attrition risk: {exc}")
            return

    # Merge with employee name/dept for display
    display = scores_df.merge(
        data.employees[["employee_id", "full_name", "department", "role_title",
                        "annual_salary"]].rename(columns={"annual_salary": "salary"}),
        on="employee_id",
        how="left",
    )

    # -----------------------------------------------------------------------
    # KPI row
    # -----------------------------------------------------------------------
    n_critical = (display["risk_category"] == "Critical").sum()
    n_high = (display["risk_category"] == "High").sum()
    n_moderate = (display["risk_category"] == "Moderate").sum()
    n_low = (display["risk_category"] == "Low").sum()
    avg_risk = display["attrition_risk"].mean()

    cols = st.columns(5)
    _metric_card(cols[0], "Avg Risk Score", f"{avg_risk:.0f}", "/100", _C["gold"])
    _metric_card(cols[1], "Critical Risk", str(n_critical), "employees", _C["purple"])
    _metric_card(cols[2], "High Risk", str(n_high), "employees", _C["orange"])
    _metric_card(cols[3], "Moderate Risk", str(n_moderate), "employees", _C["gold"])
    _metric_card(cols[4], "Low Risk", str(n_low), "employees", _C["green"])

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # Heatmap by department × risk category
    # -----------------------------------------------------------------------
    col_heat, col_bar = st.columns([3, 2], gap="large")

    with col_heat:
        st.markdown(
            "<h3 style='font-family:\"Fraunces\",Georgia,serif; font-size:16px; "
            "color:#003366; font-weight:300; margin-bottom:8px;'>"
            "Risk Distribution by Department</h3>",
            unsafe_allow_html=True,
        )
        _render_risk_heatmap(display)

    with col_bar:
        st.markdown(
            "<h3 style='font-family:\"Fraunces\",Georgia,serif; font-size:16px; "
            "color:#003366; font-weight:300; margin-bottom:8px;'>"
            "Risk Category Breakdown</h3>",
            unsafe_allow_html=True,
        )
        _render_risk_donut(n_critical, n_high, n_moderate, n_low)

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # Top at-risk employees
    # -----------------------------------------------------------------------
    st.markdown(
        "<h3 style='font-family:\"Fraunces\",Georgia,serif; font-size:16px; "
        "color:#003366; font-weight:300; margin:16px 0 8px;'>"
        "Employees Requiring Retention Attention</h3>",
        unsafe_allow_html=True,
    )
    _render_top_atrisk_table(display, data)

    # -----------------------------------------------------------------------
    # Driver attribution bar
    # -----------------------------------------------------------------------
    st.markdown(
        "<h3 style='font-family:\"Fraunces\",Georgia,serif; font-size:16px; "
        "color:#003366; font-weight:300; margin:16px 0 8px;'>"
        "Risk Driver Attribution (Org Average)</h3>",
        unsafe_allow_html=True,
    )
    _render_driver_attribution(scores_df)

    # -----------------------------------------------------------------------
    # Recommendations
    # -----------------------------------------------------------------------
    _render_retention_recommendations(display)


def _render_risk_heatmap(display: pd.DataFrame) -> None:
    if "department" not in display.columns:
        st.info("No department data available.")
        return

    cats = ["Low", "Moderate", "High", "Critical"]
    depts = sorted(display["department"].dropna().unique())

    z = []
    for dept in depts:
        row_df = display[display["department"] == dept]
        row = [int((row_df["risk_category"] == c).sum()) for c in cats]
        z.append(row)

    fig = go.Figure(go.Heatmap(
        z=z,
        x=cats,
        y=depts,
        colorscale=[
            [0, "#E8F5EF"],
            [0.33, "#C8982A"],
            [0.66, "#F07020"],
            [1.0, "#7C4DBD"],
        ],
        showscale=False,
        text=[[str(v) for v in row] for row in z],
        texttemplate="%{text}",
        hovertemplate="Dept: %{y}<br>Risk: %{x}<br>Count: %{z}<extra></extra>",
    ))
    fig.update_layout(
        height=max(220, len(depts) * 32 + 80),
        margin=dict(l=0, r=0, t=8, b=8),
        paper_bgcolor=_C["light"],
        plot_bgcolor=_C["light"],
        font=dict(family=_FONT, size=11),
        xaxis=dict(side="top"),
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_risk_donut(n_crit: int, n_high: int, n_mod: int, n_low: int) -> None:
    labels = ["Critical", "High", "Moderate", "Low"]
    values = [n_crit, n_high, n_mod, n_low]
    colors = [_C["purple"], _C["orange"], _C["gold"], _C["green"]]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.60,
        marker_colors=colors,
        textinfo="label+value",
        hovertemplate="%{label}: %{value} employees<extra></extra>",
        textfont=dict(family=_FONT, size=11),
    ))
    fig.update_layout(
        height=260,
        margin=dict(l=0, r=0, t=8, b=8),
        paper_bgcolor=_C["light"],
        showlegend=False,
        annotations=[dict(
            text=f"{n_crit + n_high}<br><span style='font-size:10px'>need<br>attention</span>",
            x=0.5, y=0.5, showarrow=False,
            font=dict(family=_FONT, size=14, color=_C["dark"]),
        )],
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_top_atrisk_table(display: pd.DataFrame, data: DashboardData) -> None:
    top = display[display["risk_category"].isin(["Critical", "High"])].copy()
    top = top.sort_values("attrition_risk", ascending=False).head(15)

    if top.empty:
        st.success("No employees in High or Critical attrition risk categories.")
        return

    def _badge(cat: str) -> str:
        color = _RISK_COLORS.get(cat, "#6B7280")
        return f'<span style="background:{color}20;color:{color};padding:2px 8px;border-radius:4px;font-size:10px;font-weight:600;">{cat}</span>'

    def _nexus_badge(eid: str) -> str:
        if str(eid) in data.nexus_ids:
            return '<span style="color:#C8982A;font-size:10px;">★ Nexus</span>'
        return ""

    def _driver_pill(driver: str) -> str:
        d = str(driver).replace("_driver", "").replace("_", " ").title()
        return f'<span style="background:#E0EAF4;color:#003366;padding:1px 6px;border-radius:3px;font-size:9px;">{d}</span>'

    rows_html = ""
    for _, row in top.iterrows():
        driver = str(row.get("top_driver", ""))
        rows_html += (
            f"<tr style='border-bottom:1px solid #E0EAF4;'>"
            f"<td style='padding:8px 12px;'><b>{row.get('full_name', row['employee_id'])}</b> "
            f"{_nexus_badge(row['employee_id'])}</td>"
            f"<td style='padding:8px 12px;color:#6B7280;'>{row.get('role_title','')}</td>"
            f"<td style='padding:8px 12px;color:#6B7280;'>{row.get('department','')}</td>"
            f"<td style='padding:8px 12px;text-align:center;'>"
            f"<b style='color:#003366;'>{row['attrition_risk']:.0f}</b></td>"
            f"<td style='padding:8px 12px;'>{_badge(row['risk_category'])}</td>"
            f"<td style='padding:8px 12px;'>{_driver_pill(driver) if driver else ''}</td>"
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
                <th style="padding:8px 12px;text-align:left;">Employee</th>
                <th style="padding:8px 12px;text-align:left;">Role</th>
                <th style="padding:8px 12px;text-align:left;">Department</th>
                <th style="padding:8px 12px;text-align:center;">Risk Score</th>
                <th style="padding:8px 12px;text-align:left;">Category</th>
                <th style="padding:8px 12px;text-align:left;">Top Driver</th>
              </tr>
            </thead>
            <tbody>{rows_html}</tbody>
          </table>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_driver_attribution(scores_df: pd.DataFrame) -> None:
    driver_cols = [c for c in scores_df.columns if c.endswith("_driver")]
    if not driver_cols:
        return

    avg_drivers = scores_df[driver_cols].mean()
    labels = [c.replace("_driver", "").replace("_", " ").title() for c in driver_cols]
    values = avg_drivers.values

    fig = go.Figure(go.Bar(
        x=values,
        y=labels,
        orientation="h",
        marker_color=[_C["primary"], _C["orange"], _C["gold"], _C["purple"], _C["green"]][:len(labels)],
        text=[f"{v:.1f}" for v in values],
        textposition="outside",
        hovertemplate="%{y}: %{x:.1f}<extra></extra>",
    ))
    fig.update_layout(
        height=220,
        margin=dict(l=0, r=60, t=8, b=8),
        paper_bgcolor=_C["light"],
        plot_bgcolor="white",
        font=dict(family=_FONT, size=11),
        xaxis=dict(title="Average contribution (0–100)", showgrid=True, gridcolor="#E0EAF4"),
        yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_retention_recommendations(display: pd.DataFrame) -> None:
    st.markdown(
        "<h3 style='font-family:\"Fraunces\",Georgia,serif; font-size:16px; "
        "color:#003366; font-weight:300; margin:16px 0 8px;'>"
        "Retention Opportunity Recommendations</h3>",
        unsafe_allow_html=True,
    )

    recommendations = [
        ("salary_driver",
         "💰 Compensation Review",
         "Employees flagged for salary risk are likely below market rate. "
         "A targeted compensation review for High/Critical risk employees may "
         "significantly reduce voluntary departures."),
        ("kpi_trend_driver",
         "📊 Performance Engagement",
         "Declining KPI trends are a leading indicator of disengagement. "
         "Schedule development conversations and review role alignment for "
         "at-risk employees with negative performance trajectories."),
        ("network_driver",
         "🤝 Social Integration",
         "Isolated employees (low collaboration network position) are at higher "
         "attrition risk. Consider mentoring programs and cross-team project "
         "assignments to increase engagement."),
        ("tenure_driver",
         "⏱ Tenure Milestones",
         "Employees in their 1st–2nd year and 5th–6th year show elevated risk. "
         "These transition points benefit from structured check-ins and "
         "career development conversations."),
    ]

    cols = st.columns(2)
    for i, (driver, title, body) in enumerate(recommendations):
        with cols[i % 2]:
            st.markdown(
                f"""
                <div style="background:#fff;border-radius:8px;padding:16px;
                            margin-bottom:12px;box-shadow:0 1px 4px rgba(0,51,102,0.08);
                            border-left:3px solid {_C['primary']};">
                  <div style="font-family:{_FONT};font-size:13px;font-weight:600;
                              color:#003366;margin-bottom:6px;">{title}</div>
                  <div style="font-family:{_FONT};font-size:12px;color:#374151;
                              line-height:1.6;">{body}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ===========================================================================
# TAB 2 — Budget Forecast
# ===========================================================================

@st.cache_data(show_spinner=False, ttl=3600)
def _compute_forecast(_key: str, emp_json: str, annual_budget: float):
    from forecasting.budget_forecaster import forecast_budget
    emp = pd.read_json(emp_json, orient="split")
    return forecast_budget(emp, annual_budget=annual_budget)


@st.cache_data(show_spinner=False, ttl=3600)
def _compute_monte_carlo(_key: str, emp_json: str, annual_budget: float,
                         attrition_json: str | None):
    from forecasting.monte_carlo import run_monte_carlo
    emp = pd.read_json(emp_json, orient="split")
    atr = pd.read_json(attrition_json, orient="split") if attrition_json else None
    return run_monte_carlo(emp, annual_budget=annual_budget, attrition_result=atr)


def _render_forecast_tab(data: DashboardData) -> None:
    annual_budget = data.total_budget or data.total_spend * 1.05

    st.markdown(
        f"""
        <p style='font-family:{_FONT};font-size:13px;color:#6B7280;margin:12px 0 20px;'>
        12-month spend and headcount forecast using historical pattern synthesis.
        Confidence bands: <b>80%</b> (darker) and <b>95%</b> (lighter).
        Annual budget baseline: <b>${annual_budget:,.0f}</b>.
        </p>
        """,
        unsafe_allow_html=True,
    )

    cache_key = f"{data.scenario_id}_{data.org_size}"
    col_fc, col_mc = st.columns([3, 2], gap="large")

    with col_fc:
        st.markdown(
            "<h3 style='font-family:\"Fraunces\",Georgia,serif; font-size:16px; "
            "color:#003366; font-weight:300; margin-bottom:8px;'>"
            "Projected Spend — 12 Month Outlook</h3>",
            unsafe_allow_html=True,
        )
        with st.spinner("Running forecast…"):
            try:
                fc_result = _compute_forecast(
                    cache_key,
                    data.employees.to_json(orient="split"),
                    annual_budget,
                )
                _render_forecast_fan_chart(fc_result, annual_budget)
            except Exception as exc:
                st.error(f"Forecast failed: {exc}")

    with col_mc:
        st.markdown(
            "<h3 style='font-family:\"Fraunces\",Georgia,serif; font-size:16px; "
            "color:#003366; font-weight:300; margin-bottom:8px;'>"
            "Monte Carlo Stress Test</h3>",
            unsafe_allow_html=True,
        )
        with st.spinner("Running 5,000 simulations…"):
            try:
                mc_result = _compute_monte_carlo(
                    cache_key,
                    data.employees.to_json(orient="split"),
                    annual_budget,
                    None,
                )
                _render_monte_carlo_summary(mc_result)
            except Exception as exc:
                st.error(f"Monte Carlo failed: {exc}")

    # Department breakdown
    try:
        fc_result2 = _compute_forecast(
            cache_key, data.employees.to_json(orient="split"), annual_budget
        )
        if fc_result2.by_department:
            st.markdown(
                "<h3 style='font-family:\"Fraunces\",Georgia,serif; font-size:16px; "
                "color:#003366; font-weight:300; margin:20px 0 8px;'>"
                "Department Spend Trajectories</h3>",
                unsafe_allow_html=True,
            )
            _render_dept_forecast(fc_result2)
    except Exception:
        pass


def _render_forecast_fan_chart(fc_result, annual_budget: float) -> None:
    from forecasting.budget_forecaster import BudgetForecastResult
    result: BudgetForecastResult = fc_result

    hist = result.total_spend.history
    fc = result.total_spend.forecast

    fig = go.Figure()

    # History line
    if not hist.empty:
        fig.add_trace(go.Scatter(
            x=hist["ds"], y=hist["y"],
            mode="lines",
            name="Historical",
            line=dict(color=_C["primary"], width=2),
            hovertemplate="<b>%{x|%b %Y}</b><br>Actual: $%{y:,.0f}<extra></extra>",
        ))

    # 95% CI band
    fig.add_trace(go.Scatter(
        x=pd.concat([fc["ds"], fc["ds"].iloc[::-1]]),
        y=pd.concat([fc["yhat_upper_95"], fc["yhat_lower_95"].iloc[::-1]]),
        fill="toself",
        fillcolor="rgba(0,51,102,0.08)",
        line=dict(color="rgba(0,0,0,0)"),
        name="95% CI",
        hoverinfo="skip",
    ))

    # 80% CI band
    fig.add_trace(go.Scatter(
        x=pd.concat([fc["ds"], fc["ds"].iloc[::-1]]),
        y=pd.concat([fc["yhat_upper_80"], fc["yhat_lower_80"].iloc[::-1]]),
        fill="toself",
        fillcolor="rgba(0,51,102,0.14)",
        line=dict(color="rgba(0,0,0,0)"),
        name="80% CI",
        hoverinfo="skip",
    ))

    # Forecast median
    fig.add_trace(go.Scatter(
        x=fc["ds"], y=fc["yhat"],
        mode="lines",
        name="Forecast (median)",
        line=dict(color=_C["primary"], width=2, dash="dash"),
        hovertemplate="<b>%{x|%b %Y}</b><br>Forecast: $%{y:,.0f}<extra></extra>",
    ))

    # Monthly budget line
    monthly_budget = annual_budget / 12
    fig.add_hline(
        y=monthly_budget,
        line_dash="dot",
        line_color=_C["orange"],
        annotation_text=f"Monthly Budget ${monthly_budget:,.0f}",
        annotation_position="right",
        annotation_font=dict(family=_FONT, size=10, color=_C["orange"]),
    )

    fig.update_layout(
        height=340,
        margin=dict(l=0, r=80, t=8, b=8),
        paper_bgcolor=_C["light"],
        plot_bgcolor="white",
        font=dict(family=_FONT, size=11),
        legend=dict(orientation="h", y=1.02, x=0, font_size=10),
        xaxis=dict(title="Month", showgrid=True, gridcolor="#E0EAF4"),
        yaxis=dict(title="Monthly Spend ($)", showgrid=True, gridcolor="#E0EAF4",
                   tickformat="$,.0f"),
    )
    model_label = result.total_spend.model.title()
    mape = result.total_spend.mape
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"Model: {model_label} · In-sample MAPE: {mape:.1f}%")


def _render_monte_carlo_summary(mc_result) -> None:
    from forecasting.monte_carlo import MonteCarloResult
    r: MonteCarloResult = mc_result

    # Fan chart for monthly spend distribution
    fig = go.Figure()

    fc = r.fan_chart

    # P90–P10 band
    fig.add_trace(go.Scatter(
        x=pd.concat([fc["ds"], fc["ds"].iloc[::-1]]),
        y=pd.concat([fc["p90"], fc["p10"].iloc[::-1]]),
        fill="toself",
        fillcolor="rgba(0,51,102,0.10)",
        line=dict(color="rgba(0,0,0,0)"),
        name="P10–P90",
        hoverinfo="skip",
    ))

    fig.add_trace(go.Scatter(
        x=fc["ds"], y=fc["p50"],
        mode="lines",
        name="Median (P50)",
        line=dict(color=_C["primary"], width=2),
        hovertemplate="<b>%{x|%b %Y}</b><br>P50: $%{y:,.0f}<extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=fc["ds"], y=fc["p90"],
        mode="lines",
        name="P90 (stress)",
        line=dict(color=_C["orange"], width=1, dash="dot"),
    ))

    fig.add_trace(go.Scatter(
        x=fc["ds"], y=fc["p10"],
        mode="lines",
        name="P10 (favourable)",
        line=dict(color=_C["green"], width=1, dash="dot"),
    ))

    fig.add_hline(
        y=r.annual_budget / 12,
        line_dash="dash",
        line_color=_C["orange"],
        annotation_text="Budget",
        annotation_font=dict(size=9),
    )

    fig.update_layout(
        height=240,
        margin=dict(l=0, r=60, t=8, b=8),
        paper_bgcolor=_C["light"],
        plot_bgcolor="white",
        font=dict(family=_FONT, size=10),
        legend=dict(orientation="h", y=1.02, x=0, font_size=9),
        xaxis=dict(showgrid=True, gridcolor="#E0EAF4"),
        yaxis=dict(tickformat="$,.0f", showgrid=True, gridcolor="#E0EAF4"),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Summary stats
    overspend_pct = r.prob_overspend_any_month * 100
    sev_color = _C["orange"] if overspend_pct > 30 else _C["green"]

    st.markdown(
        f"""
        <div style="background:#fff;border-radius:8px;padding:14px 16px;
                    box-shadow:0 1px 4px rgba(0,51,102,0.08);">
          <div style="font-family:{_FONT};font-size:11px;color:#6B7280;
                      margin-bottom:8px;">Final Month — {r.n_simulations:,} simulations</div>
          <div style="display:flex;gap:16px;flex-wrap:wrap;">
            <div><div style="font-size:10px;color:#6B7280;">P10</div>
                 <div style="font-size:14px;font-weight:600;color:#27B97C;">
                 ${r.final_month_p10:,.0f}</div></div>
            <div><div style="font-size:10px;color:#6B7280;">Median</div>
                 <div style="font-size:14px;font-weight:600;color:#003366;">
                 ${r.final_month_p50:,.0f}</div></div>
            <div><div style="font-size:10px;color:#6B7280;">P90</div>
                 <div style="font-size:14px;font-weight:600;color:#F07020;">
                 ${r.final_month_p90:,.0f}</div></div>
          </div>
          <div style="margin-top:10px;font-family:{_FONT};font-size:11px;">
            Probability of overspend in any month:
            <b style="color:{sev_color};">{overspend_pct:.1f}%</b>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if r.notes:
        for note in r.notes:
            st.caption(f"ℹ {note}")


def _render_dept_forecast(fc_result) -> None:
    if not fc_result.by_department:
        return

    colors = [_C["primary"], _C["green"], _C["purple"], _C["orange"], _C["gold"]]
    fig = go.Figure()

    for i, series in enumerate(fc_result.by_department[:8]):
        color = colors[i % len(colors)]
        fig.add_trace(go.Scatter(
            x=series.forecast["ds"],
            y=series.forecast["yhat"],
            mode="lines",
            name=series.label,
            line=dict(color=color, width=1.5),
            hovertemplate=f"<b>{series.label}</b><br>%{{x|%b %Y}}: $%{{y:,.0f}}<extra></extra>",
        ))

    fig.update_layout(
        height=260,
        margin=dict(l=0, r=20, t=8, b=8),
        paper_bgcolor=_C["light"],
        plot_bgcolor="white",
        font=dict(family=_FONT, size=11),
        legend=dict(orientation="h", y=1.02, x=0, font_size=10),
        xaxis=dict(showgrid=True, gridcolor="#E0EAF4"),
        yaxis=dict(tickformat="$,.0f", showgrid=True, gridcolor="#E0EAF4"),
    )
    st.plotly_chart(fig, use_container_width=True)


# ===========================================================================
# TAB 3 — Early Warning
# ===========================================================================

def _render_warning_tab(data: DashboardData) -> None:
    st.markdown(
        f"<p style='font-family:{_FONT};font-size:13px;color:#6B7280;margin:12px 0 20px;'>"
        "Six automated risk triggers evaluate attrition concentration, nexus employee "
        "exposure, team fragility, budget pace, impact trends, and critical skill coverage.</p>",
        unsafe_allow_html=True,
    )

    annual_budget = data.total_budget or data.total_spend * 1.05
    budget_consumed = data.total_spend * 0.42   # ~5 months YTD proxy in demo

    with st.spinner("Evaluating risk triggers…"):
        try:
            attrition_scores = _compute_attrition(
                f"{data.scenario_id}_{data.org_size}",
                data.employees.to_json(orient="split"),
                data.performance.to_json(orient="split") if not data.performance.empty else "",
                data.centrality.to_json(orient="split") if not data.centrality.empty else "",
                data.impact_scores.to_json(orient="split") if not data.impact_scores.empty else "",
            )
        except Exception:
            attrition_scores = pd.DataFrame()

        from models.early_warning import evaluate_early_warnings
        ew_result = evaluate_early_warnings(
            employee_df=data.employees,
            attrition_scores=attrition_scores if not attrition_scores.empty else None,
            team_fragility=data.team_fragility,
            nexus_ids=data.nexus_ids,
            impact_scores=data.impact_scores,
            budget_consumed=budget_consumed,
            annual_budget=annual_budget,
        )

    # -----------------------------------------------------------------------
    # Overall severity banner
    # -----------------------------------------------------------------------
    sev = ew_result.overall_severity.value
    sev_color = _SEVERITY_COLORS.get(sev, _C["mid"])
    sev_icon = _SEVERITY_ICONS.get(sev, "⚪")
    n_alerts = len([a for a in ew_result.alerts if a.severity.value != "ok"])

    st.markdown(
        f"""
        <div style="background:{sev_color}18;border:1px solid {sev_color}40;
                    border-radius:8px;padding:16px 20px;margin-bottom:20px;
                    display:flex;align-items:center;gap:12px;">
          <span style="font-size:24px;">{sev_icon}</span>
          <div>
            <div style="font-family:{_FONT};font-size:14px;font-weight:600;color:{sev_color};">
              Overall Status: {sev.title()}</div>
            <div style="font-family:{_FONT};font-size:12px;color:#6B7280;">
              {n_alerts} active alert{"s" if n_alerts != 1 else ""} ·
              {ew_result.ok_count} trigger{"s" if ew_result.ok_count != 1 else ""} within normal range ·
              Evaluated {ew_result.generated_at}
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # -----------------------------------------------------------------------
    # Trigger traffic lights (6 triggers)
    # -----------------------------------------------------------------------
    _render_trigger_summary(ew_result)

    # -----------------------------------------------------------------------
    # Alert cards
    # -----------------------------------------------------------------------
    sorted_alerts = ew_result.by_severity()
    active = [a for a in sorted_alerts if a.severity.value != "ok"]

    if not active:
        st.success("All workforce risk triggers are within acceptable thresholds.")
    else:
        st.markdown(
            f"<h3 style='font-family:\"Fraunces\",Georgia,serif;font-size:16px;"
            f"color:#003366;font-weight:300;margin:20px 0 8px;'>"
            f"Active Alerts ({len(active)})</h3>",
            unsafe_allow_html=True,
        )
        for alert in active:
            _render_alert_card(alert)

    # -----------------------------------------------------------------------
    # Risk digest
    # -----------------------------------------------------------------------
    _render_risk_digest(ew_result, data)


def _render_trigger_summary(ew_result) -> None:
    triggers = [
        ("attrition_spike",      "Attrition Spike"),
        ("nexus_attrition_risk", "Nexus Risk"),
        ("team_fragility",       "Team Fragility"),
        ("budget_overrun",       "Budget Pace"),
        ("impact_decline",       "Impact Trend"),
        ("skill_gap",            "Skill Coverage"),
    ]

    trigger_sev: dict[str, str] = {}
    for alert in ew_result.alerts:
        t = alert.trigger
        current = trigger_sev.get(t, "ok")
        if _SEVERITY_ORDER_MAP.get(alert.severity.value, 0) > _SEVERITY_ORDER_MAP.get(current, 0):
            trigger_sev[t] = alert.severity.value

    cols = st.columns(6)
    for i, (key, label) in enumerate(triggers):
        sev = trigger_sev.get(key, "ok")
        color = _SEVERITY_COLORS.get(sev, _C["mid"])
        icon = _SEVERITY_ICONS.get(sev, "⚪")
        with cols[i]:
            st.markdown(
                f"""
                <div style="background:#fff;border-radius:8px;padding:12px;
                            text-align:center;box-shadow:0 1px 4px rgba(0,51,102,0.08);
                            border-top:3px solid {color};">
                  <div style="font-size:18px;margin-bottom:4px;">{icon}</div>
                  <div style="font-family:{_FONT};font-size:10px;color:#6B7280;
                              font-weight:600;">{label}</div>
                  <div style="font-family:{_FONT};font-size:9px;color:{color};
                              text-transform:uppercase;font-weight:600;margin-top:2px;">
                  {sev.title()}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


_SEVERITY_ORDER_MAP = {"ok": 0, "low": 1, "moderate": 2, "high": 3, "critical": 4}


def _render_alert_card(alert) -> None:
    sev = alert.severity.value
    color = _SEVERITY_COLORS.get(sev, _C["mid"])
    icon = _SEVERITY_ICONS.get(sev, "⚪")
    entities = ", ".join(alert.affected_entities[:5])
    if len(alert.affected_entities) > 5:
        entities += f" +{len(alert.affected_entities)-5} more"

    st.markdown(
        f"""
        <div style="background:#fff;border-radius:8px;padding:16px;
                    margin-bottom:10px;box-shadow:0 1px 4px rgba(0,51,102,0.08);
                    border-left:4px solid {color};">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
            <span style="font-size:16px;">{icon}</span>
            <span style="font-family:{_FONT};font-size:13px;font-weight:600;
                         color:{color};">{alert.title}</span>
            <span style="margin-left:auto;background:{color}20;color:{color};
                         padding:2px 8px;border-radius:4px;font-size:10px;
                         font-weight:600;">{sev.upper()}</span>
          </div>
          <div style="font-family:{_FONT};font-size:12px;color:#374151;
                      margin-bottom:8px;">{alert.message}</div>
          {f'<div style="font-family:{_FONT};font-size:11px;color:#6B7280;margin-bottom:6px;">Affected: {entities}</div>' if entities else ''}
          <div style="font-family:{_FONT};font-size:11px;color:#003366;
                      background:#E8F0FA;border-radius:4px;padding:6px 10px;">
            💡 {alert.recommendation}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_risk_digest(ew_result, data: DashboardData) -> None:
    sorted_alerts = ew_result.by_severity()
    active = [a for a in sorted_alerts if a.severity.value != "ok"]

    st.markdown(
        "<h3 style='font-family:\"Fraunces\",Georgia,serif;font-size:16px;"
        "color:#003366;font-weight:300;margin:24px 0 8px;'>"
        "Weekly Risk Digest</h3>",
        unsafe_allow_html=True,
    )

    critical = [a for a in active if a.severity.value == "critical"]
    high = [a for a in active if a.severity.value == "high"]
    moderate = [a for a in active if a.severity.value == "moderate"]

    lines = [
        f"**Organization:** {data.org_name} · "
        f"**Headcount:** {data.total_headcount:,} · "
        f"**Scenario:** {data.scenario_id}",
        f"**Assessment Date:** {ew_result.generated_at}",
        "",
        "---",
        "",
    ]

    if critical:
        lines.append("### Critical Actions Required")
        for a in critical:
            lines.append(f"- **{a.title}**: {a.message}")
            lines.append(f"  - *Recommendation:* {a.recommendation}")
        lines.append("")

    if high:
        lines.append("### High Priority")
        for a in high:
            lines.append(f"- **{a.title}**: {a.message}")
        lines.append("")

    if moderate:
        lines.append("### Moderate Priority")
        for a in moderate:
            lines.append(f"- {a.title}: {a.message}")
        lines.append("")

    if not active:
        lines.append("✅ All workforce risk triggers are within normal range.")

    lines += [
        "---",
        f"*Generated by EIBO Predictive Analytics · {data.org_name}*",
    ]

    digest_text = "\n".join(lines)
    with st.expander("View Digest (copy-paste ready)", expanded=False):
        st.markdown(digest_text)
        st.download_button(
            label="Download Risk Digest (.md)",
            data=digest_text.encode(),
            file_name=f"risk_digest_{data.scenario_id}_{ew_result.generated_at[:10]}.md",
            mime="text/markdown",
        )


# ===========================================================================
# Shared helpers
# ===========================================================================

def _metric_card(col, label: str, value: str, sub: str, color: str) -> None:
    with col:
        st.markdown(
            f"""
            <div style="background:#fff;border-radius:8px;padding:16px;
                        box-shadow:0 1px 4px rgba(0,51,102,0.08);
                        border-top:3px solid {color};">
              <div style="font-family:{_FONT};font-size:10px;color:#6B7280;
                          font-weight:600;text-transform:uppercase;
                          letter-spacing:1px;margin-bottom:4px;">{label}</div>
              <div style="font-family:'Fraunces',Georgia,serif;font-size:24px;
                          font-weight:300;color:{color};">{value}</div>
              <div style="font-family:{_FONT};font-size:10px;color:#9CA3AF;">
                          {sub}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
