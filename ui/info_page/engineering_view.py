"""Info page — Engineering View.

Audience: Technical evaluators, architects, data engineers.
Accurate, detailed, honest. Includes limitations.
"""

import streamlit as st

from ui.components.brand import eyebrow, hero_section, section_divider
from ui.info_page.diagrams import (
    medallion_architecture_diagram,
    ilp_feasible_region_chart,
    collaboration_network_example,
    attrition_risk_heatmap,
)


def render() -> None:
    hero_section(
        label="EIBO · ENGINEERING OVERVIEW",
        title="Open-source workforce intelligence. No black boxes.",
        italic_word="intelligence",
        subtitle=(
            "Full architecture transparency, reproducible methodology, and "
            "100% open-source stack. Every algorithm is auditable, every prediction "
            "is explainable, and every constraint is configurable."
        ),
        stats=[
            ("< 2s", "ILP solve time for 5K employees"),
            ("< 100ms", "Dashboard queries at 50K records"),
            ("SHAP", "Explainability on every ML prediction"),
            ("MIT", "License — no vendor lock-in"),
        ],
    )

    _render_architecture()
    _render_algorithms()
    _render_data_schema()
    _render_stack()
    _render_performance()
    _render_security()
    _render_deployment()


# ---------------------------------------------------------------------------
# Architecture
# ---------------------------------------------------------------------------

def _render_architecture() -> None:
    st.markdown(
        '<div style="max-width:1200px; margin:0 auto; padding:56px 48px 0;">',
        unsafe_allow_html=True,
    )
    eyebrow("SYSTEM ARCHITECTURE")
    st.markdown(
        '<h2 style="font-family:\'Fraunces\',serif; font-size:22px; font-weight:300; '
        'color:#0a1628; margin:4px 0 8px;">Medallion Architecture with graph and ML layers</h2>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="font-family:\'Plus Jakarta Sans\',sans-serif; font-size:13px; '
        'color:#6B7280; margin-bottom:24px;">Three data layers feed four analytical engines. '
        'Everything runs on-premises via Docker Compose.</p>',
        unsafe_allow_html=True,
    )
    st.plotly_chart(medallion_architecture_diagram(), use_container_width=True)

    col1, col2, col3 = st.columns(3, gap="medium")
    notes = [
        ("BRONZE LAYER", "Raw ingestion only. Source data preserved as-is. "
         "Connectors for CSV, Excel, Workday, SuccessFactors, BambooHR. "
         "Schema validation at ingestion boundary."),
        ("SILVER LAYER", "Cleansing and normalization: salary currency normalization, "
         "date standardization, seniority taxonomy mapping, referential integrity enforcement. "
         "Validation reports generated per run."),
        ("GOLD LAYER", "DuckDB materialized views: team spend aggregations, performance trends, "
         "impact feature tables. Sub-100ms queries at 50K+ employees. Incremental refresh."),
    ]
    for col, (title, body) in zip([col1, col2, col3], notes):
        with col:
            st.markdown(
                f"""
                <div style="background:#fff; border-radius:10px; padding:16px 18px;
                            box-shadow:0 1px 3px rgba(0,51,102,0.07); border-top:3px solid #C8982A;">
                  <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:8px;
                              font-weight:700; letter-spacing:2px; color:#C8982A;
                              text-transform:uppercase; margin-bottom:8px;">{title}</div>
                  <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:12px;
                              color:#475569; line-height:1.65;">{body}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Algorithms
# ---------------------------------------------------------------------------

def _render_algorithms() -> None:
    st.markdown(
        '<div style="max-width:1200px; margin:0 auto; padding:56px 48px 0;">',
        unsafe_allow_html=True,
    )
    section_divider()
    eyebrow("ALGORITHMS")
    st.markdown(
        '<h2 style="font-family:\'Fraunces\',serif; font-size:22px; font-weight:300; '
        'color:#0a1628; margin:4px 0 8px;">Five analytical engines under the hood</h2>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="font-family:\'Plus Jakarta Sans\',sans-serif; font-size:13px; '
        'color:#6B7280; margin-bottom:32px;">Each component is independently testable '
        'and replaceable.</p>',
        unsafe_allow_html=True,
    )

    _algo_impact_score()
    section_divider()
    _algo_ilp()
    section_divider()
    _algo_graph()
    section_divider()
    _algo_attrition()
    section_divider()
    _algo_forecasting()
    st.markdown("</div>", unsafe_allow_html=True)


def _algo_impact_score() -> None:
    st.markdown(
        """
        <div style="display:flex; align-items:flex-start; gap:16px; margin-bottom:8px;">
          <div style="font-family:'Fraunces',serif; font-size:36px; font-weight:300;
                      color:#f1f5f9; line-height:1;">01</div>
          <div>
            <div style="font-family:'Fraunces',serif; font-size:16px; font-weight:400;
                        color:#0a1628;">Impact Scoring Model</div>
            <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:9px;
                        font-weight:700; letter-spacing:2px; text-transform:uppercase;
                        color:#C8982A;">Random Forest · SHAP · Scikit-learn</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([1, 1], gap="large")
    with col1:
        st.markdown(
            """
            <p style="font-family:'Plus Jakarta Sans',sans-serif; font-size:13px;
                      color:#475569; line-height:1.75;">
              The Impact Score is a 0–100 composite trained on historical retention outcomes.
              When historical data is unavailable, the model uses weighted heuristics with
              the same feature set.
            </p>
            <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:9px;
                        font-weight:700; letter-spacing:2px; text-transform:uppercase;
                        color:#fff; background:#003366; display:inline-block;
                        border-radius:4px; padding:2px 6px; margin:8px 0 4px;">WHY</div>
            <p style="font-family:'Plus Jakarta Sans',sans-serif; font-size:12px;
                      color:#475569; line-height:1.7;">
              Traditional performance ratings miss network effects. A mid-level engineer
              who bridges 4 teams has more organizational impact than a high-performer
              who works in isolation. SHAP values make every score auditable.
            </p>
            <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:9px;
                        font-weight:700; letter-spacing:2px; text-transform:uppercase;
                        color:#003366; background:#e0eaf4; display:inline-block;
                        border-radius:4px; padding:2px 6px; margin:8px 0 4px;">HOW</div>
            <p style="font-family:'Plus Jakarta Sans',sans-serif; font-size:12px;
                      color:#475569; line-height:1.7;">
              Cross-validation across departments prevents between-group bias. Fairness audit
              checks SHAP distribution across demographic groups. Monthly retraining cadence.
            </p>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            "<p style='font-family:\"Plus Jakarta Sans\",sans-serif; font-size:11px; "
            "color:#6B7280; margin-bottom:8px;'>Feature engineering:</p>",
            unsafe_allow_html=True,
        )
        features = [
            ("kpi_history", "40%", "Weighted average of quarterly reviews (recency-weighted)"),
            ("betweenness_centrality", "30%", "Bridge role in collaboration network (NetworkX)"),
            ("skill_criticality", "20%", "Weighted scarcity × proficiency for each critical skill"),
            ("replacement_cost", "10%", "Salary × market_multiplier × skill_rarity_factor"),
        ]
        for feat, weight, desc in features:
            st.markdown(
                f"""
                <div style="background:#F4F6F9; border-radius:6px; padding:10px 14px;
                            margin-bottom:8px; display:flex; align-items:flex-start; gap:12px;">
                  <div style="font-family:'Fraunces',serif; font-size:20px; font-weight:300;
                              color:#C8982A; min-width:48px; text-align:right;">{weight}</div>
                  <div>
                    <div style="font-family:'Courier New',monospace; font-size:11px;
                                color:#003366; font-weight:600;">{feat}</div>
                    <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:11px;
                                color:#475569; line-height:1.5;">{desc}</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _algo_ilp() -> None:
    st.markdown(
        """
        <div style="display:flex; align-items:flex-start; gap:16px; margin-bottom:8px;">
          <div style="font-family:'Fraunces',serif; font-size:36px; font-weight:300;
                      color:#f1f5f9; line-height:1;">02</div>
          <div>
            <div style="font-family:'Fraunces',serif; font-size:16px; font-weight:400;
                        color:#0a1628;">Integer Linear Programming Model</div>
            <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:9px;
                        font-weight:700; letter-spacing:2px; text-transform:uppercase;
                        color:#C8982A;">PuLP · CBC Solver · Multi-objective</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([1, 1], gap="large")
    with col1:
        st.markdown(
            "<p style='font-family:\"Plus Jakarta Sans\",sans-serif; font-size:11px; "
            "color:#6B7280; margin-bottom:4px;'>Formal model:</p>",
            unsafe_allow_html=True,
        )
        st.latex(r"""
\text{Maximize} \quad \sum_{i=1}^{n} \text{impact\_score}_i \cdot x_i
""")
        st.markdown(
            "<p style='font-family:\"Plus Jakarta Sans\",sans-serif; font-size:11px; "
            "color:#6B7280; margin:8px 0 4px;'>Subject to:</p>",
            unsafe_allow_html=True,
        )
        st.latex(r"""
\begin{aligned}
& \sum_{i=1}^{n} \text{cost}_i \cdot x_i \leq B && \text{(budget)} \\
& \sum_{i \in L_k} x_i \geq 1 \quad \forall k && \text{(leadership per team)} \\
& \sum_{i : s_{ij}=1} x_i \geq 1 \quad \forall j && \text{(critical skill } j \text{)} \\
& x_i \in \{0, 1\} \quad \forall i
\end{aligned}
""")

    with col2:
        st.plotly_chart(ilp_feasible_region_chart(), use_container_width=True)
        st.markdown(
            """
            <div style="background:#fff; border-radius:10px; padding:14px 16px;
                        box-shadow:0 1px 3px rgba(0,51,102,0.07); border-left:3px solid #C8982A;
                        margin-top:8px;">
              <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:9px;
                          font-weight:700; letter-spacing:1.5px; text-transform:uppercase;
                          color:#C8982A; margin-bottom:5px;">INFEASIBILITY HANDLING</div>
              <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:12px;
                          color:#475569; line-height:1.65;">
                When no feasible solution exists, the engine identifies conflicting constraints
                and returns specific resolution suggestions: increase budget by X, relax
                skills constraint Y, or reduce protected employees by Z.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _algo_graph() -> None:
    st.markdown(
        """
        <div style="display:flex; align-items:flex-start; gap:16px; margin-bottom:8px;">
          <div style="font-family:'Fraunces',serif; font-size:36px; font-weight:300;
                      color:#f1f5f9; line-height:1;">03</div>
          <div>
            <div style="font-family:'Fraunces',serif; font-size:16px; font-weight:400;
                        color:#0a1628;">Graph Analysis Engine</div>
            <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:9px;
                        font-weight:700; letter-spacing:2px; text-transform:uppercase;
                        color:#C8982A;">NetworkX · Louvain Community Detection</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col1, col2 = st.columns([1, 1], gap="large")
    with col1:
        metrics = [
            ("Degree Centrality", r"C_D(v) = \frac{\deg(v)}{n-1}",
             "Normalized direct connection count. Measures immediate reach."),
            ("Betweenness Centrality",
             r"C_B(v) = \sum_{s \neq v \neq t} \frac{\sigma_{st}(v)}{\sigma_{st}}",
             "Fraction of shortest paths through v. Identifies bridge roles."),
            ("PageRank",
             r"PR(v) = \frac{1-d}{n} + d \sum_{u \in N(v)} \frac{PR(u)}{L(u)}",
             "Iterative influence score. Captures second-order collaboration effects."),
        ]
        for metric, formula, desc in metrics:
            st.markdown(
                f'<p style="font-family:\'Plus Jakarta Sans\',sans-serif; font-size:11px; '
                f'font-weight:600; color:#003366; margin:12px 0 4px;">{metric}</p>',
                unsafe_allow_html=True,
            )
            st.latex(formula)
            st.markdown(
                f'<p style="font-family:\'Plus Jakarta Sans\',sans-serif; font-size:11px; '
                f'color:#475569; margin:0 0 8px;">{desc}</p>',
                unsafe_allow_html=True,
            )
        st.markdown(
            """
            <div style="background:#F4F6F9; border-radius:8px; padding:12px 16px; margin-top:8px;">
              <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:11px;
                          color:#003366; font-weight:600; margin-bottom:4px;">
                Nexus threshold
              </div>
              <div style="font-family:'Courier New',monospace; font-size:11px; color:#475569;">
                betweenness_centrality > 0.7<br>
                OR combined_centrality > 85th percentile
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.plotly_chart(collaboration_network_example(), use_container_width=True)


def _algo_attrition() -> None:
    st.markdown(
        """
        <div style="display:flex; align-items:flex-start; gap:16px; margin-bottom:8px;">
          <div style="font-family:'Fraunces',serif; font-size:36px; font-weight:300;
                      color:#f1f5f9; line-height:1;">04</div>
          <div>
            <div style="font-family:'Fraunces',serif; font-size:16px; font-weight:400;
                        color:#0a1628;">Attrition Risk Model</div>
            <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:9px;
                        font-weight:700; letter-spacing:2px; text-transform:uppercase;
                        color:#C8982A;">XGBoost · SMOTE · Platt Calibration · SHAP</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col1, col2 = st.columns([1, 1], gap="large")
    with col1:
        st.markdown(
            """
            <p style="font-family:'Plus Jakarta Sans',sans-serif; font-size:13px;
                      color:#475569; line-height:1.75;">
              Binary classification (will leave within 12 months) with probability calibration
              via Platt scaling. Class imbalance addressed with SMOTE oversampling.
              Output is a calibrated probability, not a binary flag.
            </p>
            <p style="font-family:'Plus Jakarta Sans',sans-serif; font-size:11px;
                      color:#6B7280; margin-bottom:6px;">Key features:</p>
            """,
            unsafe_allow_html=True,
        )
        features = [
            "Compensation ratio vs. market median",
            "Tenure and time since last promotion",
            "Performance trajectory (last 4 quarters)",
            "Manager change frequency (last 24 months)",
            "Collaboration network isolation (shrinking network)",
            "Engagement survey scores (when available)",
            "Impact Score trend (declining = flight risk signal)",
        ]
        for f in features:
            st.markdown(
                f'<div style="font-family:\'Courier New\',monospace; font-size:11px; '
                f'color:#003366; padding:3px 0;">→ {f}</div>',
                unsafe_allow_html=True,
            )
        st.markdown(
            """
            <div style="background:#FEF0E6; border-radius:8px; padding:12px 16px; margin-top:12px;
                        border-left:3px solid #F07020;">
              <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:9px;
                          font-weight:700; letter-spacing:1.5px; text-transform:uppercase;
                          color:#F07020; margin-bottom:5px;">KNOWN LIMITATION</div>
              <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:12px;
                          color:#475569; line-height:1.65;">
                Model requires ≥ 6 months of historical retention data for meaningful AUC.
                Synthetic demo data uses calibrated heuristics as a proxy.
                Target: AUC > 0.75 on holdout set.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.plotly_chart(attrition_risk_heatmap(), use_container_width=True)


def _algo_forecasting() -> None:
    st.markdown(
        """
        <div style="display:flex; align-items:flex-start; gap:16px; margin-bottom:8px;">
          <div style="font-family:'Fraunces',serif; font-size:36px; font-weight:300;
                      color:#f1f5f9; line-height:1;">05</div>
          <div>
            <div style="font-family:'Fraunces',serif; font-size:16px; font-weight:400;
                        color:#0a1628;">Forecasting Engine</div>
            <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:9px;
                        font-weight:700; letter-spacing:2px; text-transform:uppercase;
                        color:#C8982A;">Prophet · Monte Carlo · Scikit-learn</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col1, col2 = st.columns([1, 1], gap="large")
    with col1:
        st.markdown(
            """
            <p style="font-family:'Plus Jakarta Sans',sans-serif; font-size:13px;
                      color:#475569; line-height:1.75;">
              Budget and headcount forecasting via Facebook Prophet with additive seasonality.
              Known future events (planned hires, departures, promotions) are injected as
              regressors. Confidence intervals at 80% and 95%.
            </p>
            """,
            unsafe_allow_html=True,
        )
        prophet_config = {
            "yearly_seasonality": True,
            "weekly_seasonality": False,
            "changepoint_prior_scale": 0.05,
            "seasonality_mode": "additive",
            "horizon": "180 days",
            "target_MAPE": "< 15% (3-month)",
        }
        st.markdown(
            '<p style="font-family:\'Plus Jakarta Sans\',sans-serif; font-size:11px; '
            'color:#6B7280; margin-bottom:6px;">Prophet configuration:</p>',
            unsafe_allow_html=True,
        )
        for k, v in prophet_config.items():
            st.markdown(
                f'<div style="font-family:\'Courier New\',monospace; font-size:11px; '
                f'color:#003366; padding:3px 0;">{k}: <span style="color:#475569;">{v}</span></div>',
                unsafe_allow_html=True,
            )
    with col2:
        st.markdown(
            """
            <div style="background:#fff; border-radius:10px; padding:20px;
                        box-shadow:0 1px 4px rgba(0,51,102,0.08); border-top:3px solid #C8982A;">
              <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:9px;
                          font-weight:700; letter-spacing:2px; text-transform:uppercase;
                          color:#C8982A; margin-bottom:10px;">MONTE CARLO ENGINE</div>
              <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:12px;
                          color:#475569; line-height:1.7; margin-bottom:12px;">
                Budget stress testing via N=10,000 simulations with randomized:
              </div>
            """,
            unsafe_allow_html=True,
        )
        mc_params = [
            "Attrition rate (±30% around forecast)",
            "Salary increase % (market distribution)",
            "Hiring cost variance (±25%)",
            "Productivity ramp time (role-specific)",
        ]
        for p in mc_params:
            st.markdown(
                f'<div style="font-family:\'Courier New\',monospace; font-size:11px; '
                f'color:#003366; padding:2px 0; margin-left:8px;">→ {p}</div>',
                unsafe_allow_html=True,
            )
        st.markdown(
            """
              <div style="margin-top:12px; font-family:'Plus Jakarta Sans',sans-serif;
                          font-size:11px; color:#475569; line-height:1.65;">
                Output: fan chart showing P10/P50/P90 budget trajectories.
                Completion target: &lt; 5s for 10K simulations.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Data schema
# ---------------------------------------------------------------------------

def _render_data_schema() -> None:
    st.markdown(
        '<div style="max-width:1200px; margin:0 auto; padding:56px 48px 0;">',
        unsafe_allow_html=True,
    )
    section_divider()
    eyebrow("DATA SCHEMA")
    st.markdown(
        '<h2 style="font-family:\'Fraunces\',serif; font-size:22px; font-weight:300; '
        'color:#0a1628; margin:4px 0 8px;">Core entities and relationships</h2>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="font-family:\'Plus Jakarta Sans\',sans-serif; font-size:13px; '
        'color:#6B7280; margin-bottom:24px;">PostgreSQL schema with DuckDB analytics layer. '
        'Star schema for efficient OLAP queries.</p>',
        unsafe_allow_html=True,
    )

    tables = [
        ("dim_employee", "Core", [
            ("employee_id", "VARCHAR(36)", "PK"),
            ("full_name", "VARCHAR(150)", ""),
            ("role_title", "VARCHAR(100)", ""),
            ("seniority_level", "VARCHAR(20)", "junior/mid/senior/lead/director/exec"),
            ("department", "VARCHAR(100)", ""),
            ("team_id", "VARCHAR(36)", "FK → dim_team"),
            ("manager_id", "VARCHAR(36)", "FK → dim_employee (self-ref)"),
            ("annual_salary", "NUMERIC(12,2)", ""),
            ("annual_benefits", "NUMERIC(12,2)", "≈ 30% of salary"),
            ("hire_date", "DATE", ""),
        ]),
        ("dim_team", "Core", [
            ("team_id", "VARCHAR(36)", "PK"),
            ("team_name", "VARCHAR(100)", ""),
            ("department", "VARCHAR(100)", ""),
            ("annual_budget", "NUMERIC(14,2)", ""),
            ("manager_id", "VARCHAR(36)", "FK → dim_employee"),
        ]),
        ("fact_performance", "Fact", [
            ("performance_id", "VARCHAR(36)", "PK"),
            ("employee_id", "VARCHAR(36)", "FK → dim_employee"),
            ("review_period", "VARCHAR(20)", "e.g. '2024-Q1'"),
            ("kpi_score", "NUMERIC(4,2)", "0.0 – 5.0"),
            ("goals_met_pct", "NUMERIC(5,2)", "0 – 100"),
            ("manager_rating", "NUMERIC(4,2)", "0.0 – 5.0"),
        ]),
        ("fact_collaboration", "Graph", [
            ("source_id", "VARCHAR(36)", "FK → dim_employee"),
            ("target_id", "VARCHAR(36)", "FK → dim_employee"),
            ("relationship_type", "VARCHAR(30)", "collaborates_with / reports_to / mentors"),
            ("interaction_weight", "NUMERIC(4,3)", "0.0 – 1.0"),
        ]),
    ]

    for table_name, tag, columns in tables:
        tag_color = {"Core": "#003366", "Fact": "#7C4DBD", "Graph": "#27B97C"}[tag]
        tag_bg = {"Core": "#E0EAF4", "Fact": "#F0EBF9", "Graph": "#E0F7EF"}[tag]
        tag_txt = {"Core": "#001F4D", "Fact": "#3D1F70", "Graph": "#0D5C3A"}[tag]

        with st.expander(f"📋 {table_name}"):
            st.markdown(
                f'<div style="display:inline-block; font-family:\'Plus Jakarta Sans\',sans-serif; '
                f'font-size:9px; font-weight:500; letter-spacing:1.5px; text-transform:uppercase; '
                f'color:{tag_txt}; background:{tag_bg}; border-radius:20px; '
                f'padding:3px 12px; margin-bottom:12px;">{tag}</div>',
                unsafe_allow_html=True,
            )
            df_display = __import__("pandas").DataFrame(
                columns, columns=["Column", "Type", "Notes"]
            )
            st.dataframe(df_display, use_container_width=True, hide_index=True)

    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Tech stack
# ---------------------------------------------------------------------------

def _render_stack() -> None:
    st.markdown(
        '<div style="max-width:1200px; margin:0 auto; padding:56px 48px 0;">',
        unsafe_allow_html=True,
    )
    section_divider()
    eyebrow("TECHNOLOGY STACK")
    st.markdown(
        '<h2 style="font-family:\'Fraunces\',serif; font-size:22px; font-weight:300; '
        'color:#0a1628; margin:4px 0 8px;">100% open source. No vendor lock-in.</h2>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="font-family:\'Plus Jakarta Sans\',sans-serif; font-size:13px; '
        'color:#6B7280; margin-bottom:24px;">All licenses verified permissive (MIT, Apache 2.0, BSD).</p>',
        unsafe_allow_html=True,
    )

    groups = {
        "UI & Interface": [
            ("Streamlit", "UI Layer", "SPA with multi-page routing via session state"),
            ("Plotly", "Visualization", "Interactive charts, architecture diagrams"),
        ],
        "Data & Storage": [
            ("PostgreSQL 16", "Relational DB", "Persistent data, RBAC, audit trail"),
            ("DuckDB", "Analytics Engine", "In-process OLAP, sub-100ms queries"),
            ("NetworkX", "Graph DB", "In-memory collaboration graphs"),
        ],
        "ML & Analytics": [
            ("Scikit-learn", "Impact Model", "Random Forest + SHAP explainability"),
            ("XGBoost", "Attrition Model", "Gradient boosting with calibration"),
            ("Prophet", "Forecasting", "Time series with seasonality"),
            ("PuLP / CBC", "Optimization", "Integer linear programming"),
            ("PyOD", "Anomaly Detection", "Spending pattern outliers"),
        ],
        "Infrastructure": [
            ("Docker Compose", "Deployment", "Single-command local deployment"),
            ("Prefect", "Workflow", "Pipeline orchestration, scheduling"),
            ("Redis", "Cache", "Optional — high-concurrency deployments"),
        ],
    }

    cols = st.columns(4, gap="medium")
    for col, (group, items) in zip(cols, groups.items()):
        with col:
            st.markdown(
                f"""
                <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:8px;
                            font-weight:700; letter-spacing:3px; text-transform:uppercase;
                            color:#003366; background:#e0eaf4; padding:7px 12px;
                            border-radius:8px 8px 0 0; border-bottom:2px solid #C8982A;">
                  {group}
                </div>
                """,
                unsafe_allow_html=True,
            )
            for name, role, detail in items:
                st.markdown(
                    f"""
                    <div style="background:#fff; padding:12px 14px;
                                box-shadow:0 1px 2px rgba(0,51,102,0.06); margin-bottom:1px;">
                      <div style="font-family:'Fraunces',serif; font-size:13px;
                                  font-weight:400; color:#003366;">{name}</div>
                      <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:9px;
                                  font-weight:700; letter-spacing:1.5px; text-transform:uppercase;
                                  color:#C8982A; margin:2px 0;">{role}</div>
                      <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:11px;
                                  color:#64748b; line-height:1.5;">{detail}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Performance benchmarks
# ---------------------------------------------------------------------------

def _render_performance() -> None:
    st.markdown(
        '<div style="max-width:1200px; margin:0 auto; padding:56px 48px 0;">',
        unsafe_allow_html=True,
    )
    section_divider()
    eyebrow("PERFORMANCE TARGETS")
    st.markdown(
        '<h2 style="font-family:\'Fraunces\',serif; font-size:22px; font-weight:300; '
        'color:#0a1628; margin:4px 0 8px;">Benchmarks and design targets</h2>',
        unsafe_allow_html=True,
    )

    benchmarks = [
        ("Dashboard query latency", "< 100ms", "DuckDB at 50K employees", "green"),
        ("ILP solve time (500 emp)", "< 2s", "PuLP/CBC, standard hardware", "green"),
        ("ILP solve time (5K emp)", "< 10s", "PuLP/CBC, standard hardware", "green"),
        ("Impact Score inference", "< 500ms", "Batch of 5K employees", "green"),
        ("Monte Carlo (10K sim)", "< 5s", "NumPy vectorized", "green"),
        ("Demo database seed", "< 30s", "All scenarios × sizes", "green"),
        ("Dashboard (100K emp, 50 users)", "< 2s", "Sprint 7 target", "orange"),
        ("Attrition model AUC", "> 0.75", "Holdout test set", "orange"),
        ("Budget forecast MAPE", "< 15%", "3-month horizon", "orange"),
        ("Notification delivery", "< 30s", "From trigger event", "orange"),
    ]

    import pandas as pd
    df = pd.DataFrame(benchmarks, columns=["Metric", "Target", "Notes", "Status"])
    st.dataframe(
        df.drop(columns=["Status"]),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------

def _render_security() -> None:
    st.markdown(
        '<div style="max-width:1200px; margin:0 auto; padding:56px 48px 0;">',
        unsafe_allow_html=True,
    )
    section_divider()
    eyebrow("SECURITY ARCHITECTURE")
    st.markdown(
        '<h2 style="font-family:\'Fraunces\',serif; font-size:22px; font-weight:300; '
        'color:#0a1628; margin:4px 0 8px;">Defense-in-depth for sensitive HR data</h2>',
        unsafe_allow_html=True,
    )

    cols = st.columns(3, gap="medium")
    security_items = [
        ("Access Control", [
            "6-tier RBAC: Viewer → Analyst → Manager → Director → Executive → Admin",
            "Department-level data isolation (row-level security)",
            "Salary visibility: masked / ranges / full (role-dependent)",
            "OAuth2/OIDC: Google Workspace, Azure AD, Okta",
            "Local auth fallback for air-gapped deployments",
        ]),
        ("Data Protection", [
            "Zero external data transmission — runs entirely on-premises",
            "PII masking at query layer for unauthorized roles",
            "Configurable data retention + automated purging",
            "Anonymization pipeline for long-term archival",
            "GDPR compliance report generation on demand",
        ]),
        ("Audit & Monitoring", [
            "Immutable audit log: all access, simulations, overrides, exports",
            "Failed access attempt logging",
            "Model drift detection with threshold alerts",
            "OWASP Top 10 scan in Sprint 9 security hardening",
            "Dependency vulnerability audit (safety check)",
        ]),
    ]
    for col, (title, items) in zip(cols, security_items):
        with col:
            items_html = "".join(
                f'<div style="font-family:\'Plus Jakarta Sans\',sans-serif; font-size:11.5px; '
                f'color:#475569; padding:5px 0; border-bottom:1px solid #f0f0f0; '
                f'line-height:1.55;">→ {item}</div>'
                for item in items
            )
            st.markdown(
                f"""
                <div style="background:#fff; border-radius:10px; padding:20px;
                            box-shadow:0 1px 4px rgba(0,51,102,0.08);
                            border-top:3px solid #C8982A;">
                  <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:9px;
                              font-weight:700; letter-spacing:2px; text-transform:uppercase;
                              color:#C8982A; margin-bottom:12px;">{title}</div>
                  {items_html}
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Deployment guide
# ---------------------------------------------------------------------------

def _render_deployment() -> None:
    st.markdown(
        '<div style="max-width:1200px; margin:0 auto; padding:56px 48px;">',
        unsafe_allow_html=True,
    )
    section_divider()
    eyebrow("DEPLOYMENT")
    st.markdown(
        '<h2 style="font-family:\'Fraunces\',serif; font-size:22px; font-weight:300; '
        'color:#0a1628; margin:4px 0 8px;">From zero to running in under 5 minutes</h2>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<p style="font-family:\'Plus Jakarta Sans\',sans-serif; font-size:13px; '
        'color:#6B7280; margin-bottom:16px;">Requirements: Docker Engine, Docker Compose.</p>',
        unsafe_allow_html=True,
    )

    steps = [
        ("Clone and configure",
         "git clone https://github.com/your-org/eibo.git\ncd eibo\ncp .env.example .env\n# Edit .env with your database credentials"),
        ("Start the stack",
         "docker-compose up -d\n# PostgreSQL + Streamlit start automatically\n# Check status: docker-compose ps"),
        ("Load demo data",
         "docker-compose exec streamlit python demo_data/seed_demo.py --scenario all --size medium\n# Seeds 3 scenarios in ~30 seconds"),
        ("Open the platform",
         "# Browser: http://localhost:8501\n# pgAdmin (dev): http://localhost:5050\n# Credentials: see .env"),
    ]

    for i, (title, code) in enumerate(steps, 1):
        st.markdown(
            f"""
            <div style="background:#fff; border-radius:10px; padding:20px 24px;
                        box-shadow:0 1px 3px rgba(0,51,102,0.07); margin-bottom:12px;
                        border-left:3px solid #C8982A;">
              <div style="display:flex; align-items:center; gap:12px; margin-bottom:10px;">
                <div style="font-family:'Fraunces',serif; font-size:24px; font-weight:300;
                            color:#f1f5f9; line-height:1;">{i:02d}</div>
                <div style="font-family:'Fraunces',serif; font-size:14px; font-weight:400;
                            color:#0a1628;">{title}</div>
              </div>
              <div style="background:#1C1C2E; border-radius:6px; padding:14px 16px;
                          font-family:'Courier New',monospace; font-size:11px;
                          color:#E8C46A; line-height:1.8; white-space:pre;">{code}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)
