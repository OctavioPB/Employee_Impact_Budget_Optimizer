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

---

## Technical Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│  PRESENTATION LAYER                                                  │
│  React 18 + TypeScript (Vite 5 SPA)                                  │
│  Dashboard · Simulation · Drill-Down · Predictive · Strategic        │
│  Notifications · Admin · Info (Business + Engineering views)         │
├──────────────────────────────────────────────────────────────────────┤
│  API LAYER                                                           │
│  FastAPI (Python) · REST endpoints · Pydantic schemas               │
│  /api/dashboard · /api/simulate · /api/predictive/attrition          │
│  /api/notifications · /api/health                                    │
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
      ├──► Impact Scorer ──► ILP Optimizer ──► FastAPI ──► React UI
      │
      ├──► Network Analysis ──► Drill-Down / Graph UI
      │
      ├──► Attrition Predictor ──► Predictive UI / Alerts
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
| Anomaly Detection | PyOD | ≥1.1 | BSD |
| Explainability | SHAP | ≥0.45 | MIT |
| Data Processing | pandas, numpy | ≥2.0 / ≥1.26 | BSD |
| Containerization | Docker Compose | ≥2.20 | Apache 2.0 |

All dependencies are permissively licensed. No proprietary or usage-metered libraries.

---

## Project Structure

```
eibo/
│
├── frontend/                   # React 18 + TypeScript SPA
│   ├── src/
│   │   ├── App.tsx             # Page routing (useState, no router lib)
│   │   ├── pages/
│   │   │   ├── InfoPage.tsx    # Landing page (Business + Engineering views)
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── SimulationPage.tsx
│   │   │   ├── DrillDownPage.tsx
│   │   │   ├── PredictivePage.tsx
│   │   │   ├── StrategicPage.tsx
│   │   │   ├── NotificationsPage.tsx
│   │   │   └── AdminPage.tsx
│   │   ├── components/
│   │   │   ├── Nav.tsx         # Sticky top nav bar
│   │   │   ├── Footer.tsx
│   │   │   └── Eyebrow.tsx     # Gold rule + label component
│   │   ├── hooks/
│   │   │   └── useTheme.ts     # Dark/light mode (localStorage)
│   │   ├── stores/
│   │   │   └── demoStore.ts    # Zustand: scenario, size, demo flag
│   │   ├── services/
│   │   │   └── api.ts          # All HTTP calls (no direct fetch in components)
│   │   └── styles/
│   │       └── tokens.css      # OPB design tokens (CSS custom properties)
│   ├── index.html
│   ├── vite.config.ts          # /api/* proxied to localhost:8000
│   ├── tsconfig.json           # Strict TypeScript
│   ├── package.json
│   ├── Dockerfile              # Multi-stage: build → nginx
│   └── nginx.conf              # /api/* → backend:8000, SPA fallback
│
├── backend/                    # FastAPI REST API
│   ├── main.py                 # FastAPI app + CORS + router registration
│   ├── routers/
│   │   ├── dashboard.py        # GET /api/dashboard
│   │   ├── simulation.py       # POST /api/simulate
│   │   ├── predictive.py       # GET /api/predictive/attrition
│   │   └── notifications.py    # GET/POST /api/notifications
│   ├── services/
│   │   └── data_service.py     # Wraps demo_data.generator (lru_cache, no Streamlit)
│   └── Dockerfile
│
├── models/                     # ML models
│   ├── impact_scorer.py
│   ├── network_analysis.py
│   ├── attrition_predictor.py
│   └── early_warning.py
│
├── optimization_engine/        # ILP workforce optimization
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
├── data_pipeline/              # Medallion ETL
│   ├── bronze_ingest.py
│   ├── silver_cleanse.py
│   ├── gold_aggregate.py
│   └── validators.py
│
├── demo_data/                  # Synthetic org generator
│   ├── generator.py            # DemoGenerator class
│   ├── scenarios.py            # Scenario config loader
│   ├── seed_demo.py            # CLI database seeder
│   └── organizations/          # Scenario JSON configs (A, B, C)
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
├── ui/                         # Legacy Streamlit UI (kept for reference)
│   └── main.py
│
├── docker-compose.yml          # postgres + backend + frontend + pgadmin
├── docker-compose.prod.yml
├── .env.example
├── requirements.txt            # Python deps (includes fastapi, uvicorn)
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

---

## Security & Privacy

| Control | Implementation |
|---|---|
| No external data transfer | All computation is local; zero API calls with employee data |
| Input sanitization | SQL injection, XSS, path traversal detection at all entry points |
| PII masking | Role-based, applied at query time before UI rendering |
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
pytest tests/unit/ -v                   # 573 tests — fast, no infrastructure
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
# Run locally, or with the stack up: docker-compose exec backend python demo_data/seed_demo.py --scenario all --size medium
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
| **10** | **React 18 + FastAPI migration (UI layer)** | **Complete** |

**Codebase**: 94 Python modules · React SPA (8 pages) · FastAPI REST layer · 22,000+ lines · 734 tests

---

## License

This project uses exclusively permissively-licensed open-source dependencies (MIT, Apache 2.0, BSD). See `requirements.txt` and `frontend/package.json` for the full dependency lists.

---

*EIBO — Employee Impact & Budget Optimizer*
*OPB · Octavio Pérez Bravo · Data & AI Strategy Architect*
*From pipeline to decision.*
