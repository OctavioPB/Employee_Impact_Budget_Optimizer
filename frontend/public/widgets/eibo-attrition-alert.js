/**
 * EIBO Widget: Attrition Risk Alert
 * Usage:
 *   <script src="/widgets/eibo-attrition-alert.js"></script>
 *   <eibo-attrition-alert api-key="eibo_…" base-url="http://eibo.internal"
 *                         scenario="A" size="small"></eibo-attrition-alert>
 */
(function () {
  const STYLE = `
    :host { display: inline-block; font-family: sans-serif; }
    .card {
      background: #fff; border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.10);
      padding: 14px 18px; min-width: 200px; max-width: 280px;
    }
    .label   { font-size: 9px; letter-spacing: 2px; text-transform: uppercase; color: #6b7280; margin-bottom: 10px; }
    .row     { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
    .tier    { font-size: 11px; color: #374151; }
    .count   { font-size: 15px; font-weight: 700; }
    .bar-bg  { height: 4px; background: #f3f4f6; border-radius: 2px; flex: 1; margin: 0 10px; }
    .bar     { height: 4px; border-radius: 2px; }
    .nexus   { font-size: 10px; color: #6b7280; margin-top: 10px; border-top: 1px solid #f3f4f6; padding-top: 8px; }
    .error   { color: #dc2626; font-size: 11px; padding: 10px; }
    .loading { color: #9ca3af; font-size: 11px; padding: 10px; }
  `;

  const TIERS = [
    { key: 'critical', label: 'Critical Risk',  color: '#dc2626' },
    { key: 'high',     label: 'High Risk',      color: '#f97316' },
    { key: 'moderate', label: 'Moderate Risk',  color: '#facc15' },
    { key: 'low',      label: 'Low Risk',       color: '#22c55e' },
  ];

  class EiboAttritionAlert extends HTMLElement {
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
          `${baseUrl}/api/v1/attrition-summary?scenario=${scenario}&size=${size}`,
          { headers: { Authorization: `Bearer ${apiKey}` } },
        );
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();

        const dist  = data.distribution || {};
        const total = data.headcount || 1;
        const rows  = TIERS.map(t => {
          const n   = dist[t.key] || 0;
          const pct = Math.round((n / total) * 100);
          return `<div class="row">
            <span class="tier">${t.label}</span>
            <div class="bar-bg"><div class="bar" style="width:${pct}%;background:${t.color}"></div></div>
            <span class="count" style="color:${t.color}">${n}</span>
          </div>`;
        }).join('');

        shadow.innerHTML = `<style>${STYLE}</style>
          <div class="card">
            <div class="label">Attrition Risk Alert · ${total} employees</div>
            ${rows}
            <div class="nexus">
              ${data.nexus_at_risk || 0} nexus employee${data.nexus_at_risk !== 1 ? 's' : ''} at elevated risk
            </div>
          </div>`;
      } catch (err) {
        shadow.innerHTML = `<style>${STYLE}</style><div class="error">EIBO: ${err.message}</div>`;
      }
    }
  }

  if (!customElements.get('eibo-attrition-alert')) {
    customElements.define('eibo-attrition-alert', EiboAttritionAlert);
  }
})();
