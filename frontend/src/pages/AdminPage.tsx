import { useState, useEffect } from 'react'
import { api } from '../services/api'

// ── Types ─────────────────────────────────────────────────────────────────────

interface RbacUser {
  id:         string
  name:       string
  email:      string
  role:       string
  department: string
  lastLogin:  string
}

// ── Static demo data ──────────────────────────────────────────────────────────

const ROLES = ['Viewer', 'Analyst', 'Manager', 'Director', 'Executive', 'Admin']

const DEMO_USERS: RbacUser[] = [
  { id: 'u1',  name: 'Sarah Chen',      email: 'schen@corp.com',    role: 'Executive', department: 'All',        lastLogin: '2026-05-18' },
  { id: 'u2',  name: 'Marcus Williams', email: 'mwilliams@corp.com', role: 'Director',  department: 'Engineering', lastLogin: '2026-05-17' },
  { id: 'u3',  name: 'Ana Lima',        email: 'alima@corp.com',    role: 'Manager',   department: 'HR',          lastLogin: '2026-05-18' },
  { id: 'u4',  name: 'David Park',      email: 'dpark@corp.com',    role: 'Analyst',   department: 'Finance',     lastLogin: '2026-05-15' },
  { id: 'u5',  name: 'Fatima Osei',     email: 'fosei@corp.com',    role: 'Viewer',    department: 'Operations',  lastLogin: '2026-05-10' },
]

const ROLE_PERMISSIONS: Record<string, string[]> = {
  Viewer:    ['View dashboards'],
  Analyst:   ['View dashboards', 'Run simulations', 'Create scenarios'],
  Manager:   ['View dashboards', 'Run simulations', 'Create scenarios', 'Override decisions', 'Export data'],
  Director:  ['View dashboards', 'Run simulations', 'Create scenarios', 'Override decisions', 'Export data', 'Strategic planning'],
  Executive: ['View dashboards', 'Run simulations', 'Create scenarios', 'Override decisions', 'Export data', 'Strategic planning', 'Org-wide access'],
  Admin:     ['All permissions', 'User management', 'System configuration', 'Audit logs'],
}

const ROLE_COLORS: Record<string, string> = {
  Viewer:    'var(--mid)',
  Analyst:   'var(--primary-60)',
  Manager:   'var(--gold)',
  Director:  'var(--status-orange)',
  Executive: 'var(--status-purple)',
  Admin:     'var(--status-red)',
}

// ── Sub-components ────────────────────────────────────────────────────────────

type AdminTab = 'health' | 'users' | 'rbac' | 'audit'

function StatusDot({ ok }: { ok: boolean }) {
  return (
    <span style={{
      display: 'inline-block', width: 8, height: 8, borderRadius: '50%',
      backgroundColor: ok ? 'var(--status-green)' : 'var(--status-red)',
      marginRight: 8,
    }} />
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AdminPage() {
  const [tab,     setTab]     = useState<AdminTab>('health')
  const [healthy, setHealthy] = useState<boolean | null>(null)
  const [users,   setUsers]   = useState<RbacUser[]>(DEMO_USERS)
  const [editRole, setEditRole] = useState<Record<string, string>>({})

  useEffect(() => {
    api.health()
      .then(r => setHealthy(r.status === 'ok'))
      .catch(() => setHealthy(false))
  }, [])

  const tabBtn = (id: AdminTab, label: string) => {
    const active = tab === id
    return (
      <button
        onClick={() => setTab(id)}
        style={{
          fontFamily: 'var(--fb)', fontSize: 10, letterSpacing: '2px', textTransform: 'uppercase' as const,
          fontWeight: 600, padding: '10px 18px', border: 'none',
          borderBottom: active ? '2px solid var(--gold-light)' : '2px solid transparent',
          backgroundColor: 'transparent',
          color: active ? 'var(--gold-light)' : 'rgba(255,255,255,0.45)',
          cursor: 'pointer', marginBottom: -1,
        }}
      >{label}</button>
    )
  }

  const applyRoleChange = (userId: string) => {
    const newRole = editRole[userId]
    if (!newRole) return
    setUsers(prev => prev.map(u => u.id === userId ? { ...u, role: newRole } : u))
    setEditRole(prev => { const n = { ...prev }; delete n[userId]; return n })
  }

  return (
    <div>
      {/* Hero with tabs */}
      <div style={{ background: 'var(--primary)', paddingTop: 48, paddingLeft: 48, paddingRight: 48, paddingBottom: 0, borderBottom: '1px solid rgba(255,255,255,0.12)' }}>
        <div style={{ maxWidth: 'var(--max-width-content)', margin: '0 auto' }}>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '3px', textTransform: 'uppercase', color: 'var(--gold)', marginBottom: 10 }}>
            System Administration
          </div>
          <h1 style={{ fontFamily: 'var(--fd)', fontSize: 38, fontWeight: 600, fontStyle: 'italic', color: '#fff', margin: '0 0 24px' }}>
            Admin Console
          </h1>
          <div style={{ display: 'flex', gap: 4, borderBottom: '1px solid rgba(255,255,255,0.12)' }}>
            {tabBtn('health', 'System Health')}
            {tabBtn('users',  'Users')}
            {tabBtn('rbac',   'Permissions')}
            {tabBtn('audit',  'Audit Log')}
          </div>
        </div>
      </div>

      <div style={{ maxWidth: 'var(--max-width-content)', margin: '0 auto', padding: '36px 48px' }}>

        {/* ── Health ──────────────────────────────────────────────────── */}
        {tab === 'health' && (
          <>
            <div style={{ fontFamily: 'var(--fd)', fontSize: 20, fontWeight: 600, color: 'var(--primary)', marginBottom: 20 }}>Service Health</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 16, marginBottom: 28 }}>
              {[
                { name: 'API Backend',       ok: healthy ?? false },
                { name: 'Database',          ok: true  },
                { name: 'Analytics Engine',  ok: true  },
                { name: 'ML Models',         ok: true  },
                { name: 'Notification Queue',ok: true  },
                { name: 'Cache Layer',       ok: false },
              ].map(svc => (
                <div key={svc.name} style={{
                  backgroundColor: 'var(--white)', borderRadius: 'var(--radius-md)',
                  boxShadow: 'var(--shadow-card)', padding: '18px 20px',
                  borderLeft: `3px solid ${svc.ok ? 'var(--status-green)' : 'var(--status-red)'}`,
                }}>
                  <div style={{ fontFamily: 'var(--fb)', fontSize: 13, fontWeight: 500, color: 'var(--dark)', marginBottom: 6 }}>
                    <StatusDot ok={svc.ok} />{svc.name}
                  </div>
                  <div style={{ fontFamily: 'var(--fb)', fontSize: 10, letterSpacing: '1.5px', textTransform: 'uppercase', color: svc.ok ? 'var(--status-green)' : 'var(--status-red)' }}>
                    {svc.ok ? 'Operational' : 'Degraded'}
                  </div>
                </div>
              ))}
            </div>

            <div style={{ backgroundColor: 'var(--white)', borderRadius: 'var(--radius-md)', boxShadow: 'var(--shadow-card)', padding: '24px 28px' }}>
              <div style={{ fontFamily: 'var(--fd)', fontSize: 16, fontWeight: 600, color: 'var(--primary)', marginBottom: 16 }}>Performance Metrics</div>
              {[
                { label: 'API Avg Response Time',    val: '68ms',  target: '<200ms', ok: true },
                { label: 'Dashboard Load Time',      val: '420ms', target: '<2000ms', ok: true },
                { label: 'Simulation Avg Runtime',   val: '1.2s',  target: '<10s',   ok: true },
                { label: 'Model Prediction Latency', val: '85ms',  target: '<500ms', ok: true },
              ].map(m => (
                <div key={m.label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 0', borderBottom: '1px solid var(--primary-10)' }}>
                  <span style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--dark)' }}>{m.label}</span>
                  <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
                    <span style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)' }}>target: {m.target}</span>
                    <span style={{ fontFamily: 'var(--fd)', fontSize: 15, fontWeight: 700, color: m.ok ? 'var(--status-green)' : 'var(--status-red)' }}>{m.val}</span>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {/* ── Users ───────────────────────────────────────────────────── */}
        {tab === 'users' && (
          <div style={{ backgroundColor: 'var(--white)', borderRadius: 'var(--radius-md)', boxShadow: 'var(--shadow-card)', overflow: 'hidden' }}>
            <div style={{ padding: '18px 24px', borderBottom: '1px solid var(--primary-10)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ fontFamily: 'var(--fd)', fontSize: 18, fontWeight: 600, color: 'var(--primary)' }}>User Management</div>
              <span style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)' }}>{users.length} users</span>
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ backgroundColor: 'var(--light)' }}>
                  {['Name', 'Email', 'Role', 'Department', 'Last Login', ''].map(h => (
                    <th key={h} style={{ padding: '10px 16px', fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: 'var(--mid)', textAlign: 'left', fontWeight: 600 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {users.map(u => (
                  <tr key={u.id} style={{ borderBottom: '1px solid var(--primary-10)' }}>
                    <td style={{ padding: '12px 16px', fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--dark)', fontWeight: 500 }}>{u.name}</td>
                    <td style={{ padding: '12px 16px', fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)' }}>{u.email}</td>
                    <td style={{ padding: '12px 16px' }}>
                      <span style={{
                        fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase',
                        fontWeight: 700, padding: '3px 10px', borderRadius: 'var(--radius-pill)',
                        backgroundColor: `${ROLE_COLORS[u.role]}18`, color: ROLE_COLORS[u.role],
                      }}>{u.role}</span>
                    </td>
                    <td style={{ padding: '12px 16px', fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)' }}>{u.department}</td>
                    <td style={{ padding: '12px 16px', fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)' }}>{u.lastLogin}</td>
                    <td style={{ padding: '12px 16px' }}>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                        <select
                          value={editRole[u.id] ?? u.role}
                          onChange={e => setEditRole(prev => ({ ...prev, [u.id]: e.target.value }))}
                          style={{ fontFamily: 'var(--fb)', fontSize: 11, padding: '4px 8px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--primary-10)', color: 'var(--dark)', backgroundColor: 'var(--light)' }}
                        >
                          {ROLES.map(r => <option key={r}>{r}</option>)}
                        </select>
                        {editRole[u.id] && editRole[u.id] !== u.role && (
                          <button
                            onClick={() => applyRoleChange(u.id)}
                            style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1px', textTransform: 'uppercase', padding: '4px 10px', borderRadius: 'var(--radius-sm)', border: 'none', backgroundColor: 'var(--gold)', color: '#fff', cursor: 'pointer', fontWeight: 700 }}
                          >Apply</button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* ── RBAC ────────────────────────────────────────────────────── */}
        {tab === 'rbac' && (
          <>
            <div style={{ fontFamily: 'var(--fd)', fontSize: 20, fontWeight: 600, color: 'var(--primary)', marginBottom: 20 }}>Role Permissions</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {ROLES.map(role => (
                <div key={role} style={{
                  backgroundColor: 'var(--white)', borderRadius: 'var(--radius-md)',
                  boxShadow: 'var(--shadow-card)', padding: '18px 24px',
                  borderLeft: `3px solid ${ROLE_COLORS[role]}`,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                    <div style={{ fontFamily: 'var(--fd)', fontSize: 16, fontWeight: 600, color: 'var(--primary)' }}>{role}</div>
                    <span style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)' }}>
                      {users.filter(u => u.role === role).length} user{users.filter(u => u.role === role).length !== 1 ? 's' : ''}
                    </span>
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                    {ROLE_PERMISSIONS[role].map(p => (
                      <span key={p} style={{
                        fontFamily: 'var(--fb)', fontSize: 10, padding: '3px 10px', borderRadius: 'var(--radius-pill)',
                        backgroundColor: 'var(--primary-10)', color: 'var(--primary)',
                      }}>{p}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {/* ── Audit ───────────────────────────────────────────────────── */}
        {tab === 'audit' && (
          <>
            <div style={{ fontFamily: 'var(--fd)', fontSize: 20, fontWeight: 600, color: 'var(--primary)', marginBottom: 20 }}>Audit Trail</div>
            <div style={{ backgroundColor: 'var(--white)', borderRadius: 'var(--radius-md)', boxShadow: 'var(--shadow-card)', overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ backgroundColor: 'var(--light)' }}>
                    {['Timestamp', 'User', 'Action', 'Details', 'IP'].map(h => (
                      <th key={h} style={{ padding: '10px 16px', fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: 'var(--mid)', textAlign: 'left', fontWeight: 600 }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[
                    { ts: '2026-05-18 14:32', user: 'Sarah Chen',      action: 'Simulation Run',    detail: 'Budget: 80%, Scenario A, Medium',         ip: '10.0.1.12' },
                    { ts: '2026-05-18 13:15', user: 'Marcus Williams',  action: 'Override Applied',  detail: 'Force-retain EMP-042 (Critical project Q3)',ip: '10.0.1.8'  },
                    { ts: '2026-05-18 11:44', user: 'Ana Lima',         action: 'Report Exported',   detail: 'Attrition Risk Report — HR Department',    ip: '10.0.1.22' },
                    { ts: '2026-05-17 16:02', user: 'David Park',       action: 'Dashboard Viewed',  detail: 'Scenario B, Large',                        ip: '10.0.1.5'  },
                    { ts: '2026-05-17 09:30', user: 'System',           action: 'Model Retrained',   detail: 'Attrition model — monthly cycle',           ip: 'internal'  },
                    { ts: '2026-05-16 17:58', user: 'Sarah Chen',       action: 'Role Changed',      detail: 'User dpark@corp.com: Viewer → Analyst',     ip: '10.0.1.12' },
                  ].map((row, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid var(--primary-10)' }}>
                      <td style={{ padding: '11px 16px', fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', whiteSpace: 'nowrap' }}>{row.ts}</td>
                      <td style={{ padding: '11px 16px', fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--dark)', fontWeight: 500 }}>{row.user}</td>
                      <td style={{ padding: '11px 16px' }}>
                        <span style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: 'var(--primary)', backgroundColor: 'var(--primary-10)', borderRadius: 'var(--radius-sm)', padding: '2px 8px' }}>{row.action}</span>
                      </td>
                      <td style={{ padding: '11px 16px', fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--dark)', maxWidth: 300 }}>{row.detail}</td>
                      <td style={{ padding: '11px 16px', fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)' }}>{row.ip}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
