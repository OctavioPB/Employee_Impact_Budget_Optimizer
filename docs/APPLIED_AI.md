# Applied AI

EIBO combines machine learning, graph analytics, mathematical optimization, statistics and a local LLM. This document explains each technique: what it does in the product, how it is implemented, and what its limits are.

It distinguishes two things on purpose:

- **Library implementation:** the full method, in `models/`, `optimization_engine/` or `forecasting/`, with unit tests.
- **Live in the web app:** what the API in `backend/services/` actually computes when a page loads.

Where these differ, the difference is stated.

---

## Overview

| Capability | Technique | Library | Live in web app |
|---|---|---|---|
| Impact score | Weighted 4-component model; optional Random Forest | `models/impact_scorer.py` | Yes, 4-component model via `backend/services/scoring.py` |
| Attrition risk | Weighted heuristic; XGBoost + SMOTE + calibration + SHAP when labels exist | `models/attrition_predictor.py` | Inverse salary-rank heuristic |
| Collaboration network | Centrality, community detection, Gini fragility | `models/network_analysis.py` | Centrality feeds impact scores; nexus flag still comes from the generator |
| Budget optimization | Integer Linear Programming (CBC) | `optimization_engine/` | Yes: budget, overrides, leadership and critical-skill coverage |
| Forecasting | Prophet with linear fallback; Monte Carlo | `forecasting/` | Yes |
| Engagement anomalies | IsolationForest + CUSUM | (in service) | Yes |
| Pay equity | OLS residual gap | (in service) | Yes |
| Fairness audit | EEOC 4/5ths rule + chi-square | (in service) | Yes |
| Resilience | Multi-round cascade simulation | (in service) | Yes |
| L&D allocation | ILP + Pareto sweep | (in service) | Yes |
| Narratives | Local LLM (Ollama) with template fallback | (in service) | Yes |

---

## 1. Impact scoring

**Purpose.** Give every employee a 0–100 score of organizational contribution that goes beyond salary or a performance rating.

**Library model** (`models/impact_scorer.py`):

```
impact = 100 × (0.40·KPI + 0.30·network + 0.20·skills + 0.10·cost)
```

Each component is min-max normalized to [0, 1]:

- **KPI:** quarterly KPI history with a trend term.
- **Network:** combined centrality from the collaboration graph.
- **Skills:** criticality and uniqueness of held skills.
- **Cost:** replacement cost proxy.

With historical retention labels, an optional **Random Forest** mode predicts P(retained) and scales it to 0–100. Its per-feature attribution is an importance-weighted approximation, not true SHAP values.

**Live in the web app.** Every page and the public v1 API get impact from `backend/services/scoring.py`. It builds the org's collaboration graph, computes centrality, runs the library model's heuristic mode once per org, and caches the result. Every surface therefore reports the same score for the same employee.

It replaced a per-service shortcut, `70·salary_percentile + 15·is_nexus + noise`, which made impact a near-copy of pay (Spearman 0.99 with salary). With the 4-component model that correlation is about 0.7, and what remains comes from KPI, network position and skills rising with seniority in the synthetic data.

Consequences worth knowing:

- **Compressed scale.** Scores cluster between about 25 and 75, not 0–100. The UI therefore colors impact relative to the org (top 20% green, above median gold), and the simulation's impact chart uses org quintiles instead of fixed brackets.
- **Cost of the first load.** Centrality on the 5,000-employee org takes about 15 s, including sampled betweenness. The first request for that org takes about 30 s in total; after that the scores are cached.
- **ILP behavior.** Summing raw scores from such a compressed scale made plans favor headcount: at 80% of spend on the small Scenario A org, only 5 of the 10 top-quintile employees were kept. The web simulation therefore optimizes rank-weighted impact with a per-person cost (see [§4](#4-budget-optimization-ilp)).

---

## 2. Attrition risk

**Purpose.** Estimate each employee's probability of voluntary departure, framed as a retention opportunity.

**Library model** (`models/attrition_predictor.py`):

- **Heuristic mode** (default, no labels needed). It weights five factors:

  | Factor | Weight | Risk is higher when |
  |---|---|---|
  | Compensation position | 0.25 | pay is below peers |
  | KPI trend | 0.25 | performance is declining |
  | Impact | 0.20 | impact is lower |
  | Tenure | 0.15 | tenure is very short or very long |
  | Network centrality | 0.15 | the employee is isolated |

- **XGBoost mode** (≥ 20 labeled records):
  - **SMOTE** for class imbalance, because departures are rare.
  - **CalibratedClassifierCV** (Platt scaling), so a score of 70 means roughly a 70% observed rate.
  - Stratified cross-validation.
  - **SHAP TreeExplainer** for per-employee drivers.

- **Risk bands:** Low (0–30), Moderate (31–60), High (61–80), Critical (81–100).

**Live in the web app.** `attrition = clip(0.6·(1 − salary_percentile) + U(0, 0.4) − 0.15·is_nexus, 0.01, 0.99)`. The Predictive page shows a "top driver" text per employee, but it is not a computed SHAP attribution.

---

## 3. Collaboration network analysis

**Purpose.** Find people whose departure would fragment how work flows. These are structural risks that payroll and performance data cannot show.

**Implementation** (`models/network_analysis.py`, NetworkX):

- **Centrality.** Four normalized measures combined into one score: degree, betweenness, eigenvector and PageRank.
- **Nexus employees.** Betweenness ≥ 0.70, or combined centrality above the 85th percentile.
- **Communities.**
  - Graphs under 1,000 nodes use greedy modularity.
  - Larger graphs use label propagation, which runs in O(n + m).
- **Team fragility.** The Gini coefficient of centrality within a team. A high value means the team depends on a few people.

**Live in the web app.** The synthetic generator marks nexus employees directly (`_is_nexus`), and services consume that flag.

---

## 4. Budget optimization (ILP)

**Purpose.** Given a budget, find the set of retained employees that maximizes total impact while keeping the organization functional. This is the core "structure optimization" question.

**Formulation** (`optimization_engine/ilp_solver.py`, PuLP + CBC):

```
maximize    Σ impact_i · x_i
subject to  Σ cost_i · x_i ≤ budget                       (budget)
            Σ_{i ∈ leaders(t)} x_i ≥ 1      ∀ team t       (leadership)
            Σ_{i ∈ holders(s)} x_i ≥ 1 + d  ∀ skill s      (critical skills, succession depth d)
            Σ_{i ∈ team(t)} x_i ≥ m         ∀ team t       (optional minimum team size)
            x_i = 1 for force-retained, x_i = 0 for excluded (human overrides)
            x_i ∈ {0, 1}
```

Two companion modules sweep the same model:

- **`multi_objective.py`** solves at 15 budget fractions (50–120%) to trace the **Pareto frontier** of cost vs impact.
- **`sensitivity.py`** re-solves at ±5, ±10 and ±20% around a base budget.

**Why ILP rather than ranking.** Sorting by impact per dollar ignores constraints: it can leave a team with no leader or a critical skill with no holder. An ILP finds a provably optimal answer that respects every constraint, or proves that none exists.

**Live in the web app.** The Simulation page uses a different objective from the library:

```
maximize    Σ (pct_i − λ) · x_i
```

- **pct_i** is the employee's impact percentile within the org (0–100). Impact scores cluster in a narrow band, so summing raw scores rewarded headcount. Percentiles spread people evenly, so a top-quintile employee is worth clearly more than a median one.
- **λ (headcount cost)** is a fixed charge per person kept, in percentile points. The default is 10 and the page offers a slider from 0 to 50.
  - Anyone ranked below λ subtracts from the objective. They are kept only when a coverage constraint or a force-retain override requires it, even if budget remains.
  - When that leaves budget unused, the page says so.
  - λ = 0 makes headcount free.
- **Effect.** At 80% of spend on the small Scenario A org the plan keeps all 10 top-quintile employees (5 of 10 under the raw-sum objective), and the mean percentile of the people kept rises from about 50 to 71.
- **Reporting.** `total_impact` in the response is still the sum of raw impact scores, the business-facing number.

It also applies:
- the budget constraint, force-retain and exclude overrides, and two optional coverage constraints, with an 8 s time limit:
  - **Leadership coverage:** every team that has an available leader (lead, director or exec) keeps at least one.
  - **Critical skills coverage:** every critical skill that has an available holder keeps at least one.
- The response reports coverage for both constraints whether or not they are enforced, so the page can show what a plan gives up. At the default 80% of spend on the small Scenario A org, turning them off leaves one of the 3 teams without a leader, because leaders are expensive and impact no longer tracks pay. Turning leadership coverage on changes 3 people and costs about 1.1% of the objective.
- If the budget is infeasible, the service re-solves with each constraint dropped to name the one that conflicts.
- If PuLP is unavailable, a greedy fallback first covers every required group with its cheapest member, then fills the rest by net value (pct − λ) per dollar and stops at the first person ranked below λ.
- Not yet in the web app: succession depth and minimum team size, which the library supports.

The L&D optimizer reuses the same ILP pattern. It uses binary variables `y_{i,t}` that assign employee *i* to training program *t* under an L&D budget and a per-employee program cap. A Pareto sweep across budgets shows diminishing returns.

---

## 5. Forecasting

**Budget forecast** (`forecasting/budget_forecaster.py`):

- **Prophet** with annual and quarterly seasonality produces 12-month spend and headcount forecasts per department, with 80% and 95% intervals.
- If Prophet is not installed, a linear extrapolation takes over, so the page always renders.

**Monte Carlo stress test** (`forecasting/monte_carlo.py`):

- Simulates 2,000 budget trajectories over 12 months.
- Samples three things per trajectory:
  - **Attrition:** monthly departure probability per employee.
  - **Salary inflation:** annual shocks, correlated across employees.
  - **Hiring costs:** replacement cost overruns, triggered when someone departs.
- Returns P10/P50/P90 fan-chart bands and the probability of exceeding the budget in each month.

Both are live in the web app.

---

## 6. Engagement anomaly detection (Pulse)

**Purpose.** Spot early behavioral changes using **metadata only**, never message content. The page is labeled as demo data, and the text states that production use needs employee consent.

**Implementation** (`backend/services/pulse_service.py`):

- **Six signals** per employee over 90 days:
  - meeting density
  - cross-team reach
  - response-latency trend
  - PTO utilization
  - after-hours ratio
  - network-size delta
- **IsolationForest** (scikit-learn, contamination 10%) scores multivariate outliers across the six signals.
- **CUSUM** control charts flag sustained drift against a 70-day baseline (k = 0.5σ, h = 3σ), checking the direction that indicates risk for each signal.

**Known limitation.** The synthetic signals are generated as a cumulative random walk, which is not stationary. CUSUM assumes a stable in-control process, so on this data it flags every employee: "CUSUM alerts: 50 of 50". The synthetic generator and thresholds need recalibration before this metric is meaningful. See [Lessons Learned](LESSONS_LEARNED.md).

---

## 7. Pay equity and fairness

**Pay equity** (`compensation_service.py`):

- **Raw gap:** compares group means directly.
- **OLS-adjusted gap:** regresses salary on seniority rank and compares groups on the residuals. This separates gaps explained by legitimate factors from unexplained ones.
- **Comp-ratio:** salary relative to the cohort median.

**Fairness audit** (`fairness_service.py`):

- **EEOC 4/5ths rule.** A group's selection rate under 80% of the highest group's rate indicates adverse impact.
- **Chi-square test.** Checks whether the disparity is statistically significant rather than noise from small samples.
- **Synthetic groups.** Protected groups are synthetic proxies; no real demographic data is used or inferred.
- **Counterfactual test.** Flips a protected attribute and recomputes scores. Because the scores never take protected attributes as input, Δ is exactly 0 by construction. This shows the scoring pipeline has no direct dependency on those attributes, but it does not detect proxy bias, such as salary correlating with a group.

---

## 8. Resilience stress testing

**Cascade simulation** (`resilience_service.py`):

1. Remove a set of employees.
2. Apply pressure to everyone who remains:

   | Departure | Pressure on |
   |---|---|
   | Nexus employee | +0.28 on the same department |
   | Leader | +0.22 on more junior colleagues in the same department |
   | Any departure | a small amount scaled by the departed person's impact |

3. Anyone whose `attrition_risk + pressure > 0.75` departs in the next round.
4. Repeat for up to 3 rounds.

"Amplifiers" are the employees whose solo departure triggers the most secondary departures. The resilience score combines six sub-scores:

- skill coverage
- leadership depth
- knowledge redundancy
- network robustness
- attrition distribution
- team-size buffer

---

## 9. Organizational Health Index

A composite of six weighted sub-indices:

| Sub-index | Weight |
|---|---|
| Financial health | 20% |
| Talent risk | 20% |
| Knowledge resilience | 20% |
| Leadership pipeline | 15% |
| Compensation equity | 15% |
| Collaboration density | 10% |

On top of the composite, the page shows a 24-month trend, a department breakdown, synthetic benchmarks and a "decision preview". The decision preview recomputes OHI for a retention scenario before anyone acts on it.

---

## 10. Decision narratives (local LLM)

**Purpose.** Turn scores into plain-language explanations a manager can use in a conversation.

**Implementation** (`narrative_service.py`):

- **Model and runtime.** Ollama runs locally (default `mistral:7b-instruct-q4_K_M`) with a 30 s timeout.
- **Zero PII.** Names are replaced with `role-anonID` before any prompt; salaries are not sent.
- **Deterministic templates.** Each of the four narrative types (impact, attrition, simulation summary, manager brief) has a template. It is used whenever Ollama is unavailable or fails, so the page never depends on the model.
- **Caching.**
  - Generated narratives are cached per type, employee and day.
  - Ollama's availability is cached for 30 s, so a down model does not add seconds to every request.
- **Disclosure.** Every output carries a disclaimer and the model or template that produced it.

---

## Responsible-AI principles applied

- **Human in the loop.** Every optimization accepts force-retain and exclude overrides. The UI language says "suggested retention" and "not retained in simulation", never verdicts.
- **Explainability.**
  - The library uses SHAP where a tree model is trained.
  - Heuristic scores are simple, documented formulas.
- **Privacy.**
  - No employee data leaves the deployment.
  - Behavioral signals are metadata only.
  - The LLM is local and receives anonymized input.
- **Honest uncertainty.** Forecasts are shown as bands, never point estimates.
- **Bias checks before action.** The fairness audit runs on simulation outcomes, not only on raw data.

See [Business Value](BUSINESS_VALUE.md) for how these map to decisions, and [Lessons Learned](LESSONS_LEARNED.md) for where the implementation falls short of these principles today.
