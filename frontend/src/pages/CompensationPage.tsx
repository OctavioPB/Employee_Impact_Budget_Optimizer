import React, { useState, useEffect } from 'react'
import {
  api,
  CompensationData,
  CompensationEmployee,
  DeptEquityRow,
} from '../services/api'
import { useDemoStore } from '../stores/demoStore'

type Tab = 'benchmark' | 'equity' | 'roi'

// ── Helpers ───────────────────────────────────────────────────────────────

function fmtMoney(v: number): string {
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(2)}M`
  if (v >= 1_000)     return `$${(v / 1_000).toFixed(0)}K`
  return `$${v.toFixed(0)}`
}

const TIER_COLOR: Record<string, string> = {
  'Below Market': '#e03448',
  'At Market':    '#27b97c',
  'Above Market': '#003366',
}

// ── Scatter chart: comp_ratio vs salary ──────────────────────────────────

function ScatterChart({ employees }: { employees: CompensationEmployee[] }) {
  const W = 780, H = 320
  const PL = 64, PR = 56, PT = 24, PB = 52
  const CW = W - PL - PR, CH = H - PT - PB

  const salaries = employees.map(e => e.annual_salary)
  const xMin = Math.min(...salaries) * 0.95
  const xMax = Math.max(...salaries) * 1.05
  const yMin = 0.5, yMax = 1.6

  const xS = (v: number) => PL + ((v - xMin) / (xMax - xMin)) * CW
  const yS = (v: number) => PT + CH - ((v - yMin) / (yMax - yMin)) * CH

  const refLines = [0.85, 1.0, 1.15]
  const xTicks   = 5
  const xStep    = (xMax - xMin) / xTicks

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', display: 'block' }}>
      {/* Region shading */}
      <rect x={PL} y={yS(1.15)} width={CW} height={yS(1.0) - yS(1.15)}
        fill="#003366" fillOpacity={0.04} />
      <rect x={PL} y={yS(0.85)} width={CW} height={yS(yMin) - yS(0.85)}
        fill="#e03448" fillOpacity={0.04} />

      {/* Reference lines */}
      {refLines.map(v => (
        <line key={v}
          x1={PL} x2={W - PR}
          y1={yS(v).toFixed(1)} y2={yS(v).toFixed(1)}
          stroke={v === 1.0 ? '#336699' : '#cbd5e0'}
          strokeWidth={v === 1.0 ? 1.5 : 1}
          strokeDasharray={v === 1.0 ? '0' : '4 4'}
        />
      ))}

      {/* Y-axis labels */}
      {refLines.map(v => (
        <text key={`y${v}`}
          x={W - PR + 6} y={yS(v) + 4}
          fontSize={9} fill={v === 1.0 ? '#336699' : '#9ba5b2'}
          fontFamily="Plus Jakarta Sans, sans-serif">
          {v.toFixed(2)}
        </text>
      ))}

      {/* Points */}
      {employees.map((e, i) => (
        <circle key={i}
          cx={xS(e.annual_salary).toFixed(1)}
          cy={yS(Math.min(Math.max(e.comp_ratio, yMin), yMax)).toFixed(1)}
          r={4}
          fill={TIER_COLOR[e.market_tier] ?? '#336699'}
          fillOpacity={0.7}
        />
      ))}

      {/* X ticks */}
      {Array.from({ length: xTicks + 1 }, (_, i) => {
        const v = xMin + i * xStep
        return (
          <g key={i}>
            <line x1={xS(v).toFixed(1)} x2={xS(v).toFixed(1)}
              y1={PT + CH} y2={PT + CH + 4} stroke="#cbd5e0" strokeWidth={1} />
            <text x={xS(v).toFixed(1)} y={PT + CH + 17}
              textAnchor="middle" fontSize={9} fill="#9ba5b2"
              fontFamily="Plus Jakarta Sans, sans-serif">
              {fmtMoney(v)}
            </text>
          </g>
        )
      })}

      {/* Axis labels */}
      <text x={PL + CW / 2} y={H - 4}
        textAnchor="middle" fontSize={9} fill="#6b7280" letterSpacing="1.5"
        fontFamily="Plus Jakarta Sans, sans-serif">
        ANNUAL SALARY
      </text>
      <text x={12} y={PT + CH / 2}
        textAnchor="middle" fontSize={9} fill="#6b7280" letterSpacing="1.5"
        fontFamily="Plus Jakarta Sans, sans-serif"
        transform={`rotate(-90, 12, ${PT + CH / 2})`}>
        COMP RATIO
      </text>

      {/* Legend */}
      {Object.entries(TIER_COLOR).map(([label, color], i) => (
        <g key={label} transform={`translate(${PL + i * 170}, ${H - 6})`}>
          <circle cx={5} cy={-4} r={4} fill={color} fillOpacity={0.8} />
          <text x={13} y={0} fontSize={9} fill="#6b7280"
            fontFamily="Plus Jakarta Sans, sans-serif">
            {label}
          </text>
        </g>
      ))}
    </svg>
  )
}

// ── Pay equity bar chart ──────────────────────────────────────────────────

function EquityChart({ rows }: { rows: DeptEquityRow[] }) {
  const W   = 780
  const rowH = 52
  const H   = rows.length * rowH + 60
  const PL = 136, PR = 120, PT = 20, PB = 32
  const CW = W - PL - PR, CH = H - PT - PB

  const allVals = rows.flatMap(r => [r.group_a_median, r.group_b_median])
  const xMax = Math.max(...allVals) * 1.05
  const xS   = (v: number) => PL + (v / xMax) * CW
  const barH = 14

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', display: 'block' }}>
      {rows.map((row, i) => {
        const yC = PT + i * (CH / rows.length) + (CH / rows.length) / 2
        return (
          <g key={row.department}>
            <text x={PL - 10} y={yC + 3} textAnchor="end"
              fontSize={11} fill="#1c1c2e"
              fontFamily="Plus Jakarta Sans, sans-serif">
              {row.department}
            </text>

            {/* Group A bar */}
            <rect x={PL} y={yC - barH - 2} width={Math.max(xS(row.group_a_median) - PL, 2)} height={barH}
              fill="#003366" fillOpacity={0.85} rx={2} />
            <text x={xS(row.group_a_median) + 6} y={yC - barH / 2 - 2 + 6}
              fontSize={10} fill="#1c1c2e" fontFamily="Plus Jakarta Sans, sans-serif">
              {fmtMoney(row.group_a_median)}
            </text>

            {/* Group B bar */}
            <rect x={PL} y={yC + 2} width={Math.max(xS(row.group_b_median) - PL, 2)} height={barH}
              fill="#c8982a" fillOpacity={0.85} rx={2} />
            <text x={xS(row.group_b_median) + 6} y={yC + 2 + barH / 2 + 4}
              fontSize={10} fill="#6b7280" fontFamily="Plus Jakarta Sans, sans-serif">
              {fmtMoney(row.group_b_median)}
              {row.raw_gap_pct > 0
                ? `  −${row.raw_gap_pct.toFixed(1)}%`
                : ''}
            </text>
          </g>
        )
      })}

      {/* Legend */}
      <rect x={PL} y={H - PB + 4} width={10} height={8} fill="#003366" fillOpacity={0.85} rx={2} />
      <text x={PL + 14} y={H - PB + 12} fontSize={9} fill="#6b7280"
        fontFamily="Plus Jakarta Sans, sans-serif">
        Group A — higher-paid cohort
      </text>
      <rect x={PL + 200} y={H - PB + 4} width={10} height={8} fill="#c8982a" fillOpacity={0.85} rx={2} />
      <text x={PL + 214} y={H - PB + 12} fontSize={9} fill="#6b7280"
        fontFamily="Plus Jakarta Sans, sans-serif">
        Group B — lower-paid cohort
      </text>
    </svg>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────

export default function CompensationPage() {
  const { scenario, size, enabled: demo } = useDemoStore()

  const [data,       setData]       = useState<CompensationData | null>(null)
  const [loading,    setLoading]    = useState(true)
  const [error,      setError]      = useState<string | null>(null)
  const [tab,        setTab]        = useState<Tab>('benchmark')
  const [search,     setSearch]     = useState('')
  const [tierFilter, setTierFilter] = useState('All')

  useEffect(() => {
    setLoading(true)
    api.compensation.data(scenario, size, demo)
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [scenario, size, demo])

  const card: React.CSSProperties = {
    backgroundColor: 'var(--white)',
    border:          '1px solid var(--primary-10)',
    borderRadius:    'var(--radius-lg)',
    boxShadow:       'var(--shadow-card)',
    padding:         '24px 28px',
  }

  const tabBtn = (active: boolean): React.CSSProperties => ({
    background:    active ? 'var(--primary)' : 'transparent',
    border:        active ? 'none' : '1px solid var(--primary-30)',
    borderRadius:  'var(--radius-sm)',
    color:         active ? '#fff' : 'var(--primary-60)',
    cursor:        'pointer',
    fontFamily:    'var(--fb)',
    fontSize:      11,
    fontWeight:    600,
    letterSpacing: '1px',
    padding:       '7px 18px',
    transition:    'all 0.15s',
  })

  const thStyle: React.CSSProperties = {
    fontFamily:    'var(--fb)', fontSize: 9, letterSpacing: '1.5px',
    textTransform: 'uppercase', color: 'var(--mid)',
    padding:       '9px 12px', textAlign: 'left', fontWeight: 600,
  }

  if (loading) return (
    <div style={{ padding: 64, textAlign: 'center', fontFamily: 'var(--fb)', color: 'var(--mid)' }}>
      Loading compensation data…
    </div>
  )
  if (error) return (
    <div style={{ padding: 64, textAlign: 'center', fontFamily: 'var(--fb)', color: 'var(--status-red)' }}>
      {error}
    </div>
  )
  if (!data) return null

  const s = data.summary

  const TIERS = ['All', 'Below Market', 'At Market', 'Above Market']
  const filteredEmp = data.employees
    .filter(e => tierFilter === 'All' || e.market_tier === tierFilter)
    .filter(e =>
      search === '' ||
      e.full_name.toLowerCase().includes(search.toLowerCase()) ||
      e.department.toLowerCase().includes(search.toLowerCase())
    )

  const tabs: { id: Tab; label: string }[] = [
    { id: 'benchmark', label: 'Market Benchmarking' },
    { id: 'equity',    label: 'Pay Equity'          },
    { id: 'roi',       label: 'Retention ROI'       },
  ]

  const heroKpis = [
    { label: 'Median Comp Ratio', value: s.median_comp_ratio.toFixed(2), note: s.median_comp_ratio < 0.92 ? 'Below market avg' : 'Market-aligned' },
    { label: 'Below Market',      value: `${s.pct_below_market}%`,       note: `${Math.round(s.pct_below_market * s.total_employees / 100)} employees` },
    { label: 'Avg Pay Gap',       value: `${s.avg_equity_gap_pct.toFixed(1)}%`, note: 'Raw intra-cohort disparity' },
    { label: 'High-ROI Fixes',    value: String(s.high_roi_candidates),  note: 'Correction ROI ≥ 2×' },
  ]

  return (
    <div>
      {/* ── Hero ── */}
      <div style={{ background: 'var(--primary)', padding: '48px 48px' }}>
        <div style={{ maxWidth: 'var(--max-width-content)', margin: '0 auto' }}>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '3px', textTransform: 'uppercase', color: 'var(--gold)', marginBottom: 10 }}>
            Compensation Intelligence
          </div>
          <h1 style={{ fontFamily: 'var(--fd)', fontSize: 38, fontWeight: 600, fontStyle: 'italic', color: '#fff', margin: '0 0 10px' }}>
            Pay Equity &amp; Market Benchmarking
          </h1>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: 'rgba(255,255,255,0.55)', margin: 0 }}>
            Market positioning, pay disparity signals, and retention ROI for compensation corrections.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginTop: 32 }}>
            {heroKpis.map(k => (
              <div key={k.label} style={{
                backgroundColor: 'rgba(255,255,255,0.07)',
                border:          '1px solid rgba(255,255,255,0.1)',
                borderRadius:    'var(--radius-md)',
                padding:         '18px 20px',
              }}>
                <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--gold-light)', marginBottom: 6 }}>
                  {k.label}
                </div>
                <div style={{ fontFamily: 'var(--fd)', fontSize: 28, fontWeight: 400, color: '#fff', lineHeight: 1.1 }}>
                  {k.value}
                </div>
                <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'rgba(255,255,255,0.4)', marginTop: 4 }}>
                  {k.note}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Body ── */}
      <div style={{ maxWidth: 'var(--max-width-content)', margin: '0 auto', padding: '40px 48px' }}>

        {/* Tab bar */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 28 }}>
          {tabs.map(t => (
            <button key={t.id} style={tabBtn(tab === t.id)} onClick={() => setTab(t.id)}>
              {t.label}
            </button>
          ))}
        </div>

        {/* ── Tab: Market Benchmarking ── */}
        {tab === 'benchmark' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>

            {/* Filters */}
            <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
              <input
                placeholder="Search name or department…"
                value={search}
                onChange={e => setSearch(e.target.value)}
                style={{
                  flex: 1, minWidth: 220, maxWidth: 300,
                  border: '1px solid var(--primary-30)', borderRadius: 'var(--radius-sm)',
                  fontFamily: 'var(--fb)', fontSize: 13, padding: '7px 12px',
                  outline: 'none', color: 'var(--dark)', background: 'var(--white)',
                }}
              />
              {TIERS.map(t => {
                const isActive = tierFilter === t
                const bgColor = isActive
                  ? (t === 'Below Market' ? '#e03448' : t === 'Above Market' ? '#003366' : t === 'At Market' ? '#27b97c' : 'var(--primary)')
                  : 'transparent'
                return (
                  <button key={t}
                    onClick={() => setTierFilter(t)}
                    style={{
                      background:    bgColor,
                      border:        isActive ? 'none' : '1px solid var(--primary-30)',
                      borderRadius:  'var(--radius-sm)',
                      color:         isActive ? '#fff' : 'var(--primary-60)',
                      cursor:        'pointer',
                      fontFamily:    'var(--fb)',
                      fontSize:      10,
                      fontWeight:    600,
                      letterSpacing: '0.5px',
                      padding:       '5px 14px',
                    }}>
                    {t}
                  </button>
                )
              })}
            </div>

            {/* Scatter chart */}
            <div style={card}>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--gold)', marginBottom: 14 }}>
                Comp Ratio vs. Annual Salary
              </div>
              <ScatterChart employees={
                tierFilter === 'All'
                  ? data.employees
                  : data.employees.filter(e => e.market_tier === tierFilter)
              } />
            </div>

            {/* Employee table */}
            <div style={card}>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--mid)', marginBottom: 14 }}>
                {filteredEmp.length} employees
              </div>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ backgroundColor: 'var(--primary-10)' }}>
                      {['Name', 'Department', 'Role', 'Salary', 'Market', 'Ratio', 'Tier'].map(h => (
                        <th key={h} style={thStyle}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {filteredEmp.slice(0, 60).map((e, i) => (
                      <tr key={e.employee_id}
                        style={{ backgroundColor: i % 2 === 0 ? 'var(--white)' : 'var(--primary-10)' }}>
                        <td style={{ padding: '8px 12px', fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--dark)' }}>{e.full_name}</td>
                        <td style={{ padding: '8px 12px', fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)' }}>{e.department}</td>
                        <td style={{ padding: '8px 12px', fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)' }}>{e.role_title}</td>
                        <td style={{ padding: '8px 12px', fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--dark)', whiteSpace: 'nowrap' }}>{fmtMoney(e.annual_salary)}</td>
                        <td style={{ padding: '8px 12px', fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)', whiteSpace: 'nowrap' }}>{fmtMoney(e.market_median)}</td>
                        <td style={{ padding: '8px 12px', fontFamily: 'var(--fb)', fontSize: 13, fontWeight: 700, color: TIER_COLOR[e.market_tier] }}>
                          {e.comp_ratio.toFixed(2)}
                        </td>
                        <td style={{ padding: '8px 12px' }}>
                          <span style={{
                            fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1px',
                            textTransform: 'uppercase', fontWeight: 700,
                            padding: '3px 10px', borderRadius: 'var(--radius-pill)',
                            backgroundColor: `${TIER_COLOR[e.market_tier]}1a`,
                            color: TIER_COLOR[e.market_tier],
                          }}>{e.market_tier}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ── Tab: Pay Equity ── */}
        {tab === 'equity' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>

            <div style={{
              ...card,
              backgroundColor: 'rgba(0,51,102,0.04)',
              border: '1px solid var(--primary-30)',
            }}>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--primary-60)', lineHeight: 1.7 }}>
                <strong>Methodology:</strong> Within each (department, seniority) cohort, employees are split by salary rank — top 50% earners form Group A, bottom 50% form Group B.
                The adjusted gap uses OLS regression on seniority rank within each department to isolate pay differences not explained by role level.
                Statistical significance tested via Welch's t-test (α = 0.05).
              </div>
            </div>

            <div style={card}>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--gold)', marginBottom: 16 }}>
                Median Pay by Department &amp; Group
              </div>
              <EquityChart rows={data.dept_equity} />
            </div>

            <div style={card}>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--mid)', marginBottom: 14 }}>
                Department detail
              </div>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ backgroundColor: 'var(--primary-10)' }}>
                      {['Department', 'n', 'Group A Median', 'Group B Median', 'Raw Gap', 'Adj. Gap', 'p-value', 'Significant'].map(h => (
                        <th key={h} style={thStyle}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.dept_equity.map((row, i) => (
                      <tr key={row.department}
                        style={{ backgroundColor: i % 2 === 0 ? 'var(--white)' : 'var(--primary-10)' }}>
                        <td style={{ padding: '8px 12px', fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--dark)', fontWeight: 600 }}>{row.department}</td>
                        <td style={{ padding: '8px 12px', fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)' }}>{row.headcount}</td>
                        <td style={{ padding: '8px 12px', fontFamily: 'var(--fb)', fontSize: 13, color: '#003366', fontWeight: 700 }}>{fmtMoney(row.group_a_median)}</td>
                        <td style={{ padding: '8px 12px', fontFamily: 'var(--fb)', fontSize: 13, color: '#c8982a', fontWeight: 700 }}>{fmtMoney(row.group_b_median)}</td>
                        <td style={{ padding: '8px 12px', fontFamily: 'var(--fb)', fontSize: 13, fontWeight: 700, color: row.raw_gap_pct > 10 ? 'var(--status-red)' : 'var(--dark)' }}>
                          {row.raw_gap_pct > 0 ? `${row.raw_gap_pct.toFixed(1)}%` : '—'}
                        </td>
                        <td style={{ padding: '8px 12px', fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)' }}>
                          {row.adjusted_gap_pct.toFixed(1)}%
                        </td>
                        <td style={{ padding: '8px 12px', fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)' }}>{row.p_value.toFixed(3)}</td>
                        <td style={{ padding: '8px 12px' }}>
                          {row.significant ? (
                            <span style={{
                              fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1px', fontWeight: 700,
                              padding: '3px 10px', borderRadius: 'var(--radius-pill)',
                              backgroundColor: 'rgba(224,52,72,0.1)', color: '#e03448',
                            }}>YES</span>
                          ) : (
                            <span style={{
                              fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1px', fontWeight: 700,
                              padding: '3px 10px', borderRadius: 'var(--radius-pill)',
                              backgroundColor: 'rgba(39,185,124,0.1)', color: '#27b97c',
                            }}>No</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ── Tab: Retention ROI ── */}
        {tab === 'roi' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>

            <div style={{
              ...card,
              backgroundColor: 'rgba(39,185,124,0.06)',
              border: '1px solid rgba(39,185,124,0.2)',
            }}>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: '#0d5c3a', lineHeight: 1.7 }}>
                <strong>How to read this:</strong> ROI = estimated replacement cost ÷ annual correction cost.
                A ROI of 3.0× means every $1 spent bringing this employee to market rate saves $3 in potential replacement costs.
                Replacement cost is estimated at 50% of annual salary (industry benchmark for professional roles).
                Only employees below 90% of market median are included.
              </div>
            </div>

            {data.retention_roi.length === 0 ? (
              <div style={{ ...card, textAlign: 'center', color: 'var(--status-green)', fontFamily: 'var(--fb)', fontSize: 14, padding: 48 }}>
                All employees are at or above 90% of market median.
              </div>
            ) : (
              <div style={card}>
                <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--mid)', marginBottom: 14 }}>
                  {data.retention_roi.length} employees below 90% market rate — ranked by correction ROI
                </div>
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{ backgroundColor: 'var(--primary-10)' }}>
                        {['Name', 'Dept', 'Role', 'Current', 'Market', 'Ratio', 'Correction/yr', 'Replacement Est.', 'ROI'].map(h => (
                          <th key={h} style={thStyle}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {data.retention_roi.map((row, i) => {
                        const roiColor = row.roi >= 3 ? '#27b97c' : row.roi >= 2 ? '#c8982a' : 'var(--mid)'
                        return (
                          <tr key={row.employee_id}
                            style={{ backgroundColor: i % 2 === 0 ? 'var(--white)' : 'var(--primary-10)' }}>
                            <td style={{ padding: '8px 12px', fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--dark)' }}>{row.full_name}</td>
                            <td style={{ padding: '8px 12px', fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)' }}>{row.department}</td>
                            <td style={{ padding: '8px 12px', fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)' }}>{row.role_title}</td>
                            <td style={{ padding: '8px 12px', fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--dark)', whiteSpace: 'nowrap' }}>{fmtMoney(row.annual_salary)}</td>
                            <td style={{ padding: '8px 12px', fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)', whiteSpace: 'nowrap' }}>{fmtMoney(row.market_median)}</td>
                            <td style={{ padding: '8px 12px', fontFamily: 'var(--fb)', fontSize: 13, fontWeight: 700, color: '#e03448' }}>
                              {row.comp_ratio.toFixed(2)}
                            </td>
                            <td style={{ padding: '8px 12px', fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)', whiteSpace: 'nowrap' }}>{fmtMoney(row.correction_cost)}</td>
                            <td style={{ padding: '8px 12px', fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)', whiteSpace: 'nowrap' }}>{fmtMoney(row.replacement_cost)}</td>
                            <td style={{ padding: '8px 12px' }}>
                              <span style={{ fontFamily: 'var(--fd)', fontSize: 17, fontWeight: 400, color: roiColor }}>
                                {row.roi.toFixed(1)}×
                              </span>
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
