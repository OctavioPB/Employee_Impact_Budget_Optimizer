# Lessons Learned

EIBO was built in 20 feature sprints. A later audit, the CI rollout and capturing the screenshots for the documentation all surfaced problems that the feature work had not. This document records each problem, why it happened, how it was handled, and what we would do differently. Items marked **Open** are not fixed yet.

---

## 1. Two analytics tiers drifted apart

**What happened.**
- The analytics library (`models/`, `optimization_engine/`) implements the methods the project describes: a four-component impact score, XGBoost attrition with SMOTE, calibration and SHAP, and a constrained ILP with leadership and critical-skill coverage.
- The web API was built later, sprint by sprint, and each new service needed scores quickly. Instead of calling the library, services computed a heuristic: impact from salary percentile plus a nexus bonus, and attrition from inverse salary percentile. That heuristic ended up copied into five services and the public v1 API.
- The Simulation page showed "Leadership coverage" and "Critical skills coverage" toggles. The API accepted both flags and ignored them.

**Why it matters.** The documentation and the UI promised behavior the running application did not deliver. Tests passed because the library was tested and the services were only smoke-tested.

**Lesson.** A capability is not done until the user-facing path uses it. Every UI control should have a test proving it changes the output. Shared logic should live in one importable function before the second copy appears.

**Status.**
- **Simulation toggles: Fixed.**
  - Both constraints are now part of the web ILP, and the greedy fallback honors them too.
  - The response reports coverage (for example "3/3 teams keep a leader"), and the page shows it, so the effect is visible even when the optimal plan already satisfies the constraint.
  - An infeasible budget names the conflicting constraint.
  - `tests/unit/test_simulation_constraints.py` proves each toggle changes the plan when the budget is tight.
- **Impact scoring: Fixed.**
  - The eight copies of the heuristic (six services, the dashboard and the v1 API) now use one module, `backend/services/scoring.py`, which runs the library's 4-component model once per org.
  - Impact's rank correlation with salary dropped from 0.99 to about 0.7.
  - A test asserts that every surface reports the same score for the same employee.
  - Wiring the library in exposed two O(n²) costs in the library itself, both fixed:
    - exact betweenness centrality (~4.5 min on 5,000 nodes), now sampled above 1,000 nodes;
    - a skill-feature loop that recounted all employees on every iteration (11 s, now 0.16 s, bit-identical output).
- **Attrition risk: Open.** It is still the inverse-salary heuristic. It was deliberately left unchanged, with the same random draws, so this change only moved impact.
- **Optimizer objective: Fixed.** Maximizing the *sum* of a compressed 25–75 score rewarded headcount over impact: at 80% of spend on the small Scenario A org, only 5 of 10 top-quintile employees were kept.
  - The web ILP now maximizes Σ (impact percentile − λ) with a per-person headcount cost λ (default 10, adjustable on the page). It keeps 10 of 10.
  - `tests/unit/test_simulation_objective.py` covers top-quintile retention, monotonic headcount as λ rises, overrides beating λ, and API validation.
  - Lesson: when an objective sums a score, check the score's spread. A narrow band turns "maximize value" into "maximize count".
- **Simulation page race condition: Fixed.** Moving the budget slider scheduled an auto-run with the settings captured at that moment. Changing another control and clicking Run within 500 ms let the stale run land last and overwrite the result.
  - The timer now calls the latest function through a ref.
  - Run cancels any pending timer.
  - Only the newest response is applied.
  - It surfaced while browser-testing the new headcount-cost slider: the API returned the right plan, but the page showed the old one.

---

## 2. Synthetic data must be checked against the statistics run on it

**What happened.** Screenshots showed two numbers that cannot be right:
- **"CUSUM alerts: 50" out of 50 employees** on the Pulse page. The generator builds signals as a cumulative random walk, which is not stationary. CUSUM assumes a stable in-control process, so against a 70-day baseline every series looks like drift.
- **"Attrition reduction: 1049.4%"** on the L&D page. The service summed per-assignment risk reductions across about 100 training assignments instead of averaging per employee.

**Lesson.** Synthetic data needs its own tests. Assert that the statistical properties a downstream method assumes actually hold, and that headline metrics stay within physical bounds (a rate in [0, 1], alert counts below headcount). Looking at real rendered pages catches errors that a test suite checking response shapes never will.

**Status.**
- **L&D: Fixed.** The metric is now the average risk drop per trained employee, capped at each person's current risk, with a regression test.
- **Pulse CUSUM: Open.** The generator needs mean-reverting noise and recalibrated thresholds.

---

## 3. O(n²) pandas loops hide until the largest dataset

**What happened.**
- The OHI and Resilience pages took 12 s and 27 s on the 5,000-employee org but were instant on the 50-employee one.
- Profiling showed the same pattern in several services: inside an `iterrows()` loop, each row filtered the full DataFrame and re-mapped a column.
- One cascade simulation updated the whole frame once per departed employee, five times per page load.

**Fix.** Precompute group sizes once with `groupby`, aggregate departures per department, and convert hot columns to NumPy arrays. That brought Resilience to 1.3 s and OHI to 0.4 s. Because every service is deterministic, the full JSON output for every scenario and size could be diffed before and after, and it was identical.

**Lesson.** Run performance checks on the largest supported dataset, not the default one. Make outputs deterministic so refactors can be verified by diffing, not by eyeballing.

**Still slow (Open):**
- Mobility at 6 s
- Monte Carlo at 3.5 s
- the first request for the large org, about 30 s (generation plus impact scoring); cached afterwards

---

## 4. Upper bounds matter as much as lower bounds

**What happened.** `requirements.txt` used open ranges (`pulp>=2.7.0`). PuLP 4.0 requires Python ≥ 3.12, removed the bundled CBC solver and `PULP_CBC_CMD`, and changed the modeling API. Two different installs resulted from the same file:
- On Python 3.11, pip still resolved PuLP 3.x, so CI passed.
- On Python 3.12, pip resolved 4.x, so collection failed with `ImportError`.

Dependabot then opened PRs that raised floors (for example `numpy>=2.5.5` and `networkx>=3.7`) to versions that also require Python 3.12, which broke the 3.11 job.

**Fix.**
- Pin `pulp<4`.
- Set Dependabot to `increase-if-necessary`, so floors only move when they have to.
- Ignore major versions that need code migrations.

**Lesson.** Test on every Python version you claim to support. A range without an upper bound is a bet that no future major release will break you; for libraries with a history of API changes, cap the major version.

---

## 5. Design tokens need a visual check in both themes

**What happened.** The L&D, OHI and Narrative pages were written for a dark background:
- white-alpha text (`rgba(255,255,255,…)`);
- two tokens, `--surface` and `--radius`, that were never defined;
- `var(--light)` used as a text color.

The app's default theme is light, so these pages rendered nearly blank text on a light background. Type checks, builds and API tests all passed. The problem was only visible in a browser.

**Fix.**
- Added a theme-aware `--ink-rgb` token and used `rgba(var(--ink-rgb), α)` for tints.
- Defined the missing tokens.
- Switched SVG strokes to `currentColor`, because presentation attributes cannot resolve `var()`.

The pages now read correctly in both themes.

**Lesson.** Unknown CSS custom properties fail silently. A screenshot pass across every page in both themes catches this class of bug cheaply. That same pass also caught the L&D metric bug in §2.

**Still open:** the dashboard's chart labels are hard to read in dark mode.

---

## 6. Repository and build hygiene

**What happened.**
- `frontend/node_modules` (about 2,500 files) and `coverage.xml` were committed.
- There was no `.dockerignore`, so `docker build` copied `.env`, `.git` and `node_modules` into the backend image.
- `httpx` was used by the webhook service but missing from `requirements.txt`. The Dockerfile installed some packages a second time to compensate.

**Fix.**
- Untracked the generated files and ignored them.
- Added root and frontend `.dockerignore` files.
- Declared `httpx` and made `requirements.txt` the single source of dependencies.

**Lesson.** Set up `.gitignore` and `.dockerignore` on day one. Never compensate for a missing dependency in the Dockerfile; fix the requirements file.

---

## 7. Secure defaults are easy to skip in demo code

**What happened.** The audit found:
- **SSRF.** The webhook service accepted any URL, including `file://` and cloud metadata addresses.
- **Unauthenticated management endpoints.** API-key and webhook management have no authentication.
- **Unvalidated input.** The public API's `limit` parameter accepted negative values.
- **Unvalidated environment input.** The LLM base URL from the environment was opened without a scheme check.

The RBAC module exists and is tested, but it is not enforced at the HTTP layer.

**Fix.**
- Webhook URLs must be http(s), resolve to public addresses, and redirects are not followed.
- Every scenario and size parameter is validated.
- API-key lookup is constant-time.
- CI now runs bandit, pip-audit and npm audit, so regressions are caught automatically.

**Lesson.** "It's only a demo" code becomes production code. Write HTTP handlers secure by default from the first commit, and let CI enforce it.

**Status:** authentication on management endpoints is **Open**.

---

## 8. Tests that pass without proving much

**What happened.**
- **Coverage floor.** The CI floor was 40% and applied to unit tests only. The full suite reaches about 58%, and that is now the gate, with a 55% floor.
- **Untested services.** Most `backend/services/` modules had no direct tests, which is how the `/api/mobility` crash (a `dict(groupby)` call raising `TypeError`) shipped.
- **Tautological check.** The fairness module's counterfactual test always returns Δ = 0, because the scores never take protected attributes as input. It cannot detect proxy bias, for example salary correlating with group membership, which is the more realistic risk.

**Lesson.** Measure coverage on the code that serves users, and add one smoke test per endpoint at minimum. For fairness, test outcomes across groups (which the 4/5ths check does) rather than only model inputs.

---

## 9. Documentation drifted from the code

**What happened.**
- The README stated "734 tests" while there were 707.
- It described SHAP explanations and constraint-aware simulation as live, and linked to design documents in `planning/`, a folder that is git-ignored and so is not visible to anyone browsing the repository.
- The internal development guide still describes a Streamlit UI that was replaced by React in Sprint 10.

**Fix.** This documentation set was written against the code, and states where the library and the live application differ. The README now links here.

**Lesson.** Documentation that is not checked against the code goes stale. Prefer statements that can be verified (file paths, test names) over feature lists, and review docs whenever behavior changes.

---

## What we would do differently

1. **One analytics path.** The API calls the library from day one; the heuristics exist only as an explicit, tested fallback.
2. **Contract tests per endpoint** that check value ranges and units, not just response shape.
3. **A screenshot regression job** in CI across every page in both themes.
4. **Performance budgets on the largest dataset**, enforced in CI.
5. **Auth before features.** Enforce RBAC on every route before adding capabilities that expose data.
6. **Version caps and a multi-version CI matrix** from the first dependency.
