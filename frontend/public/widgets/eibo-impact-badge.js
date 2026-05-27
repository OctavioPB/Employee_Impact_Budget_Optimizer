/**
 * EIBO Widget: Impact Score Badge
 * Usage:
 *   <script src="/widgets/eibo-impact-badge.js"></script>
 *   <eibo-impact-badge api-key="eibo_…" base-url="http://eibo.internal"
 *                      scenario="A" size="small"></eibo-impact-badge>
 *
 * No external dependencies. Uses Shadow DOM for style isolation.
 */
(function () {
  const STYLE = `
    :host { display: inline-block; font-family: sans-serif; }
    .card {
      background: #fff; border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.10);
      padding: 14px 18px; min-width: 180px; max-width: 260px;
      border-left: 3px solid #C9A84C;
    }
    .label { font-size: 9px; letter-spacing: 2px; text-transform: uppercase;
             color: #6b7280; margin-bottom: 6px; }
    .score { font-size: 36px; font-weight: 700; color: #003366; line-height: 1; }
    .unit  { font-size: 13px; color: #9ca3af; margin-left: 2px; }
    .driver { font-size: 11px; color: #374151; margin-top: 6px; line-height: 1.4; }
    .nexus { display: inline-block; font-size: 8px; letter-spacing: 1.5px;
             text-transform: uppercase; background: rgba(201,168,76,0.15);
             color: #C9A84C; padding: 2px 7px; border-radius: 99px; margin-top: 6px; }
    .risk-bar-bg { height: 4px; background: #f3f4f6; border-radius: 2px; margin-top: 10px; }
    .risk-bar    { height: 4px; border-radius: 2px; }
    .error { color: #dc2626; font-size: 11px; padding: 10px; }
    .loading { color: #9ca3af; font-size: 11px; padding: 10px; }
  `;

  function riskColor(r) {
    if (r >= 0.81) return '#dc2626';
    if (r >= 0.61) return '#f97316';
    if (r >= 0.31) return '#facc15';
    return '#22c55e';
  }

  class EiboImpactBadge extends HTMLElement {
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
          `${baseUrl}/api/v1/impact?scenario=${scenario}&size=${size}&limit=1`,
          { headers: { Authorization: `Bearer ${apiKey}` } },
        );
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        const emp  = (data.employees || [])[0];
        if (!emp) throw new Error('No employee data');

        const score = emp.impact_score || 0;
        const risk  = emp.attrition_risk || 0;
        const color = riskColor(risk);
        const riskPct = Math.round(risk * 100);

        shadow.innerHTML = `<style>${STYLE}</style>
          <div class="card">
            <div class="label">Impact Score</div>
            <div><span class="score">${score.toFixed(0)}</span><span class="unit">/100</span></div>
            <div class="driver">${emp.role_title || 'Employee'} · ${emp.department || ''}</div>
            ${emp.is_nexus ? '<span class="nexus">Nexus Employee</span>' : ''}
            <div class="risk-bar-bg">
              <div class="risk-bar" style="width:${riskPct}%;background:${color}"></div>
            </div>
            <div style="font-size:9px;color:#6b7280;margin-top:3px">Attrition risk: ${riskPct}%</div>
          </div>`;
      } catch (err) {
        shadow.innerHTML = `<style>${STYLE}</style><div class="error">EIBO: ${err.message}</div>`;
      }
    }
  }

  if (!customElements.get('eibo-impact-badge')) {
    customElements.define('eibo-impact-badge', EiboImpactBadge);
  }
})();
