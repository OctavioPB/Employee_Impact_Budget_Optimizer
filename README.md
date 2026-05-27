# EIBO — Employee Impact & Budget Optimizer

> **Decision support for organizational leaders who need to balance budget constraints with critical talent retention — without losing the humans at the center of the decision.**

EIBO is a Capital and Budget Optimization Platform (COCP) that combines data science, graph theory, integer linear programming, and predictive analytics into a locally-deployed application. It does not make workforce decisions. It illuminates them: surfacing impact scores, attrition risk, collaboration dependencies, and budget trade-offs so that leaders can make better-informed choices with full transparency and human override at every step.

The machine suggests. People decide.

---

## Table of Contents

- [Why EIBO Exists](#why-eibo-exists)
- [Core Design Principles](#core-design-principles)
- [Platform Capabilities](#platform-capabilities)
- [Technical Architecture](#technical-architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [Demo Scenarios](#demo-scenarios)
- [RBAC Permission Model](#rbac-permission-model)
- [Public API (v1)](#public-api-v1)
- [Data Architecture](#data-architecture)
- [Optimization Engine](#optimization-engine)
- [Security & Privacy](#security--privacy)
- [Testing](#testing)
- [Key Commands](#key-commands)

---

## Why EIBO Exists

Workforce budget decisions are among the most consequential and poorly-supported decisions in any organization. Leaders typically face three tools: spreadsheets with no analytical depth, expensive HCM platforms that offer reporting but no simulation, or gut instinct under time pressure.

The result: budget reductions that eliminate critical knowledge holders, collaboration networks that fragment silently, and attrition risk that compounds undetected until talent has already left.

EIBO addresses this with a decision support system that:

- **Scores every employee's organizational impact** across four dimensions (performance, network centrality, skill criticality, replacement cost), not just salary or performance rating alone
- **Optimizes retention recommendations** under budget constraints using Integer Linear Programming — showing which combination of employees maximizes total organizational impact within the available budget
- **Maps the collaboration network** so that "Organizational Nexus" employees (those whose departure would fragment cross-team information flow) are visible before a decision is made
- **Predicts attrition risk** with calibrated probabilities and SHAP-explained drivers, surfacing employees likely to leave voluntarily regardless of budget decisions
- **Simulates budget stress scenarios** with Monte Carlo analysis and Prophet time-series forecasting, so leaders see uncertainty ranges — not false point estimates
- **Records every human override** with full audit trail, ensuring the machine's suggestion and the human's decision are always distinguishable

---

## Core Design Principles

### 1. Human-in-the-Loop — Non-Negotiable

Every model output supports manual override with annotation and audit trail. The UI presents recommendations as starting points for discussion, not verdicts. Confidence intervals are shown, not hidden. Language is always respectful:

| Never | Always |
|---|---|
| "Terminate employee" | "Not retained in simulation" |
| "Eliminate role" | "Structure optimization" |
| "Cut staff" | "Budget adjustment" |
| "Reduction plan" | "Optimization strategy" |

### 2. Privacy-First, Locally-Deployed

Zero data leaves the deployment host. All computation runs in-process or on local infrastructure. PII is masked at the data layer based on the requesting user's role before it ever reaches the UI.

### 3. Explainability at Every Layer

- ML impact scores expose SHAP breakdowns by dimension
- Attrition predictions show top contributing factors per employee
- ILP decisions link to the specific constraints that drove them
- Infeasible solutions explain which constraints conflict and suggest resolution paths

### 4. 100% Open-Source Stack

Every dependency is MIT, Apache 2.0, or BSD licensed. No vendor lock-in. No usage-based pricing that scales with headcount.

---

## Platform Capabilities

### Impact Scoring Engine
Computes a 0–100 composite impact score for every employee across four weighted dimensions:

| Dimension | Weight | What it measures |
|---|---|---|
| KPI History & Trend | 40% | Performance trajectory, not just snapshot |
| Collaboration Network Centrality | 30% | Betweenness, eigenvector, degree, and PageRank |
| Skill Criticality & Uniqueness | 20% | How rare and business-critical are their skills |
| Estimated Replacement Cost | 10% | Recruitment cost proxy based on seniority and role |

Each score includes a full SHAP breakdown so reviewers can trace exactly which factors drove the number.

### Budget Optimization (ILP)
Formulates workforce retention as an Integer Linear Programming problem:

- **Objective**: Maximize Σ(impact_score_i × x_i) where x_i ∈ {0, 1}
- **Hard constraints**: Budget ceiling, at least one leader per team, critical skill coverage
- **Configurable constraints**: Minimum team size, succession depth, diversity thresholds
- **Multi-objective**: Pareto frontier showing the budget vs. total impact trade-off curve
- **Sensitivity analysis**: Automatic ±5%, ±10%, ±20% budget scenario comparison
- **Infeasibility diagnosis**: When constraints cannot all be satisfied, EIBO identifies which constraints conflict and proposes resolution options

### Collaboration Network Analysis
Builds a directed weighted graph from collaboration data using NetworkX:

- Degree, betweenness, eigenvector centrality, and PageRank — all normalized 0–1
- Louvain community detection for natural team cluster discovery
- **Organizational Nexus** flag: employees with betweenness centrality > 0.70 whose removal would significantly fragment the information network
- **Team Fragility Score**: how dependent a team is on a small number of individuals

### Attrition Risk Prediction
Classification model with probability calibration:

- Four risk tiers: Low Risk, Moderate Risk, High Risk, Critical Risk
- SHAP-explained drivers per employee
- **Early Warning System**: configurable threshold alerts that fire when high-risk clusters appear in a department
- Handles class imbalance via SMOTE sampling
- Retraining triggered on monthly schedule or when data drift is detected

### Budget Forecasting
Dual-method forecasting with full uncertainty quantification:

- **Prophet time series**: seasonality detection, 80% and 95% confidence intervals
- **Monte Carlo stress testing**: 5,000 simulation runs returning P10/P50/P90 fan chart trajectories
- MAPE target: <15% for 3-month horizon

### Strategic Workforce Planning
- **Future State Designer**: model proposed org structures with cost and impact calculations
- **Skills Gap Analysis**: build-vs-buy recommendations with adjacency scoring
- **Transition Planner**: realistic timeline roadmaps with buffer for uncertainty
- **Strategy Comparator**: weighted scoring of multiple transition strategies

### Compensation Intelligence & Pay Equity (Sprint 10)
Market benchmarking and pay-equity analysis across the entire workforce:

- **Comp-ratio benchmarking**: every employee measured against a synthetic market median derived from role, seniority, and department — tiered as Below Market / At Market / Above Market
- **OLS pay-equity regression**: salary modeled on seniority and department; residuals expose structurally unexplained gaps by group
- **Retention ROI**: estimated cost-to-replace vs. salary-correction cost for below-market employees
- Department equity scorecards with P25/P50/P75 distributions

### Knowledge Graph & Institutional Memory (Sprint 11)
Maps the organization's knowledge ownership across 23 domains:

- **Single-Knowledge-Holder (SKH) detection**: flags any domain where only one employee holds critical knowledge
- **Knowledge loss score** per employee: weighted sum of domain criticality that would be lost on departure
- **Transfer roadmap**: ranked successor recommendations with urgency, estimated transfer hours, and estimated cost
- 23 domains spanning legacy systems, regulatory ownership, client relationships, incident playbooks, HIPAA/HL7 logic, ML model ownership, and more

### Internal Talent Mobility (Sprint 12)
Career path intelligence and succession planning:

- **Role affinity scoring**: skill-proximity matching across the full role catalog to surface realistic lateral and upward moves per employee
- **Career stagnation detection**: flags employees with high tenure, flat KPI trend, and below-percentile compensation as flight risk
- **Succession depth mapping**: for each leadership role, how many employees are ready-now, ready-6m, or ready-1y
- Gap cost estimation: per-skill upskilling cost ($4,000 proxy) to price the development investment

### Algorithmic Fairness & Bias Audit (Sprint 13)
Systematic audit of model outputs for disparate impact:

- **EEOC 4/5ths (80%) adverse impact rule** across all three model outputs: impact score, attrition risk prediction, and simulated retention selection
- **Chi-square significance testing** per (protected dimension, model) combination with p-value reporting
- **Counterfactual fairness test**: flip each protected attribute on a sample, recompute scores, report delta and 95% CI
- **Simulation disparity analysis**: checks whether top-40% retention by impact score systematically under-selects any group
- Synthetic proxy groups only — no real demographic data used or inferred

### Collaborative Decision Room (Sprint 14)
Structured multi-stakeholder deliberation with full lifecycle management:

- **Session lifecycle**: Draft → Active → Under Review → Finalized with digital sign-off
- **Participant roles**: Owner, Participant, Observer with permission-scoped actions
- **Override conflict detection**: flags when two participants retain vs. exclude the same employee and offers resolution modes (last-write, owner-wins, vote)
- **Structured deliberation feed**: comment threads, proposals, objections, and votes linked to specific employees
- **Immutable finalization**: signed sessions cannot be modified; full activity log preserved
- JSON-backed persistence — sessions survive disconnect/reconnect cycles

### Workforce Resilience Stress Testing (Sprint 15)
Six-dimension resilience scoring with active disruption simulation:

- **Composite Resilience Score (0–100)**: skill coverage, leadership depth, knowledge redundancy, network robustness, attrition concentration, and team-size buffer — each configurable weight
- **Five disruption scenario types**: targeted departure, department shock, competitive poaching, leadership vacuum, and skill crisis
- **Three-round cascade simulation**: models which primary departures trigger secondary attrition through nexus pressure and leadership gaps
- **Cascade amplifier identification**: surfaces which single departure causes the most downstream disruption
- **Intervention roadmap**: ranked actions by score-improvement-to-cost ROI ratio
- Department-level resilience breakdown with synthetic 12-month trend

### Learning & Development Investment Optimizer (Sprint 16)
ILP-driven L&D budget allocation across the full employee population:

- **15-program training catalog** across 5 tracks (technical, leadership, compliance, communication, domain)
- **Training effectiveness model**: impact-score delta, attrition reduction, and proficiency gain — keyed on inferred learning velocity per employee
- **PuLP ILP allocation**: binary assignment variables (employee × program) optimized for maximum org-wide return under budget ceiling
- **Pareto frontier sweep**: traces the retention-vs-L&D budget split curve
- **Skill gap records**: any skill with fewer than 2 holders flagged as a coverage gap
- Synthetic 12-cohort ROI history with predicted-vs-actual comparison

### Decision Narrative Engine (Sprint 17)
Local LLM-powered plain-language explanations for every model output:

- **Ollama integration** (mistral:7b-instruct) with 30-second hard timeout — no cloud API calls
- **Template-based deterministic fallback** when Ollama is unavailable, ensuring the endpoint always responds
- **Zero PII to the LLM**: names replaced with `[role]-[anonymized_id]` in all prompts before they leave the Python process
- Generates: impact-score explanations, attrition risk summaries, simulation outcome narratives, and manager retention conversation briefs
- SHAP-style heuristic driver breakdown embedded in each explanation

### Organizational Health Index (Sprint 18)
Composite OHI (0–100) across six sub-dimensions with benchmarking and forecasting:

| Sub-index | Weight | What it captures |
|---|---|---|
| Financial Health | 20% | Budget headroom, compensation leverage |
| Talent Risk | 20% | Attrition concentration, critical-role coverage |
| Knowledge Resilience | 20% | SKH exposure, knowledge transfer progress |
| Leadership Pipeline | 15% | Succession depth across leadership tiers |
| Compensation Equity | 15% | Pay-gap magnitude and coverage |
| Collaboration Density | 10% | Network centrality distribution |

- **24-month synthetic time series** with annotated org events and 6-month forward forecast
- **Department-level OHI breakdown** with radar chart comparison
- **Decision impact preview**: OHI delta across budget retention scenarios (60%, 70%, 80%, 90%)
- **Industry benchmark bands**: synthetic P25/P50/P75 percentiles per sub-index

### Workforce Intelligence API (Sprint 19)
Production-ready versioned public API with authentication and eventing:

- **Versioned REST API** at `/api/v1/` with Bearer token authentication
- **API key management**: scoped keys (`viewer`, `analyst`, `manager`, `director`, `executive`, `demo`), SHA-256 key hashing (raw keys never stored), sandbox key for immediate testing
- **Token-bucket rate limiting**: 100 requests/minute per key, in-process with no Redis dependency
- **Webhook event system**: HMAC-SHA256 signed payloads, fan-out delivery, event types covering attrition thresholds, simulation completion, OHI alerts, and notifications
- **Salary data gating**: only `manager`, `director`, and `executive` scoped keys receive exact salary figures
- **Four embeddable vanilla JS widgets** (Web Components / Shadow DOM, no framework dependency):
  - `<eibo-impact-badge>` — employee impact score chip
  - `<eibo-dept-sparkline>` — department engagement sparkline
  - `<eibo-attrition-alert>` — real-time attrition risk banner
  - `<eibo-budget-chip>` — budget utilization indicator
- **Python SDK** (`sdk/python/eibo_client.py`) — stdlib-only, no third-party dependencies
- **JavaScript SDK** (`sdk/js/eibo-client.js`) — ESM module with camelCase mapping and AbortController timeout

### Real-Time Engagement Signal Ingestion & Pulse Monitoring (Sprint 20)
Continuous behavioral signal tracking with anomaly detection and early warning:

- **6 synthetic engagement signals** per employee, sampled at daily resolution over 90 days:
  - `calendar_density_7d` — meeting load (correlated negatively with attrition risk)
  - `cross_team_interaction_7d` — breadth of cross-functional collaboration
  - `response_latency_trend` — communication responsiveness (higher = disengaging)
  - `pto_utilization_rate` — vacation uptake as a wellbeing proxy
  - `after_hours_ratio` — out-of-hours work (high = burnout signal)
  - `collaboration_network_delta` — 7-day change in collaboration breadth
- **IsolationForest anomaly detection** (contamination=0.10): signals unusual behavioral patterns not explained by role or department
- **CUSUM control chart alerting**: directional threshold alerting (upper, lower, or both) per signal with k=0.5, h=3.0 sensitivity
- **Adjusted attrition risk**: `base_risk + anomaly_score × 0.30`, clamped to [0,1] — anomalous behavior updates the predictive risk estimate
- **Department heatmap**: z-score grid (department × signal) with direction-aware color encoding
- **Early warning feed**: top-15 employees by adjusted attrition risk with signal anomaly flags
- **90-day signal timelines**: full per-employee series for the top-15 at-risk, with 70-day baseline marker
- **Team cohesion tracker**: 30-day cross-team interaction trend per department

---

## Technical Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  PRESENTATION LAYER (React 18 + TypeScript + Vite)                           │
│                                                                              │
│  Dashboard · Simulation · Drill-Down · Predictive · Forecast · Strategic     │
│  Compensation · Knowledge · Mobility · Fairness · Decision Room              │
│  Resilience · L&D · Narrative · OHI · Pulse · Notifications · Admin         │
├──────────────────────────────────────────────────────────────────────────────┤
│  API LAYER (FastAPI + Pydantic v2)                                           │
│                                                                              │
│  Internal API: /api/dashboard · /api/simulate · /api/predictive/attrition   │
│    /api/forecast · /api/compensation · /api/knowledge · /api/mobility        │
│    /api/fairness · /api/decision-room · /api/resilience · /api/ld            │
│    /api/narrative · /api/ohi · /api/pulse · /api/notifications               │
│                                                                              │
│  Public API v1: /api/v1/dashboard · /api/v1/impact · /api/v1/attrition      │
│    /api/v1/ohi · /api/v1/forecast · (Bearer token + rate limiting)           │
│                                                                              │
│  Infra: /api/v1/api-keys · /api/v1/webhooks · /api/health                   │
├──────────────────────────────────────────────────────────────────────────────┤
│  ANALYTICS & DECISION LAYER                                                  │
│                                                                              │
│  Impact Scorer        (scikit-learn + SHAP)                                  │
│  Network Analysis     (NetworkX · Louvain)                                   │
│  ILP Optimizer        (PuLP · CBC solver)                                    │
│  Attrition Predictor  (Random Forest · SMOTE · calibration)                 │
│  Forecasting          (Prophet · Monte Carlo · NumPy)                        │
│  Strategic Planner    (skills gap · adjacency · transition)                  │
│  Compensation Engine  (OLS pay equity · comp-ratio · retention ROI)          │
│  Knowledge Graph      (SKH detection · transfer roadmap)                     │
│  Talent Mobility      (skill proximity · stagnation · succession)            │
│  Fairness Auditor     (EEOC 4/5ths · chi-square · counterfactual)           │
│  Decision Room        (session lifecycle · conflict resolution · sign-off)   │
│  Resilience Engine    (cascade simulation · intervention ROI)                │
│  L&D Optimizer        (ILP allocation · Pareto sweep · gap analysis)         │
│  Narrative Engine     (Ollama LLM · deterministic fallback · zero-PII)       │
│  OHI Engine           (6-dimension · benchmarks · decision delta preview)    │
│  Pulse Monitor        (IsolationForest · CUSUM · 6-signal · 90-day series)  │
├──────────────────────────────────────────────────────────────────────────────┤
│  DATA LAYER (Medallion Architecture)                                         │
│  Bronze (raw ingestion) → Silver (cleansed) → Gold (DuckDB views)            │
├──────────────────────────────────────────────────────────────────────────────┤
│  PLATFORM SERVICES                                                           │
│  Auth (RBAC · OAuth2/OIDC · local fallback)                                  │
│  API Key Service (SHA-256 · token-bucket rate limiting · scopes)             │
│  Webhook Service (HMAC-SHA256 · fan-out · delivery log)                      │
│  Audit Logger (immutable event trail)                                        │
│  Notifications (engine · channels · bundler)                                 │
│  Workflow Engine (Prefect-compatible @task/@flow)                            │
│  Integration Hub (Workday · SuccessFactors · BambooHR · generic)            │
├──────────────────────────────────────────────────────────────────────────────┤
│  EXTERNAL INTEGRATIONS (read-only — no data egress)                         │
│  Embeddable Widgets (4 × Web Components · Shadow DOM · no framework)         │
│  Python SDK (stdlib-only · eibo_client.py)                                   │
│  JavaScript SDK (ESM · eibo-client.js · AbortController timeout)             │
│  Ollama (local LLM — zero PII — deterministic fallback if unavailable)       │
├──────────────────────────────────────────────────────────────────────────────┤
│  INFRASTRUCTURE                                                              │
│  PostgreSQL (persistent data · audit logs · user management)                 │
│  DuckDB (in-process analytics · millisecond query latency)                   │
│  Redis (optional · session cache · prediction cache)                         │
│  Docker Compose (single-command deployment)                                  │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
HRIS / CSV Upload
      │
      ▼ Bronze: raw ingestion (no transformation)
      │
      ▼ Silver: cleansing, normalization, validation
      │
      ▼ Gold: DuckDB aggregated views (fast query layer)
      │
      ├──► Impact Scorer ──► ILP Optimizer ──► FastAPI ──► React UI
      │
      ├──► Network Analysis ──► Drill-Down / Graph UI
      │
      ├──► Attrition Predictor ──► Predictive UI / Alerts / Pulse
      │
      ├──► Pulse Monitor (IsolationForest + CUSUM) ──► Pulse UI
      │
      ├──► Narrative Engine (Ollama / fallback) ──► Narrative UI
      │
      └──► Forecasting ──► Budget / Headcount Forecast UI
```

---

## Tech Stack

### Frontend
| Layer | Technology | Version | License |
|---|---|---|---|
| UI Framework | React | 18.3 | MIT |
| Language | TypeScript | 5.5 (strict) | Apache 2.0 |
| Build Tool | Vite | 5.4 | MIT |
| State Management | Zustand | 4.5 | MIT |
| Fonts | Plus Jakarta Sans, Fraunces | — | OFL |

No external UI component library — all styling is inline `React.CSSProperties` via the OPB design token system.

### Backend (API Layer)
| Layer | Technology | Version | License |
|---|---|---|---|
| API Framework | FastAPI | ≥0.111 | MIT |
| ASGI Server | Uvicorn | ≥0.29 | BSD |
| Schema Validation | Pydantic v2 | built-in | MIT |

### Analytics Engine (Python)
| Layer | Technology | Version | License |
|---|---|---|---|
| Analytics DB | DuckDB | ≥0.10 | MIT |
| Relational DB | PostgreSQL | ≥15 | PostgreSQL |
| Session Cache | Redis | ≥7 (optional) | BSD |
| ML Framework | scikit-learn | ≥1.4 | BSD |
| Optimization | PuLP (CBC) | ≥2.7 | MIT |
| Graph Analysis | NetworkX | ≥3.2 | BSD |
| Forecasting | Prophet | ≥1.1 | MIT |
| Anomaly Detection | scikit-learn IsolationForest | ≥1.4 | BSD |
| Statistical Testing | SciPy | ≥1.12 | BSD |
| Explainability | SHAP | ≥0.45 | MIT |
| Local LLM | Ollama (mistral:7b-instruct) | — | MIT |
| HTTP Client | httpx | ≥0.27 | BSD |
| Data Processing | pandas, numpy | ≥2.0 / ≥1.26 | BSD |
| Containerization | Docker Compose | ≥2.20 | Apache 2.0 |

All dependencies are permissively licensed. No proprietary or usage-metered libraries.

---

## Project Structure

```
eibo/
│
├── frontend/                        # React 18 + TypeScript SPA
│   ├── src/
│   │   ├── App.tsx                  # Page routing (useState, no router lib)
│   │   ├── pages/
│   │   │   ├── InfoPage.tsx         # Landing page (Business + Engineering views)
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── SimulationPage.tsx
│   │   │   ├── DrillDownPage.tsx
│   │   │   ├── PredictivePage.tsx
│   │   │   ├── ForecastPage.tsx
│   │   │   ├── StrategicPage.tsx
│   │   │   ├── CompensationPage.tsx # Pay equity, market benchmarking
│   │   │   ├── KnowledgePage.tsx    # Knowledge graph, SKH detection, transfer roadmap
│   │   │   ├── MobilityPage.tsx     # Career paths, stagnation, succession depth
│   │   │   ├── FairnessPage.tsx     # EEOC audit, counterfactual fairness
│   │   │   ├── DecisionRoomPage.tsx # Multi-stakeholder deliberation sessions
│   │   │   ├── ResiliencePage.tsx   # Resilience score, cascade simulation
│   │   │   ├── LDPage.tsx           # L&D budget optimizer, Pareto frontier
│   │   │   ├── NarrativePage.tsx    # LLM-generated decision narratives
│   │   │   ├── OHIPage.tsx          # Organizational Health Index
│   │   │   ├── PulsePage.tsx        # Real-time engagement signals, anomaly detection
│   │   │   ├── NotificationsPage.tsx
│   │   │   └── AdminPage.tsx        # API keys, webhooks, widget embed codes
│   │   ├── components/
│   │   │   ├── Nav.tsx              # Sticky top nav bar
│   │   │   ├── Footer.tsx
│   │   │   └── Eyebrow.tsx          # Gold rule + label component
│   │   ├── hooks/
│   │   │   └── useTheme.ts          # Dark/light mode (localStorage)
│   │   ├── stores/
│   │   │   └── demoStore.ts         # Zustand: scenario, size, demo flag
│   │   ├── services/
│   │   │   └── api.ts               # All HTTP calls (no direct fetch in components)
│   │   └── styles/
│   │       └── tokens.css           # OPB design tokens (CSS custom properties)
│   ├── public/
│   │   └── widgets/                 # Embeddable Web Component widgets
│   │       ├── eibo-impact-badge.js
│   │       ├── eibo-dept-sparkline.js
│   │       ├── eibo-attrition-alert.js
│   │       └── eibo-budget-chip.js
│   ├── index.html
│   ├── vite.config.ts               # /api/* proxied to localhost:8000
│   ├── tsconfig.json                # Strict TypeScript
│   ├── package.json
│   ├── Dockerfile                   # Multi-stage: build → nginx
│   └── nginx.conf                   # /api/* → backend:8000, SPA fallback
│
├── backend/                         # FastAPI REST API
│   ├── main.py                      # FastAPI app + CORS + router registration
│   ├── routers/
│   │   ├── dashboard.py             # GET /api/dashboard
│   │   ├── simulation.py            # POST /api/simulate
│   │   ├── predictive.py            # GET /api/predictive/attrition
│   │   ├── forecast.py              # GET /api/forecast
│   │   ├── compensation.py          # GET /api/compensation
│   │   ├── knowledge.py             # GET /api/knowledge
│   │   ├── mobility.py              # GET /api/mobility
│   │   ├── fairness.py              # GET /api/fairness
│   │   ├── decision_room.py         # CRUD /api/decision-room/sessions
│   │   ├── resilience.py            # GET /api/resilience
│   │   ├── ld.py                    # GET /api/ld
│   │   ├── narrative.py             # POST /api/narrative/*
│   │   ├── ohi.py                   # GET /api/ohi
│   │   ├── pulse.py                 # GET /api/pulse
│   │   ├── notifications.py         # GET/POST /api/notifications
│   │   ├── admin.py                 # GET /api/admin
│   │   ├── api_keys.py              # CRUD /api/v1/api-keys
│   │   ├── webhooks.py              # CRUD /api/v1/webhooks
│   │   └── v1.py                    # Public API: /api/v1/* (Bearer auth)
│   ├── services/
│   │   ├── data_service.py          # DemoGenerator wrapper (lru_cache)
│   │   ├── compensation_service.py
│   │   ├── knowledge_service.py
│   │   ├── mobility_service.py
│   │   ├── fairness_service.py
│   │   ├── decision_room_service.py
│   │   ├── resilience_service.py
│   │   ├── ld_service.py
│   │   ├── narrative_service.py
│   │   ├── ohi_service.py
│   │   ├── pulse_service.py
│   │   ├── api_key_service.py       # SHA-256 keys, token-bucket rate limiting
│   │   └── webhook_service.py       # HMAC-SHA256 signing, async fan-out
│   └── Dockerfile
│
├── sdk/
│   ├── python/
│   │   └── eibo_client.py           # Python SDK (stdlib-only, typed dataclasses)
│   └── js/
│       └── eibo-client.js           # JavaScript SDK (ESM, camelCase mapping)
│
├── models/                          # ML models
│   ├── impact_scorer.py
│   ├── network_analysis.py
│   ├── attrition_predictor.py
│   └── early_warning.py
│
├── optimization_engine/             # ILP workforce optimization
│   ├── ilp_solver.py
│   ├── constraints.py
│   ├── multi_objective.py
│   └── sensitivity.py
│
├── forecasting/
│   ├── budget_forecaster.py
│   └── monte_carlo.py
│
├── strategic_planner/
│   ├── future_state.py
│   ├── skills_gap.py
│   ├── transition_planner.py
│   └── strategy_comparator.py
│
├── data_pipeline/                   # Medallion ETL
│   ├── bronze_ingest.py
│   ├── silver_cleanse.py
│   ├── gold_aggregate.py
│   └── validators.py
│
├── demo_data/                       # Synthetic org generator
│   ├── generator.py                 # DemoGenerator class
│   ├── scenarios.py                 # Scenario config loader
│   ├── seed_demo.py                 # CLI database seeder
│   └── organizations/               # Scenario JSON configs (A, B, C)
│
├── auth/
│   ├── rbac.py
│   └── session_manager.py
│
├── audit/
│   ├── logger.py
│   ├── trail_viewer.py
│   └── compliance_reports.py
│
├── notifications/
│   ├── engine.py
│   └── channels/
│
├── workflows/
│   ├── engine.py
│   ├── data_pipeline_flow.py
│   └── model_retraining_flow.py
│
├── integration_hub/
│   ├── base_connector.py
│   ├── workday_connector.py
│   ├── bamboohr_connector.py
│   └── generic_api_connector.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── performance/
│   └── security/
│
├── ui/                              # Legacy Streamlit UI (kept for reference)
│   └── main.py
│
├── docker-compose.yml               # postgres + backend + frontend + pgadmin
├── docker-compose.prod.yml
├── .env.example
├── requirements.txt                 # Python deps (includes fastapi, uvicorn)
└── requirements-dev.txt
```

---

## Setup & Installation

### Prerequisites

- Docker ≥ 24.0 and Docker Compose ≥ 2.20 (for containerized deployment)
- Or: Python 3.11+ and Node.js 20+ (for local development)

### Option A — Docker (Recommended)

#### 1. Clone

```bash
git clone https://github.com/your-org/eibo.git
cd eibo
```

#### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` — required variables:

```bash
POSTGRES_USER=eibo_user
POSTGRES_PASSWORD=<strong-password>
POSTGRES_DB=eibo_db
SECRET_KEY=<64-character-random-hex>
DEMO_MODE_ENABLED=true
LOG_LEVEL=INFO
```

Generate a `SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

#### 3. Start the Full Stack

```bash
docker-compose up -d
```

This starts four services:

| Service | URL | Description |
|---|---|---|
| **frontend** | http://localhost:3000 | React SPA (nginx) |
| **backend** | http://localhost:8000 | FastAPI REST API |
| **postgres** | localhost:5432 | PostgreSQL database |
| **pgadmin** | http://localhost:5050 | DB admin UI (dev profile only) |

First run takes ~2–3 minutes to build images. The app starts in demo mode with pre-loaded synthetic data — no further configuration needed.

#### 4. Seed Demo Data (Optional)

The API generates demo data in-memory on first request — **seeding is not required** to use the app. It only populates the PostgreSQL database for persistence across restarts.

```bash
# Requires the stack to be running first (docker-compose up -d)
docker-compose exec backend python demo_data/seed_demo.py --scenario all --size medium

# Alternatively, run it locally (requires PostgreSQL on localhost:5432 and a .env file)
python demo_data/seed_demo.py --scenario all --size medium
```

---

### Option B — Local Development (Hot Reload)

Best for active development — runs the frontend and backend separately with live reload.

#### 1. Python Backend

```bash
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Start FastAPI with hot reload
uvicorn backend.main:app --reload --port 8000
```

API is now available at http://localhost:8000. Interactive docs at http://localhost:8000/docs.

#### 2. React Frontend

```bash
cd frontend

# Install npm dependencies (first time only)
npm install

# Start Vite dev server with HMR
npm run dev
```

Frontend is now available at http://localhost:5173. The Vite dev server automatically proxies `/api/*` requests to `localhost:8000`.

#### 3. Verify

```bash
curl http://localhost:8000/api/health
# {"status": "ok", "service": "eibo-api"}

curl "http://localhost:8000/api/dashboard?scenario=A&size=small&demo=true" | python -m json.tool | head -20
```

---

### Option C — Production Deployment

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## Demo Scenarios

EIBO ships with three fully synthetic demo organizations:

### Scenario A — Growing Company
**Industry**: Software & Technology

A fast-growing tech company that scaled headcount 3× in 18 months. Engineering is overbudget, critical architecture knowledge is concentrated in three engineers, and there is no succession plan for the VP of Engineering.

**Key challenges**: DevOps skill gap (single qualified person), engineering overbudget by 25%, no leadership succession.

### Scenario B — Restructuring
**Industry**: Financial Services

A mid-size financial services firm facing a board-mandated 20% cost reduction. Multiple departments have overlapping roles, 60% of the technology team is on legacy COBOL systems, and the Risk & Compliance function has a single expert on a new regulatory framework.

**Key challenges**: Operations redundancy, technology skills mismatch, single-point-of-failure compliance expertise.

### Scenario C — Merger Integration
**Industry**: Healthcare Technology

Two healthcare tech companies completed a merger six months ago. Duplicate leadership structures exist, competing backend implementations are being built by teams that haven't unified, and unique HIPAA expertise from the acquired company is at attrition risk.

**Key challenges**: Duplicate C-suite, role overlap, clinical domain knowledge at risk.

Each scenario is available in three sizes: **Small** (50 employees), **Medium** (500), **Large** (5,000).

---

## RBAC Permission Model

Six-tier role hierarchy enforcing data isolation at both the permission and department level:

| Role | Level | Key Capabilities |
|---|---|---|
| **Viewer** | 1 | Dashboards only, masked salary, masked PII |
| **Analyst** | 2 | Run simulations, create scenarios, salary ranges (not exact) |
| **Manager** | 3 | Full access within own department(s), overrides with annotation |
| **Director** | 4 | Cross-department access, strategic planning |
| **Executive** | 5 | Org-wide access, audit log visibility |
| **Admin** | 6 | User management, system config, full audit export |

Data isolation is enforced at query time: a Manager with `department="Engineering"` cannot access, simulate, or export data for any other department.

---

## Public API (v1)

The v1 API exposes a read-only subset of EIBO analytics for integration into external dashboards, BI tools, and custom workflows.

### Authentication

All `/api/v1/*` endpoints (except `/api/v1/health`) require a Bearer token:

```
Authorization: Bearer eibo_<scope>_<32-hex-chars>
```

Obtain a sandbox key instantly — no registration needed:

```bash
curl http://localhost:8000/api/v1/api-keys/sandbox
# {"key": "eibo_demo_sandbox0000000000000000", "scope": "demo", "label": "Sandbox Demo Key"}
```

### Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/health` | None | Service health check |
| GET | `/api/v1/dashboard` | Bearer | KPIs: headcount, avg impact, attrition risk, budget |
| GET | `/api/v1/impact` | Bearer | Per-employee impact scores (salary gated by scope) |
| GET | `/api/v1/attrition-summary` | Bearer | Attrition risk distribution by tier and department |
| GET | `/api/v1/ohi` | Bearer | OHI score and 6-dimension breakdown |
| GET | `/api/v1/forecast` | Bearer | 6-month budget forecast with P10/P50/P90 |
| GET/POST | `/api/v1/api-keys` | Bearer | List / create API keys |
| DELETE | `/api/v1/api-keys/{id}` | Bearer | Revoke a key |
| POST | `/api/v1/api-keys/verify` | None | Verify a key and return its scope |
| GET/POST | `/api/v1/webhooks` | Bearer | List / register webhooks |
| PATCH/DELETE | `/api/v1/webhooks/{id}` | Bearer | Update active state / remove webhook |
| POST | `/api/v1/webhooks/{id}/test` | Bearer | Send a test delivery to the endpoint |

### Webhook Events

| Event type | Fires when |
|---|---|
| `attrition.risk.threshold_crossed` | An employee crosses a risk tier boundary |
| `impact.score.updated` | Impact scores are recalculated |
| `simulation.completed` | A budget simulation run finishes |
| `ohi.alert` | The OHI score drops below a configured threshold |
| `notification.created` | A system notification is created |

Webhook payloads are HMAC-SHA256 signed. Verify with the `X-EIBO-Signature` header:

```python
import hmac, hashlib

def verify_signature(secret: str, body: bytes, header: str) -> bool:
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header)
```

### Embeddable Widgets

Drop any widget into an existing page — no build step required:

```html
<script src="http://localhost:8000/widgets/eibo-impact-badge.js"></script>
<script src="http://localhost:8000/widgets/eibo-dept-sparkline.js"></script>
<script src="http://localhost:8000/widgets/eibo-attrition-alert.js"></script>
<script src="http://localhost:8000/widgets/eibo-budget-chip.js"></script>

<eibo-impact-badge    api-key="eibo_demo_sandbox0000000000000000" scenario="A" size="small"></eibo-impact-badge>
<eibo-dept-sparkline  api-key="eibo_demo_sandbox0000000000000000" department="Engineering"></eibo-dept-sparkline>
<eibo-attrition-alert api-key="eibo_demo_sandbox0000000000000000" scenario="A" size="small"></eibo-attrition-alert>
<eibo-budget-chip     api-key="eibo_demo_sandbox0000000000000000" scenario="A" size="small"></eibo-budget-chip>
```

---

## Data Architecture

EIBO uses a three-layer medallion architecture:

```
Source Data (CSV / HRIS API)
        │
        ▼
   Bronze Layer — Raw ingestion, no transformation. Original format preserved.
        │
        ▼
   Silver Layer — Cleansing, type coercion, normalization, PII tokenization.
        │
        ▼
   Gold Layer — DuckDB materialized views. Pre-aggregated for millisecond latency.
        │
        ▼
   FastAPI — Serves aggregated data to the React frontend
```

**Key invariants**:
- Bronze data is write-once, never modified
- Silver cleansing is idempotent and replayable
- Gold views can be rebuilt from Silver at any time
- Demo data uses a separate schema prefix — it can never mix with real data

---

## Optimization Engine

```
Maximize:    Σ (impact_score_i × x_i)    for all employees i

Subject to:
  Budget:    Σ (cost_i × x_i) ≤ available_budget

  Leadership: for each team t:
              Σ (x_i × is_leader_i) ≥ 1

  Critical skills: for each skill s:
              Σ (x_i × has_skill_s_i) ≥ min_holders_s

  Domain:    x_i ∈ {0, 1}
```

The CBC (Coin-or Branch and Cut) solver handles problems up to 5,000 employees within a configurable time limit. For infeasible problems, EIBO identifies conflicting constraints and proposes resolution paths.

The backend falls back to a greedy impact/cost-ratio sort when PuLP is unavailable, ensuring the simulation endpoint always returns a result.

The same ILP framework is reused in the L&D optimizer: binary `y_{i,t}` variables assign employees to training programs to maximize org-wide return under a separate L&D budget ceiling.

---

## Security & Privacy

| Control | Implementation |
|---|---|
| No external data transfer | All computation is local; zero API calls with employee data |
| Zero PII to LLM | Names replaced with `[role]-[anonymized_id]` before any Ollama prompt |
| Input sanitization | SQL injection, XSS, path traversal detection at all entry points |
| PII masking | Role-based, applied at query time before UI rendering |
| API key storage | SHA-256 hash only — raw key shown once at creation, never stored |
| Webhook signing | HMAC-SHA256 on every delivery — receivers can verify payload integrity |
| Secrets validation | Startup check rejects placeholder values and enforces minimum entropy |
| Audit trail | Every simulation, override, login, and config change is logged |
| RBAC enforcement | `AccessControl.require()` raises `PermissionError` before any data access |
| Department isolation | Query filters applied server-side based on `user.departments` scope |
| CORS | FastAPI CORS middleware — only configured origins accepted |

---

## Testing

```bash
# Full Python test suite
pytest tests/ -v

# By suite
pytest tests/unit/ -v                   # fast, no infrastructure
pytest tests/integration/ -v            # end-to-end pipeline flows
pytest tests/performance/ -v            # wall-clock benchmark thresholds
pytest tests/security/ -v              # RBAC boundaries, injection prevention

# With coverage
pytest tests/ --cov=. --cov-report=html

# Frontend type check + build
cd frontend && npm run build

# Frontend lint
cd frontend && npx tsc --noEmit
```

Performance thresholds (small org, 50 employees):

| Operation | Threshold |
|---|---|
| Demo data generation | ≤ 5 seconds |
| Network centrality metrics | ≤ 5 seconds |
| Impact scoring | ≤ 5 seconds |
| ILP solve (70% budget) | ≤ 10 seconds |
| Attrition prediction | ≤ 5 seconds |
| Pulse signal generation (90-day × 50 emp × 6 signals) | ≤ 3 seconds |
| API dashboard endpoint | ≤ 200ms |
| React build | ≤ 2 minutes |

---

## Key Commands

```bash
# ── Docker ────────────────────────────────────────────────────────────────

# Start all services (frontend :3000, backend :8000, postgres :5432)
docker-compose up -d

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Production deployment
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# ── Local Development ─────────────────────────────────────────────────────

# Python backend (hot reload)
uvicorn backend.main:app --reload --port 8000

# React frontend (HMR)
cd frontend && npm run dev

# ── Data & Models ─────────────────────────────────────────────────────────

# Seed demo database into PostgreSQL (optional — API generates data in-memory without this)
python demo_data/seed_demo.py --scenario all --size medium

# Run data pipeline
python workflows/data_pipeline_flow.py --input data/payroll.csv

# Retrain models
python workflows/model_retraining_flow.py --force

# ── API ───────────────────────────────────────────────────────────────────

# Health check
curl http://localhost:8000/api/health

# Dashboard data (Scenario A, small org, demo mode)
curl "http://localhost:8000/api/dashboard?scenario=A&size=small&demo=true"

# Get sandbox API key
curl http://localhost:8000/api/v1/api-keys/sandbox

# Call the public v1 API
curl -H "Authorization: Bearer eibo_demo_sandbox0000000000000000" \
     "http://localhost:8000/api/v1/dashboard?scenario=A&size=small"

# Run simulation
curl -X POST http://localhost:8000/api/simulate \
  -H "Content-Type: application/json" \
  -d '{"scenario":"A","size":"small","budget_pct":80,"force_retain":[],"exclude":[],"leadership_constraint":true,"skills_constraint":true}'

# Interactive API docs
open http://localhost:8000/docs

# ── Testing ───────────────────────────────────────────────────────────────

# Full test suite
pytest tests/ -v

# Frontend type check
cd frontend && npx tsc --noEmit

# Frontend production build
cd frontend && npm run build
```

---

## Project Status

| Sprint | Capability | Status |
|---|---|---|
| 1 | Data infrastructure, demo database, info page | Complete |
| 2 | Analytics engine, impact scoring, dashboard | Complete |
| 3 | ILP optimization engine, budget simulation | Complete |
| 4 | Network graphs, drill-down, individual profiles | Complete |
| 5 | Attrition prediction, forecasting, early warning | Complete |
| 6 | Strategic planning, future state designer | Complete |
| 7 | RBAC, audit trail, enterprise readiness | Complete |
| 8 | Notifications, workflow engine, HRIS integrations | Complete |
| 9 | Testing suite, documentation, production hardening | Complete |
| 10 | React 18 + FastAPI migration, compensation intelligence | Complete |
| 11 | Knowledge graph, institutional memory, SKH detection | Complete |
| 12 | Internal talent mobility, career paths, succession depth | Complete |
| 13 | Algorithmic fairness, EEOC audit, counterfactual testing | Complete |
| 14 | Collaborative decision room, multi-stakeholder deliberation | Complete |
| 15 | Workforce resilience stress testing, cascade simulation | Complete |
| 16 | L&D investment optimizer, ILP training allocation | Complete |
| 17 | Local LLM decision narrative engine (Ollama + fallback) | Complete |
| 18 | Organizational Health Index, 6-dimension benchmarking | Complete |
| 19 | Workforce Intelligence API v1, webhooks, widgets, SDKs | Complete |
| 20 | Real-time engagement signals, IsolationForest, CUSUM, Pulse UI | Complete |

**Codebase**: 130+ Python modules · React SPA (19 pages) · FastAPI REST layer (19 routers) · Python & JS SDKs · 4 embeddable widgets · 35,000+ lines · 734 tests

---

## License

This project uses exclusively permissively-licensed open-source dependencies (MIT, Apache 2.0, BSD). See `requirements.txt` and `frontend/package.json` for the full dependency lists.

---

*EIBO — Employee Impact & Budget Optimizer*
*OPB · Octavio Pérez Bravo · Data & AI Strategy Architect*
*From pipeline to decision.*
