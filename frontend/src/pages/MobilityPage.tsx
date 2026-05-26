import React, { useState, useEffect, useMemo } from 'react'
import {
  api,
  MobilityData,
  CareerSuggestion,
  SuccessionRow,
  StagnationHeatCell,
} from '../services/api'
import { useDemoStore } from '../stores/demoStore'

type Tab = 'paths' | 'stagnation' | 'succession'

// ── Helpers ───────────────────────────────────────────────────────────────

function fmtMoney(v: number): string {
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(2)}M`
  if (v >= 1_000)     return `$${(v / 1_000).toFixed(0)}K`
  return `$${v.toFixed(0)}`
}

function fmtTenure(days: number): string {
  const yrs = Math.floor(days / 365)
  const mos = Math.floor((days % 365) / 30)
  if (yrs > 0) return `${yrs}y ${mos}m`
  return `${mos}m`
}

const SEN_ORDER = ['junior', 'mid', 'senior', 'lead', 'director', 'exec']

function stagColor(score: number): string {
  if (score >= 70) return '#e03448'
  if (score >= 50) return '#f07020'
  if (score >= 30) return '#c8982a'
  return '#27b97c'
}

// ── Suggestion card ───────────────────────────────────────────────────────

function SuggestionCard({ s, rank }: { s: CareerSuggestion; rank: number }) {
  const rankColors = ['#c8982a', '#336699', '#6b7280']
  const rc = rankColors[rank] ?? '#6b7280'

  return (
    <div style={{
      border:        `1px solid ${rc}28`,
      borderLeft:    `3px solid ${rc}`,
      borderRadius:  'var(--radius-md)',
      padding:       '12px 14px',
      flex:          1,
      minWidth:      200,
      background:    'var(--white)',
    }}>
      <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: rc, marginBottom: 4 }}>
        #{rank + 1} suggestion
      </div>
      <div style={{ fontFamily: 'var(--fb)', fontSize: 13, fontWeight: 700, color: 'var(--dark)', marginBottom: 2 }}>
        {s.role_title}
      </div>
      <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', marginBottom: 10 }}>
        {s.department} · {s.seniority}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px 12px', marginBottom: 10 }}>
        {[
          { label: 'Skill Overlap', value: `${(s.skill_overlap * 100).toFixed(0)}%` },
          { label: 'Timeline',      value: `${s.timeline_months} mo` },
          { label: 'Training Cost', value: fmtMoney(s.training_cost) },
          { label: 'Salary Uplift', value: fmtMoney(s.salary_uplift) },
        ].map(k => (
          <div key={k.label}>
            <div style={{ fontFamily: 'var(--fb)', fontSize: 8, letterSpacing: '1.5px', textTransform: 'uppercase', color: 'var(--mid)' }}>
              {k.label}
            </div>
            <div style={{ fontFamily: 'var(--fb)', fontSize: 13, fontWeight: 700, color: 'var(--dark)' }}>
              {k.value}
            </div>
          </div>
        ))}
      </div>

      {s.gap_skills.length > 0 && (
        <div>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 8, letterSpacing: '1.5px', textTransform: 'uppercase', color: 'var(--mid)', marginBottom: 4 }}>
            Skills to develop
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {s.gap_skills.map(sk => (
              <span key={sk} style={{
                fontFamily: 'var(--fb)', fontSize: 9, padding: '2px 7px',
                borderRadius: 'var(--radius-pill)', backgroundColor: 'var(--primary-10)',
                color: 'var(--primary-60)',
              }}>{sk}</span>
            ))}
          </div>
        </div>
      )}

      <div style={{ marginTop: 10, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1px', color: 'var(--mid)' }}>
          ROI
        </span>
        <span style={{ fontFamily: 'var(--fd)', fontSize: 18, fontWeight: 400, color: s.roi >= 3 ? '#27b97c' : s.roi >= 1.5 ? '#c8982a' : 'var(--mid)' }}>
          {s.roi >= 99 ? '—' : `${s.roi.toFixed(1)}×`}
        </span>
      </div>
    </div>
  )
}

// ── Stagnation heatmap ────────────────────────────────────────────────────
// Rows = seniority levels, Columns = departments

function StagnationHeatmap({ cells, depts }: { cells: StagnationHeatCell[]; depts: string[] }) {
  const cellMap: Record<string, Record<string, StagnationHeatCell>> = {}
  for (const c of cells) {
    if (!cellMap[c.seniority_level]) cellMap[c.seniority_level] = {}
    cellMap[c.seniority_level][c.department] = c
  }

  const CELL_W = 80, CELL_H = 40
  const LEFT = 68, TOP = 80
  const W = LEFT + depts.length * CELL_W + 20
  const H = TOP  + SEN_ORDER.length * CELL_H + 20

  return (
    <div style={{ overflowX: 'auto' }}>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ minWidth: W, display: 'block' }}>

        {/* Column headers (departments) */}
        {depts.map((dept, di) => (
          <text key={dept}
            x={LEFT + di * CELL_W + CELL_W / 2}
            y={TOP - 8}
            textAnchor="middle"
            fontSize={9}
            fill="#6b7280"
            fontFamily="Plus Jakarta Sans, sans-serif">
            {dept.length > 10 ? dept.slice(0, 9) + '…' : dept}
          </text>
        ))}

        {/* Row labels (seniority) + cells */}
        {SEN_ORDER.map((sen, si) => {
          const y = TOP + si * CELL_H
          return (
            <g key={sen}>
              <text x={LEFT - 8} y={y + CELL_H / 2 + 4}
                textAnchor="end" fontSize={10} fill="#1c1c2e"
                fontFamily="Plus Jakarta Sans, sans-serif">
                {sen}
              </text>
              {depts.map((dept, di) => {
                const cell = cellMap[sen]?.[dept]
                if (!cell) {
                  return (
                    <rect key={dept} x={LEFT + di * CELL_W + 1} y={y + 1}
                      width={CELL_W - 2} height={CELL_H - 2}
                      fill="#f4f6f9" rx={3} />
                  )
                }
                const bg = cell.avg_score >= 70 ? 'rgba(224,52,72,0.8)'
                  : cell.avg_score >= 50 ? 'rgba(240,112,32,0.75)'
                  : cell.avg_score >= 30 ? 'rgba(200,152,42,0.6)'
                  : 'rgba(39,185,124,0.5)'
                return (
                  <g key={dept}>
                    <rect x={LEFT + di * CELL_W + 1} y={y + 1}
                      width={CELL_W - 2} height={CELL_H - 2}
                      fill={bg} rx={3} />
                    <text x={LEFT + di * CELL_W + CELL_W / 2} y={y + CELL_H / 2 + 2}
                      textAnchor="middle" fontSize={12} fontWeight={700}
                      fill="#fff" fontFamily="Plus Jakarta Sans, sans-serif">
                      {cell.avg_score.toFixed(0)}
                    </text>
                    <text x={LEFT + di * CELL_W + CELL_W / 2} y={y + CELL_H / 2 + 14}
                      textAnchor="middle" fontSize={8}
                      fill="rgba(255,255,255,0.8)" fontFamily="Plus Jakarta Sans, sans-serif">
                      n={cell.count}
                    </text>
                  </g>
                )
              })}
            </g>
          )
        })}

        {/* Legend */}
        {[
          { label: '≥70 High', color: 'rgba(224,52,72,0.8)' },
          { label: '50–69',    color: 'rgba(240,112,32,0.75)' },
          { label: '30–49',    color: 'rgba(200,152,42,0.6)' },
          { label: '<30 Low',  color: 'rgba(39,185,124,0.5)' },
        ].map(({ label, color }, i) => (
          <g key={label} transform={`translate(${LEFT + i * 100}, ${H - 10})`}>
            <rect x={0} y={-8} width={10} height={10} fill={color} rx={2} />
            <text x={14} y={0} fontSize={8} fill="#6b7280"
              fontFamily="Plus Jakarta Sans, sans-serif">{label}</text>
          </g>
        ))}
      </svg>
    </div>
  )
}

// ── Succession depth bar ──────────────────────────────────────────────────

function DepthBar({ d1, d2, d3 }: { d1: number; d2: number; d3: number }) {
  const total = Math.max(d1 + d2 + d3, 1)
  const pct1 = (d1 / total) * 100
  const pct2 = (d2 / total) * 100
  const pct3 = (d3 / total) * 100
  return (
    <div style={{ display: 'flex', height: 10, borderRadius: 5, overflow: 'hidden', width: 120, backgroundColor: 'var(--primary-10)' }}>
      <div style={{ width: `${pct1}%`, backgroundColor: '#003366' }} />
      <div style={{ width: `${pct2}%`, backgroundColor: '#99bbdd' }} />
      <div style={{ width: `${pct3}%`, backgroundColor: '#e0eaf4' }} />
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────

export default function MobilityPage() {
  const { scenario, size, enabled: demo } = useDemoStore()

  const [data,    setData]    = useState<MobilityData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState<string | null>(null)
  const [tab,     setTab]     = useState<Tab>('paths')
  const [search,  setSearch]  = useState('')
  const [expanded, setExpanded] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    api.mobility.data(scenario, size, demo)
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
    fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px',
    textTransform: 'uppercase', color: 'var(--mid)',
    padding: '9px 12px', textAlign: 'left', fontWeight: 600,
  }

  // Derive dept list from heatmap cells
  const heatDepts = useMemo(() => {
    if (!data) return []
    const s = new Set(data.stagnation.dept_seniority_heat.map(c => c.department))
    return Array.from(s).sort()
  }, [data])

  const filteredPaths = useMemo(() => {
    if (!data) return []
    const q = search.toLowerCase()
    return data.career_paths.filter(cp =>
      !q || cp.full_name.toLowerCase().includes(q) || cp.department.toLowerCase().includes(q)
    ).slice(0, 40)
  }, [data, search])

  if (loading) return (
    <div style={{ padding: 64, textAlign: 'center', fontFamily: 'var(--fb)', color: 'var(--mid)' }}>
      Computing career paths…
    </div>
  )
  if (error) return (
    <div style={{ padding: 64, textAlign: 'center', fontFamily: 'var(--fb)', color: 'var(--status-red)' }}>
      {error}
    </div>
  )
  if (!data) return null

  const s = data.summary
  const tabs: { id: Tab; label: string }[] = [
    { id: 'paths',      label: 'Career Paths'    },
    { id: 'stagnation', label: 'Stagnation'      },
    { id: 'succession', label: 'Succession Depth'},
  ]

  const heroKpis = [
    { label: 'Paths Generated',   value: String(s.career_paths_count), note: 'Employees with ≥1 suggestion' },
    { label: 'Stagnation Risk',   value: String(s.stagnated_count),    note: `Avg score ${s.avg_stagnation}` },
    { label: 'Succession Gaps',   value: String(s.succession_gaps),    note: 'Leaders with no ready successor' },
    { label: 'Leaders Mapped',    value: String(s.leaders_mapped),     note: 'Succession depth analysed' },
  ]

  return (
    <div>
      {/* ── Hero ── */}
      <div style={{ background: 'var(--primary)', padding: '48px 48px' }}>
        <div style={{ maxWidth: 'var(--max-width-content)', margin: '0 auto' }}>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '3px', textTransform: 'uppercase', color: 'var(--gold)', marginBottom: 10 }}>
            Talent Mobility
          </div>
          <h1 style={{ fontFamily: 'var(--fd)', fontSize: 38, fontWeight: 600, fontStyle: 'italic', color: '#fff', margin: '0 0 10px' }}>
            Career Path &amp; Internal Mobility Intelligence
          </h1>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: 'rgba(255,255,255,0.55)', margin: 0 }}>
            Who could grow, where, and how — before you look outside.
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

        {/* Tabs */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 28 }}>
          {tabs.map(t => (
            <button key={t.id} style={tabBtn(tab === t.id)} onClick={() => setTab(t.id)}>
              {t.label}
            </button>
          ))}
        </div>

        {/* ── Tab: Career Paths ── */}
        {tab === 'paths' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

            <div style={{
              ...card,
              backgroundColor: 'rgba(0,51,102,0.04)',
              border: '1px solid var(--primary-30)',
            }}>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--primary-60)', lineHeight: 1.7 }}>
                <strong>How suggestions work:</strong> Each employee's current skill set is matched against every role in the catalog using Jaccard overlap.
                Candidates within ±1 seniority level are ranked by <em>(salary_uplift × skill_overlap) / training_cost</em>.
                Training cost = $4,000 per gap skill (professional upskilling estimate).
              </div>
            </div>

            <input
              placeholder="Search by name or department…"
              value={search}
              onChange={e => setSearch(e.target.value)}
              style={{
                width: '100%', maxWidth: 340,
                border: '1px solid var(--primary-30)', borderRadius: 'var(--radius-sm)',
                fontFamily: 'var(--fb)', fontSize: 13, padding: '8px 12px',
                outline: 'none', color: 'var(--dark)', background: 'var(--white)',
              }}
            />

            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {filteredPaths.map(cp => {
                const isOpen = expanded === cp.employee_id
                return (
                  <div key={cp.employee_id} style={card}>
                    {/* Header row */}
                    <div
                      style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer' }}
                      onClick={() => setExpanded(isOpen ? null : cp.employee_id)}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                        <div>
                          <div style={{ fontFamily: 'var(--fb)', fontSize: 14, fontWeight: 700, color: 'var(--dark)' }}>
                            {cp.full_name}
                          </div>
                          <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)' }}>
                            {cp.role_title} · {cp.department} · {cp.seniority_level}
                          </div>
                        </div>
                        <div style={{
                          fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 700, padding: '3px 10px',
                          borderRadius: 'var(--radius-pill)',
                          backgroundColor: `${stagColor(cp.stagnation_score)}14`,
                          color: stagColor(cp.stagnation_score),
                        }}>
                          Stagnation {cp.stagnation_score.toFixed(0)}
                        </div>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                        <div style={{ textAlign: 'right' }}>
                          <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1px', color: 'var(--mid)', textTransform: 'uppercase' }}>
                            {cp.suggestions.length} paths · {fmtMoney(cp.annual_salary)}
                          </div>
                        </div>
                        <span style={{ color: 'var(--mid)', fontSize: 16 }}>
                          {isOpen ? '▲' : '▼'}
                        </span>
                      </div>
                    </div>

                    {/* Expanded: suggestions */}
                    {isOpen && (
                      <div style={{ marginTop: 16, borderTop: '1px solid var(--primary-10)', paddingTop: 16 }}>
                        {cp.current_skills.length > 0 && (
                          <div style={{ marginBottom: 14 }}>
                            <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: 'var(--mid)', marginBottom: 6 }}>
                              Current skills
                            </div>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
                              {cp.current_skills.map(sk => (
                                <span key={sk} style={{
                                  fontFamily: 'var(--fb)', fontSize: 9, padding: '3px 9px',
                                  borderRadius: 'var(--radius-pill)',
                                  backgroundColor: 'var(--primary-10)', color: 'var(--primary-60)',
                                }}>{sk}</span>
                              ))}
                            </div>
                          </div>
                        )}

                        {cp.suggestions.length === 0 ? (
                          <div style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)' }}>
                            No adjacent roles found in catalog.
                          </div>
                        ) : (
                          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                            {cp.suggestions.map((s, idx) => (
                              <SuggestionCard key={idx} s={s} rank={idx} />
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* ── Tab: Stagnation ── */}
        {tab === 'stagnation' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>

            <div style={{
              ...card,
              backgroundColor: 'rgba(0,51,102,0.04)',
              border: '1px solid var(--primary-30)',
            }}>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--primary-60)', lineHeight: 1.7 }}>
                <strong>Stagnation score</strong> (0–100) combines four signals: tenure length (max 35), salary percentile within cohort (max 25), declining KPI trend (max 25), and seniority-tenure mismatch for junior/mid employees (max 15).
                Scores ≥ 60 are flagged as high-risk intervention candidates.
              </div>
            </div>

            {/* Heatmap */}
            <div style={card}>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--gold)', marginBottom: 16 }}>
                Avg stagnation score by department × seniority
              </div>
              <StagnationHeatmap
                cells={data.stagnation.dept_seniority_heat}
                depts={heatDepts}
              />
            </div>

            {/* Dept summary bars */}
            <div style={card}>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--mid)', marginBottom: 16 }}>
                Department summary
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {data.stagnation.dept_summary.map(row => (
                  <div key={row.department} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <div style={{ width: 140, fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--dark)', flexShrink: 0 }}>
                      {row.department}
                    </div>
                    <div style={{ flex: 1, height: 8, backgroundColor: 'var(--primary-10)', borderRadius: 4 }}>
                      <div style={{ height: '100%', borderRadius: 4, width: `${row.avg_score}%`, maxWidth: '100%', backgroundColor: stagColor(row.avg_score) }} />
                    </div>
                    <span style={{ fontFamily: 'var(--fb)', fontSize: 12, fontWeight: 700, color: stagColor(row.avg_score), width: 36, textAlign: 'right', flexShrink: 0 }}>
                      {row.avg_score.toFixed(0)}
                    </span>
                    <span style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', width: 48, flexShrink: 0 }}>
                      n={row.count}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* High-risk list */}
            {data.stagnation.high_risk.length > 0 && (
              <div style={card}>
                <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--gold)', marginBottom: 14 }}>
                  {data.stagnation.high_risk.length} high-risk employees (score ≥ 60)
                </div>
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{ backgroundColor: 'var(--primary-10)' }}>
                        {['Name', 'Department', 'Role', 'Tenure', 'Salary', 'Stagnation Score'].map(h => (
                          <th key={h} style={thStyle}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {data.stagnation.high_risk.map((e, i) => (
                        <tr key={e.employee_id}
                          style={{ backgroundColor: i % 2 === 0 ? 'var(--white)' : 'var(--primary-10)' }}>
                          <td style={{ padding: '8px 12px', fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--dark)' }}>{e.full_name}</td>
                          <td style={{ padding: '8px 12px', fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)' }}>{e.department}</td>
                          <td style={{ padding: '8px 12px', fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)' }}>{e.role_title}</td>
                          <td style={{ padding: '8px 12px', fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)' }}>{fmtTenure(e.tenure_days)}</td>
                          <td style={{ padding: '8px 12px', fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)', whiteSpace: 'nowrap' }}>{fmtMoney(e.annual_salary)}</td>
                          <td style={{ padding: '8px 12px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                              <div style={{ width: 80, height: 6, backgroundColor: 'var(--primary-10)', borderRadius: 3 }}>
                                <div style={{ height: '100%', borderRadius: 3, width: `${e.stagnation_score}%`, backgroundColor: stagColor(e.stagnation_score) }} />
                              </div>
                              <span style={{ fontFamily: 'var(--fb)', fontSize: 13, fontWeight: 700, color: stagColor(e.stagnation_score) }}>
                                {e.stagnation_score.toFixed(0)}
                              </span>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── Tab: Succession Depth ── */}
        {tab === 'succession' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>

            <div style={{
              ...card,
              backgroundColor: 'rgba(0,51,102,0.04)',
              border: '1px solid var(--primary-30)',
            }}>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--primary-60)', lineHeight: 1.7 }}>
                <strong>Depth 1</strong> = same dept, one level below, low stagnation (ready now).&nbsp;
                <strong>Depth 2</strong> = same dept, two levels below (ready ~12 months).&nbsp;
                <strong>Depth 3</strong> = broader pool (12–36 months). A role with zero Depth-1 successors is a single-point-of-leadership risk.
              </div>
            </div>

            <div style={card}>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ backgroundColor: 'var(--primary-10)' }}>
                      {['Leader', 'Role', 'Dept', 'Depth', 'Depth-1 (Ready Now)', 'Depth-2', 'Status'].map(h => (
                        <th key={h} style={thStyle}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.succession.map((row: SuccessionRow, i) => (
                      <tr key={row.employee_id + i}
                        style={{ backgroundColor: i % 2 === 0 ? 'var(--white)' : 'var(--primary-10)' }}>
                        <td style={{ padding: '8px 12px', fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--dark)', fontWeight: 600 }}>
                          {row.leader_name}
                        </td>
                        <td style={{ padding: '8px 12px', fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)' }}>
                          {row.role_title}
                        </td>
                        <td style={{ padding: '8px 12px', fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)' }}>
                          {row.department}
                        </td>
                        <td style={{ padding: '8px 12px' }}>
                          <DepthBar d1={row.depth_1_count} d2={row.depth_2_count} d3={row.depth_3_count} />
                          <div style={{ fontFamily: 'var(--fb)', fontSize: 9, color: 'var(--mid)', marginTop: 3 }}>
                            {row.depth_1_count}/{row.depth_2_count}/{row.depth_3_count}
                          </div>
                        </td>
                        <td style={{ padding: '8px 12px' }}>
                          {row.depth_1.length > 0 ? (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                              {row.depth_1.slice(0, 3).map(name => (
                                <span key={name} style={{ fontFamily: 'var(--fb)', fontSize: 11, color: '#003366' }}>{name}</span>
                              ))}
                              {row.depth_1.length > 3 && (
                                <span style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'var(--mid)' }}>+{row.depth_1.length - 3} more</span>
                              )}
                            </div>
                          ) : (
                            <span style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', fontStyle: 'italic' }}>None</span>
                          )}
                        </td>
                        <td style={{ padding: '8px 12px' }}>
                          {row.depth_2.length > 0 ? (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                              {row.depth_2.slice(0, 2).map(name => (
                                <span key={name} style={{ fontFamily: 'var(--fb)', fontSize: 11, color: '#99bbdd' }}>{name}</span>
                              ))}
                              {row.depth_2.length > 2 && (
                                <span style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'var(--mid)' }}>+{row.depth_2.length - 2} more</span>
                              )}
                            </div>
                          ) : (
                            <span style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', fontStyle: 'italic' }}>None</span>
                          )}
                        </td>
                        <td style={{ padding: '8px 12px' }}>
                          {row.succession_gap ? (
                            <span style={{
                              fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1px', fontWeight: 700,
                              padding: '3px 10px', borderRadius: 'var(--radius-pill)',
                              backgroundColor: 'rgba(224,52,72,0.1)', color: '#e03448',
                            }}>GAP</span>
                          ) : (
                            <span style={{
                              fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1px', fontWeight: 700,
                              padding: '3px 10px', borderRadius: 'var(--radius-pill)',
                              backgroundColor: 'rgba(39,185,124,0.1)', color: '#27b97c',
                            }}>COVERED</span>
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
      </div>
    </div>
  )
}
