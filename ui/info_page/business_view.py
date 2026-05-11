"""Info page — Business View.

Audience: People Analytics leads, HR Directors, Finance VPs.
Zero code, zero jargon. Visual-first explanations.
"""

import streamlit as st

from ui.components.brand import eyebrow, hero_section, section_divider, card
from ui.info_page.diagrams import (
    impact_score_breakdown_chart,
    collaboration_network_example,
    decision_flow_diagram,
    sample_performance_trend,
    attrition_risk_heatmap,
)


def render() -> None:
    hero_section(
        label="EIBO · BUSINESS OVERVIEW",
        title="Turn budget pressure into strategic clarity.",
        italic_word="strategic",
        subtitle=(
            "EIBO gives organizational leaders a data-driven lens to balance "
            "cost targets with critical talent retention — without sacrificing "
            "the human judgment that defines responsible decision-making."
        ),
        stats=[
            ("3×", "Faster budget scenario analysis"),
            ("< 2s", "Optimization for 5,000 employees"),
            ("100%", "Human override on every suggestion"),
            ("$0", "Licensing cost — fully open source"),
        ],
    )

    _render_tour()
    _render_key_concepts()
    _render_use_cases()
    _render_roi_calculator()
    _render_glossary()
    _render_faq()


# ---------------------------------------------------------------------------
# Guided tour
# ---------------------------------------------------------------------------

def _render_tour() -> None:
    st.markdown(
        '<div style="max-width:1200px; margin:0 auto; padding:56px 48px 0;">',
        unsafe_allow_html=True,
    )
    eyebrow("PLATFORM WALKTHROUGH")
    st.markdown(
        '<h2 style="font-family:\'Fraunces\',serif; font-size:22px; font-weight:300; '
        'color:#0a1628; margin:4px 0 8px;">Five steps from data to decision</h2>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="font-family:\'Plus Jakarta Sans\',sans-serif; font-size:13px; '
        'color:#6B7280; margin-bottom:32px;">Upload your data or load a demo scenario. '
        'The platform handles the rest.</p>',
        unsafe_allow_html=True,
    )

    steps = [
        ("01", "Load your data", "Connect HR data via file upload or direct HRIS integration. "
         "Demo mode provides three pre-built organizations — no upload required."),
        ("02", "Understand your organization", "EIBO calculates Impact Scores for every employee, "
         "maps your collaboration network, and identifies concentration risks in minutes."),
        ("03", "Set budget targets", "Move the budget slider to explore scenarios. "
         "The optimizer instantly recalculates retention recommendations."),
        ("04", "Apply human judgment", "Override any suggestion, add context annotations, "
         "and protect employees by name. Every human decision is logged."),
        ("05", "Export and act", "Generate boardroom-ready reports, share scenarios with "
         "stakeholders, and track decisions over time in the audit trail."),
    ]

    cols = st.columns(5)
    for col, (num, title, body) in zip(cols, steps):
        with col:
            st.markdown(
                f"""
                <div style="background:#fff; border-radius:12px; padding:20px;
                            box-shadow:0 1px 4px rgba(0,51,102,0.08); height:100%;">
                  <div style="font-family:'Fraunces',serif; font-size:40px;
                              font-weight:300; color:#f1f5f9; line-height:1; margin-bottom:4px;">
                    {num}
                  </div>
                  <div style="width:28px; height:3px; background:#C8982A; border-radius:2px; margin:6px 0 12px;"></div>
                  <div style="font-family:'Fraunces',serif; font-size:14px; font-weight:400;
                              color:#0a1628; margin-bottom:8px;">{title}</div>
                  <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:12px;
                              color:#475569; line-height:1.7;">{body}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Key concepts
# ---------------------------------------------------------------------------

def _render_key_concepts() -> None:
    st.markdown(
        '<div style="max-width:1200px; margin:0 auto; padding:56px 48px 0;">',
        unsafe_allow_html=True,
    )
    section_divider()
    eyebrow("KEY CONCEPTS")
    st.markdown(
        '<h2 style="font-family:\'Fraunces\',serif; font-size:22px; font-weight:300; '
        'color:#0a1628; margin:4px 0 8px;">What does EIBO actually measure?</h2>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="font-family:\'Plus Jakarta Sans\',sans-serif; font-size:13px; '
        'color:#6B7280; margin-bottom:32px;">Four core concepts that power every recommendation.</p>',
        unsafe_allow_html=True,
    )

    # Concept 1: Impact Score
    col1, col2 = st.columns([1, 1], gap="large")
    with col1:
        st.markdown(
            """
            <div style="padding-top:24px;">
              <div style="font-family:'Fraunces',serif; font-size:17px; font-weight:400;
                          color:#0a1628; margin-bottom:12px;">Impact Score</div>
              <p style="font-family:'Plus Jakarta Sans',sans-serif; font-size:13px;
                        color:#475569; line-height:1.75;">
                A 0–100 composite score that answers: <em>how much would this organization
                feel the absence of this person?</em>
              </p>
              <p style="font-family:'Plus Jakarta Sans',sans-serif; font-size:13px;
                        color:#475569; line-height:1.75;">
                It combines performance history, collaboration influence, skill uniqueness,
                and replacement difficulty — each weighted by what matters most in your organization.
                Unlike a simple performance rating, Impact Score captures network effects and
                knowledge concentration that traditional HR systems miss.
              </p>
              <div style="background:#E0EAF4; border-radius:8px; padding:14px 16px; margin-top:16px;
                          border-left:3px solid #C8982A;">
                <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:9px;
                            font-weight:700; letter-spacing:1.5px; text-transform:uppercase;
                            color:#C8982A; margin-bottom:5px;">EXAMPLE</div>
                <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:12.5px;
                            color:#475569; line-height:1.65;">
                  A mid-level engineer with Impact Score 82 outranks a director with Score 61
                  because they are the sole expert in a critical system used by 8 teams.
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.plotly_chart(impact_score_breakdown_chart(), use_container_width=True)

    section_divider()

    # Concept 2: Nexus Employees
    col1, col2 = st.columns([1, 1], gap="large")
    with col1:
        st.plotly_chart(collaboration_network_example(), use_container_width=True)
    with col2:
        st.markdown(
            """
            <div style="padding-top:24px;">
              <div style="font-family:'Fraunces',serif; font-size:17px; font-weight:400;
                          color:#0a1628; margin-bottom:12px;">Nexus Employees</div>
              <p style="font-family:'Plus Jakarta Sans',sans-serif; font-size:13px;
                        color:#475569; line-height:1.75;">
                Some people are bridges. They connect teams that would otherwise operate in silos.
                EIBO maps every collaboration relationship and identifies employees whose departure
                would fragment your organization's knowledge flow.
              </p>
              <p style="font-family:'Plus Jakarta Sans',sans-serif; font-size:13px;
                        color:#475569; line-height:1.75;">
                A Nexus badge doesn't mean "most popular" — it means "critical connector."
                These are often overlooked by traditional performance systems because their
                value is relational, not just transactional.
              </p>
              <div style="display:inline-flex; align-items:center; gap:8px; margin-top:12px;
                          background:#FEF0E6; border-radius:20px; padding:6px 16px;">
                <span style="width:8px; height:8px; background:#F07020; border-radius:50%;
                             display:inline-block;"></span>
                <span style="font-family:'Plus Jakarta Sans',sans-serif; font-size:10px;
                             font-weight:500; color:#7A3800;">NEXUS EMPLOYEE</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    section_divider()

    # Concept 3: Budget Optimization
    col1, col2 = st.columns([1, 1], gap="large")
    with col1:
        st.markdown(
            """
            <div style="padding-top:24px;">
              <div style="font-family:'Fraunces',serif; font-size:17px; font-weight:400;
                          color:#0a1628; margin-bottom:12px;">Budget Optimization</div>
              <p style="font-family:'Plus Jakarta Sans',sans-serif; font-size:13px;
                        color:#475569; line-height:1.75;">
                EIBO uses mathematical optimization to find the best possible retention strategy
                within your budget constraints. It's not a ranking — it's a system of equations
                that respects real organizational rules simultaneously.
              </p>
              <p style="font-family:'Plus Jakarta Sans',sans-serif; font-size:13px;
                        color:#475569; line-height:1.75;">
                The engine ensures every team retains at least one leader, that critical skills
                are preserved across the organization, and that diversity thresholds are maintained —
                all while maximizing aggregate impact within the available budget.
              </p>
              <p style="font-family:'Plus Jakarta Sans',sans-serif; font-size:13px;
                        color:#475569; line-height:1.75;">
                If there's no feasible solution at a given budget, EIBO tells you exactly which
                constraints are in conflict and suggests how to resolve them.
              </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.plotly_chart(sample_performance_trend(), use_container_width=True)

    section_divider()

    # Concept 4: Human-in-the-Loop
    col1, col2 = st.columns([1, 1], gap="large")
    with col1:
        st.plotly_chart(decision_flow_diagram(), use_container_width=True)
    with col2:
        st.markdown(
            """
            <div style="padding-top:24px;">
              <div style="font-family:'Fraunces',serif; font-size:17px; font-weight:400;
                          color:#0a1628; margin-bottom:12px;">Human-in-the-Loop</div>
              <p style="font-family:'Plus Jakarta Sans',sans-serif; font-size:13px;
                        color:#475569; line-height:1.75;">
                EIBO's most important design principle: the machine informs, people decide.
                Every suggestion can be overridden. Every override is logged with a reason.
                The audit trail is immutable and available for compliance review.
              </p>
              <p style="font-family:'Plus Jakarta Sans',sans-serif; font-size:13px;
                        color:#475569; line-height:1.75;">
                When a manager marks an employee as "Force Retain" with an annotation like
                "Critical project delivery until Q3," the optimizer recalculates the entire
                scenario around that constraint — and shows you the cascade effects.
              </p>
              <div style="background:#E0F7EF; border-radius:8px; padding:14px 16px; margin-top:16px;
                          border-left:3px solid #27B97C;">
                <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:9px;
                            font-weight:700; letter-spacing:1.5px; text-transform:uppercase;
                            color:#27B97C; margin-bottom:5px;">CORE PRINCIPLE</div>
                <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:12.5px;
                            color:#475569; line-height:1.65;">
                  Behind every data point is a person with a career. EIBO treats both
                  with the same level of care.
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Use cases
# ---------------------------------------------------------------------------

def _render_use_cases() -> None:
    st.markdown(
        '<div style="max-width:1200px; margin:0 auto; padding:56px 48px 0;">',
        unsafe_allow_html=True,
    )
    section_divider()
    eyebrow("USE CASES")
    st.markdown(
        '<h2 style="font-family:\'Fraunces\',serif; font-size:22px; font-weight:300; '
        'color:#0a1628; margin:4px 0 8px;">Designed for real organizational challenges</h2>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="font-family:\'Plus Jakarta Sans\',sans-serif; font-size:13px; '
        'color:#6B7280; margin-bottom:32px;">Three scenarios where EIBO delivers measurable value.</p>',
        unsafe_allow_html=True,
    )

    use_cases = [
        {
            "icon": "📈",
            "title": "Hypergrowth Cost Control",
            "scenario": "Engineering budget exceeded target by 25%. Leadership needs to reduce "
                        "headcount costs without losing the 3 engineers who own critical architecture.",
            "eibo_action": "EIBO identifies the nexus engineers, models 12 budget scenarios in seconds, "
                           "and surfaces a path that meets the cost target while protecting every "
                           "critical knowledge holder.",
            "outcome": "20% cost reduction. Zero critical knowledge loss. Decision logged in 4 hours.",
            "badge_text": "Scenario A — Growing",
            "badge_color": "blue",
        },
        {
            "icon": "🔄",
            "title": "Restructuring with Fairness",
            "scenario": "Board mandates 20% cost reduction across all departments. "
                        "Multiple teams are over budget. Skills redundancy exists in legacy systems "
                        "while critical modern skills are scarce.",
            "eibo_action": "EIBO runs a fairness audit across demographic groups, identifies the "
                           "4 employees with unique RegTech expertise as 'protected', and optimizes "
                           "the remaining structure against the budget constraint.",
            "outcome": "22% cost reduction achieved. Diversity metrics preserved. "
                       "4 critical skill holders retained in all scenarios.",
            "badge_text": "Scenario B — Restructuring",
            "badge_color": "orange",
        },
        {
            "icon": "🤝",
            "title": "Merger Integration",
            "scenario": "Two organizations merged 6 months ago. Duplicate roles in every department. "
                        "Cultural friction. Combined headcount is 38% above target.",
            "eibo_action": "EIBO maps the collaboration networks of both legacy organizations, "
                           "identifies which duplicate roles are actually complementary vs. truly "
                           "redundant, and proposes a consolidation that preserves both cultures' "
                           "institutional knowledge.",
            "outcome": "35% headcount consolidation. HIPAA expertise protected. "
                       "Both legacy CTO-equivalents given clear differentiated roles.",
            "badge_text": "Scenario C — Merger",
            "badge_color": "purple",
        },
    ]

    cols = st.columns(3, gap="medium")
    for col, uc in zip(cols, use_cases):
        with col:
            badge_colors = {"blue": "#001F4D", "orange": "#7A3800", "purple": "#3D1F70"}
            badge_bgs = {"blue": "#E0EAF4", "orange": "#FEF0E6", "purple": "#F0EBF9"}
            badge_c = uc["badge_color"]
            st.markdown(
                f"""
                <div style="background:#fff; border-radius:12px; padding:24px;
                            box-shadow:0 1px 4px rgba(0,51,102,0.08); height:100%;
                            border-top:3px solid #C8982A;">
                  <div style="font-size:28px; margin-bottom:12px;">{uc['icon']}</div>
                  <div style="display:inline-block; font-family:'Plus Jakarta Sans',sans-serif;
                              font-size:9px; font-weight:500; letter-spacing:1.5px;
                              text-transform:uppercase; color:{badge_colors[badge_c]};
                              background:{badge_bgs[badge_c]}; border-radius:20px;
                              padding:4px 12px; margin-bottom:12px;">
                    {uc['badge_text']}
                  </div>
                  <div style="font-family:'Fraunces',serif; font-size:15px; font-weight:400;
                              color:#0a1628; margin-bottom:10px;">{uc['title']}</div>
                  <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:12px;
                              color:#475569; line-height:1.7; margin-bottom:12px;">
                    <strong>Situation:</strong> {uc['scenario']}
                  </div>
                  <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:12px;
                              color:#475569; line-height:1.7; margin-bottom:12px;">
                    <strong>How EIBO helps:</strong> {uc['eibo_action']}
                  </div>
                  <div style="background:#E0F7EF; border-radius:6px; padding:10px 14px;
                              border-left:3px solid #27B97C;">
                    <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:11px;
                                color:#0D5C3A; line-height:1.6;">
                      ✓ {uc['outcome']}
                    </div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# ROI Calculator
# ---------------------------------------------------------------------------

def _render_roi_calculator() -> None:
    st.markdown(
        '<div style="max-width:1200px; margin:0 auto; padding:56px 48px 0;">',
        unsafe_allow_html=True,
    )
    section_divider()
    eyebrow("ROI CALCULATOR")
    st.markdown(
        '<h2 style="font-family:\'Fraunces\',serif; font-size:22px; font-weight:300; '
        'color:#0a1628; margin:4px 0 8px;">Estimate the value for your organization</h2>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="font-family:\'Plus Jakarta Sans\',sans-serif; font-size:13px; '
        'color:#6B7280; margin-bottom:32px;">Conservative assumptions. Adjust to your context.</p>',
        unsafe_allow_html=True,
    )

    col_inputs, col_results = st.columns([1, 1], gap="large")

    with col_inputs:
        n_employees = st.slider("Total employees", 50, 10_000, 500, step=50)
        avg_salary = st.slider("Average annual salary ($)", 50_000, 250_000, 100_000, step=5_000)
        target_reduction = st.slider("Budget reduction target (%)", 5, 40, 15)
        attrition_rate = st.slider("Annual voluntary attrition rate (%)", 5, 35, 12)
        replacement_cost_multiplier = st.slider(
            "Replacement cost (× annual salary)", 0.5, 2.0, 0.8, step=0.1,
            help="Industry average: 0.5–2× salary including hiring, onboarding, productivity ramp."
        )

    with col_results:
        total_payroll = n_employees * avg_salary
        savings_target = total_payroll * target_reduction / 100
        attrition_cost = n_employees * (attrition_rate / 100) * avg_salary * replacement_cost_multiplier
        avoidable_attrition_pct = 0.30
        savings_from_retention = attrition_cost * avoidable_attrition_pct
        decision_speed_days_saved = 18
        analyst_cost_per_day = 800
        speed_savings = decision_speed_days_saved * analyst_cost_per_day * 4
        total_annual_value = savings_from_retention + speed_savings

        st.markdown(
            f"""
            <div style="background:#003366; border-radius:12px; padding:32px;
                        background-image: linear-gradient(rgba(255,255,255,.025) 1px, transparent 1px),
                        linear-gradient(90deg, rgba(255,255,255,.025) 1px, transparent 1px);
                        background-size: 48px 48px;">
              <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:9px;
                          font-weight:700; letter-spacing:4px; text-transform:uppercase;
                          color:rgba(255,255,255,0.35); margin-bottom:24px;">
                ESTIMATED ANNUAL VALUE
              </div>
              <div style="display:flex; flex-direction:column; gap:20px;">
                <div style="border-left:2px solid #C8982A; padding-left:18px;">
                  <div style="font-family:'Fraunces',serif; font-size:32px;
                              font-weight:300; color:#E8C46A; line-height:1; margin-bottom:6px;">
                    ${savings_target:,.0f}
                  </div>
                  <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:12px;
                              color:rgba(255,255,255,0.5);">Budget reduction target</div>
                </div>
                <div style="border-left:2px solid #C8982A; padding-left:18px;">
                  <div style="font-family:'Fraunces',serif; font-size:32px;
                              font-weight:300; color:#E8C46A; line-height:1; margin-bottom:6px;">
                    ${savings_from_retention:,.0f}
                  </div>
                  <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:12px;
                              color:rgba(255,255,255,0.5);">
                    Avoidable attrition cost savings
                    <br>(30% of at-risk exits prevented)
                  </div>
                </div>
                <div style="border-left:2px solid #27B97C; padding-left:18px;">
                  <div style="font-family:'Fraunces',serif; font-size:32px;
                              font-weight:300; color:#27B97C; line-height:1; margin-bottom:6px;">
                    ${total_annual_value:,.0f}
                  </div>
                  <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:12px;
                              color:rgba(255,255,255,0.5);">
                    Total estimated annual value
                  </div>
                </div>
              </div>
              <div style="margin-top:20px; font-family:'Plus Jakarta Sans',sans-serif;
                          font-size:10px; color:rgba(255,255,255,0.3); line-height:1.6;">
                Methodology: Attrition cost = employees × rate × salary × replacement multiplier.
                30% of voluntary exits assumed preventable with early intervention.
                Speed savings: 18 analyst-days per decision cycle × 4 cycles/year.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Glossary
# ---------------------------------------------------------------------------

def _render_glossary() -> None:
    st.markdown(
        '<div style="max-width:1200px; margin:0 auto; padding:56px 48px 0;">',
        unsafe_allow_html=True,
    )
    section_divider()
    eyebrow("METRICS GLOSSARY")
    st.markdown(
        '<h2 style="font-family:\'Fraunces\',serif; font-size:22px; font-weight:300; '
        'color:#0a1628; margin:4px 0 32px;">Plain-language definitions for every KPI</h2>',
        unsafe_allow_html=True,
    )

    terms = [
        ("Impact Score", "0–100 composite score measuring the organizational value of an individual. "
         "Combines performance trajectory, collaboration centrality, skill uniqueness, and replacement difficulty."),
        ("Nexus Employee", "A person whose departure would significantly fragment your collaboration network. "
         "Identified by betweenness centrality — how many shortest paths between colleagues pass through them."),
        ("Suggested Retention", "Model output: this person should be prioritized for retention under "
         "the current budget constraint. Not a performance judgment — a system impact assessment."),
        ("Not Retained in Simulation", "Model output: at the current budget target, this person is "
         "not in the optimizer's recommended retention set. Always subject to human override."),
        ("Attrition Risk", "Probability (0–100%) that an employee will voluntarily leave within "
         "12 months. Derived from compensation ratio, performance trend, network isolation signals, "
         "and engagement indicators."),
        ("Team Fragility", "A 0–100 score measuring how dependent a team is on a small number "
         "of critical individuals. Teams with Fragility > 70 are flagged for succession planning."),
        ("Available Budget", "The target annual spend against which the optimization runs. "
         "Adjusted via the simulation slider."),
        ("Monte Carlo Simulation", "A statistical technique that runs thousands of budget scenarios "
         "with random variation to show the range of likely outcomes — not just a single forecast."),
        ("Override", "A human decision that changes the model's suggestion for a specific employee. "
         "Requires a written reason and is permanently logged in the audit trail."),
        ("Pareto Frontier", "The set of optimal solutions where improving retention quality "
         "requires increasing the budget. EIBO shows you this frontier so you can make "
         "an informed trade-off."),
    ]

    for i in range(0, len(terms), 2):
        cols = st.columns(2, gap="medium")
        for col, (term, definition) in zip(cols, terms[i:i+2]):
            with col:
                st.markdown(
                    f"""
                    <div style="background:#fff; border-radius:10px; padding:20px 24px;
                                box-shadow:0 1px 3px rgba(0,51,102,0.07); margin-bottom:12px;
                                border-left:3px solid #C8982A;">
                      <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:9px;
                                  font-weight:700; letter-spacing:1.5px; text-transform:uppercase;
                                  color:#C8982A; margin-bottom:5px;">TERM</div>
                      <div style="font-family:'Fraunces',serif; font-size:14px; font-weight:400;
                                  color:#0a1628; margin-bottom:6px;">{term}</div>
                      <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:12.5px;
                                  color:#475569; line-height:1.65;">{definition}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# FAQ
# ---------------------------------------------------------------------------

def _render_faq() -> None:
    st.markdown(
        '<div style="max-width:1200px; margin:0 auto; padding:56px 48px;">',
        unsafe_allow_html=True,
    )
    section_divider()
    eyebrow("FAQ")
    st.markdown(
        '<h2 style="font-family:\'Fraunces\',serif; font-size:22px; font-weight:300; '
        'color:#0a1628; margin:4px 0 32px;">Common questions from HR and Finance</h2>',
        unsafe_allow_html=True,
    )

    faqs = [
        ("Is EIBO making the final decision?",
         "Never. EIBO generates recommendations. Every suggestion can be overridden with a "
         "written reason. The platform is a decision support tool — all final decisions remain "
         "with your leadership team, and every decision is logged in an immutable audit trail."),
        ("What data does EIBO need?",
         "At minimum: employee records (name, role, salary, department, hire date) and team structure. "
         "Optional but valuable: performance history, skills inventory, and collaboration data from "
         "your HRIS. Demo mode requires no data upload."),
        ("Does any data leave our organization?",
         "No. EIBO runs entirely on your infrastructure (Docker Compose, on-premises or private cloud). "
         "No data is sent to external services. Salary and PII data never leave your environment."),
        ("How does EIBO handle employee privacy?",
         "Access is role-based. Salary data is masked or hidden based on user permissions. "
         "PII is protected at the data layer. The system follows GDPR data processing principles "
         "and generates compliance reports on request."),
        ("Can we use EIBO without historical performance data?",
         "Yes. EIBO uses weighted heuristics as a fallback when historical data is absent. "
         "The Impact Score still calculates using tenure, role seniority, collaboration data, "
         "and skills inventory. Accuracy improves with more historical data."),
        ("How do we explain a suggestion to an affected employee?",
         "EIBO generates plain-language explanations for every recommendation, grounded in the "
         "contributing factors (skills, performance, network centrality). We strongly recommend "
         "pairing any EIBO output with direct human conversation — the platform provides context, "
         "not verdicts."),
        ("What if the optimization finds no solution?",
         "EIBO shows which constraints are in conflict (e.g., 'Budget cannot be met while preserving "
         "all critical skill holders') and suggests resolution paths: increase budget by X, relax "
         "constraint Y, or protect fewer employees. It never returns a silent failure."),
        ("How long does implementation take?",
         "Demo mode is immediate — one click. Production setup with Docker Compose takes under "
         "30 minutes for a technical team. Full HRIS integration depends on your connector "
         "configuration (typically 1–3 days with our pre-built connectors for Workday, "
         "SuccessFactors, and BambooHR)."),
    ]

    for q, a in faqs:
        with st.expander(q):
            st.markdown(
                f'<p style="font-family:\'Plus Jakarta Sans\',sans-serif; font-size:13px; '
                f'color:#475569; line-height:1.75;">{a}</p>',
                unsafe_allow_html=True,
            )

    st.markdown("</div>", unsafe_allow_html=True)
