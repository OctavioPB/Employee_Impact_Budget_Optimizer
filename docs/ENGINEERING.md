# Engineering

How the codebase is organized, how it is tested and shipped, and the engineering decisions behind it. For the component view see [Architecture](ARCHITECTURE.md). For the models see [Applied AI](APPLIED_AI.md).

---

## 1. Codebase at a glance

| Area | Size | Notes |
|---|---|---|
| Python | ~23,500 lines | API, services, analytics library, enterprise modules, tests |
| TypeScript / React | ~14,600 lines | 19 pages, 2 shared components, typed API client |
| API surface | 19 routers | Internal `/api/*` and public `/api/v1/*` |
| Tests | 707 collected | 530 unit · 121 security · 36 integration · 20 performance |
| Coverage | ~58% line+branch | CI floor 55% (`pyproject.toml`) |

```
backend/            FastAPI app: routers (HTTP) → services (logic) → schemas (shared types)
models/             impact scoring, attrition prediction, network analysis, early warning
optimization_engine/ ILP solver, constraints, Pareto frontier, sensitivity analysis
forecasting/        Prophet budget forecaster, Monte Carlo simulator
strategic_planner/  future state, skills gap, transition planner, strategy comparator
demo_data/          deterministic synthetic organization generator (3 scenarios × 3 sizes)
data_pipeline/      Bronze / Silver / Gold ingestion, validators, PostgreSQL schema
auth/ audit/ notifications/ workflows/ integration_hub/ health/ utils/
frontend/           React 18 + TypeScript + Vite SPA
sdk/                Python and JavaScript API clients
tests/              unit / integration / security / performance
```

---

## 2. Backend conventions

**Thin routers, pure services.**
- Routers validate input and map exceptions to status codes: `ValueError` → 400, `KeyError` → 404, validation errors → 422.
- Services take plain arguments and return JSON-ready dicts, so they can be unit-tested without HTTP.

**Shared validation types.** `backend/schemas/common.py` defines `ScenarioId` and `OrgSize`. Every endpoint that takes a scenario or org size uses them, so a bad value returns 422 instead of reaching a service and failing with 500.

**Determinism.** Every random draw uses a seeded `numpy.random.default_rng`. Given the same scenario and size, every endpoint returns byte-identical output. This made the performance refactors in §5 verifiable by diffing JSON before and after.

**Lazy heavy imports.** Prophet, SHAP and httpx are imported inside the functions that need them. If an optional dependency is missing, only the feature that needs it falls back.

---

## 3. Frontend conventions

- **Typed client.** All HTTP calls go through `services/api.ts`, which declares a TypeScript interface for every response shape.
- **Code splitting.** `App.tsx` loads every page with `React.lazy` inside a `Suspense` boundary. The initial bundle dropped from 607 kB to 243 kB.
- **Design tokens.**
  - Colors, radii and shadows are CSS custom properties in `styles/tokens.css`, with a dark theme under `html[data-theme="dark"]`.
  - Translucent tints use `rgba(var(--ink-rgb), α)`, so the same component reads correctly in both themes.
- **No chart library.** Charts are hand-written SVG, so there are no extra dependencies and the styling stays under the design system's control.
- **Type safety gate.** `npm run type-check` (`tsc --noEmit`) runs in CI, and the production build runs `tsc` before `vite build`.

---

## 4. Continuous integration

`.github/workflows/ci.yml` runs on every push to `master`, every pull request, and on demand:

| Job | Checks |
|---|---|
| **Lint** | `ruff check` (pinned to 0.9.10; rule sets E, W, F, I, UP, B, C4, RUF) |
| **Tests** | Full `pytest tests/` on Python 3.11 and 3.12, coverage floor 55%, coverage report uploaded as an artifact |
| **Frontend** | `npm ci`, `npm run type-check`, `npm run build` on Node 20 |
| **Security** | `bandit` (medium+ severity), `pip-audit` on `requirements.txt`, `npm audit` (high+) |
| **Docker build** | Builds the backend and frontend images with layer caching; runs only after lint, tests and frontend pass |

Dependency updates come from **Dependabot** (`.github/dependabot.yml`):
- weekly grouped minor and patch updates for pip and npm
- monthly updates for GitHub Actions
- npm major versions and PuLP 4 are ignored, because they need code migrations
- pip floors are only raised when the current range stops allowing the latest version

### Running locally

```bash
pip install -r requirements-dev.txt
ruff check .
pytest tests/                       # full suite with coverage
bandit -r . -x ./tests,./frontend,./sdk,./htmlcov -ll

cd frontend
npm ci
npm run type-check
npm run build
```

---

## 5. Performance work

The service layer was profiled with `cProfile` against the 5,000-employee organization. Most hot spots had the same cause: a pandas filter over the full DataFrame executed once per row inside `iterrows()` loops, which makes the work O(n²).

| Endpoint (large org) | Before | After | Change |
|---|---|---|---|
| `/api/resilience` | 27 s | 1.3 s | Leader succession counts precomputed with one `groupby`; cascade pressure aggregated per department instead of per departed employee |
| `/api/ohi` | 12 s | 0.4 s | Same succession-count fix in the leadership-pipeline sub-index |
| `/api/narrative` (repeat requests) | 4 s | 0.01 s | Ollama availability cached for 30 s; LLM call skipped when Ollama is down |
| `/api/mobility` | 500 error | 6 s | Fixed a `dict(groupby)` call that raised `TypeError` |
| Frontend initial bundle | 607 kB | 243 kB | Per-page code splitting |
| Betweenness centrality (5,000 nodes) | 264 s | 9 s | Sampled with 200 seeded pivots above 1,000 nodes (Spearman 0.91 vs exact on the 500-node org at 100 pivots) |
| Impact skill features (5,000 employees) | 11.5 s | 0.16 s | Hoisted an employee count out of a per-employee loop and vectorized with `groupby`; output bit-identical |

Each change was verified by serializing the full output for every scenario and size before and after; the outputs were identical.

---

## 6. Security engineering

- **Input.** Pydantic validation on every body and query parameter, plus sanitizers in `utils/sanitization.py` that reject NaN and ∞.
- **Secrets.**
  - API keys are stored only as SHA-256 hashes and compared in constant time.
  - Webhook payloads are signed with HMAC-SHA256.
  - `utils/secrets_validator.py` rejects placeholder secrets at startup.
- **SSRF.** Webhook URLs must be http(s) and resolve to public addresses, and redirects are not followed. Set `EIBO_ALLOW_PRIVATE_WEBHOOKS=1` for local development.
- **Build hygiene.**
  - `.dockerignore` keeps `.env`, `.git` and `node_modules` out of images.
  - `node_modules` and coverage artifacts are not tracked in git.
- **Regression tests.** `tests/security/` covers RBAC boundaries, injection patterns, secret validation and the hardening fixes above.

**Open item.** The admin, API-key and webhook management endpoints are unauthenticated. `auth/rbac.py` implements a six-tier model (Viewer → Admin), but it is not yet enforced at the HTTP layer.

---

## 7. Testing strategy

| Suite | What it proves |
|---|---|
| `tests/unit/` | Each analytics module in isolation: generator invariants, scorer bounds, ILP feasibility and constraint satisfaction, forecaster output shape, RBAC rules, notifications |
| `tests/integration/` | End-to-end pipeline: generate → score → optimize → forecast on all scenarios |
| `tests/security/` | Permission boundaries, sanitization, secrets validation, backend hardening (SSRF, input bounds, bounded L&D metrics) |
| `tests/performance/` | Wall-clock budgets on the small org (generation, centrality, scoring and attrition ≤ 5 s; ILP solve ≤ 10 s) |

None of the suites need external services; they all run on generated data. That is why the full suite runs in CI in about 2 minutes.

**Coverage gaps.**
- Most `backend/services/` modules are exercised only through smoke tests.
- `optimization_engine/multi_objective.py` and `optimization_engine/sensitivity.py` have no direct tests.

---

## 8. Local development

```bash
# Backend (http://localhost:8000, OpenAPI at /docs)
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000

# Frontend (http://localhost:3000, proxies /api to :8000)
cd frontend && npm ci && npm run dev

# Everything in containers
docker compose up --build
```

Optional: run `ollama serve` with a Mistral model pulled to enable LLM narratives. Without it the Narrative page uses its deterministic templates.

### Regenerating the README screenshots

The screenshots in `docs/images/screenshots/` were captured with Playwright driving the installed Edge browser at 1440×900, with both servers running. Navigation is state-based (no URLs), so the script hovers each nav group and clicks the page button, then waits for network idle before capturing. The images are quantized to a 256-color palette (about 0.7 MB for all 19).
