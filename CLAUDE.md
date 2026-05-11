# CLAUDE.md - Development Guide for Project EIBO

## Project Summary
EIBO (Employee Impact & Budget Optimizer) is a Capital and Budget Optimization Platform (POCP) that helps organizational leaders balance budget constraints with critical talent retention. It uses data science, graph theory, linear programming, predictive analytics, and strategic workforce modeling to recommend workforce optimization strategies with human oversight.

---

## Core Principles (Non-Negotiable)

### 1. Human-in-the-Loop
- The machine **suggests**, people **decide**
- Every model output must allow manual override with traceability
- UI design must make clear this is a decision support tool, not a verdict
- Override annotations must be supported ("Critical project until Q3")

### 2. Privacy & Security
- **Zero data to external services**: Everything runs locally
- HR data is sensitive by definition; treat with maximum care
- Never log personally identifiable information
- RBAC must enforce data isolation at department level
- PII masking required for roles without full visibility

### 3. Language & Tone
- **NEVER** use terms like: "terminated employee", "eliminate", "cut staff", "fire"
- **ALWAYS** use: "suggested retention", "structure optimization", "budget adjustment", "not retained in simulation"
- The tool optimizes for **retention**, not for layoffs
- Scenarios are "strategies", not "reduction plans"

### 4. 100% Open Source Stack
- **Forbidden** to add paid dependencies or restrictively licensed libraries
- Verify licenses of any library before adding to `requirements.txt`
- Prefer permissive licenses (MIT, Apache 2.0, BSD)
- Document license exceptions if unavoidable

### 5. Explainability
- Every ML prediction must be explainable (SHAP values required)
- Optimization decisions must show contributing factors
- Risk assessments must cite specific drivers
- "Black box" decisions are unacceptable for HR use cases

---

## Architecture: What You Need to Know

### Medallion Architecture (3 data layers)
ERP/HRIS → Bronze (raw) → Silver (clean) → Gold (aggregated) → UI

text
- **Bronze**: Never modify source data, only store. Preserve original format.
- **Silver**: Cleansing and normalization happens here. This is where data quality rules live.
- **Gold**: Materialized views for fast consumption. Incremental refresh where possible.

### Technology Stack
UI Layer: Streamlit (SPA with multi-page architecture)
Analytics Engine: DuckDB (fast in-memory queries, millisecond latency)
Relational DB: PostgreSQL (persistent data, user management, audit logs)
Cache: Redis (optional, for high-concurrency deployments)
Graph Analysis: NetworkX (collaboration relationships, centrality metrics)
Optimization: PuLP (Integer Linear Programming, multi-objective)
ML/Scoring: Scikit-learn (Random Forest, XGBoost, SHAP)
Forecasting: Prophet (time series, budget/headcount forecasting)
Anomaly Detection: PyOD (spending pattern outliers)
Workflow: Prefect (pipeline orchestration, scheduling)
Notifications: Custom engine (in-app, email, webhook)
Auth: OAuth2/OIDC (with local auth fallback)
Deployment: Docker Compose (single-node), K8s-ready design

text

### Directory Structure
/project_root
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
├── requirements.txt
├── requirements-dev.txt
├── README.md
├── PLAN.md
├── CLAUDE.md
├── BRAND.md ← MANDATORY UI GUIDE
├── /data_pipeline
│ ├── bronze_ingest.py
│ ├── silver_cleanse.py
│ ├── gold_aggregate.py
│ └── validators.py
├── /demo_data
│ ├── generator.py ← Synthetic data generator
│ ├── scenarios.py ← Pre-built scenario definitions
│ ├── seed_demo.py ← Database seeding CLI
│ └── organizations/ ← Scenario configs (JSON)
├── /models
│ ├── impact_scorer.py
│ ├── train_impact_model.py
│ ├── attrition_predictor.py
│ ├── train_attrition_model.py
│ └── explainability.py ← SHAP integration
├── /optimization_engine
│ ├── ilp_solver.py
│ ├── constraints.py
│ ├── multi_objective.py ← Pareto frontier
│ └── sensitivity.py ← Sensitivity analysis
├── /forecasting
│ ├── budget_forecaster.py
│ ├── headcount_forecaster.py
│ └── monte_carlo.py
├── /strategic_planner
│ ├── future_state.py
│ ├── skills_gap.py
│ ├── transition_planner.py
│ └── strategy_comparator.py
├── /workflows
│ ├── data_pipeline_flow.py
│ ├── model_retraining_flow.py
│ └── report_generation_flow.py
├── /integration_hub
│ ├── base_connector.py
│ ├── workday_connector.py
│ ├── successfactors_connector.py
│ ├── bamboohr_connector.py
│ └── generic_api_connector.py
├── /auth
│ ├── rbac.py
│ ├── oauth_providers.py
│ └── session_manager.py
├── /notifications
│ ├── engine.py
│ ├── channels/
│ │ ├── in_app.py
│ │ ├── email_channel.py
│ │ └── webhook_channel.py
│ └── templates/
├── /audit
│ ├── logger.py
│ ├── trail_viewer.py
│ └── compliance_reports.py
├── /ui
│ ├── main.py ← App entry point
│ ├── info_page/
│ │ ├── business_view.py
│ │ ├── engineering_view.py
│ │ └── diagrams.py
│ ├── dashboard.py
│ ├── simulator.py
│ ├── drilldown.py
│ ├── predictive.py ← Attrition & forecast views
│ ├── strategic.py ← Future state designer
│ ├── admin.py ← RBAC, config, health
│ ├── notifications_ui.py
│ └── components/ ← Reusable UI components
├── /tests
│ ├── unit/
│ ├── integration/
│ ├── performance/
│ ├── security/
│ └── fixtures/
└── /docs
├── user_guide/
├── admin_guide/
├── developer_guide/
└── images/


---

## Key Design Decisions

### 1. Demo Database (Critical for Adoption)
- **Must work with zero configuration**: "Load Demo" button on homepage
- Three organization sizes: Small (50 emp), Medium (500 emp), Large (5,000 emp)
- Three scenarios each: Growing Company, Restructuring, Merger Integration
- Data must be realistic:
  - Salaries follow market distributions (not uniform)
  - Collaboration networks follow organizational patterns (not random)
  - Performance data has seasonal patterns
  - Include deliberate edge cases for demonstrating platform value
- Demo mode flag: `st.session_state.demo_mode = True`
- Never allow demo data to mix with real data (separate DB schema or prefix)

### 2. Info Page (Two Mandatory Views)
- **Business View**: For People Analytics and HR stakeholders
  - No code or technical jargon
  - Visual diagrams explaining concepts
  - ROI calculator
  - Guided tour
- **Engineering View**: For technical evaluators
  - Architecture diagrams (render dynamically, not static images)
  - Algorithm descriptions with mathematical notation (LaTeX)
  - Performance benchmarks
  - Security architecture
- Both views must be accessible from a single "Info" tab with toggle

### 3. Impact Score (ML Model)
- **Not just performance**: It's a combination of:
  - KPI history with trend (40%)
  - Collaboration network centrality (30%)
  - Skill criticality and uniqueness (20%)
  - Estimated replacement cost (10%)
- **Explainability is mandatory**: Every score must show SHAP breakdown
- Model is retrained with historical retention data
- If no historical data, use weighted heuristics as fallback
- Fairness audit required: check for demographic bias

### 4. ILP Engine (PuLP)
- **Objective Function**: Maximize Σ(impact_score_i × x_i)
- **Variable x_i**: Binary (1 = retained, 0 = not retained in simulation)
- **Mandatory constraints**:
  - Budget: Σ(cost_i × x_i) ≤ available_budget
  - Leadership: At least 1 leader per team
  - Critical skills: At least 1 person with each critical skill on team
- **Optional constraints** (configurable):
  - Diversity representation thresholds
  - Succession planning backups
  - Minimum team size
- Multi-objective optimization: Pareto frontier for budget vs impact trade-offs
- If infeasible: show conflicting constraints with resolution suggestions

### 5. Attrition Risk Model
- **Classification approach** with probability calibration
- Must handle class imbalance (attrition is rare) via SMOTE
- Output calibrated probabilities, not binary predictions
- Risk categories: Low, Moderate, High, Critical
- SHAP drivers required for each prediction
- Retraining schedule: monthly or on data drift detection

### 6. Forecasting
- Prophet for time series with:
  - Seasonality detection (annual, quarterly review cycles)
  - Known future events injection
  - Confidence intervals (80% and 95%)
- Monte Carlo for stress testing budget scenarios
- MAPE target: <15% for 3-month horizon

### 7. Network Metrics (NetworkX)
- **Degree centrality**: Direct connections count
- **Betweenness centrality**: Bridge role indicator
- **Eigenvector centrality**: Influence score
- **PageRank**: Alternative influence measure
- Community detection: Louvain method for natural clusters
- All normalized 0-1
- Employees with betweenness > 0.7: flagged as "Nexus"
- Team fragility = f(dependency concentration on few individuals)

### 8. RBAC Model
Viewer → Analyst → Manager → Director → Executive → Admin

text
- **Viewer**: Dashboards only, no simulation
- **Analyst**: Run simulations, create scenarios, no overrides
- **Manager**: Own department, full features, can override
- **Director**: Multiple departments, strategic planning access
- **Executive**: Organization-wide, all features except admin
- **Admin**: System configuration, user management, audit logs
- Data-level isolation: Department-scoped queries based on role
- Salary visibility: Full/Partial (ranges)/Masked based on role

### 9. Data Handling
- Salaries always in normalized currency (convert on ingestion)
- Dates in ISO 8601 format (YYYY-MM-DD)
- Employee IDs as strings (never use social security numbers)
- Null values in skills → "does not possess the skill" (no imputation)
- PII masking for roles without full access
- Data retention policies must be configurable

---

## Sprint Development Guidelines

### Sprint 1: Data & Infrastructure + Demo Database
- **Demo database is a first-class feature, not an afterthought**
- Data generator must produce realistic patterns, not random data
- Info page Business View: explain concepts visually before asking users to engage
- Info page Engineering View: be honest about limitations, clear about strengths
- Diagrams must be dynamic (Plotly/Altair), not static images
- Validate demo data with: `python -m pytest tests/unit/test_demo_generator.py`
- BRAND.md compliance from day one (even for Info pages)

### Sprint 2: Scoring & Dashboard
- Dashboard must tell a story: "Where are we spending? Where is our critical talent?"
- Impact scores must have SHAP explanations from first deployment
- Performance targets: <100ms for 50K employees (anticipating Sprint 7 load)
- Fairness audit results must be accessible (Engineering View of Info page)
- Centrality metrics must be recalculable on data changes

### Sprint 3: Optimization & Simulation
- Budget slider must have realistic limits (min: 50% current, max: 120%)
- Simulation auto-runs on slider move (500ms debounce)
- Manual overrides generate visual diff (model suggestion vs human decision)
- Annotation support for overrides (free text reason)
- Scenario comparison: support 5+ simultaneous scenarios
- Sensitivity analysis: ±5%, ±10%, ±20% budget scenarios
- Cascade effects must be shown when protecting one employee forces others out

### Sprint 4: Graphs & Drill-Down
- Graph must not saturate: max ~50 nodes visible, group the rest by community
- Drill-down maintains context (breadcrumbs, not lost navigation)
- Individual view: complete profile with radar chart, sparklines, skill matrix
- "Nexus" badge for high-centrality employees
- Export system: CSV, Excel, PDF (formatted, not raw dump)
- Docker Compose must work with single command

### Sprint 5: Predictive Analytics
- Attrition model must not cause panic: frame as "retention opportunities"
- Forecasts must show uncertainty (confidence intervals, not point estimates)
- Early warning system: configurable thresholds per department
- Monte Carlo: fan chart visualization for communicating uncertainty
- Risk digest: weekly automated summary with actionable recommendations
- All predictions must be explainable (SHAP)

### Sprint 6: Strategic Planning
- Future State Designer: drag-and-drop with cost calculations
- Build vs Buy: data-driven recommendations, not opinions
- Transition roadmap: realistic timelines with buffer for uncertainty
- Strategy comparison: weighted scoring based on user-defined priorities
- Executive presentation mode: clean, boardroom-ready output

### Sprint 7: Enterprise Readiness
- RBAC must be tested with penetration testing scenarios
- Audit trail: immutable, queryable, exportable
- Multi-tenancy: logical separation with zero cross-tenant leakage
- Performance: 100K employees, 100 concurrent users, <2s dashboard loads
- Health dashboard: model drift detection, service status, error rates

### Sprint 8: Notifications & Integrations
- Notifications must be smart-bundled (no alert fatigue)
- Workflows: idempotent, retryable, observable
- Connectors: abstract interface for extensibility
- Data mapping: preview before applying transformations
- Webhook support for Slack, Teams, custom integrations

### Sprint 9: Testing & Documentation
- Coverage target: >85% unit, critical path integration, UI smoke tests
- Documentation: getting started in 5 minutes, complete admin guide
- Security: OWASP Top 10 scan, dependency audit, RBAC penetration test
- Accessibility: WCAG 2.1 AA target
- Production hardening: secrets management, health checks, disaster recovery

---

## ⚠️ CRITICAL RULE: UI Decisions → BRAND.md

### Before writing ANY interface code:
1. **Read BRAND.md completely**
2. Verify:
   - Approved color palette (check for semantic color meanings)
   - Typography and hierarchy rules
   - Tone of voice and approved terminology
   - Allowed iconography set
   - Defined interaction patterns (buttons, forms, navigation)
   - Accessibility requirements (contrast ratios, focus states)

### What you must NEVER do in UI:
- ❌ Use red for "at-risk" or "not retained" statuses
- ❌ Labels like "Terminate", "Eliminate", "Expendable", "Fire", "Cut"
- ❌ Rankings of "worst employees" or "most expensive"
- ❌ Dehumanizing charts (people disappearing, red X marks)
- ❌ Aggressive confirmations ("Are you sure you want to FIRE X?")
- ❌ Binary language around people decisions
- ❌ Truncate employee names or use ID-only displays
- ❌ Show salary data to unauthorized roles

### What you must ALWAYS do:
- ✅ Use green/blue for "Retained", gray/neutral for "Not Retained in Simulation"
- ✅ Labels: "Retain", "Review", "Critical Talent", "Organizational Nexus"
- ✅ Show human context: skills, contributions, tenure, team role
- ✅ Respectful confirmations: "Simulation suggests not retaining X. Adjust?"
- ✅ Confidence indicators: show uncertainty, not false precision
- ✅ Always remember: behind every record is a person with a career
- ✅ Provide override reasons field
- ✅ Mask or hide salary data based on role permissions

### Info Page Specific Rules:
- **Business View**: Zero code, zero jargon. Visual-first explanations.
- **Engineering View**: Accurate, detailed, honest. Include limitations.
- Diagrams must be interactive when possible (hover, click, zoom)
- ROI calculator: use conservative assumptions, show methodology

---

## Useful Commands

### Development
```bash
# Start entire stack
docker-compose up -d

# Start with production overrides
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# View specific service logs
docker-compose logs -f streamlit
docker-compose logs -f postgres

# Run data pipeline (production data)
python data_pipeline/bronze_ingest.py --input data/payroll.csv
python data_pipeline/silver_cleanse.py
python data_pipeline/gold_aggregate.py

# Seed demo database
python demo_data/seed_demo.py --scenario all --size medium
python demo_data/seed_demo.py --scenario A --size small  # Specific scenario

# Validate demo data
python -m pytest tests/unit/test_demo_generator.py -v

# Retrain impact model
python models/train_impact_model.py --data gold/ --output models/impact_model.joblib

# Retrain attrition model
python models/train_attrition_model.py --data gold/ --output models/attrition_model.joblib

# Run tests
pytest tests/ -v
pytest tests/ --cov=. --cov-report=html  # With coverage

# CLI simulation (for debugging)
python optimization_engine/ilp_solver.py --budget 500000 --team 3

# Run sensitivity analysis
python optimization_engine/sensitivity.py --budget 500000 --variations 5,10,20

# Streamlit dev (hot reload)
streamlit run ui/main.py --server.runOnSave true

# Lint and format
black .
ruff check .
mypy .
Workflows (Prefect)
bash
# Start Prefect server (local)
prefect server start

# Run data pipeline workflow
python workflows/data_pipeline_flow.py --input data/payroll.csv

# Schedule daily risk assessment
python workflows/risk_assessment_flow.py --schedule daily

# Run model retraining workflow
python workflows/model_retraining_flow.py --force
Testing
bash
# Unit tests
pytest tests/unit/ -v

# Integration tests (requires running services)
pytest tests/integration/ -v --run-integration

# Performance benchmarks
pytest tests/performance/ -v --benchmark

# Security scan
bandit -r .
safety check

# Load test (with locust, if installed)
locust -f tests/performance/locustfile.py --host http://localhost:8501
Database
bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Backup demo database
pg_dump -h localhost -U eibo_user eibo_db > backups/demo_backup.sql

# Restore demo database
psql -h localhost -U eibo_user eibo_db < backups/demo_backup.sql
Environment Variables (.env)
bash
# Database
POSTGRES_USER=eibo_user
POSTGRES_PASSWORD=<secure_password_generated>
POSTGRES_DB=eibo_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# DuckDB
DUCKDB_PATH=/data/eibo_analytics.db

# Redis (optional, for caching)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# Application
LOG_LEVEL=INFO
MAX_EMPLOYEES_SIMULATION=5000
SIMULATION_TIMEOUT_SECONDS=10
DEMO_MODE_ENABLED=true
SECRET_KEY=<generate_random_64_char_string>

# Authentication (OAuth2/OIDC)
OAUTH_PROVIDER=google  # google, azure, okta, local
OAUTH_CLIENT_ID=
OAUTH_CLIENT_SECRET=
OAUTH_DISCOVERY_URL=

# Email (for notifications)
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
EMAIL_FROM=noreply@eibo.local

# Integrations
WORKDAY_API_URL=
WORKDAY_API_KEY=
SUCCESSFACTORS_API_URL=
SUCCESSFACTORS_API_KEY=

# Data retention
AUDIT_LOG_RETENTION_DAYS=365
SIMULATION_HISTORY_RETENTION_DAYS=90
```

# Development FAQs
Q: How do I add a new demo scenario?
A: Create a JSON config in demo_data/organizations/ following the schema, then register it in demo_data/scenarios.py. Run python demo_data/seed_demo.py --validate to check.

Q: Streamlit seems limited for complex UI. Can I use something else?
A: Streamlit is the current standard. If a feature absolutely cannot be built in Streamlit, discuss with the architecture team. Any alternative must be open source and run in Docker.

Q: How do I add a new HRIS connector?
A: Extend integration_hub/base_connector.py, implement the required interface methods, add field mappings to the mapping engine, and write integration tests against the vendor's sandbox.

Q: What happens if the ILP model finds no feasible solution?
A: Return infeasibility details: which constraints conflict, suggested resolutions (increase budget XX, relax skills constraint Y, protect fewer employees). Never return an empty or partial solution.

Q: How do I handle model drift detection?
A: Compare current predictions vs actual outcomes quarterly. If R² drops below threshold or SHAP distributions shift significantly, trigger retraining workflow. Log drift metrics to health dashboard.

Q: Can I cache model predictions?
A: Yes, for identical inputs (same employee features, same constraints). Use Redis with TTL. Invalidate on model retraining or data updates. Never cache across different tenants.

Q: How are notifications deduplicated?
A: Same risk source + same time window → bundle. Configurable windows per notification type. Users can set digest preferences (immediate, hourly, daily).

# Project Glossary
## Technical Term	Meaning in EIBO
Impact Score	0-100 score combining performance, centrality, skills, and replacement cost
Nexus Employee	Person with high betweenness centrality whose departure would fragment the collaboration network
Suggested Retention	Model output: employee who should be retained under budget constraint
Not Retained in Simulation	Model output: employee the model doesn't prioritize under given budget
Override	Human decision changing model suggestion (force retain or exclude)
Human-in-the-loop	Principle that every final decision is human, model only informs
Drill-Down	Hierarchical navigation from organizational view to individual
Available Budget	Target amount against which optimization runs (slider variable)
Attrition Risk	Probability (0-100%) that employee will voluntarily leave within 12 months
Monte Carlo Simulation	Stochastic method for budget stress testing with thousands of random scenarios
Future State Designer	Strategic tool for modeling proposed organizational structures
Build vs Buy	Analysis comparing internal upskilling cost vs external hiring for skill gaps
Team Fragility	Measure of team dependency on few critical individuals (0-100)
Skill Adjacency	How close an employee's current skills are to a target skill (training distance)
Pareto Frontier	Set of optimal solutions where improving one objective requires sacrificing another
Fan Chart	Visualization showing forecast confidence intervals widening over time
RBAC	Role-Based Access Control: 6-tier permission model (Viewer to Admin)
Tenant	Isolated business unit/division within shared infrastructure
Contacts & Responsibilities
Data Pipeline + Demo DB: Owner of bronze/silver/gold + synthetic data generator

ML Models: Owner of impact scoring, attrition prediction, SHAP explainability

ILP Engine: Owner of optimization, constraints, sensitivity analysis

Forecasting: Owner of Prophet models, Monte Carlo simulation

Strategic Planner: Owner of future state designer, skills gap, transition planning

UI/UX: Owner of Streamlit, BRAND.md compliance, accessibility, Info page

Notifications & Workflows: Owner of notification engine, Prefect flows

Integrations: Owner of HRIS connectors, data mapping engine

Auth & Audit: Owner of RBAC, OAuth, audit trail, compliance reports

DevOps: Owner of Docker, deployment, monitoring, disaster recovery

Each area is responsible for its unit tests + integration tests + documentation.

# Quick Reference: Key Files
Purpose	File
App entry	ui/main.py
Demo generator	demo_data/generator.py
Demo seeder	demo_data/seed_demo.py
Info - Business	ui/info_page/business_view.py
Info - Engineering	ui/info_page/engineering_view.py
Impact model	models/impact_scorer.py
Attrition model	models/attrition_predictor.py
ILP solver	optimization_engine/ilp_solver.py
Budget forecast	forecasting/budget_forecaster.py
Future state	strategic_planner/future_state.py
RBAC	auth/rbac.py
Audit logger	audit/logger.py
Notification engine	notifications/engine.py
Base connector	integration_hub/base_connector.py
Data pipeline flow	workflows/data_pipeline_flow.py
UI components	ui/components/
Unit tests	tests/unit/
Integration tests	tests/integration/
text

---

