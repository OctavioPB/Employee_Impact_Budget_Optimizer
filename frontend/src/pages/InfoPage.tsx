import React, { useState } from 'react'
import Eyebrow from '../components/Eyebrow'

interface InfoPageProps {
  onLaunch: () => void
}

type InfoTab = 'business' | 'engineering'

// ── Shared styles ────────────────────────────────────────────────────────

const hero: React.CSSProperties = {
  backgroundColor: 'var(--primary)',
  backgroundImage: `
    linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px)
  `,
  backgroundSize: '48px 48px',
  padding:        '48px 48px 0',
}

const heroInner: React.CSSProperties = {
  maxWidth: 'var(--max-width-content)',
  margin:   '0 auto',
}

const body: React.CSSProperties = {
  backgroundColor: 'var(--light)',
  minHeight:       '60vh',
}

const section: React.CSSProperties = {
  maxWidth: 'var(--max-width-content)',
  margin:   '0 auto',
  padding:  '56px 48px',
}

const card: React.CSSProperties = {
  backgroundColor: 'var(--white)',
  borderRadius:    'var(--radius-md)',
  padding:         '28px',
  boxShadow:       'var(--shadow-card)',
  border:          '1px solid var(--primary-10)',
}

const grid2: React.CSSProperties = {
  display:             'grid',
  gridTemplateColumns: '1fr 1fr',
  gap:                 24,
}

const divider: React.CSSProperties = {
  height:     1,
  background: 'var(--primary-10)',
  margin:     '48px 0',
}

// ── Sub-components ───────────────────────────────────────────────────────

function KpiStat({ value, label }: { value: string; label: string }) {
  return (
    <div style={{ borderLeft: '2px solid var(--gold)', paddingLeft: 18 }}>
      <div style={{ fontFamily: 'var(--fd)', fontSize: 34, fontWeight: 300, color: 'var(--gold-light)', lineHeight: 1, marginBottom: 8 }}>
        {value}
      </div>
      <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'rgba(255,255,255,0.5)', lineHeight: 1.55 }}>
        {label}
      </div>
    </div>
  )
}

function PainCard({ title, body: b }: { title: string; body: string }) {
  return (
    <div style={{ ...card, borderLeft: '3px solid var(--status-red)', padding: '20px 22px' }}>
      <div style={{ fontFamily: 'var(--fd)', fontSize: 15, fontWeight: 400, color: 'var(--dark)', marginBottom: 8 }}>{title}</div>
      <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: '#475569', lineHeight: 1.75, margin: 0 }}>{b}</p>
    </div>
  )
}

function CapabilityCard({
  num, title, pain, what, matters, limit,
}: {
  num: number; title: string; pain: string; what: string; matters: string; limit?: string
}) {
  return (
    <div style={{ ...card, display: 'flex', flexDirection: 'column', gap: 0 }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 18, marginBottom: 16 }}>
        <div style={{ fontFamily: 'var(--fd)', fontSize: 40, fontWeight: 300, color: 'var(--primary-30)', lineHeight: 1, flexShrink: 0, marginTop: 2 }}>
          {num}
        </div>
        <div>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--status-red)', marginBottom: 5, opacity: 0.85 }}>
            Pain resolved
          </div>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 12, color: '#475569', lineHeight: 1.6, margin: '0 0 10px', fontStyle: 'italic' }}>{pain}</p>
          <div style={{ fontFamily: 'var(--fd)', fontSize: 17, fontWeight: 400, color: 'var(--dark)' }}>{title}</div>
        </div>
      </div>
      <div style={{ width: 32, height: 2, background: 'var(--gold)', borderRadius: 2, marginBottom: 14 }} />
      <div style={{ fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--mid)', marginBottom: 6 }}>What it does</div>
      <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: '#334155', lineHeight: 1.8, margin: '0 0 16px' }}>{what}</p>
      <div style={{ fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--mid)', marginBottom: 6 }}>Why it matters</div>
      <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: '#334155', lineHeight: 1.8, margin: 0 }}>{matters}</p>
      {limit && (
        <p style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', lineHeight: 1.6, margin: '14px 0 0', fontStyle: 'italic', borderTop: '1px solid var(--primary-10)', paddingTop: 12 }}>
          Limitation: {limit}
        </p>
      )}
    </div>
  )
}

// ── Business View ────────────────────────────────────────────────────────

function BusinessView() {
  return (
    <div style={body}>
      <div style={section}>

        {/* ── Where workforce planning breaks down ── */}
        <Eyebrow>The Problem</Eyebrow>
        <h2 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--dark)', marginBottom: 8 }}>
          Where current workforce planning breaks down.
        </h2>
        <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: '#475569', maxWidth: 680, lineHeight: 1.8, marginBottom: 36 }}>
          Most organizations manage workforce cost through spreadsheets, HRIS exports, and finance models that treat headcount as a line item. These tools are adequate for steady-state reporting. They are not adequate when cost pressure demands decisions about which roles and people represent the highest organizational value — and which carry the highest risk if lost.
        </p>

        <div style={grid2}>
          <PainCard
            title="Budget cuts default to salary, not value"
            body="Without a systematic measure of organizational impact, cost reduction decisions fall back on annual salary as a proxy for contribution. This consistently undervalues employees whose importance is structural — those who connect teams, hold rare skills, or sit on critical knowledge paths — and overvalues tenure as a signal of indispensability." />
          <PainCard
            title="Attrition risk surfaces after resignation"
            body="Exit interviews and offboarding surveys arrive after the decision is irreversible. There is no standard mechanism to identify who is likely to leave before they hand in notice. High-impact departures are therefore treated as surprises rather than addressable risks with a probability and a lead time." />
          <PainCard
            title="Collaboration dependencies are invisible in org charts"
            body="Formal reporting structures capture hierarchy, not information flow. The employee who informally connects two departments, resolves cross-team friction, or acts as the primary knowledge broker for a technical domain does not appear in a headcount report. Their departure fragments teams in ways that become visible only after the fact." />
          <PainCard
            title="Scenario modeling takes days and produces one answer"
            body="A single 'what does a 12% budget reduction look like for Engineering?' analysis built in a spreadsheet takes an analyst two to three days, introduces manual error, and produces a single result with no sensitivity analysis. When assumptions change — as they always do — the analysis must restart from scratch." />
          <PainCard
            title="Budget forecasts carry no uncertainty"
            body="HR submits a payroll projection. Finance plans against it as though it were a certainty. There is no confidence interval, no stress test, and no quantification of how much that number is likely to shift due to attrition variance, salary inflation, or seasonal cost patterns." />
          <PainCard
            title="Workforce decisions lack documented justification"
            body="In regulated industries and in organizations subject to employment law, a decision that results in someone not being retained carries legal and compliance exposure unless it has a data-supported, role-appropriate, documented rationale. Most current processes cannot provide this at the individual level." />
          <PainCard
            title="Institutional knowledge has no inventory"
            body="When a senior engineer or domain specialist leaves, the organization often discovers only afterward which processes, client relationships, system behaviors, and undocumented decisions lived exclusively in that person's head. Knowledge transfer is treated as an offboarding task rather than a continuous risk management practice." />
          <PainCard
            title="Pay equity gaps are discovered in litigation, not analysis"
            body="Compensation disparities by gender, age bracket, or tenure cohort that are not explained by role, seniority, or performance are a structural and legal risk. Most organizations have no mechanism to surface these gaps systematically before they become complaints or regulatory inquiries." />
          <PainCard
            title="Disengagement accumulates in the background, invisible until departure"
            body="Behavioral signals — declining calendar density, reduced cross-team interaction, increasing after-hours work — change gradually weeks or months before formal disengagement or resignation. Without continuous signal monitoring, these patterns become visible only in retrospect." />
          <PainCard
            title="Workforce decisions are made in silos, then announced"
            body="Budget decisions that affect multiple teams are frequently made in sequence by separate stakeholders with no shared view of assumptions, constraints, or conflicts. The deliberation happens informally, the rationale is not captured, and the outcome cannot be reconstructed or defended after the fact." />
        </div>

        <div style={divider} />

        {/* ── Capability deep-dive ── */}
        <Eyebrow>Platform Capabilities</Eyebrow>
        <h2 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--dark)', marginBottom: 8 }}>
          Seventeen capabilities, each addressing a specific failure mode.
        </h2>
        <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: '#475569', maxWidth: 680, lineHeight: 1.8, marginBottom: 36 }}>
          The platform does not replace workforce judgment. It structures the information on which that judgment depends — making implicit assumptions explicit, quantifying risks that are currently described qualitatively, and creating a documented record of how decisions were reached.
        </p>

        <div style={grid2}>
          <CapabilityCard
            num={1}
            title="Impact Scoring"
            pain="Cost decisions are made without a systematic measure of who generates disproportionate organizational value."
            what="Every employee receives a composite 0–100 impact score built from four independently weighted inputs: KPI performance percentile relative to role and seniority, collaboration network centrality (how frequently the employee sits on the shortest path between other employees in the actual information flow graph), skill criticality (rarity of the employee's primary skills across the current workforce), and estimated replacement cost incorporating time-to-fill and ramp period. The score is recomputed whenever underlying data is refreshed."
            matters="The score makes the cost-versus-value trade-off explicit at the individual level. A $140K employee with a score of 88 and a $95K employee with a score of 31 are not equivalent budget line items, even though the salary gap might suggest otherwise. This shifts the conversation from 'how much does this person cost?' to 'what does it cost the organization if this person leaves?'"
            limit="The score reflects data at a point in time. A recent promotion, a performance improvement plan, or a role transfer will not be reflected until the next scoring cycle. It is a signal, not a ground truth." />

          <CapabilityCard
            num={2}
            title="Budget Optimization"
            pain="There is no systematic way to identify which combination of retention decisions maximizes organizational impact within a given budget constraint."
            what="An Integer Linear Programming solver (PuLP/CBC) takes a budget target and returns the allocation of retained versus not-retained employees that maximizes total impact score within the constraint. Three hard constraints are enforced by default: the total retained payroll cannot exceed the budget ceiling, every team must retain at least one leadership-tier employee, and every critical skill in the org must remain covered by at least one retained employee. The optimization solves in under two seconds for 5,000 employees."
            matters="Manual scenario analysis produces one answer. The optimizer produces the mathematically optimal answer for any budget level and allows rapid exploration of the trade-off curve — what happens to total retained impact if you move the budget slider from 80% to 75%? The answer is available in two seconds, not two days. Every output is a starting point for human review, not a final decision."
            limit="The optimizer treats the impact score as ground truth. Errors in scoring — for example, a recently promoted employee whose score has not been refreshed — propagate directly into the optimization output. Any result that conflicts with manager judgment should trigger a score review, not an override of the manager." />

          <CapabilityCard
            num={3}
            title="Attrition Risk"
            pain="Flight risk is identified reactively, through exit interviews and resignation conversations, after the opportunity for retention intervention has passed."
            what="A gradient-boosted classifier outputs a per-employee probability (0–100%) of voluntary departure within 12 months. Input features include compensation relative to estimated market rate, performance trajectory over the prior four quarters, tenure milestone proximity (3, 5, and 10-year thresholds correlate with elevated departure probability), engagement signal proxies, and role-level market demand. SHAP (SHapley Additive exPlanations) values identify the single highest-contributing feature for each individual — the primary driver of their specific risk score."
            matters="An employee at 74% attrition risk still has a 26% chance of staying. The output is a triage signal for prioritizing retention conversations, compensation reviews, and role redesign — not a prediction of certainty. The SHAP top driver tells a manager which lever to pull: 'below-market compensation' calls for a different conversation than 'tenure milestone (5yr)' or 'limited growth trajectory.' Early-stage intervention is substantially cheaper than replacement."
            limit="The model is calibrated on historical departure patterns. In organizations that have undergone recent restructuring, the training signal may not reflect the current environment. Model accuracy should be evaluated against actual departure rates after each quarterly refresh." />

          <CapabilityCard
            num={4}
            title="Nexus Employee Identification"
            pain="Collaboration dependencies that sit outside the formal org chart are not visible until the employee who holds them leaves."
            what="The platform constructs a weighted collaboration graph from available connectivity data (calendar co-occurrence, communication metadata, shared project participation). Betweenness centrality — a graph theory measure of how frequently a node lies on the shortest path between other nodes — is computed for every employee. Employees above a 0.7 centrality threshold receive the Nexus designation. Louvain community detection independently identifies informal team clusters, which are overlaid against the formal org structure to surface misalignments."
            matters="A Nexus employee's departure does not just create a vacancy — it fragments the information flow between teams that depended on them as a connector. This fragmentation typically takes 14 to 22 months to self-repair as new relationships form. The Nexus badge makes this risk visible before it becomes a vacancy. In a budget simulation, retaining a Nexus employee who scores moderately on KPI metrics may still represent a higher-value decision than retaining a high-KPI employee who is structurally peripheral."
            limit="Centrality quality is a direct function of collaboration data coverage. Organizations without calendar or communication system integration will have centrality computed from org chart proximity, which is a weaker signal and may not reflect actual information flow patterns." />

          <CapabilityCard
            num={5}
            title="Budget Forecasting and Monte Carlo Stress Testing"
            pain="Finance receives a single payroll projection number with no uncertainty range, no seasonal breakdown, and no quantification of how much the number is likely to shift under realistic attrition scenarios."
            what="A 12-month time series forecast of total payroll cost and headcount is produced using Facebook Prophet, which decomposes the historical payroll signal into trend, annual seasonality, and quarterly seasonality components. Outputs include a point forecast and 80%/95% confidence bands at the total and department levels. Separately, 2,000 Monte Carlo simulations run each employee month-by-month, drawing attrition events from individual risk scores, applying salary inflation, adding replacement cost hits when employees depart, and overlaying seasonal cost spikes. P10, P50, and P90 percentile bands emerge from the distribution of 2,000 outcomes."
            matters="The confidence interval is the analytically important output, not the point forecast. A department whose P90 monthly spend crosses the approved budget line in month 4 has a quantified risk: 1 in 10 plausible scenarios produces an overspend before the end of Q2. The Monte Carlo overspend probability — the fraction of 2,000 simulations in which spend exceeded budget in at least one month — provides a single defensible number for a contingency reserve conversation with Finance." />

          <CapabilityCard
            num={6}
            title="Strategic Workforce Planning"
            pain="Org redesign proposals are developed in presentation software without a systematic view of actual skill coverage, replacement costs by role, or the cost difference between internal development and external hire."
            what="The Future State Designer allows modeling of proposed org structures — team consolidations, new roles, reporting line changes, department transfers — with immediate recalculation of total cost impact and headcount movement. Skills Gap Analysis inventories current skill coverage across the workforce against a defined future-state requirement set and quantifies the gap by role and seniority. Build vs. Buy analysis computes the cost differential between upskilling an existing employee and making an equivalent external hire for each identified gap, factoring in ramp time and market salary premium."
            matters="Strategic planning decisions that do not incorporate actual skill inventory, replacement cost, and coverage gap data are made on assumptions that may not hold. This module connects the design decision to the cost and talent reality before the decision is finalized — not after the hiring plan has been approved and the gaps become apparent. The output is not a recommendation; it is a cost and coverage model that leadership can use to stress-test the assumptions in a proposed redesign." />

          <CapabilityCard
            num={7}
            title="Compensation Intelligence & Pay Equity"
            pain="Salary decisions are made relative to internal precedent and budget availability, not relative to market. Structural pay gaps — those not explained by role, seniority, or performance — go unmeasured until they become retention problems or compliance events."
            what="Every employee is benchmarked against a market median derived from their role, seniority band, and department. Comp-ratio (actual salary ÷ market median) places each person on a Below Market / At Market / Above Market spectrum. An OLS regression then models salary as a function of role and seniority; the residuals identify pay gaps that cannot be explained by these legitimate factors. For below-market employees, the retention ROI calculation compares the cost of a salary correction against the estimated replacement cost if the employee departs."
            matters="Pay equity analysis surfaces structurally unexplained gaps before they escalate. The retention ROI figure gives finance a defensible basis for a targeted compensation adjustment: the cost of correction is bounded, the cost of turnover is estimated, and the comparison is visible in the same interface as the gap itself. The analysis uses synthetic proxy groups — no real demographic data is used or inferred."
            limit="Market median figures are based on synthetic salary tables keyed by role and seniority. In production, these should be replaced with actual market survey data (Radford, Mercer, Levels.fyi) for the relevant geography and industry." />

          <CapabilityCard
            num={8}
            title="Knowledge Graph & Institutional Memory"
            pain="There is no inventory of which employees hold which critical knowledge, and no mechanism to identify single points of failure before a departure makes them visible."
            what="Twenty-three knowledge domains are mapped across the workforce — ranging from legacy system architecture, production deploy runbooks, and incident response playbooks to strategic client relationships, HIPAA integration logic, and regulatory process ownership. Each domain carries a criticality weight (0–1). Every employee is assigned domains probabilistically based on their role and department. The Single-Knowledge-Holder (SKH) flag marks any domain where only one employee holds ownership. A knowledge loss score per employee sums the criticality-weighted domains that would be lost on their departure. A transfer roadmap ranks successor candidates by skill proximity, urgency, estimated transfer hours, and cost."
            matters="The knowledge graph converts an invisible organizational risk into a measurable and addressable one. An SKH designation for a domain like 'Production Deploy Runbooks' in a department with no documented succession plan is a concrete, actionable finding — not a qualitative observation. The transfer roadmap gives managers a specific starting point for knowledge distribution conversations before the risk becomes a vacancy."
            limit="Knowledge domain assignments are inferred from role and department affinity. They reflect likely ownership, not confirmed ownership. Calibration against actual employee self-assessments or manager attestation will improve signal quality." />

          <CapabilityCard
            num={9}
            title="Internal Talent Mobility"
            pain="Internal career development is managed through annual review cycles and informal conversations. The organization has no systematic view of which employees are stagnating, which roles they could grow into, and what the gap-closing cost would be."
            what="Career path suggestions are generated by computing skill-proximity between each employee's current profile and every role in the catalog. The top three lateral and upward moves are surfaced with an estimated skill gap, a development cost (at $4,000 per skill), and a projected salary change. Career stagnation detection flags employees who combine long tenure, a flat KPI trajectory over recent quarters, and below-peer-percentile compensation — a combination that correlates with elevated departure probability. Succession depth maps each leadership role against the pool of employees who are ready now, ready in six months, or ready in twelve months."
            matters="Mobility analysis shifts the retention conversation from reactive to structural. An employee flagged for stagnation is not simply a flight risk — they are someone whose current role may no longer represent appropriate scope for their tenure and performance. Knowing that a Director-level role has zero ready-now successors and one ready-in-12-months candidate is the kind of information that should drive a development investment conversation before the role becomes vacant." />

          <CapabilityCard
            num={10}
            title="Algorithmic Fairness & Bias Audit"
            pain="Model outputs that influence workforce decisions may systematically disadvantage groups defined by gender, age, or other protected characteristics, without anyone in the decision process being aware that this is happening."
            what="The fairness audit applies the EEOC 4/5ths (80%) adverse impact rule across three model outputs: impact score, attrition risk prediction, and simulated retention selection. For each (protected dimension, model output) combination, a chi-square test assesses statistical significance of group differences. A counterfactual fairness test flips each protected attribute on a sample of employees, recomputes the relevant scores, and reports the delta and 95% confidence interval. A simulation disparity analysis checks whether retaining the top-40% by impact score systematically under-selects any group."
            matters="Bias audit results do not block decisions — they inform them. A model output that fails the 4/5ths rule in a statistically significant direction is a finding that requires human review before that output is used to influence a decision. The audit surface is part of the platform, not a separate compliance process that happens after the fact. All demographic groups in the demo environment are synthetic proxies — no real demographic data is used or inferred."
            limit="Fairness analysis depends on the quality and coverage of the underlying impact score and attrition model. If the input models contain systematic errors for certain role or department clusters, those errors will propagate into the fairness output. Fixing model quality is a prerequisite for meaningful fairness interpretation." />

          <CapabilityCard
            num={11}
            title="Collaborative Decision Room"
            pain="Workforce decisions that affect multiple teams are made through a sequence of disconnected conversations, informal agreements, and presentation decks. The deliberation is not captured, conflicts between stakeholders are not formally resolved, and the final decision cannot be reconstructed or defended."
            what="A Decision Room is a structured session with a defined lifecycle: Draft → Active → Under Review → Finalized. Participants hold one of three roles — Owner, Participant, or Observer — each with scoped capabilities. When two participants mark the same employee differently (retain vs. exclude), the system detects the conflict and offers three resolution modes: last-write wins, owner decides, or a majority vote among Participants. Comment threads, proposals, and objections are attached to specific employees and preserved in a timestamped activity feed. Digital sign-off by all required participants triggers immutable finalization. The session record — every participant action, every comment, every conflict and its resolution — is retained permanently."
            matters="The Decision Room converts an informal multi-stakeholder process into a documented, auditable one. The activity log is not a byproduct — it is the primary output. A finalized session record contains everything needed to explain why a set of decisions was reached: who was in the room, what conflicts arose, how they were resolved, and who signed off." />

          <CapabilityCard
            num={12}
            title="Workforce Resilience Stress Testing"
            pain="An organization's ability to absorb the departure of key employees is assessed qualitatively and retrospectively. There is no mechanism to measure structural fragility before it is tested by an actual disruption."
            what="A six-dimension Resilience Score (0–100) is computed from skill coverage breadth, leadership succession depth, knowledge redundancy across SKH domains, collaboration network robustness, concentration of attrition risk, and team size buffer against minimum viable coverage. Five disruption scenario types can be applied: targeted departure of specific high-impact employees, a department-wide shock, competitive poaching of a role cluster, leadership vacuum from a simultaneous multi-leader departure, and a critical skill crisis. Each scenario runs a three-round cascade simulation that models which primary departures trigger secondary attrition through nexus pressure and leadership gap propagation. An intervention roadmap ranks responses by the ratio of resilience score improvement to estimated cost."
            matters="Resilience scoring gives a concrete, repeatable answer to the question 'how fragile are we?' before disruption tests the organization. The cascade amplifier analysis — which single departure would trigger the most secondary departures — identifies the specific intervention points where investment has disproportionate structural value." />

          <CapabilityCard
            num={13}
            title="Learning & Development Investment Optimizer"
            pain="L&D budget is allocated to training programs based on availability, past participation, and manager discretion rather than a systematic view of which investments would produce the highest return across the workforce."
            what="A catalog of fifteen training programs across five tracks (technical, leadership, compliance, communication, domain) defines each program's expected impact-score delta, attrition risk reduction, and proficiency gain. A per-employee learning velocity is inferred from seniority and role. An Integer Linear Programming model then assigns employees to programs — binary variables for each (employee, program) pair — to maximize total organizational return within the L&D budget ceiling. A Pareto frontier sweep shows the trade-off curve between retention investment and L&D investment as the split between them varies. Skill gap records flag any critical skill held by fewer than two employees, directly informing training prioritization."
            matters="L&D investment optimization converts a discretionary spend into a defensible allocation with a quantified expected return. The ILP result shows not just who should receive which training but what the aggregate impact-score and attrition-risk improvement looks like at any given budget level — making the conversation between HR and Finance about L&D investment one that has numbers on both sides." />

          <CapabilityCard
            num={14}
            title="Decision Narrative Engine"
            pain="Model outputs — impact scores, attrition risks, simulation results — are numbers. The conversation that needs to happen between a manager and a team member, or between an HR leader and a finance partner, requires plain language that translates those numbers into context and rationale."
            what="A local Ollama instance running mistral:7b-instruct generates plain-language explanations for four output types: an impact score explanation linking each SHAP dimension to the employee's specific profile, an attrition risk summary describing the top-contributing factors in plain terms, a three-paragraph simulation outcome narrative describing what the ILP result means for each affected team, and a manager retention conversation brief that frames a specific retention risk without exposing confidential model details. All prompts replace employee names and identifiers with anonymized role codes before reaching the LLM — zero PII is included in any prompt. A deterministic template-based fallback activates automatically when Ollama is unavailable, ensuring the endpoint always responds."
            matters="The narrative engine does not add information to the model output. It translates the same information into a form that supports a specific human conversation. A manager who sees 'attrition_risk: 78, top_driver: comp_ratio' needs different framing to have a productive conversation than one who reads 'this employee's compensation sits 18% below the estimated market rate for their role and seniority — the primary driver of their current retention risk.'"
            limit="LLM output should be reviewed before use in high-stakes conversations. The template fallback is deterministic and auditable; the Ollama output is not. In regulated environments, the deterministic fallback may be preferable to the LLM path." />

          <CapabilityCard
            num={15}
            title="Organizational Health Index"
            pain="There is no single indicator that summarizes the organization's structural health across financial, talent, knowledge, and equity dimensions simultaneously. Each function monitors its own metrics in isolation."
            what="The Organizational Health Index (OHI) is a composite score (0–100) weighted across six sub-dimensions: financial health (20%), talent risk (20%), knowledge resilience (20%), leadership pipeline depth (15%), compensation equity (15%), and collaboration density (10%). A 24-month synthetic time series with annotated organizational events provides historical context. A 6-month forward forecast extends the trend. Department-level OHI breakdowns allow cross-department comparison on each sub-dimension. A decision impact preview shows how the OHI would shift under each of four budget retention scenarios (60%, 70%, 80%, 90%). Industry benchmark bands (P25/P50/P75) frame the score against a synthetic peer distribution."
            matters="The OHI gives leadership a single defensible starting point for a board-level conversation about organizational condition. The sub-dimension breakdown prevents that single number from obscuring meaningful variation — an organization can have a high OHI overall while showing a deteriorating leadership pipeline score, which is a materially different situation than one with uniformly balanced sub-scores. The decision impact preview makes the cost of a budget cut visible not just in dollars but in organizational health terms." />

          <CapabilityCard
            num={16}
            title="Workforce Intelligence API"
            pain="Analytics that live only inside a platform interface cannot be embedded into the BI tools, dashboards, or workflows where decisions actually happen."
            what="A versioned public REST API at /api/v1/ exposes a read-only subset of EIBO analytics — dashboard KPIs, per-employee impact scores, attrition summaries, OHI scores, and budget forecasts — under Bearer token authentication. API keys are scoped to six permission levels (viewer through executive). Raw keys are shown once at creation and never stored — only a SHA-256 hash is retained. Token-bucket rate limiting (100 req/min per key) operates in-process without requiring Redis. A webhook event system delivers HMAC-SHA256 signed payloads to registered endpoints on five event types: attrition threshold crossings, impact score updates, simulation completions, OHI alerts, and notification creation. Four embeddable Web Component widgets (no framework dependency, Shadow DOM isolation) allow any HTML page to display live EIBO data with a single script tag. A Python SDK (stdlib-only) and a JavaScript ESM SDK are included."
            matters="The API layer makes EIBO data portable without making it insecure. Salary figures are withheld from keys scoped below manager tier. Webhook delivery logs are retained per endpoint. The sandbox key provides immediate access for integration testing without requiring a registration flow." />

          <CapabilityCard
            num={17}
            title="Real-Time Engagement Signal Monitoring"
            pain="Attrition risk models are built from HR system data that reflects formal decisions and recorded history. Behavioral disengagement — the pattern that typically precedes departure — is not captured in any structured system."
            what="Six behavioral engagement signals are tracked per employee at daily resolution across a 90-day window: calendar meeting density, cross-team interaction breadth, communication response latency, PTO utilization rate, after-hours work ratio, and collaboration network delta (7-day change in interaction breadth). An IsolationForest anomaly detector (contamination=0.10) identifies employees whose signal pattern is statistically unusual relative to the population. A CUSUM control chart (k=0.5, h=3.0) detects directional threshold crossings on each signal independently. Anomaly scores are used to adjust the base attrition risk estimate — an employee flagged as anomalous has their risk increased by up to 30 percentage points. A department heatmap visualizes z-scores across all signal-department combinations. The early warning feed ranks the top 15 employees by adjusted attrition risk. Full 90-day signal timelines are available for individual review."
            matters="Engagement signals extend the predictive window for attrition from the quarterly model refresh cycle to a continuous, daily-resolution view. An employee whose base attrition risk is moderate but who shows a CUSUM alert on after-hours ratio and a declining collaboration network delta may be exhibiting early disengagement that warrants a proactive conversation — weeks before that pattern would appear in a formal performance review or HRIS record."
            limit="Signal generation in the demo environment uses synthetic behavioral data derived from attrition risk and org structure parameters. In production, these signals must be sourced from calendar system APIs, communication platform metadata, and identity provider activity logs. Signal quality varies substantially by the completeness of integration coverage." />
        </div>

        <div style={divider} />

        {/* ── Decision framework ── */}
        <Eyebrow>Decision Framework</Eyebrow>
        <h2 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--dark)', marginBottom: 8 }}>
          The model informs. Every decision remains with your team.
        </h2>
        <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: '#475569', maxWidth: 680, lineHeight: 1.8, marginBottom: 28 }}>
          No output from this platform constitutes a workforce decision. Every optimization result, attrition flag, and scenario projection is a structured input to a human decision process. The override mechanism exists not as an escape valve but as a first-class feature — manager judgment that contradicts the model is captured, documented, and added to the audit record.
        </p>
        <div style={{ display: 'flex', gap: 0 }}>
          {[
            {
              step: '01',
              title: 'Connect your data',
              body: 'Integrate via the Workday, BambooHR, or SuccessFactors connectors, or upload a structured CSV export. The demo environment uses a statistically realistic synthetic workforce — no HRIS access is required to evaluate the platform.',
            },
            {
              step: '02',
              title: 'Review the baseline',
              body: 'The dashboard surfaces impact scores, attrition risk tiers, budget variance by department, Nexus employee flags, and collaboration health — all computed automatically. Every score is accompanied by its SHAP explanation, which identifies the specific features driving it.',
            },
            {
              step: '03',
              title: 'Run and override scenarios',
              body: 'Set a budget target. The optimizer returns the maximum-impact retention set in under two seconds. Any employee can be force-retained or force-excluded. Each override requires a written justification, which is appended to the immutable audit log with the user identity and timestamp.',
            },
          ].map(({ step, title, body: b }, i) => (
            <div key={step} style={{ flex: 1, padding: '28px 32px', borderLeft: i === 0 ? '3px solid var(--gold)' : '1px solid var(--primary-10)', background: 'var(--white)', borderRadius: i === 0 ? 'var(--radius-md) 0 0 var(--radius-md)' : i === 2 ? '0 var(--radius-md) var(--radius-md) 0' : 0 }}>
              <div style={{ fontFamily: 'var(--fd)', fontSize: 32, fontWeight: 300, color: 'var(--primary-30)', marginBottom: 8 }}>{step}</div>
              <div style={{ fontFamily: 'var(--fd)', fontSize: 16, fontWeight: 400, color: 'var(--dark)', marginBottom: 10 }}>{title}</div>
              <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: '#475569', lineHeight: 1.8, margin: 0 }}>{b}</p>
            </div>
          ))}
        </div>

        <div style={divider} />

        {/* ── Access and compliance ── */}
        <Eyebrow>Access Control and Audit</Eyebrow>
        <h2 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--dark)', marginBottom: 8 }}>
          Role-appropriate data, immutable audit trail.
        </h2>
        <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: '#475569', maxWidth: 680, lineHeight: 1.8, marginBottom: 28 }}>
          Workforce decisions carry legal and compliance weight. Data access is enforced at the query layer — not just the UI — so a scoped role cannot retrieve data outside their department boundary regardless of how a request is constructed. Below Manager tier, salary figures are replaced with band ranges. Every action that reads sensitive data, runs a simulation, or exports results is written to an append-only audit log.
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2, marginBottom: 28 }}>
          {[
            { role: 'Viewer',    scope: 'Own department',       perms: 'Read-only dashboard access. No simulation, no export, no salary figures.',                                                 color: 'var(--mid)' },
            { role: 'Analyst',  scope: 'Assigned departments',  perms: 'Run simulations, save scenarios, export aggregated results. Salary shown as band range. No override capability.',          color: 'var(--primary-60)' },
            { role: 'Manager',  scope: 'Own department',        perms: 'Full department access including exact salary figures. Can override model suggestions with mandatory written justification.', color: 'var(--status-blue)' },
            { role: 'Director', scope: 'Multiple departments',   perms: 'Cross-department view, strategic planning module access. Override capability across scope.',                                color: 'var(--gold)' },
            { role: 'Executive',scope: 'Org-wide',              perms: 'Full platform access excluding system administration. Can view all simulations across departments.',                        color: 'var(--status-purple)' },
            { role: 'Admin',    scope: 'System-wide',           perms: 'User provisioning, role assignment, audit log access, data pipeline controls, demo data generation.',                      color: 'var(--status-green)' },
          ].map(({ role, scope, perms, color }) => (
            <div key={role} style={{ display: 'grid', gridTemplateColumns: '110px 160px 1fr', alignItems: 'center', gap: 20, padding: '14px 20px', background: 'var(--white)', borderRadius: 8, border: '1px solid var(--primary-10)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{ width: 3, height: 24, background: color, borderRadius: 2, flexShrink: 0 }} />
                <span style={{ fontFamily: 'var(--fb)', fontSize: 11, fontWeight: 700, letterSpacing: '1px', textTransform: 'uppercase', color }}>{role}</span>
              </div>
              <span style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', fontStyle: 'italic' }}>{scope}</span>
              <span style={{ fontFamily: 'var(--fb)', fontSize: 13, color: '#475569' }}>{perms}</span>
            </div>
          ))}
        </div>
        <div style={{ ...card, borderLeft: '3px solid var(--primary-60)', padding: '20px 24px' }}>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--primary)', marginBottom: 8 }}>Audit trail</div>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: '#334155', lineHeight: 1.8, margin: 0 }}>
            Every simulation run, model override, data export, login event, and administrative action is written to an append-only audit log with user identity, role at time of action, timestamp, and a structured detail record. Logs are queryable by event category, user, outcome, and date range. Compliance report generation (GDPR data processing, access summary, model decision audit) is available directly from the platform. The override record — who overrode which model suggestion, when, and with what justification — is retained permanently and is available for regulatory review.
          </p>
        </div>

      </div>
    </div>
  )
}

// ── Engineering View ─────────────────────────────────────────────────────

function EngineeringView() {
  const mono: React.CSSProperties = {
    fontFamily:      'Courier New, monospace',
    fontSize:        11,
    lineHeight:      1.65,
    color:           '#1e293b',
    backgroundColor: '#f8fafc',
    border:          '1px solid #e2e8f0',
    borderRadius:    8,
    padding:         '18px 22px',
    overflowX:       'auto',
    whiteSpace:      'pre',
    marginBottom:    24,
  }

  const lbl: React.CSSProperties = {
    fontFamily:    'var(--fb)',
    fontSize:      9,
    fontWeight:    700,
    letterSpacing: '2px',
    textTransform: 'uppercase',
    color:         'var(--mid)',
    marginBottom:  8,
    marginTop:     20,
  }

  const algCard: React.CSSProperties = {
    ...card,
    borderLeft:   '3px solid var(--primary-60)',
    marginBottom: 20,
  }

  const algTitle: React.CSSProperties = {
    fontFamily:   'var(--fd)',
    fontSize:     17,
    fontWeight:   400,
    color:        'var(--dark)',
    marginBottom: 4,
  }

  const inlineCode: React.CSSProperties = {
    fontFamily:      'Courier New, monospace',
    fontSize:        11,
    backgroundColor: '#f1f5f9',
    border:          '1px solid #e2e8f0',
    borderRadius:    3,
    padding:         '1px 5px',
    color:           '#1e293b',
  }

  return (
    <div style={body}>
      <div style={section}>

        {/* ── 1. Architecture ── */}
        <Eyebrow>System Architecture</Eyebrow>
        <h2 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--dark)', marginBottom: 8 }}>
          Medallion pipeline → DuckDB → FastAPI → React
        </h2>
        <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: '#475569', maxWidth: 700, lineHeight: 1.8, marginBottom: 28 }}>
          All computation is local. No data leaves the Docker network. HRIS connectors write to an immutable Bronze layer; Silver applies validation and normalisation; Gold materialises impact scores, graph metrics, and aggregated views; DuckDB holds the Gold layer in-process for sub-100ms analytical queries at up to 50K employees.
        </p>

        <div style={lbl}>End-to-end data flow</div>
        <div style={mono}>{
`┌────────────────────────────────────────────────────────────────────────────┐
│  CONNECTORS  (backend/connectors/)                                         │
│  WorkdayConnector · BambooHRConnector · SuccessFactorsConnector · CSV      │
│  Protocol: REST/OData → Python dataclass → validated Pydantic model        │
└───────────────────────────────┬────────────────────────────────────────────┘
                                │  raw JSON/CSV — append-only write
                                ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  BRONZE  (backend/data/pipeline/ingestion.py)                              │
│  • Parquet partitioned by ingestion_ts — never mutated after write         │
│  • Required fields enforced: employee_id, department, salary, hire_date    │
│  • All source columns preserved verbatim                                   │
└───────────────────────────────┬────────────────────────────────────────────┘
                                │  immutable source representation
                                ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  SILVER  (backend/data/pipeline/transformation.py)                         │
│  • Null imputation, type coercion, date normalisation to ISO 8601          │
│  • Deduplication on (employee_id, effective_date) composite key            │
│  • Column taxonomy standardisation — unified department names              │
│  • PII hash: employee_id → SHA-256(id + salt) for roles < Manager         │
└───────────────────────────────┬────────────────────────────────────────────┘
                                │  clean, schema-stable records
                                ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  GOLD  (backend/data/pipeline/aggregation.py)                              │
│  • dim_employee · dim_team · fact_performance · fact_budget                │
│  • skills · employee_skills (many-to-many)                                 │
│  • ImpactScorer: 4-feature weighted sum → impact_score ∈ [0, 100]         │
│  • GraphAnalyser (NetworkX): betweenness centrality + Louvain communities  │
│  • ProphetForecaster: historical payroll → trend + seasonality components  │
│  All views loaded into DuckDB in-process database on service start         │
└───────────────────────────────┬────────────────────────────────────────────┘
                                │  DuckDB SQL — < 100ms / 50K rows
                                ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  FastAPI  (backend/main.py — uvicorn, port 8000)                           │
│  19 routers — internal /api/* and versioned public /api/v1/*               │
│  Internal: dashboard · simulation · predictive · forecast · compensation   │
│            knowledge · mobility · fairness · decision_room · resilience    │
│            ld · narrative · ohi · pulse · notifications · admin            │
│  Public v1 (Bearer auth): dashboard · impact · attrition · ohi · forecast  │
│  Infra: api_keys · webhooks (HMAC-SHA256 signed delivery)                  │
│  Auth middleware: JWT (PyJWT 2.x) + bcrypt + 6-tier RBAC                  │
│  PostgreSQL 16: users · audit_logs · simulation_history · notifications    │
└───────────────────────────────┬────────────────────────────────────────────┘
                                │  JSON/HTTP — no websockets
                                ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  React 18  (frontend/src/ — Vite 5, port 5173)                             │
│  19 pages — Zustand: demoStore · themeStore — no Redux                     │
│  Pure SVG charts — hand-coded, no chart library dependency                 │
│  CSS: inline React.CSSProperties + design token vars — no Tailwind         │
└────────────────────────────────────────────────────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
┌──────────────────────────┐   ┌────────────────────────────────────────────┐
│  Ollama (local, port 11434)│   │  External integrators (via /api/v1/)       │
│  mistral:7b-instruct       │   │  Python SDK · JS SDK · 4 Web Components    │
│  Zero PII in any prompt    │   │  Webhook fan-out to registered endpoints   │
│  Deterministic fallback    │   │  Token-bucket rate limiting (in-process)   │
│  when Ollama unavailable   │   │  HMAC-SHA256 payload signing               │
└──────────────────────────┘   └────────────────────────────────────────────┘`
        }</div>

        <div style={lbl}>Repository layout (abridged)</div>
        <div style={mono}>{
`employee-impact-budget-optimizer/
├── backend/
│   ├── main.py                        # FastAPI app, CORS, 19 router registrations
│   ├── routers/
│   │   ├── dashboard.py  simulation.py  predictive.py  forecast.py
│   │   ├── compensation.py  knowledge.py  mobility.py  fairness.py
│   │   ├── decision_room.py  resilience.py  ld.py  narrative.py
│   │   ├── ohi.py  pulse.py  notifications.py  admin.py
│   │   ├── api_keys.py  webhooks.py    # Infra — API key + webhook mgmt
│   │   └── v1.py                      # Public versioned API (/api/v1/*)
│   └── services/
│       ├── data_service.py            # DemoGenerator wrapper (lru_cache)
│       ├── compensation_service.py    # OLS pay equity, comp-ratio, ROI
│       ├── knowledge_service.py       # SKH detection, 23 domains, transfer roadmap
│       ├── mobility_service.py        # Career paths, stagnation, succession depth
│       ├── fairness_service.py        # EEOC 4/5ths, chi-square, counterfactual
│       ├── decision_room_service.py   # Session lifecycle, conflict resolution
│       ├── resilience_service.py      # 6-dim score, cascade simulation
│       ├── ld_service.py              # ILP training allocation, Pareto sweep
│       ├── narrative_service.py       # Ollama wrapper + deterministic fallback
│       ├── ohi_service.py             # 6-dimension OHI, 24-month series, benchmarks
│       ├── pulse_service.py           # IsolationForest + CUSUM + 6-signal series
│       ├── api_key_service.py         # SHA-256 hashing, token-bucket rate limiting
│       └── webhook_service.py         # HMAC-SHA256 signing, async fan-out delivery
├── sdk/
│   ├── python/eibo_client.py          # stdlib-only typed client
│   └── js/eibo-client.js              # ESM module, camelCase mapping
└── frontend/src/
    ├── App.tsx                        # Page union type + routing switch
    ├── pages/                         # 19 pages (InfoPage through PulsePage)
    ├── components/Nav.tsx             # Sticky nav — all 19 pages addressable
    ├── services/api.ts                # Typed fetch wrappers for all endpoints
    └── stores/demoStore.ts            # Zustand: scenario, size, demo flag`
        }</div>

        <div style={divider} />

        {/* ── 2. Technology stack ── */}
        <Eyebrow>Technology Stack</Eyebrow>
        <h2 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--dark)', marginBottom: 8 }}>
          Dependency choices and rationale
        </h2>
        <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: '#475569', maxWidth: 700, lineHeight: 1.8, marginBottom: 24 }}>
          Every dependency is open source with a permissive or LGPL licence. No paid APIs or SaaS services are called at runtime.
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          {[
            { layer: 'Runtime',        pkg: 'Python 3.11+',                 why: 'Match-statement RBAC dispatch; faster CPython startup vs 3.10; tomllib in stdlib.' },
            { layer: 'API',            pkg: 'FastAPI 0.111 + uvicorn',       why: 'ASGI async by default; Pydantic v2 response models with runtime type checking; auto OpenAPI docs.' },
            { layer: 'Frontend',       pkg: 'React 18 + TypeScript 5.4',     why: 'Concurrent rendering (useTransition) for heavy simulation state; strict mode + noUnusedLocals enforced.' },
            { layer: 'Build',          pkg: 'Vite 5',                        why: 'ESM-native dev server; < 300ms HMR; zero-config TypeScript; production bundle with code splitting.' },
            { layer: 'State',          pkg: 'Zustand 4',                     why: 'Flat store, no boilerplate, no context providers. demoStore (scenario/size/demo) + themeStore.' },
            { layer: 'OLAP',           pkg: 'DuckDB 0.10 (in-process)',      why: 'Columnar, vectorised engine — no network overhead. 50K-row GROUP BY in < 100ms without indexing.' },
            { layer: 'Persistence',    pkg: 'PostgreSQL 16 + psycopg2',      why: 'ACID for audit logs (append-only), user accounts, simulation history. DuckDB is read-only at runtime.' },
            { layer: 'Optimisation',   pkg: 'PuLP 2.8 + CBC solver',         why: 'Open-source LP/ILP. CBC solves 5K-variable binary problems in < 2s. GLPK swappable.' },
            { layer: 'ML',             pkg: 'XGBoost 2.0 + scikit-learn',    why: 'GBDT for attrition classification. imbalanced-learn SMOTE for minority class oversampling.' },
            { layer: 'Explainability', pkg: 'SHAP 0.45',                     why: 'TreeExplainer for XGBoost; O(TLD) complexity. Required on every prediction — not optional per design.' },
            { layer: 'Forecasting',    pkg: 'Prophet 1.1',                   why: 'Handles annual + quarterly seasonality without manual feature engineering. NumPy polyfit fallback.' },
            { layer: 'Simulation',     pkg: 'NumPy 1.26',                    why: 'Vectorised Monte Carlo draws (np.random.binomial) across 2,000 paths × N employees. Pulse signal array (90 × N × 6) also fully vectorised.' },
            { layer: 'Graph',          pkg: 'NetworkX 3.3',                  why: 'Betweenness centrality via Brandes algorithm O(VE). python-louvain for community detection.' },
            { layer: 'Anomaly',        pkg: 'scikit-learn IsolationForest',  why: 'Pulse monitoring: contamination=0.10, decision_function inverted to [0,1] anomaly score. No PyOD dependency.' },
            { layer: 'Statistics',     pkg: 'SciPy 1.12',                    why: 'OLS regression for pay equity residuals (stats.linregress). Chi-square for EEOC disparate-impact significance testing.' },
            { layer: 'Local LLM',      pkg: 'Ollama (mistral:7b-instruct)',   why: 'Decision narrative generation — zero PII in prompts. 30s hard timeout; deterministic template fallback if unavailable. No cloud API.' },
            { layer: 'HTTP client',    pkg: 'httpx 0.27',                    why: 'Async webhook fan-out delivery. Replaces requests for async contexts without adding aiohttp.' },
            { layer: 'Auth',           pkg: 'PyJWT 2.8 + bcrypt',            why: 'Stateless JWT with RS256 signing; bcrypt cost factor 12 for stored credentials.' },
            { layer: 'Containers',     pkg: 'Docker Compose 2.27',           why: 'Three-service topology: postgres / backend / frontend. No Kubernetes needed for single-node.' },
          ].map(({ layer, pkg, why }) => (
            <div key={layer} style={{ display: 'grid', gridTemplateColumns: '120px 240px 1fr', gap: 16, padding: '11px 18px', background: 'var(--white)', borderRadius: 6, border: '1px solid var(--primary-10)', alignItems: 'start' }}>
              <span style={{ fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--mid)', paddingTop: 2 }}>{layer}</span>
              <span style={{ fontFamily: 'Courier New, monospace', fontSize: 12, color: '#003366', fontWeight: 600 }}>{pkg}</span>
              <span style={{ fontFamily: 'var(--fb)', fontSize: 12, color: '#475569', lineHeight: 1.65 }}>{why}</span>
            </div>
          ))}
        </div>

        <div style={divider} />

        {/* ── 3. Algorithms ── */}
        <Eyebrow>Algorithms</Eyebrow>
        <h2 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--dark)', marginBottom: 32 }}>
          Twelve computation stages — formulas and implementation parameters
        </h2>

        {/* 3a: Impact Score */}
        <div style={algCard}>
          <div style={algTitle}>1 — Impact Score  (backend/models/impact_scorer.py)</div>
          <div style={lbl}>Composite formula</div>
          <div style={mono}>{
`impact_score_i = clamp(round(
    0.40 × kpi_percentile_i          ← percentile rank within (role, seniority_band) cohort
  + 0.30 × betweenness_norm_i        ← graph centrality, normalised 0–100
  + 0.20 × skill_criticality_i       ← rarity of primary skill across current workforce
  + 0.10 × replacement_cost_norm_i   ← (time_to_fill × daily_rate) / org_max_replacement_cost
), 0, 100)

kpi_percentile_i        = percentile_rank(kpi_score_i, cohort=(role, seniority_band))
skill_criticality_i     = 100 × (1 − count_employees_with_skill_i / total_employees)
replacement_cost_norm_i = (salary_i × 0.50 + fixed_recruit_cost) / max_replacement_cost_org

Weight vector (0.40 / 0.30 / 0.20 / 0.10) is configurable per deployment in config.yaml.
Scores are recomputed on every data refresh — not cached between sessions.`
          }</div>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: '#475569', lineHeight: 1.75, margin: '4px 0 0' }}>
            The 0.50 replacement cost multiplier covers recruiter fees, time-to-productivity ramp, and interim contractor cost. A $140K employee at impact score 88 and a $95K employee at impact score 31 are not equivalent budget line items even though the salary gap suggests otherwise — the score makes the cost-versus-structural-value trade-off explicit at the individual level.
          </p>
        </div>

        {/* 3b: ILP */}
        <div style={algCard}>
          <div style={algTitle}>2 — Budget Optimisation — Integer Linear Programme  (backend/models/budget_optimizer.py)</div>
          <div style={lbl}>Complete PuLP / CBC formulation</div>
          <div style={mono}>{
`Variables:  x_i ∈ {0, 1}  for each employee i  (1 = retained in simulation)

Maximise:   Σ_i  impact_score_i · x_i

Subject to:
  [Budget]       Σ_i  annual_cost_i · x_i  ≤  available_budget
  [Leadership]   ∀ team t:  Σ_{i ∈ t, is_leader_i = true}  x_i  ≥  1
  [Skill cover]  ∀ s ∈ critical_skills:  Σ_{i: s ∈ skills_i}  x_i  ≥  1
  [Force-keep]   ∀ i ∈ forced_retain:    x_i = 1
  [Force-out]    ∀ i ∈ forced_exclude:   x_i = 0

annual_cost_i = salary_i + benefits_loading_i
benefits_loading default = 0.25 × salary_i  (configurable)

Solver: CBC (COIN-OR Branch and Cut)
Typical solve time: < 2s for N = 5,000
LP relaxation bound reported alongside integer solution as optimality gap`
          }</div>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: '#475569', lineHeight: 1.75, margin: '4px 0 0' }}>
            Force-keep and force-exclude constraints encode manager overrides. Each override writes an audit record (user, role, timestamp, justification text) before the constraint is applied to the model. The optimality gap — the difference between the LP bound and the integer solution — is typically &lt; 0.1% for workforce-scale problems, confirming that the CBC solution is effectively optimal.
          </p>
        </div>

        {/* 3c: Attrition */}
        <div style={algCard}>
          <div style={algTitle}>3 — Attrition Risk Classifier  (backend/models/attrition_model.py)</div>
          <div style={lbl}>Training pipeline</div>
          <div style={mono}>{
`1. Feature engineering (per employee):
     comp_ratio        = salary_i / estimated_market_rate_i
     perf_slope        = OLS slope of kpi_score over last 4 quarters
     tenure_milestone  = min(|tenure_years − {3, 5, 10}|)  ← proximity to known departure peaks
     engagement_proxy  = f(calendar_density, cross_team_interaction_count)
     market_demand_idx = role-level external job posting volume (normalised 0–100)

2. Class imbalance — SMOTE (k=5 neighbours) on training split only
     Typical base attrition rate 8–15 %  →  significant skew without oversampling

3. Classifier: XGBoost 2.0
     n_estimators=400, max_depth=5, learning_rate=0.05
     subsample=0.8, colsample_bytree=0.8
     objective=binary:logistic, eval_metric=auc

4. Calibration: Platt scaling
     LogisticRegression fit on validation-fold XGBoost raw probability output
     Converts uncalibrated probability to P(voluntary departure in 12 months)

5. Explainability: SHAP TreeExplainer (mandatory)
     shap_values[i]   →  per-employee feature contribution vector
     top_driver_i     = argmax |shap_values[i]|  →  surfaced in UI alongside score
     UI will not render an attrition score without a top driver

Output: attrition_risk_i ∈ [0, 100]  (calibrated probability × 100)
Target: AUC > 0.78 on held-out test fold`
          }</div>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: '#475569', lineHeight: 1.75, margin: '4px 0 0' }}>
            The model is retrained on each quarterly data refresh. Calibration quality should be validated against observed departure rates after each cycle; the Platt scaler can drift if the base attrition rate shifts substantially due to restructuring or labour market conditions.
          </p>
        </div>

        {/* 3d: Graph */}
        <div style={algCard}>
          <div style={algTitle}>4 — Graph Analysis — Betweenness Centrality + Louvain  (backend/models/graph_analyser.py)</div>
          <div style={lbl}>Betweenness centrality (Brandes, 2001)</div>
          <div style={mono}>{
`C_B(v) = Σ_{s ≠ v ≠ t}  σ(s,t|v) / σ(s,t)

  σ(s,t)    = total shortest paths from node s to node t
  σ(s,t|v)  = shortest paths from s to t that pass through v

Implementation: NetworkX betweenness_centrality(G, normalized=True, weight='interaction_count')
Complexity: O(VE) via Brandes — feasible up to ~5,000 nodes
Edge weight: interaction_count (calendar co-occurrence volume + message volume proxy)

Normalisation to [0, 100]:
  betweenness_norm_i = C_B(i) / max(C_B) × 100

Nexus threshold: betweenness_norm_i >= 70  →  is_nexus = True

Louvain community detection (python-louvain):
  Maximises modularity  Q = Σ_c [ L_c/m − (d_c / 2m)² ]
    L_c  = edges within community c
    d_c  = sum of degrees of nodes in c
    m    = total edges in graph
  Communities overlaid against formal org structure
  Employees whose Louvain community ≠ formal department are flagged for review`
          }</div>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: '#475569', lineHeight: 1.75, margin: '4px 0 0' }}>
            Graph quality is a direct function of collaboration data coverage. With calendar and communication integration, centrality reflects actual information flow. Without it, the graph falls back to org-chart proximity (direct and second-degree reporting relationships), which undercounts real connectors and should be treated as a weaker signal.
          </p>
        </div>

        {/* 3e: Prophet */}
        <div style={algCard}>
          <div style={algTitle}>5 — Budget Forecasting — Facebook Prophet  (backend/models/forecasting.py)</div>
          <div style={lbl}>Decomposition model</div>
          <div style={mono}>{
`y(t) = trend(t) + seasonality_annual(t) + seasonality_quarterly(t) + ε(t)

trend(t):               piecewise linear with automatic changepoint detection
                        changepoint_prior_scale = 0.05  (moderate flexibility)

seasonality_annual:     Fourier series, order = 10
                        Captures year-end salary cycles, annual review periods

seasonality_quarterly:  Fourier series, order = 5  (custom — not Prophet default)
                        Captures Q1 hiring spikes, Q3 budget freeze patterns

Uncertainty intervals:
  80% CI:  yhat_lower_80 / yhat_upper_80   primary planning band
  95% CI:  yhat_lower_95 / yhat_upper_95   tail risk band
  Method:  uncertainty_samples = 1000 (Prophet internal Monte Carlo)

Input:    24 months historical payroll  →  12-month forward forecast
          Run separately per department and for org-wide total
Fallback: numpy.polyfit(degree=1) if historical data < 2 full seasonal cycles
          Fallback produces point forecast only — no confidence bands; flagged in UI

Target:   MAPE < 15% at 3-month horizon on held-out validation fold`
          }</div>
        </div>

        {/* 3f: Monte Carlo */}
        <div style={algCard}>
          <div style={algTitle}>6 — Monte Carlo Stress Test  (backend/models/monte_carlo.py)</div>
          <div style={lbl}>Simulation parameters</div>
          <div style={mono}>{
`n_simulations = 2,000  (each is an independent 12-month path)

Per simulation k, per employee i, per month m:
  departure_event_ikm ~ Bernoulli(p_i / 12)      ← monthly departure probability draw
  p_i = attrition_risk_i / 100                   ← calibrated XGBoost output

  If departure_event_ikm = 1:
    replacement_cost_im = salary_i × REPLACEMENT_MULTIPLIER + seasonal_spike_m
    REPLACEMENT_MULTIPLIER = 0.25  (configurable in monte_carlo.py)
    seasonal_spike_m:  +5% in January (Q1 hiring market), +10% in September

Monthly cost for simulation k:
  C_km = Σ_i [ (salary_i / 12) × (1 − departed_ik_cumulative) + replacement_cost_im ]

Output aggregated across 2,000 simulations:
  P10_m, P50_m, P90_m   fan chart percentile bands per month
  budget_line_m          approved monthly budget (input parameter)
  exceedance_prob_m      fraction of 2,000 simulations where C_km > budget_line_m

Implementation: fully vectorised via NumPy
  draws shape: (n_simulations, n_employees, 12)  →  np.random.binomial(1, p/12, shape)`
          }</div>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: '#475569', lineHeight: 1.75, margin: '4px 0 0' }}>
            The 0.25 replacement multiplier is conservative; literature estimates range from 0.5× (entry-level) to 2× (senior/specialist). Adjust <code style={inlineCode}>REPLACEMENT_MULTIPLIER</code> before production deployment. The exceedance probability — the fraction of 2,000 simulations where cost exceeds budget in at least one month — is the single most actionable output for a contingency reserve conversation with Finance.
          </p>
        </div>

        {/* 7: Pay Equity OLS */}
        <div style={algCard}>
          <div style={algTitle}>7 — Pay Equity Regression  (backend/services/compensation_service.py)</div>
          <div style={lbl}>OLS model and residual interpretation</div>
          <div style={mono}>{
`salary_i = β₀ + β₁·seniority_rank_i + β₂·dept_dummy_i + ε_i

  seniority_rank:   junior=0, mid=1, senior=2, lead=3, director=4, exec=5
  dept_dummy:       one-hot encoded department (k-1 dummies, reference = Engineering)
  ε_i (residual):   unexplained salary variation after controlling for seniority + dept

comp_ratio_i = salary_i / market_median(dept_i, seniority_i)
  Below Market  if comp_ratio_i < 0.85
  At Market     if 0.85 ≤ comp_ratio_i ≤ 1.15
  Above Market  if comp_ratio_i > 1.15

retention_roi_i = replacement_cost_i − correction_cost_i
  replacement_cost_i  = salary_i × 0.50 + fixed_recruit_cost
  correction_cost_i   = max(0, market_median_i − salary_i)

Implementation: scipy.stats.linregress on (seniority_rank, salary) per department
Residual ε_i > 0 → paid above expectation for cohort
Residual ε_i < 0 → paid below expectation for cohort (structural gap candidate)`
          }</div>
        </div>

        {/* 8: IsolationForest + CUSUM */}
        <div style={algCard}>
          <div style={algTitle}>8 — Engagement Anomaly Detection  (backend/services/pulse_service.py)</div>
          <div style={lbl}>IsolationForest + CUSUM control chart</div>
          <div style={mono}>{
`Signal array shape: (90 days, N employees, 6 signals)
  s₀  calendar_density_7d        meetings/week
  s₁  cross_team_interaction_7d  unique cross-dept contacts/week
  s₂  response_latency_trend     normalised latency score ∈ [0, 2.5]
  s₃  pto_utilization_rate       fraction of entitled PTO taken ∈ [0, 1]
  s₄  after_hours_ratio          fraction of activity outside 08:00–18:00 ∈ [0, 0.9]
  s₅  collaboration_network_delta 7-day change in unique contacts ∈ [−1.8, 0.3]

IsolationForest  (sklearn.ensemble.IsolationForest)
  Input:    last_day_values — shape (N, 6), last observation per employee per signal
  params:   n_estimators=100, contamination=0.10, random_state=42
  Output:   decision_function(X) → raw scores → inverted to anomaly_score ∈ [0, 1]
            score = (raw − raw.min()) / (raw.max() − raw.min())

CUSUM control chart  (vectorised NumPy)
  params:  k = 0.5  (allowance — half the expected shift magnitude)
           h = 3.0  (decision threshold — triggers alert after sustained drift)
  Upper CUSUM:  S⁺_t = max(0, S⁺_{t-1} + z_t − k)   alert if S⁺_t > h
  Lower CUSUM:  S⁻_t = max(0, S⁻_{t-1} − z_t − k)   alert if S⁻_t > h
  z_t:  z-score of signal value relative to baseline mean (days 0–69)
  Alert direction per signal: s₀,s₁,s₅ → low; s₂,s₄ → high; s₃ → both

Adjusted attrition risk:
  adjusted_risk_i = clamp(base_risk_i + anomaly_score_i × 0.30, 0, 1)`
          }</div>
        </div>

        {/* 9: EEOC Fairness */}
        <div style={algCard}>
          <div style={algTitle}>9 — Algorithmic Fairness Audit  (backend/services/fairness_service.py)</div>
          <div style={lbl}>EEOC 4/5ths rule and chi-square significance test</div>
          <div style={mono}>{
`EEOC 4/5ths (80%) adverse impact rule:
  For each (protected group g, model output m):
    selection_rate_g  = P(outcome_i > threshold | group_i = g)
    reference_rate    = max selection rate across all groups
    impact_ratio_g    = selection_rate_g / reference_rate
    adverse_impact    = impact_ratio_g < 0.80

Chi-square significance test  (scipy.stats.chi2_contingency):
  Contingency table:  rows = [above threshold, below threshold]
                      cols = [group g, all other groups]
  α = 0.05; p < α → statistically significant disparity

Counterfactual fairness test:
  For each protected attribute a and a sample of 200 employees:
    flip attribute a on employee i → recompute model score
    Δscore_i = score(flipped) − score(original)
    Report: mean(Δscore), 95% CI via bootstrap (n=1000)
    Flag if |mean(Δscore)| > 2.0 points

Model outputs audited:  impact_score · attrition_risk · simulated_retention_selection
Protected dimensions:   gender · age_bracket · ethnicity_proxy
All groups are synthetic proxies — no real demographic data used or inferred`
          }</div>
        </div>

        {/* 10: L&D ILP */}
        <div style={algCard}>
          <div style={algTitle}>10 — L&D Budget ILP  (backend/services/ld_service.py)</div>
          <div style={lbl}>PuLP formulation — employee × program binary assignment</div>
          <div style={mono}>{
`Variables:  y_{i,t} ∈ {0, 1}  — 1 if employee i is assigned to program t

Maximise:   Σ_{i,t}  y_{i,t} · [w_impact · Δimpact_{i,t}
                                + w_attrition · Δattrition_{i,t}
                                + w_proficiency · Δproficiency_{i,t}]
            w_impact=0.50, w_attrition=0.30, w_proficiency=0.20

Subject to:
  [Budget]    Σ_{i,t}  y_{i,t} · cost_t  ≤  ld_budget
  [Capacity]  ∀ t:  Σ_i  y_{i,t}  ≤  capacity_t
  [One prog]  ∀ i:  Σ_t  y_{i,t}  ≤  1

Δimpact_{i,t}     = program_impact_delta_t × learning_velocity_i
learning_velocity_i inferred from:  junior→0.6, mid→0.8, senior→1.0, lead→0.9, exec→0.7
Δattrition_{i,t}  = program_attrition_reduction_t × (attrition_risk_i / 100)

Pareto sweep:  total_budget varied; ld_budget ∈ [0, total_budget] in 20 steps
               reports (retention_score, ld_return) frontier
Capped at top 150 employees by attrition risk to keep solve time < 3s`
          }</div>
        </div>

        {/* 11: Knowledge SKH */}
        <div style={algCard}>
          <div style={algTitle}>11 — Knowledge Loss Score  (backend/services/knowledge_service.py)</div>
          <div style={lbl}>Weighted domain criticality and single-holder detection</div>
          <div style={mono}>{
`23 knowledge domains, each with criticality c_d ∈ [0, 1]
  Examples:  legacy_system_arch=0.95, hipaa_integration=0.90,
             production_runbooks=0.88, client_relationships=0.85

Domain assignment probability for employee i:
  P(domain d | employee i) = base_prob + affinity_bonus
  base_prob  = 0.12 (all employees)
  affinity_bonus = 0.35 if department_i ∈ domain_d.affinity_departments

knowledge_loss_score_i = Σ_d  c_d × owns(i, d) × (1 − has_backup_d)
  has_backup_d = 1 if count(owners of d) > 1 else 0
  Employees with knowledge_loss_score > 0.5 flagged as high-knowledge-loss risk

Single-Knowledge-Holder (SKH):
  skh_flag_d = (count_owners_d == 1)

Transfer roadmap for employee i (top 5 successors per domain):
  successor_score_j = skill_overlap(j, domain_d) + (1 − attrition_risk_j)
  estimated_transfer_hours = criticality_d × 40  (configurable)
  estimated_transfer_cost  = estimated_transfer_hours × $150/hr`
          }</div>
        </div>

        {/* 12: OHI */}
        <div style={algCard}>
          <div style={algTitle}>12 — Organizational Health Index  (backend/services/ohi_service.py)</div>
          <div style={lbl}>Six-dimension weighted composite with forecast</div>
          <div style={mono}>{
`OHI = Σ_d  weight_d × sub_score_d   ∈ [0, 100]

Sub-dimension computation:
  financial_health (20%):
    = clamp(100 × (1 − budget_variance) × compensation_leverage, 0, 100)
  talent_risk (20%):
    = 100 − (attrition_concentration × critical_role_exposure)
  knowledge_resilience (20%):
    = 100 × (1 − fraction_skh_domains) × transfer_progress
  leadership_pipeline (15%):
    = 100 × ready_now_count / required_leaders
  compensation_equity (15%):
    = 100 × (1 − mean_absolute_equity_gap)
  collaboration_density (10%):
    = 100 × mean_betweenness_norm_all_employees

24-month time series:  base OHI evolved with AR(1) noise + annotated events
6-month forecast:      numpy.polyfit(degree=1) on last 12 months → extrapolated
Industry benchmarks:   P25/P50/P75 generated from rng.normal(base_ohi, σ_peer)

Decision impact preview:
  For budget retention at [60%, 70%, 80%, 90%] of total payroll:
    recalculate talent_risk and knowledge_resilience sub-scores
    report ΔOHI relative to baseline`
          }</div>
        </div>

        <div style={divider} />

        {/* ── 4. API Endpoints ── */}
        <Eyebrow>API Endpoints</Eyebrow>
        <h2 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--dark)', marginBottom: 8 }}>
          All routes — method, path, minimum role, response shape
        </h2>
        <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: '#475569', maxWidth: 700, lineHeight: 1.8, marginBottom: 24 }}>
          Internal API prefixed <code style={inlineCode}>/api</code> — JWT + RBAC. Public API at <code style={inlineCode}>/api/v1/</code> — Bearer token (scoped API key). All GET routes accept <code style={inlineCode}>scenario</code>, <code style={inlineCode}>size</code>, <code style={inlineCode}>demo</code> query params.
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          {[
            { method: 'GET',  path: '/api/dashboard',                 role: 'Analyst',  desc: 'Impact scores, attrition risk, budget vs actual, Nexus flags — all employees in RBAC scope' },
            { method: 'GET',  path: '/api/simulation',                role: 'Analyst',  desc: 'Current scenario state: retained/excluded sets, total impact score, budget utilisation %' },
            { method: 'POST', path: '/api/simulation/run',            role: 'Analyst',  desc: 'Body: {budget, forced_retain[], forced_exclude[]} → ILP result + optimality gap' },
            { method: 'POST', path: '/api/simulation/override',       role: 'Manager',  desc: 'Body: {employee_id, action, justification} → audit entry + updated scenario state' },
            { method: 'GET',  path: '/api/predictive',                role: 'Analyst',  desc: 'Attrition risk score + SHAP top driver per employee; department filter applied by RBAC' },
            { method: 'GET',  path: '/api/forecast/budget',           role: 'Analyst',  desc: 'Prophet forecast: 24-month history + 12-month forward + 80/95% CI per dept or total' },
            { method: 'GET',  path: '/api/forecast/montecarlo',       role: 'Analyst',  desc: 'Monte Carlo fan chart: P10/P50/P90 × 12 months + per-month exceedance probabilities' },
            { method: 'GET',  path: '/api/compensation',              role: 'Analyst',  desc: 'Comp-ratio per employee, OLS pay equity residuals, retention ROI, dept scorecards' },
            { method: 'GET',  path: '/api/knowledge',                 role: 'Analyst',  desc: 'Knowledge domain map, SKH flags, knowledge_loss_score per employee, transfer roadmap' },
            { method: 'GET',  path: '/api/mobility',                  role: 'Analyst',  desc: 'Career path suggestions, stagnation flags, succession depth per leadership role' },
            { method: 'GET',  path: '/api/fairness',                  role: 'Director', desc: 'EEOC 4/5ths results, chi-square p-values, counterfactual deltas per (dimension, model)' },
            { method: 'GET',  path: '/api/decision-room/sessions',    role: 'Manager',  desc: 'All sessions in scope with lifecycle state, participant list, and activity feed' },
            { method: 'POST', path: '/api/decision-room/sessions',    role: 'Manager',  desc: 'Create session — body: {name, participants[], scenario} → session_id + Draft state' },
            { method: 'GET',  path: '/api/resilience',                role: 'Director', desc: '6-dim resilience score, department breakdown, cascade simulation, intervention roadmap' },
            { method: 'GET',  path: '/api/ld',                        role: 'Analyst',  desc: 'ILP training allocation, Pareto frontier, skill gap records, 12-cohort ROI history' },
            { method: 'POST', path: '/api/narrative/impact',          role: 'Manager',  desc: 'Body: {employee_id} → LLM or template explanation of impact score SHAP breakdown' },
            { method: 'POST', path: '/api/narrative/attrition',       role: 'Manager',  desc: 'Body: {employee_id} → plain-language attrition risk summary with top drivers' },
            { method: 'POST', path: '/api/narrative/simulation',      role: 'Director', desc: 'Body: {simulation_id} → 3-paragraph outcome narrative for the full simulation result' },
            { method: 'GET',  path: '/api/ohi',                       role: 'Executive',desc: 'OHI score, 6-sub-dimension breakdown, 24-month series, forecast, benchmark bands' },
            { method: 'GET',  path: '/api/pulse',                     role: 'Analyst',  desc: 'Signal heatmap, early warning feed, 90-day timelines, team cohesion by department' },
            { method: 'GET',  path: '/api/notifications',             role: 'Viewer',   desc: 'Active alerts in scope: attrition spikes, budget overruns, threshold breaches' },
            { method: 'GET',  path: '/api/admin/audit',               role: 'Admin',    desc: 'Queryable audit log: filter by user, event_type, date range, outcome' },
            { method: 'GET',  path: '/api/v1/health',                 role: 'None',     desc: 'Service health — no auth required' },
            { method: 'GET',  path: '/api/v1/dashboard',              role: 'Bearer',   desc: 'KPI summary — salary gated by key scope (manager+ only)' },
            { method: 'GET',  path: '/api/v1/impact',                 role: 'Bearer',   desc: 'Per-employee impact scores — salary withheld below manager scope' },
            { method: 'GET',  path: '/api/v1/attrition-summary',      role: 'Bearer',   desc: 'Attrition risk distribution by tier and department' },
            { method: 'GET',  path: '/api/v1/ohi',                    role: 'Bearer',   desc: 'OHI score and 6-dimension breakdown' },
            { method: 'GET',  path: '/api/v1/forecast',               role: 'Bearer',   desc: '6-month budget forecast with P10/P50/P90 bands' },
            { method: 'GET',  path: '/api/v1/api-keys/sandbox',       role: 'None',     desc: 'Returns the demo sandbox key — immediate integration testing, no registration' },
            { method: 'POST', path: '/api/v1/api-keys',               role: 'Bearer',   desc: 'Create a scoped API key — raw key returned once, SHA-256 hash stored' },
            { method: 'POST', path: '/api/v1/webhooks',               role: 'Bearer',   desc: 'Register a webhook endpoint for one or more event types — secret returned once' },
            { method: 'POST', path: '/api/v1/webhooks/{id}/test',     role: 'Bearer',   desc: 'Send a test delivery to the endpoint; response includes status and latency' },
          ].map(({ method, path, role, desc }) => (
            <div key={path + method} style={{ display: 'grid', gridTemplateColumns: '58px 280px 1fr', gap: 16, padding: '11px 16px', background: 'var(--white)', borderRadius: 6, border: '1px solid var(--primary-10)', alignItems: 'start' }}>
              <span style={{ fontFamily: 'Courier New, monospace', fontSize: 10, fontWeight: 700, color: method === 'GET' ? '#1d4ed8' : '#6d28d9', backgroundColor: method === 'GET' ? '#eff6ff' : '#f5f3ff', padding: '2px 6px', borderRadius: 3, whiteSpace: 'nowrap', display: 'inline-block' }}>{method}</span>
              <span style={{ fontFamily: 'Courier New, monospace', fontSize: 11, color: '#1e293b' }}>{path}</span>
              <span style={{ fontFamily: 'var(--fb)', fontSize: 12, color: '#475569', lineHeight: 1.6 }}><strong style={{ color: 'var(--mid)' }}>{role}+</strong> — {desc}</span>
            </div>
          ))}
        </div>

        <div style={divider} />

        {/* ── 5. Data schema ── */}
        <Eyebrow>Data Schema</Eyebrow>
        <h2 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--dark)', marginBottom: 8 }}>
          Gold-layer tables (DuckDB) and audit table (PostgreSQL)
        </h2>
        <div style={mono}>{
`dim_employee
  employee_id       VARCHAR  PK   SHA-256 hashed for roles < Manager
  department        VARCHAR       normalised taxonomy
  role              VARCHAR
  seniority_band    VARCHAR       [IC1–IC6, M1–M4, E1–E3]
  hire_date         DATE
  annual_salary     DECIMAL(12,2)
  is_leader         BOOLEAN
  is_nexus          BOOLEAN       betweenness_norm >= 70
  impact_score      DECIMAL(5,2)  0–100, computed at Gold materialisation
  attrition_risk    DECIMAL(5,2)  0–100, XGBoost calibrated probability × 100
  attrition_driver  VARCHAR       SHAP top feature name
  community_id      INTEGER       Louvain community label

dim_team
  team_id           INTEGER  PK
  team_name         VARCHAR
  department        VARCHAR
  manager_id        VARCHAR  FK → dim_employee.employee_id

fact_performance
  employee_id       VARCHAR  FK
  quarter           DATE          first day of quarter (ISO 8601)
  kpi_score         DECIMAL(5,2)  0–100
  review_rating     VARCHAR       [exceeds, meets, below, n/a]

fact_budget
  department        VARCHAR
  month             DATE          first day of month
  budgeted_cost     DECIMAL(12,2)
  actual_cost       DECIMAL(12,2)
  headcount_budget  INTEGER
  headcount_actual  INTEGER

skills                              employee_skills  (many-to-many join)
  skill_id    INTEGER  PK             employee_id   VARCHAR  FK
  skill_name  VARCHAR                 skill_id      INTEGER  FK
  category    VARCHAR                 proficiency   VARCHAR  [beginner/intermediate/expert]
  is_critical BOOLEAN

audit_logs  (PostgreSQL — not DuckDB — append-only, no UPDATE/DELETE permitted)
  log_id      BIGSERIAL  PK
  user_id     VARCHAR
  user_role   VARCHAR        role at time of action (immutable snapshot)
  event_type  VARCHAR        [simulation_run, override, export, login, admin_action]
  target_id   VARCHAR        employee_id or simulation_id
  detail      JSONB          structured action record
  created_at  TIMESTAMPTZ`
        }</div>

        <div style={divider} />

        {/* ── 6. Performance ── */}
        <Eyebrow>Performance Targets</Eyebrow>
        <h2 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--dark)', marginBottom: 24 }}>
          Measured benchmarks
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
          {[
            { metric: '< 100ms',   label: 'DuckDB full dashboard aggregation · 50K employees' },
            { metric: '< 2s',      label: 'ILP solve · 5K-variable binary programme · CBC' },
            { metric: '< 3s',      label: 'L&D ILP · top 150 employees × 15 programs · CBC' },
            { metric: '< 500ms',   label: 'Impact scoring recalculation · full org · 50K employees' },
            { metric: '< 5s',      label: 'Graph centrality · Brandes O(VE) · 5,000-node graph' },
            { metric: '< 3s',      label: 'Pulse signal generation · 90 days × N employees × 6 signals · NumPy vectorised' },
            { metric: '< 15%',     label: 'MAPE · Prophet 3-month forecast horizon · validation fold' },
            { metric: '< 30s',     label: 'Monte Carlo · 2,000 simulations · 500 employees' },
            { metric: 'AUC > 0.78',label: 'Attrition classifier · held-out test fold · XGBoost' },
            { metric: '< 30s',     label: 'Narrative generation · Ollama mistral:7b with 30s hard timeout' },
            { metric: '100 req/m', label: 'API v1 rate limit · token-bucket per key · in-process, no Redis' },
            { metric: '>= 85%',    label: 'Unit test coverage target (pytest + pytest-cov)' },
          ].map(({ metric, label }) => (
            <div key={metric} style={{ ...card }}>
              <div style={{ fontFamily: 'var(--fd)', fontSize: 24, fontWeight: 300, color: 'var(--primary)', lineHeight: 1, marginBottom: 8 }}>{metric}</div>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', lineHeight: 1.55 }}>{label}</div>
            </div>
          ))}
        </div>

        <div style={divider} />

        {/* ── 7. Security ── */}
        <Eyebrow>Security Architecture</Eyebrow>
        <h2 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--dark)', marginBottom: 8 }}>
          Zero data to external services — RBAC enforced at query layer
        </h2>
        <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: '#475569', maxWidth: 700, lineHeight: 1.8, marginBottom: 24 }}>
          Data isolation is enforced in the DuckDB WHERE clause, not in the UI. A scoped role cannot retrieve out-of-scope data regardless of how a request is constructed — the filter is injected by RBAC middleware before the query reaches DuckDB.
        </p>
        <div style={mono}>{
`RBAC enforcement — query layer injection (FastAPI middleware):

  dept_filter = rbac.get_scope(current_user)   →  list[str] | None  (None = org-wide)
  if dept_filter:
      query += f"WHERE department IN ({placeholders})"   ← parameterised, not interpolated
      params += dept_filter

PII masking:
  if current_user.role in {Viewer, Analyst}:
      salary fields  →  salary_band string  (e.g. "$90K–$110K")
      employee_id    →  SHA-256(employee_id + SALT)  (Silver layer, propagated to Gold)
  Manager tier and above see exact figures

Auth flow:
  POST /auth/login  →  bcrypt.verify(password, stored_hash)       cost factor = 12
                    →  jwt.encode({sub, role, scope, exp: now+8h}, RS256_private_key)
  All protected routes →  jwt.decode(token, RS256_public_key)
                       →  {role, scope} injected into request state

OWASP controls:
  A01 Broken Access Control  →  RBAC middleware on every protected route; no UI bypass possible
  A03 Injection              →  DuckDB parameterised queries; no f-string SQL construction
  A07 Auth failures          →  JWT expiry 8h; bcrypt cost 12; no server-side session storage
  A09 Security logging       →  every request written to audit_logs (user, route, ts, outcome)

Forbidden at all times: logging any value from salary, employee_id (clear), name, or email fields`
        }</div>

        <div style={divider} />

        {/* ── 8. Deployment ── */}
        <Eyebrow>Deployment Topology</Eyebrow>
        <h2 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--dark)', marginBottom: 8 }}>
          Docker Compose — three services, single-node
        </h2>
        <div style={mono}>{
`docker-compose.yml  (abridged)

  postgres:
    image: postgres:16-alpine
    ports: "5432:5432"
    volumes: postgres_data:/var/lib/postgresql/data
    env: POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
    healthcheck: pg_isready -U $$POSTGRES_USER

  backend:
    build: ./backend  (base: python:3.11-slim)
    command: uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
    ports: "8000:8000"
    depends_on: postgres (condition: service_healthy)
    volumes: ./backend:/app/backend  ← bind-mount enables --reload in dev
    env: DATABASE_URL, JWT_SECRET, DEMO_MODE, SALT

  frontend:
    build: ./frontend  (base: node:20-alpine)
    command: npm run dev -- --host 0.0.0.0  (vite preview in production build)
    ports: "5173:5173"
    depends_on: backend

Trained model artefacts (XGBoost weights, Prophet serialised model) are written to
backend/models/artefacts/ on first training run and loaded from disk on subsequent starts.

No service makes outbound network calls at runtime.
All three containers communicate on the internal Docker bridge network only.`
        }</div>

      </div>
    </div>
  )
}

// ── Main InfoPage ────────────────────────────────────────────────────────

export default function InfoPage({ onLaunch }: InfoPageProps) {
  const [tab, setTab] = useState<InfoTab>('business')

  const tabBtn = (id: InfoTab): React.CSSProperties => ({
    background:       'none',
    backgroundColor:  'transparent',
    border:           'none',
    borderBottom:     `2px solid ${tab === id ? 'var(--gold-light)' : 'transparent'}`,
    marginBottom:     -1,
    padding:          '14px 24px',
    fontFamily:       'var(--fb)',
    fontSize:         11,
    fontWeight:       500,
    letterSpacing:    '1.5px',
    textTransform:    'uppercase',
    color:            tab === id ? 'var(--gold-light)' : 'rgba(255,255,255,0.4)',
    cursor:           'pointer',
    transition:       'color 0.15s',
    whiteSpace:       'nowrap',
  })

  return (
    <div>
      {/* Own sticky nav bar — not the main Nav component */}
      <nav style={{ backgroundColor: 'rgba(0,51,102,0.97)', backdropFilter: 'blur(12px)', height: 52, position: 'sticky', top: 0, zIndex: 999, borderBottom: '1px solid rgba(255,255,255,0.08)', padding: '0 40px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 1 }}>
          <span style={{ fontFamily: 'var(--fd)', fontSize: 20, fontWeight: 300, color: '#fff', lineHeight: 1 }}>O</span>
          <em style={{ fontFamily: 'var(--fd)', fontSize: 20, fontWeight: 300, fontStyle: 'italic', color: 'var(--gold-light)', lineHeight: 1 }}>PB</em>
        </div>
        <span style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '3px', textTransform: 'uppercase', color: 'rgba(255,255,255,0.4)' }}>
          EMPLOYEE IMPACT &amp; BUDGET OPTIMIZER · PLATFORM OVERVIEW
        </span>
        <button
          onClick={onLaunch}
          style={{ fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 700, letterSpacing: '1.5px', textTransform: 'uppercase', background: 'var(--gold)', color: '#fff', border: 'none', borderRadius: 'var(--radius-sm)', padding: '8px 16px', cursor: 'pointer', transition: 'background 0.15s' }}
          onMouseOver={(e) => { (e.target as HTMLButtonElement).style.background = 'var(--gold-light)'; (e.target as HTMLButtonElement).style.color = 'var(--primary)' }}
          onMouseOut={(e) => { (e.target as HTMLButtonElement).style.background = 'var(--gold)'; (e.target as HTMLButtonElement).style.color = '#fff' }}
        >
          Launch Application →
        </button>
      </nav>

      {/* Hero — padding-bottom: 0 so tab bar merges with hero border */}
      <div style={hero}>
        <div style={heroInner}>
          <Eyebrow light>EIBO · Platform Overview</Eyebrow>
          <h1 style={{ fontFamily: 'var(--fd)', fontSize: 40, fontWeight: 300, color: '#fff', maxWidth: 680, lineHeight: 1.25, margin: '0 0 16px' }}>
            Turn budget pressure into{' '}
            <em style={{ fontStyle: 'italic', color: 'var(--gold-light)' }}>strategic clarity.</em>
          </h1>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: 'rgba(255,255,255,0.6)', maxWidth: 560, lineHeight: 1.75, margin: '0 0 40px' }}>
            EIBO gives organizational leaders a data-driven lens to balance cost targets
            with critical talent retention — without sacrificing the human judgment that
            defines responsible decision-making.
          </p>
          <div style={{ display: 'flex', gap: 48, flexWrap: 'wrap', marginBottom: 40 }}>
            <KpiStat value="17"    label="Analytical capabilities across the workforce decision lifecycle" />
            <KpiStat value="< 2s"  label="ILP optimization for 5,000 employees" />
            <KpiStat value="100%"  label="Human override on every model suggestion" />
            <KpiStat value="$0"    label="Licensing cost — fully open source" />
          </div>

          {/* Tab bar — bottom of hero, marginBottom: -1 merges border */}
          <div style={{ display: 'flex', borderBottom: '1px solid rgba(255,255,255,0.1)', marginTop: 16 }}>
            <button style={tabBtn('business')}    onClick={() => setTab('business')}>
              Business View
            </button>
            <button style={tabBtn('engineering')} onClick={() => setTab('engineering')}>
              Engineering View
            </button>
          </div>
        </div>
      </div>

      {/* Tab content */}
      {tab === 'business'    ? <BusinessView />    : <EngineeringView />}
    </div>
  )
}
