// Impact-score bands relative to the org being shown.
//
// Impact scores come from the 4-component model (KPI · network · skills · cost), whose
// values cluster in a narrow range (roughly 25–75 on the demo orgs). Fixed cut-offs
// such as ">= 75 is high" would colour almost nobody, so bands are taken from the
// distribution itself: high = top 20%, mid = above the median.

export interface ImpactBands {
  high: number // 80th percentile
  mid: number  // median
}

export function quantile(values: number[], q: number): number {
  if (values.length === 0) return 0
  const sorted = [...values].sort((a, b) => a - b)
  const pos = (sorted.length - 1) * q
  const lo = Math.floor(pos)
  const hi = Math.ceil(pos)
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (pos - lo)
}

export function impactBands(scores: number[]): ImpactBands {
  return { high: quantile(scores, 0.8), mid: quantile(scores, 0.5) }
}

export function impactColor(score: number, bands: ImpactBands): string {
  if (score >= bands.high) return 'var(--status-green)'
  if (score >= bands.mid) return 'var(--gold)'
  return 'var(--mid)'
}
