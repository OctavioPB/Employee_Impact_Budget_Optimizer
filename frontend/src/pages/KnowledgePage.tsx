import React, { useState, useEffect } from 'react'
import {
  api,
  KnowledgeData,
  HeatmapEmployee,
  HeatmapDomain,
  HeatmapCell,
  TransferRow,
} from '../services/api'
import { useDemoStore } from '../stores/demoStore'

type Tab = 'alerts' | 'map' | 'roadmap'

// ── Helpers ───────────────────────────────────────────────────────────────

function fmtMoney(v: number): string {
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(2)}M`
  if (v >= 1_000)     return `$${(v / 1_000).toFixed(0)}K`
  return `$${v.toFixed(0)}`
}

function critColor(c: number): string {
  if (c >= 0.90) return '#e03448'
  if (c >= 0.78) return '#f07020'
  return '#c8982a'
}

function profColor(p: number): string {
  if (p >= 4.0) return '#003366'
  if (p >= 3.0) return '#336699'
  if (p >= 2.0) return '#99bbdd'
  return '#e0eaf4'
}

// ── Knowledge Heatmap ─────────────────────────────────────────────────────
// Rows = employees (top 25 by knowledge_loss_score)
// Cols = knowledge domains (sorted by criticality)
// Cell colour = proficiency level, SKH cells get a dot marker

function KnowledgeHeatmap({
  employees,
  domains,
  cells,
}: {
  employees: HeatmapEmployee[]
  domains:   HeatmapDomain[]
  cells:     HeatmapCell[]
}) {
  const cellMap: Record<string, Record<string, HeatmapCell>> = {}
  for (const c of cells) {
    if (!cellMap[c.employee_id]) cellMap[c.employee_id] = {}
    cellMap[c.employee_id][c.domain_id] = c
  }

  // Layout
  const CELL_W = 28, CELL_H = 22
  const LEFT   = 168, TOP = 90
  const W = LEFT + domains.length * CELL_W + 20
  const H = TOP  + employees.length * CELL_H + 40

  return (
    <div style={{ overflowX: 'auto' }}>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ minWidth: W, display: 'block' }}>

        {/* Column headers (domain names, rotated) */}
        {domains.map((dom, di) => (
          <g key={dom.domain_id}>
            <text
              x={LEFT + di * CELL_W + CELL_W / 2}
              y={TOP - 6}
              textAnchor="start"
              fontSize={8}
              fill={critColor(dom.criticality)}
              fontFamily="Plus Jakarta Sans, sans-serif"
              transform={`rotate(-55, ${LEFT + di * CELL_W + CELL_W / 2}, ${TOP - 6})`}
            >
              {dom.name.length > 22 ? dom.name.slice(0, 21) + '…' : dom.name}
            </text>
          </g>
        ))}

        {/* Row headers + cells */}
        {employees.map((emp, ei) => {
          const y = TOP + ei * CELL_H
          return (
            <g key={emp.employee_id}>
              {/* KL score bar (left margin) */}
              <rect x={0} y={y + 3} width={Math.round(emp.knowledge_loss_score * 0.55)} height={CELL_H - 6}
                fill="#003366" fillOpacity={0.15} rx={2} />
              <text x={62} y={y + CELL_H / 2 + 4}
                fontSize={9} fill="#6b7280" textAnchor="end"
                fontFamily="Plus Jakarta Sans, sans-serif">
                {emp.knowledge_loss_score.toFixed(0)}
              </text>

              {/* Name */}
              <text x={70} y={y + CELL_H / 2 + 4}
                fontSize={10} fill="#1c1c2e"
                fontFamily="Plus Jakarta Sans, sans-serif">
                {emp.full_name.length > 18 ? emp.full_name.slice(0, 17) + '…' : emp.full_name}
              </text>

              {/* Cells */}
              {domains.map((dom, di) => {
                const cell = cellMap[emp.employee_id]?.[dom.domain_id]
                const cx = LEFT + di * CELL_W
                if (!cell) {
                  return (
                    <rect key={dom.domain_id} x={cx + 1} y={y + 1}
                      width={CELL_W - 2} height={CELL_H - 2}
                      fill="#f4f6f9" rx={2} />
                  )
                }
                return (
                  <g key={dom.domain_id}>
                    <rect x={cx + 1} y={y + 1}
                      width={CELL_W - 2} height={CELL_H - 2}
                      fill={profColor(cell.proficiency)} rx={2} />
                    <text x={cx + CELL_W / 2} y={y + CELL_H / 2 + 3}
                      textAnchor="middle" fontSize={8}
                      fill={cell.proficiency >= 3.0 ? '#fff' : '#336699'}
                      fontFamily="Plus Jakarta Sans, sans-serif"
                      fontWeight={cell.is_skh ? 700 : 400}>
                      {cell.proficiency.toFixed(1)}
                    </text>
                    {/* SKH marker: red dot top-right */}
                    {cell.is_skh && (
                      <circle cx={cx + CELL_W - 4} cy={y + 4} r={3} fill="#e03448" />
                    )}
                  </g>
                )
              })}
            </g>
          )
        })}

        {/* Legend */}
        {[
          { color: '#003366', label: '4.0–5.0 Expert' },
          { color: '#336699', label: '3.0–3.9 Proficient' },
          { color: '#99bbdd', label: '2.0–2.9 Developing' },
          { color: '#e0eaf4', label: '< 2.0 Novice' },
        ].map(({ color, label }, i) => (
          <g key={label} transform={`translate(${LEFT + i * 145}, ${H - 20})`}>
            <rect x={0} y={0} width={14} height={10} fill={color} rx={2} />
            <text x={18} y={9} fontSize={9} fill="#6b7280"
              fontFamily="Plus Jakarta Sans, sans-serif">
              {label}
            </text>
          </g>
        ))}
        <g transform={`translate(${LEFT + 4 * 145}, ${H - 20})`}>
          <circle cx={5} cy={5} r={4} fill="#e03448" />
          <text x={13} y={9} fontSize={9} fill="#6b7280"
            fontFamily="Plus Jakarta Sans, sans-serif">
            SKH (sole holder)
          </text>
        </g>
      </svg>
    </div>
  )
}

// ── Urgency bar ───────────────────────────────────────────────────────────

function UrgencyBar({ score }: { score: number }) {
  const color = score >= 0.7 ? '#e03448' : score >= 0.4 ? '#f07020' : '#c8982a'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ flex: 1, height: 5, backgroundColor: 'var(--primary-10)', borderRadius: 3 }}>
        <div style={{ height: '100%', borderRadius: 3, backgroundColor: color, width: `${score * 100}%`, maxWidth: '100%' }} />
      </div>
      <span style={{ fontFamily: 'var(--fb)', fontSize: 11, color, width: 34, textAlign: 'right' }}>
        {(score * 100).toFixed(0)}
      </span>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────

export default function KnowledgePage() {
  const { scenario, size, enabled: demo } = useDemoStore()

  const [data,    setData]    = useState<KnowledgeData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState<string | null>(null)
  const [tab,     setTab]     = useState<Tab>('alerts')

  useEffect(() => {
    setLoading(true)
    api.knowledge.data(scenario, size, demo)
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

  if (loading) return (
    <div style={{ padding: 64, textAlign: 'center', fontFamily: 'var(--fb)', color: 'var(--mid)' }}>
      Mapping knowledge graph…
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
    { id: 'alerts',  label: 'SKH Alerts'       },
    { id: 'map',     label: 'Knowledge Map'     },
    { id: 'roadmap', label: 'Transfer Roadmap'  },
  ]

  const heroKpis = [
    { label: 'Knowledge Domains',  value: String(s.total_domains),         note: '23 institutional categories' },
    { label: 'SKH Domains',        value: String(s.skh_domains),           note: 'Single-holder critical domains' },
    { label: 'SKH Employees',      value: String(s.skh_employees),         note: 'Sole owners of critical knowledge' },
    { label: 'High-Risk Employees',value: String(s.high_risk_employees),   note: 'Knowledge loss score ≥ 60' },
  ]

  // SKH alerts: employees who are sole holders, sorted by max criticality domain
  const skhEmployees = data.employees.filter(e => e.is_skh)

  // Domain criticality lookup
  const domainByName = Object.fromEntries(data.domains.map(d => [d.name, d]))

  return (
    <div>
      {/* ── Hero ── */}
      <div style={{ background: 'var(--primary)', padding: '48px 48px' }}>
        <div style={{ maxWidth: 'var(--max-width-content)', margin: '0 auto' }}>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '3px', textTransform: 'uppercase', color: 'var(--gold)', marginBottom: 10 }}>
            Knowledge Intelligence
          </div>
          <h1 style={{ fontFamily: 'var(--fd)', fontSize: 38, fontWeight: 600, fontStyle: 'italic', color: '#fff', margin: '0 0 10px' }}>
            Institutional Memory &amp; Knowledge Graph
          </h1>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: 'rgba(255,255,255,0.55)', margin: 0 }}>
            Who knows what, who teaches whom — and which knowledge has no backup holder.
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

        {/* ── Tab: SKH Alerts ── */}
        {tab === 'alerts' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>

            {/* Domain coverage table */}
            <div style={card}>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--gold)', marginBottom: 14 }}>
                Domain coverage status — {data.domains.length} domains
              </div>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ backgroundColor: 'var(--primary-10)' }}>
                      {['Domain', 'Criticality', 'Holders', 'Primary', 'Backup', 'Coverage', 'Risk'].map(h => (
                        <th key={h} style={thStyle}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.domains.map((dom, i) => (
                      <tr key={dom.domain_id}
                        style={{ backgroundColor: i % 2 === 0 ? 'var(--white)' : 'var(--primary-10)' }}>
                        <td style={{ padding: '8px 12px', fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--dark)', fontWeight: 600 }}>
                          {dom.name}
                        </td>
                        <td style={{ padding: '8px 12px' }}>
                          <span style={{ fontFamily: 'var(--fb)', fontSize: 12, fontWeight: 700, color: critColor(dom.criticality) }}>
                            {(dom.criticality * 100).toFixed(0)}%
                          </span>
                        </td>
                        <td style={{ padding: '8px 12px', fontFamily: 'var(--fb)', fontSize: 13, color: dom.holder_count === 0 ? '#e03448' : 'var(--dark)', fontWeight: 700 }}>
                          {dom.holder_count}
                        </td>
                        <td style={{ padding: '8px 12px', fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--dark)' }}>
                          {dom.primary_holder}
                        </td>
                        <td style={{ padding: '8px 12px', fontFamily: 'var(--fb)', fontSize: 12, color: dom.backup_holder === '—' ? 'var(--mid)' : 'var(--dark)' }}>
                          {dom.backup_holder}
                          {dom.backup_holder !== '—' && (
                            <span style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'var(--mid)', marginLeft: 6 }}>
                              ({dom.backup_proficiency.toFixed(1)})
                            </span>
                          )}
                        </td>
                        <td style={{ padding: '8px 12px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            <div style={{ width: 48, height: 5, backgroundColor: 'var(--primary-10)', borderRadius: 3 }}>
                              <div style={{ height: '100%', borderRadius: 3, width: `${dom.coverage_ratio * 100}%`, maxWidth: '100%',
                                backgroundColor: dom.coverage_ratio >= 1 ? '#27b97c' : dom.coverage_ratio >= 0.5 ? '#f07020' : '#e03448' }} />
                            </div>
                            <span style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'var(--mid)' }}>
                              {(dom.coverage_ratio * 100).toFixed(0)}%
                            </span>
                          </div>
                        </td>
                        <td style={{ padding: '8px 12px' }}>
                          {dom.is_uncovered ? (
                            <span style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1px', fontWeight: 700, padding: '3px 10px', borderRadius: 'var(--radius-pill)', backgroundColor: 'rgba(224,52,72,0.15)', color: '#e03448' }}>
                              UNCOVERED
                            </span>
                          ) : dom.is_skh ? (
                            <span style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1px', fontWeight: 700, padding: '3px 10px', borderRadius: 'var(--radius-pill)', backgroundColor: 'rgba(240,112,32,0.12)', color: '#f07020' }}>
                              SKH
                            </span>
                          ) : (
                            <span style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1px', fontWeight: 700, padding: '3px 10px', borderRadius: 'var(--radius-pill)', backgroundColor: 'rgba(39,185,124,0.1)', color: '#27b97c' }}>
                              OK
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* SKH employees */}
            {skhEmployees.length > 0 && (
              <div style={card}>
                <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--gold)', marginBottom: 14 }}>
                  {skhEmployees.length} Single-Knowledge-Holder employees
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {skhEmployees.map(emp => (
                    <div key={emp.employee_id} style={{
                      border: '1px solid rgba(240,112,32,0.25)',
                      borderLeft: '4px solid #f07020',
                      borderRadius: 'var(--radius-md)',
                      padding: '14px 18px',
                      display: 'grid',
                      gridTemplateColumns: '1fr auto',
                      alignItems: 'start',
                      gap: 16,
                    }}>
                      <div>
                        <div style={{ fontFamily: 'var(--fb)', fontSize: 14, fontWeight: 700, color: 'var(--dark)', marginBottom: 2 }}>
                          {emp.full_name}
                        </div>
                        <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)', marginBottom: 10 }}>
                          {emp.role_title} · {emp.department}
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                          {emp.skh_domains.map(dn => {
                            const dom = domainByName[dn]
                            const crit = dom?.criticality ?? 0.7
                            return (
                              <span key={dn} style={{
                                fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 600,
                                padding: '3px 10px', borderRadius: 'var(--radius-pill)',
                                backgroundColor: `${critColor(crit)}12`,
                                color: critColor(crit),
                                border: `1px solid ${critColor(crit)}30`,
                              }}>
                                {dn}
                              </span>
                            )
                          })}
                        </div>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: 'var(--mid)', marginBottom: 4 }}>
                          Knowledge Loss Score
                        </div>
                        <div style={{ fontFamily: 'var(--fd)', fontSize: 28, fontWeight: 400, color: emp.knowledge_loss_score >= 60 ? '#e03448' : '#f07020' }}>
                          {emp.knowledge_loss_score.toFixed(0)}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── Tab: Knowledge Map ── */}
        {tab === 'map' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
            <div style={{
              ...card,
              backgroundColor: 'rgba(0,51,102,0.04)',
              border: '1px solid var(--primary-30)',
            }}>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--primary-60)', lineHeight: 1.7 }}>
                <strong>Reading the map:</strong> Rows are the top 25 employees ranked by Knowledge Loss Score (left bar).
                Columns are knowledge domains ordered by criticality (left = most critical). Cell colour = proficiency level (1–5).
                A <strong style={{ color: '#e03448' }}>red dot</strong> marks Single-Knowledge-Holder cells — this employee is the only qualified person for that domain.
              </div>
            </div>

            <div style={{ ...card, padding: '24px 16px' }}>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--gold)', marginBottom: 18 }}>
                Employee × Domain proficiency matrix
              </div>
              <KnowledgeHeatmap
                employees={data.heatmap.employees}
                domains={data.heatmap.domains}
                cells={data.heatmap.cells}
              />
            </div>
          </div>
        )}

        {/* ── Tab: Transfer Roadmap ── */}
        {tab === 'roadmap' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
            <div style={{
              ...card,
              backgroundColor: 'rgba(39,185,124,0.06)',
              border: '1px solid rgba(39,185,124,0.2)',
            }}>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: '#0d5c3a', lineHeight: 1.7 }}>
                <strong>Urgency score</strong> = domain criticality × knowledge loss score of current holder.
                <strong> Transfer cost</strong> estimates 3 months of coaching per proficiency point gap at $6,000/month.
                Prioritise rows with high urgency and SKH status — these represent knowledge concentration risk.
              </div>
            </div>

            <div style={card}>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--mid)', marginBottom: 14 }}>
                {data.transfer_roadmap.length} transfer opportunities — ranked by urgency
              </div>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ backgroundColor: 'var(--primary-10)' }}>
                      {['Domain', 'Crit.', 'Current Holder', 'Successor', 'Gap', 'Months', 'Investment', 'Urgency'].map(h => (
                        <th key={h} style={thStyle}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.transfer_roadmap.map((row: TransferRow, i) => (
                      <tr key={row.domain_id + i}
                        style={{ backgroundColor: i % 2 === 0 ? 'var(--white)' : 'var(--primary-10)' }}>
                        <td style={{ padding: '8px 12px' }}>
                          <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--dark)', fontWeight: 600 }}>
                            {row.domain_name}
                          </div>
                          {row.is_skh && (
                            <span style={{ fontFamily: 'var(--fb)', fontSize: 8, letterSpacing: '1px', fontWeight: 700, padding: '2px 6px', borderRadius: 'var(--radius-pill)', backgroundColor: 'rgba(240,112,32,0.12)', color: '#f07020' }}>
                              SKH
                            </span>
                          )}
                        </td>
                        <td style={{ padding: '8px 12px', fontFamily: 'var(--fb)', fontSize: 12, fontWeight: 700, color: critColor(row.criticality) }}>
                          {(row.criticality * 100).toFixed(0)}%
                        </td>
                        <td style={{ padding: '8px 12px' }}>
                          <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--dark)' }}>{row.current_holder}</div>
                          <div style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'var(--mid)' }}>
                            {row.current_holder_dept} · prof {row.current_proficiency.toFixed(1)}
                          </div>
                        </td>
                        <td style={{ padding: '8px 12px' }}>
                          <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--dark)' }}>{row.successor}</div>
                          {row.successor_proficiency > 0 && (
                            <div style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'var(--mid)' }}>
                              prof {row.successor_proficiency.toFixed(1)}
                            </div>
                          )}
                        </td>
                        <td style={{ padding: '8px 12px', fontFamily: 'var(--fb)', fontSize: 13, fontWeight: 700, color: row.proficiency_gap >= 1.5 ? '#e03448' : '#c8982a' }}>
                          {row.proficiency_gap > 0 ? `+${row.proficiency_gap.toFixed(1)}` : '—'}
                        </td>
                        <td style={{ padding: '8px 12px', fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)' }}>
                          {row.transfer_months > 0 ? `${row.transfer_months.toFixed(1)} mo` : '< 1 mo'}
                        </td>
                        <td style={{ padding: '8px 12px', fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)', whiteSpace: 'nowrap' }}>
                          {fmtMoney(row.transfer_cost)}
                        </td>
                        <td style={{ padding: '8px 12px', minWidth: 120 }}>
                          <UrgencyBar score={row.urgency_score} />
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
