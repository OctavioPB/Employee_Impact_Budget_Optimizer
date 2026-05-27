import React, { useState, useEffect } from 'react'
import {
  api,
  OHIData,
  OHISubIndex,
  OHIDeptRow,
  OHITrendPoint,
  OHIBenchmarkBand,
  OHIDecisionPoint,
  OHIAlert,
} from '../services/api'
import { useDemoStore } from '../stores/demoStore'

type Tab = 'overview' | 'trend' | 'preview' | 'benchmark'

// ── Colours ───────────────────────────────────────────────────────────────────

const SUB_COLORS: Record<string, string> = {
  financial_health:      '#2a7ab0',
  talent_risk:           '#e07030',
  knowledge_resilience:  '#6a42a8',
  leadership_pipeline:   '#1a8c4e',
  compensation_equity:   '#c8982a',
  collaboration_density: '#2a8ab0',
}

function gradeColor(g: string): string {
  return g === 'A' ? '#1a8c4e' : g === 'B' ? '#2a7ab0' : g === 'C' ? '#c8982a' : g === 'D' ? '#e07030' : '#e03448'
}
function dirColor(d: string): string {
  return d === 'improving' ? '#1a8c4e' : d === 'declining' ? '#e03448' : '#c8982a'
}
function dirArrow(d: string): string { return d === 'improving' ? '↑' : d === 'declining' ? '↓' : '→' }
function sevColor(s: string): string { return s === 'critical' ? '#e03448' : '#e07030' }
function fmt(n: number): string { return n.toLocaleString(undefined, { maximumFractionDigits: 0 }) }

// ── Shared card style ─────────────────────────────────────────────────────────

const card: React.CSSProperties = {
  backgroundColor: 'var(--surface)', borderRadius: 'var(--radius)',
  border: '1px solid rgba(255,255,255,0.06)', padding: '16px 20px',
}

// ── Alert banner ──────────────────────────────────────────────────────────────

function AlertBanner({ alert }: { alert: OHIAlert }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 14, marginBottom: 20,
      padding: '10px 18px', borderRadius: 6,
      backgroundColor: `${sevColor(alert.severity)}14`,
      border: `1px solid ${sevColor(alert.severity)}44`,
    }}>
      <span style={{ fontSize: 16 }}>⚠</span>
      <div>
        <div style={{ fontFamily: 'var(--fb)', fontSize: 11, fontWeight: 700,
          color: sevColor(alert.severity) }}>
          OHI Alert — {alert.severity.toUpperCase()}
        </div>
        <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.55)', marginTop: 2 }}>
          {alert.message}
        </div>
      </div>
    </div>
  )
}

// ── OHI Composite Gauge (half-circle SVG) ─────────────────────────────────────

function OHIGauge({ score, grade }: { score: number; grade: string }) {
  const W = 200; const H = 120; const R = 80; const cx = W / 2; const cy = 108
  const sweepDeg = (score / 100) * 180
  const sweepRad = (sweepDeg - 180) * (Math.PI / 180)
  const ex = cx + R * Math.cos(sweepRad)
  const ey = cy + R * Math.sin(sweepRad)
  const largeArc = sweepDeg > 180 ? 1 : 0

  // Track gradient background
  const trackD = `M ${cx - R} ${cy} A ${R} ${R} 0 0 1 ${cx + R} ${cy}`
  const fillD  = `M ${cx - R} ${cy} A ${R} ${R} 0 ${largeArc} 1 ${ex} ${ey}`

  return (
    <svg width={W} height={H} style={{ display: 'block', margin: '0 auto' }}>
      {/* Track */}
      <path d={trackD} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth={14}
        strokeLinecap="round" />
      {/* Fill */}
      <path d={fillD} fill="none" stroke={gradeColor(grade)} strokeWidth={14}
        strokeLinecap="round" />
      {/* Score */}
      <text x={cx} y={cy - 16} textAnchor="middle"
        style={{ fontFamily: 'var(--fd)', fontSize: 34, fill: 'var(--light)' }}>
        {score.toFixed(0)}
      </text>
      {/* Grade */}
      <text x={cx} y={cy - 2} textAnchor="middle"
        style={{ fontFamily: 'var(--fb)', fontSize: 12, fill: gradeColor(grade), fontWeight: 700 }}>
        GRADE {grade}
      </text>
    </svg>
  )
}

// ── Sub-index card ─────────────────────────────────────────────────────────────

function SubIndexCard({ dimKey, dim, onClick, selected }: {
  dimKey: string; dim: OHISubIndex; onClick: () => void; selected: boolean
}) {
  const color = SUB_COLORS[dimKey] ?? '#888'
  const compEntries = Object.entries(dim.components)

  return (
    <div onClick={onClick} style={{
      ...card,
      cursor: 'pointer',
      borderColor: selected ? `${color}55` : 'rgba(255,255,255,0.06)',
      borderLeftWidth: 3, borderLeftColor: color,
      transition: 'border-color 0.15s',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
        <div>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px',
            textTransform: 'uppercase', color: 'rgba(255,255,255,0.4)', marginBottom: 4 }}>
            {dim.label}
          </div>
          <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.3)', fontFamily: 'var(--fb)' }}>
            weight {(dim.weight * 100).toFixed(0)}%
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontFamily: 'var(--fd)', fontSize: 26, color, lineHeight: 1 }}>
            {dim.score.toFixed(0)}
          </div>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 700,
            color: gradeColor(dim.grade), marginTop: 2 }}>
            {dim.grade}
          </div>
        </div>
      </div>
      {/* Score bar */}
      <div style={{ height: 4, backgroundColor: 'rgba(255,255,255,0.06)', borderRadius: 2, marginBottom: 10 }}>
        <div style={{ height: '100%', width: `${dim.score}%`, backgroundColor: color, borderRadius: 2 }} />
      </div>
      {/* Component breakdown (shown when selected) */}
      {selected && (
        <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 6 }}>
          {compEntries.map(([k, v]) => (
            <div key={k}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                <span style={{ fontSize: 9, color: 'rgba(255,255,255,0.5)' }}>
                  {dim.labels?.[k] ?? k}
                </span>
                <span style={{ fontSize: 9, color, fontWeight: 600, fontFamily: 'var(--fb)' }}>
                  {v.toFixed(0)}
                </span>
              </div>
              <div style={{ height: 3, backgroundColor: 'rgba(255,255,255,0.05)', borderRadius: 2 }}>
                <div style={{ height: '100%', width: `${v}%`, backgroundColor: `${color}88`, borderRadius: 2 }} />
              </div>
            </div>
          ))}
          <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.3)', marginTop: 4, lineHeight: 1.5 }}>
            {dim.detail}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Department table ──────────────────────────────────────────────────────────

function DeptTable({ rows }: { rows: OHIDeptRow[] }) {
  const hdrs = ['Department', 'OHI', 'Grade', 'Headcount', 'Nexus', 'Avg Impact', 'Avg Risk']
  const rowGrid: React.CSSProperties = {
    display: 'grid', gridTemplateColumns: '1fr 60px 44px 80px 50px 90px 80px',
    gap: '0 12px', padding: '7px 12px', alignItems: 'center',
    fontFamily: 'var(--fb)', fontSize: 11,
  }
  return (
    <div style={card}>
      <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px',
        textTransform: 'uppercase', color: 'rgba(255,255,255,0.4)', marginBottom: 10 }}>
        Department Health
      </div>
      <div style={{ ...rowGrid, fontSize: 8, color: 'rgba(255,255,255,0.3)',
        letterSpacing: '1.5px', textTransform: 'uppercase',
        borderBottom: '1px solid rgba(255,255,255,0.07)', paddingBottom: 6 }}>
        {hdrs.map(h => <span key={h}>{h}</span>)}
      </div>
      {rows.map((r, i) => (
        <div key={r.department} style={{
          ...rowGrid,
          backgroundColor: i % 2 === 0 ? 'rgba(255,255,255,0.02)' : 'transparent',
          borderRadius: 4,
        }}>
          <div style={{ fontWeight: 600, color: 'var(--light)' }}>{r.department}</div>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: gradeColor(r.grade),
              fontFamily: 'var(--fd)' }}>{r.score.toFixed(0)}</div>
            <div style={{ height: 2, backgroundColor: 'rgba(255,255,255,0.05)', borderRadius: 1, marginTop: 2 }}>
              <div style={{ height: '100%', width: `${r.score}%`,
                backgroundColor: gradeColor(r.grade), borderRadius: 1 }} />
            </div>
          </div>
          <span style={{ fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 700,
            color: gradeColor(r.grade) }}>{r.grade}</span>
          <span style={{ color: 'rgba(255,255,255,0.6)' }}>{r.headcount}</span>
          <span style={{ color: r.nexus_count > 0 ? 'var(--gold-light)' : 'rgba(255,255,255,0.3)' }}>
            {r.nexus_count > 0 ? `★ ${r.nexus_count}` : '—'}
          </span>
          <span style={{ color: '#2a7ab0' }}>{r.avg_impact.toFixed(0)}</span>
          <span style={{ color: r.avg_attrition > 0.5 ? '#e07030' : 'rgba(255,255,255,0.55)' }}>
            {(r.avg_attrition * 100).toFixed(0)}%
          </span>
        </div>
      ))}
    </div>
  )
}

// ── Trend chart (SVG) ─────────────────────────────────────────────────────────

function TrendChart({ points }: { points: OHITrendPoint[] }) {
  const W = 680; const H = 240
  const PAD = { top: 24, right: 80, bottom: 42, left: 52 }
  const innerW = W - PAD.left - PAD.right
  const innerH = H - PAD.top  - PAD.bottom

  const scores   = points.map(p => p.score)
  const minScore = Math.max(0,   Math.min(...scores) - 8)
  const maxScore = Math.min(100, Math.max(...scores) + 8)

  const xScale = (i: number) => PAD.left + (i / (points.length - 1)) * innerW
  const yScale = (v: number) => PAD.top + innerH - ((v - minScore) / (maxScore - minScore)) * innerH

  const hist     = points.filter(p => !p.is_forecast)
  const forecast = points.filter(p => p.is_forecast)

  // Separate index offsets
  const histEndIdx  = points.findIndex(p => p.is_forecast) - 1
  const fcStartIdx  = points.findIndex(p => p.is_forecast)

  const histPath = hist.map((p, i) =>
    `${i === 0 ? 'M' : 'L'} ${xScale(i)} ${yScale(p.score)}`
  ).join(' ')

  const fcPath = forecast.length > 0
    ? [`M ${xScale(histEndIdx + 1)} ${yScale(points[histEndIdx + 1]?.score ?? 0)}`,
       ...forecast.map((p, i) => `L ${xScale(fcStartIdx + i)} ${yScale(p.score)}`)
      ].join(' ')
    : ''

  // Month labels — every 4th
  const xLabels = points.map((p, i) => ({ i, label: p.month }))
    .filter((_, i) => i % 4 === 0)

  // Y gridlines
  const yTicks = [minScore, (minScore + maxScore) / 2, maxScore].map(v => Math.round(v))

  // Events
  const events = points.map((p, i) => ({ i, event: p.event })).filter(e => e.event)

  return (
    <svg width={W} height={H} style={{ display: 'block' }}>
      {/* Y gridlines */}
      {yTicks.map(v => (
        <g key={v}>
          <line x1={PAD.left} y1={yScale(v)} x2={PAD.left + innerW} y2={yScale(v)}
            stroke="rgba(255,255,255,0.05)" strokeWidth={1} />
          <text x={PAD.left - 6} y={yScale(v) + 4} textAnchor="end"
            style={{ fontSize: 9, fill: 'rgba(255,255,255,0.3)', fontFamily: 'var(--fb)' }}>
            {v}
          </text>
        </g>
      ))}

      {/* Forecast shaded region */}
      {fcStartIdx >= 0 && (
        <rect x={xScale(fcStartIdx)} y={PAD.top}
          width={innerW - (xScale(fcStartIdx) - PAD.left)} height={innerH}
          fill="rgba(201,168,76,0.04)" />
      )}
      {fcStartIdx >= 0 && (
        <text x={xScale(fcStartIdx) + 6} y={PAD.top + 12}
          style={{ fontSize: 8, fill: 'rgba(201,168,76,0.45)', fontFamily: 'var(--fb)',
            textTransform: 'uppercase', letterSpacing: '1px' }}>
          FORECAST
        </text>
      )}

      {/* Event annotations */}
      {events.map(e => (
        <g key={e.i}>
          <line x1={xScale(e.i)} y1={PAD.top} x2={xScale(e.i)} y2={PAD.top + innerH}
            stroke="rgba(255,255,255,0.15)" strokeWidth={1} strokeDasharray="3 3" />
          <text x={xScale(e.i) + 3} y={PAD.top + 14}
            style={{ fontSize: 7.5, fill: 'rgba(255,255,255,0.4)', fontFamily: 'var(--fb)' }}>
            {e.event}
          </text>
        </g>
      ))}

      {/* Historical line */}
      <path d={histPath} fill="none" stroke="var(--gold-light)" strokeWidth={2.5} />

      {/* Forecast line */}
      {fcPath && (
        <path d={fcPath} fill="none" stroke="rgba(201,168,76,0.5)"
          strokeWidth={2} strokeDasharray="5 4" />
      )}

      {/* Today marker */}
      {histEndIdx >= 0 && (
        <circle cx={xScale(histEndIdx)} cy={yScale(hist[hist.length - 1]?.score ?? 0)}
          r={4} fill="var(--gold-light)" />
      )}

      {/* X axis */}
      <line x1={PAD.left} y1={PAD.top + innerH} x2={PAD.left + innerW} y2={PAD.top + innerH}
        stroke="rgba(255,255,255,0.08)" />

      {/* X labels */}
      {xLabels.map(({ i, label }) => (
        <text key={i} x={xScale(i)} y={H - 6} textAnchor="middle"
          style={{ fontSize: 8.5, fill: 'rgba(255,255,255,0.35)', fontFamily: 'var(--fb)' }}>
          {label.split(' ')[0]}
        </text>
      ))}

      {/* Y axis label */}
      <text x={10} y={H / 2} textAnchor="middle" transform={`rotate(-90,10,${H/2})`}
        style={{ fontSize: 9, fill: 'rgba(255,255,255,0.35)', fontFamily: 'var(--fb)' }}>
        OHI SCORE
      </text>
    </svg>
  )
}

// ── Decision preview Pareto ───────────────────────────────────────────────────

function PreviewPareto({ points, selectedPct }: {
  points: OHIDecisionPoint[]
  selectedPct: number
}) {
  const W = 480; const H = 200
  const PAD = { top: 20, right: 20, bottom: 36, left: 52 }
  const innerW = W - PAD.left - PAD.right
  const innerH = H - PAD.top  - PAD.bottom

  const ohis   = points.map(p => p.ohi)
  const minOHI = Math.max(0, Math.min(...ohis) - 5)
  const maxOHI = Math.min(100, Math.max(...ohis) + 5)

  const xScale = (sav: number) => PAD.left + (sav / 50) * innerW   // 0-50% savings range
  const yScale = (ohi: number) => PAD.top + innerH - ((ohi - minOHI) / (maxOHI - minOHI)) * innerH

  const linePath = points.map((p, i) =>
    `${i === 0 ? 'M' : 'L'} ${xScale(p.budget_savings_pct)} ${yScale(p.ohi)}`
  ).join(' ')

  return (
    <svg width={W} height={H} style={{ display: 'block' }}>
      <path d={linePath} fill="none" stroke="rgba(255,255,255,0.2)" strokeWidth={1.5} />
      {points.map((p, i) => {
        const isSelected = p.retention_pct === selectedPct
        return (
          <circle key={i} cx={xScale(p.budget_savings_pct)} cy={yScale(p.ohi)}
            r={isSelected ? 6 : 4}
            fill={isSelected ? 'var(--gold-light)' : gradeColor(p.ohi >= 85 ? 'A' : p.ohi >= 70 ? 'B' : p.ohi >= 55 ? 'C' : 'D')}
            opacity={isSelected ? 1 : 0.6}
          />
        )
      })}
      {/* Labels on selected point */}
      {points.filter(p => p.retention_pct === selectedPct).map((p, i) => (
        <g key={i}>
          <text x={xScale(p.budget_savings_pct)} y={yScale(p.ohi) - 10} textAnchor="middle"
            style={{ fontSize: 9, fill: 'var(--gold-light)', fontFamily: 'var(--fb)', fontWeight: 700 }}>
            OHI {p.ohi}
          </text>
        </g>
      ))}
      {/* Axes */}
      <line x1={PAD.left} y1={PAD.top + innerH} x2={PAD.left + innerW} y2={PAD.top + innerH}
        stroke="rgba(255,255,255,0.08)" />
      {[0, 10, 20, 30, 40, 50].map(v => (
        <text key={v} x={xScale(v)} y={H - 6} textAnchor="middle"
          style={{ fontSize: 8, fill: 'rgba(255,255,255,0.35)', fontFamily: 'var(--fb)' }}>
          {v}%
        </text>
      ))}
      {[minOHI, (minOHI + maxOHI) / 2, maxOHI].map(v => (
        <text key={v} x={PAD.left - 4} y={yScale(v) + 4} textAnchor="end"
          style={{ fontSize: 8, fill: 'rgba(255,255,255,0.3)', fontFamily: 'var(--fb)' }}>
          {Math.round(v)}
        </text>
      ))}
      <text x={PAD.left + innerW / 2} y={H - 2} textAnchor="middle"
        style={{ fontSize: 8.5, fill: 'rgba(255,255,255,0.3)', fontFamily: 'var(--fb)' }}>
        BUDGET SAVINGS (%)
      </text>
      <text x={8} y={H / 2} textAnchor="middle" transform={`rotate(-90,8,${H/2})`}
        style={{ fontSize: 8.5, fill: 'rgba(255,255,255,0.3)', fontFamily: 'var(--fb)' }}>
        OHI SCORE
      </text>
    </svg>
  )
}

// ── Benchmark chart ───────────────────────────────────────────────────────────

function BenchmarkChart({
  subIndices, benchmark,
}: {
  subIndices: Record<string, OHISubIndex>
  benchmark:  Record<string, OHIBenchmarkBand>
}) {
  const keys = Object.keys(subIndices)
  const BAR_W = 380

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {/* Legend */}
      <div style={{ display: 'flex', gap: 20, fontSize: 9, fontFamily: 'var(--fb)',
        color: 'rgba(255,255,255,0.4)', marginBottom: 4 }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ width: 20, height: 8, backgroundColor: 'rgba(255,255,255,0.10)',
            borderRadius: 2 }} />
          P25–P75 synthetic benchmark band
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ width: 10, height: 10, borderRadius: '50%',
            backgroundColor: 'var(--gold-light)' }} />
          Current organization
        </span>
      </div>

      {keys.map(key => {
        const sub   = subIndices[key]
        const band  = benchmark[key]
        if (!band) return null
        const color = SUB_COLORS[key] ?? '#888'

        const px = (v: number) => (v / 100) * BAR_W
        const p25x = px(band.p25); const p75x = px(band.p75)
        const currX = px(sub.score)
        const above = sub.score > band.p75
        const below = sub.score < band.p25

        return (
          <div key={key}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
              <span style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'rgba(255,255,255,0.65)' }}>
                {sub.label}
              </span>
              <span style={{ display: 'flex', gap: 12, fontSize: 10, fontFamily: 'var(--fb)' }}>
                <span style={{ color: 'rgba(255,255,255,0.35)' }}>
                  P50 {band.p50}
                </span>
                <span style={{
                  color: above ? '#1a8c4e' : below ? '#e07030' : 'var(--gold-light)',
                  fontWeight: 700,
                }}>
                  {above ? '▲' : below ? '▼' : '●'} {sub.score.toFixed(0)}
                </span>
              </span>
            </div>
            <div style={{ position: 'relative', height: 16, width: BAR_W }}>
              {/* Track */}
              <div style={{ position: 'absolute', top: 6, left: 0, right: 0, height: 4,
                backgroundColor: 'rgba(255,255,255,0.06)', borderRadius: 2 }} />
              {/* P25-P75 band */}
              <div style={{
                position: 'absolute', top: 6, left: p25x, width: p75x - p25x, height: 4,
                backgroundColor: 'rgba(255,255,255,0.12)', borderRadius: 2,
              }} />
              {/* P50 tick */}
              <div style={{
                position: 'absolute', top: 4, left: px(band.p50) - 1, width: 2, height: 8,
                backgroundColor: 'rgba(255,255,255,0.25)', borderRadius: 1,
              }} />
              {/* Current */}
              <div style={{
                position: 'absolute', top: 3, left: currX - 5, width: 10, height: 10,
                borderRadius: '50%', backgroundColor: color,
                boxShadow: `0 0 6px ${color}99`,
              }} />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between',
              fontSize: 8, color: 'rgba(255,255,255,0.25)', fontFamily: 'var(--fb)', marginTop: 2 }}>
              <span>{band.p25} P25</span>
              <span>{band.p75} P75</span>
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ── Overview tab ──────────────────────────────────────────────────────────────

function OverviewTab({ data }: { data: OHIData }) {
  const [selectedDim, setSelectedDim] = useState<string | null>(null)
  const s = data.summary
  const dimKeys = Object.keys(data.sub_indices)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr', gap: 20 }}>
        {/* Composite score */}
        <div style={{ ...card, display: 'flex', flexDirection: 'column', alignItems: 'center',
          justifyContent: 'center', gap: 8 }}>
          <OHIGauge score={s.overall} grade={s.grade} />
          <div style={{ textAlign: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
              <span style={{ fontFamily: 'var(--fd)', fontSize: 18, color: dirColor(s.trend_direction) }}>
                {dirArrow(s.trend_direction)}
              </span>
              <span style={{ fontFamily: 'var(--fb)', fontSize: 10,
                color: dirColor(s.trend_direction) }}>
                {s.trend_direction.toUpperCase()}
              </span>
            </div>
            <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.35)', marginTop: 3,
              fontFamily: 'var(--fb)' }}>
              {s.trend_delta_90d >= 0 ? '+' : ''}{s.trend_delta_90d.toFixed(1)} pts / 90 days
            </div>
          </div>
          <div style={{ display: 'flex', gap: 16, marginTop: 4 }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 8, color: 'rgba(255,255,255,0.35)',
                textTransform: 'uppercase', letterSpacing: '1px' }}>Employees</div>
              <div style={{ fontFamily: 'var(--fd)', fontSize: 18, color: 'var(--light)' }}>
                {fmt(s.n_employees)}
              </div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 8, color: 'rgba(255,255,255,0.35)',
                textTransform: 'uppercase', letterSpacing: '1px' }}>Nexus</div>
              <div style={{ fontFamily: 'var(--fd)', fontSize: 18, color: 'var(--gold-light)' }}>
                {s.nexus_count}
              </div>
            </div>
          </div>
        </div>

        {/* Sub-index grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 10 }}>
          {dimKeys.map(key => (
            <SubIndexCard key={key} dimKey={key} dim={data.sub_indices[key]}
              onClick={() => setSelectedDim(selectedDim === key ? null : key)}
              selected={selectedDim === key}
            />
          ))}
        </div>
      </div>

      <DeptTable rows={data.dept_ohi} />
    </div>
  )
}

// ── Trend tab ─────────────────────────────────────────────────────────────────

function TrendTab({ data }: { data: OHIData }) {
  const events = data.trend.filter(p => p.event)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div style={card}>
        <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px',
          textTransform: 'uppercase', color: 'rgba(255,255,255,0.4)', marginBottom: 12 }}>
          24-Month OHI Time Series + 6-Month Forecast
        </div>
        <div style={{ overflowX: 'auto' }}>
          <TrendChart points={data.trend} />
        </div>
        {/* Legend */}
        <div style={{ display: 'flex', gap: 20, marginTop: 12, fontSize: 9,
          color: 'rgba(255,255,255,0.4)', fontFamily: 'var(--fb)' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{ width: 20, height: 2, backgroundColor: 'var(--gold-light)' }} />
            Historical OHI
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{ width: 20, height: 2, backgroundColor: 'rgba(201,168,76,0.5)',
              backgroundImage: 'repeating-linear-gradient(90deg, rgba(201,168,76,0.5) 0 5px, transparent 5px 9px)' }} />
            Forecast
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{ width: 1, height: 14, backgroundColor: 'rgba(255,255,255,0.25)',
              borderLeft: '1px dashed rgba(255,255,255,0.25)' }} />
            Event annotation
          </span>
        </div>
      </div>

      {/* Event log */}
      {events.length > 0 && (
        <div style={card}>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px',
            textTransform: 'uppercase', color: 'rgba(255,255,255,0.4)', marginBottom: 10 }}>
            Annotated Events
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {events.map((e, i) => (
              <div key={i} style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
                <span style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'rgba(255,255,255,0.35)',
                  width: 72, flexShrink: 0 }}>
                  {e.month}
                </span>
                <div style={{ width: 6, height: 6, borderRadius: '50%',
                  backgroundColor: 'rgba(255,255,255,0.3)', flexShrink: 0 }} />
                <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.65)' }}>{e.event}</span>
                <span style={{ fontFamily: 'var(--fd)', fontSize: 14, color: 'var(--gold-light)',
                  marginLeft: 'auto' }}>{e.score.toFixed(0)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Impact preview tab ────────────────────────────────────────────────────────

function PreviewTab({ data }: { data: OHIData }) {
  const points    = data.decision_preview
  const baseOHI   = data.summary.overall
  const [selIdx, setSelIdx] = useState(points.length - 1)  // start at 100% retention
  const sel       = points[selIdx] ?? points[points.length - 1]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Intro */}
      <div style={{ ...card, fontSize: 11, color: 'rgba(255,255,255,0.55)', lineHeight: 1.65 }}>
        Simulate the OHI impact of different budget retention levels before executing any structural change.
        Sliding left reduces headcount and shows the projected OHI cost of that decision.
      </div>

      {/* Slider + KPI */}
      <div style={card}>
        <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px',
          textTransform: 'uppercase', color: 'rgba(255,255,255,0.4)', marginBottom: 8 }}>
          Retention scenario: keep {sel.retention_pct}% of headcount ({sel.n_retained} employees)
        </div>
        <input type="range" min={0} max={points.length - 1} step={1}
          value={selIdx} onChange={e => setSelIdx(Number(e.target.value))}
          style={{ width: '100%', accentColor: 'var(--gold-light)', marginBottom: 16 }} />

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12 }}>
          {[
            { label: 'Projected OHI',   value: sel.ohi.toFixed(1),
              color: gradeColor(sel.ohi >= 85 ? 'A' : sel.ohi >= 70 ? 'B' : 'C') },
            { label: 'OHI Delta',
              value: `${sel.ohi_delta >= 0 ? '+' : ''}${sel.ohi_delta.toFixed(1)}`,
              color: sel.ohi_delta >= 0 ? '#1a8c4e' : '#e03448' },
            { label: 'Budget Savings',  value: `${sel.budget_savings_pct}%`, color: '#2a7ab0' },
            { label: 'Headcount Kept',  value: String(sel.n_retained),       color: 'var(--gold-light)' },
          ].map(k => (
            <div key={k.label} style={{ ...card, textAlign: 'center' }}>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 8, letterSpacing: '1.5px',
                textTransform: 'uppercase', color: 'rgba(255,255,255,0.35)', marginBottom: 6 }}>
                {k.label}
              </div>
              <div style={{ fontFamily: 'var(--fd)', fontSize: 26, color: k.color, lineHeight: 1 }}>
                {k.value}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Before → After */}
      <div style={{ display: 'flex', gap: 20, alignItems: 'center' }}>
        <div style={{ ...card, flex: 1, textAlign: 'center' }}>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 8, color: 'rgba(255,255,255,0.35)',
            textTransform: 'uppercase', letterSpacing: '1.5px', marginBottom: 6 }}>
            Current OHI
          </div>
          <div style={{ fontFamily: 'var(--fd)', fontSize: 40, color: 'var(--gold-light)' }}>
            {baseOHI.toFixed(1)}
          </div>
        </div>
        <div style={{ fontSize: 24, color: 'rgba(255,255,255,0.3)' }}>→</div>
        <div style={{ ...card, flex: 1, textAlign: 'center',
          borderColor: sel.ohi_delta < -5 ? '#e0344844' : 'rgba(255,255,255,0.06)' }}>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 8, color: 'rgba(255,255,255,0.35)',
            textTransform: 'uppercase', letterSpacing: '1.5px', marginBottom: 6 }}>
            Projected OHI ({sel.retention_pct}% retained)
          </div>
          <div style={{ fontFamily: 'var(--fd)', fontSize: 40,
            color: gradeColor(sel.ohi >= 85 ? 'A' : sel.ohi >= 70 ? 'B' : 'C') }}>
            {sel.ohi.toFixed(1)}
          </div>
        </div>
      </div>

      {/* Pareto chart */}
      <div style={card}>
        <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px',
          textTransform: 'uppercase', color: 'rgba(255,255,255,0.4)', marginBottom: 4 }}>
          Budget Savings vs OHI Cost — Pareto Frontier
        </div>
        <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', marginBottom: 12 }}>
          Each point shows the OHI score achievable at a given budget reduction level.
          Highlighted point matches the slider above.
        </div>
        <PreviewPareto points={points} selectedPct={sel.retention_pct} />
      </div>
    </div>
  )
}

// ── Benchmark tab ─────────────────────────────────────────────────────────────

function BenchmarkTab({ data }: { data: OHIData }) {
  const bm = data.benchmark

  // Count above/below benchmark
  const above = Object.entries(data.sub_indices).filter(
    ([k, v]) => bm.sub_indices[k] && v.score > bm.sub_indices[k].p75
  ).length
  const below = Object.entries(data.sub_indices).filter(
    ([k, v]) => bm.sub_indices[k] && v.score < bm.sub_indices[k].p25
  ).length

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Benchmark context */}
      <div style={{ ...card, display: 'flex', gap: 24, alignItems: 'center', flexWrap: 'wrap' }}>
        {[
          { label: 'Synthetic Comparators', value: String(bm.comparators), sub: `${bm.org_size} orgs` },
          { label: 'Sub-Indices Above P75', value: String(above), sub: 'outperforming benchmark' },
          { label: 'Sub-Indices Below P25', value: String(below), sub: 'improvement areas' },
        ].map(k => (
          <div key={k.label} style={{ textAlign: 'center', flex: 1 }}>
            <div style={{ fontFamily: 'var(--fb)', fontSize: 8, letterSpacing: '1.5px',
              textTransform: 'uppercase', color: 'rgba(255,255,255,0.35)', marginBottom: 4 }}>
              {k.label}
            </div>
            <div style={{ fontFamily: 'var(--fd)', fontSize: 28, color: 'var(--gold-light)' }}>
              {k.value}
            </div>
            <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.35)', marginTop: 2 }}>{k.sub}</div>
          </div>
        ))}
        <div style={{ flex: 2, fontSize: 10, color: 'rgba(255,255,255,0.35)', lineHeight: 1.6,
          borderLeft: '1px solid rgba(255,255,255,0.08)', paddingLeft: 20 }}>
          ⓘ {bm.source}. Comparator profiles are generated from synthetic organizational data across
          similar workforce sizes. Not based on real company benchmarks.
        </div>
      </div>

      {/* Benchmark chart */}
      <div style={card}>
        <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px',
          textTransform: 'uppercase', color: 'rgba(255,255,255,0.4)', marginBottom: 16 }}>
          Sub-Index Position vs Synthetic Benchmark
        </div>
        <BenchmarkChart subIndices={data.sub_indices} benchmark={bm.sub_indices} />
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function OHIPage() {
  const { scenario, size } = useDemoStore()
  const [data, setData]   = useState<OHIData | null>(null)
  const [tab, setTab]     = useState<Tab>('overview')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setData(null)
    setError(null)
    api.ohi.data(scenario, size)
      .then(setData)
      .catch(e => setError(String(e)))
  }, [scenario, size])

  const pageStyle: React.CSSProperties = {
    padding: '32px 40px', minHeight: '100vh',
    backgroundColor: 'var(--light)', color: 'var(--light)',
  }

  if (error) return (
    <div style={{ ...pageStyle, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <span style={{ color: '#e03448', fontFamily: 'var(--fb)', fontSize: 13 }}>
        Failed to load OHI data: {error}
      </span>
    </div>
  )

  if (!data) return (
    <div style={{ ...pageStyle, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <span style={{ color: 'rgba(255,255,255,0.4)', fontFamily: 'var(--fb)', fontSize: 13 }}>
        Computing Organizational Health Index…
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
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontFamily: 'var(--fd)', fontSize: 28, fontWeight: 300,
          color: 'var(--light)', margin: 0, marginBottom: 4 }}>
          Organizational Health Index
        </h1>
        <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)', margin: 0 }}>
          Composite systemic health metric across six dimensions — tracked over time,
          benchmarked against synthetic comparators, and projected against decision scenarios.
        </p>
      </div>

      {/* Alert */}
      {data.alert && <AlertBanner alert={data.alert} />}

      {/* Hero KPIs */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, marginBottom: 28 }}>
        {[
          { label: 'OHI Score',      value: s.overall.toFixed(1), sub: `Grade ${s.grade}`, color: gradeColor(s.grade) },
          { label: '90-Day Trend',
            value: `${s.trend_delta_90d >= 0 ? '+' : ''}${s.trend_delta_90d.toFixed(1)}`,
            sub: s.trend_direction, color: dirColor(s.trend_direction) },
          { label: 'Employees',      value: fmt(s.n_employees),   sub: `${s.nexus_count} nexus`,  color: 'var(--gold-light)' },
          { label: 'Sub-Indices',    value: '6',                  sub: 'dimensions tracked',       color: 'var(--gold-light)' },
        ].map(k => (
          <div key={k.label} style={{ ...card, textAlign: 'center' }}>
            <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px',
              textTransform: 'uppercase', color: 'rgba(255,255,255,0.4)', marginBottom: 6 }}>
              {k.label}
            </div>
            <div style={{ fontFamily: 'var(--fd)', fontSize: 30, color: k.color, lineHeight: 1 }}>
              {k.value}
            </div>
            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)', marginTop: 5 }}>{k.sub}</div>
          </div>
        ))}
      </div>

      {/* Tab bar */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 24,
        borderBottom: '1px solid rgba(255,255,255,0.07)', paddingBottom: 12 }}>
        <button style={tabStyle('overview')}   onClick={() => setTab('overview')}>Overview</button>
        <button style={tabStyle('trend')}      onClick={() => setTab('trend')}>24-Month Trend</button>
        <button style={tabStyle('preview')}    onClick={() => setTab('preview')}>Decision Preview</button>
        <button style={tabStyle('benchmark')}  onClick={() => setTab('benchmark')}>Benchmark</button>
      </div>

      {/* Tab content */}
      {tab === 'overview'   && <OverviewTab   data={data} />}
      {tab === 'trend'      && <TrendTab      data={data} />}
      {tab === 'preview'    && <PreviewTab    data={data} />}
      {tab === 'benchmark'  && <BenchmarkTab  data={data} />}
    </div>
  )
}
