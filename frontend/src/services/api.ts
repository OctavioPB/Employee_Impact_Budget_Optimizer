// UI_Decisions.md §12: All HTTP calls go through this module.
// No component imports fetch directly.
// Pagination is unwrapped here — callers receive T[], not { items: T[] }.

// ── Types ────────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string
}

export interface DepartmentRow {
  department:          string
  headcount:           number
  total_spend:         number
  annual_budget:       number
  budget_variance_pct: number
  avg_impact:          number
  avg_kpi:             number
  fragility_avg:       number
}

export interface EmployeeRow {
  employee_id:    string
  full_name:      string
  role_title:     string
  department:     string
  team_name:      string
  annual_salary:  number
  impact_score:   number
  attrition_risk: number
  is_nexus:       boolean
  top_skill:      string
}

export interface DashboardData {
  org_name:            string
  scenario_id:         string
  org_size:            string
  total_headcount:     number
  total_spend:         number
  total_budget:        number
  avg_impact_score:    number
  budget_variance_pct: number
  n_nexus_employees:   number
  n_at_risk_teams:     number
  scoring_mode:        string
  dept_summary:        DepartmentRow[]
  employee_table:      EmployeeRow[]
}

export interface SimulationRequest {
  scenario:    string
  size:        string
  budget_pct:  number
  force_retain: string[]
  exclude:      string[]
  leadership_constraint:  boolean
  skills_constraint:      boolean
}

export interface SimulationEmployee {
  employee_id:  string
  full_name:    string
  department:   string
  role_title:   string
  annual_salary: number
  impact_score:  number
  is_nexus:      boolean
  retained:      boolean
  override:      boolean
}

export interface SimulationResult {
  retained_count:  number
  at_risk_count:   number
  total_retained_cost: number
  total_at_risk_cost:  number
  budget_used_pct: number
  total_impact:    number
  employees:       SimulationEmployee[]
  feasible:        boolean
  infeasibility_reason: string | null
}

export interface AttritionEmployee {
  employee_id:    string
  full_name:      string
  department:     string
  role_title:     string
  attrition_risk: number
  risk_category:  'Low' | 'Moderate' | 'High' | 'Critical'
  top_driver:     string
}

export interface AttritionData {
  high_risk_count:     number
  critical_risk_count: number
  avg_risk:            number
  employees:           AttritionEmployee[]
}

export interface Notification {
  id:         string
  title:      string
  body:       string
  severity:   'info' | 'warning' | 'critical'
  created_at: string
  read:       boolean
}

// ── Base request ─────────────────────────────────────────────────────────

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`${res.status} ${text}`)
  }
  return res.json() as Promise<T>
}

// ── API surface ───────────────────────────────────────────────────────────

export const api = {
  health: () =>
    request<HealthResponse>('/api/health'),

  dashboard: {
    data: (scenario: string, size: string, demo = true) =>
      request<DashboardData>(
        `/api/dashboard?scenario=${scenario}&size=${size}&demo=${demo}`,
      ),
  },

  simulation: {
    run: (body: SimulationRequest) =>
      request<SimulationResult>('/api/simulate', {
        method: 'POST',
        body:   JSON.stringify(body),
      }),
  },

  predictive: {
    attrition: (scenario: string, size: string, demo = true) =>
      request<AttritionData>(
        `/api/predictive/attrition?scenario=${scenario}&size=${size}&demo=${demo}`,
      ),
  },

  notifications: {
    list: () =>
      request<Notification[]>('/api/notifications'),
    markRead: (id: string) =>
      request<void>(`/api/notifications/${id}/read`, { method: 'POST' }),
  },
}
