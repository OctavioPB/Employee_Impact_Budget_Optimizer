/**
 * EIBO Widget: Budget Forecast Chip
 * Usage:
 *   <script src="/widgets/eibo-budget-chip.js"></script>
 *   <eibo-budget-chip api-key="eibo_…" base-url="http://eibo.internal"
 *                     scenario="A" size="small"></eibo-budget-chip>
 */
(function () {
  const STYLE = `
    :host { display: inline-block; font-family: sans-serif; }
    .chip {
      background: #fff; border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.10);
      padding: 14px 18px; min-width: 200px; max-width: 300px;
    }
    .label    { font-size: 9px; letter-spacing: 2px; text-transform: uppercase; color: #6b7280; margin-bottom: 6px; }
    .budget   { font-size: 22px; font-weight: 700; color: #003366; line-height: 1; margin-bottom: 4px; }
    .sub      { font-size: 11px; color: #9ca3af; margin-bottom: 12px; }
    .arrow    { font-size: 20px; margin-right: 6px; }
    .forecast { font-size: 12px; color: #374151; display: flex; align-items: center; }
    .band     { font-size: 10px; color: #9ca3af; margin-top: 6px; }
    .bar-wrap { display: flex; gap: 2px; margin-top: 10px; }
    .bar-col  { flex: 1; }
    .bar-outer{ height: 32px; background: #f3f4f6; border-radius: 3px; display: flex; align-items: flex-end; }
    .bar-inner{ border-radius: 3px; }
    .bar-lbl  { font-size: 8px; text-align: center; color: #9ca3af; margin-top: 2px; }
    .error    { color: #dc2626; font-size: 11px; padding: 10px; }
    .loading  { color: #9ca3af; font-size: 11px; padding: 10px; }
  `;

  function fmt(n) {
    if (n >= 1e6) return `$${(n / 1e6).toFixed(1)}M`;
    if (n >= 1e3) return `$${(n / 1e3).toFixed(0)}K`;
    return `$${n.toFixed(0)}`;
  }

  class EiboBudgetChip extends HTMLElement {
    connectedCallback() { this._render(); }

    async _render() {
      const shadow = this.attachShadow({ mode: 'open' });
      shadow.innerHTML = `<style>${STYLE}</style><div class="loading">Loading…</div>`;

      const apiKey   = this.getAttribute('api-key') || '';
      const baseUrl  = (this.getAttribute('base-url') || '').replace(/\/$/, '');
      const scenario = this.getAttribute('scenario') || 'A';
      const size     = this.getAttribute('size') || 'small';

      try {
        const resp = await fetch(
          `${baseUrl}/api/v1/forecast?scenario=${scenario}&size=${size}`,
          { headers: { Authorization: `Bearer ${apiKey}` } },
        );
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();

        const baseline = data.monthly_baseline || 0;
        const forecast = data.forecast || [];
        const maxF     = Math.max(...forecast.map(f => f.upper_80), baseline);
        const last     = forecast[forecast.length - 1] || {};
        const trend    = last.forecast_budget > baseline ? '↑' : '↓';
        const trendClr = last.forecast_budget > baseline ? '#f97316' : '#22c55e';

        const bars = forecast.slice(0, 6).map((f, i) => {
          const h = Math.round((f.forecast_budget / maxF) * 28);
          return `<div class="bar-col">
            <div class="bar-outer">
              <div class="bar-inner" style="width:100%;height:${h}px;background:#C9A84C;opacity:${0.4 + i * 0.1}"></div>
            </div>
            <div class="bar-lbl">M${i + 1}</div>
          </div>`;
        }).join('');

        shadow.innerHTML = `<style>${STYLE}</style>
          <div class="chip">
            <div class="label">Monthly Budget Forecast</div>
            <div class="budget">${fmt(baseline)}</div>
            <div class="sub">current monthly baseline</div>
            <div class="forecast">
              <span class="arrow" style="color:${trendClr}">${trend}</span>
              <span>6-month avg: ${fmt(forecast.reduce((a, f) => a + (f.forecast_budget || 0), 0) / (forecast.length || 1))}</span>
            </div>
            <div class="bar-wrap">${bars}</div>
            <div class="band">80% confidence: ${fmt(last.lower_80 || 0)} – ${fmt(last.upper_80 || 0)}</div>
          </div>`;
      } catch (err) {
        shadow.innerHTML = `<style>${STYLE}</style><div class="error">EIBO: ${err.message}</div>`;
      }
    }
  }

  if (!customElements.get('eibo-budget-chip')) {
    customElements.define('eibo-budget-chip', EiboBudgetChip);
  }
})();
