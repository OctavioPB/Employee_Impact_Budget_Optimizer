import React, { useState, useCallback, useRef } from 'react'
import { api, SimulationResult, SimulationEmployee } from '../services/api'
import { useDemoStore } from '../stores/demoStore'

// ── Sub-components ────────────────────────────────────────────────────────────

const sectionTitle: React.CSSProperties = {
  fontFamily:    'var(--fd)',
  fontSize:      22,
  fontWeight:    600,
  color:         'var(--primary)',
  marginBottom:  4,
}

const label: React.CSSProperties = {
  fontFamily:   'var(--fb)',
  fontSize:     10,
  letterSpacing:'2px',
  textTransform:'uppercase' as const,
  color:        'var(--mid)',
  marginBottom: 6,
  display:      'block',
}

function StatBox({ value, caption, accent }: { value: string; caption: string; accent?: string }) {
  return (
    <div style={{
      borderLeft:  `3px solid ${accent ?? 'var(--gold)'}`,
      paddingLeft: 16,
      flex:        1,
    }}>
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
            marginLeft: 6,
            fontFamily: 'var(--fb)', fontSize: 8, letterSpacing: '1.5px',
            textTransform: 'uppercase', color: 'var(--gold)',
            border: '1px solid var(--gold)', borderRadius: 'var(--radius-pill)',
            padding: '1px 6px',
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

// ── Main page ─────────────────────────────────────────────────────────────────

export default function SimulationPage() {
  const { scenario, size } = useDemoStore()

  const [budgetPct, setBudgetPct]     = useState(80)
  const [leadership, setLeadership]   = useState(true)
  const [skills, setSkills]           = useState(true)
  const [forceRetain, setForceRetain] = useState('')
  const [exclude, setExclude]         = useState('')

  const [result,  setResult]  = useState<SimulationResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState<string | null>(null)

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const runSimulation = useCallback(async (pct: number) => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.simulation.run({
        scenario,
        size,
        budget_pct:           pct,
        force_retain:         forceRetain.split(',').map(s => s.trim()).filter(Boolean),
        exclude:              exclude.split(',').map(s => s.trim()).filter(Boolean),
        leadership_constraint: leadership,
        skills_constraint:    skills,
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

  // ── Hero ──────────────────────────────────────────────────────────────────

  return (
    <div>
      {/* Hero */}
      <div style={{
        background:   'var(--primary)',
        paddingTop:   48,
        paddingBottom:48,
        paddingLeft:  48,
        paddingRight: 48,
      }}>
        <div style={{ maxWidth: 'var(--max-width-content)', margin: '0 auto' }}>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '3px', textTransform: 'uppercase', color: 'var(--gold)', marginBottom: 10 }}>
            Budget Simulation Engine
          </div>
          <h1 style={{ fontFamily: 'var(--fd)', fontSize: 38, fontWeight: 600, fontStyle: 'italic', color: '#fff', margin: '0 0 10px' }}>
            Optimization Simulator
          </h1>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: 'rgba(255,255,255,0.55)', margin: 0, maxWidth: 520 }}>
            Adjust budget targets and constraints to see which talent the model recommends retaining. Every decision is yours.
          </p>
        </div>
      </div>

      {/* Content */}
      <div style={{ maxWidth: 'var(--max-width-content)', margin: '0 auto', padding: '40px 48px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: 32 }}>

          {/* Controls panel */}
          <div style={{
            backgroundColor: 'var(--white)',
            borderRadius:    'var(--radius-md)',
            boxShadow:       'var(--shadow-card)',
            padding:         28,
            height:          'fit-content',
            position:        'sticky',
            top:             68,
          }}>
            <div style={{ ...sectionTitle, fontSize: 16, marginBottom: 24 }}>Simulation Controls</div>

            {/* Budget slider */}
            <div style={{ marginBottom: 24 }}>
              <span style={label}>Available Budget</span>
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
              <div style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'var(--mid)', marginTop: 4 }}>
                of current total spend
              </div>
            </div>

            {/* Constraints */}
            <div style={{ marginBottom: 20 }}>
              <span style={label}>Constraints</span>
              {[
                { id: 'leadership', label: 'Leadership coverage',      val: leadership, set: setLeadership },
                { id: 'skills',     label: 'Critical skills coverage', val: skills,     set: setSkills },
              ].map(({ id, label: lbl, val, set }) => (
                <label key={id} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10, cursor: 'pointer' }}>
                  <input type="checkbox" checked={val} onChange={e => set(e.target.checked)} style={{ accentColor: 'var(--gold)', width: 15, height: 15 }} />
                  <span style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--dark)' }}>{lbl}</span>
                </label>
              ))}
            </div>

            {/* Force retain */}
            <div style={{ marginBottom: 16 }}>
              <span style={label}>Force Retain (IDs, comma-separated)</span>
              <input
                type="text"
                value={forceRetain}
                onChange={e => setForceRetain(e.target.value)}
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
              <span style={label}>Exclude from Simulation (IDs)</span>
              <input
                type="text"
                value={exclude}
                onChange={e => setExclude(e.target.value)}
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
                width:           '100%',
                fontFamily:      'var(--fb)',
                fontSize:        10,
                letterSpacing:   '2px',
                textTransform:   'uppercase',
                fontWeight:      700,
                backgroundColor: loading ? 'var(--mid)' : 'var(--gold)',
                color:           '#fff',
                border:          'none',
                borderRadius:    'var(--radius-sm)',
                padding:         '12px 0',
                cursor:          loading ? 'not-allowed' : 'pointer',
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
              <div style={{
                backgroundColor: 'var(--white)', borderRadius: 'var(--radius-md)',
                boxShadow: 'var(--shadow-card)', padding: 48, textAlign: 'center',
              }}>
                <div style={{ fontFamily: 'var(--fd)', fontSize: 20, color: 'var(--primary)', marginBottom: 8 }}>Set constraints and run the simulation</div>
                <div style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)' }}>Adjust the budget slider and click Run Simulation to see results.</div>
              </div>
            )}

            {loading && (
              <div style={{
                backgroundColor: 'var(--white)', borderRadius: 'var(--radius-md)',
                boxShadow: 'var(--shadow-card)', padding: 48, textAlign: 'center',
              }}>
                <div style={{ fontFamily: 'var(--fd)', fontSize: 20, color: 'var(--primary)' }}>Running optimization…</div>
              </div>
            )}

            {result && !loading && (
              <>
                {/* Feasibility alert */}
                {!result.feasible && (
                  <div style={{ backgroundColor: 'rgba(240,112,32,0.08)', border: '1px solid rgba(240,112,32,0.25)', borderRadius: 'var(--radius-md)', padding: '16px 20px', marginBottom: 20 }}>
                    <div style={{ fontFamily: 'var(--fb)', fontSize: 11, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--status-orange)', marginBottom: 4 }}>Infeasible Scenario</div>
                    <div style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--dark)' }}>{result.infeasibility_reason}</div>
                  </div>
                )}

                {/* Stats strip */}
                <div style={{
                  backgroundColor: 'var(--white)', borderRadius: 'var(--radius-md)',
                  boxShadow: 'var(--shadow-card)', padding: '24px 28px',
                  display: 'flex', gap: 28, marginBottom: 20,
                }}>
                  <StatBox value={String(result.retained_count)}    caption="Retained"       accent="var(--status-green)" />
                  <StatBox value={String(result.at_risk_count)}     caption="Not Retained"   accent="var(--mid)" />
                  <StatBox value={`${result.budget_used_pct.toFixed(1)}%`} caption="Budget Used" accent="var(--gold)" />
                  <StatBox value={result.total_impact.toFixed(0)}   caption="Total Impact"   accent="var(--status-purple)" />
                </div>

                {/* Cost strip */}
                <div style={{
                  backgroundColor: 'var(--white)', borderRadius: 'var(--radius-md)',
                  boxShadow: 'var(--shadow-card)', padding: '24px 28px',
                  display: 'flex', gap: 28, marginBottom: 24,
                }}>
                  <StatBox value={`$${(result.total_retained_cost / 1e6).toFixed(2)}M`} caption="Retained Payroll" />
                  <StatBox value={`$${(result.total_at_risk_cost / 1e6).toFixed(2)}M`} caption="Not-Retained Payroll" accent="var(--mid)" />
                </div>

                {/* Employee table */}
                <div style={{ backgroundColor: 'var(--white)', borderRadius: 'var(--radius-md)', boxShadow: 'var(--shadow-card)', overflow: 'hidden' }}>
                  <div style={{ padding: '20px 24px 0', borderBottom: '1px solid var(--primary-10)' }}>
                    <div style={{ ...sectionTitle, fontSize: 16, marginBottom: 12 }}>Simulation Results</div>
                  </div>
                  <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                      <thead>
                        <tr style={{ backgroundColor: 'var(--light)' }}>
                          {['Name', 'Department', 'Role', 'Annual Salary', 'Impact', 'Status'].map(h => (
                            <th key={h} style={{ padding: '10px 12px', fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: 'var(--mid)', textAlign: h === 'Annual Salary' ? 'right' : 'left', fontWeight: 600 }}>{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {result.employees.sort((a, b) => (b.retained ? 1 : 0) - (a.retained ? 1 : 0)).map(emp => (
                          <EmployeeRow key={emp.employee_id} emp={emp} />
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
