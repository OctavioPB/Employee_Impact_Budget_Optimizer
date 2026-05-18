import React, { useState, useCallback, useRef } from 'react'
import { api, SimulationResult, SimulationEmployee } from '../services/api'
import { useDemoStore } from '../stores/demoStore'

type SimTab = 'configure' | 'impact'

// ── Shared styles ─────────────────────────────────────────────────────────────

const sectionTitle: React.CSSProperties = {
  fontFamily:   'var(--fd)',
  fontSize:     22,
  fontWeight:   600,
  color:        'var(--primary)',
  marginBottom: 4,
}

const labelStyle: React.CSSProperties = {
  fontFamily:    'var(--fb)',
  fontSize:      10,
  letterSpacing: '2px',
  textTransform: 'uppercase' as const,
  color:         'var(--mid)',
  marginBottom:  6,
  display:       'block',
}

const cardStyle: React.CSSProperties = {
  backgroundColor: 'var(--white)',
  borderRadius:    'var(--radius-md)',
  boxShadow:       'var(--shadow-card)',
  padding:         '24px 28px',
}

// ── Configure tab sub-components ──────────────────────────────────────────────

function StatBox({ value, caption }: { value: string; caption: string; accent?: string }) {
  return (
    <div style={{ borderLeft: '3px solid var(--gold)', paddingLeft: 16, flex: 1 }}>
      <div style={{ fontFamily: 'var(--fd)', fontSize: 28, fontWeight: 700, color: 'var(--primary)' }}>{value}</div>
      <div style={{ fontFamily: 'var(--fb)', fontSize: 10, letterSpacing: '1.5px', textTransform: 'uppercase', color: 'var(--mid)' }}>{caption}</div>
    </div>
  )
}

function RetentionBadge({ retained, override }: { retained: boolean; override: boolean }) {
  const base: React.CSSProperties = {
    fontFamily:    'var(--fb)',
    fontSize:      9,
    letterSpacing: '1.5px',
    textTransform: 'uppercase' as const,
    padding:       '3px 10px',
    borderRadius:  'var(--radius-pill)',
    fontWeight:    600,
  }
  if (retained) {
    return (
      <span style={{ ...base, backgroundColor: 'rgba(39,185,124,0.12)', color: 'var(--status-green)' }}>
        {override ? 'Retained (Override)' : 'Retained'}
      </span>
    )
  }
  return (
    <span style={{ ...base, backgroundColor: 'rgba(107,114,128,0.1)', color: 'var(--mid)' }}>
      Not Retained
    </span>
  )
}

function EmployeeRow({ emp }: { emp: SimulationEmployee }) {
  return (
    <tr style={{ borderBottom: '1px solid var(--primary-10)' }}>
      <td style={{ padding: '10px 12px', fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--dark)', fontWeight: 500 }}>
        {emp.full_name}
        {emp.is_nexus && (
          <span style={{
            marginLeft: 6, fontFamily: 'var(--fb)', fontSize: 8, letterSpacing: '1.5px',
            textTransform: 'uppercase', color: 'var(--gold)',
            border: '1px solid var(--gold)', borderRadius: 'var(--radius-pill)', padding: '1px 6px',
          }}>Nexus</span>
        )}
      </td>
      <td style={{ padding: '10px 12px', fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)' }}>{emp.department}</td>
      <td style={{ padding: '10px 12px', fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)' }}>{emp.role_title}</td>
      <td style={{ padding: '10px 12px', fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--primary)', textAlign: 'right' }}>
        ${emp.annual_salary.toLocaleString()}
      </td>
      <td style={{ padding: '10px 12px', textAlign: 'center' }}>
        <span style={{ fontFamily: 'var(--fd)', fontSize: 15, fontWeight: 700,
          color: emp.impact_score >= 75 ? 'var(--status-green)' : emp.impact_score >= 50 ? 'var(--gold)' : 'var(--mid)',
        }}>{emp.impact_score.toFixed(0)}</span>
      </td>
      <td style={{ padding: '10px 12px', textAlign: 'center' }}>
        <RetentionBadge retained={emp.retained} override={emp.override} />
      </td>
    </tr>
  )
}

// ── Impact Analysis sub-components ────────────────────────────────────────────

function DeltaCard({ title, before, after, format, accent, positiveDirection }: {
  title:             string
  before:            number
  after:             number
  format:            (n: number) => string
  accent:            string
  positiveDirection: 'up' | 'down' | 'neutral'
}) {
  const delta    = after - before
  const deltaPct = before !== 0 ? (delta / Math.abs(before)) * 100 : 0
  const isUp     = delta >= 0

  const deltaColor = positiveDirection === 'neutral'
    ? 'var(--mid)'
    : (positiveDirection === 'up') === isUp
      ? 'var(--status-green)'
      : 'var(--status-orange)'

  return (
    <div style={{ ...cardStyle, flex: 1, borderTop: '3px solid var(--gold)' }}>
      <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--mid)', marginBottom: 18 }}>{title}</div>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 20, marginBottom: 14 }}>
        <div>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 9, color: 'var(--mid)', marginBottom: 4, letterSpacing: '1px', textTransform: 'uppercase' }}>Before</div>
          <div style={{ fontFamily: 'var(--fd)', fontSize: 20, fontWeight: 600, color: 'rgba(0,51,102,0.4)' }}>{format(before)}</div>
        </div>
        <div style={{ fontFamily: 'var(--fb)', fontSize: 16, color: 'var(--mid)', paddingBottom: 2 }}>→</div>
        <div>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 9, color: 'var(--mid)', marginBottom: 4, letterSpacing: '1px', textTransform: 'uppercase' }}>After</div>
          <div style={{ fontFamily: 'var(--fd)', fontSize: 24, fontWeight: 700, color: accent }}>{format(after)}</div>
        </div>
      </div>
      <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: deltaColor, fontWeight: 600 }}>
        {isUp ? '▲' : '▼'} {Math.abs(deltaPct).toFixed(1)}%
      </div>
    </div>
  )
}

function DeptRetentionChart({ employees }: { employees: SimulationEmployee[] }) {
  const depts: Record<string, { retained: number; total: number }> = {}
  for (const e of employees) {
    if (!depts[e.department]) depts[e.department] = { retained: 0, total: 0 }
    depts[e.department].total += 1
    if (e.retained) depts[e.department].retained += 1
  }

  const rows = Object.entries(depts)
    .map(([dept, d]) => ({ dept, ...d, pct: d.total > 0 ? (d.retained / d.total) * 100 : 0 }))
    .sort((a, b) => b.pct - a.pct)

  return (
    <div style={cardStyle}>
      <div style={{ ...sectionTitle, fontSize: 16, marginBottom: 6 }}>Retention by Department</div>
      <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', marginBottom: 22 }}>Headcount retained vs not retained per department</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 13 }}>
        {rows.map(({ dept, retained, total, pct }) => (
          <div key={dept}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
              <span style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--dark)', fontWeight: 500 }}>{dept}</span>
              <span style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)' }}>
                {retained}/{total} &nbsp;·&nbsp; {pct.toFixed(0)}%
              </span>
            </div>
            <div style={{ display: 'flex', borderRadius: 4, overflow: 'hidden', height: 8 }}>
              <div style={{ width: `${pct}%`, backgroundColor: 'var(--status-green)', opacity: 0.85, transition: 'width 0.5s ease' }} />
              <div style={{ flex: 1, backgroundColor: 'rgba(107,114,128,0.15)' }} />
            </div>
          </div>
        ))}
      </div>
      <div style={{ display: 'flex', gap: 20, marginTop: 20 }}>
        {[
          { color: 'var(--status-green)', label: 'Retained' },
          { color: 'rgba(107,114,128,0.25)', label: 'Not Retained in Simulation' },
        ].map(({ color, label }) => (
          <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{ width: 10, height: 10, borderRadius: 2, backgroundColor: color }} />
            <span style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'var(--mid)' }}>{label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function ImpactShift({ employees }: { employees: SimulationEmployee[] }) {
  const ranges: Array<[number, number]> = [[0, 20], [20, 40], [40, 60], [60, 80], [80, 100]]
  const labels = ['0–20', '20–40', '40–60', '60–80', '80–100']

  const allCounts = ranges.map(([lo, hi]) =>
    employees.filter(e => e.impact_score >= lo && (hi === 100 ? e.impact_score <= hi : e.impact_score < hi)).length
  )
  const retCounts = ranges.map(([lo, hi]) =>
    employees.filter(e => e.retained && e.impact_score >= lo && (hi === 100 ? e.impact_score <= hi : e.impact_score < hi)).length
  )

  const maxCount = Math.max(...allCounts, 1)
  const W = 340
  const H = 140
  const groupW = W / 5
  const bw = groupW * 0.32

  return (
    <div style={cardStyle}>
      <div style={{ ...sectionTitle, fontSize: 16, marginBottom: 4 }}>Impact Score Distribution</div>
      <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', marginBottom: 20 }}>
        All employees vs retained employees by impact bracket
      </div>
      <svg width="100%" viewBox={`0 0 ${W} ${H + 28}`} style={{ overflow: 'visible' }}>
        {/* Horizontal guide lines */}
        {[0.25, 0.5, 0.75, 1.0].map(f => (
          <line key={f} x1={0} y1={H - f * H} x2={W} y2={H - f * H}
            stroke="var(--primary-10)" strokeWidth={1} strokeDasharray={f === 1 ? undefined : '3 3'} />
        ))}
        {/* Bars */}
        {labels.map((lbl, i) => {
          const cx = i * groupW + groupW / 2
          const aH = (allCounts[i] / maxCount) * H
          const rH = (retCounts[i] / maxCount) * H
          return (
            <g key={lbl}>
              <rect x={cx - bw - 2} y={H - aH} width={bw} height={aH}
                fill="var(--primary)" opacity={0.18} rx={2} />
              <rect x={cx + 2} y={H - rH} width={bw} height={rH}
                fill="var(--status-green)" opacity={0.85} rx={2} />
              {retCounts[i] > 0 && (
                <text x={cx + 2 + bw / 2} y={H - rH - 5} textAnchor="middle"
                  fontSize={8} fontFamily="var(--fb)" fill="var(--status-green)">{retCounts[i]}</text>
              )}
              <text x={cx} y={H + 16} textAnchor="middle"
                fontSize={8} fontFamily="var(--fb)" fill="#6b7280">{lbl}</text>
            </g>
          )
        })}
        <line x1={0} y1={H} x2={W} y2={H} stroke="#e5e7eb" strokeWidth={1} />
      </svg>
      <div style={{ display: 'flex', gap: 20, marginTop: 4 }}>
        {[
          { color: 'rgba(0,51,102,0.2)', label: 'All Employees' },
          { color: 'var(--status-green)', label: 'Retained' },
        ].map(({ color, label }) => (
          <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{ width: 10, height: 10, borderRadius: 2, backgroundColor: color }} />
            <span style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'var(--mid)' }}>{label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function PayrollDonut({ retainedCost, atRiskCost }: { retainedCost: number; atRiskCost: number }) {
  const total         = retainedCost + atRiskCost
  const retainedFrac  = total > 0 ? retainedCost / total : 0
  const R             = 52
  const cx            = 80
  const cy            = 80
  const circ          = 2 * Math.PI * R
  const retainedArc   = retainedFrac * circ

  return (
    <div style={cardStyle}>
      <div style={{ ...sectionTitle, fontSize: 16, marginBottom: 4 }}>Payroll Allocation</div>
      <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', marginBottom: 16 }}>
        Retained vs not-retained payroll split
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
        <svg width={160} height={160} viewBox="0 0 160 160">
          <circle cx={cx} cy={cy} r={R} fill="none" stroke="rgba(107,114,128,0.12)" strokeWidth={22} />
          <circle cx={cx} cy={cy} r={R} fill="none" stroke="var(--status-green)" strokeWidth={22}
            strokeDasharray={`${retainedArc} ${circ}`}
            strokeDashoffset={circ / 4}
            strokeLinecap="butt"
          />
          <text x={cx} y={cy - 7} textAnchor="middle" fontSize={18} fontWeight={700}
            fontFamily="var(--fd)" fill="var(--primary)">{(retainedFrac * 100).toFixed(0)}%</text>
          <text x={cx} y={cy + 10} textAnchor="middle" fontSize={8}
            fontFamily="var(--fb)" fill="#6b7280">retained</text>
        </svg>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          <div>
            <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: 'var(--status-green)', marginBottom: 4 }}>Retained Payroll</div>
            <div style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 700, color: 'var(--primary)' }}>
              ${(retainedCost / 1e6).toFixed(2)}M
            </div>
          </div>
          <div>
            <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: 'var(--mid)', marginBottom: 4 }}>Not Retained</div>
            <div style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 700, color: 'var(--mid)' }}>
              ${(atRiskCost / 1e6).toFixed(2)}M
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function NexusProtection({ employees }: { employees: SimulationEmployee[] }) {
  const nexusAll      = employees.filter(e => e.is_nexus)
  const nexusRetained = nexusAll.filter(e => e.retained)
  const pct           = nexusAll.length > 0 ? (nexusRetained.length / nexusAll.length) * 100 : 100
  const barColor      = pct >= 80 ? 'var(--status-green)' : pct >= 50 ? 'var(--gold)' : 'var(--status-red)'

  const displayList = nexusAll.slice(0, 8)
  const remaining   = nexusAll.length - displayList.length

  return (
    <div style={cardStyle}>
      <div style={{ ...sectionTitle, fontSize: 16, marginBottom: 4 }}>Nexus Employee Protection</div>
      <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', marginBottom: 18 }}>
        Organizational connectors whose departure would fragment the collaboration network
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 14 }}>
        <span style={{ fontFamily: 'var(--fd)', fontSize: 44, fontWeight: 700, color: barColor, lineHeight: 1 }}>{nexusRetained.length}</span>
        <span style={{ fontFamily: 'var(--fd)', fontSize: 22, color: 'var(--mid)' }}>/ {nexusAll.length}</span>
        <span style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)' }}>retained</span>
      </div>
      <div style={{ height: 8, backgroundColor: 'rgba(107,114,128,0.15)', borderRadius: 4, overflow: 'hidden', marginBottom: 10 }}>
        <div style={{ height: '100%', width: `${pct}%`, backgroundColor: barColor, borderRadius: 4 }} />
      </div>
      <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: barColor, fontWeight: 600, marginBottom: 20 }}>
        {pct.toFixed(0)}% of nexus employees protected
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {displayList.map(e => (
          <div key={e.employee_id} style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '7px 12px', borderRadius: 'var(--radius-sm)',
            backgroundColor: e.retained ? 'rgba(39,185,124,0.06)' : 'rgba(107,114,128,0.05)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{
                width: 28, height: 28, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
                backgroundColor: e.retained ? 'rgba(39,185,124,0.15)' : 'rgba(107,114,128,0.12)',
                fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 700,
                color: e.retained ? 'var(--status-green)' : 'var(--mid)',
                flexShrink: 0,
              }}>
                {e.full_name.split(' ').map(n => n[0]).join('').slice(0, 2)}
              </div>
              <div>
                <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--dark)', fontWeight: 500 }}>{e.full_name}</div>
                <div style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'var(--mid)' }}>{e.department}</div>
              </div>
            </div>
            <RetentionBadge retained={e.retained} override={e.override} />
          </div>
        ))}
        {remaining > 0 && (
          <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', textAlign: 'center', paddingTop: 6 }}>
            + {remaining} more nexus employees
          </div>
        )}
      </div>
    </div>
  )
}

function BudgetGauge({ budgetPct, usedPct }: { budgetPct: number; usedPct: number }) {
  const gaugeColor = usedPct > 98 ? 'var(--status-red)' : usedPct > 85 ? 'var(--gold)' : 'var(--status-green)'
  const clamped    = Math.min(usedPct, 100)

  return (
    <div style={cardStyle}>
      <div style={{ ...sectionTitle, fontSize: 16, marginBottom: 4 }}>Budget Utilization</div>
      <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', marginBottom: 24 }}>
        Simulation target: {budgetPct}% of total payroll budget
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 14 }}>
        <span style={{ fontFamily: 'var(--fd)', fontSize: 44, fontWeight: 700, color: gaugeColor, lineHeight: 1 }}>{usedPct.toFixed(1)}%</span>
        <span style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)' }}>of available budget used</span>
      </div>
      <div style={{ position: 'relative', height: 16, backgroundColor: 'rgba(107,114,128,0.12)', borderRadius: 8, overflow: 'hidden', marginBottom: 10 }}>
        <div style={{
          height: '100%', width: `${clamped}%`,
          backgroundColor: gaugeColor,
          borderRadius: 8,
          transition: 'width 0.6s ease',
        }} />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 20 }}>
        <span style={{ fontFamily: 'var(--fb)', fontSize: 9, color: 'var(--mid)' }}>0%</span>
        <span style={{ fontFamily: 'var(--fb)', fontSize: 9, color: 'var(--mid)' }}>100%</span>
      </div>

      {/* Efficiency note */}
      <div style={{
        backgroundColor: usedPct < 80 ? 'rgba(39,185,124,0.06)' : usedPct < 95 ? 'rgba(240,180,41,0.08)' : 'rgba(224,52,72,0.06)',
        borderRadius:    'var(--radius-sm)',
        padding:         '10px 14px',
      }}>
        <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--dark)' }}>
          {usedPct < 80
            ? 'Budget headroom available — consider retaining additional talent.'
            : usedPct < 98
              ? 'Budget well-utilized with minimal surplus.'
              : 'Near-full budget consumption — verify constraints allow flexibility.'}
        </div>
      </div>
    </div>
  )
}

// ── Impact Dashboard ──────────────────────────────────────────────────────────

function ImpactDashboard({ result, budgetPct }: { result: SimulationResult; budgetPct: number }) {
  const all      = result.employees
  const retained = all.filter(e => e.retained)

  const totalCostBefore   = all.reduce((s, e) => s + e.annual_salary, 0)
  const totalImpactBefore = all.reduce((s, e) => s + e.impact_score, 0)
  const avgImpactBefore   = all.length > 0 ? totalImpactBefore / all.length : 0
  const avgImpactAfter    = retained.length > 0
    ? retained.reduce((s, e) => s + e.impact_score, 0) / retained.length
    : 0

  return (
    <div style={{ maxWidth: 'var(--max-width-content)', margin: '0 auto', padding: '40px 48px' }}>

      {/* Before / After delta cards */}
      <div style={{ display: 'flex', gap: 20, marginBottom: 24 }}>
        <DeltaCard
          title="Headcount"
          before={all.length}
          after={result.retained_count}
          format={n => String(Math.round(n))}
          accent="var(--primary)"
          positiveDirection="neutral"
        />
        <DeltaCard
          title="Total Payroll"
          before={totalCostBefore}
          after={result.total_retained_cost}
          format={n => `$${(n / 1e6).toFixed(2)}M`}
          accent="var(--gold)"
          positiveDirection="down"
        />
        <DeltaCard
          title="Avg Impact Score"
          before={avgImpactBefore}
          after={avgImpactAfter}
          format={n => n.toFixed(1)}
          accent="var(--status-green)"
          positiveDirection="up"
        />
        <DeltaCard
          title="Total Impact"
          before={totalImpactBefore}
          after={result.total_impact}
          format={n => n.toFixed(0)}
          accent="var(--primary)"
          positiveDirection="neutral"
        />
      </div>

      {/* Row 2: Dept breakdown + Impact shift */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 24 }}>
        <DeptRetentionChart employees={all} />
        <ImpactShift employees={all} />
      </div>

      {/* Row 3: Payroll donut + Nexus + Budget gauge */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.6fr 1fr', gap: 20 }}>
        <PayrollDonut retainedCost={result.total_retained_cost} atRiskCost={result.total_at_risk_cost} />
        <NexusProtection employees={all} />
        <BudgetGauge budgetPct={budgetPct} usedPct={result.budget_used_pct} />
      </div>

    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function SimulationPage() {
  const { scenario, size } = useDemoStore()

  const [budgetPct,   setBudgetPct]   = useState(80)
  const [leadership,  setLeadership]  = useState(true)
  const [skills,      setSkills]      = useState(true)
  const [forceRetain, setForceRetain] = useState('')
  const [exclude,     setExclude]     = useState('')

  const [result,  setResult]  = useState<SimulationResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<SimTab>('configure')

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const runSimulation = useCallback(async (pct: number) => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.simulation.run({
        scenario,
        size,
        budget_pct:            pct,
        force_retain:          forceRetain.split(',').map(s => s.trim()).filter(Boolean),
        exclude:               exclude.split(',').map(s => s.trim()).filter(Boolean),
        leadership_constraint: leadership,
        skills_constraint:     skills,
      })
      setResult(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Simulation failed')
    } finally {
      setLoading(false)
    }
  }, [scenario, size, forceRetain, exclude, leadership, skills])

  const handleSlider = (val: number) => {
    setBudgetPct(val)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => runSimulation(val), 500)
  }

  // ── Tab button style ───────────────────────────────────────────────────────

  const tabBtn = (tab: SimTab, label: string, hasResult: boolean): React.ReactElement => {
    const active = activeTab === tab
    return (
      <button
        key={tab}
        onClick={() => setActiveTab(tab)}
        style={{
          background:    'transparent',
          border:        'none',
          borderBottom:  active ? '2px solid var(--gold)' : '2px solid transparent',
          color:         active ? '#fff' : 'rgba(255,255,255,0.5)',
          fontFamily:    'var(--fb)',
          fontSize:      10,
          letterSpacing: '2px',
          textTransform: 'uppercase',
          fontWeight:    active ? 700 : 400,
          padding:       '10px 0',
          cursor:        'pointer',
          marginRight:   28,
          display:       'inline-flex',
          alignItems:    'center',
          gap:           6,
        }}
      >
        {label}
        {tab === 'impact' && hasResult && !active && (
          <span style={{
            width: 6, height: 6, borderRadius: '50%',
            backgroundColor: 'var(--gold)', display: 'inline-block',
          }} />
        )}
      </button>
    )
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div>
      {/* Hero */}
      <div style={{ background: 'var(--primary)', paddingTop: 40, paddingBottom: 0, paddingLeft: 48, paddingRight: 48 }}>
        <div style={{ maxWidth: 'var(--max-width-content)', margin: '0 auto' }}>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '3px', textTransform: 'uppercase', color: 'var(--gold)', marginBottom: 10 }}>
            Budget Simulation Engine
          </div>
          <h1 style={{ fontFamily: 'var(--fd)', fontSize: 38, fontWeight: 600, fontStyle: 'italic', color: '#fff', margin: '0 0 10px' }}>
            Optimization Simulator
          </h1>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: 'rgba(255,255,255,0.55)', margin: '0 0 28px', maxWidth: 520 }}>
            Adjust budget targets and constraints to see which talent the model recommends retaining. Every decision is yours.
          </p>
          {/* Tabs */}
          <div style={{ borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: 4 }}>
            {tabBtn('configure', 'Configure & Results', result !== null)}
            {tabBtn('impact',    'Impact Analysis',     result !== null)}
          </div>
        </div>
      </div>

      {/* ── Configure tab ─────────────────────────────────────────────────── */}
      {activeTab === 'configure' && (
        <div style={{ maxWidth: 'var(--max-width-content)', margin: '0 auto', padding: '40px 48px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: 32 }}>

            {/* Controls panel */}
            <div style={{
              ...cardStyle,
              height:   'fit-content',
              position: 'sticky',
              top:      68,
            }}>
              <div style={{ ...sectionTitle, fontSize: 16, marginBottom: 24 }}>Simulation Controls</div>

              {/* Budget slider */}
              <div style={{ marginBottom: 24 }}>
                <span style={labelStyle}>Available Budget</span>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                  <span style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)' }}>50%</span>
                  <span style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 700, color: 'var(--primary)' }}>{budgetPct}%</span>
                  <span style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)' }}>120%</span>
                </div>
                <input
                  type="range" min={50} max={120} value={budgetPct}
                  onChange={e => handleSlider(Number(e.target.value))}
                  style={{ width: '100%', accentColor: 'var(--gold)' }}
                />
                <div style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'var(--mid)', marginTop: 4 }}>of current total spend</div>
              </div>

              {/* Constraints */}
              <div style={{ marginBottom: 20 }}>
                <span style={labelStyle}>Constraints</span>
                {[
                  { id: 'leadership', label: 'Leadership coverage',      val: leadership, set: setLeadership },
                  { id: 'skills',     label: 'Critical skills coverage', val: skills,     set: setSkills },
                ].map(({ id, label: lbl, val, set }) => (
                  <label key={id} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10, cursor: 'pointer' }}>
                    <input type="checkbox" checked={val} onChange={e => set(e.target.checked)}
                      style={{ accentColor: 'var(--gold)', width: 15, height: 15 }} />
                    <span style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--dark)' }}>{lbl}</span>
                  </label>
                ))}
              </div>

              {/* Force retain */}
              <div style={{ marginBottom: 16 }}>
                <span style={labelStyle}>Force Retain (IDs, comma-separated)</span>
                <input type="text" value={forceRetain} onChange={e => setForceRetain(e.target.value)}
                  placeholder="e.g. EMP-001, EMP-042"
                  style={{
                    width: '100%', boxSizing: 'border-box',
                    fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--dark)',
                    border: '1px solid var(--primary-10)', borderRadius: 'var(--radius-sm)',
                    padding: '8px 12px', backgroundColor: 'var(--light)', outline: 'none',
                  }}
                />
              </div>

              {/* Exclude */}
              <div style={{ marginBottom: 24 }}>
                <span style={labelStyle}>Exclude from Simulation (IDs)</span>
                <input type="text" value={exclude} onChange={e => setExclude(e.target.value)}
                  placeholder="e.g. EMP-099"
                  style={{
                    width: '100%', boxSizing: 'border-box',
                    fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--dark)',
                    border: '1px solid var(--primary-10)', borderRadius: 'var(--radius-sm)',
                    padding: '8px 12px', backgroundColor: 'var(--light)', outline: 'none',
                  }}
                />
              </div>

              <button
                onClick={() => runSimulation(budgetPct)}
                disabled={loading}
                style={{
                  width: '100%', fontFamily: 'var(--fb)', fontSize: 10, letterSpacing: '2px',
                  textTransform: 'uppercase', fontWeight: 700,
                  backgroundColor: loading ? 'var(--mid)' : 'var(--gold)',
                  color: '#fff', border: 'none', borderRadius: 'var(--radius-sm)',
                  padding: '12px 0', cursor: loading ? 'not-allowed' : 'pointer',
                }}
              >
                {loading ? 'Running…' : 'Run Simulation'}
              </button>
            </div>

            {/* Results */}
            <div>
              {error && (
                <div style={{ backgroundColor: 'rgba(224,52,72,0.08)', border: '1px solid rgba(224,52,72,0.2)', borderRadius: 'var(--radius-md)', padding: 20, marginBottom: 24 }}>
                  <span style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--status-red)' }}>{error}</span>
                </div>
              )}

              {!result && !loading && (
                <div style={{ ...cardStyle, padding: 48, textAlign: 'center' }}>
                  <div style={{ fontFamily: 'var(--fd)', fontSize: 20, color: 'var(--primary)', marginBottom: 8 }}>Set constraints and run the simulation</div>
                  <div style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)' }}>Adjust the budget slider and click Run Simulation to see results.</div>
                </div>
              )}

              {loading && (
                <div style={{ ...cardStyle, padding: 48, textAlign: 'center' }}>
                  <div style={{ fontFamily: 'var(--fd)', fontSize: 20, color: 'var(--primary)' }}>Running optimization…</div>
                </div>
              )}

              {result && !loading && (
                <>
                  {!result.feasible && (
                    <div style={{ backgroundColor: 'rgba(240,112,32,0.08)', border: '1px solid rgba(240,112,32,0.25)', borderRadius: 'var(--radius-md)', padding: '16px 20px', marginBottom: 20 }}>
                      <div style={{ fontFamily: 'var(--fb)', fontSize: 11, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--status-orange)', marginBottom: 4 }}>Infeasible Scenario</div>
                      <div style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--dark)' }}>{result.infeasibility_reason}</div>
                    </div>
                  )}

                  {/* Stats strip */}
                  <div style={{ ...cardStyle, display: 'flex', gap: 28, marginBottom: 20 }}>
                    <StatBox value={String(result.retained_count)}              caption="Retained"          accent="var(--status-green)"  />
                    <StatBox value={String(result.at_risk_count)}               caption="Not Retained"      accent="var(--mid)"           />
                    <StatBox value={`${result.budget_used_pct.toFixed(1)}%`}   caption="Budget Used"       accent="var(--gold)"          />
                    <StatBox value={result.total_impact.toFixed(0)}             caption="Total Impact"      accent="var(--status-purple)" />
                  </div>

                  {/* Cost strip */}
                  <div style={{ ...cardStyle, display: 'flex', gap: 28, marginBottom: 24 }}>
                    <StatBox value={`$${(result.total_retained_cost / 1e6).toFixed(2)}M`} caption="Retained Payroll"     />
                    <StatBox value={`$${(result.total_at_risk_cost  / 1e6).toFixed(2)}M`} caption="Not-Retained Payroll" accent="var(--mid)" />
                  </div>

                  {/* Prompt to view Impact Analysis */}
                  <div style={{
                    backgroundColor: 'rgba(0,51,102,0.04)', border: '1px solid var(--primary-10)',
                    borderRadius: 'var(--radius-sm)', padding: '12px 16px', marginBottom: 20,
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  }}>
                    <span style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)' }}>
                      Simulation complete. View before/after charts in Impact Analysis.
                    </span>
                    <button
                      onClick={() => setActiveTab('impact')}
                      style={{
                        fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '2px', textTransform: 'uppercase',
                        fontWeight: 700, backgroundColor: 'var(--primary)', color: '#fff',
                        border: 'none', borderRadius: 'var(--radius-sm)', padding: '7px 14px', cursor: 'pointer',
                      }}
                    >
                      View Impact Analysis →
                    </button>
                  </div>

                  {/* Employee table */}
                  <div style={{ ...cardStyle, padding: 0, overflow: 'hidden' }}>
                    <div style={{ padding: '20px 24px 0', borderBottom: '1px solid var(--primary-10)' }}>
                      <div style={{ ...sectionTitle, fontSize: 16, marginBottom: 12 }}>Simulation Results</div>
                    </div>
                    <div style={{ overflowX: 'auto' }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                          <tr style={{ backgroundColor: 'var(--light)' }}>
                            {['Name', 'Department', 'Role', 'Annual Salary', 'Impact', 'Status'].map(h => (
                              <th key={h} style={{
                                padding: '10px 12px', fontFamily: 'var(--fb)', fontSize: 9,
                                letterSpacing: '1.5px', textTransform: 'uppercase', color: 'var(--mid)',
                                textAlign: h === 'Annual Salary' ? 'right' : 'left', fontWeight: 600,
                              }}>{h}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {result.employees
                            .slice()
                            .sort((a, b) => (b.retained ? 1 : 0) - (a.retained ? 1 : 0))
                            .map(emp => <EmployeeRow key={emp.employee_id} emp={emp} />)
                          }
                        </tbody>
                      </table>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── Impact Analysis tab ────────────────────────────────────────────── */}
      {activeTab === 'impact' && (
        result
          ? <ImpactDashboard result={result} budgetPct={budgetPct} />
          : (
            <div style={{ maxWidth: 'var(--max-width-content)', margin: '0 auto', padding: '80px 48px', textAlign: 'center' }}>
              <div style={{ ...cardStyle, display: 'inline-block', padding: '48px 64px' }}>
                <div style={{ fontFamily: 'var(--fd)', fontSize: 24, color: 'var(--primary)', marginBottom: 10 }}>
                  No simulation results yet
                </div>
                <div style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)', marginBottom: 24, maxWidth: 360 }}>
                  Run a simulation on the Configure tab to unlock the before/after impact dashboard.
                </div>
                <button
                  onClick={() => setActiveTab('configure')}
                  style={{
                    fontFamily: 'var(--fb)', fontSize: 10, letterSpacing: '2px', textTransform: 'uppercase',
                    fontWeight: 700, backgroundColor: 'var(--gold)', color: '#fff',
                    border: 'none', borderRadius: 'var(--radius-sm)', padding: '12px 24px', cursor: 'pointer',
                  }}
                >
                  Go to Configure
                </button>
              </div>
            </div>
          )
      )}
    </div>
  )
}
