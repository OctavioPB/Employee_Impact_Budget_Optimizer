import { useState, useEffect } from 'react'
import { api, PulseData, PulseSignalDefinition, PulseHeatmapRow, PulseWarningEmployee, PulseTimeline, PulseCohesionRow } from '../services/api'
import { useDemoStore } from '../stores/demoStore'

// ── Palette helpers ────────────────────────────────────────────────────────────

function zscoreColor(z: number, direction: string): string {
  const abs = Math.abs(z)
  if (abs < 0.5) return 'transparent'
  const concerning =
    (direction === 'high' && z > 0) ||
    (direction === 'low'  && z < 0) ||
    (direction === 'both' && abs > 0)
  if (!concerning) return abs < 1 ? 'rgba(39,185,124,0.10)' : 'rgba(39,185,124,0.20)'
  if (abs < 1)  return 'rgba(232,152,33,0.12)'
  if (abs < 1.5) return 'rgba(232,152,33,0.25)'
  if (abs < 2)  return 'rgba(232,152,33,0.45)'
  return 'rgba(224,52,72,0.35)'
}

function zscoreText(z: number, direction: string): string {
  const abs = Math.abs(z)
  if (abs < 0.5) return 'var(--mid)'
  const concerning =
    (direction === 'high' && z > 0) ||
    (direction === 'low'  && z < 0) ||
    (direction === 'both' && abs > 0)
  if (!concerning) return 'var(--status-green)'
  if (abs < 1.5) return 'var(--status-orange)'
  return 'var(--status-red)'
}

function anomalyColor(score: number): string {
  if (score < 0.40) return 'var(--status-green)'
  if (score < 0.60) return 'var(--status-orange)'
  return 'var(--status-red)'
}

function riskDelta(base: number, adjusted: number) {
  const delta = adjusted - base
  if (Math.abs(delta) < 0.01) return null
  return { val: (delta * 100).toFixed(0), up: delta > 0 }
}

// ── Disclaimer banner ──────────────────────────────────────────────────────────

function DisclaimerBanner({ text }: { text: string }) {
  return (
    <div style={{
      backgroundColor: 'rgba(201,168,76,0.08)',
      border:          '1px solid rgba(201,168,76,0.3)',
      borderRadius:    'var(--radius-md)',
      padding:         '10px 18px',
      marginBottom:    24,
      fontFamily:      'var(--fb)',
      fontSize:        11,
      color:           'var(--gold)',
      display:         'flex',
      alignItems:      'flex-start',
      gap:             10,
      lineHeight:      1.6,
    }}>
      <span style={{ fontSize: 14, flexShrink: 0, marginTop: 1 }}>⚠</span>
      {text}
    </div>
  )
}

// ── Summary KPI strip ──────────────────────────────────────────────────────────

function SummaryStrip({ data }: { data: PulseData }) {
  const s = data.summary
  const kpis = [
    { label: 'Employees Monitored', value: s.monitored.toLocaleString() },
    { label: 'Anomaly Alerts',      value: s.anomaly_count.toString(),      accent: s.anomaly_count > 0 },
    { label: 'CUSUM Alerts',        value: s.cusum_alert_count.toString(),   accent: s.cusum_alert_count > 0 },
    { label: 'Avg Anomaly Score',   value: (s.avg_anomaly_score * 100).toFixed(1) + '%' },
    { label: 'Signal Date',         value: s.collection_date },
  ]
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 14, marginBottom: 28 }}>
      {kpis.map(k => (
        <div key={k.label} style={{ backgroundColor: 'var(--white)', borderRadius: 'var(--radius-md)', boxShadow: 'var(--shadow-card)', padding: '16px 20px' }}>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '2px', textTransform: 'uppercase' as const, color: 'var(--mid)', marginBottom: 6 }}>{k.label}</div>
          <div style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 700, color: k.accent ? 'var(--status-orange)' : 'var(--primary)' }}>{k.value}</div>
        </div>
      ))}
    </div>
  )
}

// ── Heatmap tab ────────────────────────────────────────────────────────────────

function HeatmapTab({ rows, defs }: { rows: PulseHeatmapRow[]; defs: PulseSignalDefinition[] }) {
  return (
    <div style={{ backgroundColor: 'var(--white)', borderRadius: 'var(--radius-md)', boxShadow: 'var(--shadow-card)', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ display: 'grid', gridTemplateColumns: `180px repeat(${defs.length}, 1fr)`, borderBottom: '1px solid var(--primary-10)', backgroundColor: 'var(--light)' }}>
        <div style={{ padding: '10px 16px', fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase' as const, color: 'var(--mid)' }}>Department</div>
        {defs.map(d => (
          <div key={d.name} style={{ padding: '10px 8px', fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.2px', textTransform: 'uppercase' as const, color: 'var(--mid)', textAlign: 'center' as const }}>
            <div>{d.label}</div>
            <div style={{ fontWeight: 400, opacity: 0.6, marginTop: 2 }}>{d.unit}</div>
          </div>
        ))}
      </div>

      {rows.map((row, ri) => (
        <div key={row.department} style={{ display: 'grid', gridTemplateColumns: `180px repeat(${defs.length}, 1fr)`, borderBottom: ri < rows.length - 1 ? '1px solid var(--primary-10)' : 'none' }}>
          <div style={{ padding: '12px 16px' }}>
            <div style={{ fontFamily: 'var(--fb)', fontSize: 13, fontWeight: 600, color: 'var(--dark)' }}>{row.department}</div>
            <div style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'var(--mid)' }}>{row.headcount} employees</div>
          </div>
          {defs.map(d => {
            const cell = row.signals[d.name]
            if (!cell) return <div key={d.name} />
            const bg   = zscoreColor(cell.zscore, d.alert_direction)
            const tc   = zscoreText(cell.zscore, d.alert_direction)
            return (
              <div key={d.name} title={`${d.label}: ${cell.value} (z=${cell.zscore})`} style={{ padding: '12px 8px', backgroundColor: bg, textAlign: 'center' as const, borderLeft: '1px solid var(--primary-10)' }}>
                <div style={{ fontFamily: 'var(--fd)', fontSize: 14, fontWeight: 700, color: tc }}>{cell.value.toFixed(d.name.includes('ratio') || d.name.includes('trend') || d.name.includes('delta') ? 2 : 1)}</div>
                <div style={{ fontFamily: 'var(--fb)', fontSize: 9, color: tc, marginTop: 2 }}>
                  z={cell.zscore > 0 ? '+' : ''}{cell.zscore.toFixed(1)}
                  {cell.alert && <span style={{ marginLeft: 4, color: 'var(--status-orange)' }}>▲</span>}
                </div>
              </div>
            )
          })}
        </div>
      ))}

      {/* Legend */}
      <div style={{ padding: '10px 16px', backgroundColor: 'var(--light)', display: 'flex', gap: 20, alignItems: 'center', flexWrap: 'wrap' as const }}>
        <span style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase' as const, color: 'var(--mid)' }}>z-score legend:</span>
        {[
          { bg: 'rgba(39,185,124,0.20)', label: 'Better than baseline' },
          { bg: 'transparent',           label: 'Within normal range' },
          { bg: 'rgba(232,152,33,0.25)', label: 'Mildly elevated (z > 1.5)' },
          { bg: 'rgba(224,52,72,0.35)',  label: 'Significant deviation (z > 2)' },
        ].map(l => (
          <div key={l.label} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{ width: 14, height: 14, borderRadius: 3, backgroundColor: l.bg, border: '1px solid var(--primary-10)' }} />
            <span style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'var(--mid)' }}>{l.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Early warning tab ──────────────────────────────────────────────────────────

function EarlyWarningTab({ employees, defs }: { employees: PulseWarningEmployee[]; defs: PulseSignalDefinition[] }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {employees.map(emp => {
        const delta = riskDelta(emp.base_attrition_risk, emp.adjusted_attrition_risk)
        return (
          <div key={emp.employee_id} style={{
            backgroundColor: 'var(--white)', borderRadius: 'var(--radius-md)', boxShadow: 'var(--shadow-card)',
            padding: '18px 22px', borderLeft: `3px solid ${anomalyColor(emp.anomaly_score)}`,
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 3 }}>
                  <span style={{ fontFamily: 'var(--fb)', fontSize: 13, fontWeight: 600, color: 'var(--dark)' }}>{emp.anon_id}</span>
                  {emp.is_nexus && <span style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase' as const, backgroundColor: 'rgba(201,168,76,0.15)', color: 'var(--gold)', padding: '2px 8px', borderRadius: 'var(--radius-pill)' }}>Nexus</span>}
                </div>
                <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)' }}>{emp.role_title} · {emp.department} · {emp.seniority_level}</div>
              </div>
              <div style={{ textAlign: 'right' as const, flexShrink: 0, marginLeft: 20 }}>
                <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '2px', textTransform: 'uppercase' as const, color: 'var(--mid)', marginBottom: 3 }}>Anomaly Score</div>
                <div style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 700, color: anomalyColor(emp.anomaly_score) }}>
                  {(emp.anomaly_score * 100).toFixed(0)}%
                </div>
              </div>
            </div>

            {/* Risk comparison */}
            <div style={{ display: 'flex', gap: 20, marginBottom: 10, flexWrap: 'wrap' as const }}>
              <div>
                <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase' as const, color: 'var(--mid)', marginBottom: 2 }}>Base Attrition Risk</div>
                <div style={{ fontFamily: 'var(--fd)', fontSize: 15, fontWeight: 600, color: 'var(--primary)' }}>{(emp.base_attrition_risk * 100).toFixed(0)}%</div>
              </div>
              <div>
                <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase' as const, color: 'var(--mid)', marginBottom: 2 }}>Adjusted Risk</div>
                <div style={{ fontFamily: 'var(--fd)', fontSize: 15, fontWeight: 600, color: delta?.up ? 'var(--status-orange)' : 'var(--primary)' }}>
                  {(emp.adjusted_attrition_risk * 100).toFixed(0)}%
                  {delta && <span style={{ fontSize: 11, fontWeight: 400, marginLeft: 4, color: delta.up ? 'var(--status-orange)' : 'var(--status-green)' }}>{delta.up ? '+' : ''}{delta.val}pp</span>}
                </div>
              </div>
            </div>

            {/* Signal z-scores */}
            <div style={{ display: 'flex', flexWrap: 'wrap' as const, gap: 8 }}>
              {defs.map(d => {
                const z     = emp.signal_zscores[d.name] ?? 0
                const isCusum = emp.cusum_alerts.includes(d.name)
                const tc    = zscoreText(z, d.alert_direction)
                return (
                  <div key={d.name} style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '4px 10px', borderRadius: 'var(--radius-sm)', backgroundColor: 'var(--light)', border: isCusum ? '1px solid var(--status-orange)' : '1px solid transparent' }}>
                    <span style={{ fontFamily: 'var(--fb)', fontSize: 9, color: 'var(--mid)' }}>{d.label}</span>
                    <span style={{ fontFamily: 'var(--fd)', fontSize: 12, fontWeight: 600, color: tc }}>
                      {z > 0 ? '+' : ''}{z.toFixed(1)}σ
                    </span>
                    {isCusum && <span style={{ fontSize: 8, color: 'var(--status-orange)' }}>CUSUM</span>}
                  </div>
                )
              })}
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ── Signal sparkline ───────────────────────────────────────────────────────────

function Sparkline({ values, color = 'var(--gold)', h = 48, w = 280 }: { values: number[]; color?: string; h?: number; w?: number }) {
  if (!values.length) return null
  const lo = Math.min(...values), hi = Math.max(...values)
  const span = hi - lo || 1
  const pts  = values.map((v, i) => {
    const x = (i / (values.length - 1)) * w
    const y = h - ((v - lo) / span) * (h - 6) - 3
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
  const lastX = w, lastY = h - ((values[values.length - 1] - lo) / span) * (h - 6) - 3
  return (
    <svg width={w} height={h} xmlns="http://www.w3.org/2000/svg" style={{ display: 'block' }}>
      {/* Baseline reference at 70th day */}
      <line x1={(70 / 89) * w} y1={0} x2={(70 / 89) * w} y2={h} stroke="rgba(0,51,102,0.12)" strokeWidth={1} strokeDasharray="3,2" />
      <polyline points={pts} fill="none" stroke={color} strokeWidth={1.5} strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={lastX} cy={lastY} r={3} fill={color} />
    </svg>
  )
}

// ── Individual timelines tab ───────────────────────────────────────────────────

function TimelinesTab({ timelines, defs }: { timelines: PulseTimeline[]; defs: PulseSignalDefinition[] }) {
  const [selected, setSelected] = useState(0)

  const tl = timelines[selected]
  if (!tl) return null

  const SIGNAL_COLORS: Record<string, string> = {
    calendar_density_7d:         'var(--primary)',
    cross_team_interaction_7d:   'var(--gold)',
    response_latency_trend:      'var(--status-orange)',
    pto_utilization_rate:        'var(--primary-60)',
    after_hours_ratio:           'var(--status-red)',
    collaboration_network_delta: 'var(--status-green)',
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr', gap: 24, alignItems: 'start' }}>
      {/* Employee list */}
      <div style={{ backgroundColor: 'var(--white)', borderRadius: 'var(--radius-md)', boxShadow: 'var(--shadow-card)', overflow: 'hidden' }}>
        {timelines.map((tl, i) => (
          <button
            key={tl.employee_id}
            onClick={() => setSelected(i)}
            style={{
              display: 'block', width: '100%', textAlign: 'left' as const,
              padding: '12px 14px', border: 'none', cursor: 'pointer',
              backgroundColor: i === selected ? 'var(--primary-10)' : 'transparent',
              borderBottom: i < timelines.length - 1 ? '1px solid var(--primary-10)' : 'none',
              borderLeft: i === selected ? '3px solid var(--gold)' : '3px solid transparent',
            }}
          >
            <div style={{ fontFamily: 'var(--fb)', fontSize: 12, fontWeight: 600, color: 'var(--dark)', marginBottom: 2 }}>{tl.anon_id}</div>
            <div style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'var(--mid)' }}>{tl.department}</div>
          </button>
        ))}
      </div>

      {/* Signal charts */}
      <div>
        <div style={{ fontFamily: 'var(--fd)', fontSize: 17, fontWeight: 600, color: 'var(--primary)', marginBottom: 4 }}>{tl.anon_id}</div>
        <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', marginBottom: 20 }}>{tl.role_title} · {tl.department} · 90-day signal history</div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          {defs.map(d => {
            const values = tl.signals[d.name] ?? []
            const color  = SIGNAL_COLORS[d.name] ?? 'var(--primary)'
            const last   = values[values.length - 1] ?? 0
            return (
              <div key={d.name} style={{ backgroundColor: 'var(--white)', borderRadius: 'var(--radius-md)', boxShadow: 'var(--shadow-card)', padding: '16px 18px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: 8 }}>
                  <div>
                    <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase' as const, color: 'var(--mid)', marginBottom: 2 }}>{d.label}</div>
                    <div style={{ fontFamily: 'var(--fd)', fontSize: 18, fontWeight: 700, color }}>
                      {last.toFixed(d.name.includes('ratio') || d.name.includes('trend') || d.name.includes('delta') ? 2 : 1)}
                      <span style={{ fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 400, color: 'var(--mid)', marginLeft: 4 }}>{d.unit}</span>
                    </div>
                  </div>
                  <div style={{ fontFamily: 'var(--fb)', fontSize: 9, color: 'var(--mid)', textAlign: 'right' as const }}>
                    Healthy: {d.healthy_range}
                  </div>
                </div>
                <Sparkline values={values} color={color} w={260} h={52} />
                <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'var(--fb)', fontSize: 9, color: 'var(--mid)', marginTop: 4 }}>
                  <span>90d ago</span>
                  <span style={{ opacity: 0.5 }}>| baseline ends</span>
                  <span>Yesterday</span>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

// ── Team cohesion tab ──────────────────────────────────────────────────────────

function CohesionTab({ rows }: { rows: PulseCohesionRow[] }) {
  const maxScore = Math.max(...rows.map(r => r.cohesion_score), 1)

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
      {rows.sort((a, b) => b.cohesion_score - a.cohesion_score).map(row => {
        const pct   = (row.cohesion_score / maxScore) * 100
        const delta = row.delta_30d
        const lo    = Math.min(...row.trend)
        const hi    = Math.max(...row.trend)
        const span  = hi - lo || 1
        const W = 220, H = 36
        const pts = row.trend.map((v, i) => {
          const x = (i / (row.trend.length - 1)) * W
          const y = H - ((v - lo) / span) * (H - 6) - 3
          return `${x.toFixed(1)},${y.toFixed(1)}`
        }).join(' ')

        return (
          <div key={row.department} style={{ backgroundColor: 'var(--white)', borderRadius: 'var(--radius-md)', boxShadow: 'var(--shadow-card)', padding: '18px 22px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
              <div>
                <div style={{ fontFamily: 'var(--fd)', fontSize: 15, fontWeight: 600, color: 'var(--primary)', marginBottom: 2 }}>{row.department}</div>
                <div style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'var(--mid)' }}>{row.headcount} employees</div>
              </div>
              <div style={{ textAlign: 'right' as const }}>
                <div style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 700, color: row.cohesion_score >= 60 ? 'var(--status-green)' : row.cohesion_score >= 40 ? 'var(--gold)' : 'var(--status-orange)' }}>
                  {row.cohesion_score.toFixed(0)}
                </div>
                <div style={{ fontFamily: 'var(--fb)', fontSize: 9, color: 'var(--mid)' }}>cohesion score</div>
              </div>
            </div>

            {/* Score bar */}
            <div style={{ height: 5, backgroundColor: 'var(--primary-10)', borderRadius: 3, marginBottom: 12 }}>
              <div style={{ height: 5, width: `${pct}%`, borderRadius: 3, backgroundColor: row.cohesion_score >= 60 ? 'var(--status-green)' : row.cohesion_score >= 40 ? 'var(--gold)' : 'var(--status-orange)' }} />
            </div>

            {/* Sparkline */}
            <svg width={W} height={H} style={{ display: 'block', marginBottom: 6 }}>
              <polyline points={pts} fill="none" stroke="var(--gold)" strokeWidth={1.5} strokeLinejoin="round" strokeLinecap="round" />
            </svg>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'var(--fb)', fontSize: 9, color: 'var(--mid)' }}>
              <span>30 days ago</span>
              <span style={{ color: delta > 0.1 ? 'var(--status-green)' : delta < -0.1 ? 'var(--status-orange)' : 'var(--mid)' }}>
                {delta > 0 ? '+' : ''}{delta.toFixed(2)} cross-team contacts/day
              </span>
              <span>Now</span>
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ── Main page ──────────────────────────────────────────────────────────────────

type PulseTab = 'heatmap' | 'warning' | 'timelines' | 'cohesion'

export default function PulsePage() {
  const { scenario, size } = useDemoStore()
  const [tab,  setTab]  = useState<PulseTab>('heatmap')
  const [data, setData] = useState<PulseData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    api.pulse.data(scenario, size)
      .then(setData)
      .catch(e => setError(e instanceof Error ? e.message : 'Failed to load'))
      .finally(() => setLoading(false))
  }, [scenario, size])

  const tabBtn = (id: PulseTab, label: string, badge?: number) => {
    const active = tab === id
    return (
      <button
        onClick={() => setTab(id)}
        style={{
          fontFamily: 'var(--fb)', fontSize: 10, letterSpacing: '2px', textTransform: 'uppercase' as const,
          fontWeight: 600, padding: '10px 18px', border: 'none',
          borderBottom: active ? '2px solid var(--gold-light)' : '2px solid transparent',
          backgroundColor: 'transparent', color: active ? 'var(--gold-light)' : 'rgba(255,255,255,0.45)',
          cursor: 'pointer', marginBottom: -1, display: 'flex', alignItems: 'center', gap: 6,
        }}
      >
        {label}
        {badge !== undefined && badge > 0 && (
          <span style={{ fontSize: 9, backgroundColor: 'var(--status-orange)', color: '#fff', borderRadius: 'var(--radius-pill)', padding: '1px 6px', fontWeight: 700 }}>
            {badge}
          </span>
        )}
      </button>
    )
  }

  return (
    <div>
      {/* Header */}
      <div style={{ background: 'var(--primary)', paddingTop: 48, paddingLeft: 48, paddingRight: 48, paddingBottom: 0, borderBottom: '1px solid rgba(255,255,255,0.12)' }}>
        <div style={{ maxWidth: 'var(--max-width-content)', margin: '0 auto' }}>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '3px', textTransform: 'uppercase', color: 'var(--gold)', marginBottom: 10 }}>
            Sprint 20 · Engagement Intelligence
          </div>
          <h1 style={{ fontFamily: 'var(--fd)', fontSize: 38, fontWeight: 600, fontStyle: 'italic', color: '#fff', margin: '0 0 6px' }}>
            Pulse Monitoring
          </h1>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'rgba(255,255,255,0.55)', margin: '0 0 24px', maxWidth: 580, lineHeight: 1.6 }}>
            Metadata-only engagement signals. Six behavioral indicators per employee, updated daily.
            Anomalies detected via IsolationForest with CUSUM drift control charting.
          </p>
          <div style={{ display: 'flex', gap: 4, borderBottom: '1px solid rgba(255,255,255,0.12)' }}>
            {tabBtn('heatmap',   'Pulse Heatmap')}
            {tabBtn('warning',   'Early Warning', data?.summary.anomaly_count)}
            {tabBtn('timelines', 'Signal Timelines')}
            {tabBtn('cohesion',  'Team Cohesion')}
          </div>
        </div>
      </div>

      <div style={{ maxWidth: 'var(--max-width-content)', margin: '0 auto', padding: '36px 48px' }}>
        {loading && (
          <div style={{ textAlign: 'center' as const, padding: 80, fontFamily: 'var(--fd)', fontSize: 18, color: 'var(--mid)', fontStyle: 'italic' }}>
            Running anomaly detection…
          </div>
        )}
        {error && (
          <div style={{ backgroundColor: 'rgba(224,52,72,0.06)', border: '1px solid rgba(224,52,72,0.2)', borderRadius: 'var(--radius-md)', padding: '16px 20px', color: 'var(--status-red)', fontFamily: 'var(--fb)', fontSize: 12 }}>
            {error}
          </div>
        )}

        {data && (
          <>
            <DisclaimerBanner text={data.disclaimer} />
            <SummaryStrip data={data} />

            {tab === 'heatmap' && (
              <HeatmapTab rows={data.heatmap} defs={data.signal_definitions} />
            )}
            {tab === 'warning' && (
              <EarlyWarningTab employees={data.early_warning} defs={data.signal_definitions} />
            )}
            {tab === 'timelines' && (
              <TimelinesTab timelines={data.timelines} defs={data.signal_definitions} />
            )}
            {tab === 'cohesion' && (
              <CohesionTab rows={data.team_cohesion} />
            )}
          </>
        )}
      </div>
    </div>
  )
}
