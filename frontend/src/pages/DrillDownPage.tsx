import React, { useState, useEffect } from 'react'
import { api, DashboardData, EmployeeRow } from '../services/api'
import { useDemoStore } from '../stores/demoStore'

// ── Breadcrumb ────────────────────────────────────────────────────────────────

type View = 'org' | 'department' | 'employee'

interface Crumb { label: string; view: View; dept?: string; empId?: string }

function Breadcrumbs({ crumbs, onJump }: { crumbs: Crumb[]; onJump: (i: number) => void }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 24 }}>
      {crumbs.map((c, i) => (
        <React.Fragment key={i}>
          {i > 0 && <span style={{ color: 'var(--mid)', fontFamily: 'var(--fb)', fontSize: 12 }}>›</span>}
          <button
            onClick={() => onJump(i)}
            style={{
              background: 'none', border: 'none', cursor: i === crumbs.length - 1 ? 'default' : 'pointer',
              fontFamily: 'var(--fb)', fontSize: 12,
              color: i === crumbs.length - 1 ? 'var(--primary)' : 'var(--mid)',
              fontWeight: i === crumbs.length - 1 ? 600 : 400,
              padding: 0,
            }}
          >{c.label}</button>
        </React.Fragment>
      ))}
    </div>
  )
}

// ── Employee profile card ─────────────────────────────────────────────────────

function EmployeeProfile({ emp }: { emp: EmployeeRow }) {
  const impactColor = emp.impact_score >= 75 ? 'var(--status-green)' : emp.impact_score >= 50 ? 'var(--gold)' : 'var(--mid)'
  const attrRisk    = Math.round(emp.attrition_risk * 100)
  const attrColor   = attrRisk >= 70 ? 'var(--status-red)' : attrRisk >= 40 ? 'var(--status-orange)' : 'var(--status-green)'

  const row = (k: string, v: string) => (
    <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--primary-10)' }}>
      <span style={{ fontFamily: 'var(--fb)', fontSize: 11, letterSpacing: '1px', textTransform: 'uppercase', color: 'var(--mid)' }}>{k}</span>
      <span style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--dark)', fontWeight: 500 }}>{v}</span>
    </div>
  )

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
      {/* Identity */}
      <div style={{ backgroundColor: 'var(--white)', borderRadius: 'var(--radius-md)', boxShadow: 'var(--shadow-card)', padding: 28 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 24 }}>
          <div style={{
            width: 56, height: 56, borderRadius: '50%',
            backgroundColor: 'var(--primary)', display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 700, color: '#fff',
          }}>
            {emp.full_name.split(' ').map(n => n[0]).join('').slice(0, 2)}
          </div>
          <div>
            <div style={{ fontFamily: 'var(--fd)', fontSize: 20, fontWeight: 600, color: 'var(--primary)' }}>{emp.full_name}</div>
            <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)' }}>{emp.role_title}</div>
            {emp.is_nexus && (
              <span style={{
                fontFamily: 'var(--fb)', fontSize: 8, letterSpacing: '1.5px', textTransform: 'uppercase',
                color: 'var(--gold)', border: '1px solid var(--gold)', borderRadius: 'var(--radius-pill)',
                padding: '2px 8px', marginTop: 4, display: 'inline-block',
              }}>Organizational Nexus</span>
            )}
          </div>
        </div>
        {row('Department',   emp.department)}
        {row('Team',         emp.team_name)}
        {row('Employee ID',  emp.employee_id)}
        {row('Top Skill',    emp.top_skill)}
        {row('Annual Salary', `$${emp.annual_salary.toLocaleString()}`)}
      </div>

      {/* Scores */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* Impact */}
        <div style={{ backgroundColor: 'var(--white)', borderRadius: 'var(--radius-md)', boxShadow: 'var(--shadow-card)', padding: 24 }}>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--mid)', marginBottom: 6 }}>Impact Score</div>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8 }}>
            <div style={{ fontFamily: 'var(--fd)', fontSize: 48, fontWeight: 700, color: impactColor, lineHeight: 1 }}>{emp.impact_score.toFixed(0)}</div>
            <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)', marginBottom: 6 }}>/100</div>
          </div>
          <div style={{ marginTop: 12, height: 6, backgroundColor: 'var(--primary-10)', borderRadius: 3 }}>
            <div style={{ height: '100%', borderRadius: 3, backgroundColor: impactColor, width: `${emp.impact_score}%` }} />
          </div>
        </div>

        {/* Attrition risk */}
        <div style={{ backgroundColor: 'var(--white)', borderRadius: 'var(--radius-md)', boxShadow: 'var(--shadow-card)', padding: 24 }}>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--mid)', marginBottom: 6 }}>Attrition Risk</div>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8 }}>
            <div style={{ fontFamily: 'var(--fd)', fontSize: 48, fontWeight: 700, color: attrColor, lineHeight: 1 }}>{attrRisk}%</div>
          </div>
          <div style={{ marginTop: 12, height: 6, backgroundColor: 'var(--primary-10)', borderRadius: 3 }}>
            <div style={{ height: '100%', borderRadius: 3, backgroundColor: attrColor, width: `${attrRisk}%` }} />
          </div>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', marginTop: 8 }}>
            Probability of voluntary departure within 12 months
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Department view ───────────────────────────────────────────────────────────

function DepartmentView({ dept, employees, onEmployee }: {
  dept: string
  employees: EmployeeRow[]
  onEmployee: (emp: EmployeeRow) => void
}) {
  const avgImpact = employees.reduce((s, e) => s + e.impact_score, 0) / employees.length
  const totalSalary = employees.reduce((s, e) => s + e.annual_salary, 0)
  const nexusCount = employees.filter(e => e.is_nexus).length

  return (
    <div>
      {/* Dept stats */}
      <div style={{ display: 'flex', gap: 20, marginBottom: 28 }}>
        {[
          { val: String(employees.length), cap: 'Headcount' },
          { val: avgImpact.toFixed(1), cap: 'Avg Impact' },
          { val: String(nexusCount), cap: 'Nexus Employees' },
          { val: `$${(totalSalary / 1e6).toFixed(2)}M`, cap: 'Total Payroll' },
        ].map(({ val, cap }) => (
          <div key={cap} style={{
            flex: 1, backgroundColor: 'var(--white)', borderRadius: 'var(--radius-md)',
            boxShadow: 'var(--shadow-card)', padding: '18px 20px',
            borderLeft: '3px solid var(--gold)',
          }}>
            <div style={{ fontFamily: 'var(--fd)', fontSize: 26, fontWeight: 700, color: 'var(--primary)' }}>{val}</div>
            <div style={{ fontFamily: 'var(--fb)', fontSize: 10, letterSpacing: '1.5px', textTransform: 'uppercase', color: 'var(--mid)' }}>{cap}</div>
          </div>
        ))}
      </div>

      {/* Employee list */}
      <div style={{ backgroundColor: 'var(--white)', borderRadius: 'var(--radius-md)', boxShadow: 'var(--shadow-card)', overflow: 'hidden' }}>
        <div style={{ padding: '18px 24px', borderBottom: '1px solid var(--primary-10)', fontFamily: 'var(--fd)', fontSize: 17, fontWeight: 600, color: 'var(--primary)' }}>
          {dept} — Team Members
        </div>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ backgroundColor: 'var(--light)' }}>
              {['Name', 'Role', 'Team', 'Impact', 'Attrition Risk'].map(h => (
                <th key={h} style={{ padding: '9px 16px', fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: 'var(--mid)', textAlign: 'left', fontWeight: 600 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {employees.map(emp => (
              <tr
                key={emp.employee_id}
                onClick={() => onEmployee(emp)}
                style={{ borderBottom: '1px solid var(--primary-10)', cursor: 'pointer' }}
                onMouseEnter={e => (e.currentTarget.style.backgroundColor = 'var(--light)')}
                onMouseLeave={e => (e.currentTarget.style.backgroundColor = 'transparent')}
              >
                <td style={{ padding: '11px 16px', fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--dark)', fontWeight: 500 }}>
                  {emp.full_name}
                  {emp.is_nexus && <span style={{ marginLeft: 6, fontFamily: 'var(--fb)', fontSize: 8, color: 'var(--gold)', border: '1px solid var(--gold)', borderRadius: 'var(--radius-pill)', padding: '1px 6px' }}>Nexus</span>}
                </td>
                <td style={{ padding: '11px 16px', fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)' }}>{emp.role_title}</td>
                <td style={{ padding: '11px 16px', fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)' }}>{emp.team_name}</td>
                <td style={{ padding: '11px 16px' }}>
                  <span style={{ fontFamily: 'var(--fd)', fontSize: 14, fontWeight: 700, color: emp.impact_score >= 75 ? 'var(--status-green)' : emp.impact_score >= 50 ? 'var(--gold)' : 'var(--mid)' }}>
                    {emp.impact_score.toFixed(0)}
                  </span>
                </td>
                <td style={{ padding: '11px 16px' }}>
                  <span style={{ fontFamily: 'var(--fb)', fontSize: 12, color: emp.attrition_risk >= 0.7 ? 'var(--status-red)' : emp.attrition_risk >= 0.4 ? 'var(--status-orange)' : 'var(--status-green)' }}>
                    {Math.round(emp.attrition_risk * 100)}%
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Org view ──────────────────────────────────────────────────────────────────

function OrgView({ data, onDept }: { data: DashboardData; onDept: (dept: string) => void }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 18 }}>
      {data.dept_summary.map(dept => (
        <button
          key={dept.department}
          onClick={() => onDept(dept.department)}
          style={{
            backgroundColor: 'var(--white)', borderRadius: 'var(--radius-md)',
            boxShadow: 'var(--shadow-card)', padding: '22px 24px',
            border: '1px solid var(--primary-10)', cursor: 'pointer', textAlign: 'left',
            transition: 'box-shadow 0.15s',
          }}
          onMouseEnter={e => ((e.currentTarget as HTMLElement).style.boxShadow = '0 4px 16px rgba(0,51,102,0.14)')}
          onMouseLeave={e => ((e.currentTarget as HTMLElement).style.boxShadow = 'var(--shadow-card)')}
        >
          <div style={{ fontFamily: 'var(--fd)', fontSize: 17, fontWeight: 600, color: 'var(--primary)', marginBottom: 4 }}>{dept.department}</div>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', marginBottom: 16 }}>{dept.headcount} employees</div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <div>
              <div style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 700, color: 'var(--primary)' }}>{dept.avg_impact.toFixed(0)}</div>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: 'var(--mid)' }}>Avg Impact</div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 700, color: dept.fragility_avg >= 0.7 ? 'var(--status-red)' : dept.fragility_avg >= 0.4 ? 'var(--status-orange)' : 'var(--status-green)' }}>
                {(dept.fragility_avg * 100).toFixed(0)}%
              </div>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: 'var(--mid)' }}>Fragility</div>
            </div>
          </div>
        </button>
      ))}
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function DrillDownPage() {
  const { scenario, size, enabled: demo } = useDemoStore()

  const [data,    setData]    = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState<string | null>(null)

  const [view,         setView]    = useState<View>('org')
  const [activeDept,   setDept]    = useState<string | null>(null)
  const [activeEmp,    setEmp]     = useState<EmployeeRow | null>(null)
  const [crumbs,       setCrumbs]  = useState<Crumb[]>([{ label: 'Organization', view: 'org' }])

  useEffect(() => {
    api.dashboard.data(scenario, size, demo)
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [scenario, size, demo])

  const goOrg = () => { setView('org'); setDept(null); setEmp(null); setCrumbs([{ label: 'Organization', view: 'org' }]) }
  const goDept = (dept: string) => { setView('department'); setDept(dept); setEmp(null); setCrumbs([{ label: 'Organization', view: 'org' }, { label: dept, view: 'department' }]) }
  const goEmp  = (emp: EmployeeRow) => { setView('employee'); setEmp(emp); setCrumbs([{ label: 'Organization', view: 'org' }, { label: activeDept!, view: 'department' }, { label: emp.full_name, view: 'employee' }]) }

  const jumpTo = (i: number) => {
    const c = crumbs[i]
    if (c.view === 'org')        goOrg()
    else if (c.view === 'department') { setView('department'); setCrumbs(crumbs.slice(0, i + 1)) }
  }

  const deptEmployees = data ? data.employee_table.filter(e => e.department === activeDept) : []

  return (
    <div>
      {/* Hero */}
      <div style={{ background: 'var(--primary)', paddingTop: 48, paddingBottom: 48, paddingLeft: 48, paddingRight: 48 }}>
        <div style={{ maxWidth: 'var(--max-width-dashboard)', margin: '0 auto' }}>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '3px', textTransform: 'uppercase', color: 'var(--gold)', marginBottom: 10 }}>
            Hierarchical Exploration
          </div>
          <h1 style={{ fontFamily: 'var(--fd)', fontSize: 38, fontWeight: 600, fontStyle: 'italic', color: '#fff', margin: 0 }}>
            Org Drill-Down
          </h1>
        </div>
      </div>

      <div style={{ maxWidth: 'var(--max-width-dashboard)', margin: '0 auto', padding: '36px 48px' }}>
        {loading && <div style={{ fontFamily: 'var(--fd)', fontSize: 20, color: 'var(--primary)' }}>Loading…</div>}
        {error   && <div style={{ color: 'var(--status-red)', fontFamily: 'var(--fb)', fontSize: 13 }}>{error}</div>}

        {data && (
          <>
            <Breadcrumbs crumbs={crumbs} onJump={jumpTo} />
            {view === 'org'        && <OrgView data={data} onDept={goDept} />}
            {view === 'department' && activeDept && <DepartmentView dept={activeDept} employees={deptEmployees} onEmployee={goEmp} />}
            {view === 'employee'   && activeEmp  && <EmployeeProfile emp={activeEmp} />}
          </>
        )}
      </div>
    </div>
  )
}
