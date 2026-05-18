import React, { useState, useEffect } from 'react'
import { api, ForecastData, ForecastSeries, MonteCarloData } from '../services/api'
import { useDemoStore } from '../stores/demoStore'

// ── Helpers ───────────────────────────────────────────────────────────────

function fmtMoney(v: number): string {
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(2)}M`
  if (v >= 1_000)     return `$${(v / 1_000).toFixed(0)}K`
  return `$${v.toFixed(0)}`
}

// ── Budget Forecast Chart ─────────────────────────────────────────────────

function ForecastChart({ series }: { series: ForecastSeries }) {
  const W = 780, H = 280
  const PL = 78, PR = 20, PT = 24, PB = 48
  const CW = W - PL - PR
  const CH = H - PT - PB

  const nH = series.history.length
  const fc  = series.forecast
  const n   = nH + fc.length

  const allY = [
    ...series.history.map(d => d.y),
    ...fc.map(d => d.yhat),
    ...fc.map(d => d.yhat_lower_95),
    ...fc.map(d => d.yhat_upper_95),
  ].filter(v => isFinite(v) && v >= 0)

  if (allY.length === 0 || n < 2) return null

  const yMin = Math.min(...allY) * 0.92
  const yMax = Math.max(...allY) * 1.05

  const xS = (i: number) => PL + (i / (n - 1)) * CW
  const yS = (v: number) => PT + CH - ((v - yMin) / (yMax - yMin)) * CH

  // CI polygons — forecast points start at index nH on the x-axis
  const upper95 = fc.map((d, i) => `${xS(nH + i).toFixed(1)},${yS(d.yhat_upper_95).toFixed(1)}`)
  const lower95 = [...fc].reverse().map((d, i) => `${xS(n - 1 - i).toFixed(1)},${yS(d.yhat_lower_95).toFixed(1)}`)
  const poly95  = [...upper95, ...lower95].join(' ')

  const upper80 = fc.map((d, i) => `${xS(nH + i).toFixed(1)},${yS(d.yhat_upper_80).toFixed(1)}`)
  const lower80 = [...fc].reverse().map((d, i) => `${xS(n - 1 - i).toFixed(1)},${yS(d.yhat_lower_80).toFixed(1)}`)
  const poly80  = [...upper80, ...lower80].join(' ')

  // Line paths
  const histPath = series.history
    .map((d, i) => `${i === 0 ? 'M' : 'L'}${xS(i).toFixed(1)},${yS(d.y).toFixed(1)}`)
    .join(' ')

  const lastHistY = series.history[nH - 1]?.y ?? 0
  const fcPath = [
    `M${xS(nH - 1).toFixed(1)},${yS(lastHistY).toFixed(1)}`,
    ...fc.map((d, i) => `L${xS(nH + i).toFixed(1)},${yS(d.yhat).toFixed(1)}`),
  ].join(' ')

  const divX = xS(nH - 1)

  // Y ticks
  const yStep  = (yMax - yMin) / 4
  const yTicks = Array.from({ length: 5 }, (_, i) => yMin + i * yStep)

  // X labels every 6 months
  const allDates = [...series.history.map(d => d.ds), ...fc.map(d => d.ds)]

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', display: 'block' }}>
      {/* Gridlines */}
      {yTicks.map((v, i) => (
        <line key={i} x1={PL} x2={W - PR} y1={yS(v).toFixed(1)} y2={yS(v).toFixed(1)}
          stroke="#e4e9f0" strokeWidth={1} />
      ))}

      {/* 95% CI band */}
      <polygon points={poly95} fill="#003366" fillOpacity={0.06} />
      {/* 80% CI band */}
      <polygon points={poly80} fill="#003366" fillOpacity={0.12} />

      {/* History/Forecast divider */}
      <line x1={divX.toFixed(1)} x2={divX.toFixed(1)} y1={PT} y2={H - PB}
        stroke="#003366" strokeWidth={1} strokeDasharray="4,3" strokeOpacity={0.25} />

      {/* History line */}
      <path d={histPath} fill="none" stroke="#003366" strokeWidth={2} />
      {/* Forecast line */}
      <path d={fcPath} fill="none" stroke="#C9A84C" strokeWidth={2.5} />

      {/* Y axis labels */}
      {yTicks.map((v, i) => (
        <text key={i} x={PL - 8} y={(yS(v) + 4).toFixed(1)} textAnchor="end"
          fontSize={10} fill="#7a91a8" fontFamily="'Plus Jakarta Sans', sans-serif">
          {fmtMoney(v)}
        </text>
      ))}

      {/* X axis labels */}
      {allDates.map((ds, i) => {
        if (i % 6 !== 0 && i !== n - 1) return null
        return (
          <text key={ds} x={xS(i).toFixed(1)} y={H - PB + 18} textAnchor="middle"
            fontSize={10} fill="#7a91a8" fontFamily="'Plus Jakarta Sans', sans-serif">
            {ds.slice(0, 7)}
          </text>
        )
      })}

      {/* Annotations */}
      <text x={(divX - 8).toFixed(1)} y={PT + 12} textAnchor="end"
        fontSize={9} fill="#7a91a8" fontFamily="'Plus Jakarta Sans', sans-serif" letterSpacing="1">
        HISTORY
      </text>
      <text x={(divX + 8).toFixed(1)} y={PT + 12} textAnchor="start"
        fontSize={9} fill="#C9A84C" fontFamily="'Plus Jakarta Sans', sans-serif" letterSpacing="1">
        12-MONTH FORECAST
      </text>
    </svg>
  )
}

// ── Monte Carlo Fan Chart ─────────────────────────────────────────────────

function MonteCarloChart({ data }: { data: MonteCarloData }) {
  const W = 780, H = 260
  const PL = 78, PR = 72, PT = 24, PB = 48
  const CW = W - PL - PR
  const CH = H - PT - PB

  const fan = data.fan_chart
  const n   = fan.length
  if (n === 0) return null

  const allY = [
    ...fan.map(d => d.p10),
    ...fan.map(d => d.p90),
    data.monthly_budget,
  ].filter(v => isFinite(v) && v > 0)

  if (allY.length === 0) return null

  const yMin = Math.min(...allY) * 0.90
  const yMax = Math.max(...allY) * 1.08

  const xS = (i: number) => PL + (i / Math.max(n - 1, 1)) * CW
  const yS = (v: number) => PT + CH - ((v - yMin) / (yMax - yMin)) * CH

  const upperPts = fan.map((d, i) => `${xS(i).toFixed(1)},${yS(d.p90).toFixed(1)}`)
  const lowerPts = [...fan].reverse().map((d, i) => `${xS(n - 1 - i).toFixed(1)},${yS(d.p10).toFixed(1)}`)
  const bandPoly = [...upperPts, ...lowerPts].join(' ')

  const p50Path = fan
    .map((d, i) => `${i === 0 ? 'M' : 'L'}${xS(i).toFixed(1)},${yS(d.p50).toFixed(1)}`)
    .join(' ')

  const budgetY  = yS(data.monthly_budget)
  const yStep    = (yMax - yMin) / 4
  const yTicks   = Array.from({ length: 5 }, (_, i) => yMin + i * yStep)
  const last     = fan[n - 1]

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', display: 'block' }}>
      {/* Gridlines */}
      {yTicks.map((v, i) => (
        <line key={i} x1={PL} x2={W - PR} y1={yS(v).toFixed(1)} y2={yS(v).toFixed(1)}
          stroke="#e4e9f0" strokeWidth={1} />
      ))}

      {/* P10–P90 band */}
      <polygon points={bandPoly} fill="#003366" fillOpacity={0.09} />

      {/* Budget line (dashed red) */}
      <line x1={PL} x2={W - PR} y1={budgetY.toFixed(1)} y2={budgetY.toFixed(1)}
        stroke="#c0392b" strokeWidth={1.5} strokeDasharray="6,4" />
      <text x={W - PR + 6} y={(budgetY + 4).toFixed(1)} fontSize={9} fill="#c0392b"
        fontFamily="'Plus Jakarta Sans', sans-serif">Budget</text>

      {/* P50 median line (gold) */}
      <path d={p50Path} fill="none" stroke="#C9A84C" strokeWidth={2.5} />

      {/* End-of-horizon labels */}
      <text x={(xS(n - 1) + 4).toFixed(1)} y={(yS(last.p90) + 4).toFixed(1)} fontSize={9}
        fill="#003366" fillOpacity={0.6} fontFamily="'Plus Jakarta Sans', sans-serif">P90</text>
      <text x={(xS(n - 1) + 4).toFixed(1)} y={(yS(last.p50) + 4).toFixed(1)} fontSize={9}
        fill="#C9A84C" fontFamily="'Plus Jakarta Sans', sans-serif">P50</text>
      <text x={(xS(n - 1) + 4).toFixed(1)} y={(yS(last.p10) + 4).toFixed(1)} fontSize={9}
        fill="#003366" fillOpacity={0.6} fontFamily="'Plus Jakarta Sans', sans-serif">P10</text>

      {/* Y axis labels */}
      {yTicks.map((v, i) => (
        <text key={i} x={PL - 8} y={(yS(v) + 4).toFixed(1)} textAnchor="end"
          fontSize={10} fill="#7a91a8" fontFamily="'Plus Jakarta Sans', sans-serif">
          {fmtMoney(v)}
        </text>
      ))}

      {/* X axis labels every 3 months */}
      {fan.map((d, i) => {
        if (i % 3 !== 0 && i !== n - 1) return null
        return (
          <text key={d.ds} x={xS(i).toFixed(1)} y={H - PB + 18} textAnchor="middle"
            fontSize={10} fill="#7a91a8" fontFamily="'Plus Jakarta Sans', sans-serif">
            {d.ds.slice(0, 7)}
          </text>
        )
      })}
    </svg>
  )
}

// ── Exceedance Bar Chart ─────────────────────────────────────────────────

function ExceedanceChart({ data }: { data: MonteCarloData }) {
  const W = 780, H = 96
  const PL = 78, PR = 20, PT = 12, PB = 32
  const CW = W - PL - PR
  const CH = H - PT - PB

  const exc = data.exceedance_prob
  const n   = exc.length
  if (n === 0) return null

  const barW = (CW / n) * 0.55
  const xS   = (i: number) => PL + (i + 0.5) / n * CW

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', display: 'block' }}>
      {/* 50% reference line */}
      <line x1={PL} x2={W - PR} y1={(PT + CH * 0.5).toFixed(1)} y2={(PT + CH * 0.5).toFixed(1)}
        stroke="#e4e9f0" strokeWidth={1} strokeDasharray="4,3" />

      {exc.map((d, i) => {
        const barH = d.prob_over_budget * CH
        const barX = xS(i) - barW / 2
        const barY = PT + CH - barH
        const fill = d.prob_over_budget >= 0.5
          ? '#c0392b'
          : d.prob_over_budget >= 0.25
            ? '#e67e22'
            : '#003366'
        return (
          <g key={d.ds}>
            <rect x={barX.toFixed(1)} y={barY.toFixed(1)}
              width={barW.toFixed(1)} height={Math.max(barH, 1).toFixed(1)}
              fill={fill} fillOpacity={0.72} rx={2} />
            {(i % 3 === 0 || i === n - 1) && (
              <text x={xS(i).toFixed(1)} y={H - PB + 14} textAnchor="middle"
                fontSize={9} fill="#7a91a8" fontFamily="'Plus Jakarta Sans', sans-serif">
                {d.ds.slice(5, 7)}/{d.ds.slice(2, 4)}
              </text>
            )}
          </g>
        )
      })}

      <text x={PL - 8} y={(PT + CH * 0.5 + 4).toFixed(1)} textAnchor="end"
        fontSize={9} fill="#7a91a8" fontFamily="'Plus Jakarta Sans', sans-serif">50%</text>
      <text x={PL - 8} y={(PT + 4).toFixed(1)} textAnchor="end"
        fontSize={9} fill="#7a91a8" fontFamily="'Plus Jakarta Sans', sans-serif">100%</text>
    </svg>
  )
}

// ── Model note ────────────────────────────────────────────────────────────

function ModelNote({ model, mape, generated }: { model: string; mape: number; generated: string }) {
  return (
    <div style={{
      flex: 1, display: 'flex', gap: 10, alignItems: 'flex-start',
      backgroundColor: 'var(--primary-10)', borderRadius: 'var(--radius-sm)',
      padding: '10px 14px',
    }}>
      <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px', textTransform: 'uppercase', color: 'var(--primary)', fontWeight: 700, whiteSpace: 'nowrap', marginTop: 1 }}>
        Model
      </div>
      <div style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--primary)', lineHeight: 1.6 }}>
        {model === 'prophet' ? 'Facebook Prophet (annual + quarterly seasonality)' : 'Linear extrapolation (Prophet unavailable)'}
        {' '}— in-sample MAPE {mape.toFixed(1)}%. Generated {generated}.
      </div>
    </div>
  )
}

// ── Legend item ───────────────────────────────────────────────────────────

function LegendItem({ color, label, band = false, opacity = 1 }: { color: string; label: string; band?: boolean; opacity?: number }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      {band
        ? <div style={{ width: 18, height: 10, backgroundColor: color, opacity, borderRadius: 2 }} />
        : <div style={{ width: 18, height: 3, backgroundColor: color }} />
      }
      <span style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'var(--mid)' }}>{label}</span>
    </div>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────

export default function ForecastPage() {
  const { scenario, size, enabled: demo } = useDemoStore()

  const [forecast,   setForecast]   = useState<ForecastData | null>(null)
  const [monteCarlo, setMonteCarlo] = useState<MonteCarloData | null>(null)
  const [fLoading,   setFLoading]   = useState(true)
  const [mcLoading,  setMcLoading]  = useState(true)
  const [fError,     setFError]     = useState<string | null>(null)
  const [mcError,    setMcError]    = useState<string | null>(null)
  const [activeDept, setActiveDept] = useState<string>('total')

  useEffect(() => {
    setFLoading(true)
    setFError(null)
    setActiveDept('total')
    api.forecast.budget(scenario, size, demo)
      .then(setForecast)
      .catch(e => setFError(e.message))
      .finally(() => setFLoading(false))
  }, [scenario, size, demo])

  useEffect(() => {
    setMcLoading(true)
    setMcError(null)
    api.forecast.monteCarlo(scenario, size, demo)
      .then(setMonteCarlo)
      .catch(e => setMcError(e.message))
      .finally(() => setMcLoading(false))
  }, [scenario, size, demo])

  const depts = forecast ? forecast.by_department.map(s => s.label) : []

  const activeSeries: ForecastSeries | undefined = forecast
    ? activeDept === 'total'
      ? forecast.total_spend
      : (forecast.by_department.find(s => s.label === activeDept) ?? forecast.total_spend)
    : undefined

  const card: React.CSSProperties = {
    backgroundColor: 'var(--white)',
    borderRadius: 'var(--radius-md)',
    boxShadow: 'var(--shadow-card)',
    padding: '28px 32px',
    marginBottom: 24,
  }

  const sectionLabel: React.CSSProperties = {
    fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '2px',
    textTransform: 'uppercase', color: 'var(--mid)', marginBottom: 6,
  }

  const sectionTitle: React.CSSProperties = {
    fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 600, color: 'var(--dark)',
  }

  return (
    <div>
      {/* Hero */}
      <div style={{ background: 'var(--primary)', paddingTop: 48, paddingBottom: 48, paddingLeft: 48, paddingRight: 48 }}>
        <div style={{ maxWidth: 'var(--max-width-content)', margin: '0 auto' }}>
          <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '3px', textTransform: 'uppercase', color: 'var(--gold)', marginBottom: 10 }}>
            Budget Intelligence
          </div>
          <h1 style={{ fontFamily: 'var(--fd)', fontSize: 38, fontWeight: 600, fontStyle: 'italic', color: '#fff', margin: '0 0 10px' }}>
            12-Month Forecast &amp; Stress Test
          </h1>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: 'rgba(255,255,255,0.55)', margin: 0 }}>
            Payroll trajectory forecasts with Monte Carlo uncertainty quantification across 2,000 simulated budget paths.
          </p>

          {forecast && monteCarlo && (
            <div style={{ display: 'flex', gap: 32, marginTop: 32, flexWrap: 'wrap' }}>
              {[
                { val: fmtMoney(monteCarlo.annual_budget),  label: 'Annual Budget'       },
                { val: fmtMoney(monteCarlo.monthly_budget), label: 'Monthly Target'       },
                { val: `${(monteCarlo.prob_overspend_any_month * 100).toFixed(0)}%`, label: 'Overspend Risk'  },
                { val: String(forecast.by_department.length), label: 'Departments'        },
              ].map(({ val, label }) => (
                <div key={label} style={{ borderLeft: '3px solid var(--gold)', paddingLeft: 14 }}>
                  <div style={{ fontFamily: 'var(--fd)', fontSize: 30, fontWeight: 700, color: 'var(--gold-light)' }}>{val}</div>
                  <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '2px', textTransform: 'uppercase', color: 'rgba(255,255,255,0.45)' }}>{label}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div style={{ maxWidth: 'var(--max-width-content)', margin: '0 auto', padding: '36px 48px' }}>

        {/* ── Budget Forecast ── */}
        <div style={card}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20, flexWrap: 'wrap', gap: 12 }}>
            <div>
              <div style={sectionLabel}>Payroll Forecast</div>
              <div style={sectionTitle}>Budget Trajectory</div>
            </div>

            {forecast && (
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {['total', ...depts].map(id => (
                  <button
                    key={id}
                    onClick={() => setActiveDept(id)}
                    style={{
                      fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '1.5px',
                      textTransform: 'uppercase', fontWeight: 600,
                      padding: '5px 12px', borderRadius: 'var(--radius-pill)',
                      border: 'none', cursor: 'pointer',
                      backgroundColor: activeDept === id ? 'var(--primary)' : 'var(--light)',
                      color:           activeDept === id ? '#fff' : 'var(--mid)',
                    }}
                  >
                    {id === 'total' ? 'Total' : id}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Before-chart description */}
          <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: 'var(--mid)', lineHeight: 1.75, maxWidth: 680, margin: '0 0 24px' }}>
            This chart shows where your total payroll costs are heading over the next 12 months.
            The <strong style={{ color: 'var(--primary)', fontWeight: 600 }}>navy line</strong> on the left traces actual spending from the past two years — your financial history.
            The <strong style={{ color: '#C9A84C', fontWeight: 600 }}>gold line</strong> on the right is the forecast: where costs are most likely to go if current patterns continue.
            The shaded bands show uncertainty — the darker band means we are 80% confident the real cost will land within it; the lighter band widens that to 95%.
          </p>

          {fLoading && (
            <div style={{ fontFamily: 'var(--fd)', fontSize: 18, color: 'var(--primary)', padding: '48px 0', textAlign: 'center' }}>
              Building forecast…
            </div>
          )}
          {fError && (
            <div style={{ color: 'var(--status-red)', fontFamily: 'var(--fb)', fontSize: 13 }}>{fError}</div>
          )}
          {activeSeries && <ForecastChart series={activeSeries} />}

          {forecast && activeSeries && (
            <>
              {/* Legend row */}
              <div style={{ display: 'flex', gap: 14, alignItems: 'center', flexWrap: 'wrap', marginTop: 16, marginBottom: 28 }}>
                <LegendItem color="#003366" label="History" />
                <LegendItem color="#C9A84C" label="Forecast" />
                <LegendItem color="#003366" label="80% confidence range" band opacity={0.12} />
                <LegendItem color="#003366" label="95% confidence range" band opacity={0.06} />
              </div>

              {/* After-chart explanation */}
              <div style={{ borderTop: '1px solid var(--primary-10)', paddingTop: 24, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 32 }}>
                <div>
                  <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--primary)', fontWeight: 700, marginBottom: 10 }}>
                    How it was calculated
                  </div>
                  <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--dark)', lineHeight: 1.8, margin: 0 }}>
                    The model studied 24 months of payroll history to detect three things: the overall growth trend (are costs rising or falling?), recurring seasonal patterns — December bonus spikes, mid-year review increases, post-bonus dips in January — and normal month-to-month variation. It then projects those patterns forward. The confidence bands widen as the forecast extends because small uncertainties compound over time: a month-12 estimate is naturally less certain than a month-1 estimate.
                  </p>
                  {activeSeries.model !== 'prophet' && (
                    <p style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)', lineHeight: 1.7, marginTop: 12, marginBottom: 0 }}>
                      <em>Note: this forecast uses linear trend extrapolation. For richer seasonality modelling, install the Prophet library.</em>
                    </p>
                  )}
                </div>
                <div>
                  <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--primary)', fontWeight: 700, marginBottom: 10 }}>
                    Why it matters
                  </div>
                  <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--dark)', lineHeight: 1.8, margin: 0 }}>
                    Traditional budget planning works from last year's number plus a growth percentage — a single point estimate with no sense of risk. This forecast gives you a range. If the gold line trends above your approved budget, that is an early warning to adjust headcount plans or reallocate spend before a variance becomes a crisis. Use the department tabs above to identify which teams are driving cost growth and where pressure is building soonest.
                  </p>
                </div>
              </div>

              <ModelNote model={activeSeries.model} mape={activeSeries.mape} generated={forecast.generated_at} />
            </>
          )}
        </div>

        {/* ── Monte Carlo ── */}
        <div style={card}>
          <div style={{ marginBottom: 20 }}>
            <div style={sectionLabel}>Monte Carlo Stress Test</div>
            <div style={sectionTitle}>Budget Fan Chart</div>
          </div>

          {mcLoading && (
            <div style={{ fontFamily: 'var(--fd)', fontSize: 18, color: 'var(--primary)', padding: '48px 0', textAlign: 'center' }}>
              Running 2,000 budget simulations…
            </div>
          )}
          {mcError && (
            <div style={{ color: 'var(--status-red)', fontFamily: 'var(--fb)', fontSize: 13 }}>{mcError}</div>
          )}

          {/* Before-chart description */}
          <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: 'var(--mid)', lineHeight: 1.75, maxWidth: 680, margin: '0 0 24px' }}>
            Instead of a single forecast line, this chart shows the full spectrum of possible outcomes — from optimistic to adverse.
            Each of the 2,000 simulated paths represents a different version of the next 12 months where employees leave at different rates, replacement costs land differently, and salary inflation hits at varying intensities.
            The shaded band captures the middle 80% of all outcomes.
            The <strong style={{ color: '#C9A84C', fontWeight: 600 }}>gold line</strong> is the median — half of all simulations land above it, half below.
            The <strong style={{ color: '#c0392b', fontWeight: 600 }}>red dashed line</strong> is your monthly budget target.
          </p>

          {monteCarlo && (
            <>
              <MonteCarloChart data={monteCarlo} />

              {/* KPI row */}
              <div style={{ display: 'flex', gap: 16, marginTop: 28, flexWrap: 'wrap' }}>
                {[
                  { val: fmtMoney(monteCarlo.final_month.p10),  label: 'P10 — Month 12',  sub: 'best case'    },
                  { val: fmtMoney(monteCarlo.final_month.p50),  label: 'P50 — Month 12',  sub: 'median'       },
                  { val: fmtMoney(monteCarlo.final_month.p90),  label: 'P90 — Month 12',  sub: 'adverse case' },
                  { val: `${(monteCarlo.prob_overspend_any_month * 100).toFixed(0)}%`, label: 'Overspend Risk', sub: 'any month'  },
                ].map(({ val, label, sub }) => (
                  <div key={label} style={{ flex: 1, minWidth: 140, borderTop: '3px solid var(--gold)', paddingTop: 16 }}>
                    <div style={{ fontFamily: 'var(--fd)', fontSize: 26, fontWeight: 700, color: 'var(--primary)', marginBottom: 4 }}>{val}</div>
                    <div style={{ fontFamily: 'var(--fb)', fontSize: 11, fontWeight: 600, color: 'var(--dark)', marginBottom: 2 }}>{label}</div>
                    <div style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'var(--mid)', textTransform: 'uppercase', letterSpacing: '1px' }}>{sub}</div>
                  </div>
                ))}
              </div>

              {/* Exceedance chart */}
              <div style={{ marginTop: 32 }}>
                <div style={sectionLabel}>Monthly Overspend Probability</div>
                <ExceedanceChart data={monteCarlo} />
              </div>

              {/* Legend */}
              <div style={{ display: 'flex', gap: 16, marginTop: 16, alignItems: 'center', flexWrap: 'wrap' }}>
                <LegendItem color="#C9A84C" label="P50 (median)" />
                <LegendItem color="#003366" label="P10–P90 range" band opacity={0.09} />
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <div style={{ width: 18, height: 2, backgroundColor: '#c0392b', borderRadius: 1 }} />
                  <span style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'var(--mid)' }}>Monthly budget</span>
                </div>
              </div>

              {/* After-chart explanation */}
              <div style={{ borderTop: '1px solid var(--primary-10)', marginTop: 28, paddingTop: 24, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 32 }}>
                <div>
                  <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--primary)', fontWeight: 700, marginBottom: 10 }}>
                    How it was calculated
                  </div>
                  <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--dark)', lineHeight: 1.8, margin: 0 }}>
                    Each simulation runs month by month through your entire employee roster. Every month, each person has an individual probability of leaving based on their retention risk score — employees flagged as high-risk are more likely to depart in the model. When someone leaves, the simulation adds a one-time replacement cost and removes their salary going forward. The remaining team's costs grow with salary inflation. December gets an 8% cost spike for bonuses; June and July receive a 2% increase for mid-year reviews. After 2,000 runs, the P10, P50, and P90 bands emerge from the full distribution of outcomes.
                  </p>
                </div>
                <div>
                  <div style={{ fontFamily: 'var(--fb)', fontSize: 9, letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--primary)', fontWeight: 700, marginBottom: 10 }}>
                    Why it matters
                  </div>
                  <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--dark)', lineHeight: 1.8, margin: 0 }}>
                    Where the red budget line sits relative to the P50 tells you whether your budget is comfortable or stretched. If the P90 band crosses the budget line early in the year, even a moderately bad scenario — not a worst case, just an average bad month — leads to overspend. The overspend probability below the fan chart translates this directly: a 30% probability means roughly 1 in 3 similar years would have exceeded budget at some point. Use this to decide whether to hold a contingency reserve, accelerate hiring controls, or flag the risk to finance.
                  </p>
                </div>
              </div>

              {monteCarlo.notes.length > 0 && (
                <div style={{
                  marginTop: 20, backgroundColor: 'var(--primary-10)', borderRadius: 'var(--radius-sm)',
                  padding: '12px 16px',
                }}>
                  {monteCarlo.notes.map((note, i) => (
                    <div key={i} style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--primary)', lineHeight: 1.6 }}>
                      • {note}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
