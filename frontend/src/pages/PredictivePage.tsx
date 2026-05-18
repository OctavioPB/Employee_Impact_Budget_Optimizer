import { useState, useEffect } from 'react'
import { api, AttritionData, AttritionEmployee } from '../services/api'
import { useDemoStore } from '../stores/demoStore'

const CAT_COLORS: Record<string, string> = {
  Low:      'var(--status-green)',
  Moderate: 'var(--gold)',
  High:     'var(--status-orange)',
  Critical: 'var(--status-red)',
}

function RiskPill({ category }: { category: AttritionEmployee['risk_category'] }) {
  return (
    <span style={{
      fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase',
      fontWeight: 700, padding: '3px 10px', borderRadius: 'var(--radius-pill)',
      backgroundColor: `${CAT_COLORS[category]}18`,
      color: CAT_COLORS[category],
    }}>{category}</span>
  )
}

function RiskBar({ value }: { value: number }) {
  const color = value >= 0.7 ? 'var(--status-red)' : value >= 0.4 ? 'var(--status-orange)' : 'var(--status-green)'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ flex: 1, height: 5, backgroundColor: 'var(--primary-10)', borderRadius: 3 }}>
        <div style={{ height: '100%', borderRadius: 3, backgroundColor: color, width: `${value * 100}%` }} />
      </div>
      <span style={{ fontFamily: 'var(--fb)', fontSize: 11, color, width: 34, textAlign: 'right' }}>
        {Math.round(value * 100)}%
      </span>
    </div>
  )
}

export default function PredictivePage() {
  const { scenario, size, enabled: demo } = useDemoStore()

  const [data,    setData]    = useState<AttritionData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState<string | null>(null)
  const [search,  setSearch]  = useState('')
  const [catFilter, setCat]   = useState<string>('All')

  useEffect(() => {
    setLoading(true)
    api.predictive.attrition(scenario, size, demo)
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [scenario, size, demo])

  const CATS = ['All', 'Critical', 'High', 'Moderate', 'Low']

  const filtered = data
    ? data.employees
        .filter(e => catFilter === 'All' || e.risk_category === catFilter)
        .filter(e =>
          search === '' ||
          e.full_name.toLowerCase().includes(search.toLowerCase()) ||
          e.department.toLowerCase().includes(search.toLowerCase())
        )
        .sort((a, b) => b.attrition_risk - a.attrition_risk)
    : []

  return (
    <div>
      {/* Hero */}
      <div style={{ background: 'var(--primary)', paddingTop: 48, paddingBottom: 48, paddingLeft: 48, paddingRight: 48 }}>
        <div style={{ maxWidth: 'var(--max-width-content)', margin: '0 auto' }}>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '3px', textTransform: 'uppercase', color: 'var(--gold)', marginBottom: 10 }}>
            Predictive Analytics
          </div>
          <h1 style={{ fontFamily: 'var(--fd)', fontSize: 38, fontWeight: 600, fontStyle: 'italic', color: '#fff', margin: '0 0 10px' }}>
            Retention Risk Dashboard
          </h1>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: 'rgba(255,255,255,0.55)', margin: 0 }}>
            Early signals for voluntary departures — framed as retention opportunities.
          </p>

          {/* Summary stats in hero */}
          {data && (
            <div style={{ display: 'flex', gap: 32, marginTop: 32 }}>
              {[
                { val: String(data.high_risk_count),     label: 'High Risk',     color: 'var(--status-orange)' },
                { val: String(data.critical_risk_count), label: 'Critical Risk', color: 'var(--status-red)' },
                { val: `${(data.avg_risk * 100).toFixed(1)}%`, label: 'Avg Risk Score', color: 'var(--gold-light)' },
              ].map(({ val, label, color }) => (
                <div key={label} style={{ borderLeft: `3px solid ${color}`, paddingLeft: 14 }}>
                  <div style={{ fontFamily: 'var(--fd)', fontSize: 30, fontWeight: 700, color }}>{val}</div>
                  <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '2px', textTransform: 'uppercase', color: 'rgba(255,255,255,0.45)' }}>{label}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div style={{ maxWidth: 'var(--max-width-content)', margin: '0 auto', padding: '36px 48px' }}>
        {loading && <div style={{ fontFamily: 'var(--fd)', fontSize: 20, color: 'var(--primary)' }}>Analyzing retention signals…</div>}
        {error   && <div style={{ color: 'var(--status-red)', fontFamily: 'var(--fb)', fontSize: 13 }}>{error}</div>}

        {data && (
          <>
            {/* Filters */}
            <div style={{ display: 'flex', gap: 12, marginBottom: 24, alignItems: 'center', flexWrap: 'wrap' }}>
              <input
                type="text"
                placeholder="Search name or department…"
                value={search}
                onChange={e => setSearch(e.target.value)}
                style={{
                  fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--dark)',
                  border: '1px solid var(--primary-10)', borderRadius: 'var(--radius-sm)',
                  padding: '8px 14px', backgroundColor: 'var(--white)',
                  outline: 'none', minWidth: 240,
                }}
              />
              <div style={{ display: 'flex', gap: 6 }}>
                {CATS.map(cat => (
                  <button
                    key={cat}
                    onClick={() => setCat(cat)}
                    style={{
                      fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase',
                      fontWeight: 600, padding: '5px 12px', borderRadius: 'var(--radius-pill)',
                      border: 'none', cursor: 'pointer',
                      backgroundColor: catFilter === cat ? 'var(--primary)' : 'var(--white)',
                      color:           catFilter === cat ? '#fff' : 'var(--mid)',
                      boxShadow:       'var(--shadow-card)',
                    }}
                  >{cat}</button>
                ))}
              </div>
              <span style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', marginLeft: 'auto' }}>
                {filtered.length} employee{filtered.length !== 1 ? 's' : ''}
              </span>
            </div>

            {/* Table */}
            <div style={{ backgroundColor: 'var(--white)', borderRadius: 'var(--radius-md)', boxShadow: 'var(--shadow-card)', overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ backgroundColor: 'var(--light)' }}>
                    {['Name', 'Department', 'Role', 'Risk Level', 'Risk Score', 'Top Driver'].map(h => (
                      <th key={h} style={{ padding: '10px 16px', fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: 'var(--mid)', textAlign: 'left', fontWeight: 600 }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filtered.map(emp => (
                    <tr key={emp.employee_id} style={{ borderBottom: '1px solid var(--primary-10)' }}>
                      <td style={{ padding: '12px 16px', fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--dark)', fontWeight: 500 }}>{emp.full_name}</td>
                      <td style={{ padding: '12px 16px', fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)' }}>{emp.department}</td>
                      <td style={{ padding: '12px 16px', fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)' }}>{emp.role_title}</td>
                      <td style={{ padding: '12px 16px' }}><RiskPill category={emp.risk_category} /></td>
                      <td style={{ padding: '12px 16px', minWidth: 160 }}><RiskBar value={emp.attrition_risk} /></td>
                      <td style={{ padding: '12px 16px', fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--dark)', maxWidth: 200 }}>{emp.top_driver}</td>
                    </tr>
                  ))}
                  {filtered.length === 0 && (
                    <tr>
                      <td colSpan={6} style={{ padding: 36, textAlign: 'center', fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)' }}>
                        No employees match the current filters.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Explainability note */}
            <div style={{
              marginTop: 20, backgroundColor: 'var(--primary-10)', borderRadius: 'var(--radius-md)',
              padding: '14px 20px', display: 'flex', gap: 12, alignItems: 'flex-start',
            }}>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 11, letterSpacing: '1.5px', textTransform: 'uppercase', color: 'var(--primary)', fontWeight: 700, whiteSpace: 'nowrap', marginTop: 1 }}>
                Model Note
              </div>
              <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--primary)', lineHeight: 1.6 }}>
                Attrition scores are calibrated probabilities from a gradient-boosted classifier (SHAP-explainable). "Top Driver" reflects the highest-contributing SHAP feature for each individual. Predictions are updated monthly or on data drift detection. This tool surfaces retention opportunities — all decisions remain with your team.
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
