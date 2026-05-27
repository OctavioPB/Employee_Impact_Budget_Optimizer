import React, { useState, useEffect } from 'react'
import {
  api,
  ResilienceData,
  ResilienceSubScores,
  DeptResilience,
  DisruptionResult,
  CascadeEmployee,
  ResilienceIntervention,
  DisruptionPreset,
} from '../services/api'
import { useDemoStore } from '../stores/demoStore'

type Tab = 'scorecard' | 'disruptions' | 'cascade' | 'roadmap'

// ── Helpers ───────────────────────────────────────────────────────────────────

function gradeColor(grade: string): string {
  return grade === 'A' ? '#1a8c4e' : grade === 'B' ? '#2a7ab0' : grade === 'C' ? '#c8982a' : grade === 'D' ? '#e07030' : '#e03448'
}

function gradeLabel(grade: string): string {
  return { A: 'Excellent', B: 'Good', C: 'Moderate', D: 'Fragile', F: 'Critical' }[grade] ?? grade
}

function scoreColor(s: number): string {
  if (s >= 80) return '#1a8c4e'
  if (s >= 65) return '#2a7ab0'
  if (s >= 50) return '#c8982a'
  if (s >= 35) return '#e07030'
  return '#e03448'
}

function priorityColor(p: string): string {
  return p === 'critical' ? '#e03448' : p === 'high' ? '#e07030' : p === 'medium' ? '#c8982a' : '#1a8c4e'
}

function fmtMoney(v: number): string {
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`
  if (v >= 1_000)     return `$${(v / 1_000).toFixed(0)}K`
  return `$${v}`
}

const DIM_LABELS: Record<keyof ResilienceSubScores, string> = {
  skill_coverage:           'Skill Coverage',
  leadership_depth:         'Leadership Depth',
  knowledge_redundancy:     'Knowledge Redundancy',
  network_robustness:       'Network Robustness',
  attrition_concentration:  'Attrition Distribution',
  team_size_buffer:         'Team Size Buffer',
}

const DIM_DESCRIPTIONS: Record<keyof ResilienceSubScores, string> = {
  skill_coverage:           'Fraction of role types with ≥2 holders — single-role-holder concentration risk.',
  leadership_depth:         'Fraction of leadership roles with ≥2 succession candidates one level below.',
  knowledge_redundancy:     'Per-department average: fraction of role types with backup holders.',
  network_robustness:       'Nexus employee distribution across departments; inverse of concentration.',
  attrition_concentration:  'Inverse Gini of attrition risk — high score = risk evenly spread, not concentrated.',
  team_size_buffer:         'Fraction of teams above minimum viable headcount (3) by more than 20%.',
}

// ── Sub-score Gauge ───────────────────────────────────────────────────────────

function SubScoreGauge({ dim, score, weight }: { dim: keyof ResilienceSubScores; score: number; weight: number }) {
  const color = scoreColor(score)
  const arc   = (score / 100) * 180
  const r     = 36, cx = 50, cy = 50
  const toRad = (deg: number) => (deg - 180) * (Math.PI / 180)
  const arcX  = cx + r * Math.cos(toRad(arc))
  const arcY  = cy + r * Math.sin(toRad(arc))
  const large = arc > 90 ? 1 : 0

  return (
    <div style={{
      backgroundColor: 'var(--card-bg)', border: '1px solid var(--border)',
      borderRadius: 8, padding: '14px 16px', display: 'flex', flexDirection: 'column', alignItems: 'center',
    }}>
      <svg viewBox="0 0 100 58" style={{ width: 90, marginBottom: 4 }}>
        {/* Background arc */}
        <path
          d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
          fill="none" stroke="var(--border)" strokeWidth={8} strokeLinecap="round"
        />
        {/* Value arc */}
        {score > 0 && (
          <path
            d={`M ${cx - r} ${cy} A ${r} ${r} 0 ${large} 1 ${arcX} ${arcY}`}
            fill="none" stroke={color} strokeWidth={8} strokeLinecap="round"
          />
        )}
        <text x={cx} y={cy - 2} textAnchor="middle" fontSize={14} fontWeight={600}
          fill={color} fontFamily="Plus Jakarta Sans, sans-serif">
          {score.toFixed(0)}
        </text>
      </svg>
      <p style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: 'var(--text-muted)', textAlign: 'center', margin: '0 0 2px', fontWeight: 500 }}>
        {DIM_LABELS[dim]}
      </p>
      <p style={{ fontSize: 9, color: 'var(--text-muted)', margin: 0 }}>
        weight {(weight * 100).toFixed(0)}%
      </p>
    </div>
  )
}

// ── Resilience Trend Chart ────────────────────────────────────────────────────

function TrendChart({ trend }: { trend: ResilienceData['trend'] }) {
  if (trend.length === 0) return null
  const W = 560, H = 120, PAD_L = 32, PAD_R = 16, PAD_T = 12, PAD_B = 28
  const scores = trend.map(p => p.score)
  const min    = Math.floor(Math.min(...scores) / 10) * 10
  const max    = Math.ceil(Math.max(...scores) / 10) * 10
  const range  = max - min || 10

  const x  = (i: number) => PAD_L + (i / (trend.length - 1)) * (W - PAD_L - PAD_R)
  const y  = (s: number) => PAD_T + (1 - (s - min) / range) * (H - PAD_T - PAD_B)
  const pts = trend.map((p, i) => `${x(i)},${y(p.score)}`).join(' ')

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', display: 'block' }}>
      {/* Grid lines */}
      {[0, 25, 50, 75, 100].filter(v => v >= min && v <= max).map(v => (
        <g key={v}>
          <line x1={PAD_L} x2={W - PAD_R} y1={y(v)} y2={y(v)}
            stroke="var(--border)" strokeWidth={0.5} strokeDasharray="3,3" />
          <text x={PAD_L - 4} y={y(v) + 4} textAnchor="end" fontSize={8}
            fill="var(--text-muted)" fontFamily="Plus Jakarta Sans, sans-serif">{v}</text>
        </g>
      ))}
      {/* Area fill */}
      <polygon
        points={`${x(0)},${y(min)} ${pts} ${x(trend.length - 1)},${y(min)}`}
        fill="rgba(0,51,102,0.07)"
      />
      {/* Line */}
      <polyline points={pts} fill="none" stroke="var(--navy)" strokeWidth={1.5} />
      {/* Month labels (every 3rd) */}
      {trend.filter((_, i) => i % 3 === 0).map((p, i) => (
        <text key={p.month} x={x(i * 3)} y={H - 6} textAnchor="middle" fontSize={8}
          fill="var(--text-muted)" fontFamily="Plus Jakarta Sans, sans-serif">
          {p.month.slice(5)}
        </text>
      ))}
      {/* Current dot */}
      <circle cx={x(trend.length - 1)} cy={y(trend[trend.length - 1].score)}
        r={3} fill="var(--navy)" />
    </svg>
  )
}

// ── Department Breakdown Table ────────────────────────────────────────────────

function DeptTable({ rows }: { rows: DeptResilience[] }) {
  return (
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
      <thead>
        <tr style={{ borderBottom: '1px solid var(--border)' }}>
          {['Department', 'Score', 'Grade', 'N', 'Nexus', 'At Risk', 'Skill Cov', 'Ldr Depth', 'Net Robust'].map(h => (
            <th key={h} style={{ padding: '5px 10px', textAlign: 'left', fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 500 }}>
              {h}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map(r => (
          <tr key={r.department} style={{ borderBottom: '1px solid var(--border)' }}>
            <td style={{ padding: '7px 10px', fontWeight: 500, color: 'var(--text-body)' }}>{r.department}</td>
            <td style={{ padding: '7px 10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <div style={{ width: 60, height: 5, borderRadius: 3, backgroundColor: 'var(--border)', overflow: 'hidden' }}>
                  <div style={{ height: '100%', width: `${r.overall}%`, backgroundColor: scoreColor(r.overall), borderRadius: 3 }} />
                </div>
                <span style={{ fontSize: 11, color: scoreColor(r.overall), fontWeight: 600 }}>{r.overall.toFixed(0)}</span>
              </div>
            </td>
            <td style={{ padding: '7px 10px', color: gradeColor(r.grade), fontWeight: 700 }}>{r.grade}</td>
            <td style={{ padding: '7px 10px', color: 'var(--text-muted)' }}>{r.headcount}</td>
            <td style={{ padding: '7px 10px', color: r.nexus_count > 0 ? 'var(--gold-mid)' : 'var(--text-muted)' }}>{r.nexus_count}</td>
            <td style={{ padding: '7px 10px', color: r.at_risk_count > 0 ? '#e03448' : 'var(--text-muted)' }}>{r.at_risk_count}</td>
            <td style={{ padding: '7px 10px', color: scoreColor(r.sub_scores.skill_coverage) }}>{r.sub_scores.skill_coverage.toFixed(0)}</td>
            <td style={{ padding: '7px 10px', color: scoreColor(r.sub_scores.leadership_depth) }}>{r.sub_scores.leadership_depth.toFixed(0)}</td>
            <td style={{ padding: '7px 10px', color: scoreColor(r.sub_scores.network_robustness) }}>{r.sub_scores.network_robustness.toFixed(0)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

// ── Disruption Scenario Builder ───────────────────────────────────────────────

function DisruptionBuilder({
  presets,
  scenario,
  size,
  onResult,
}: {
  presets:   DisruptionPreset[]
  scenario:  string
  size:      string
  onResult:  (r: DisruptionResult) => void
}) {
  const [selected,   setSelected]   = useState<number | null>(null)
  const [running,    setRunning]    = useState(false)
  const [error,      setError]      = useState<string | null>(null)
  const [lastResult, setLastResult] = useState<DisruptionResult | null>(null)

  async function run(idx: number) {
    const p = presets[idx]
    setRunning(true)
    setError(null)
    setSelected(idx)
    try {
      const result = await api.resilience.runScenario(scenario, size, p.type, p.params)
      setLastResult(result)
      onResult(result)
    } catch (e) {
      setError(String(e))
    } finally {
      setRunning(false)
    }
  }

  return (
    <div>
      <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16, lineHeight: 1.6 }}>
        Select a disruption scenario to stress-test the organization. Each scenario simulates
        primary departures and up to three rounds of cascade effects.
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 24 }}>
        {presets.map((p, i) => (
          <div
            key={i}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              border: `1px solid ${selected === i ? 'var(--navy)' : 'var(--border)'}`,
              borderRadius: 6, padding: '12px 16px', cursor: 'pointer',
              backgroundColor: selected === i ? 'rgba(0,51,102,0.04)' : 'var(--card-bg)',
              transition: 'border-color 0.15s',
            }}
            onClick={() => !running && run(i)}
          >
            <div>
              <p style={{ fontWeight: 600, color: 'var(--navy)', fontSize: 13, margin: '0 0 3px' }}>{p.label}</p>
              <p style={{ fontSize: 10, color: 'var(--text-muted)', margin: 0, fontFamily: 'var(--fb)', letterSpacing: '1px', textTransform: 'uppercase' }}>
                {p.type.replace(/_/g, ' ')}
              </p>
            </div>
            {selected === i && running ? (
              <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--fb)' }}>Running…</span>
            ) : (
              <button
                style={{
                  border: '1px solid var(--navy)', borderRadius: 4, padding: '5px 14px',
                  background: 'var(--navy)', color: '#fff', cursor: 'pointer',
                  fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase',
                }}
                onClick={e => { e.stopPropagation(); run(i) }}
                disabled={running}
              >
                Run
              </button>
            )}
          </div>
        ))}
      </div>

      {error && (
        <p style={{ color: '#e03448', fontSize: 12 }}>{error}</p>
      )}

      {lastResult && (
        <DisruptionSummaryCard result={lastResult} />
      )}
    </div>
  )
}

// ── Disruption Summary Card ───────────────────────────────────────────────────

function DisruptionSummaryCard({ result }: { result: DisruptionResult }) {
  const deltaColor = result.resilience_delta < -15 ? '#e03448' : result.resilience_delta < -5 ? '#e07030' : '#c8982a'

  return (
    <div style={{ border: '1px solid var(--border)', borderRadius: 8, padding: 20, backgroundColor: 'var(--card-bg)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
        <h3 style={{ fontFamily: 'var(--fd)', fontSize: 16, fontWeight: 300, color: 'var(--navy)', margin: 0 }}>
          {result.scenario_label}
        </h3>
        <span style={{ fontSize: 10, color: deltaColor, fontFamily: 'var(--fb)', fontWeight: 600, border: `1px solid ${deltaColor}`, borderRadius: 4, padding: '2px 7px' }}>
          Resilience {result.resilience_delta.toFixed(1)}
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 16 }}>
        {[
          ['Primary', result.primary_count, ''],
          ['Total Departed', result.total_departed, ''],
          ['Cascade ×', result.cascade_multiplier.toFixed(2), ''],
          ['Financial Impact', fmtMoney(result.financial_impact), ''],
        ].map(([label, val]) => (
          <div key={label as string} style={{ textAlign: 'center' }}>
            <p style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--navy)', margin: '0 0 3px' }}>{val as string}</p>
            <p style={{ fontSize: 9, color: 'var(--text-muted)', margin: 0, fontFamily: 'var(--fb)', letterSpacing: '1px', textTransform: 'uppercase' }}>{label as string}</p>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        {result.orphaned_skills.length > 0 && (
          <div>
            <p style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 6, fontWeight: 500 }}>
              Orphaned Roles
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
              {result.orphaned_skills.slice(0, 6).map(s => (
                <span key={s} style={{ fontSize: 10, padding: '2px 7px', backgroundColor: 'rgba(224,52,72,0.08)', color: '#e03448', borderRadius: 3, border: '1px solid rgba(224,52,72,0.2)' }}>
                  {s.length > 30 ? s.slice(0, 29) + '…' : s}
                </span>
              ))}
            </div>
          </div>
        )}
        {result.cascade_amplifiers.length > 0 && (
          <div>
            <p style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 6, fontWeight: 500 }}>
              Top Cascade Amplifiers
            </p>
            {result.cascade_amplifiers.slice(0, 3).map(a => (
              <div key={a.employee_id} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 3 }}>
                <span style={{ color: 'var(--text-body)' }}>{a.full_name}</span>
                <span style={{ color: '#e07030', fontWeight: 600 }}>+{a.secondary_triggered} secondary</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ display: 'flex', gap: 12, marginTop: 14, alignItems: 'center' }}>
        <div style={{ flex: 1 }}>
          <p style={{ fontSize: 9, fontFamily: 'var(--fb)', letterSpacing: '1px', color: 'var(--text-muted)', marginBottom: 3 }}>BEFORE</p>
          <div style={{ height: 8, borderRadius: 4, backgroundColor: 'var(--border)', overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${result.resilience_before}%`, backgroundColor: scoreColor(result.resilience_before), transition: 'width 0.3s' }} />
          </div>
          <p style={{ fontSize: 10, color: scoreColor(result.resilience_before), fontWeight: 600, marginTop: 2 }}>{result.resilience_before.toFixed(1)}</p>
        </div>
        <span style={{ fontSize: 16, color: 'var(--text-muted)' }}>→</span>
        <div style={{ flex: 1 }}>
          <p style={{ fontSize: 9, fontFamily: 'var(--fb)', letterSpacing: '1px', color: 'var(--text-muted)', marginBottom: 3 }}>AFTER</p>
          <div style={{ height: 8, borderRadius: 4, backgroundColor: 'var(--border)', overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${result.resilience_after}%`, backgroundColor: scoreColor(result.resilience_after), transition: 'width 0.3s' }} />
          </div>
          <p style={{ fontSize: 10, color: scoreColor(result.resilience_after), fontWeight: 600, marginTop: 2 }}>{result.resilience_after.toFixed(1)}</p>
        </div>
      </div>
    </div>
  )
}

// ── Cascade Visualization ─────────────────────────────────────────────────────
// SVG funnel: horizontal band per round, employees as circles

const ROUND_COLORS = ['#003366', '#e07030', '#c8982a', '#aaaaaa']
const ROUND_LABELS = ['Primary\n(Scenario Trigger)', 'Round 1\n(Direct Cascade)', 'Round 2\n(Secondary)', 'Round 3\n(Tertiary)']

function CascadeViz({ result }: { result: DisruptionResult }) {
  const allRounds: { round: number; employees: CascadeEmployee[] }[] = [
    { round: 0, employees: result.primary_employees },
    ...result.cascade_rounds,
  ]

  const maxPerRow = 12
  const CELL_W = 60, CELL_H = 80
  const LEFT = 140, PAD_Y = 20
  const totalH = allRounds.length * (CELL_H + PAD_Y) + PAD_Y

  const rowCount = (n: number) => Math.ceil(n / maxPerRow)
  let cumH = PAD_Y

  return (
    <div style={{ overflowX: 'auto' }}>
      <svg
        viewBox={`0 0 ${LEFT + maxPerRow * CELL_W + 20} ${totalH}`}
        style={{ minWidth: LEFT + maxPerRow * CELL_W + 20, display: 'block' }}
      >
        {allRounds.map((round) => {
          const employees = round.employees.slice(0, maxPerRow)
          const color     = ROUND_COLORS[round.round] ?? '#aaa'
          const label     = ROUND_LABELS[round.round] ?? `Round ${round.round}`
          const bandH     = rowCount(employees.length) * CELL_H + 10
          const bandY     = cumH
          cumH += bandH + PAD_Y

          return (
            <g key={round.round}>
              {/* Band background */}
              <rect
                x={0} y={bandY}
                width={LEFT + maxPerRow * CELL_W + 20}
                height={bandH}
                fill={color} opacity={0.05} rx={6}
              />
              {/* Round label */}
              {label.split('\n').map((line, li) => (
                <text
                  key={li}
                  x={LEFT - 10}
                  y={bandY + 22 + li * 13}
                  textAnchor="end"
                  fontSize={9}
                  fill={color}
                  fontFamily="Plus Jakarta Sans, sans-serif"
                  fontWeight={600}
                >
                  {line}
                </text>
              ))}
              <text x={LEFT - 10} y={bandY + 52} textAnchor="end" fontSize={10} fill={color} fontFamily="Plus Jakarta Sans, sans-serif" fontWeight={700}>
                {round.employees.length}
              </text>
              {/* Connector arrow from previous round */}
              {round.round > 0 && (
                <line
                  x1={LEFT + 10} y1={bandY - PAD_Y / 2}
                  x2={LEFT + 10} y2={bandY}
                  stroke={color} strokeWidth={1.5} strokeDasharray="4,3" opacity={0.5}
                />
              )}
              {/* Employee circles */}
              {employees.map((emp, i) => {
                const col = i % maxPerRow
                const cx  = LEFT + col * CELL_W + CELL_W / 2
                const cy  = bandY + 30
                return (
                  <g key={emp.employee_id}>
                    <circle cx={cx} cy={cy} r={14} fill={color} opacity={0.15} />
                    <circle cx={cx} cy={cy} r={14} fill="none" stroke={color} strokeWidth={emp.is_nexus ? 2.5 : 1} />
                    {emp.is_nexus && (
                      <circle cx={cx} cy={cy} r={4} fill={color} opacity={0.6} />
                    )}
                    <text x={cx} y={cy + 4} textAnchor="middle" fontSize={7}
                      fill={color} fontFamily="Plus Jakarta Sans, sans-serif">
                      {emp.full_name.split(' ')[0].slice(0, 7)}
                    </text>
                    <text x={cx} y={cy + 26} textAnchor="middle" fontSize={7}
                      fill="var(--text-muted)" fontFamily="Plus Jakarta Sans, sans-serif">
                      {emp.department.slice(0, 8)}
                    </text>
                  </g>
                )
              })}
              {round.employees.length > maxPerRow && (
                <text
                  x={LEFT + maxPerRow * CELL_W - 10}
                  y={bandY + 34}
                  fontSize={9}
                  fill={color}
                  fontFamily="Plus Jakarta Sans, sans-serif"
                >
                  +{round.employees.length - maxPerRow} more
                </text>
              )}
            </g>
          )
        })}
      </svg>
    </div>
  )
}

// ── Intervention Roadmap ──────────────────────────────────────────────────────

function InterventionRoadmap({ interventions }: { interventions: ResilienceIntervention[] }) {
  if (interventions.length === 0) {
    return (
      <div style={{ padding: '32px', textAlign: 'center', border: '1px dashed var(--border)', borderRadius: 8 }}>
        <p style={{ fontSize: 13, color: '#1a8c4e', fontWeight: 600 }}>All resilience dimensions above threshold.</p>
        <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>No interventions required at this time.</p>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {interventions.map((iv, i) => (
        <div key={iv.dimension} style={{
          backgroundColor: 'var(--card-bg)', border: `1px solid var(--border)`,
          borderLeft: `3px solid ${priorityColor(iv.priority)}`,
          borderRadius: 8, padding: '16px 20px',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
                <span style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: priorityColor(iv.priority), fontWeight: 600 }}>
                  {iv.priority}
                </span>
                <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--navy)' }}>{iv.dimension_label}</span>
                <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>current: {iv.current_score.toFixed(0)}</span>
              </div>
              <p style={{ fontSize: 12, color: 'var(--text-body)', margin: 0, lineHeight: 1.6, maxWidth: 620 }}>
                {iv.description}
              </p>
            </div>
            <div style={{ textAlign: 'right', flexShrink: 0, marginLeft: 16 }}>
              <p style={{ fontFamily: 'var(--fd)', fontSize: 20, fontWeight: 300, color: '#1a8c4e', margin: '0 0 2px' }}>
                +{iv.score_improvement.toFixed(1)}
              </p>
              <p style={{ fontSize: 9, color: 'var(--text-muted)', margin: 0, fontFamily: 'var(--fb)', letterSpacing: '1px', textTransform: 'uppercase' }}>score pts</p>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
            {[
              ['Cost', fmtMoney(iv.cost)],
              ['ROI', iv.roi.toFixed(2) + '×'],
              ['Timeline', iv.timeline_months + ' months'],
            ].map(([label, val]) => (
              <div key={label as string}>
                <span style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--fb)', letterSpacing: '1px', textTransform: 'uppercase' }}>
                  {label as string}:
                </span>
                {' '}
                <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-body)' }}>{val as string}</span>
              </div>
            ))}
            <div>
              <span style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--fb)', letterSpacing: '1px', textTransform: 'uppercase' }}>
                Priority Rank:
              </span>
              {' '}
              <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--navy)' }}>#{i + 1}</span>
            </div>
          </div>

          {/* Score improvement bar */}
          <div style={{ marginTop: 10 }}>
            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              <div style={{ flex: 1, height: 5, borderRadius: 3, backgroundColor: 'var(--border)', overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${iv.current_score}%`, backgroundColor: scoreColor(iv.current_score), borderRadius: 3 }} />
              </div>
              <span style={{ fontSize: 9, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>current</span>
            </div>
            <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginTop: 3 }}>
              <div style={{ flex: 1, height: 5, borderRadius: 3, backgroundColor: 'var(--border)', overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${Math.min(100, iv.current_score + iv.score_improvement)}%`, backgroundColor: '#1a8c4e', borderRadius: 3 }} />
              </div>
              <span style={{ fontSize: 9, color: '#1a8c4e', whiteSpace: 'nowrap' }}>after</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function ResiliencePage() {
  const { scenario, size } = useDemoStore()
  const [data,    setData]    = useState<ResilienceData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState<string | null>(null)
  const [tab,     setTab]     = useState<Tab>('scorecard')
  const [lastRun, setLastRun] = useState<DisruptionResult | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    api.resilience.data(scenario, size)
      .then(d => { setData(d); setLoading(false) })
      .catch(e => { setError(String(e)); setLoading(false) })
  }, [scenario, size])

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 300 }}>
      <span style={{ fontFamily: 'var(--fb)', fontSize: 12, letterSpacing: '2px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
        Computing resilience score…
      </span>
    </div>
  )
  if (error || !data) return (
    <div style={{ padding: 40, color: '#e03448', fontFamily: 'var(--fb)', fontSize: 13 }}>
      {error ?? 'No data'}
    </div>
  )

  const { summary, org_resilience, dept_resilience, interventions, disruption_presets, trend } = data

  const tabStyle = (active: boolean): React.CSSProperties => ({
    background: 'none', border: 'none', cursor: 'pointer',
    fontFamily: 'var(--fb)', fontSize: 10, letterSpacing: '2px',
    textTransform: 'uppercase', padding: '8px 16px',
    borderBottom: active ? '2px solid var(--navy)' : '2px solid transparent',
    color: active ? 'var(--navy)' : 'var(--text-muted)',
    transition: 'color 0.15s',
  })

  return (
    <div style={{ padding: '32px 40px', maxWidth: 1280, margin: '0 auto' }}>

      {/* Page header */}
      <div style={{ marginBottom: 28 }}>
        <p style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '3px', textTransform: 'uppercase', color: 'var(--gold-mid)', marginBottom: 6 }}>
          Sprint 15 · Workforce Resilience
        </p>
        <h1 style={{ fontFamily: 'var(--fd)', fontWeight: 300, fontSize: 28, color: 'var(--navy)', margin: 0 }}>
          Resilience Stress Testing
        </h1>
        <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 6, maxWidth: 680 }}>
          Six-dimension organizational resilience score with adversarial disruption modeling,
          three-round cascade simulation, and targeted intervention roadmap.
        </p>
      </div>

      {/* Hero KPIs */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 28 }}>
        <div style={{
          backgroundColor: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 8, padding: '16px 20px',
          gridColumn: '1 / 2',
        }}>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--text-muted)', margin: '0 0 6px' }}>
            Overall Resilience
          </p>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
            <span style={{ fontFamily: 'var(--fd)', fontSize: 36, fontWeight: 300, color: scoreColor(summary.overall_resilience), lineHeight: 1 }}>
              {summary.overall_resilience.toFixed(1)}
            </span>
            <span style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: gradeColor(org_resilience.grade) }}>
              {org_resilience.grade}
            </span>
          </div>
          <p style={{ fontSize: 11, color: gradeColor(org_resilience.grade), margin: '4px 0 0', fontWeight: 600 }}>
            {gradeLabel(org_resilience.grade)}
          </p>
        </div>

        {[
          { label: 'Nexus Employees', value: summary.nexus_count, sub: 'single-point-of-failure risk', color: 'var(--gold-mid)' },
          { label: 'At-Risk Teams',   value: summary.at_risk_teams, sub: 'avg attrition > 50%', color: summary.at_risk_teams > 0 ? '#e07030' : '#1a8c4e' },
          { label: 'Interventions',   value: summary.intervention_count, sub: 'dimensions below threshold', color: summary.intervention_count > 0 ? '#c8982a' : '#1a8c4e' },
        ].map(k => (
          <div key={k.label} style={{ backgroundColor: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 8, padding: '16px 20px' }}>
            <p style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--text-muted)', margin: '0 0 8px' }}>
              {k.label}
            </p>
            <p style={{ fontFamily: 'var(--fd)', fontSize: 28, fontWeight: 300, color: k.color, margin: '0 0 4px' }}>
              {k.value}
            </p>
            <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: 0 }}>{k.sub}</p>
          </div>
        ))}
      </div>

      {/* Tab bar */}
      <div style={{ borderBottom: '1px solid var(--border)', display: 'flex', gap: 0, marginBottom: 28 }}>
        {([
          ['scorecard',   'Scorecard'],
          ['disruptions', 'Disruption Scenarios'],
          ['cascade',     lastRun ? `Cascade (${lastRun.total_departed} departed)` : 'Cascade'],
          ['roadmap',     `Roadmap (${interventions.length})`],
        ] as [Tab, string][]).map(([id, label]) => (
          <button key={id} style={tabStyle(tab === id)} onClick={() => setTab(id)}>
            {label}
          </button>
        ))}
      </div>

      {/* ── Tab: Scorecard ─────────────────────────────────────────────── */}
      {tab === 'scorecard' && (
        <div>
          {/* 6 sub-dimension gauges */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 12, marginBottom: 24 }}>
            {(Object.keys(org_resilience.sub_scores) as (keyof ResilienceSubScores)[]).map(dim => (
              <SubScoreGauge
                key={dim}
                dim={dim}
                score={org_resilience.sub_scores[dim]}
                weight={org_resilience.weights[dim]}
              />
            ))}
          </div>

          {/* Dimension explanations */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 24 }}>
            {(Object.keys(org_resilience.sub_scores) as (keyof ResilienceSubScores)[]).map(dim => (
              <div key={dim} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                <div style={{
                  width: 6, height: 6, borderRadius: '50%', marginTop: 5, flexShrink: 0,
                  backgroundColor: scoreColor(org_resilience.sub_scores[dim]),
                }} />
                <div>
                  <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-body)' }}>{DIM_LABELS[dim]}</span>
                  {' '}
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{DIM_DESCRIPTIONS[dim]}</span>
                </div>
              </div>
            ))}
          </div>

          {/* Trend chart */}
          <div style={{ backgroundColor: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 8, padding: '20px 20px 12px', marginBottom: 24 }}>
            <h3 style={{ fontFamily: 'var(--fb)', fontSize: 11, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 14, fontWeight: 500 }}>
              12-Month Resilience Trend
            </h3>
            <TrendChart trend={trend} />
          </div>

          {/* Department breakdown */}
          <div style={{ backgroundColor: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 8, padding: 20 }}>
            <h3 style={{ fontFamily: 'var(--fb)', fontSize: 11, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 16, fontWeight: 500 }}>
              Department Breakdown — sorted by resilience (lowest first)
            </h3>
            <DeptTable rows={dept_resilience} />
          </div>
        </div>
      )}

      {/* ── Tab: Disruption Scenarios ──────────────────────────────────── */}
      {tab === 'disruptions' && (
        <div style={{ display: 'grid', gridTemplateColumns: '420px 1fr', gap: 24 }}>
          <DisruptionBuilder
            presets={disruption_presets}
            scenario={scenario}
            size={size}
            onResult={r => { setLastRun(r); setTab('cascade') }}
          />
          <div>
            <div style={{ backgroundColor: 'rgba(0,51,102,0.03)', border: '1px solid var(--border)', borderRadius: 8, padding: 20 }}>
              <h3 style={{ fontFamily: 'var(--fb)', fontSize: 11, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 14, fontWeight: 500 }}>
                Scenario Methodology
              </h3>
              {[
                ['Targeted Departure', 'Removes the N employees with the highest impact score simultaneously. Tests the cost of losing your most valuable contributors.'],
                ['Department Shock', 'Removes a random percentage of one department. Simulates team-level disruption from reorganization or market competition.'],
                ['Competitive Poaching', 'Removes high-impact employees who could be recruited by a competitor. Targets employees above a configurable impact threshold.'],
                ['Leadership Vacuum', 'Removes all employees at lead, director, and exec seniority levels. Tests organizational resilience to management loss.'],
                ['Role/Skill Crisis', 'Removes all employees sharing the most common role title. Tests single-role-type concentration risk.'],
              ].map(([label, desc]) => (
                <div key={label as string} style={{ marginBottom: 12 }}>
                  <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--navy)', margin: '0 0 3px' }}>{label as string}</p>
                  <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: 0, lineHeight: 1.6 }}>{desc as string}</p>
                </div>
              ))}
              <div style={{ marginTop: 14, paddingTop: 14, borderTop: '1px solid var(--border)' }}>
                <p style={{ fontSize: 11, fontWeight: 600, color: 'var(--navy)', margin: '0 0 4px' }}>Cascade Simulation</p>
                <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: 0, lineHeight: 1.6 }}>
                  After primary departures, up to 3 cascade rounds propagate: nexus departure adds 0.28 pressure
                  to same-department employees; leadership departure adds 0.22 to direct reports.
                  An employee departs if <code style={{ fontFamily: 'monospace', fontSize: 10 }}>attrition_risk + pressure &gt; 0.75</code>.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Tab: Cascade Visualization ─────────────────────────────────── */}
      {tab === 'cascade' && (
        <div>
          {!lastRun ? (
            <div style={{ padding: '48px 32px', textAlign: 'center', border: '1px dashed var(--border)', borderRadius: 8 }}>
              <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 12 }}>
                No disruption scenario has been run yet.
              </p>
              <button
                style={{ border: '1px solid var(--navy)', borderRadius: 4, padding: '7px 18px', background: 'var(--navy)', color: '#fff', cursor: 'pointer', fontFamily: 'var(--fb)', fontSize: 10, letterSpacing: '1.5px', textTransform: 'uppercase' }}
                onClick={() => setTab('disruptions')}
              >
                Go to Disruption Scenarios
              </button>
            </div>
          ) : (
            <>
              <div style={{ marginBottom: 20 }}>
                <DisruptionSummaryCard result={lastRun} />
              </div>

              <div style={{ backgroundColor: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 8, padding: 20 }}>
                <h3 style={{ fontFamily: 'var(--fb)', fontSize: 11, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 6, fontWeight: 500 }}>
                  Cascade Propagation — {lastRun.scenario_label}
                </h3>
                <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 16 }}>
                  Each band represents one departure wave. Filled circles = nexus employees. Arrows show cascade direction.
                </p>
                <CascadeViz result={lastRun} />
              </div>

              {/* Amplifier table */}
              {lastRun.cascade_amplifiers.length > 0 && (
                <div style={{ marginTop: 16, backgroundColor: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 8, padding: 20 }}>
                  <h3 style={{ fontFamily: 'var(--fb)', fontSize: 11, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 14, fontWeight: 500 }}>
                    Cascade Amplifiers — who triggers the most secondary departures?
                  </h3>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid var(--border)' }}>
                        {['Employee', 'Department', 'Impact', 'Nexus', 'Secondary Triggered'].map(h => (
                          <th key={h} style={{ padding: '5px 10px', textAlign: 'left', fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 500 }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {lastRun.cascade_amplifiers.map(a => (
                        <tr key={a.employee_id} style={{ borderBottom: '1px solid var(--border)' }}>
                          <td style={{ padding: '7px 10px', fontWeight: 500, color: 'var(--text-body)' }}>{a.full_name}</td>
                          <td style={{ padding: '7px 10px', color: 'var(--text-muted)' }}>{a.department}</td>
                          <td style={{ padding: '7px 10px', color: 'var(--navy)' }}>{a.impact_score.toFixed(0)}</td>
                          <td style={{ padding: '7px 10px', color: a.is_nexus ? 'var(--gold-mid)' : 'var(--text-muted)' }}>
                            {a.is_nexus ? '◆ Nexus' : '—'}
                          </td>
                          <td style={{ padding: '7px 10px', fontWeight: 600, color: a.secondary_triggered > 0 ? '#e07030' : 'var(--text-muted)' }}>
                            {a.secondary_triggered > 0 ? `+${a.secondary_triggered}` : '0'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Tab: Roadmap ───────────────────────────────────────────────── */}
      {tab === 'roadmap' && (
        <div>
          <div style={{ backgroundColor: 'rgba(0,51,102,0.03)', border: '1px solid var(--border)', borderRadius: 8, padding: '12px 18px', marginBottom: 20, fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.6 }}>
            Interventions target dimensions scoring below 80. Ranked by{' '}
            <strong>ROI = score_improvement / (cost / $10K)</strong>.
            All costs are estimates; timeline assumes dedicated part-time resource allocation.
          </div>
          <InterventionRoadmap interventions={interventions} />
        </div>
      )}
    </div>
  )
}
