import React, { useState, useEffect } from 'react'
import {
  api,
  FairnessData,
  EEOCRow,
  GroupProfile,
  SimSelectionRow,
} from '../services/api'
import { useDemoStore } from '../stores/demoStore'

type Tab = 'profiles' | 'eeoc' | 'counterfactual'

// ── Helpers ───────────────────────────────────────────────────────────────

const DIM_LABEL: Record<string, string> = {
  gender:          'Gender',
  age_bracket:     'Age Bracket',
  ethnicity_proxy: 'Ethnicity Proxy',
}

function airColor(air: number): string {
  if (air >= 0.95) return '#1a8c4e'
  if (air >= 0.80) return '#c8982a'
  return '#e03448'
}

function pvalColor(p: number): string {
  if (p < 0.01) return '#e03448'
  if (p < 0.05) return '#f07020'
  return '#1a8c4e'
}

function PassBadge({ pass }: { pass: boolean }) {
  return (
    <span style={{
      display:         'inline-block',
      padding:         '2px 8px',
      borderRadius:    4,
      fontSize:        10,
      fontFamily:      'var(--fb)',
      fontWeight:      600,
      letterSpacing:   '1px',
      textTransform:   'uppercase',
      backgroundColor: pass ? 'rgba(26,140,78,0.12)' : 'rgba(224,52,72,0.12)',
      color:           pass ? '#1a8c4e' : '#e03448',
    }}>
      {pass ? 'PASS' : 'FLAG'}
    </span>
  )
}

// ── Group Profile Bar Chart ────────────────────────────────────────────────
// Horizontal bar chart of avg_impact_score and avg_attrition per group,
// rendered for one dimension at a time.

function GroupProfileChart({
  profiles,
  dimension,
  metric,
}: {
  profiles:  GroupProfile[]
  dimension: string
  metric:    'avg_impact_score' | 'avg_attrition'
}) {
  const filtered = profiles.filter(p => p.dimension === dimension)
  const isImpact = metric === 'avg_impact_score'
  const maxVal   = isImpact ? 100 : 1
  const barColor = isImpact ? '#003366' : '#e03448'

  const BAR_H  = 22
  const LEFT   = 100
  const BAR_W  = 240
  const GAP    = 6
  const H      = filtered.length * (BAR_H + GAP) + 30

  return (
    <svg viewBox={`0 0 ${LEFT + BAR_W + 80} ${H}`} style={{ display: 'block', width: '100%', maxWidth: 460 }}>
      {filtered.map((p, i) => {
        const val  = p[metric] as number
        const pct  = val / maxVal
        const bw   = Math.max(2, pct * BAR_W)
        const y    = i * (BAR_H + GAP)
        const disp = isImpact ? val.toFixed(1) : (val * 100).toFixed(1) + '%'
        return (
          <g key={p.group}>
            <text x={LEFT - 6} y={y + BAR_H / 2 + 4} textAnchor="end" fontSize={10}
              fill="var(--text-muted)" fontFamily="Plus Jakarta Sans, sans-serif">
              {p.group}
            </text>
            <rect x={LEFT} y={y} width={bw} height={BAR_H}
              fill={barColor} opacity={0.82} rx={2} />
            <text x={LEFT + bw + 6} y={y + BAR_H / 2 + 4} fontSize={10}
              fill="var(--text-body)" fontFamily="Plus Jakarta Sans, sans-serif">
              {disp}
            </text>
          </g>
        )
      })}
    </svg>
  )
}

// ── EEOC Detail Row ───────────────────────────────────────────────────────

function EEOCDetail({ row }: { row: EEOCRow }) {
  const [open, setOpen] = useState(false)
  return (
    <div style={{ borderBottom: '1px solid var(--border)', padding: '10px 0' }}>
      <div
        onClick={() => setOpen(o => !o)}
        style={{ display: 'flex', alignItems: 'center', gap: 12, cursor: 'pointer' }}
      >
        <span style={{ fontSize: 12, color: 'var(--text-muted)', width: 120, flexShrink: 0 }}>
          {DIM_LABEL[row.dimension] ?? row.dimension}
        </span>
        <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-body)', width: 110 }}>
          {row.model}
        </span>
        <div style={{ flex: 1 }}>
          <AIRBar air={row.min_air} />
        </div>
        <span style={{ fontSize: 11, color: airColor(row.min_air), width: 48, textAlign: 'right' }}>
          {row.min_air.toFixed(3)}
        </span>
        <span style={{ width: 56, textAlign: 'center' }}>
          <PassBadge pass={row.eeoc_pass} />
        </span>
        <span style={{ fontSize: 11, color: pvalColor(row.chi2_pval), width: 52, textAlign: 'right' }}>
          p={row.chi2_pval.toFixed(3)}
        </span>
        <span style={{ fontSize: 16, color: 'var(--text-muted)', width: 20 }}>
          {open ? '▲' : '▼'}
        </span>
      </div>

      {open && (
        <div style={{ marginTop: 10, paddingLeft: 8 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                {['Group', 'N', 'Selected', 'Sel. Rate', 'Avg Score', 'AIR', 'Status'].map(h => (
                  <th key={h} style={{ padding: '4px 8px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 500 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {row.groups.map(g => (
                <tr key={g.group} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td style={{ padding: '5px 8px', color: 'var(--text-body)', fontWeight: g.is_reference ? 600 : 400 }}>
                    {g.group}{g.is_reference ? ' ✦' : ''}
                  </td>
                  <td style={{ padding: '5px 8px', color: 'var(--text-muted)' }}>{g.count}</td>
                  <td style={{ padding: '5px 8px', color: 'var(--text-muted)' }}>{g.selected}</td>
                  <td style={{ padding: '5px 8px', color: 'var(--text-body)' }}>{(g.selection_rate * 100).toFixed(1)}%</td>
                  <td style={{ padding: '5px 8px', color: 'var(--text-body)' }}>{g.avg_score.toFixed(1)}</td>
                  <td style={{ padding: '5px 8px', color: airColor(g.adverse_impact_ratio), fontWeight: 600 }}>
                    {g.adverse_impact_ratio.toFixed(3)}
                  </td>
                  <td style={{ padding: '5px 8px' }}><PassBadge pass={g.eeoc_pass} /></td>
                </tr>
              ))}
            </tbody>
          </table>
          <p style={{ marginTop: 6, fontSize: 10, color: 'var(--text-muted)' }}>
            χ² = {row.chi2_stat.toFixed(2)}, p = {row.chi2_pval.toFixed(4)}
            {row.significant ? ' — statistically significant' : ' — not significant'}
            {' · '}✦ reference group (highest selection rate)
          </p>
        </div>
      )}
    </div>
  )
}

// ── AIR Bar ───────────────────────────────────────────────────────────────

function AIRBar({ air }: { air: number }) {
  const pct   = Math.min(air, 1) * 100
  const color = airColor(air)
  return (
    <div style={{ position: 'relative', height: 6, borderRadius: 3, backgroundColor: 'var(--border)', overflow: 'hidden' }}>
      <div style={{
        position:        'absolute',
        left:            0,
        top:             0,
        height:          '100%',
        width:           `${pct}%`,
        backgroundColor: color,
        borderRadius:    3,
        transition:      'width 0.3s',
      }} />
      {/* 80% threshold marker */}
      <div style={{
        position:        'absolute',
        left:            '80%',
        top:             0,
        width:           1,
        height:          '100%',
        backgroundColor: 'rgba(224,52,72,0.5)',
      }} />
    </div>
  )
}

// ── Simulation Selection Panel ────────────────────────────────────────────

function SimPanel({
  simAnalysis,
  dimension,
}: {
  simAnalysis: Record<string, SimSelectionRow[]>
  dimension:  string
}) {
  const rows = simAnalysis[dimension] ?? []
  const maxRate = Math.max(...rows.map(r => r.selection_rate), 0.001)
  return (
    <div>
      {rows.map(r => (
        <div key={r.group} style={{ marginBottom: 6 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 3 }}>
            <span style={{ fontSize: 11, color: 'var(--text-body)', width: 90, flexShrink: 0 }}>{r.group}</span>
            <div style={{ flex: 1, height: 10, borderRadius: 5, backgroundColor: 'var(--border)', overflow: 'hidden' }}>
              <div style={{
                height:          '100%',
                width:           `${(r.selection_rate / maxRate) * 100}%`,
                backgroundColor: r.eeoc_pass ? '#1a8c4e' : '#e03448',
                borderRadius:    5,
              }} />
            </div>
            <span style={{ fontSize: 10, color: airColor(r.adverse_impact_ratio), width: 38, textAlign: 'right' }}>
              {(r.selection_rate * 100).toFixed(1)}%
            </span>
            <span style={{ width: 46 }}><PassBadge pass={r.eeoc_pass} /></span>
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Counterfactual Table ──────────────────────────────────────────────────

function CIBar({ lo, hi }: { lo: number; hi: number }) {
  // Visualise CI around 0; scale ±5 units
  const scale = 5
  const loP   = 50 + (lo / scale) * 50
  const hiP   = 50 + (hi / scale) * 50
  const contains0 = lo <= 0 && hi >= 0
  return (
    <div style={{ position: 'relative', height: 8, backgroundColor: 'var(--border)', borderRadius: 4, width: 120 }}>
      {/* zero line */}
      <div style={{ position: 'absolute', left: '50%', top: 0, width: 1, height: '100%', backgroundColor: 'rgba(0,0,0,0.2)' }} />
      {/* CI band */}
      <div style={{
        position:        'absolute',
        left:            `${Math.max(0, loP)}%`,
        width:           `${Math.min(100, hiP) - Math.max(0, loP)}%`,
        height:          '100%',
        backgroundColor: contains0 ? '#1a8c4e' : '#e03448',
        borderRadius:    4,
        opacity:         0.7,
      }} />
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────

const ATTR_LABEL: Record<string, string> = {
  gender:          'Gender',
  age_bracket:     'Age Bracket',
  ethnicity_proxy: 'Ethnicity Proxy',
}

export default function FairnessPage() {
  const { scenario, size } = useDemoStore()
  const [data,    setData]    = useState<FairnessData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState<string | null>(null)
  const [tab,     setTab]     = useState<Tab>('profiles')
  const [activeDim, setActiveDim] = useState<string>('gender')
  const [profileMetric, setProfileMetric] = useState<'avg_impact_score' | 'avg_attrition'>('avg_impact_score')

  useEffect(() => {
    setLoading(true)
    setError(null)
    api.fairness.data(scenario, size)
      .then(d => { setData(d); setLoading(false) })
      .catch(e => { setError(String(e)); setLoading(false) })
  }, [scenario, size])

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 300 }}>
      <span style={{ fontFamily: 'var(--fb)', fontSize: 12, letterSpacing: '2px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
        Running bias audit…
      </span>
    </div>
  )
  if (error || !data) return (
    <div style={{ padding: 40, color: '#e03448', fontFamily: 'var(--fb)', fontSize: 13 }}>
      {error ?? 'No data'}
    </div>
  )

  const { summary, group_profiles, eeoc_analysis, simulation_analysis, counterfactual, protected_groups } = data
  const dims = ['gender', 'age_bracket', 'ethnicity_proxy']

  // ── Tab nav styles ────────────────────────────────────────────────────
  const tabBase: React.CSSProperties = {
    background:      'none',
    border:          'none',
    cursor:          'pointer',
    fontFamily:      'var(--fb)',
    fontSize:        10,
    letterSpacing:   '2px',
    textTransform:   'uppercase',
    padding:         '8px 16px',
    borderBottom:    '2px solid transparent',
    color:           'var(--text-muted)',
    transition:      'color 0.15s, border-color 0.15s',
  }
  const tabActive: React.CSSProperties = {
    color:        'var(--navy)',
    borderBottom: '2px solid var(--navy)',
  }

  // ── Hero KPI card ─────────────────────────────────────────────────────
  const kpis = [
    {
      label: 'Overall Status',
      value: summary.overall_pass ? 'PASS' : 'FLAG',
      sub:   `${summary.eeoc_flags + summary.sim_flags} flags raised`,
      color: summary.overall_pass ? '#1a8c4e' : '#e03448',
      bg:    summary.overall_pass ? 'rgba(26,140,78,0.06)' : 'rgba(224,52,72,0.06)',
    },
    {
      label: 'EEOC Checks',
      value: `${summary.eeoc_flags} / ${summary.dimensions_tested * summary.model_outputs_tested}`,
      sub:   'flags / total checks',
      color: summary.eeoc_flags > 0 ? '#e03448' : '#1a8c4e',
      bg:    'var(--card-bg)',
    },
    {
      label: 'Counterfactual',
      value: summary.counterfactual_fair ? 'FAIR' : 'BIASED',
      sub:   'attribute flip → Δ score',
      color: summary.counterfactual_fair ? '#1a8c4e' : '#e03448',
      bg:    'var(--card-bg)',
    },
    {
      label: 'Groups Analyzed',
      value: String(summary.dimensions_tested),
      sub:   `${summary.total_employees} employees`,
      color: 'var(--navy)',
      bg:    'var(--card-bg)',
    },
  ]

  return (
    <div style={{ padding: '32px 40px', maxWidth: 1280, margin: '0 auto' }}>

      {/* Page header */}
      <div style={{ marginBottom: 28 }}>
        <p style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '3px', textTransform: 'uppercase', color: 'var(--gold-mid)', marginBottom: 6 }}>
          Sprint 13 · Algorithmic Fairness
        </p>
        <h1 style={{ fontFamily: 'var(--fd)', fontWeight: 300, fontSize: 28, color: 'var(--navy)', margin: 0 }}>
          Bias Audit &amp; Ethical Guardrails
        </h1>
        <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 6, maxWidth: 680 }}>
          EEOC 4/5ths adverse-impact analysis across gender, age, and ethnicity proxy dimensions.
          Counterfactual fairness verified — protected attributes are not model inputs.
        </p>
      </div>

      {/* Disclaimer banner */}
      <div style={{
        backgroundColor: 'rgba(201,168,76,0.08)',
        border:          '1px solid rgba(201,168,76,0.25)',
        borderRadius:    6,
        padding:         '10px 16px',
        fontSize:        11,
        color:           'var(--text-muted)',
        marginBottom:    24,
        lineHeight:      1.6,
      }}>
        <strong style={{ color: 'var(--gold-mid)' }}>Synthetic Proxy Groups —</strong>{' '}
        {data.note}
      </div>

      {/* Hero KPIs */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 28 }}>
        {kpis.map(k => (
          <div key={k.label} style={{
            backgroundColor: k.bg,
            border:          '1px solid var(--border)',
            borderRadius:    8,
            padding:         '16px 20px',
          }}>
            <p style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--text-muted)', margin: '0 0 8px' }}>
              {k.label}
            </p>
            <p style={{ fontFamily: 'var(--fd)', fontSize: 26, fontWeight: 300, color: k.color, margin: '0 0 4px', letterSpacing: 1 }}>
              {k.value}
            </p>
            <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: 0 }}>{k.sub}</p>
          </div>
        ))}
      </div>

      {/* Tab bar */}
      <div style={{ borderBottom: '1px solid var(--border)', display: 'flex', gap: 0, marginBottom: 28 }}>
        {([
          ['profiles',      'Group Profiles'],
          ['eeoc',          'EEOC Analysis'],
          ['counterfactual','Counterfactual'],
        ] as [Tab, string][]).map(([id, label]) => (
          <button key={id} style={tab === id ? { ...tabBase, ...tabActive } : tabBase} onClick={() => setTab(id)}>
            {label}
          </button>
        ))}
      </div>

      {/* ── Tab: Group Profiles ────────────────────────────────────────── */}
      {tab === 'profiles' && (
        <div>
          {/* Dimension selector */}
          <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
            {dims.map(d => (
              <button
                key={d}
                onClick={() => setActiveDim(d)}
                style={{
                  background:      activeDim === d ? 'var(--navy)' : 'none',
                  color:           activeDim === d ? '#fff' : 'var(--text-muted)',
                  border:          '1px solid var(--border)',
                  borderRadius:    4,
                  padding:         '5px 14px',
                  fontSize:        11,
                  fontFamily:      'var(--fb)',
                  cursor:          'pointer',
                  letterSpacing:   '1px',
                  textTransform:   'uppercase',
                }}
              >
                {DIM_LABEL[d]}
              </button>
            ))}
          </div>

          {/* Metric toggle */}
          <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
            {([['avg_impact_score', 'Impact Score'], ['avg_attrition', 'Attrition Risk']] as ['avg_impact_score' | 'avg_attrition', string][]).map(([m, lbl]) => (
              <button
                key={m}
                onClick={() => setProfileMetric(m)}
                style={{
                  background:    profileMetric === m ? 'rgba(0,51,102,0.08)' : 'none',
                  color:         profileMetric === m ? 'var(--navy)' : 'var(--text-muted)',
                  border:        `1px solid ${profileMetric === m ? 'var(--navy)' : 'var(--border)'}`,
                  borderRadius:  4,
                  padding:       '4px 12px',
                  fontSize:      10,
                  fontFamily:    'var(--fb)',
                  cursor:        'pointer',
                  letterSpacing: '1px',
                  textTransform: 'uppercase',
                }}
              >
                {lbl}
              </button>
            ))}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
            {/* Profile bar chart */}
            <div style={{ backgroundColor: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 8, padding: 20 }}>
              <h3 style={{ fontFamily: 'var(--fb)', fontSize: 11, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 16, fontWeight: 500 }}>
                {DIM_LABEL[activeDim]} · {profileMetric === 'avg_impact_score' ? 'Avg Impact Score' : 'Avg Attrition Risk'}
              </h3>
              <GroupProfileChart profiles={group_profiles} dimension={activeDim} metric={profileMetric} />
            </div>

            {/* Group distribution */}
            <div style={{ backgroundColor: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 8, padding: 20 }}>
              <h3 style={{ fontFamily: 'var(--fb)', fontSize: 11, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 16, fontWeight: 500 }}>
                Group Distribution · {DIM_LABEL[activeDim]}
              </h3>
              {(() => {
                const distRows = protected_groups[activeDim] ?? []
                const total    = distRows.reduce((s, r) => s + r.count, 0)
                return distRows.map(r => (
                  <div key={r.group} style={{ marginBottom: 10 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                      <span style={{ fontSize: 11, color: 'var(--text-body)' }}>{r.group}</span>
                      <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                        {r.count} ({total > 0 ? ((r.count / total) * 100).toFixed(1) : '0'}%)
                      </span>
                    </div>
                    <div style={{ height: 8, borderRadius: 4, backgroundColor: 'var(--border)', overflow: 'hidden' }}>
                      <div style={{
                        height:          '100%',
                        width:           `${total > 0 ? (r.count / total) * 100 : 0}%`,
                        backgroundColor: 'var(--navy)',
                        opacity:         0.7,
                        borderRadius:    4,
                      }} />
                    </div>
                  </div>
                ))
              })()}

              {/* Simulation selection panel */}
              <h3 style={{ fontFamily: 'var(--fb)', fontSize: 11, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--text-muted)', marginTop: 24, marginBottom: 12, fontWeight: 500 }}>
                Simulated Selection (Top 40%)
              </h3>
              <SimPanel simAnalysis={simulation_analysis} dimension={activeDim} />
            </div>
          </div>

          {/* Full group profiles table */}
          <div style={{ marginTop: 24, backgroundColor: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 8, padding: 20 }}>
            <h3 style={{ fontFamily: 'var(--fb)', fontSize: 11, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 16, fontWeight: 500 }}>
              Detailed Profile — {DIM_LABEL[activeDim]}
            </h3>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)' }}>
                  {['Group', 'N', 'Avg Impact', 'Avg Attrition', 'Median Salary'].map(h => (
                    <th key={h} style={{ padding: '6px 10px', textAlign: 'left', fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 500 }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {group_profiles.filter(p => p.dimension === activeDim).map(p => (
                  <tr key={p.group} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td style={{ padding: '8px 10px', color: 'var(--text-body)', fontWeight: 500 }}>{p.group}</td>
                    <td style={{ padding: '8px 10px', color: 'var(--text-muted)' }}>{p.count}</td>
                    <td style={{ padding: '8px 10px', color: 'var(--navy)', fontWeight: 600 }}>{p.avg_impact_score.toFixed(1)}</td>
                    <td style={{ padding: '8px 10px', color: p.avg_attrition > 0.4 ? '#e03448' : 'var(--text-body)' }}>
                      {(p.avg_attrition * 100).toFixed(1)}%
                    </td>
                    <td style={{ padding: '8px 10px', color: 'var(--text-body)' }}>
                      ${p.median_salary.toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Tab: EEOC Analysis ─────────────────────────────────────────── */}
      {tab === 'eeoc' && (
        <div>
          <div style={{ backgroundColor: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 8, padding: 24, marginBottom: 20 }}>
            <h3 style={{ fontFamily: 'var(--fb)', fontSize: 11, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 4, fontWeight: 500 }}>
              EEOC 4/5ths (80%) Adverse Impact Rule
            </h3>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 20, lineHeight: 1.6 }}>
              The Adverse Impact Ratio (AIR) = selection rate of group ÷ selection rate of highest-performing group.
              An AIR below <strong style={{ color: '#e03448' }}>0.800</strong> is flagged under the EEOC Uniform Guidelines on Employee Selection Procedures.
              "Selection" is defined as scoring in the top 40% for impact score, or being flagged as high attrition risk.
              Chi-square tests significance of the group × selected contingency table.
            </p>

            {/* Legend */}
            <div style={{ display: 'flex', gap: 20, marginBottom: 20, flexWrap: 'wrap' }}>
              {[['#1a8c4e', 'AIR ≥ 0.95 — Strong pass'], ['#c8982a', '0.80 ≤ AIR < 0.95 — Marginal'], ['#e03448', 'AIR < 0.80 — FLAG']].map(([color, label]) => (
                <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <div style={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: color }} />
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{label}</span>
                </div>
              ))}
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ fontSize: 13 }}>✦</span>
                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Reference group (highest rate)</span>
              </div>
            </div>

            {/* Column headers */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '0 0 8px', borderBottom: '1px solid var(--border)' }}>
              <span style={{ fontSize: 10, color: 'var(--text-muted)', width: 120, letterSpacing: '1px', textTransform: 'uppercase' }}>Dimension</span>
              <span style={{ fontSize: 10, color: 'var(--text-muted)', width: 110, letterSpacing: '1px', textTransform: 'uppercase' }}>Model</span>
              <span style={{ flex: 1, fontSize: 10, color: 'var(--text-muted)', letterSpacing: '1px', textTransform: 'uppercase' }}>Min AIR</span>
              <span style={{ fontSize: 10, color: 'var(--text-muted)', width: 48, textAlign: 'right', letterSpacing: '1px', textTransform: 'uppercase' }}>AIR</span>
              <span style={{ fontSize: 10, color: 'var(--text-muted)', width: 56, textAlign: 'center', letterSpacing: '1px', textTransform: 'uppercase' }}>Status</span>
              <span style={{ fontSize: 10, color: 'var(--text-muted)', width: 52, textAlign: 'right', letterSpacing: '1px', textTransform: 'uppercase' }}>p-val</span>
              <span style={{ width: 20 }} />
            </div>

            {eeoc_analysis.map((row, i) => (
              <EEOCDetail key={i} row={row} />
            ))}
          </div>

          {/* Summary table */}
          <div style={{ backgroundColor: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 8, padding: 20 }}>
            <h3 style={{ fontFamily: 'var(--fb)', fontSize: 11, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 16, fontWeight: 500 }}>
              Summary by Dimension
            </h3>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)' }}>
                  {['Dimension', 'Impact Score', 'Attrition Risk', 'Flags'].map(h => (
                    <th key={h} style={{ padding: '6px 10px', textAlign: 'left', fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 500 }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {dims.map(dim => {
                  const dimRows = eeoc_analysis.filter(r => r.dimension === dim)
                  const impactRow = dimRows.find(r => r.score_col === 'impact_score')
                  const attrRow   = dimRows.find(r => r.score_col === 'attrition_risk')
                  const flags     = dimRows.filter(r => !r.eeoc_pass).length
                  return (
                    <tr key={dim} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td style={{ padding: '8px 10px', fontWeight: 500, color: 'var(--text-body)' }}>{DIM_LABEL[dim]}</td>
                      <td style={{ padding: '8px 10px' }}>
                        {impactRow && <span style={{ color: airColor(impactRow.min_air) }}>{impactRow.min_air.toFixed(3)}</span>}
                        {impactRow && <span style={{ marginLeft: 8 }}><PassBadge pass={impactRow.eeoc_pass} /></span>}
                      </td>
                      <td style={{ padding: '8px 10px' }}>
                        {attrRow && <span style={{ color: airColor(attrRow.min_air) }}>{attrRow.min_air.toFixed(3)}</span>}
                        {attrRow && <span style={{ marginLeft: 8 }}><PassBadge pass={attrRow.eeoc_pass} /></span>}
                      </td>
                      <td style={{ padding: '8px 10px', color: flags > 0 ? '#e03448' : '#1a8c4e', fontWeight: 600 }}>
                        {flags}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Tab: Counterfactual ────────────────────────────────────────── */}
      {tab === 'counterfactual' && (
        <div>
          <div style={{ backgroundColor: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 8, padding: 24, marginBottom: 20 }}>
            <h3 style={{ fontFamily: 'var(--fb)', fontSize: 11, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8, fontWeight: 500 }}>
              Counterfactual Fairness Methodology
            </h3>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.7, maxWidth: 720 }}>
              For each protected attribute, a random sample of 30 employees has their attribute label flipped
              (e.g., Male ↔ Female). Model scores are recomputed on the flipped data.
              Since neither <em>impact_score</em> nor <em>attrition_risk</em> use protected attributes as inputs,
              the score delta Δ = 0.000 exactly — demonstrating <strong style={{ color: '#1a8c4e' }}>counterfactual fairness</strong>.
              The 95% confidence interval (bootstrap) is reported for transparency.
              A result is marked FAIR if the CI contains 0 or |Δ| &lt; 0.5 points.
            </p>
            <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 10, fontStyle: 'italic' }}>
              Note: Counterfactual fairness at the individual level does not preclude group-level disparate impact.
              The EEOC analysis above captures the latter.
            </p>
          </div>

          <div style={{ backgroundColor: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 8, padding: 20 }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)' }}>
                  {['Attribute', 'Model', 'Sample', 'Mean Δ', 'Std Δ', '95% CI', 'CI spans 0', 'Verdict'].map(h => (
                    <th key={h} style={{ padding: '6px 10px', textAlign: 'left', fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 500 }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {counterfactual.map((row, i) => {
                  const ciSpans0 = row.ci_lower_95 <= 0 && row.ci_upper_95 >= 0
                  return (
                    <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td style={{ padding: '8px 10px', fontWeight: 500, color: 'var(--text-body)' }}>
                        {ATTR_LABEL[row.attribute] ?? row.attribute}
                      </td>
                      <td style={{ padding: '8px 10px', color: 'var(--text-muted)' }}>
                        {row.model === 'impact_score' ? 'Impact Score' : 'Attrition Risk'}
                      </td>
                      <td style={{ padding: '8px 10px', color: 'var(--text-muted)' }}>{row.sample_size}</td>
                      <td style={{ padding: '8px 10px', color: Math.abs(row.mean_delta) < 0.001 ? '#1a8c4e' : '#e03448', fontFamily: 'monospace' }}>
                        {row.mean_delta >= 0 ? '+' : ''}{row.mean_delta.toFixed(4)}
                      </td>
                      <td style={{ padding: '8px 10px', color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                        {row.std_delta.toFixed(4)}
                      </td>
                      <td style={{ padding: '8px 10px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <CIBar lo={row.ci_lower_95} hi={row.ci_upper_95} />
                          <span style={{ fontSize: 10, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                            [{row.ci_lower_95.toFixed(3)}, {row.ci_upper_95.toFixed(3)}]
                          </span>
                        </div>
                      </td>
                      <td style={{ padding: '8px 10px', color: ciSpans0 ? '#1a8c4e' : '#e03448', fontWeight: 600 }}>
                        {ciSpans0 ? 'Yes' : 'No'}
                      </td>
                      <td style={{ padding: '8px 10px' }}>
                        <PassBadge pass={row.is_fair} />
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* Flip maps reference */}
          <div style={{ marginTop: 20, backgroundColor: 'rgba(0,51,102,0.03)', border: '1px solid var(--border)', borderRadius: 8, padding: 16 }}>
            <h4 style={{ fontFamily: 'var(--fb)', fontSize: 10, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 10, fontWeight: 500 }}>
              Attribute Flip Mappings
            </h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
              {[
                { label: 'Gender', pairs: [['Male', 'Female'], ['Female', 'Male'], ['Non-binary', 'Non-binary']] },
                { label: 'Age Bracket', pairs: [['25–34', '45–54'], ['35–44', '55+'], ['45–54', '25–34'], ['55+', '35–44']] },
                { label: 'Ethnicity Proxy', pairs: [['Group A', 'Group D'], ['Group B', 'Group C'], ['Group C', 'Group B'], ['Group D', 'Group A']] },
              ].map(({ label, pairs }) => (
                <div key={label}>
                  <p style={{ fontSize: 11, fontWeight: 600, color: 'var(--navy)', marginBottom: 6 }}>{label}</p>
                  {pairs.map(([from, to]) => (
                    <p key={from} style={{ fontSize: 11, color: 'var(--text-muted)', margin: '2px 0' }}>
                      {from} → {to}
                    </p>
                  ))}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
