# EIBO — Employee Impact & Budget Optimizer

> **Decision support for organizational leaders who need to balance budget constraints with critical talent retention — without losing the humans at the center of the decision.**

EIBO is a Capital and Budget Optimization Platform (COCP) that combines data science, graph theory, integer linear programming, and predictive analytics into a single, locally-deployed Streamlit application. It does not make workforce decisions. It illuminates them: surfacing impact scores, attrition risk, collaboration dependencies, and budget trade-offs so that leaders can make better-informed choices with full transparency and human override at every step.

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
- [Data Architecture](#data-architecture)
- [Optimization Engine](#optimization-engine)
- [Security & Privacy](#security--privacy)
- [Testing](#testing)
- [Documentation](#documentation)
- [Project Status](#project-status)

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

The machine suggests. People decide.

---

## Core Design Principles

### 1. Human-in-the-Loop — Non-Negotiable

Every model output supports manual override with annotation and audit trail. The UI is designed to present recommendations as starting points for discussion, not verdicts. Confidence intervals are shown, not hidden. Language is always respectful:

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
- **Infeasibility diagnosis**: When constraints cannot all be satisfied simultaneously, EIBO identifies which constraints conflict and proposes resolution options

### Collaboration Network Analysis
Builds a directed weighted graph from collaboration data using NetworkX:

- Degree, betweenness, eigenvector centrality, and PageRank — all normalized 0–1
- Louvain community detection for natural team cluster discovery
- **Organizational Nexus** flag: employees with betweenness centrality > 0.70 whose removal would significantly fragment the information network
- **Team Fragility Score**: how dependent a team is on a small number of individuals
- Interactive graph visualization with community coloring, node sizing by impact score, and edge weight rendering

### Attrition Risk Prediction
Classification model with probability calibration:

- Four risk tiers: Low Risk, Moderate Risk, High Risk, Critical Risk
- SHAP-explained drivers per employee (tenure, engagement trend, market salary gap, manager change frequency, etc.)
- **Early Warning System**: configurable threshold alerts that fire when high-risk clusters appear in a department
- Handles class imbalance (attrition is rare) via SMOTE sampling
- Retraining triggered on monthly schedule or when data drift is detected

### Budget Forecasting
Dual-method forecasting with full uncertainty quantification:

- **Prophet time series**: seasonality detection (annual review cycles, quarterly planning), holiday injection, 80% and 95% confidence intervals
- **Monte Carlo stress testing**: 5,000 simulation runs sampling attrition events and cost shocks, returning P10/P50/P90 fan chart trajectories
- MAPE target: <15% for 3-month horizon
- Forecasts always show intervals, never false point estimates

### Strategic Workforce Planning
Forward-looking organizational modeling:

- **Future State Designer**: model proposed org structures with cost and impact impact calculations
- **Skills Gap Analysis**: compare current skill inventory against target state, with adjacency scoring (how close existing skills are to required skills) and build-vs-buy recommendations
- **Transition Planner**: realistic timeline roadmaps with buffer for uncertainty
- **Strategy Comparator**: weighted scoring of multiple transition strategies against user-defined priorities

### Drill-Down Navigation
Hierarchical exploration from macro to individual:

- Organization → Department → Team → Individual
- Individual profiles include radar chart (4-dimension impact), performance sparklines, skill matrix with criticality ratings, collaboration network excerpt, and attrition risk with SHAP breakdown
- Simulation status visible on every profile card, with inline override capability
- Export at any level: CSV, Excel, PDF (formatted report, not raw data dump)

### Notifications & Workflow Engine
- Lightweight Prefect-compatible `@task`/`@flow` decorator system
- Smart notification bundling: same source + same time window → single digest, not alert fatigue
- Multi-channel dispatch: in-app, email (SMTP), webhook (Slack/Teams/custom)
- Three built-in automated flows: data pipeline refresh, model retraining, weekly risk digest

### Enterprise HRIS Integration
Abstract connector interface with three concrete implementations:

- **Workday** connector
- **SAP SuccessFactors** connector
- **BambooHR** connector
- **Generic REST API** connector for any HRIS with a JSON API

Field mapping engine with transform support (type coercion, unit conversion, format normalization) and preview-before-apply validation.

### Audit Trail
Full immutable event log covering every user action:

- Login/logout, simulation runs, overrides, exports, configuration changes, permission denials
- Thread-safe singleton logger with JSON-lines disk persistence and in-memory ring buffer for fast recent-event access
- Queryable by category, user, date range, outcome, and severity
- JSONL and CSV export for compliance reporting

---

## Technical Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│  PRESENTATION LAYER                                                  │
│  Streamlit SPA · ui/main.py entry point                              │
│  Dashboard · Simulation · Drill-Down · Predictive · Strategic        │
│  Notifications · Admin · Info (Business + Engineering views)         │
├──────────────────────────────────────────────────────────────────────┤
│  ANALYTICS & DECISION LAYER                                          │
│  Impact Scorer (scikit-learn + SHAP)                                 │
│  Network Analysis (NetworkX · Louvain)                               │
│  ILP Optimizer (PuLP · CBC solver)                                   │
│  Attrition Predictor (Random Forest · SMOTE · calibration)          │
│  Forecasting (Prophet · Monte Carlo · NumPy)                         │
│  Strategic Planner (skills gap · adjacency · transition)             │
├──────────────────────────────────────────────────────────────────────┤
│  DATA LAYER (Medallion Architecture)                                 │
│  Bronze (raw ingestion) → Silver (cleansed) → Gold (DuckDB views)   │
├──────────────────────────────────────────────────────────────────────┤
│  PLATFORM SERVICES                                                   │
│  Auth (RBAC · OAuth2/OIDC · local fallback)                          │
│  Audit Logger (immutable event trail)                                │
│  Notifications (engine · channels · bundler)                         │
│  Workflow Engine (Prefect-compatible @task/@flow)                    │
│  Integration Hub (Workday · SuccessFactors · BambooHR · generic)    │
│  Health Checker · Structured Logging · Input Sanitization            │
├──────────────────────────────────────────────────────────────────────┤
│  INFRASTRUCTURE                                                      │
│  PostgreSQL (persistent data · audit logs · user management)         │
│  DuckDB (in-process analytics · millisecond query latency)           │
│  Redis (optional · session cache · prediction cache)                 │
│  Docker Compose (single-command deployment)                          │
└──────────────────────────────────────────────────────────────────────┘
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
      ├──► Impact Scorer ──► ILP Optimizer ──► Simulation UI
      │
      ├──► Network Analysis ──► Drill-Down / Graph UI
      │
      ├──► Attrition Predictor ──► Predictive UI / Alerts
      │
      └──► Forecasting ──► Budget / Headcount Forecast UI
```

---

## Tech Stack

| Layer | Technology | Version | License |
|---|---|---|---|
| UI Framework | Streamlit | ≥1.32 | Apache 2.0 |
| Analytics DB | DuckDB | ≥0.10 | MIT |
| Relational DB | PostgreSQL | ≥15 | PostgreSQL |
| Session Cache | Redis | ≥7 (optional) | BSD |
| ML Framework | scikit-learn | ≥1.4 | BSD |
| Optimization | PuLP (CBC) | ≥2.7 | MIT |
| Graph Analysis | NetworkX | ≥3.2 | BSD |
| Forecasting | Prophet | ≥1.1 | MIT |
| Anomaly Detection | PyOD | ≥1.1 | BSD |
| Explainability | SHAP | ≥0.45 | MIT |
| HTTP Client | httpx | ≥0.27 | BSD |
| Data Processing | pandas, numpy | ≥2.0 / ≥1.26 | BSD |
| Visualization | Plotly | ≥5.20 | MIT |
| Workflow | Prefect-compatible decorators | built-in | — |
| Containerization | Docker Compose | ≥2.20 | Apache 2.0 |

All dependencies are permissively licensed. No proprietary or usage-metered libraries.

---

## Project Structure

```
eibo/
│
├── ui/                         # Streamlit pages
│   ├── main.py                 # App entry point and routing
│   ├── dashboard.py            # Executive dashboard
│   ├── simulator.py            # Budget simulation & scenario management
│   ├── drilldown.py            # Org → Dept → Team → Individual
│   ├── predictive.py           # Attrition risk & forecasts
│   ├── strategic.py            # Future state designer
│   ├── notifications_ui.py     # Notification center
│   ├── admin.py                # RBAC, config, health monitor
│   ├── info_page/              # Business & Engineering info views
│   └── components/             # Reusable Streamlit components
│
├── models/                     # ML models
│   ├── impact_scorer.py        # Composite 0–100 impact score
│   ├── network_analysis.py     # Graph construction & centrality
│   ├── attrition_predictor.py  # Attrition risk classification
│   └── early_warning.py        # Threshold-based alert system
│
├── optimization_engine/        # ILP workforce optimization
│   ├── ilp_solver.py           # solve() — PuLP CBC entry point
│   ├── constraints.py          # ConstraintConfig dataclass
│   ├── multi_objective.py      # Pareto frontier analysis
│   └── sensitivity.py          # Budget sensitivity scenarios
│
├── forecasting/                # Time-series & Monte Carlo
│   ├── budget_forecaster.py    # Prophet 12-month budget forecast
│   └── monte_carlo.py          # 5,000-run P10/P50/P90 fan charts
│
├── strategic_planner/          # Workforce planning modules
│   ├── future_state.py         # Proposed org structure modeler
│   ├── skills_gap.py           # Skill inventory & adjacency scoring
│   ├── transition_planner.py   # Roadmap generation
│   └── strategy_comparator.py  # Weighted strategy scoring
│
├── data_pipeline/              # Medallion ETL
│   ├── bronze_ingest.py        # Raw data ingestion
│   ├── silver_cleanse.py       # Normalization & validation
│   ├── gold_aggregate.py       # DuckDB materialized views
│   └── validators.py           # Schema & quality validators
│
├── demo_data/                  # Synthetic org generator
│   ├── generator.py            # DemoGenerator class
│   ├── scenarios.py            # Scenario config loader
│   ├── seed_demo.py            # CLI database seeder
│   └── organizations/          # Scenario JSON configs (A, B, C)
│
├── auth/                       # Access control
│   ├── rbac.py                 # 6-tier Role + Permission model
│   └── session_manager.py      # OAuth2/OIDC + local auth
│
├── audit/                      # Immutable event trail
│   ├── logger.py               # Thread-safe singleton logger
│   ├── trail_viewer.py         # Query & export interface
│   └── compliance_reports.py   # Formatted compliance output
│
├── notifications/              # Notification engine
│   ├── engine.py               # Store + bundler + dispatcher
│   └── channels/               # in_app, email, webhook
│
├── workflows/                  # Prefect-compatible flows
│   ├── engine.py               # @task / @flow decorators
│   ├── data_pipeline_flow.py   # Scheduled data refresh
│   ├── model_retraining_flow.py
│   └── report_generation_flow.py
│
├── integration_hub/            # HRIS connectors
│   ├── base_connector.py       # Abstract connector interface
│   ├── workday_connector.py
│   ├── bamboohr_connector.py
│   ├── generic_api_connector.py
│   └── ConnectorRegistry
│
├── health/
│   └── checker.py              # Component health + latency checks
│
├── utils/
│   ├── logging_config.py       # JSON + dev formatter
│   ├── sanitization.py         # SQL/XSS/path-traversal defense
│   └── secrets_validator.py    # Env var validation
│
├── tests/
│   ├── unit/                   # 573 unit tests
│   ├── integration/            # End-to-end pipeline tests
│   ├── performance/            # Wall-clock benchmark tests
│   └── security/               # RBAC & injection security tests
│
├── docs/
│   ├── user_guide/quickstart.md
│   ├── admin_guide/deployment.md
│   └── developer_guide/contributing.md
│
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
├── requirements.txt
└── requirements-dev.txt
```

---

## Setup & Installation

### Prerequisites

- Docker ≥ 24.0 and Docker Compose ≥ 2.20
- Or: Python 3.11+ with a virtual environment (for local development)

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/eibo.git
cd eibo
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and set the required variables:

```bash
# Database — required
POSTGRES_USER=eibo_user
POSTGRES_PASSWORD=<strong-password>
POSTGRES_DB=eibo_db
POSTGRES_HOST=postgres

# Application security — required
SECRET_KEY=<64-character-random-hex>

# Mode
DEMO_MODE_ENABLED=true    # true = no real data required
LOG_LEVEL=INFO
```

Generate a secure `SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Start the Stack

```bash
docker-compose up -d
```

First run downloads images and runs database migrations (~2–3 minutes).

### 4. Open the App

Navigate to `http://localhost:8501` in your browser.

The app starts in demo mode with a pre-loaded synthetic organization. No further configuration is required to explore every feature.

### 5. (Optional) Seed the Demo Database

```bash
docker-compose exec streamlit python demo_data/seed_demo.py --scenario all --size medium
```

### Local Development (Without Docker)

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

cp .env.example .env               # edit as above

streamlit run ui/main.py --server.runOnSave true
```

---

## Demo Scenarios

EIBO ships with three fully synthetic demo organizations covering the most common workforce budget situations:

### Scenario A — Growing Company
**Industry**: Software & Technology

A fast-growing tech company that scaled headcount 3x in 18 months. Engineering is overbudget, critical architecture knowledge is concentrated in three engineers, and there is no succession plan for the VP of Engineering.

**Key challenges**: DevOps skill gap (single qualified person), engineering overbudget by 25%, no leadership succession.

### Scenario B — Restructuring
**Industry**: Financial Services

A mid-size financial services firm facing a board-mandated 20% cost reduction. Multiple departments have overlapping roles, 60% of the technology team is on legacy COBOL systems with declining demand, and the Risk & Compliance function has a single expert on a new regulatory framework.

**Key challenges**: Operations redundancy, technology skills mismatch, single-point-of-failure compliance expertise.

### Scenario C — Merger Integration
**Industry**: Healthcare Technology

Two healthcare tech companies completed a merger six months ago. Duplicate leadership structures exist across both legacy entities, competing backend implementations are being built by teams that haven't yet unified, and unique HIPAA expertise from the acquired company is at attrition risk.

**Key challenges**: Duplicate C-suite, role overlap, clinical domain knowledge at risk.

Each scenario is available in three sizes: **Small** (50 employees), **Medium** (500), and **Large** (5,000).

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

Data isolation is enforced at query time: a Manager with `department="Engineering"` cannot access, simulate, or export data for any other department. Salary and PII visibility cascade independently of simulation permissions.

---

## Data Architecture

EIBO uses a three-layer medallion architecture:

```
Source Data (CSV / HRIS API)
        │
        ▼
   Bronze Layer
   Raw ingestion, no transformation.
   Original format preserved.
   bronze_ingest.py
        │
        ▼
   Silver Layer
   Cleansing: type coercion, normalization,
   duplicate detection, null handling,
   PII tokenization, schema validation.
   silver_cleanse.py
        │
        ▼
   Gold Layer
   DuckDB materialized views.
   Pre-aggregated for millisecond query latency.
   Incremental refresh on source changes.
   gold_aggregate.py
        │
        ▼
   Analytics & UI
```

**Key invariants**:
- Bronze data is write-once, never modified
- Silver cleansing is idempotent and replayable
- Gold views are derived and can be rebuilt from Silver at any time
- Demo data uses a separate schema/prefix — it can never mix with real data

---

## Optimization Engine

The ILP formulation:

```
Maximize:    Σ (impact_score_i × x_i)    for all employees i

Subject to:
  Budget:    Σ (cost_i × x_i) ≤ available_budget
  
  Leadership: for each team t:
              Σ (x_i × is_leader_i) ≥ 1
  
  Critical skills: for each skill s:
              Σ (x_i × has_skill_s_i) ≥ min_holders_s
  
  Optionally:
    Min team size:  Σ (x_i | team_i = t) ≥ min_team_size
    Succession:     Σ (x_i × has_skill_s_i) ≥ succession_depth + 1
  
  Domain:    x_i ∈ {0, 1}
```

Where `cost_i = annual_salary_i + annual_benefits_i`.

The CBC (Coin-or Branch and Cut) solver handles problems up to 5,000 employees within a configurable time limit (default 30s). For infeasible problems, EIBO identifies conflicting constraints and proposes resolution paths (e.g., "Increase budget by $X to satisfy leadership constraint for Team Y").

---

## Security & Privacy

EIBO is designed for HR data, which is PII-dense and regulation-sensitive.

| Control | Implementation |
|---|---|
| No external data transfer | All computation is local; zero API calls with employee data |
| Input sanitization | SQL injection, XSS, path traversal detection at all entry points (`utils/sanitization.py`) |
| PII masking | Role-based, applied at query time before UI rendering |
| Secrets validation | Startup check rejects placeholder values and enforces minimum entropy (`utils/secrets_validator.py`) |
| Audit trail | Every simulation, override, login, and config change is logged with user, timestamp, and outcome |
| RBAC enforcement | `AccessControl.require()` raises `PermissionError` before any data access |
| Department isolation | Query filters applied server-side based on `user.departments` scope |
| Structured logging | JSON-lines format in production; PII never logged, only anonymized IDs |

---

## Testing

734 tests across four suites:

```
tests/unit/          573 tests   Fast, isolated, no external dependencies
tests/integration/    50 tests   Multi-module vertical slices, no infrastructure mocking
tests/performance/    30 tests   Wall-clock benchmarks with defined thresholds
tests/security/       81 tests   RBAC boundaries, data leakage, injection prevention
```

Run the full suite:

```bash
pytest tests/ -v
```

Run specific suites:

```bash
pytest tests/unit/ -v                           # fast, no infrastructure needed
pytest tests/integration/ -v                   # end-to-end flows
pytest tests/performance/ -v --tb=short        # benchmark thresholds
pytest tests/security/ -v                      # OWASP-aligned security checks
```

With coverage:

```bash
pytest tests/ --cov=. --cov-report=html
```

Performance thresholds (small org, 50 employees):

| Operation | Threshold |
|---|---|
| Demo data generation | ≤ 5 seconds |
| Network centrality metrics | ≤ 5 seconds |
| Impact scoring | ≤ 5 seconds |
| ILP solve (70% budget) | ≤ 10 seconds |
| Attrition prediction | ≤ 5 seconds |
| Workflow pipeline flow | ≤ 5 seconds |

Security test coverage (OWASP-aligned):
- **A01 Broken Access Control**: 9 permissions × 6 roles = exhaustive boundary matrix
- **A03 Injection**: SQL injection, XSS, and path traversal — parametrized payload sets
- **Data leakage**: salary tier and PII tier verified for all 6 roles independently
- **Department isolation**: manager scope, executive scope, viewer denial
- **Secrets management**: placeholder detection, entropy minimums, demo vs production mode

---

## Documentation

| Document | Location | Audience |
|---|---|---|
| Quickstart (5 min) | `docs/user_guide/quickstart.md` | All users |
| Deployment & Admin | `docs/admin_guide/deployment.md` | System administrators |
| Contributing & Architecture | `docs/developer_guide/contributing.md` | Engineers |
| Info Page (Business View) | In-app → Info → Business View | HR / People Analytics stakeholders |
| Info Page (Engineering View) | In-app → Info → Engineering View | Technical evaluators |

---

## Project Status

All nine sprints are complete:

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

**Codebase**: 94 Python modules · 22,000+ lines · 734 tests passing

---

## Key Commands

```bash
# Start the full stack
docker-compose up -d

# Production deployment
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Seed demo database
python demo_data/seed_demo.py --scenario all --size medium

# Run data pipeline
python workflows/data_pipeline_flow.py --input data/payroll.csv

# Retrain models
python workflows/model_retraining_flow.py --force

# Check system health
python -c "from health.checker import get_health_summary; import json; print(json.dumps(get_health_summary(), indent=2))"

# Run full test suite
pytest tests/ -v

# Validate production secrets
python -c "from utils.secrets_validator import assert_production_secrets; assert_production_secrets()"

# Streamlit dev with hot reload
streamlit run ui/main.py --server.runOnSave true
```

---

## License

This project uses exclusively permissively-licensed open-source dependencies (MIT, Apache 2.0, BSD). See `requirements.txt` for the full dependency list with version pins.

---

*EIBO — Employee Impact & Budget Optimizer*
*OPB AI Mastery Lab · Octavio Pérez Bravo · Data & AI Strategy Architect*
*From pipeline to decision.*
