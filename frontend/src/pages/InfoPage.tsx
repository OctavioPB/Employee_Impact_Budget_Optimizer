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

const grid3: React.CSSProperties = {
  display:             'grid',
  gridTemplateColumns: 'repeat(3, 1fr)',
  gap:                 24,
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

function FeatureCard({ num, title, desc }: { num: number; title: string; desc: string }) {
  return (
    <div style={card}>
      <div style={{ fontFamily: 'var(--fd)', fontSize: 44, fontWeight: 300, color: 'var(--primary-30)', lineHeight: 1, userSelect: 'none' }}>
        {num}
      </div>
      <div style={{ width: 36, height: 3, background: 'var(--gold)', borderRadius: 2, margin: '6px 0 12px' }} />
      <div style={{ fontFamily: 'var(--fd)', fontSize: 18, fontWeight: 300, color: 'var(--dark)', marginBottom: 10 }}>
        {title}
      </div>
      <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: '#475569', lineHeight: 1.75, margin: 0 }}>
        {desc}
      </p>
    </div>
  )
}

// ── Business View ────────────────────────────────────────────────────────

function BusinessView() {
  return (
    <div style={body}>
      <div style={section}>

        {/* Platform capabilities */}
        <Eyebrow>Platform Capabilities</Eyebrow>
        <h2 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--dark)', marginBottom: 8 }}>
          Six lenses on your workforce — all in one platform.
        </h2>
        <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: '#475569', maxWidth: 620, lineHeight: 1.75, marginBottom: 40 }}>
          EIBO combines data science, graph theory, and linear programming to give
          organizational leaders a complete picture of talent cost and risk.
        </p>

        <div style={grid3}>
          <FeatureCard num={1} title="Impact Scoring"
            desc="Every employee receives a 0–100 impact score combining KPI history, collaboration network centrality, skill criticality, and estimated replacement cost." />
          <FeatureCard num={2} title="Budget Simulation"
            desc="Run ILP-powered optimization across hundreds of budget scenarios in under 2 seconds. Override any suggestion — the model informs, you decide." />
          <FeatureCard num={3} title="Attrition Risk"
            desc="Calibrated probability that each employee voluntarily leaves within 12 months. Early warning alerts let retention action happen before risk becomes departure." />
          <FeatureCard num={4} title="Network Analysis"
            desc="Collaboration graph reveals Nexus employees — those whose departure would fragment teams. Betweenness centrality flags hidden dependencies invisible in org charts." />
          <FeatureCard num={5} title="Budget Forecasting"
            desc="Prophet-based time series forecasting with 80% and 95% confidence intervals. Monte Carlo stress testing shows tail risk across thousands of random scenarios." />
          <FeatureCard num={6} title="Strategic Planning"
            desc="Future State Designer models proposed structures with real cost projections. Build vs Buy analysis compares upskilling cost against external hiring for each skill gap." />
        </div>

        <div style={divider} />

        {/* How it works */}
        <Eyebrow>Decision Flow</Eyebrow>
        <h2 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--dark)', marginBottom: 32 }}>
          The machine suggests. <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>You decide.</em>
        </h2>
        <div style={{ display: 'flex', gap: 0 }}>
          {[
            { step: '01', title: 'Load your data', body: 'Connect HRIS (Workday, BambooHR, SuccessFactors) or upload a CSV. Demo mode uses realistic synthetic data — no setup required.' },
            { step: '02', title: 'Explore the dashboard', body: 'Impact scores, attrition risk, budget variance, and collaboration health — all computed automatically, all explainable via SHAP.' },
            { step: '03', title: 'Run a simulation', body: 'Set a budget target. The optimizer returns a retention plan in seconds. Override any decision with a written justification — full audit trail.' },
          ].map(({ step, title, body: b }, i) => (
            <div key={step} style={{ flex: 1, padding: '28px 32px', borderLeft: i === 0 ? '3px solid var(--gold)' : '1px solid var(--primary-10)', background: 'var(--white)', borderRadius: i === 0 ? 'var(--radius-md) 0 0 var(--radius-md)' : i === 2 ? '0 var(--radius-md) var(--radius-md) 0' : 0 }}>
              <div style={{ fontFamily: 'var(--fd)', fontSize: 32, fontWeight: 300, color: 'var(--primary-30)', marginBottom: 8 }}>{step}</div>
              <div style={{ fontFamily: 'var(--fd)', fontSize: 16, fontWeight: 400, color: 'var(--dark)', marginBottom: 10 }}>{title}</div>
              <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: '#475569', lineHeight: 1.75, margin: 0 }}>{b}</p>
            </div>
          ))}
        </div>

        <div style={divider} />

        {/* ROI Calculator */}
        <Eyebrow>Value Proposition</Eyebrow>
        <h2 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--dark)', marginBottom: 32 }}>
          Industry benchmarks on workforce optimization.
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
          {[
            { value: '$85K',  label: 'Average cost to replace a mid-level employee', color: 'var(--status-orange)' },
            { value: '34%',   label: 'Annual turnover rate in tech and finance sectors', color: 'var(--status-red)' },
            { value: '3×',    label: 'Faster budget scenario analysis vs. manual modeling', color: 'var(--status-green)' },
            { value: '< 2s',  label: 'Optimization runtime for 5,000 employees', color: 'var(--primary-60)' },
          ].map(({ value, label, color }) => (
            <div key={value} style={{ ...card, borderTop: '3px solid var(--gold)' }}>
              <div style={{ fontFamily: 'var(--fd)', fontSize: 32, fontWeight: 300, color, lineHeight: 1, marginBottom: 8 }}>{value}</div>
              <p style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)', lineHeight: 1.6, margin: 0 }}>{label}</p>
            </div>
          ))}
        </div>

        <div style={divider} />

        {/* RBAC */}
        <Eyebrow>Access Control</Eyebrow>
        <h2 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--dark)', marginBottom: 24 }}>
          Six-tier role model — right data, right people.
        </h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {[
            { role: 'Viewer',    desc: 'Dashboard read access. No simulation.', color: 'var(--mid)' },
            { role: 'Analyst',   desc: 'Run simulations, create scenarios. No overrides.', color: 'var(--primary-60)' },
            { role: 'Manager',   desc: 'Full access to own department. Can override model suggestions.', color: 'var(--status-blue)' },
            { role: 'Director',  desc: 'Multiple departments. Strategic planning access.', color: 'var(--gold)' },
            { role: 'Executive', desc: 'Org-wide view. All features except system admin.', color: 'var(--status-purple)' },
            { role: 'Admin',     desc: 'System configuration, user management, audit logs.', color: 'var(--status-green)' },
          ].map(({ role, desc, color }) => (
            <div key={role} style={{ display: 'flex', alignItems: 'center', gap: 20, padding: '14px 20px', background: 'var(--white)', borderRadius: 8, border: '1px solid var(--primary-10)' }}>
              <div style={{ width: 4, height: 24, background: color, borderRadius: 2, flexShrink: 0 }} />
              <span style={{ fontFamily: 'var(--fb)', fontSize: 11, fontWeight: 700, letterSpacing: '1px', textTransform: 'uppercase', color, minWidth: 80 }}>{role}</span>
              <span style={{ fontFamily: 'var(--fb)', fontSize: 13, color: '#475569' }}>{desc}</span>
            </div>
          ))}
        </div>

      </div>
    </div>
  )
}

// ── Engineering View ─────────────────────────────────────────────────────

function EngineeringView() {
  return (
    <div style={body}>
      <div style={section}>

        <Eyebrow>System Architecture</Eyebrow>
        <h2 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--dark)', marginBottom: 8 }}>
          Medallion data architecture — three layers of trust.
        </h2>
        <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: '#475569', maxWidth: 640, lineHeight: 1.75, marginBottom: 32 }}>
          Raw ERP/HRIS data flows through Bronze (raw) → Silver (clean) → Gold (aggregated) layers.
          Each layer has defined quality guarantees. Only Gold-layer data reaches the UI.
        </p>

        {/* Architecture flow */}
        <div style={{ display: 'flex', alignItems: 'stretch', gap: 0, marginBottom: 40 }}>
          {[
            { label: 'HRIS / ERP', sub: 'Workday · BambooHR · SuccessFactors · CSV' },
            { label: 'Bronze',     sub: 'Raw ingestion — immutable source of truth'   },
            { label: 'Silver',     sub: 'Cleansing · normalisation · validation'       },
            { label: 'Gold',       sub: 'Aggregated views · impact scores · centrality' },
            { label: 'UI / API',   sub: 'React frontend → FastAPI → DuckDB'            },
          ].map(({ label, sub }, i) => (
            <React.Fragment key={label}>
              {i > 0 && (
                <div style={{ display: 'flex', alignItems: 'center', color: 'var(--primary-30)', fontFamily: 'var(--fb)', fontSize: 18, padding: '0 4px' }}>→</div>
              )}
              <div style={{ flex: 1, background: 'var(--white)', border: '1px solid var(--primary-10)', borderTop: '3px solid var(--gold)', borderRadius: 8, padding: '16px 18px' }}>
                <div style={{ fontFamily: 'var(--fd)', fontSize: 15, fontWeight: 400, color: 'var(--dark)', marginBottom: 6 }}>{label}</div>
                <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', lineHeight: 1.5 }}>{sub}</div>
              </div>
            </React.Fragment>
          ))}
        </div>

        <div style={divider} />

        {/* Tech stack */}
        <Eyebrow>Technology Stack</Eyebrow>
        <h2 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--dark)', marginBottom: 24 }}>
          100% open source. Zero licensing cost.
        </h2>
        <div style={grid2}>
          {[
            { layer: 'UI',            stack: 'React 18 + TypeScript + Vite 5',               note: 'Inline styles, no UI library — full OPB design fidelity' },
            { layer: 'API',           stack: 'FastAPI + uvicorn',                              note: 'Async, auto-documented, Pydantic response models' },
            { layer: 'Analytics',     stack: 'DuckDB (in-process OLAP)',                      note: '<100ms for 50K employee queries' },
            { layer: 'Persistence',   stack: 'PostgreSQL 16',                                 note: 'Users, audit logs, simulation history, notifications' },
            { layer: 'Optimization',  stack: 'PuLP (Integer Linear Programming)',             note: 'Multi-objective, Pareto frontier, sensitivity analysis' },
            { layer: 'ML / Scoring',  stack: 'Scikit-learn + XGBoost + SHAP',                note: 'SHAP explanations mandatory on every prediction' },
            { layer: 'Forecasting',   stack: 'Prophet + Monte Carlo (NumPy)',                 note: 'Fan-chart confidence intervals, 80% and 95% bands' },
            { layer: 'Graph',         stack: 'NetworkX — Louvain community detection',        note: 'Betweenness > 0.7 → Nexus employee badge' },
          ].map(({ layer, stack, note }) => (
            <div key={layer} style={{ ...card, borderLeft: '3px solid var(--gold)' }}>
              <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                <div>
                  <div style={{ fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--mid)', marginBottom: 4 }}>{layer}</div>
                  <div style={{ fontFamily: 'var(--fd)', fontSize: 15, fontWeight: 400, color: 'var(--dark)', marginBottom: 6 }}>{stack}</div>
                  <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: '#475569', lineHeight: 1.6 }}>{note}</div>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div style={divider} />

        {/* ILP formulation */}
        <Eyebrow>Optimization Engine</Eyebrow>
        <h2 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--dark)', marginBottom: 16 }}>
          Integer Linear Programming — exact optimal solutions.
        </h2>
        <div style={{ ...card, borderLeft: '3px solid var(--primary-60)', fontFamily: 'Courier New, monospace', fontSize: 13, lineHeight: 2, color: 'var(--dark)' }}>
          <div><strong>Objective:</strong>  maximize Σ (impact_score<sub>i</sub> × x<sub>i</sub>)</div>
          <div><strong>Subject to:</strong></div>
          <div style={{ paddingLeft: 24, color: 'var(--primary-60)' }}>Σ (cost<sub>i</sub> × x<sub>i</sub>) ≤ available_budget</div>
          <div style={{ paddingLeft: 24, color: 'var(--primary-60)' }}>∀ team t: Σ leader<sub>it</sub> × x<sub>i</sub> ≥ 1</div>
          <div style={{ paddingLeft: 24, color: 'var(--primary-60)' }}>∀ critical skill s: Σ has_skill<sub>is</sub> × x<sub>i</sub> ≥ 1</div>
          <div style={{ paddingLeft: 24, color: 'var(--mid)' }}>x<sub>i</sub> ∈ {'{0, 1}'}  (binary — retained or not retained in simulation)</div>
        </div>

        <div style={divider} />

        {/* Performance */}
        <Eyebrow>Performance Targets</Eyebrow>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
          {[
            { metric: '< 100ms', label: 'Impact scoring · 50K employees' },
            { metric: '< 2s',    label: 'ILP optimization · 5K employees' },
            { metric: '< 15%',   label: 'MAPE · 3-month forecast horizon' },
            { metric: '>85%',    label: 'Unit test coverage target' },
          ].map(({ metric, label }) => (
            <div key={metric} style={{ ...card }}>
              <div style={{ fontFamily: 'var(--fd)', fontSize: 28, fontWeight: 300, color: 'var(--primary)', lineHeight: 1, marginBottom: 8 }}>{metric}</div>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', lineHeight: 1.5 }}>{label}</div>
            </div>
          ))}
        </div>

        <div style={divider} />

        {/* Security */}
        <Eyebrow>Security Architecture</Eyebrow>
        <h2 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--dark)', marginBottom: 24 }}>
          Zero data to external services.
        </h2>
        <div style={grid3}>
          {[
            { title: 'Local processing', body: 'All computation runs inside your Docker network. No HR data leaves the perimeter — not for ML, not for forecasting, not for any feature.' },
            { title: 'RBAC + PII masking', body: 'Department-scoped queries enforce data isolation. Salary data is masked (ranges only) for roles below Manager. Audit trail is immutable.' },
            { title: 'OWASP compliance', body: 'SQL injection via parameterized queries. Input validation at every API boundary. Dependency scanning in CI. WCAG 2.1 AA accessibility target.' },
          ].map(({ title, body: b }) => (
            <div key={title} style={{ ...card }}>
              <div style={{ fontFamily: 'var(--fd)', fontSize: 16, fontWeight: 400, color: 'var(--dark)', marginBottom: 10 }}>{title}</div>
              <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: '#475569', lineHeight: 1.75, margin: 0 }}>{b}</p>
            </div>
          ))}
        </div>

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
            <KpiStat value="3×"    label="Faster budget scenario analysis" />
            <KpiStat value="< 2s"  label="Optimization for 5,000 employees" />
            <KpiStat value="100%"  label="Human override on every suggestion" />
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
