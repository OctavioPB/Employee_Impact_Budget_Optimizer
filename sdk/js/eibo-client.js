/**
 * EIBO JavaScript/TypeScript Client SDK — Sprint 19
 * Typed fetch wrapper for the /api/v1/ public API.
 *
 * Usage (browser or Node ≥ 18):
 *   import { EiboClient } from './eibo-client.js'
 *
 *   const client = new EiboClient({ apiKey: 'eibo_analyst_…', baseUrl: 'http://eibo.internal' })
 *   const kpis   = await client.dashboard({ scenario: 'A', size: 'medium' })
 *   console.log(kpis.headcount, kpis.avgImpactScore)
 *
 * @typedef {{ scenario: string, size: string, headcount: number, departments: number,
 *             avgImpactScore: number, avgAttrition: number, nexusCount: number,
 *             totalPayroll: number, scope: string }} DashboardKPIs
 *
 * @typedef {{ employeeId: string, roleTitle: string, department: string, seniority: string,
 *             impactScore: number, attritionRisk: number, isNexus: boolean,
 *             annualSalary?: number }} ImpactEmployee
 *
 * @typedef {{ scenario: string, size: string, scope: string, count: number,
 *             employees: ImpactEmployee[] }} ImpactData
 *
 * @typedef {{ critical: number, high: number, moderate: number, low: number }} AttritionDist
 *
 * @typedef {{ scenario: string, size: string, headcount: number, avgRisk: number,
 *             distribution: AttritionDist, nexusAtRisk: number }} AttritionSummary
 *
 * @typedef {{ department: string, ohiScore: number, grade: string, headcount: number }} OHIDept
 *
 * @typedef {{ scenario: string, size: string, compositeScore: number, grade: string,
 *             subIndices: object[], departmentOhi: OHIDept[] }} OHISummary
 *
 * @typedef {{ monthOffset: number, forecastBudget: number,
 *             lower80: number, upper80: number }} ForecastMonth
 *
 * @typedef {{ scenario: string, size: string, monthlyBaseline: number, annualBudget: number,
 *             forecastHorizon: number, forecast: ForecastMonth[] }} ForecastData
 */

export class EiboError extends Error {
  /** @param {number} status @param {string} body */
  constructor(status, body) {
    super(`EIBO API error ${status}: ${body}`);
    this.status = status;
  }
}

export class EiboClient {
  /**
   * @param {{ apiKey?: string, baseUrl?: string, timeout?: number }} opts
   */
  constructor({
    apiKey  = 'eibo_demo_sandbox0000000000000000',
    baseUrl = 'http://localhost:8000',
    timeout = 30000,
  } = {}) {
    this._key     = apiKey;
    this._base    = baseUrl.replace(/\/$/, '');
    this._timeout = timeout;
  }

  /**
   * @param {string} path
   * @param {Record<string,string>} [params]
   * @returns {Promise<unknown>}
   */
  async _get(path, params = {}) {
    const qs  = new URLSearchParams(params).toString();
    const url = `${this._base}${path}${qs ? '?' + qs : ''}`;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this._timeout);
    try {
      const resp = await fetch(url, {
        headers: { Authorization: `Bearer ${this._key}` },
        signal: controller.signal,
      });
      clearTimeout(timer);
      const body = await resp.text();
      if (!resp.ok) throw new EiboError(resp.status, body);
      return JSON.parse(body);
    } finally {
      clearTimeout(timer);
    }
  }

  /** Ping the v1 API. @returns {Promise<{ status: string, version: string }>} */
  async health() {
    return /** @type {any} */ (await this._get('/api/v1/health'));
  }

  /**
   * Org-level KPI summary.
   * @param {{ scenario?: string, size?: string }} [opts]
   * @returns {Promise<DashboardKPIs>}
   */
  async dashboard({ scenario = 'A', size = 'small' } = {}) {
    const d = /** @type {any} */ (await this._get('/api/v1/dashboard', { scenario, size }));
    return {
      scenario:         d.scenario,
      size:             d.size,
      headcount:        d.headcount,
      departments:      d.departments,
      avgImpactScore:   d.avg_impact_score,
      avgAttrition:     d.avg_attrition,
      nexusCount:       d.nexus_count,
      totalPayroll:     d.total_payroll,
      scope:            d.scope,
    };
  }

  /**
   * Impact scores for employees.
   * @param {{ scenario?: string, size?: string, limit?: number }} [opts]
   * @returns {Promise<ImpactData>}
   */
  async impact({ scenario = 'A', size = 'small', limit = 100 } = {}) {
    const d = /** @type {any} */ (await this._get('/api/v1/impact', { scenario, size, limit: String(limit) }));
    return {
      scenario:  d.scenario,
      size:      d.size,
      scope:     d.scope,
      count:     d.count,
      employees: (d.employees || []).map(e => ({
        employeeId:    e.employee_id,
        roleTitle:     e.role_title,
        department:    e.department,
        seniority:     e.seniority,
        impactScore:   e.impact_score,
        attritionRisk: e.attrition_risk,
        isNexus:       e.is_nexus,
        annualSalary:  e.annual_salary,
      })),
    };
  }

  /**
   * Org-level attrition risk distribution.
   * @param {{ scenario?: string, size?: string }} [opts]
   * @returns {Promise<AttritionSummary>}
   */
  async attritionSummary({ scenario = 'A', size = 'small' } = {}) {
    const d = /** @type {any} */ (await this._get('/api/v1/attrition-summary', { scenario, size }));
    return {
      scenario:     d.scenario,
      size:         d.size,
      headcount:    d.headcount,
      avgRisk:      d.avg_risk,
      distribution: d.distribution,
      nexusAtRisk:  d.nexus_at_risk,
    };
  }

  /**
   * OHI composite score and department breakdown.
   * @param {{ scenario?: string, size?: string }} [opts]
   * @returns {Promise<OHISummary>}
   */
  async ohi({ scenario = 'A', size = 'small' } = {}) {
    const d = /** @type {any} */ (await this._get('/api/v1/ohi', { scenario, size }));
    return {
      scenario:       d.scenario,
      size:           d.size,
      compositeScore: d.composite_score,
      grade:          d.grade,
      subIndices:     d.sub_indices || [],
      departmentOhi:  (d.department_ohi || []).map(r => ({
        department: r.department,
        ohiScore:   r.ohi_score,
        grade:      r.grade,
        headcount:  r.headcount,
      })),
    };
  }

  /**
   * 6-month budget forecast with confidence bands.
   * @param {{ scenario?: string, size?: string }} [opts]
   * @returns {Promise<ForecastData>}
   */
  async forecast({ scenario = 'A', size = 'small' } = {}) {
    const d = /** @type {any} */ (await this._get('/api/v1/forecast', { scenario, size }));
    return {
      scenario:        d.scenario,
      size:            d.size,
      monthlyBaseline: d.monthly_baseline,
      annualBudget:    d.annual_budget,
      forecastHorizon: d.forecast_horizon,
      forecast:        (d.forecast || []).map(m => ({
        monthOffset:    m.month_offset,
        forecastBudget: m.forecast_budget,
        lower80:        m.lower_80,
        upper80:        m.upper_80,
      })),
    };
  }
}

export default EiboClient;
