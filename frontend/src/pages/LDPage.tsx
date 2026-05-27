import React, { useState, useEffect } from 'react'
import {
  api,
  LDData,
  LDOptimizationResult,
  TrainingAllocation,
  ParetoPoint,
  SkillGapRow,
  ROIRecord,
  EmployeePreview,
  TrainingProgramEffectiveness,
} from '../services/api'
import { useDemoStore } from '../stores/demoStore'

type Tab = 'optimizer' | 'preview' | 'gaps' | 'roi'

// ── Track color map ────────────────────────────────────────────────────────────

const TRACK_COLORS: Record<string, string> = {
  'Technical':        '#2a7ab0',
  'Data & Analytics': '#6a42a8',
  'Leadership':       '#1a8c4e',
  'Product & Business':'#c8982a',
  'Communication':    '#2a8ab0',
}
const TRACK_BG: Record<string, string> = {
  'Technical':        'rgba(42,122,176,0.12)',
  'Data & Analytics': 'rgba(106,66,168,0.12)',
  'Leadership':       'rgba(26,140,78,0.12)',
  'Product & Business':'rgba(200,152,42,0.12)',
  'Communication':    'rgba(42,138,176,0.12)',
}

function trackColor(track: string): string  { return TRACK_COLORS[track] ?? '#888' }
function trackBg(track: string): string     { return TRACK_BG[track]     ?? 'rgba(128,128,128,0.1)' }

function severityColor(sev: string): string {
  return sev === 'critical' ? '#e03448' : sev === 'high' ? '#e07030' : sev === 'medium' ? '#c8982a' : '#2a7ab0'
}

function roiStatusColor(status: string): string {
  return status === 'above_forecast' ? '#1a8c4e' : status === 'below_forecast' ? '#e03448' : '#c8982a'
}

function fmt(n: number): string { return n.toLocaleString(undefined, { maximumFractionDigits: 0 }) }
function fmtK(n: number): string { return `$${(n / 1000).toFixed(0)}K` }
function pct(n: number): string  { return `${(n * 100).toFixed(1)}%` }

// ── Pareto Curve (SVG) ────────────────────────────────────────────────────────

function ParetoCurve({ points }: { points: ParetoPoint[] }) {
  if (points.length === 0) return null
  const W = 480; const H = 200; const PAD = { top: 16, right: 16, bottom: 36, left: 52 }
  const innerW = W - PAD.left - PAD.right
  const innerH = H - PAD.top  - PAD.bottom

  const maxScore = Math.max(...points.map(p => p.combined_score))
  const minScore = Math.min(...points.map(p => p.combined_score)) * 0.9

  const xScale = (pct: number) => PAD.left + (pct / 100) * innerW
  const yScale = (v: number)   => PAD.top  + innerH - ((v - minScore) / (maxScore - minScore + 0.001)) * innerH

  // Retention area (bottom)
  const retPath = [
    `M ${xScale(points[0].ld_pct)} ${yScale(0)}`,
    ...points.map(p => `L ${xScale(p.ld_pct)} ${yScale(p.retention_impact / maxScore * maxScore * 0.5)}`),
    `L ${xScale(points[points.length-1].ld_pct)} ${yScale(0)}`, 'Z'
  ].join(' ')

  // Combined score line
  const linePath = points.map((p, i) =>
    `${i === 0 ? 'M' : 'L'} ${xScale(p.ld_pct)} ${yScale(p.combined_score)}`
  ).join(' ')

  // Find optimal point (max combined_score)
  const optimal = points.reduce((best, p) => p.combined_score > best.combined_score ? p : best, points[0])

  return (
    <svg width={W} height={H} style={{ display: 'block' }}>
      {/* Retention area */}
      <path d={retPath} fill="rgba(42,122,176,0.15)" />
      {/* Combined line */}
      <path d={linePath} fill="none" stroke="var(--gold-light)" strokeWidth={2.5} />
      {/* Points */}
      {points.map((p, i) => (
        <circle key={i} cx={xScale(p.ld_pct)} cy={yScale(p.combined_score)}
          r={p.ld_pct === optimal.ld_pct ? 5 : 3}
          fill={p.ld_pct === optimal.ld_pct ? 'var(--gold-light)' : 'var(--gold-light)'}
          opacity={p.ld_pct === optimal.ld_pct ? 1 : 0.55}
        />
      ))}
      {/* Optimal drop line */}
      <line x1={xScale(optimal.ld_pct)} y1={yScale(optimal.combined_score)}
            x2={xScale(optimal.ld_pct)} y2={PAD.top + innerH}
            stroke="var(--gold-light)" strokeDasharray="3 3" strokeWidth={1} opacity={0.5} />
      {/* X axis */}
      <line x1={PAD.left} y1={PAD.top+innerH} x2={PAD.left+innerW} y2={PAD.top+innerH}
            stroke="rgba(255,255,255,0.12)" strokeWidth={1} />
      {/* X labels */}
      {[0, 25, 50, 75, 100].map(v => (
        <text key={v} x={xScale(v)} y={H - 6} textAnchor="middle"
          style={{ fontSize: 9, fill: 'rgba(255,255,255,0.4)', fontFamily: 'var(--fb)' }}>
          {v}%
        </text>
      ))}
      {/* Y axis label */}
      <text x={12} y={H/2} textAnchor="middle" transform={`rotate(-90,12,${H/2})`}
        style={{ fontSize: 9, fill: 'rgba(255,255,255,0.4)', fontFamily: 'var(--fb)' }}>
        COMBINED SCORE
      </text>
      {/* Optimal label */}
      <text x={xScale(optimal.ld_pct)} y={yScale(optimal.combined_score) - 8} textAnchor="middle"
        style={{ fontSize: 8, fill: 'var(--gold-light)', fontFamily: 'var(--fb)' }}>
        OPTIMAL {optimal.ld_pct}% L&D
      </text>
      {/* X axis title */}
      <text x={PAD.left + innerW / 2} y={H - 2} textAnchor="middle"
        style={{ fontSize: 9, fill: 'rgba(255,255,255,0.35)', fontFamily: 'var(--fb)' }}>
        % OF BUDGET ALLOCATED TO L&D
      </text>
    </svg>
  )
}

// ── Track badge ────────────────────────────────────────────────────────────────

function TrackBadge({ track }: { track: string }) {
  return (
    <span style={{
      display: 'inline-block', padding: '2px 7px',
      borderRadius: 3, fontSize: 8, fontWeight: 700,
      letterSpacing: '1px', textTransform: 'uppercase',
      color: trackColor(track), backgroundColor: trackBg(track),
      fontFamily: 'var(--fb)',
    }}>
      {track}
    </span>
  )
}

// ── Allocation table ──────────────────────────────────────────────────────────

function AllocationTable({ allocations }: { allocations: TrainingAllocation[] }) {
  if (allocations.length === 0) return (
    <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: 12, padding: '16px 0' }}>
      No training allocations — try increasing the budget.
    </p>
  )

  const cols: React.CSSProperties = {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr 130px 70px 70px 60px 60px',
    gap: '0 12px',
    alignItems: 'center',
    padding: '8px 12px',
    fontFamily: 'var(--fb)',
    fontSize: 11,
  }
  const hdr: React.CSSProperties = {
    ...cols,
    borderBottom: '1px solid rgba(255,255,255,0.08)',
    color: 'rgba(255,255,255,0.35)',
    fontSize: 8,
    letterSpacing: '1.5px',
    textTransform: 'uppercase',
    paddingBottom: 6,
  }

  return (
    <div style={{ maxHeight: 340, overflowY: 'auto' }}>
      <div style={hdr}>
        <span>EMPLOYEE</span><span>PROGRAM</span><span>TRACK</span>
        <span style={{ textAlign: 'right' }}>COST</span>
        <span style={{ textAlign: 'right' }}>IMPACT +</span>
        <span style={{ textAlign: 'right' }}>ATTR −</span>
        <span style={{ textAlign: 'right' }}>ROI</span>
      </div>
      {allocations.map((a, i) => (
        <div key={i} style={{
          ...cols,
          backgroundColor: i % 2 === 0 ? 'rgba(255,255,255,0.02)' : 'transparent',
          borderRadius: 4,
        }}>
          <div>
            <div style={{ fontWeight: 600, color: 'var(--light)' }}>{a.full_name}</div>
            <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.4)', marginTop: 1 }}>
              {a.department} · {a.seniority_level}
            </div>
          </div>
          <div style={{ color: 'rgba(255,255,255,0.75)', fontSize: 11 }}>{a.program_name}</div>
          <TrackBadge track={a.track} />
          <div style={{ textAlign: 'right', color: 'rgba(255,255,255,0.6)' }}>${fmt(a.cost)}</div>
          <div style={{ textAlign: 'right', color: '#1a8c4e', fontWeight: 600 }}>+{a.impact_delta.toFixed(1)}</div>
          <div style={{ textAlign: 'right', color: '#2a7ab0', fontWeight: 600 }}>−{(a.attrition_reduction * 100).toFixed(1)}%</div>
          <div style={{ textAlign: 'right', color: 'var(--gold-light)', fontWeight: 600 }}>{a.roi.toFixed(1)}×</div>
        </div>
      ))}
    </div>
  )
}

// ── Optimizer tab ─────────────────────────────────────────────────────────────

interface OptimizerTabProps {
  data: LDData
  scenario: string
  size: string
}

function OptimizerTab({ data, scenario, size }: OptimizerTabProps) {
  const defaultBudget = data.summary.default_budget
  const [budget, setBudget]     = useState(defaultBudget)
  const [maxPer, setMaxPer]     = useState(2)
  const [closeGaps, setCloseGaps] = useState(false)
  const [result, setResult]     = useState<LDOptimizationResult>(data.default_optimization)
  const [running, setRunning]   = useState(false)

  const runOptimize = async () => {
    setRunning(true)
    try {
      const r = await api.ld.optimize({ scenario, size, budget, max_per_employee: maxPer, close_gaps: closeGaps })
      setResult(r)
    } finally {
      setRunning(false)
    }
  }

  const card: React.CSSProperties = {
    backgroundColor: 'var(--surface)', borderRadius: 'var(--radius)',
    border: '1px solid rgba(255,255,255,0.06)', padding: '16px 20px',
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Controls */}
      <div style={{ ...card, display: 'flex', gap: 24, alignItems: 'flex-end', flexWrap: 'wrap' }}>
        <div style={{ flex: '1 1 280px' }}>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px',
            textTransform: 'uppercase', color: 'rgba(255,255,255,0.4)', marginBottom: 8 }}>
            L&D Budget: {fmtK(budget)}
          </div>
          <input type="range" min={10000} max={defaultBudget * 2} step={10000}
            value={budget} onChange={e => setBudget(Number(e.target.value))}
            style={{ width: '100%', accentColor: 'var(--gold-light)' }} />
          <div style={{ display: 'flex', justifyContent: 'space-between',
            fontSize: 9, color: 'rgba(255,255,255,0.3)', marginTop: 4, fontFamily: 'var(--fb)' }}>
            <span>$10K</span><span>{fmtK(defaultBudget * 2)}</span>
          </div>
        </div>

        <div>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px',
            textTransform: 'uppercase', color: 'rgba(255,255,255,0.4)', marginBottom: 8 }}>
            Max programs / employee
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            {[1, 2, 3].map(v => (
              <button key={v} onClick={() => setMaxPer(v)}
                style={{
                  padding: '5px 14px', borderRadius: 4, border: 'none', cursor: 'pointer',
                  fontFamily: 'var(--fb)', fontSize: 11, fontWeight: 600,
                  backgroundColor: maxPer === v ? 'var(--gold-light)' : 'rgba(255,255,255,0.07)',
                  color: maxPer === v ? '#003366' : 'rgba(255,255,255,0.6)',
                }}>
                {v}
              </button>
            ))}
          </div>
        </div>

        <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
          <input type="checkbox" checked={closeGaps} onChange={e => setCloseGaps(e.target.checked)}
            style={{ accentColor: 'var(--gold-light)', width: 14, height: 14 }} />
          <span style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'rgba(255,255,255,0.6)' }}>
            Prioritize skill gap closure
          </span>
        </label>

        <button onClick={runOptimize} disabled={running}
          style={{
            padding: '8px 22px', borderRadius: 4, border: 'none', cursor: running ? 'wait' : 'pointer',
            backgroundColor: 'var(--gold-light)', color: '#003366',
            fontFamily: 'var(--fb)', fontSize: 11, fontWeight: 700, letterSpacing: '1px',
            textTransform: 'uppercase', opacity: running ? 0.7 : 1,
          }}>
          {running ? 'Optimizing…' : 'Optimize'}
        </button>
      </div>

      {/* KPI row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        {[
          { label: 'Budget Used',          value: fmtK(result.budget_used), sub: `of ${fmtK(result.budget)}` },
          { label: 'Employees Receiving Training', value: String(result.unique_employees), sub: `${result.total_allocations} total programs` },
          { label: 'Expected Impact Gain',  value: `+${result.expected_impact_gain.toFixed(1)}`, sub: 'points avg across org' },
          { label: 'Attrition Reduction',  value: pct(result.expected_attrition_reduction), sub: 'projected risk drop' },
        ].map(k => (
          <div key={k.label} style={{ ...card, textAlign: 'center' }}>
            <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px',
              textTransform: 'uppercase', color: 'rgba(255,255,255,0.4)', marginBottom: 6 }}>
              {k.label}
            </div>
            <div style={{ fontFamily: 'var(--fd)', fontSize: 28, color: 'var(--gold-light)', lineHeight: 1 }}>
              {k.value}
            </div>
            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', marginTop: 4 }}>{k.sub}</div>
          </div>
        ))}
      </div>

      {/* Allocation table */}
      <div style={card}>
        <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px',
          textTransform: 'uppercase', color: 'rgba(255,255,255,0.4)', marginBottom: 12 }}>
          Optimized Training Assignments — {result.status}
        </div>
        <AllocationTable allocations={result.allocations} />
      </div>

      {/* Pareto frontier */}
      <div style={card}>
        <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px',
          textTransform: 'uppercase', color: 'rgba(255,255,255,0.4)', marginBottom: 4 }}>
          Retention vs L&D Investment — Pareto Frontier
        </div>
        <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', marginBottom: 12 }}>
          How splitting a shared budget between retention and training affects combined workforce impact.
        </div>
        <div style={{ overflowX: 'auto' }}>
          <ParetoCurve points={data.pareto_frontier} />
        </div>
        <div style={{ display: 'flex', gap: 20, marginTop: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{ width: 24, height: 2, backgroundColor: 'var(--gold-light)' }} />
            <span style={{ fontSize: 9, color: 'rgba(255,255,255,0.4)', fontFamily: 'var(--fb)' }}>
              COMBINED SCORE
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{ width: 14, height: 10, backgroundColor: 'rgba(42,122,176,0.3)', borderRadius: 2 }} />
            <span style={{ fontSize: 9, color: 'rgba(255,255,255,0.4)', fontFamily: 'var(--fb)' }}>
              RETENTION CONTRIBUTION
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Training preview tab ──────────────────────────────────────────────────────

function ProgramEffectivenessBar({ prog }: { prog: TrainingProgramEffectiveness }) {
  const barW = Math.min(100, prog.roi * 25)
  return (
    <div style={{
      padding: '10px 14px',
      borderRadius: 6,
      backgroundColor: 'rgba(255,255,255,0.03)',
      border: `1px solid ${trackColor(prog.track)}22`,
      marginBottom: 8,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
        <div>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 11, fontWeight: 600, color: 'var(--light)' }}>
            {prog.program_name}
          </div>
          <div style={{ marginTop: 3 }}>
            <TrackBadge track={prog.track} />
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontFamily: 'var(--fd)', fontSize: 18, color: 'var(--gold-light)' }}>
            {prog.roi.toFixed(1)}×
          </div>
          <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.35)', fontFamily: 'var(--fb)' }}>ROI</div>
        </div>
      </div>
      <div style={{ display: 'flex', gap: 16, marginBottom: 6 }}>
        <span style={{ fontSize: 10, color: '#1a8c4e' }}>+{prog.impact_delta.toFixed(1)} impact</span>
        <span style={{ fontSize: 10, color: '#2a7ab0' }}>−{(prog.attrition_reduction * 100).toFixed(1)}% attrition risk</span>
        <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)' }}>{prog.duration_weeks}w · ${fmt(prog.cost)}</span>
      </div>
      <div style={{ height: 4, backgroundColor: 'rgba(255,255,255,0.06)', borderRadius: 2 }}>
        <div style={{ height: '100%', width: `${barW}%`, backgroundColor: trackColor(prog.track), borderRadius: 2 }} />
      </div>
    </div>
  )
}

function PreviewTab({ previews }: { previews: EmployeePreview[] }) {
  const [selectedIdx, setSelectedIdx] = useState(0)
  if (previews.length === 0) return null
  const emp = previews[selectedIdx]

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '260px 1fr', gap: 20 }}>
      {/* Employee list */}
      <div style={{
        backgroundColor: 'var(--surface)', borderRadius: 'var(--radius)',
        border: '1px solid rgba(255,255,255,0.06)', overflowY: 'auto', maxHeight: 600,
      }}>
        <div style={{ padding: '12px 14px', borderBottom: '1px solid rgba(255,255,255,0.06)',
          fontFamily: 'var(--fb)', fontSize: 8, letterSpacing: '1.5px',
          textTransform: 'uppercase', color: 'rgba(255,255,255,0.4)' }}>
          Priority Employees (by risk × impact)
        </div>
        {previews.map((e, i) => (
          <button key={e.employee_id} onClick={() => setSelectedIdx(i)}
            style={{
              width: '100%', textAlign: 'left', background: 'none', border: 'none',
              cursor: 'pointer', padding: '10px 14px',
              backgroundColor: i === selectedIdx ? 'rgba(201,168,76,0.08)' : 'transparent',
              borderLeft: i === selectedIdx ? '3px solid var(--gold-light)' : '3px solid transparent',
            }}>
            <div style={{ fontFamily: 'var(--fb)', fontSize: 11, fontWeight: 600, color: 'var(--light)' }}>
              {e.full_name}
            </div>
            <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.4)', marginTop: 2 }}>
              {e.department} · {e.seniority_level}
            </div>
            <div style={{ display: 'flex', gap: 10, marginTop: 3 }}>
              <span style={{ fontSize: 9, color: '#c8982a' }}>Impact {e.impact_score.toFixed(0)}</span>
              <span style={{ fontSize: 9, color: '#e07030' }}>Risk {pct(e.attrition_risk)}</span>
            </div>
          </button>
        ))}
      </div>

      {/* Program effectiveness */}
      <div>
        <div style={{
          backgroundColor: 'var(--surface)', borderRadius: 'var(--radius)',
          border: '1px solid rgba(255,255,255,0.06)', padding: '16px 20px', marginBottom: 16,
        }}>
          <div style={{ fontFamily: 'var(--fd)', fontSize: 18, color: 'var(--light)', marginBottom: 4 }}>
            {emp.full_name}
          </div>
          <div style={{ display: 'flex', gap: 20, fontSize: 11, color: 'rgba(255,255,255,0.5)' }}>
            <span>{emp.department}</span>
            <span>{emp.role_title}</span>
            <span style={{ textTransform: 'capitalize' }}>{emp.seniority_level}</span>
          </div>
          <div style={{ display: 'flex', gap: 24, marginTop: 12 }}>
            <div>
              <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.4)', fontFamily: 'var(--fb)',
                textTransform: 'uppercase', letterSpacing: '1px', marginBottom: 2 }}>Learning Velocity</div>
              <div style={{ fontFamily: 'var(--fd)', fontSize: 22, color: 'var(--gold-light)' }}>
                {(emp.learning_velocity * 100).toFixed(0)}%
              </div>
            </div>
            <div>
              <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.4)', fontFamily: 'var(--fb)',
                textTransform: 'uppercase', letterSpacing: '1px', marginBottom: 2 }}>Attrition Risk</div>
              <div style={{ fontFamily: 'var(--fd)', fontSize: 22, color: '#e07030' }}>
                {pct(emp.attrition_risk)}
              </div>
            </div>
            <div>
              <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.4)', fontFamily: 'var(--fb)',
                textTransform: 'uppercase', letterSpacing: '1px', marginBottom: 2 }}>Impact Score</div>
              <div style={{ fontFamily: 'var(--fd)', fontSize: 22, color: '#1a8c4e' }}>
                {emp.impact_score.toFixed(0)}
              </div>
            </div>
          </div>
        </div>

        <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px',
          textTransform: 'uppercase', color: 'rgba(255,255,255,0.4)', marginBottom: 10 }}>
          Training programs — ranked by ROI
        </div>
        <div style={{ maxHeight: 440, overflowY: 'auto' }}>
          {emp.programs.map(p => (
            <ProgramEffectivenessBar key={p.program_id} prog={p} />
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Skill gaps tab ────────────────────────────────────────────────────────────

function GapsTab({ gaps }: { gaps: SkillGapRow[] }) {
  const card: React.CSSProperties = {
    backgroundColor: 'var(--surface)', borderRadius: 'var(--radius)',
    border: '1px solid rgba(255,255,255,0.06)', padding: '16px 20px',
  }
  const hdrStyle: React.CSSProperties = {
    display: 'grid',
    gridTemplateColumns: '1fr 140px 80px 80px 120px 80px',
    gap: '0 12px', padding: '6px 12px',
    fontFamily: 'var(--fb)', fontSize: 8, letterSpacing: '1.5px',
    textTransform: 'uppercase', color: 'rgba(255,255,255,0.35)',
    borderBottom: '1px solid rgba(255,255,255,0.08)', marginBottom: 4,
  }
  const rowStyle: React.CSSProperties = {
    display: 'grid',
    gridTemplateColumns: '1fr 140px 80px 80px 120px 80px',
    gap: '0 12px', padding: '8px 12px', alignItems: 'center',
    fontFamily: 'var(--fb)', fontSize: 11,
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Summary chips */}
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        {(['critical','high','medium'] as const).map(sev => {
          const cnt = gaps.filter(g => g.gap_severity === sev).length
          return cnt > 0 ? (
            <span key={sev} style={{
              padding: '4px 12px', borderRadius: 20, fontSize: 10, fontWeight: 700,
              backgroundColor: `${severityColor(sev)}22`, color: severityColor(sev),
              fontFamily: 'var(--fb)', textTransform: 'capitalize',
            }}>
              {cnt} {sev}
            </span>
          ) : null
        })}
      </div>

      <div style={card}>
        <div style={hdrStyle}>
          <span>SKILL / ROLE</span>
          <span>DEPARTMENT</span>
          <span style={{ textAlign: 'center' }}>HOLDERS</span>
          <span style={{ textAlign: 'center' }}>SEVERITY</span>
          <span>RECOMMENDED PROGRAMS</span>
          <span style={{ textAlign: 'right' }}>EST. COST</span>
        </div>
        {gaps.length === 0 && (
          <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: 12, padding: '12px 0' }}>
            No skill gaps detected in this org.
          </p>
        )}
        {gaps.map((g, i) => (
          <div key={i} style={{
            ...rowStyle,
            backgroundColor: i % 2 === 0 ? 'rgba(255,255,255,0.02)' : 'transparent',
            borderRadius: 4,
          }}>
            <div>
              <div style={{ fontWeight: 600, color: 'var(--light)' }}>{g.skill}</div>
              <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.35)', marginTop: 1 }}>
                {g.internal_closeable ? '✓ Closeable via training' : '→ May require external hire'}
              </div>
            </div>
            <div style={{ color: 'rgba(255,255,255,0.6)' }}>{g.department}</div>
            <div style={{ textAlign: 'center', color: 'rgba(255,255,255,0.5)' }}>
              {g.current_holders} / {g.required_holders}
            </div>
            <div style={{ textAlign: 'center' }}>
              <span style={{
                padding: '2px 8px', borderRadius: 10, fontSize: 8, fontWeight: 700,
                backgroundColor: `${severityColor(g.gap_severity)}22`,
                color: severityColor(g.gap_severity), fontFamily: 'var(--fb)',
                textTransform: 'uppercase',
              }}>
                {g.gap_severity}
              </span>
            </div>
            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.5)' }}>
              {g.recommended_programs.length > 0 ? g.recommended_programs.join(', ') : '—'}
            </div>
            <div style={{ textAlign: 'right', color: 'rgba(255,255,255,0.6)' }}>
              {g.estimated_cost > 0 ? `$${fmt(g.estimated_cost)}` : '—'}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── ROI tracker tab ───────────────────────────────────────────────────────────

function ROIBar({ predicted, actual }: { predicted: number; actual: number }) {
  const maxROI = 4
  const pw = Math.min(100, (predicted / maxROI) * 100)
  const aw = Math.min(100, (actual   / maxROI) * 100)
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 100 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <div style={{ flex: 1, height: 4, backgroundColor: 'rgba(255,255,255,0.06)', borderRadius: 2 }}>
          <div style={{ height: '100%', width: `${pw}%`, backgroundColor: 'rgba(255,255,255,0.25)', borderRadius: 2 }} />
        </div>
        <span style={{ fontSize: 9, color: 'rgba(255,255,255,0.4)', width: 30, textAlign: 'right', fontFamily: 'var(--fb)' }}>
          {predicted}×
        </span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <div style={{ flex: 1, height: 4, backgroundColor: 'rgba(255,255,255,0.06)', borderRadius: 2 }}>
          <div style={{ height: '100%', width: `${aw}%`,
            backgroundColor: actual >= predicted ? '#1a8c4e' : '#e03448', borderRadius: 2 }} />
        </div>
        <span style={{ fontSize: 9, color: actual >= predicted ? '#1a8c4e' : '#e03448',
          width: 30, textAlign: 'right', fontFamily: 'var(--fb)', fontWeight: 700 }}>
          {actual}×
        </span>
      </div>
    </div>
  )
}

function ROITab({ records }: { records: ROIRecord[] }) {
  const card: React.CSSProperties = {
    backgroundColor: 'var(--surface)', borderRadius: 'var(--radius)',
    border: '1px solid rgba(255,255,255,0.06)', padding: '16px 20px',
  }

  const avgActual    = records.reduce((s, r) => s + r.actual_roi, 0) / Math.max(records.length, 1)
  const avgPredicted = records.reduce((s, r) => s + r.predicted_roi, 0) / Math.max(records.length, 1)
  const totalSpend   = records.reduce((s, r) => s + r.total_cost, 0)
  const aboveCount   = records.filter(r => r.status === 'above_forecast').length

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Summary KPIs */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        {[
          { label: 'Avg Realized ROI',    value: `${avgActual.toFixed(1)}×`,  sub: `Predicted ${avgPredicted.toFixed(1)}×` },
          { label: 'Total L&D Spend',     value: fmtK(totalSpend),            sub: `${records.length} cohorts tracked`     },
          { label: 'Above Forecast',      value: `${aboveCount}`,             sub: `of ${records.length} programs`         },
          { label: 'Model Accuracy',      value: `${((1 - Math.abs(avgActual - avgPredicted) / avgPredicted) * 100).toFixed(0)}%`,
                                                                               sub: 'prediction vs actual'                  },
        ].map(k => (
          <div key={k.label} style={{ ...card, textAlign: 'center' }}>
            <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px',
              textTransform: 'uppercase', color: 'rgba(255,255,255,0.4)', marginBottom: 6 }}>
              {k.label}
            </div>
            <div style={{ fontFamily: 'var(--fd)', fontSize: 26, color: 'var(--gold-light)', lineHeight: 1 }}>
              {k.value}
            </div>
            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', marginTop: 4 }}>{k.sub}</div>
          </div>
        ))}
      </div>

      {/* ROI table */}
      <div style={card}>
        <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px',
          textTransform: 'uppercase', color: 'rgba(255,255,255,0.4)', marginBottom: 12 }}>
          Training Cohort ROI History
        </div>
        <div style={{ display: 'flex', gap: 12, marginBottom: 8, fontSize: 9,
          color: 'rgba(255,255,255,0.35)', fontFamily: 'var(--fb)' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <div style={{ width: 20, height: 3, backgroundColor: 'rgba(255,255,255,0.25)' }} /> PREDICTED
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <div style={{ width: 20, height: 3, backgroundColor: '#1a8c4e' }} /> ACTUAL (above)
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <div style={{ width: 20, height: 3, backgroundColor: '#e03448' }} /> ACTUAL (below)
          </span>
        </div>

        {records.map((r, i) => (
          <div key={r.id} style={{
            display: 'grid',
            gridTemplateColumns: '1fr 120px 70px 70px 110px 90px',
            gap: '0 12px', alignItems: 'center', padding: '9px 10px',
            backgroundColor: i % 2 === 0 ? 'rgba(255,255,255,0.02)' : 'transparent',
            borderRadius: 4, fontFamily: 'var(--fb)',
          }}>
            <div>
              <div style={{ fontWeight: 600, fontSize: 11, color: 'var(--light)' }}>{r.program_name}</div>
              <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.35)', marginTop: 1 }}>{r.completion_month}</div>
            </div>
            <TrackBadge track={r.track} />
            <div style={{ textAlign: 'right', fontSize: 11, color: 'rgba(255,255,255,0.55)' }}>
              {r.participants} emp.
            </div>
            <div style={{ textAlign: 'right', fontSize: 11, color: 'rgba(255,255,255,0.55)' }}>
              ${fmt(r.total_cost)}
            </div>
            <ROIBar predicted={r.predicted_roi} actual={r.actual_roi} />
            <div style={{ textAlign: 'right' }}>
              <span style={{
                fontSize: 9, fontWeight: 700, padding: '2px 8px',
                borderRadius: 10, textTransform: 'uppercase',
                backgroundColor: `${roiStatusColor(r.status)}22`,
                color: roiStatusColor(r.status),
              }}>
                {r.status === 'above_forecast' ? 'Above' : r.status === 'below_forecast' ? 'Below' : 'On target'}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Catalog sidebar ───────────────────────────────────────────────────────────

function CatalogSidebar({ data }: { data: LDData }) {
  const tracks = Array.from(new Set(data.catalog.map(p => p.track)))
  return (
    <div style={{
      backgroundColor: 'var(--surface)', borderRadius: 'var(--radius)',
      border: '1px solid rgba(255,255,255,0.06)', padding: '16px',
      width: 220, flexShrink: 0,
    }}>
      <div style={{ fontFamily: 'var(--fb)', fontSize: 8, letterSpacing: '1.5px',
        textTransform: 'uppercase', color: 'rgba(255,255,255,0.35)', marginBottom: 12 }}>
        Training Catalog
      </div>
      {tracks.map(track => (
        <div key={track} style={{ marginBottom: 14 }}>
          <div style={{ marginBottom: 6 }}><TrackBadge track={track} /></div>
          {data.catalog.filter(p => p.track === track).map(prog => (
            <div key={prog.id} style={{ marginBottom: 6, paddingLeft: 8,
              borderLeft: `2px solid ${trackColor(track)}44` }}>
              <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.7)', lineHeight: 1.3 }}>
                {prog.name}
              </div>
              <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.35)', marginTop: 2 }}>
                ${fmt(prog.cost)} · {prog.duration_weeks}w
              </div>
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function LDPage() {
  const { scenario, size } = useDemoStore()
  const [data, setData]   = useState<LDData | null>(null)
  const [tab, setTab]     = useState<Tab>('optimizer')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setData(null)
    setError(null)
    api.ld.data(scenario, size)
      .then(setData)
      .catch(e => setError(String(e)))
  }, [scenario, size])

  const pageStyle: React.CSSProperties = {
    padding: '32px 40px',
    minHeight: '100vh',
    backgroundColor: 'var(--light)',
    color: 'var(--light)',
  }

  if (error) return (
    <div style={{ ...pageStyle, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <span style={{ color: '#e03448', fontFamily: 'var(--fb)', fontSize: 13 }}>
        Failed to load L&D data: {error}
      </span>
    </div>
  )

  if (!data) return (
    <div style={{ ...pageStyle, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <span style={{ color: 'rgba(255,255,255,0.4)', fontFamily: 'var(--fb)', fontSize: 13 }}>
        Loading learning & development data…
      </span>
    </div>
  )

  const s = data.summary

  const tabStyle = (t: Tab): React.CSSProperties => ({
    background: 'none', border: 'none', cursor: 'pointer',
    fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '2px',
    textTransform: 'uppercase', padding: '7px 14px', borderRadius: 3,
    color: tab === t ? 'var(--gold-light)' : 'rgba(255,255,255,0.45)',
    backgroundColor: tab === t ? 'rgba(201,168,76,0.12)' : 'transparent',
  })

  return (
    <div style={pageStyle}>
      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontFamily: 'var(--fd)', fontSize: 28, fontWeight: 300,
          color: 'var(--light)', margin: 0, marginBottom: 4 }}>
          Learning &amp; Development Optimizer
        </h1>
        <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)', margin: 0 }}>
          Optimize training investment to maximize impact score gains and reduce attrition risk across the workforce.
        </p>
      </div>

      {/* Hero KPIs */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 28 }}>
        {[
          { label: 'Training Programs',    value: String(s.catalog_size),   sub: 'in catalog across 5 tracks' },
          { label: 'Skill Gaps Identified',value: String(s.skill_gaps),     sub: `${s.critical_gaps} critical` },
          { label: 'Avg Learning Velocity',value: `${(s.avg_learning_velocity * 100).toFixed(0)}%`,
                                                                             sub: 'across eligible employees' },
          { label: 'Expected Impact Gain', value: `+${s.expected_impact_gain.toFixed(1)}`, sub: 'with default budget' },
        ].map(k => (
          <div key={k.label} style={{
            backgroundColor: 'var(--surface)', borderRadius: 'var(--radius)',
            border: '1px solid rgba(255,255,255,0.06)', padding: '16px 20px', textAlign: 'center',
          }}>
            <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px',
              textTransform: 'uppercase', color: 'rgba(255,255,255,0.4)', marginBottom: 6 }}>
              {k.label}
            </div>
            <div style={{ fontFamily: 'var(--fd)', fontSize: 30, color: 'var(--gold-light)', lineHeight: 1 }}>
              {k.value}
            </div>
            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', marginTop: 5 }}>{k.sub}</div>
          </div>
        ))}
      </div>

      {/* Tab bar */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 24,
        borderBottom: '1px solid rgba(255,255,255,0.07)', paddingBottom: 12 }}>
        <button style={tabStyle('optimizer')} onClick={() => setTab('optimizer')}>Optimizer</button>
        <button style={tabStyle('preview')}   onClick={() => setTab('preview')}>Training Preview</button>
        <button style={tabStyle('gaps')}      onClick={() => setTab('gaps')}>Skill Gaps</button>
        <button style={tabStyle('roi')}       onClick={() => setTab('roi')}>ROI Tracker</button>
      </div>

      {/* Content */}
      <div style={{ display: 'flex', gap: 20, alignItems: 'flex-start' }}>
        {/* Catalog sidebar (only on optimizer tab) */}
        {tab === 'optimizer' && <CatalogSidebar data={data} />}

        {/* Main content */}
        <div style={{ flex: 1, minWidth: 0 }}>
          {tab === 'optimizer' && (
            <OptimizerTab data={data} scenario={scenario} size={size} />
          )}
          {tab === 'preview' && (
            <PreviewTab previews={data.employee_previews} />
          )}
          {tab === 'gaps' && (
            <GapsTab gaps={data.skill_gaps} />
          )}
          {tab === 'roi' && (
            <ROITab records={data.roi_history} />
          )}
        </div>
      </div>
    </div>
  )
}
