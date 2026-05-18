// Executive Dashboard — fetches from /api/dashboard and renders:
// 1. Hero with 4 org-level KPI stats
// 2. Department summary table
// 3. Impact score distribution (CSS bar chart)
// 4. Employee table with search

import React, { useEffect, useState } from 'react'
import Eyebrow from '../components/Eyebrow'
import { api, type DashboardData, type DepartmentRow, type EmployeeRow } from '../services/api'
import { useDemoStore } from '../stores/demoStore'

// ── Shared styles ────────────────────────────────────────────────────────

const hero: React.CSSProperties = {
  backgroundColor: 'var(--primary)',
  backgroundImage: `
    linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px)
  `,
  backgroundSize: '48px 48px',
  padding:        '56px 48px',
}

const body: React.CSSProperties = {
  backgroundColor: 'var(--light)',
  minHeight:       '70vh',
}

const section: React.CSSProperties = {
  maxWidth: 'var(--max-width-dashboard)',
  margin:   '0 auto',
  padding:  '48px 48px',
}

const card: React.CSSProperties = {
  backgroundColor: 'var(--white)',
  borderRadius:    'var(--radius-md)',
  padding:         '28px',
  boxShadow:       'var(--shadow-card)',
  border:          '1px solid var(--primary-10)',
}

const divider: React.CSSProperties = { height: 1, background: 'var(--primary-10)', margin: '40px 0' }

// ── Sub-components ───────────────────────────────────────────────────────

function KpiCard({ label, value, sub, accent }: { label: string; value: string; sub?: string; accent: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'stretch', gap: 16, ...card }}>
      <div style={{ width: 3, backgroundColor: accent, borderRadius: 2, flexShrink: 0 }} />
      <div>
        <div style={{ fontFamily: 'var(--fd)', fontSize: 30, fontWeight: 300, color: 'var(--dark)', lineHeight: 1 }}>
          {value}
        </div>
        {sub && (
          <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: sub.startsWith('+') ? 'var(--status-green)' : sub.startsWith('−') ? 'var(--status-orange)' : 'var(--mid)', marginTop: 4 }}>
            {sub}
          </div>
        )}
        <div style={{ fontFamily: 'var(--fb)', fontSize: 10, textTransform: 'uppercase', letterSpacing: '2px', color: 'var(--mid)', marginTop: 6 }}>
          {label}
        </div>
      </div>
    </div>
  )
}

function VariancePill({ pct }: { pct: number }) {
  const over  = pct > 5
  const under = pct < -5
  const color = over ? 'var(--status-orange)' : under ? 'var(--status-green)' : 'var(--mid)'
  const bg    = over ? 'var(--status-orange-bg)' : under ? 'var(--status-green-bg)' : 'var(--primary-10)'
  return (
    <span style={{ display: 'inline-block', background: bg, color, borderRadius: 'var(--radius-pill)', padding: '2px 8px', fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 600 }}>
      {pct >= 0 ? '+' : ''}{pct.toFixed(1)}%
    </span>
  )
}

function ImpactBar({ score }: { score: number }) {
  const pct   = Math.min(100, Math.max(0, score))
  const color = pct >= 70 ? 'var(--status-green)' : pct >= 40 ? 'var(--gold)' : 'var(--status-orange)'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ flex: 1, height: 4, background: 'var(--primary-10)', borderRadius: 2 }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 2, transition: 'width 0.3s' }} />
      </div>
      <span style={{ fontFamily: 'var(--fb)', fontSize: 11, fontWeight: 600, color, minWidth: 28, textAlign: 'right' }}>
        {score.toFixed(0)}
      </span>
    </div>
  )
}

// ── Department table ─────────────────────────────────────────────────────

function DeptTable({ rows }: { rows: DepartmentRow[] }) {
  const th: React.CSSProperties = {
    fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 600, letterSpacing: '2px',
    textTransform: 'uppercase', padding: '12px 16px', textAlign: 'left',
    color: '#fff', background: 'var(--primary)', whiteSpace: 'nowrap',
  }
  const td: React.CSSProperties = {
    fontFamily: 'var(--fb)', fontSize: 13, padding: '10px 16px', color: 'var(--dark)',
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
            <th style={{ ...th, minWidth: 140 }}>Avg Impact</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.department} style={{ background: i % 2 === 0 ? 'var(--white)' : 'var(--primary-10)' }}>
              <td style={{ ...td, fontWeight: 600 }}>{r.department}</td>
              <td style={{ ...td, textAlign: 'right' }}>{r.headcount.toLocaleString()}</td>
              <td style={{ ...td, textAlign: 'right' }}>${(r.total_spend / 1_000_000).toFixed(2)}M</td>
              <td style={{ ...td, textAlign: 'right' }}>${(r.annual_budget / 1_000_000).toFixed(2)}M</td>
              <td style={{ ...td, textAlign: 'center' }}><VariancePill pct={r.budget_variance_pct} /></td>
              <td style={td}><ImpactBar score={r.avg_impact} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Employee table ───────────────────────────────────────────────────────

function EmployeeTable({ rows }: { rows: EmployeeRow[] }) {
  const [query, setQuery]   = useState('')
  const [sortKey, setSortKey] = useState<keyof EmployeeRow>('impact_score')
  const [sortAsc, setSortAsc] = useState(false)

  const toggle = (key: keyof EmployeeRow) => {
    if (sortKey === key) setSortAsc((a) => !a)
    else { setSortKey(key); setSortAsc(false) }
  }

  const filtered = rows
    .filter((r) => {
      const q = query.toLowerCase()
      return (
        r.full_name.toLowerCase().includes(q) ||
        r.department.toLowerCase().includes(q) ||
        r.role_title.toLowerCase().includes(q)
      )
    })
    .sort((a, b) => {
      const av = a[sortKey]; const bv = b[sortKey]
      const cmp = typeof av === 'string' ? av.localeCompare(bv as string) : (av as number) - (bv as number)
      return sortAsc ? cmp : -cmp
    })

  const th = (_label: string, _key: keyof EmployeeRow, align: 'left' | 'right' | 'center' = 'left'): React.CSSProperties => ({
    fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 600, letterSpacing: '2px',
    textTransform: 'uppercase', padding: '12px 16px', textAlign: align,
    color: '#fff', background: 'var(--primary)', cursor: 'pointer', whiteSpace: 'nowrap',
  })

  const header = (label: string, key: keyof EmployeeRow, align?: 'left' | 'right' | 'center') => (
    <th style={th(label, key, align)} onClick={() => toggle(key)}>
      {label}{sortKey === key ? (sortAsc ? ' ▴' : ' ▾') : ''}
    </th>
  )

  const td: React.CSSProperties = { fontFamily: 'var(--fb)', fontSize: 13, padding: '10px 16px', color: 'var(--dark)' }

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by name, department, role…"
          style={{ fontFamily: 'var(--fb)', fontSize: 13, padding: '8px 14px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--primary-10)', background: 'var(--white)', color: 'var(--dark)', width: 320, outline: 'none' }}
        />
      </div>
      <div style={{ overflowX: 'auto', maxHeight: 480, overflowY: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead style={{ position: 'sticky', top: 0 }}>
            <tr>
              {header('Name',       'full_name')}
              {header('Department', 'department')}
              {header('Role',       'role_title')}
              {header('Impact',     'impact_score', 'right')}
              {header('Attrition', 'attrition_risk', 'right')}
              <th style={th('Flags', 'is_nexus', 'center')}>Flags</th>
            </tr>
          </thead>
          <tbody>
            {filtered.slice(0, 200).map((r, i) => (
              <tr key={r.employee_id} style={{ background: i % 2 === 0 ? 'var(--white)' : 'var(--primary-10)' }}>
                <td style={{ ...td, fontWeight: 600 }}>{r.full_name}</td>
                <td style={td}>{r.department}</td>
                <td style={{ ...td, color: 'var(--mid)' }}>{r.role_title}</td>
                <td style={{ ...td, textAlign: 'right' }}>
                  <span style={{ fontFamily: 'var(--fd)', fontSize: 14, fontWeight: 400, color: r.impact_score >= 70 ? 'var(--status-green)' : r.impact_score >= 40 ? 'var(--gold)' : 'var(--status-orange)' }}>
                    {r.impact_score.toFixed(0)}
                  </span>
                </td>
                <td style={{ ...td, textAlign: 'right' }}>
                  <span style={{ color: r.attrition_risk >= 0.7 ? 'var(--status-red)' : r.attrition_risk >= 0.4 ? 'var(--status-orange)' : 'var(--mid)' }}>
                    {(r.attrition_risk * 100).toFixed(0)}%
                  </span>
                </td>
                <td style={{ ...td, textAlign: 'center' }}>
                  {r.is_nexus && (
                    <span title="Organizational Nexus" style={{ fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 700, letterSpacing: '1px', textTransform: 'uppercase', background: 'var(--status-purple-bg)', color: 'var(--status-purple)', borderRadius: 'var(--radius-pill)', padding: '2px 8px' }}>
                      Nexus
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length > 200 && (
          <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)', padding: '12px 16px', textAlign: 'center' }}>
            Showing 200 of {filtered.length} results — refine your search to see more.
          </div>
        )}
      </div>
    </div>
  )
}

// ── Main ─────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const { scenario, size, enabled: demo } = useDemoStore()
  const [data,    setData]    = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    api.dashboard
      .data(scenario, size, demo)
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [scenario, size, demo])

  const scenarioLabels: Record<string, string> = {
    A: 'Growing Company',
    B: 'Restructuring',
    C: 'Merger Integration',
  }

  if (loading) return (
    <div style={{ ...body, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: 'var(--mid)' }}>Loading analytics data…</p>
    </div>
  )

  if (error || !data) return (
    <div style={{ ...body, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ textAlign: 'center' }}>
        <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: 'var(--status-orange)', marginBottom: 8 }}>
          Could not load dashboard data.
        </p>
        <p style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)' }}>
          {error ?? 'Unknown error'} — ensure the backend is running on port 8000.
        </p>
      </div>
    </div>
  )

  const varSign = data.budget_variance_pct >= 0 ? '+' : '−'
  const varAbs  = Math.abs(data.budget_variance_pct).toFixed(1)

  return (
    <div>
      {/* Hero */}
      <div style={hero}>
        <div style={{ maxWidth: 'var(--max-width-dashboard)', margin: '0 auto' }}>
          <Eyebrow light>
            {data.org_size.toUpperCase()} ORG · SCENARIO {data.scenario_id} — {scenarioLabels[data.scenario_id] ?? data.scenario_id}
          </Eyebrow>
          <h1 style={{ fontFamily: 'var(--fd)', fontSize: 34, fontWeight: 300, color: '#fff', margin: '0 0 8px', lineHeight: 1.2 }}>
            {data.org_name} —{' '}
            <em style={{ fontStyle: 'italic', color: 'var(--gold-light)' }}>Executive Dashboard</em>
          </h1>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: 'rgba(255,255,255,0.55)', margin: '0 0 32px' }}>
            Workforce analytics · impact scoring · budget status
          </p>
          <div style={{ display: 'flex', gap: 40, flexWrap: 'wrap' }}>
            {[
              { value: data.total_headcount.toLocaleString(), label: 'Total Employees',    accent: 'var(--primary-60)' },
              { value: `$${(data.total_budget / 1_000_000).toFixed(1)}M`,  label: 'Annual Budget',      accent: 'var(--gold)' },
              { value: `$${(data.total_spend / 1_000_000).toFixed(1)}M`,   label: 'YTD Spend',          accent: data.budget_variance_pct > 5 ? 'var(--status-orange)' : 'var(--status-green)' },
              { value: data.avg_impact_score.toFixed(1),    label: 'Avg Impact Score',    accent: 'var(--status-purple)' },
            ].map(({ value, label, accent: _accent }) => (
              <div key={label} style={{ borderLeft: '2px solid var(--gold)', paddingLeft: 18 }}>
                <div style={{ fontFamily: 'var(--fd)', fontSize: 34, fontWeight: 300, color: 'var(--gold-light)', lineHeight: 1, marginBottom: 8 }}>
                  {value}
                </div>
                <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'rgba(255,255,255,0.5)' }}>
                  {label}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Body */}
      <div style={body}>
        <div style={section}>

          {/* KPI strip */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 40 }}>
            <KpiCard label="Budget Variance"    value={`${varSign}${varAbs}%`}                                    accent={data.budget_variance_pct > 5 ? 'var(--status-orange)' : 'var(--status-green)'} />
            <KpiCard label="Nexus Employees"    value={data.n_nexus_employees.toString()}  sub="Org network anchors"  accent="var(--status-purple)" />
            <KpiCard label="At-Risk Teams"      value={data.n_at_risk_teams.toString()}    sub="Budget overrun > 5%"  accent="var(--status-orange)" />
            <KpiCard label="Scoring Mode"       value={data.scoring_mode === 'ml' ? 'ML' : 'Heuristic'}            accent="var(--primary-60)" />
          </div>

          {/* Department table */}
          <Eyebrow>Department Overview</Eyebrow>
          <h2 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--dark)', marginBottom: 20 }}>
            Budget and impact by <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>department.</em>
          </h2>
          <div style={card}>
            <DeptTable rows={data.dept_summary} />
          </div>

          <div style={divider} />

          {/* Employee table */}
          <Eyebrow>Employee Intelligence</Eyebrow>
          <h2 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--dark)', marginBottom: 20 }}>
            Impact scores, attrition risk, and <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>network flags.</em>
          </h2>
          <div style={card}>
            <EmployeeTable rows={data.employee_table} />
          </div>

        </div>
      </div>
    </div>
  )
}
