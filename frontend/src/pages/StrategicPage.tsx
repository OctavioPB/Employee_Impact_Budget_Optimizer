import { useState } from 'react'

// ── Types ─────────────────────────────────────────────────────────────────────

interface SkillGap {
  skill:        string
  current:      number
  target:       number
  buildCost:    number
  buyCost:      number
  recommendation: 'build' | 'buy' | 'hybrid'
}

interface Milestone {
  quarter:     string
  action:      string
  headcount:   number
  cost:        number
  completed:   boolean
}

// ── Static demo data ──────────────────────────────────────────────────────────

const SKILL_GAPS: SkillGap[] = [
  { skill: 'Machine Learning',    current: 4,  target: 10, buildCost: 280000,  buyCost: 520000,  recommendation: 'build'  },
  { skill: 'Cloud Architecture',  current: 2,  target: 8,  buildCost: 340000,  buyCost: 480000,  recommendation: 'hybrid' },
  { skill: 'Product Management',  current: 6,  target: 9,  buildCost: 120000,  buyCost: 390000,  recommendation: 'build'  },
  { skill: 'Data Engineering',    current: 3,  target: 10, buildCost: 390000,  buyCost: 560000,  recommendation: 'buy'    },
  { skill: 'UX Research',         current: 1,  target: 4,  buildCost: 180000,  buyCost: 220000,  recommendation: 'buy'    },
]

const ROADMAP: Milestone[] = [
  { quarter: 'Q1 2026', action: 'Launch ML upskilling cohort (12 participants)',    headcount: 0,  cost: 85000,  completed: false },
  { quarter: 'Q1 2026', action: 'Hire 2 Senior Data Engineers',                     headcount: 2,  cost: 280000, completed: false },
  { quarter: 'Q2 2026', action: 'Cloud Architecture certification program',          headcount: 0,  cost: 60000,  completed: false },
  { quarter: 'Q2 2026', action: 'Hire Lead UX Researcher',                           headcount: 1,  cost: 130000, completed: false },
  { quarter: 'Q3 2026', action: 'Internal PM rotation program',                      headcount: 0,  cost: 40000,  completed: false },
  { quarter: 'Q3 2026', action: 'Hire 1 ML Engineer (external)',                     headcount: 1,  cost: 165000, completed: false },
  { quarter: 'Q4 2026', action: 'Skills gap reassessment and model retraining',      headcount: 0,  cost: 15000,  completed: false },
]

const REC_COLORS: Record<string, string> = {
  build:  'var(--primary)',
  buy:    'var(--primary-60)',
  hybrid: 'var(--gold)',
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SkillBar({ current, target }: { current: number; target: number }) {
  const pct = (current / target) * 100
  return (
    <div style={{ position: 'relative', height: 6, backgroundColor: 'var(--primary-10)', borderRadius: 3 }}>
      <div style={{ height: '100%', borderRadius: 3, backgroundColor: 'var(--gold)', width: `${pct}%`, maxWidth: '100%' }} />
    </div>
  )
}

type Tab = 'skills' | 'roadmap' | 'scenarios'

// ── Page ──────────────────────────────────────────────────────────────────────

export default function StrategicPage() {
  const [tab, setTab] = useState<Tab>('skills')

  const tabBtn = (id: Tab, label: string) => {
    const active = tab === id
    return (
      <button
        onClick={() => setTab(id)}
        style={{
          fontFamily:    'var(--fb)',
          fontSize:      10,
          letterSpacing: '2px',
          textTransform: 'uppercase' as const,
          fontWeight:    600,
          padding:       '10px 18px',
          border:        'none',
          borderBottom:  active ? '2px solid var(--gold-light)' : '2px solid transparent',
          backgroundColor: 'transparent',
          color:         active ? 'var(--gold-light)' : 'rgba(255,255,255,0.45)',
          cursor:        'pointer',
          marginBottom:  -1,
        }}
      >{label}</button>
    )
  }

  const totalBuildCost = SKILL_GAPS.filter(g => g.recommendation !== 'buy').reduce((s, g) => s + g.buildCost, 0)
  const totalBuyCost   = SKILL_GAPS.filter(g => g.recommendation !== 'build').reduce((s, g) => s + g.buyCost, 0)
  const totalRoadmap   = ROADMAP.reduce((s, m) => s + m.cost, 0)

  return (
    <div>
      {/* Hero with tabs */}
      <div style={{ background: 'var(--primary)', paddingTop: 48, paddingLeft: 48, paddingRight: 48, paddingBottom: 0, borderBottom: '1px solid rgba(255,255,255,0.12)' }}>
        <div style={{ maxWidth: 'var(--max-width-content)', margin: '0 auto' }}>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '3px', textTransform: 'uppercase', color: 'var(--gold)', marginBottom: 10 }}>
            Strategic Workforce Planning
          </div>
          <h1 style={{ fontFamily: 'var(--fd)', fontSize: 38, fontWeight: 600, fontStyle: 'italic', color: '#fff', margin: '0 0 6px' }}>
            Future State Designer
          </h1>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: 'rgba(255,255,255,0.55)', margin: '0 0 28px' }}>
            Model where your organization needs to go and chart a realistic path there.
          </p>

          {/* Tab bar */}
          <div style={{ display: 'flex', gap: 4, borderBottom: '1px solid rgba(255,255,255,0.12)' }}>
            {tabBtn('skills',    'Skills Gap')}
            {tabBtn('roadmap',   'Transition Roadmap')}
            {tabBtn('scenarios', 'Strategy Scenarios')}
          </div>
        </div>
      </div>

      <div style={{ maxWidth: 'var(--max-width-content)', margin: '0 auto', padding: '36px 48px' }}>

        {/* ── Skills gap tab ─────────────────────────────────────────────── */}
        {tab === 'skills' && (
          <>
            {/* Summary strip */}
            <div style={{ display: 'flex', gap: 20, marginBottom: 28 }}>
              {[
                { val: String(SKILL_GAPS.length), cap: 'Skill Gaps Identified' },
                { val: `$${(totalBuildCost / 1e6).toFixed(2)}M`, cap: 'Est. Build Cost' },
                { val: `$${(totalBuyCost / 1e6).toFixed(2)}M`, cap: 'Est. Buy Cost' },
              ].map(({ val, cap }) => (
                <div key={cap} style={{ flex: 1, backgroundColor: 'var(--white)', borderRadius: 'var(--radius-md)', boxShadow: 'var(--shadow-card)', padding: '18px 20px', borderLeft: '3px solid var(--gold)' }}>
                  <div style={{ fontFamily: 'var(--fd)', fontSize: 26, fontWeight: 700, color: 'var(--primary)' }}>{val}</div>
                  <div style={{ fontFamily: 'var(--fb)', fontSize: 10, letterSpacing: '1.5px', textTransform: 'uppercase', color: 'var(--mid)' }}>{cap}</div>
                </div>
              ))}
            </div>

            {/* Skills table */}
            <div style={{ backgroundColor: 'var(--white)', borderRadius: 'var(--radius-md)', boxShadow: 'var(--shadow-card)', overflow: 'hidden' }}>
              <div style={{ padding: '18px 24px', borderBottom: '1px solid var(--primary-10)' }}>
                <div style={{ fontFamily: 'var(--fd)', fontSize: 18, fontWeight: 600, color: 'var(--primary)' }}>Build vs Buy Analysis</div>
              </div>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ backgroundColor: 'var(--light)' }}>
                    {['Skill', 'Coverage (Current → Target)', 'Build Cost', 'Buy Cost', 'Recommendation'].map(h => (
                      <th key={h} style={{ padding: '10px 16px', fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: 'var(--mid)', textAlign: 'left', fontWeight: 600 }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {SKILL_GAPS.map(gap => (
                    <tr key={gap.skill} style={{ borderBottom: '1px solid var(--primary-10)' }}>
                      <td style={{ padding: '14px 16px', fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--dark)', fontWeight: 500 }}>{gap.skill}</td>
                      <td style={{ padding: '14px 16px', minWidth: 200 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                          <span style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)' }}>{gap.current} FTEs</span>
                          <span style={{ color: 'var(--mid)' }}>→</span>
                          <span style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--primary)', fontWeight: 600 }}>{gap.target} FTEs</span>
                        </div>
                        <SkillBar current={gap.current} target={gap.target} />
                      </td>
                      <td style={{ padding: '14px 16px', fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--dark)' }}>${gap.buildCost.toLocaleString()}</td>
                      <td style={{ padding: '14px 16px', fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--dark)' }}>${gap.buyCost.toLocaleString()}</td>
                      <td style={{ padding: '14px 16px' }}>
                        <span style={{
                          fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase',
                          fontWeight: 700, padding: '3px 10px', borderRadius: 'var(--radius-pill)',
                          backgroundColor: `${REC_COLORS[gap.recommendation]}18`,
                          color: REC_COLORS[gap.recommendation],
                        }}>{gap.recommendation}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}

        {/* ── Roadmap tab ────────────────────────────────────────────────── */}
        {tab === 'roadmap' && (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
              <div>
                <div style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 600, color: 'var(--primary)', marginBottom: 4 }}>12-Month Transition Roadmap</div>
                <div style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)' }}>Data-driven milestones for closing identified skill gaps</div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontFamily: 'var(--fd)', fontSize: 26, fontWeight: 700, color: 'var(--primary)' }}>${(totalRoadmap / 1e6).toFixed(2)}M</div>
                <div style={{ fontFamily: 'var(--fb)', fontSize: 10, letterSpacing: '1.5px', textTransform: 'uppercase', color: 'var(--mid)' }}>Total Investment</div>
              </div>
            </div>

            {['Q1 2026', 'Q2 2026', 'Q3 2026', 'Q4 2026'].map(quarter => {
              const qMilestones = ROADMAP.filter(m => m.quarter === quarter)
              if (!qMilestones.length) return null
              return (
                <div key={quarter} style={{ marginBottom: 28 }}>
                  <div style={{ fontFamily: 'var(--fb)', fontSize: 10, letterSpacing: '2.5px', textTransform: 'uppercase', color: 'var(--gold)', marginBottom: 12, fontWeight: 700 }}>{quarter}</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    {qMilestones.map((m, i) => (
                      <div key={i} style={{
                        backgroundColor: 'var(--white)', borderRadius: 'var(--radius-md)',
                        boxShadow: 'var(--shadow-card)', padding: '16px 20px',
                        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                        borderLeft: `3px solid ${m.headcount > 0 ? 'var(--primary)' : 'var(--gold)'}`,
                      }}>
                        <div>
                          <div style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--dark)', fontWeight: 500 }}>{m.action}</div>
                          {m.headcount > 0 && (
                            <div style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'var(--mid)', marginTop: 2 }}>+{m.headcount} headcount</div>
                          )}
                        </div>
                        <div style={{ textAlign: 'right', flexShrink: 0, marginLeft: 24 }}>
                          <div style={{ fontFamily: 'var(--fd)', fontSize: 16, fontWeight: 700, color: 'var(--primary)' }}>${m.cost.toLocaleString()}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )
            })}
          </>
        )}

        {/* ── Scenarios tab ──────────────────────────────────────────────── */}
        {tab === 'scenarios' && (
          <>
            <div style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 600, color: 'var(--primary)', marginBottom: 6 }}>Strategy Comparison</div>
            <div style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)', marginBottom: 28 }}>
              Three strategic postures — weighted against your organizational priorities.
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 20 }}>
              {[
                {
                  name:   'Optimize & Retain',
                  desc:   'Maximize retention of current talent through upskilling, compensation adjustments, and engagement programs.',
                  impact: 82, speed: 55, cost: 65, risk: 30,
                  rec:    true,
                },
                {
                  name:   'Selective Acquisition',
                  desc:   'Hire targeted external talent for critical gaps while maintaining the core team structure.',
                  impact: 75, speed: 80, cost: 45, risk: 50,
                  rec:    false,
                },
                {
                  name:   'Structural Redesign',
                  desc:   'Restructure teams around capabilities rather than legacy org charts, with phased talent adjustment.',
                  impact: 90, speed: 30, cost: 35, risk: 70,
                  rec:    false,
                },
              ].map(s => (
                <div key={s.name} style={{
                  backgroundColor: 'var(--white)', borderRadius: 'var(--radius-md)',
                  boxShadow: s.rec ? '0 0 0 2px var(--gold), var(--shadow-card)' : 'var(--shadow-card)',
                  padding: '24px',
                }}>
                  {s.rec && (
                    <div style={{ fontFamily: 'var(--fb)', fontSize: 8, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--gold)', fontWeight: 700, marginBottom: 8 }}>Recommended</div>
                  )}
                  <div style={{ fontFamily: 'var(--fd)', fontSize: 17, fontWeight: 600, color: 'var(--primary)', marginBottom: 8 }}>{s.name}</div>
                  <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)', lineHeight: 1.6, marginBottom: 20 }}>{s.desc}</div>

                  {[
                    { label: 'Impact Score',        val: s.impact, color: 'var(--primary)'    },
                    { label: 'Implementation Speed', val: s.speed, color: 'var(--gold)'      },
                    { label: 'Cost Efficiency',      val: s.cost,  color: 'var(--primary-60)' },
                    { label: 'Risk Level',           val: s.risk,  color: s.risk > 60 ? 'var(--status-red)' : 'var(--status-orange)' },
                  ].map(({ label, val, color }) => (
                    <div key={label} style={{ marginBottom: 12 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                        <span style={{ fontFamily: 'var(--fb)', fontSize: 10, letterSpacing: '1px', textTransform: 'uppercase', color: 'var(--mid)' }}>{label}</span>
                        <span style={{ fontFamily: 'var(--fd)', fontSize: 14, fontWeight: 700, color }}>{val}</span>
                      </div>
                      <div style={{ height: 4, backgroundColor: 'var(--primary-10)', borderRadius: 2 }}>
                        <div style={{ height: '100%', borderRadius: 2, backgroundColor: color, width: `${val}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              ))}
            </div>

            <div style={{ marginTop: 20, fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', textAlign: 'center' }}>
              Scores are calculated from weighted multi-criteria analysis. Adjust priority weights in Admin → Strategy Settings.
            </div>
          </>
        )}
      </div>
    </div>
  )
}
