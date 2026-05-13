# EIBO Developer Guide

> Architecture reference, extension points, and contribution standards.

---

## Architecture

EIBO follows a **Medallion + Module** architecture:

```
                       Browser
                          │
                    Streamlit UI
                  ui/main.py (SPA)
                          │
          ┌───────────────┼────────────────┐
          │               │                │
      Dashboard      Simulation        Predictive
      Drill-Down     Scenarios         Strategic
      Notifications  Admin             (etc.)
          │               │                │
          └───────────────┼────────────────┘
                          │
               ┌──────────┴──────────┐
               │                     │
          Analytics Engine      Optimization Engine
          models/               optimization_engine/
          DuckDB (Gold layer)   ILP via PuLP
               │
     ┌─────────┴──────────┐
     │                    │
  Silver layer         Gold layer
  (clean data)         (aggregated views)
     │
  Bronze layer
  (raw ingestion)
     │
  Source data (CSV / HRIS connectors)
```

### Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| UI framework | Streamlit | 100% open source, single-command deploy |
| Analytics | DuckDB | In-process, millisecond latency, no server overhead |
| Optimization | PuLP (CBC solver) | MIT license, ILP-native, constraint-based |
| ML framework | scikit-learn | Mature, SHAP-compatible, open source |
| Forecasting | Prophet | Handles seasonality and business calendars |
| Network analysis | NetworkX | Full graph algorithm library |
| Persistence | PostgreSQL | ACID, audit trail, RBAC |
| Workflow | Prefect-compatible decorators | Observable, retryable, local-first |

---

## Repository Structure

```
eibo/
├── data_pipeline/         # Bronze/Silver/Gold ETL
├── demo_data/             # Synthetic data generation
│   ├── generator.py       # DemoGenerator class
│   └── organizations/     # Scenario config JSON files
├── models/                # ML models and scoring
│   ├── impact_scorer.py   # ImpactScorer (heuristic + ML)
│   ├── attrition_predictor.py
│   └── network_analysis.py
├── optimization_engine/   # ILP solver
│   ├── ilp_solver.py      # solve() entry point
│   ├── constraints.py     # ConstraintConfig
│   ├── multi_objective.py # Pareto frontier
│   └── sensitivity.py
├── forecasting/           # Prophet + Monte Carlo
├── strategic_planner/     # Future state modeling
├── workflows/             # Prefect-compatible flows
├── integration_hub/       # HRIS connectors
│   ├── base_connector.py  # AbstractBaseConnector
│   └── *_connector.py     # Concrete implementations
├── auth/                  # RBAC + OAuth
│   ├── rbac.py            # Role enum, RBACManager, decorators
│   └── session_manager.py
├── notifications/         # Notification engine
│   ├── engine.py          # NotificationEngine + Store
│   └── channels/          # EmailChannel, WebhookChannel, InAppChannel
├── audit/                 # Audit trail
│   └── logger.py          # AuditLogger singleton
├── health/                # Health checking
│   └── checker.py         # HealthChecker, ComponentHealth
├── utils/                 # Cross-cutting utilities
│   ├── logging_config.py  # JsonFormatter, configure_logging()
│   ├── sanitization.py    # Input sanitization + threat detection
│   └── secrets_validator.py
├── ui/                    # Streamlit pages
│   ├── main.py            # App entry point
│   ├── components/        # Reusable UI components
│   └── info_page/         # Business + Engineering views
├── tests/
│   ├── unit/              # Isolated unit tests
│   ├── integration/       # Multi-module tests
│   ├── performance/       # Benchmark tests
│   └── security/          # RBAC + injection tests
└── docs/                  # This documentation
```

---

## Development Setup

### 1. Create a Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
.venv\Scripts\activate           # Windows
pip install -r requirements-dev.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Set DEMO_MODE_ENABLED=true for local development
# Set LOG_MODE=development for colored console output
```

### 3. Start Streamlit with Hot Reload

```bash
streamlit run ui/main.py --server.runOnSave true
```

### 4. Run Tests

```bash
# All tests
pytest tests/ -v

# Unit tests only (fast)
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# Performance benchmarks
pytest tests/performance/ -v --tb=short

# Security tests
pytest tests/security/ -v

# With coverage
pytest tests/ --cov=. --cov-report=html
```

### 5. Lint and Format

```bash
black .
ruff check .
mypy .
```

---

## Coding Standards

### Mandatory

- **Type hints on all public functions**: `def score(employees_df: pd.DataFrame) -> ScorerResult`
- **No bare `except`**: Always catch specific exception types
- **No `print()` in production code**: Use `logging.getLogger(__name__)`
- **Input sanitization at boundaries**: Use `utils/sanitization.py` for any user-supplied string or number
- **BRAND.md compliance for all UI**: Read `BRAND.md` before writing any Streamlit code
- **SHAP explanations for all ML outputs**: Every prediction must expose SHAP values
- **Human-in-the-loop framing**: "Suggested Retention" / "Not Retained in Simulation" — never "fired", "eliminated", "cut"

### Naming Conventions

```python
# Classes: PascalCase
class ImpactScorer: ...

# Functions and variables: snake_case
def compute_centrality_metrics(graph: nx.Graph) -> CentralityResult: ...

# Constants: UPPER_SNAKE_CASE
MAX_EMPLOYEES_DEFAULT = 5_000

# Module files: snake_case
# impact_scorer.py, budget_forecaster.py

# Test functions: test_<unit>_<behavior>_<condition>
def test_ilp_solver_returns_optimal_when_budget_is_sufficient(): ...
```

### Testing Standards

Every new function or class needs:
1. A **smoke test** (import + basic instantiation — catches setup errors early)
2. **Unit tests** for the happy path
3. **Unit tests** for edge cases and error conditions
4. **Integration tests** if the module interacts with other modules

Coverage target: >85% for all modules.

---

## Extending the Platform

### Adding a New Demo Scenario

1. Create a JSON config in `demo_data/organizations/`:

```json
{
  "scenario_id": "D",
  "name": "Spin-off",
  "description": "A business unit separating into an independent company.",
  "headcount": {
    "small": 50,
    "medium": 500,
    "large": 5000
  },
  "budget_pressure": 0.85,
  "attrition_multiplier": 1.4
}
```

2. Register it in `demo_data/scenarios.py`:

```python
SCENARIOS["D"] = ScenarioConfig.from_json("demo_data/organizations/scenario_d.json")
```

3. Validate: `pytest tests/unit/test_demo_generator.py -v`

---

### Adding a New HRIS Connector

All connectors extend `integration_hub.base_connector.BaseConnector`:

```python
from integration_hub.base_connector import BaseConnector, ConnectorSchema, FieldMapping

class MyHRISConnector(BaseConnector):
    """Connector for MyHRIS API v3."""

    def __init__(self, api_url: str, api_key: str) -> None:
        schema = ConnectorSchema(
            source_name="MyHRIS",
            field_mappings=[
                FieldMapping(source_field="emp_id", target_field="employee_id"),
                FieldMapping(source_field="full_name", target_field="name"),
                FieldMapping(source_field="dept", target_field="department"),
                FieldMapping(source_field="base_salary", target_field="annual_salary",
                             transform="multiply_12"),  # if monthly
            ],
        )
        super().__init__(schema=schema)
        self._api_url = api_url
        self._api_key = api_key

    def fetch_employees(self) -> list[dict]:
        """Fetch raw employee records from the API."""
        # Implementation here — return list of raw dicts
        ...

    def test_connection(self) -> bool:
        """Return True if the API is reachable and credentials are valid."""
        ...
```

Register the connector:

```python
# integration_hub/__init__.py
from integration_hub.connector_registry import ConnectorRegistry
ConnectorRegistry.register("myhris", MyHRISConnector)
```

Write integration tests in `tests/integration/` against the vendor's sandbox.

---

### Adding a New Notification Channel

Extend `notifications.channels.base.BaseChannel`:

```python
from notifications.channels.base import BaseChannel
from notifications.engine import Notification

class SlackChannel(BaseChannel):
    """Send notifications to a Slack webhook."""

    def __init__(self, webhook_url: str) -> None:
        self._webhook_url = webhook_url

    def deliver(self, notification: Notification) -> bool:
        """Return True if delivery succeeded."""
        payload = {
            "text": f"*{notification.title}*\n{notification.message}",
        }
        # Use httpx to POST to self._webhook_url
        ...
```

Register in `notifications/engine.py`'s channel list.

---

### Adding a New Prefect-Compatible Workflow

```python
from workflows.engine import task, flow

@task(name="my_task", retries=2)
def my_task(data: dict) -> dict:
    """Process data."""
    return {"processed": True, **data}

@flow(name="my_flow")
def my_flow(input_path: str, _flow_run=None) -> None:
    """Top-level workflow."""
    data = load_data(input_path)
    result = my_task(data)
    # _flow_run is injected automatically — use for logging if needed
```

> **Important**: Always include `_flow_run=None` as a parameter in your `@flow`-decorated function. The workflow engine injects this kwarg when calling the wrapped function.

---

### Adding a New UI Page

1. Create `ui/your_page.py` with a `render()` function:

```python
import streamlit as st
from ui.components.brand import page_header

def render() -> None:
    page_header("Your Page Title", "Optional subtitle")
    # Streamlit components here
    # Remember: BRAND.md compliance is mandatory
```

2. Register in `ui/main.py`:

```python
# In _render_sidebar(), add to pages dict:
pages = {
    ...
    "your_page": "🆕  Your Page",
    ...
}

# In main(), add routing:
elif page == "your_page":
    your_page.render()
```

3. Import at the top of `ui/main.py`:

```python
from ui import ..., your_page
```

---

## Security Requirements

All contributions must comply:

- **No PII in logs**: Never log employee names, salaries, or IDs. Log only anonymized identifiers or counts.
- **Sanitize all inputs**: Run user strings through `utils/sanitization.py` before use in queries or display.
- **RBAC checks before data access**: Use `@require_role(Role.ANALYST)` decorator on any function that returns sensitive data.
- **No external network calls from sensitive paths**: All ML inference and optimization runs locally.
- **Audit trail for all mutations**: Log every simulation, override, user creation, and configuration change via `audit.logger`.

Run the security tests before submitting a PR:

```bash
pytest tests/security/ -v
bandit -r . --skip B101  # B101 = assert usage (acceptable in tests)
safety check              # Check for known vulnerable dependencies
```

---

## Pull Request Process

1. **Branch naming**: `feat/short-description`, `fix/short-description`, `chore/short-description`
2. **Tests**: All new code must have tests. `pytest tests/ -v` must pass.
3. **Coverage**: `--cov` report must not decrease below 85% for modified modules.
4. **Lint**: `black .` and `ruff check .` must pass with no warnings.
5. **BRAND.md**: For any UI change, include a note confirming BRAND.md compliance was checked.
6. **Security**: For any change touching auth, RBAC, or data access, tag a security review.
7. **PR description**: Include what changed, why, and how to test it.

---

## Glossary

| Term | Definition |
|---|---|
| Impact Score | 0–100 score: 40% KPI history, 30% network centrality, 20% skill criticality, 10% replacement cost |
| Organizational Nexus | Employee with betweenness centrality > 0.7; flagged in the UI |
| Suggested Retention | Model recommendation to retain within budget constraints |
| Not Retained in Simulation | Model output indicating this person falls outside budget in the current scenario |
| Override | Human decision changing the model's suggestion, with annotation |
| Team Fragility | Measure of a team's dependency on a small number of individuals (0–100) |
| Pareto Frontier | Set of optimal budget vs. impact trade-off points; shown in multi-objective optimization |
| SHAP | SHapley Additive exPlanations — technique for explaining ML prediction contributions |
| Medallion | Bronze (raw) → Silver (clean) → Gold (aggregated) data layer pattern |

---

*EIBO — Employee Impact & Budget Optimizer · OPB AI Mastery Lab*
