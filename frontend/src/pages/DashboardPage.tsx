import React, { useEffect, useState } from 'react'
import Eyebrow from '../components/Eyebrow'
import { api, type DashboardData, type DepartmentRow, type EmployeeRow } from '../services/api'
import { useDemoStore } from '../stores/demoStore'

// ── Design constants ──────────────────────────────────────────────────────────

const PALETTE = ['#003366', '#1a4d80', '#336699', '#4d7099', '#99bbdd', '#c8982a', '#e8c46a', '#b07820', '#ccdde8']

const hero: React.CSSProperties = {
  backgroundColor: 'var(--primary)',
  backgroundImage: `linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px)`,
  backgroundSize: '48px 48px',
  padding: '52px 48px 40px',
}

const wrap: React.CSSProperties = { maxWidth: 'var(--max-width-dashboard)', margin: '0 auto' }

const card: React.CSSProperties = {
  backgroundColor: 'var(--white)',
  borderRadius:    'var(--radius-md)',
  boxShadow:       'var(--shadow-card)',
  border:          '1px solid var(--primary-10)',
}

const sectionGap = 32

// ── Helpers ───────────────────────────────────────────────────────────────────

const fmt$M = (n: number) => `$${(n / 1e6).toFixed(1)}M`
const fmtK  = (n: number) => n >= 1000 ? `${(n / 1000).toFixed(1)}K` : String(n)

function impactColor(s: number) {
  return s >= 70 ? 'var(--status-green)' : s >= 40 ? 'var(--gold)' : 'var(--status-orange)'
}
function riskColor(r: number) {
  return r >= 0.7 ? 'var(--status-red)' : r >= 0.5 ? 'var(--status-orange)' : r >= 0.3 ? 'var(--gold)' : 'var(--status-green)'
}
function varianceColor(v: number) {
  return v > 10 ? 'var(--status-red)' : v > 4 ? 'var(--status-orange)' : v < -4 ? 'var(--status-green)' : 'var(--gold)'
}
function varianceBg(v: number) {
  return v > 10 ? 'var(--status-red-bg)'
       : v > 4  ? 'var(--status-orange-bg)'
       : v < -4 ? 'var(--status-green-bg)'
       : 'rgba(200,152,42,0.10)'
}
function varianceBorder(v: number) {
  return v > 10 ? 'rgba(224,52,72,0.25)'
       : v > 4  ? 'rgba(240,112,32,0.25)'
       : v < -4 ? 'rgba(39,185,124,0.25)'
       : 'rgba(200,152,42,0.25)'
}

// ── Hero KPI stat ─────────────────────────────────────────────────────────────

function HeroStat({ value, label, sub }: { value: string; label: string; sub?: string }) {
  return (
    <div style={{ borderLeft: '2px solid var(--gold)', paddingLeft: 18, minWidth: 120 }}>
      <div style={{ fontFamily: 'var(--fd)', fontSize: 32, fontWeight: 300, color: 'var(--gold-light)', lineHeight: 1 }}>
        {value}
      </div>
      {sub && (
        <div style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'rgba(255,255,255,0.5)', marginTop: 3 }}>{sub}</div>
      )}
      <div style={{ fontFamily: 'var(--fb)', fontSize: 10, letterSpacing: '2px', textTransform: 'uppercase', color: 'rgba(255,255,255,0.4)', marginTop: 4 }}>
        {label}
      </div>
    </div>
  )
}

// ── Section header ────────────────────────────────────────────────────────────

function SectionHead({ eyebrow, title, sub }: { eyebrow: string; title: React.ReactNode; sub?: string }) {
  return (
    <div style={{ marginBottom: 20 }}>
      <Eyebrow>{eyebrow}</Eyebrow>
      <h2 style={{ fontFamily: 'var(--fd)', fontSize: 21, fontWeight: 300, color: 'var(--dark)', margin: '6px 0 0' }}>
        {title}
      </h2>
      {sub && <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)', marginTop: 4 }}>{sub}</p>}
    </div>
  )
}

// ── SVG: Budget Variance per Department ───────────────────────────────────────

function BudgetVarianceChart({ rows }: { rows: DepartmentRow[] }) {
  const sorted  = [...rows].sort((a, b) => b.budget_variance_pct - a.budget_variance_pct)
  const maxAbs  = Math.max(15, ...sorted.map(r => Math.abs(r.budget_variance_pct)))
  const ROW_H   = 38
  const PAD_L   = 148
  const BAR_W   = 320
  const PAD_R   = 64
  const W       = PAD_L + BAR_W + PAD_R
  const H       = sorted.length * ROW_H + 28
  const ZERO_X  = PAD_L + BAR_W / 2
  const scale   = (BAR_W / 2) / maxAbs

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: 'block' }}>
      {/* Zero line */}
      <line x1={ZERO_X} y1={0} x2={ZERO_X} y2={H - 24} stroke="rgba(0,51,102,0.12)" strokeWidth={1} />

      {/* Axis ticks */}
      {[-1, -0.5, 0, 0.5, 1].map(t => {
        const x = ZERO_X + t * (BAR_W / 2)
        return (
          <g key={t}>
            <line x1={x} y1={0} x2={x} y2={H - 24} stroke="rgba(0,51,102,0.06)" strokeWidth={1} />
            <text x={x} y={H - 6} fontSize={8} fill="#9ca3af" textAnchor="middle">
              {t > 0 ? '+' : ''}{(t * maxAbs).toFixed(0)}%
            </text>
          </g>
        )
      })}

      {sorted.map((r, i) => {
        const y      = i * ROW_H + ROW_H / 2
        const barW   = Math.abs(r.budget_variance_pct) * scale
        const barX   = r.budget_variance_pct >= 0 ? ZERO_X : ZERO_X - barW
        const color  = r.budget_variance_pct > 10 ? '#e03448'
                     : r.budget_variance_pct > 4  ? '#f07020'
                     : r.budget_variance_pct < -4 ? '#27b97c'
                     : '#c8982a'
        return (
          <g key={r.department}>
            <text x={PAD_L - 10} y={y + 4} fontSize={11} fill="#1c1c2e" textAnchor="end"
              fontFamily="'Plus Jakarta Sans', sans-serif">
              {r.department.length > 16 ? r.department.slice(0, 15) + '…' : r.department}
            </text>
            <rect x={PAD_L} y={y - 8} width={BAR_W} height={16} fill="rgba(0,51,102,0.04)" rx={3} />
            <rect x={barX} y={y - 8} width={Math.max(3, barW)} height={16} fill={color} rx={3} opacity={0.82} />
            <text x={PAD_L + BAR_W + 8} y={y + 4} fontSize={10} fill={color}
              fontFamily="'Plus Jakarta Sans', sans-serif" fontWeight="600">
              {r.budget_variance_pct >= 0 ? '+' : ''}{r.budget_variance_pct.toFixed(1)}%
            </text>
          </g>
        )
      })}
    </svg>
  )
}

// ── SVG: Spend Donut ──────────────────────────────────────────────────────────

function SpendDonut({ rows }: { rows: DepartmentRow[] }) {
  const sorted = [...rows].sort((a, b) => b.total_spend - a.total_spend)
  const total  = rows.reduce((s, r) => s + r.total_spend, 0)
  const R = 36, C = 2 * Math.PI * R
  let cum = 0

  const segments = sorted.map((r, i) => {
    const pct    = r.total_spend / total
    const dash   = C * pct
    const offset = C * (1 - cum)
    cum += pct
    return { ...r, dash, offset, color: PALETTE[i % PALETTE.length] }
  })

  return (
    <div>
      <svg viewBox="0 0 100 100" width="100%" style={{ display: 'block', maxHeight: 180 }}>
        <circle cx="50" cy="50" r={R} fill="none" stroke="var(--primary-10)" strokeWidth={20} />
        {segments.map(s => (
          <circle key={s.department} cx="50" cy="50" r={R}
            fill="none" stroke={s.color} strokeWidth={20}
            strokeDasharray={`${s.dash} ${C - s.dash}`}
            strokeDashoffset={s.offset}
            transform="rotate(-90 50 50)"
            opacity={0.88}
          />
        ))}
        <text x="50" y="46" textAnchor="middle" fontSize="6.5" fill="#6b7280" fontFamily="'Plus Jakarta Sans', sans-serif">Total Spend</text>
        <text x="50" y="57" textAnchor="middle" fontSize="9" fill="#003366" fontFamily="Fraunces, serif" fontWeight="700">
          {fmt$M(total)}
        </text>
      </svg>

      {/* Legend */}
      <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 5 }}>
        {segments.slice(0, 6).map(s => (
          <div key={s.department} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 8, height: 8, borderRadius: 2, backgroundColor: s.color, flexShrink: 0 }} />
            <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--dark)', flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {s.department}
            </div>
            <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', flexShrink: 0 }}>
              {(s.total_spend / total * 100).toFixed(0)}%
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── SVG: Impact Score Histogram ───────────────────────────────────────────────

function ImpactHistogram({ employees }: { employees: EmployeeRow[] }) {
  const buckets = [
    { label: '0–20',   min: 0,  max: 20,  color: '#99bbdd' },
    { label: '20–40',  min: 20, max: 40,  color: '#4d7099' },
    { label: '40–60',  min: 40, max: 60,  color: '#336699' },
    { label: '60–80',  min: 60, max: 80,  color: '#1a4d80' },
    { label: '80–100', min: 80, max: 101, color: '#c8982a' },
  ]
  const counts = buckets.map(b => employees.filter(e => e.impact_score >= b.min && e.impact_score < b.max).length)
  const maxC   = Math.max(...counts, 1)
  const W = 260, H = 150, PB = 28, PT = 12, PL = 8, PR = 8
  const bW = (W - PL - PR) / buckets.length

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: 'block' }}>
      <line x1={PL} y1={H - PB} x2={W - PR} y2={H - PB} stroke="rgba(0,51,102,0.12)" strokeWidth={1} />
      {buckets.map((b, i) => {
        const barH = (counts[i] / maxC) * (H - PB - PT)
        const x    = PL + i * bW + bW * 0.12
        const bw   = bW * 0.76
        const y    = PT + (H - PB - PT) - barH
        return (
          <g key={b.label}>
            <rect x={x} y={y} width={bw} height={barH} fill={b.color} rx={3} opacity={0.83} />
            {counts[i] > 0 && (
              <text x={x + bw / 2} y={y - 3} fontSize={8.5} fill={b.color} textAnchor="middle" fontWeight="700">
                {counts[i]}
              </text>
            )}
            <text x={x + bw / 2} y={H - 6} fontSize={8} fill="#9ca3af" textAnchor="middle">
              {b.label}
            </text>
          </g>
        )
      })}
    </svg>
  )
}

// ── Attrition Risk Tier breakdown ─────────────────────────────────────────────

function AttritionTiers({ employees }: { employees: EmployeeRow[] }) {
  const tiers = [
    { label: 'Critical', min: 0.70, color: 'var(--status-red)',    bg: 'rgba(224,52,72,0.08)'   },
    { label: 'High',     min: 0.50, color: 'var(--status-orange)', bg: 'rgba(240,112,32,0.08)'  },
    { label: 'Moderate', min: 0.30, color: 'var(--gold)',           bg: 'rgba(200,152,42,0.08)'  },
    { label: 'Low',      min: 0.00, color: 'var(--status-green)',   bg: 'rgba(39,185,124,0.08)'  },
  ]
  const total = employees.length || 1
  const counts = tiers.map((t, i) => {
    const max = i === 0 ? 1.01 : tiers[i - 1].min
    return employees.filter(e => e.attrition_risk >= t.min && e.attrition_risk < max).length
  })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {tiers.map((t, i) => (
        <div key={t.label}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
            <span style={{ fontFamily: 'var(--fb)', fontSize: 11, fontWeight: 600, color: t.color,
              backgroundColor: t.bg, borderRadius: 'var(--radius-pill)', padding: '2px 9px' }}>
              {t.label}
            </span>
            <div style={{ textAlign: 'right' }}>
              <span style={{ fontFamily: 'var(--fd)', fontSize: 18, fontWeight: 700, color: t.color }}>{counts[i]}</span>
              <span style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'var(--mid)', marginLeft: 4 }}>
                {(counts[i] / total * 100).toFixed(0)}%
              </span>
            </div>
          </div>
          <div style={{ height: 5, backgroundColor: 'var(--primary-10)', borderRadius: 3 }}>
            <div style={{ height: '100%', borderRadius: 3, backgroundColor: t.color,
              width: `${counts[i] / total * 100}%`, transition: 'width 0.4s' }} />
          </div>
        </div>
      ))}
    </div>
  )
}

// ── SVG: Strategic Quadrant ───────────────────────────────────────────────────

function QuadrantChart({ employees }: { employees: EmployeeRow[] }) {
  const sample = employees.length > 400
    ? employees.filter((_, i) => i % Math.ceil(employees.length / 400) === 0)
    : employees

  const W = 540, H = 300
  const PL = 40, PR = 20, PT = 22, PB = 38
  const pW = W - PL - PR, pH = H - PT - PB
  const RX = 0.50, IY = 60  // thresholds
  const qx = PL + pW * RX
  const qy = PT + pH * (1 - IY / 100)

  const toX = (r: number) => PL + r * pW
  const toY = (s: number) => PT + (1 - s / 100) * pH

  const dot = (e: EmployeeRow) => {
    const hi = e.attrition_risk >= RX && e.impact_score >= IY
    const hp = e.attrition_risk < RX  && e.impact_score >= IY
    const rv = e.attrition_risk >= RX && e.impact_score < IY
    return hi ? '#e03448' : hp ? '#27b97c' : rv ? '#f07020' : '#99bbdd'
  }

  // Quadrant counts
  const qCounts = {
    actNow:  sample.filter(e => e.attrition_risk >= RX && e.impact_score >= IY).length,
    protect: sample.filter(e => e.attrition_risk <  RX && e.impact_score >= IY).length,
    review:  sample.filter(e => e.attrition_risk >= RX && e.impact_score <  IY).length,
    monitor: sample.filter(e => e.attrition_risk <  RX && e.impact_score <  IY).length,
  }

  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: 'block' }}>
        {/* Quadrant fills */}
        <rect x={PL}  y={PT}  width={qx - PL}     height={qy - PT}     fill="rgba(39,185,124,0.05)"  />
        <rect x={qx}  y={PT}  width={W - PR - qx}  height={qy - PT}     fill="rgba(224,52,72,0.06)"   />
        <rect x={PL}  y={qy}  width={qx - PL}     height={H - PB - qy} fill="rgba(0,51,102,0.03)"    />
        <rect x={qx}  y={qy}  width={W - PR - qx}  height={H - PB - qy} fill="rgba(240,112,32,0.05)" />

        {/* Quadrant labels */}
        <text x={PL + 6}  y={PT + 13} fontSize={8.5} fill="#27b97c" fontWeight="700" letterSpacing="1" fontFamily="'Plus Jakarta Sans',sans-serif">PROTECT ({qCounts.protect})</text>
        <text x={qx + 6}  y={PT + 13} fontSize={8.5} fill="#e03448" fontWeight="700" letterSpacing="1" fontFamily="'Plus Jakarta Sans',sans-serif">ACT NOW ({qCounts.actNow})</text>
        <text x={PL + 6}  y={H - PB - 6} fontSize={8.5} fill="#99bbdd" letterSpacing="1" fontFamily="'Plus Jakarta Sans',sans-serif">MONITOR ({qCounts.monitor})</text>
        <text x={qx + 6}  y={H - PB - 6} fontSize={8.5} fill="#f07020" letterSpacing="1" fontFamily="'Plus Jakarta Sans',sans-serif">REVIEW ({qCounts.review})</text>

        {/* Dividers */}
        <line x1={qx} y1={PT} x2={qx} y2={H - PB} stroke="rgba(0,51,102,0.18)" strokeWidth={1} strokeDasharray="4 3" />
        <line x1={PL} y1={qy} x2={W - PR} y2={qy}  stroke="rgba(0,51,102,0.18)" strokeWidth={1} strokeDasharray="4 3" />

        {/* Dots */}
        {sample.map(e => {
          const cx = toX(e.attrition_risk)
          const cy = toY(e.impact_score)
          const c  = dot(e)
          const r  = e.is_nexus ? 5 : 3
          return (
            <g key={e.employee_id}>
              {e.is_nexus && <circle cx={cx} cy={cy} r={r + 3} fill="none" stroke="#c8982a" strokeWidth={1.5} opacity={0.65} />}
              <circle cx={cx} cy={cy} r={r} fill={c} opacity={0.72} />
            </g>
          )
        })}

        {/* Axes */}
        <line x1={PL} y1={H - PB} x2={W - PR} y2={H - PB} stroke="rgba(0,51,102,0.15)" strokeWidth={1} />
        <line x1={PL} y1={PT}     x2={PL}      y2={H - PB} stroke="rgba(0,51,102,0.15)" strokeWidth={1} />

        {/* Axis labels */}
        <text x={PL + pW / 2} y={H - 4}  fontSize={9} fill="#6b7280" textAnchor="middle" fontFamily="'Plus Jakarta Sans',sans-serif">Attrition Risk →</text>
        <text x={12}           y={PT + pH / 2} fontSize={9} fill="#6b7280" textAnchor="middle" fontFamily="'Plus Jakarta Sans',sans-serif" transform={`rotate(-90 12 ${PT + pH / 2})`}>Impact Score →</text>

        {/* Tick labels */}
        <text x={PL}       y={H - PB + 11} fontSize={8} fill="#9ca3af" textAnchor="middle">0%</text>
        <text x={W - PR}   y={H - PB + 11} fontSize={8} fill="#9ca3af" textAnchor="middle">100%</text>
        <text x={PL - 4}   y={PT + 4}      fontSize={8} fill="#9ca3af" textAnchor="end">100</text>
        <text x={PL - 4}   y={H - PB + 4}  fontSize={8} fill="#9ca3af" textAnchor="end">0</text>
      </svg>

      {/* Legend */}
      <div style={{ display: 'flex', gap: 20, justifyContent: 'center', marginTop: 10, flexWrap: 'wrap' }}>
        {[
          { color: '#27b97c', label: 'Protect — high impact, low risk'   },
          { color: '#e03448', label: 'Act Now — high impact, high risk'  },
          { color: '#f07020', label: 'Review — low impact, high risk'    },
          { color: '#99bbdd', label: 'Monitor — low impact, low risk'    },
        ].map(({ color, label }) => (
          <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: color }} />
            <span style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'var(--mid)' }}>{label}</span>
          </div>
        ))}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <svg width="14" height="14" viewBox="0 0 14 14">
            <circle cx="7" cy="7" r="5" fill="none" stroke="#c8982a" strokeWidth="1.5" />
            <circle cx="7" cy="7" r="2.5" fill="#c8982a" opacity="0.72" />
          </svg>
          <span style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'var(--mid)' }}>Nexus employee</span>
        </div>
      </div>
    </div>
  )
}

// ── Nexus Spotlight cards ─────────────────────────────────────────────────────

function NexusSpotlight({ employees }: { employees: EmployeeRow[] }) {
  const nexus = employees.filter(e => e.is_nexus).sort((a, b) => b.impact_score - a.impact_score).slice(0, 6)
  if (!nexus.length) return (
    <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)' }}>No Nexus employees identified in this scenario.</p>
  )
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16 }}>
      {nexus.map(e => {
        const initials = e.full_name.split(' ').map(n => n[0]).join('').slice(0, 2)
        const attrRisk = Math.round(e.attrition_risk * 100)
        const attrC    = riskColor(e.attrition_risk)
        return (
          <div key={e.employee_id} style={{ ...card, padding: 18 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14 }}>
              <div style={{
                width: 42, height: 42, borderRadius: '50%', flexShrink: 0,
                background: 'linear-gradient(135deg, var(--primary) 0%, var(--primary-60) 100%)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                border: '2px solid var(--gold)',
              }}>
                <span style={{ fontFamily: 'var(--fd)', fontSize: 15, fontWeight: 700, color: '#fff' }}>{initials}</span>
              </div>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontFamily: 'var(--fb)', fontSize: 12, fontWeight: 600, color: 'var(--dark)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {e.full_name}
                </div>
                <div style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'var(--mid)', marginTop: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {e.role_title}
                </div>
              </div>
            </div>

            <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase',
              color: 'var(--gold)', fontWeight: 700, marginBottom: 10 }}>{e.department}</div>

            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10 }}>
              <div>
                <div style={{ fontFamily: 'var(--fb)', fontSize: 8, letterSpacing: '1px', textTransform: 'uppercase', color: 'var(--mid)', marginBottom: 2 }}>Impact</div>
                <div style={{ fontFamily: 'var(--fd)', fontSize: 20, fontWeight: 700, color: impactColor(e.impact_score) }}>{e.impact_score.toFixed(0)}</div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontFamily: 'var(--fb)', fontSize: 8, letterSpacing: '1px', textTransform: 'uppercase', color: 'var(--mid)', marginBottom: 2 }}>Attrition</div>
                <div style={{ fontFamily: 'var(--fd)', fontSize: 20, fontWeight: 700, color: attrC }}>{attrRisk}%</div>
              </div>
            </div>

            <div style={{ marginTop: 10, height: 3, backgroundColor: 'var(--primary-10)', borderRadius: 2 }}>
              <div style={{ height: '100%', borderRadius: 2, backgroundColor: attrC, width: `${attrRisk}%` }} />
            </div>
            <div style={{ fontFamily: 'var(--fb)', fontSize: 9, color: 'var(--mid)', marginTop: 4 }}>Top skill: {e.top_skill}</div>
          </div>
        )
      })}
    </div>
  )
}

// ── Department table (improved) ───────────────────────────────────────────────

function DeptTable({ rows }: { rows: DepartmentRow[] }) {
  const sorted = [...rows].sort((a, b) => b.total_spend - a.total_spend)
  const th: React.CSSProperties = {
    fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 600, letterSpacing: '2px',
    textTransform: 'uppercase', padding: '11px 14px',
    color: '#fff', background: 'var(--primary)', whiteSpace: 'nowrap',
  }
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={th}>Department</th>
            <th style={{ ...th, textAlign: 'right' }}>Headcount</th>
            <th style={{ ...th, textAlign: 'right' }}>Spend</th>
            <th style={{ ...th, textAlign: 'right' }}>Budget</th>
            <th style={{ ...th, textAlign: 'center' }}>Variance</th>
            <th style={{ ...th, minWidth: 120 }}>Avg Impact</th>
            <th style={{ ...th, minWidth: 110 }}>Fragility</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((r, i) => {
            const vColor  = varianceColor(r.budget_variance_pct)
            const fragPct = Math.round(r.fragility_avg * 100)
            const fragC   = r.fragility_avg >= 0.7 ? 'var(--status-red)' : r.fragility_avg >= 0.4 ? 'var(--status-orange)' : 'var(--status-green)'
            return (
              <tr key={r.department} style={{ background: i % 2 === 0 ? 'var(--white)' : 'rgba(0,51,102,0.02)', borderBottom: '1px solid var(--primary-10)' }}>
                <td style={{ fontFamily: 'var(--fb)', fontSize: 13, padding: '11px 14px', fontWeight: 600, color: 'var(--dark)' }}>
                  {r.department}
                </td>
                <td style={{ fontFamily: 'var(--fb)', fontSize: 13, padding: '11px 14px', textAlign: 'right', color: 'var(--dark)' }}>
                  {r.headcount.toLocaleString()}
                </td>
                <td style={{ fontFamily: 'var(--fb)', fontSize: 13, padding: '11px 14px', textAlign: 'right', color: 'var(--dark)' }}>
                  {fmt$M(r.total_spend)}
                </td>
                <td style={{ fontFamily: 'var(--fb)', fontSize: 13, padding: '11px 14px', textAlign: 'right', color: 'var(--mid)' }}>
                  {fmt$M(r.annual_budget)}
                </td>
                <td style={{ padding: '11px 14px', textAlign: 'center' }}>
                  <span style={{ fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 700, color: vColor,
                    backgroundColor: varianceBg(r.budget_variance_pct),
                    borderRadius: 'var(--radius-pill)', padding: '2px 9px',
                    border: `1px solid ${varianceBorder(r.budget_variance_pct)}`,
                  }}>
                    {r.budget_variance_pct >= 0 ? '+' : ''}{r.budget_variance_pct.toFixed(1)}%
                  </span>
                </td>
                <td style={{ padding: '11px 14px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                    <div style={{ flex: 1, height: 4, background: 'var(--primary-10)', borderRadius: 2 }}>
                      <div style={{ width: `${r.avg_impact}%`, height: '100%', background: impactColor(r.avg_impact), borderRadius: 2 }} />
                    </div>
                    <span style={{ fontFamily: 'var(--fb)', fontSize: 11, fontWeight: 600, color: impactColor(r.avg_impact), minWidth: 26, textAlign: 'right' }}>
                      {r.avg_impact.toFixed(0)}
                    </span>
                  </div>
                </td>
                <td style={{ padding: '11px 14px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                    <div style={{ flex: 1, height: 4, background: 'var(--primary-10)', borderRadius: 2 }}>
                      <div style={{ width: `${fragPct}%`, height: '100%', background: fragC, borderRadius: 2 }} />
                    </div>
                    <span style={{ fontFamily: 'var(--fb)', fontSize: 11, fontWeight: 600, color: fragC, minWidth: 32, textAlign: 'right' }}>
                      {fragPct}%
                    </span>
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ── Employee table ────────────────────────────────────────────────────────────

function EmployeeTable({ rows }: { rows: EmployeeRow[] }) {
  const [query,   setQuery]   = useState('')
  const [sortKey, setSortKey] = useState<keyof EmployeeRow>('impact_score')
  const [sortAsc, setSortAsc] = useState(false)

  const toggle = (key: keyof EmployeeRow) => {
    if (sortKey === key) setSortAsc(a => !a)
    else { setSortKey(key); setSortAsc(false) }
  }

  const filtered = rows
    .filter(r => {
      const q = query.toLowerCase()
      return r.full_name.toLowerCase().includes(q) || r.department.toLowerCase().includes(q) || r.role_title.toLowerCase().includes(q)
    })
    .sort((a, b) => {
      const av = a[sortKey], bv = b[sortKey]
      const cmp = typeof av === 'string' ? av.localeCompare(bv as string) : (av as number) - (bv as number)
      return sortAsc ? cmp : -cmp
    })

  const th = (align: 'left' | 'right' | 'center' = 'left'): React.CSSProperties => ({
    fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 600, letterSpacing: '2px',
    textTransform: 'uppercase', padding: '11px 14px', textAlign: align,
    color: '#fff', background: 'var(--primary)', cursor: 'pointer', whiteSpace: 'nowrap',
  })

  const header = (label: string, key: keyof EmployeeRow, align?: 'left' | 'right' | 'center') => (
    <th style={th(align)} onClick={() => toggle(key)}>
      {label}{sortKey === key ? (sortAsc ? ' ▴' : ' ▾') : ''}
    </th>
  )

  return (
    <div>
      <div style={{ marginBottom: 14, display: 'flex', gap: 12, alignItems: 'center' }}>
        <input
          value={query} onChange={e => setQuery(e.target.value)}
          placeholder="Search by name, department, role…"
          style={{ fontFamily: 'var(--fb)', fontSize: 13, padding: '8px 14px', borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--primary-10)', background: 'var(--white)', color: 'var(--dark)',
            width: 300, outline: 'none' }}
        />
        <span style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)' }}>
          {filtered.length.toLocaleString()} employees
        </span>
      </div>
      <div style={{ overflowX: 'auto', maxHeight: 460, overflowY: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead style={{ position: 'sticky', top: 0 }}>
            <tr>
              {header('Name',       'full_name')}
              {header('Department', 'department')}
              {header('Role',       'role_title')}
              {header('Salary',     'annual_salary', 'right')}
              {header('Impact',     'impact_score',  'right')}
              {header('Attrition', 'attrition_risk', 'right')}
              <th style={th('center')}>Flags</th>
            </tr>
          </thead>
          <tbody>
            {filtered.slice(0, 200).map((r, i) => (
              <tr key={r.employee_id} style={{ background: i % 2 === 0 ? 'var(--white)' : 'rgba(0,51,102,0.02)', borderBottom: '1px solid var(--primary-10)' }}>
                <td style={{ fontFamily: 'var(--fb)', fontSize: 13, padding: '10px 14px', fontWeight: 600, color: 'var(--dark)' }}>{r.full_name}</td>
                <td style={{ fontFamily: 'var(--fb)', fontSize: 12, padding: '10px 14px', color: 'var(--mid)' }}>{r.department}</td>
                <td style={{ fontFamily: 'var(--fb)', fontSize: 12, padding: '10px 14px', color: 'var(--mid)' }}>{r.role_title}</td>
                <td style={{ fontFamily: 'var(--fb)', fontSize: 12, padding: '10px 14px', textAlign: 'right', color: 'var(--dark)' }}>
                  ${r.annual_salary.toLocaleString()}
                </td>
                <td style={{ fontFamily: 'var(--fb)', fontSize: 12, padding: '10px 14px', textAlign: 'right' }}>
                  <span style={{ fontFamily: 'var(--fd)', fontSize: 14, fontWeight: 700, color: impactColor(r.impact_score) }}>
                    {r.impact_score.toFixed(0)}
                  </span>
                </td>
                <td style={{ fontFamily: 'var(--fb)', fontSize: 12, padding: '10px 14px', textAlign: 'right' }}>
                  <span style={{ color: riskColor(r.attrition_risk), fontWeight: 600 }}>
                    {(r.attrition_risk * 100).toFixed(0)}%
                  </span>
                </td>
                <td style={{ padding: '10px 14px', textAlign: 'center' }}>
                  {r.is_nexus && (
                    <span style={{ fontFamily: 'var(--fb)', fontSize: 8, fontWeight: 700, letterSpacing: '1px',
                      textTransform: 'uppercase', color: 'var(--gold)',
                      border: '1px solid var(--gold)', borderRadius: 'var(--radius-pill)', padding: '2px 7px' }}>
                      Nexus
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length > 200 && (
          <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)', padding: '12px', textAlign: 'center' }}>
            Showing 200 of {filtered.length.toLocaleString()} — refine your search to see more.
          </div>
        )}
      </div>
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────

const SCENARIO_NAMES: Record<string, string> = { A: 'Growing Company', B: 'Restructuring', C: 'Merger Integration' }

export default function DashboardPage() {
  const { scenario, size, enabled: demo } = useDemoStore()
  const [data,    setData]    = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState<string | null>(null)

  useEffect(() => {
    setLoading(true); setError(null)
    api.dashboard.data(scenario, size, demo)
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [scenario, size, demo])

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
      <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: 'var(--mid)' }}>Loading analytics data…</p>
    </div>
  )

  if (error || !data) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
      <div style={{ textAlign: 'center' }}>
        <p style={{ fontFamily: 'var(--fd)', fontSize: 18, color: 'var(--status-orange)', marginBottom: 6 }}>Could not load dashboard data.</p>
        <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)' }}>{error ?? 'Unknown error'} — ensure the backend is running.</p>
      </div>
    </div>
  )

  const criticalAttrition = data.employee_table.filter(e => e.attrition_risk >= 0.7).length
  const highAttrition     = data.employee_table.filter(e => e.attrition_risk >= 0.5 && e.attrition_risk < 0.7).length

  return (
    <div style={{ backgroundColor: 'var(--light)' }}>

      {/* ── Hero ── */}
      <div style={hero}>
        <div style={wrap}>
          <Eyebrow light>
            {data.org_size.toUpperCase()} · SCENARIO {data.scenario_id} — {SCENARIO_NAMES[data.scenario_id] ?? data.scenario_id}
          </Eyebrow>
          <h1 style={{ fontFamily: 'var(--fd)', fontSize: 34, fontWeight: 300, color: '#fff', margin: '0 0 6px', lineHeight: 1.2 }}>
            {data.org_name} — <em style={{ fontStyle: 'italic', color: 'var(--gold-light)' }}>Executive Dashboard</em>
          </h1>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'rgba(255,255,255,0.45)', margin: '0 0 32px' }}>
            People analytics · budget health · talent risk · network intelligence
          </p>
          <div style={{ display: 'flex', gap: 28, flexWrap: 'wrap' }}>
            <HeroStat value={fmtK(data.total_headcount)}                label="Employees" />
            <HeroStat value={fmt$M(data.total_budget)}                label="Annual Budget" />
            <HeroStat value={fmt$M(data.total_spend)}                 label="Total Spend"
                      sub={`${data.budget_variance_pct >= 0 ? '+' : ''}${data.budget_variance_pct.toFixed(1)}% vs budget`} />
            <HeroStat value={data.avg_impact_score.toFixed(1)}        label="Avg Impact Score" />
            <HeroStat value={String(data.n_nexus_employees)}          label="Nexus Employees"   sub="Network anchors" />
            <HeroStat value={String(criticalAttrition + highAttrition)} label="High/Critical Risk" sub="Retention priority" />
          </div>
        </div>
      </div>

      {/* ── Body ── */}
      <div style={{ maxWidth: 'var(--max-width-dashboard)', margin: '0 auto', padding: '44px 48px', display: 'flex', flexDirection: 'column', gap: sectionGap }}>

        {/* Row 1: Budget Variance + Spend Donut */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 260px', gap: 20 }}>
          <div style={{ ...card, padding: 28 }}>
            <SectionHead
              eyebrow="Financial Health"
              title={<>Budget variance by <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>department</em></>}
              sub="Green = under budget (favorable). Orange/red = overspend requiring attention."
            />
            <BudgetVarianceChart rows={data.dept_summary} />
          </div>
          <div style={{ ...card, padding: 28 }}>
            <SectionHead eyebrow="Spend Allocation" title="Payroll by dept" />
            <SpendDonut rows={data.dept_summary} />
          </div>
        </div>

        {/* Row 2: Impact Histogram + Attrition Tiers + KPIs */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 20 }}>
          <div style={{ ...card, padding: 28 }}>
            <SectionHead eyebrow="Impact Distribution" title={<>Score <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>spread</em></>}
              sub="How impact scores are distributed across the org." />
            <ImpactHistogram employees={data.employee_table} />
          </div>
          <div style={{ ...card, padding: 28 }}>
            <SectionHead eyebrow="Retention Risk" title={<>Attrition <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>tiers</em></>}
              sub="Voluntary departure probability in the next 12 months." />
            <AttritionTiers employees={data.employee_table} />
          </div>
          <div style={{ ...card, padding: 28 }}>
            <SectionHead eyebrow="At a Glance" title={<>Key <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>signals</em></>} />
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {[
                { label: 'Nexus Employees',     value: data.n_nexus_employees,   total: data.total_headcount, color: 'var(--gold)',           caption: 'Network-critical connectors' },
                { label: 'Critical Attrition',  value: criticalAttrition,         total: data.total_headcount, color: 'var(--status-red)',     caption: '≥70% departure probability' },
                { label: 'High Attrition',      value: highAttrition,             total: data.total_headcount, color: 'var(--status-orange)',  caption: '50–70% departure probability' },
                { label: 'Depts Over Budget',   value: data.dept_summary.filter(d => d.budget_variance_pct > 5).length, total: data.dept_summary.length, color: 'var(--status-orange)', caption: 'Departments overspending >5%' },
              ].map(({ label, value, total, color, caption }) => (
                <div key={label}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--dark)' }}>{label}</span>
                    <div>
                      <span style={{ fontFamily: 'var(--fd)', fontSize: 16, fontWeight: 700, color }}>{value}</span>
                      <span style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'var(--mid)', marginLeft: 4 }}>/ {total}</span>
                    </div>
                  </div>
                  <div style={{ height: 4, backgroundColor: 'var(--primary-10)', borderRadius: 2 }}>
                    <div style={{ height: '100%', borderRadius: 2, backgroundColor: color, width: `${Math.min(100, value / total * 100)}%` }} />
                  </div>
                  <div style={{ fontFamily: 'var(--fb)', fontSize: 9, color: 'var(--mid)', marginTop: 3 }}>{caption}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Row 3: Strategic Quadrant */}
        <div style={{ ...card, padding: 28 }}>
          <SectionHead
            eyebrow="Strategic Quadrant"
            title={<>Impact vs Attrition Risk — <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>every employee plotted</em></>}
            sub="Top-right (Act Now): high-impact employees most likely to leave. Top-left (Protect): your stable critical talent. Each gold-ringed dot is an Organizational Nexus."
          />
          <QuadrantChart employees={data.employee_table} />
        </div>

        {/* Row 4: Nexus Spotlight */}
        {data.n_nexus_employees > 0 && (
          <div>
            <SectionHead
              eyebrow="Organizational Nexus"
              title={<>Network <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>anchors</em></>}
              sub="Employees whose departure would fragment the internal collaboration graph. Ranked by impact score."
            />
            <NexusSpotlight employees={data.employee_table} />
          </div>
        )}

        {/* Row 5: Department Health */}
        <div>
          <SectionHead
            eyebrow="Department Overview"
            title={<>Budget, impact, and <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>fragility</em> by department</>}
            sub="Fragility measures team dependency on a small number of critical individuals."
          />
          <div style={{ ...card, overflow: 'hidden' }}>
            <DeptTable rows={data.dept_summary} />
          </div>
        </div>

        {/* Row 6: Employee Table */}
        <div>
          <SectionHead
            eyebrow="Employee Intelligence"
            title={<>Full roster — impact, risk, and <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>network flags</em></>}
            sub="Sort any column. Search filters across name, department, and role."
          />
          <div style={{ ...card, padding: 24 }}>
            <EmployeeTable rows={data.employee_table} />
          </div>
        </div>

      </div>
    </div>
  )
}
