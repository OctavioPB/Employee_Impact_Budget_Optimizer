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

export interface ForecastHistoryPoint {
  ds: string
  y:  number
}

export interface ForecastFuturePoint {
  ds:            string
  yhat:          number
  yhat_lower_80: number
  yhat_upper_80: number
  yhat_lower_95: number
  yhat_upper_95: number
}

export interface ForecastSeries {
  label:    string
  metric:   string
  model:    string
  mape:     number
  history:  ForecastHistoryPoint[]
  forecast: ForecastFuturePoint[]
}

export interface ForecastData {
  generated_at:  string
  total_spend:   ForecastSeries
  headcount:     ForecastSeries | null
  by_department: ForecastSeries[]
}

export interface FanChartPoint {
  ds:          string
  p10:         number
  p50:         number
  p90:         number
  mean:        number
  budget_line: number
}

export interface ExceedancePoint {
  ds:               string
  prob_over_budget: number
}

export interface MonteCarloData {
  n_simulations:            number
  annual_budget:            number
  monthly_budget:           number
  prob_overspend_any_month: number
  final_month:              { p10: number; p50: number; p90: number; mean: number }
  fan_chart:                FanChartPoint[]
  exceedance_prob:          ExceedancePoint[]
  notes:                    string[]
}

export interface GenerateRequest {
  scenario:        string
  size:            string
  seed:            number
  org_name:        string
  nexus_fraction:  number
  budget_variance: number
}

export interface GenerateResult {
  status:      string
  org_name:    string
  scenario_id: string
  org_size:    string
  headcount:   number
  departments: number
}

export interface ResetResult {
  status:          string
  cleared_entries: number
}

export interface CompensationSummary {
  total_employees:     number
  median_comp_ratio:   number
  pct_below_market:    number
  pct_at_market:       number
  pct_above_market:    number
  avg_equity_gap_pct:  number
  high_roi_candidates: number
}

export interface CompensationEmployee {
  employee_id:       string
  full_name:         string
  department:        string
  seniority_level:   string
  role_title:        string
  annual_salary:     number
  market_median:     number
  comp_ratio:        number
  market_tier:       'Below Market' | 'At Market' | 'Above Market'
  demographic_group: 'Group A' | 'Group B'
}

export interface DeptEquityRow {
  department:        string
  headcount:         number
  group_a_count:     number
  group_b_count:     number
  group_a_median:    number
  group_b_median:    number
  raw_gap_pct:       number
  adjusted_gap_pct:  number
  p_value:           number
  significant:       boolean
}

export interface RetentionRoiRow {
  employee_id:       string
  full_name:         string
  department:        string
  seniority_level:   string
  role_title:        string
  annual_salary:     number
  market_median:     number
  comp_ratio:        number
  correction_cost:   number
  replacement_cost:  number
  roi:               number
}

export interface CompensationData {
  summary:       CompensationSummary
  employees:     CompensationEmployee[]
  dept_equity:   DeptEquityRow[]
  retention_roi: RetentionRoiRow[]
}

export interface KnowledgeSummary {
  total_domains:       number
  skh_domains:         number
  uncovered_domains:   number
  skh_employees:       number
  avg_knowledge_loss:  number
  high_risk_employees: number
}

export interface KnowledgeEmployee {
  employee_id:          string
  full_name:            string
  department:           string
  seniority_level:      string
  role_title:           string
  knowledge_loss_score: number
  domain_count:         number
  skh_domains:          string[]
  is_skh:               boolean
}

export interface KnowledgeDomain {
  domain_id:          string
  name:               string
  criticality:        number
  holder_count:       number
  is_skh:             boolean
  is_uncovered:       boolean
  primary_holder:     string
  backup_holder:      string
  backup_proficiency: number
  coverage_ratio:     number
}

export interface TransferRow {
  domain_id:             string
  domain_name:           string
  criticality:           number
  is_skh:                boolean
  current_holder:        string
  current_holder_dept:   string
  current_proficiency:   number
  successor:             string
  successor_proficiency: number
  proficiency_gap:       number
  transfer_months:       number
  transfer_cost:         number
  urgency_score:         number
}

export interface HeatmapEmployee {
  employee_id:          string
  full_name:            string
  department:           string
  knowledge_loss_score: number
}

export interface HeatmapDomain {
  domain_id:   string
  name:        string
  criticality: number
}

export interface HeatmapCell {
  employee_id: string
  domain_id:   string
  proficiency: number
  is_skh:      boolean
}

export interface KnowledgeData {
  summary:          KnowledgeSummary
  employees:        KnowledgeEmployee[]
  domains:          KnowledgeDomain[]
  transfer_roadmap: TransferRow[]
  heatmap: {
    employees: HeatmapEmployee[]
    domains:   HeatmapDomain[]
    cells:     HeatmapCell[]
  }
}

export interface MobilitySummary {
  total_employees:    number
  stagnated_count:    number
  avg_stagnation:     number
  career_paths_count: number
  succession_gaps:    number
  leaders_mapped:     number
}

export interface CareerSuggestion {
  role_title:      string
  department:      string
  seniority:       string
  skill_overlap:   number
  gap_skills:      string[]
  training_cost:   number
  timeline_months: number
  target_salary:   number
  salary_uplift:   number
  roi:             number
}

export interface CareerPath {
  employee_id:      string
  full_name:        string
  department:       string
  seniority_level:  string
  role_title:       string
  annual_salary:    number
  stagnation_score: number
  current_skills:   string[]
  suggestions:      CareerSuggestion[]
}

export interface StagnationDeptRow {
  department: string
  avg_score:  number
  count:      number
}

export interface StagnationHeatCell {
  department:      string
  seniority_level: string
  avg_score:       number
  count:           number
}

export interface StagnationEmployee {
  employee_id:      string
  full_name:        string
  department:       string
  seniority_level:  string
  role_title:       string
  tenure_days:      number
  stagnation_score: number
  annual_salary:    number
}

export interface SuccessionRow {
  employee_id:      string
  leader_name:      string
  role_title:       string
  department:       string
  seniority_level:  string
  depth_1:          string[]
  depth_2:          string[]
  depth_3:          string[]
  depth_1_count:    number
  depth_2_count:    number
  depth_3_count:    number
  succession_gap:   boolean
}

export interface MobilityData {
  summary:       MobilitySummary
  career_paths:  CareerPath[]
  stagnation: {
    dept_summary:        StagnationDeptRow[]
    dept_seniority_heat: StagnationHeatCell[]
    high_risk:           StagnationEmployee[]
  }
  succession: SuccessionRow[]
}

export interface FairnessGroupStat {
  group:                string
  count:                number
  selected:             number
  selection_rate:       number
  avg_score:            number
  adverse_impact_ratio: number
  is_reference:         boolean
  eeoc_pass:            boolean
}

export interface EEOCRow {
  dimension:   string
  model:       string
  score_col:   string
  groups:      FairnessGroupStat[]
  min_air:     number
  eeoc_pass:   boolean
  chi2_stat:   number
  chi2_pval:   number
  significant: boolean
}

export interface SimSelectionRow {
  group:                string
  count:                number
  selected:             number
  selection_rate:       number
  adverse_impact_ratio: number
  eeoc_pass:            boolean
}

export interface CounterfactualRow {
  attribute:    string
  model:        string
  sample_size:  number
  mean_delta:   number
  std_delta:    number
  ci_lower_95:  number
  ci_upper_95:  number
  is_fair:      boolean
}

export interface GroupProfile {
  dimension:        string
  group:            string
  count:            number
  avg_impact_score: number
  avg_attrition:    number
  median_salary:    number
}

export interface FairnessSummary {
  total_employees:      number
  eeoc_threshold:       number
  dimensions_tested:    number
  model_outputs_tested: number
  eeoc_flags:           number
  sim_flags:            number
  overall_pass:         boolean
  counterfactual_fair:  boolean
}

export interface FairnessData {
  summary:            FairnessSummary
  protected_groups:   Record<string, { group: string; count: number }[]>
  group_profiles:     GroupProfile[]
  eeoc_analysis:      EEOCRow[]
  simulation_analysis: Record<string, SimSelectionRow[]>
  counterfactual:     CounterfactualRow[]
  note:               string
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

  admin: {
    resetDemo: () =>
      request<ResetResult>('/api/admin/demo/reset', { method: 'POST' }),
    generateDemo: (body: GenerateRequest) =>
      request<GenerateResult>('/api/admin/demo/generate', {
        method: 'POST',
        body:   JSON.stringify(body),
      }),
  },

  forecast: {
    budget: (scenario: string, size: string, demo = true) =>
      request<ForecastData>(
        `/api/forecast/budget?scenario=${scenario}&size=${size}&demo=${demo}`,
      ),
    monteCarlo: (scenario: string, size: string, demo = true) =>
      request<MonteCarloData>(
        `/api/forecast/montecarlo?scenario=${scenario}&size=${size}&demo=${demo}`,
      ),
  },

  compensation: {
    data: (scenario: string, size: string, demo = true) =>
      request<CompensationData>(
        `/api/compensation?scenario=${scenario}&size=${size}&demo=${demo}`,
      ),
  },

  knowledge: {
    data: (scenario: string, size: string, demo = true) =>
      request<KnowledgeData>(
        `/api/knowledge?scenario=${scenario}&size=${size}&demo=${demo}`,
      ),
  },

  mobility: {
    data: (scenario: string, size: string, demo = true) =>
      request<MobilityData>(
        `/api/mobility?scenario=${scenario}&size=${size}&demo=${demo}`,
      ),
  },

  fairness: {
    data: (scenario: string, size: string, demo = true) =>
      request<FairnessData>(
        `/api/fairness?scenario=${scenario}&size=${size}&demo=${demo}`,
      ),
  },

  decisionRoom: {
    list:   () =>
      request<DecisionSession[]>('/api/decision-room/sessions'),
    seed:   (scenario: string, size: string) =>
      request<DecisionSession>('/api/decision-room/sessions/seed', {
        method: 'POST', body: JSON.stringify({ scenario, size }),
      }),
    create: (body: CreateSessionBody) =>
      request<DecisionSession>('/api/decision-room/sessions', {
        method: 'POST', body: JSON.stringify(body),
      }),
    get:    (id: string) =>
      request<DecisionSession>(`/api/decision-room/sessions/${id}`),
    join:   (id: string, body: { user_id: string; display_name: string; role: string }) =>
      request<DecisionSession>(`/api/decision-room/sessions/${id}/join`, {
        method: 'POST', body: JSON.stringify(body),
      }),
    updateStatus: (id: string, new_status: string, updated_by: string) =>
      request<DecisionSession>(`/api/decision-room/sessions/${id}/status`, {
        method: 'PUT', body: JSON.stringify({ new_status, updated_by }),
      }),
    addOverride: (id: string, body: {
      employee_id: string; employee_name: string;
      override_type: string; set_by: string; rationale: string
    }) =>
      request<DecisionSession>(`/api/decision-room/sessions/${id}/overrides`, {
        method: 'POST', body: JSON.stringify(body),
      }),
    removeOverride: (id: string, employee_id: string, set_by: string) =>
      request<DecisionSession>(`/api/decision-room/sessions/${id}/overrides/${employee_id}`, {
        method: 'DELETE', body: JSON.stringify({ set_by }),
      }),
    resolveConflict: (id: string, employee_id: string, resolution: string, resolved_by: string) =>
      request<DecisionSession>(`/api/decision-room/sessions/${id}/conflicts/${employee_id}/resolve`, {
        method: 'POST', body: JSON.stringify({ resolution, resolved_by }),
      }),
    addComment: (id: string, body: {
      employee_id: string; employee_name: string; author: string; body: string
    }) =>
      request<DecisionSession>(`/api/decision-room/sessions/${id}/comments`, {
        method: 'POST', body: JSON.stringify(body),
      }),
    addProposal: (id: string, body: {
      employee_id: string; employee_name: string;
      override_type: string; rationale: string; proposed_by: string
    }) =>
      request<DecisionSession>(`/api/decision-room/sessions/${id}/proposals`, {
        method: 'POST', body: JSON.stringify(body),
      }),
    addObjection: (id: string, proposal_id: string, objector: string, reason: string) =>
      request<DecisionSession>(
        `/api/decision-room/sessions/${id}/proposals/${proposal_id}/objection`, {
        method: 'POST', body: JSON.stringify({ objector, reason }),
      }),
    openVote: (id: string, proposal_id: string, opened_by: string) =>
      request<DecisionSession>(
        `/api/decision-room/sessions/${id}/proposals/${proposal_id}/open-vote`, {
        method: 'POST', body: JSON.stringify({ opened_by }),
      }),
    castVote: (id: string, proposal_id: string, voter: string, decision: string) =>
      request<DecisionSession>(
        `/api/decision-room/sessions/${id}/proposals/${proposal_id}/vote`, {
        method: 'POST', body: JSON.stringify({ voter, decision }),
      }),
    signOff: (id: string, user_id: string, display_name: string, comment: string) =>
      request<DecisionSession>(`/api/decision-room/sessions/${id}/sign-off`, {
        method: 'POST', body: JSON.stringify({ user_id, display_name, comment }),
      }),
  },

  resilience: {
    data: (scenario: string, size: string, demo = true) =>
      request<ResilienceData>(
        `/api/resilience?scenario=${scenario}&size=${size}&demo=${demo}`,
      ),
    runScenario: (scenario: string, size: string, scenario_type: string, params: Record<string, unknown>) =>
      request<DisruptionResult>('/api/resilience/scenario', {
        method: 'POST',
        body:   JSON.stringify({ scenario, size, scenario_type, params }),
      }),
  },

  ld: {
    data: (scenario: string, size: string, demo = true) =>
      request<LDData>(
        `/api/ld?scenario=${scenario}&size=${size}&demo=${demo}`,
      ),
    optimize: (body: { scenario: string; size: string; budget: number; max_per_employee: number; close_gaps: boolean }) =>
      request<LDOptimizationResult>('/api/ld/optimize', {
        method: 'POST',
        body:   JSON.stringify(body),
      }),
    pareto: (body: { scenario: string; size: string; total_budget: number }) =>
      request<ParetoPoint[]>('/api/ld/pareto', {
        method: 'POST',
        body:   JSON.stringify(body),
      }),
  },

  ohi: {
    data: (scenario: string, size: string, demo = true) =>
      request<OHIData>(
        `/api/ohi?scenario=${scenario}&size=${size}&demo=${demo}`,
      ),
    preview: (body: { scenario: string; size: string; retention_pct: number }) =>
      request<OHIPreviewResult>('/api/ohi/preview', {
        method: 'POST', body: JSON.stringify(body),
      }),
  },

  narrative: {
    data: (scenario: string, size: string, demo = true) =>
      request<NarrativePageData>(
        `/api/narrative?scenario=${scenario}&size=${size}&demo=${demo}`,
      ),
    status: () =>
      request<OllamaStatus>('/api/narrative/status'),
    impact: (body: NarrativeRequest) =>
      request<NarrativeResult>('/api/narrative/impact', {
        method: 'POST', body: JSON.stringify(body),
      }),
    attrition: (body: NarrativeRequest) =>
      request<NarrativeResult>('/api/narrative/attrition', {
        method: 'POST', body: JSON.stringify(body),
      }),
    simulation: (body: NarrativeRequest) =>
      request<NarrativeResult>('/api/narrative/simulation', {
        method: 'POST', body: JSON.stringify(body),
      }),
    brief: (body: NarrativeRequest) =>
      request<NarrativeResult>('/api/narrative/brief', {
        method: 'POST', body: JSON.stringify(body),
      }),
  },

  apiKeys: {
    list:    ()                         => request<ApiKeyRecord[]>('/api/v1/api-keys'),
    scopes:  ()                         => request<string[]>('/api/v1/api-keys/scopes'),
    sandbox: ()                         => request<{ key: string; scope: string; label: string }>('/api/v1/api-keys/sandbox'),
    create:  (body: ApiKeyCreateRequest) => request<ApiKeyCreateResult>('/api/v1/api-keys', {
      method: 'POST', body: JSON.stringify(body),
    }),
    revoke:  (keyId: string)            => request<{ status: string; key_id: string }>(`/api/v1/api-keys/${keyId}`, { method: 'DELETE' }),
    verify:  (key: string)              => request<{ valid: boolean; scope: string; label: string }>('/api/v1/api-keys/verify', {
      method: 'POST', body: JSON.stringify({ key }),
    }),
  },

  pulse: {
    data: (scenario: string, size: string, demo = true) =>
      request<PulseData>(`/api/pulse?scenario=${scenario}&size=${size}&demo=${demo}`),
  },

  webhooks: {
    list:       ()                               => request<WebhookRecord[]>('/api/v1/webhooks'),
    eventTypes: ()                               => request<string[]>('/api/v1/webhooks/event-types'),
    create:     (body: WebhookCreateRequest)     => request<WebhookRecord & { secret: string }>('/api/v1/webhooks', {
      method: 'POST', body: JSON.stringify(body),
    }),
    remove:     (id: string)                     => request<{ status: string }>(`/api/v1/webhooks/${id}`, { method: 'DELETE' }),
    setActive:  (id: string, active: boolean)    => request<{ status: string; active: boolean }>(`/api/v1/webhooks/${id}`, {
      method: 'PATCH', body: JSON.stringify({ active }),
    }),
    test:       (id: string)                     => request<WebhookDeliveryLog>(`/api/v1/webhooks/${id}/test`, { method: 'POST' }),
  },
}

// ── Decision Room types ───────────────────────────────────────────────────────

export interface SessionParticipant {
  user_id:      string
  display_name: string
  role:         'Owner' | 'Participant' | 'Observer'
  last_action:  string
  joined_at:    string
}

export interface SessionOverride {
  id:            string
  employee_id:   string
  employee_name: string
  override_type: 'retain' | 'exclude'
  set_by:        string
  rationale:     string
  timestamp:     string
}

export interface SessionConflict {
  employee_id:   string
  employee_name: string
  retain_by:     string
  exclude_by:    string
  resolved:      boolean
  resolution:    string | null
  resolved_by:   string | null
  resolved_at:   string | null
}

export interface SessionComment {
  id:            string
  employee_id:   string
  employee_name: string
  author:        string
  body:          string
  timestamp:     string
}

export interface ProposalObjection {
  objector:  string
  reason:    string
  timestamp: string
}

export interface SessionProposal {
  id:            string
  employee_id:   string
  employee_name: string
  override_type: 'retain' | 'exclude'
  rationale:     string
  proposed_by:   string
  timestamp:     string
  objections:    ProposalObjection[]
  votes:         Record<string, 'yes' | 'no'>
  vote_open:     boolean
  vote_result:   'passed' | 'failed' | null
  applied:       boolean
}

export interface ActivityEvent {
  id:        string
  timestamp: string
  actor:     string
  action:    string
  subject:   string
}

export interface SessionSignOff {
  user_id:      string
  display_name: string
  comment:      string
  timestamp:    string
}

export interface DecisionSession {
  session_id:      string
  name:            string
  scenario:        string
  size:            string
  status:          'Draft' | 'Active' | 'Under Review' | 'Finalized'
  budget_pct:      number
  resolution_mode: string
  created_at:      string
  participants:    SessionParticipant[]
  overrides:       SessionOverride[]
  conflicts:       SessionConflict[]
  comments:        SessionComment[]
  proposals:       SessionProposal[]
  sign_offs:       SessionSignOff[]
  activity:        ActivityEvent[]
}

export interface CreateSessionBody {
  name:            string
  owner_name:      string
  owner_id:        string
  scenario:        string
  size:            string
  budget_pct:      number
  resolution_mode: string
}

// ── Resilience types ──────────────────────────────────────────────────────────

export interface ResilienceSubScores {
  skill_coverage:           number
  leadership_depth:         number
  knowledge_redundancy:     number
  network_robustness:       number
  attrition_concentration:  number
  team_size_buffer:         number
}

export interface ResilienceScore {
  overall:    number
  sub_scores: ResilienceSubScores
  weights:    ResilienceSubScores
  grade:      string
}

export interface DeptResilience {
  department:   string
  overall:      number
  headcount:    number
  nexus_count:  number
  at_risk_count:number
  sub_scores:   ResilienceSubScores
  grade:        string
}

export interface CascadeEmployee {
  employee_id:    string
  full_name:      string
  department:     string
  role_title:     string
  impact_score:   number
  attrition_risk: number
  is_nexus:       boolean
  departure_round:number
  trigger_reason: string
}

export interface CascadeRound {
  round:     number
  count:     number
  employees: CascadeEmployee[]
}

export interface CascadeAmplifier {
  employee_id:         string
  full_name:           string
  department:          string
  is_nexus:            boolean
  impact_score:        number
  secondary_triggered: number
}

export interface DisruptionResult {
  scenario_type:       string
  scenario_label:      string
  params:              Record<string, string | number | boolean>
  primary_count:       number
  total_departed:      number
  cascade_multiplier:  number
  financial_impact:    number
  orphaned_skills:     string[]
  teams_below_minimum: string[]
  resilience_before:   number
  resilience_after:    number
  resilience_delta:    number
  cascade_rounds:      CascadeRound[]
  primary_employees:   CascadeEmployee[]
  cascade_amplifiers:  CascadeAmplifier[]
}

export interface DisruptionPreset {
  label:  string
  type:   string
  params: Record<string, string | number | boolean>
}

export interface ResilienceTrendPoint {
  month: string
  score: number
}

export interface ResilienceIntervention {
  dimension:        string
  dimension_label:  string
  description:      string
  current_score:    number
  cost:             number
  score_improvement:number
  priority:         'critical' | 'high' | 'medium' | 'low'
  timeline_months:  number
  roi:              number
}

export interface ResilienceSummary {
  total_employees:         number
  overall_resilience:      number
  grade:                   string
  nexus_count:             number
  at_risk_teams:           number
  top_cascade_amplifier:   string
  intervention_count:      number
}

export interface ResilienceData {
  summary:            ResilienceSummary
  org_resilience:     ResilienceScore
  dept_resilience:    DeptResilience[]
  interventions:      ResilienceIntervention[]
  disruption_presets: DisruptionPreset[]
  trend:              ResilienceTrendPoint[]
}

// ── L&D types ─────────────────────────────────────────────────────────────────

export interface TrainingProgram {
  id:               string
  name:             string
  track:            string
  target_skill:     string
  cost:             number
  duration_weeks:   number
  proficiency_gain: number
  prerequisites:    string[]
  capacity:         number
}

export interface TrainingAllocation {
  employee_id:          string
  full_name:            string
  department:           string
  role_title:           string
  seniority_level:      string
  impact_score:         number
  attrition_risk:       number
  learning_velocity:    number
  program_id:           string
  program_name:         string
  track:                string
  cost:                 number
  duration_weeks:       number
  impact_delta:         number
  attrition_reduction:  number
  roi:                  number
}

export interface LDOptimizationResult {
  budget:                       number
  budget_used:                  number
  total_allocations:            number
  unique_employees:             number
  expected_impact_gain:         number
  expected_attrition_reduction: number
  gap_closures:                 number
  allocations:                  TrainingAllocation[]
  status:                       string
}

export interface ParetoPoint {
  ld_pct:            number
  retention_pct:     number
  ld_budget:         number
  retention_budget:  number
  retention_impact:  number
  ld_impact_gain:    number
  combined_score:    number
}

export interface SkillGapRow {
  department:           string
  skill:                string
  current_holders:      number
  required_holders:     number
  gap_severity:         'critical' | 'high' | 'medium' | 'low'
  recommended_programs: string[]
  internal_closeable:   boolean
  estimated_cost:       number
  affected_employees:   number
}

export interface ROIRecord {
  id:                string
  program_name:      string
  track:             string
  completion_month:  string
  participants:      number
  total_cost:        number
  predicted_roi:     number
  actual_roi:        number
  avg_impact_delta:  number
  status:            'above_forecast' | 'on_target' | 'below_forecast'
}

export interface TrainingProgramEffectiveness {
  program_id:          string
  program_name:        string
  track:               string
  cost:                number
  duration_weeks:      number
  impact_delta:        number
  attrition_reduction: number
  proficiency_gain:    number
  roi:                 number
  eligible:            boolean
}

export interface EmployeePreview {
  employee_id:      string
  full_name:        string
  department:       string
  role_title:       string
  seniority_level:  string
  impact_score:     number
  attrition_risk:   number
  learning_velocity:number
  programs:         TrainingProgramEffectiveness[]
}

export interface LDSummary {
  total_employees:        number
  catalog_size:           number
  skill_gaps:             number
  critical_gaps:          number
  avg_learning_velocity:  number
  default_budget:         number
  expected_impact_gain:   number
}

export interface LDData {
  summary:              LDSummary
  catalog:              TrainingProgram[]
  default_optimization: LDOptimizationResult
  skill_gaps:           SkillGapRow[]
  roi_history:          ROIRecord[]
  pareto_frontier:      ParetoPoint[]
  employee_previews:    EmployeePreview[]
}

// ── OHI types ─────────────────────────────────────────────────────────────────

export interface OHISubIndex {
  score:      number
  grade:      string
  weight:     number
  label:      string
  components: Record<string, number>
  labels:     Record<string, string>
  detail:     string
}

export interface OHIDeptRow {
  department:    string
  score:         number
  grade:         string
  headcount:     number
  nexus_count:   number
  avg_impact:    number
  avg_attrition: number
  sub_scores:    Record<string, number>
}

export interface OHITrendPoint {
  month:       string
  score:       number
  is_forecast: boolean
  event:       string | null
}

export interface OHIBenchmarkBand {
  p25:   number
  p50:   number
  p75:   number
  label: string
}

export interface OHIBenchmark {
  org_size:    string
  comparators: number
  source:      string
  sub_indices: Record<string, OHIBenchmarkBand>
}

export interface OHIDecisionPoint {
  retention_pct:      number
  budget_savings_pct: number
  ohi:                number
  ohi_delta:          number
  n_retained:         number
}

export interface OHIAlert {
  type:     string
  message:  string
  severity: 'critical' | 'high' | 'medium'
}

export interface OHISummary {
  overall:          number
  grade:            string
  trend_direction:  'improving' | 'stable' | 'declining'
  trend_delta_90d:  number
  n_employees:      number
  nexus_count:      number
  alert:            boolean
}

export interface OHIData {
  summary:          OHISummary
  sub_indices:      Record<string, OHISubIndex>
  dept_ohi:         OHIDeptRow[]
  trend:            OHITrendPoint[]
  benchmark:        OHIBenchmark
  decision_preview: OHIDecisionPoint[]
  alert:            OHIAlert | null
}

export interface OHIPreviewResult {
  retention_pct: number
  n_retained:    number
  n_total:       number
  ohi:           number
  ohi_delta:     number
  grade:         string
  sub_indices:   Record<string, number>
}

// ── Narrative types ───────────────────────────────────────────────────────────

export interface OllamaStatus {
  available:     boolean
  model:         string
  base_url:      string
  loaded_models: string[]
}

export interface NarrativeDriver {
  factor:       string
  value:        string
  contribution: number
  direction:    'positive' | 'risk' | 'protective' | 'neutral'
}

export interface NarrativeSourceData {
  anon_id?:         string
  role?:            string
  seniority?:       string
  department?:      string
  impact_score?:    number
  attrition_risk?:  number
  is_nexus?:        boolean
  drivers?:         NarrativeDriver[]
  budget_pct?:      number
  n_retained?:      number
  n_total?:         number
  [key: string]:    unknown
}

export interface NarrativeResult {
  narrative:      string
  is_llm:         boolean
  model:          string
  source_data:    NarrativeSourceData
  disclaimer:     string
  cached:         boolean
  generated_at:   string
  generation_ms?: number
}

export interface NarrativeRequest {
  scenario:    string
  size:        string
  employee_id: string
  budget_pct:  number
}

export interface NarrativeEmployee {
  employee_id:    string
  full_name:      string
  role_title:     string
  department:     string
  seniority_level:string
  impact_score:   number
  attrition_risk: number
  is_nexus:       boolean
}

export interface NarrativeOrgStats {
  n_employees:    number
  total_payroll:  number
  avg_impact:     number
  nexus_count:    number
  high_risk_count:number
}

export interface NarrativePageData {
  ollama_status:          OllamaStatus
  top_impact_employees:   NarrativeEmployee[]
  priority_employees:     NarrativeEmployee[]
  org_stats:              NarrativeOrgStats
}

// ── Sprint 19: API Keys & Webhooks types ──────────────────────────────────────

export interface ApiKeyRecord {
  key_id:     string
  key_prefix: string
  label:      string
  scope:      string
  created_at: number
  last_used:  number
  rate_limit: number
}

export interface ApiKeyCreateRequest {
  label:      string
  scope:      string
  rate_limit: number
}

export interface ApiKeyCreateResult extends ApiKeyRecord {
  key:     string
  warning: string
}

export interface WebhookDeliveryLog {
  event:       string
  attempt:     number
  ts:          number
  status:      string
  http_status?: number
  error?:      string
}

export interface WebhookRecord {
  webhook_id:       string
  url:              string
  events:           string[]
  label:            string
  active:           boolean
  created_at:       number
  secret_hint:      string
  total_deliveries: number
  last_delivery:    WebhookDeliveryLog | null
}

export interface WebhookCreateRequest {
  url:    string
  events: string[]
  label:  string
  secret: string
}

// ── Sprint 20: Pulse Monitoring types ─────────────────────────────────────────

export interface PulseSignalDefinition {
  name:            string
  label:           string
  unit:            string
  alert_direction: string
  healthy_range:   string
  mu:              number
  sigma:           number
}

export interface PulseSignalCell {
  value:  number
  zscore: number
  alert:  boolean
}

export interface PulseHeatmapRow {
  department: string
  headcount:  number
  signals:    Record<string, PulseSignalCell>
}

export interface PulseWarningEmployee {
  employee_id:             string
  anon_id:                 string
  role_title:              string
  department:              string
  seniority_level:         string
  is_nexus:                boolean
  anomaly_score:           number
  base_attrition_risk:     number
  adjusted_attrition_risk: number
  cusum_alerts:            string[]
  signal_zscores:          Record<string, number>
}

export interface PulseTimeline {
  employee_id: string
  anon_id:     string
  role_title:  string
  department:  string
  signals:     Record<string, number[]>
}

export interface PulseCohesionRow {
  department:    string
  headcount:     number
  cohesion_score:number
  trend:         number[]
  delta_30d:     number
}

export interface PulseSummary {
  headcount:         number
  monitored:         number
  anomaly_count:     number
  cusum_alert_count: number
  avg_anomaly_score: number
  collection_date:   string
}

export interface PulseData {
  enabled:            boolean
  disclaimer:         string
  summary:            PulseSummary
  signal_definitions: PulseSignalDefinition[]
  heatmap:            PulseHeatmapRow[]
  early_warning:      PulseWarningEmployee[]
  timelines:          PulseTimeline[]
  team_cohesion:      PulseCohesionRow[]
}
