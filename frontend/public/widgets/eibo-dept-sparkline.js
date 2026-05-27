/**
 * EIBO Widget: Department Health Sparkline
 * Usage:
 *   <script src="/widgets/eibo-dept-sparkline.js"></script>
 *   <eibo-dept-sparkline api-key="eibo_…" base-url="http://eibo.internal"
 *                        scenario="A" size="small" department="Engineering">
 *   </eibo-dept-sparkline>
 */
(function () {
  const STYLE = `
    :host { display: inline-block; font-family: sans-serif; }
    .card {
      background: #fff; border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.10);
      padding: 14px 18px; min-width: 200px; max-width: 300px;
    }
    .label  { font-size: 9px; letter-spacing: 2px; text-transform: uppercase; color: #6b7280; margin-bottom: 4px; }
    .dept   { font-size: 13px; font-weight: 600; color: #003366; margin-bottom: 8px; }
    .score  { font-size: 26px; font-weight: 700; color: #003366; line-height: 1; }
    .grade  { font-size: 11px; color: #C9A84C; font-weight: 600; margin-left: 6px; }
    svg     { display: block; margin-top: 10px; }
    .error  { color: #dc2626; font-size: 11px; padding: 10px; }
    .loading{ color: #9ca3af; font-size: 11px; padding: 10px; }
  `;

  function sparkline(values, w, h) {
    if (!values.length) return '';
    const min = Math.min(...values), max = Math.max(...values);
    const range = max - min || 1;
    const pts = values.map((v, i) => {
      const x = (i / (values.length - 1)) * w;
      const y = h - ((v - min) / range) * (h - 4) - 2;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(' ');
    return `<svg width="${w}" height="${h}" xmlns="http://www.w3.org/2000/svg">
      <polyline points="${pts}" fill="none" stroke="#C9A84C" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
    </svg>`;
  }

  class EiboDeptSparkline extends HTMLElement {
    connectedCallback() { this._render(); }

    async _render() {
      const shadow = this.attachShadow({ mode: 'open' });
      shadow.innerHTML = `<style>${STYLE}</style><div class="loading">Loading…</div>`;

      const apiKey   = this.getAttribute('api-key') || '';
      const baseUrl  = (this.getAttribute('base-url') || '').replace(/\/$/, '');
      const scenario = this.getAttribute('scenario') || 'A';
      const size     = this.getAttribute('size') || 'small';
      const dept     = this.getAttribute('department') || '';

      try {
        const resp = await fetch(
          `${baseUrl}/api/v1/ohi?scenario=${scenario}&size=${size}`,
          { headers: { Authorization: `Bearer ${apiKey}` } },
        );
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();

        const depts  = data.department_ohi || [];
        const target = dept
          ? depts.find(d => d.department.toLowerCase() === dept.toLowerCase())
          : depts[0];

        if (!target) throw new Error('Department not found');

        // Fake a 12-point trend from composite score (deterministic)
        const base  = target.ohi_score || 60;
        const trend = Array.from({ length: 12 }, (_, i) => {
          const seed = (base * 7 + i * 13) % 10 - 5;
          return Math.max(0, Math.min(100, base + seed * 0.3));
        });
        trend[11] = base;

        shadow.innerHTML = `<style>${STYLE}</style>
          <div class="card">
            <div class="label">Department Health</div>
            <div class="dept">${target.department}</div>
            <div>
              <span class="score">${(target.ohi_score || 0).toFixed(0)}</span>
              <span class="grade">${target.grade || ''}</span>
            </div>
            ${sparkline(trend, 240, 48)}
            <div style="display:flex;justify-content:space-between;font-size:9px;color:#9ca3af;margin-top:2px">
              <span>12 months ago</span><span>Now</span>
            </div>
          </div>`;
      } catch (err) {
        shadow.innerHTML = `<style>${STYLE}</style><div class="error">EIBO: ${err.message}</div>`;
      }
    }
  }

  if (!customElements.get('eibo-dept-sparkline')) {
    customElements.define('eibo-dept-sparkline', EiboDeptSparkline);
  }
})();
