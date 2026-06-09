"""Local LLM-Powered Decision Narrative Engine — Sprint 17.

Implements:
  - LLM service wrapper: Ollama (mistral:7b-instruct) with 30s hard timeout
    and deterministic template-based fallback when Ollama is unavailable
  - SHAP-style impact score explanation (pseudo-SHAP from heuristic model)
  - Attrition risk explanation with risk driver breakdown
  - 3-paragraph simulation outcome summary
  - Manager retention conversation brief (PII-stripped prompts)
  - Zero PII to LLM: names replaced with [role]-[anonymized_id] in all prompts
"""

import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import numpy as np
import pandas as pd

from backend.services.data_service import get_org

# ── Ollama config ─────────────────────────────────────────────────────────────

OLLAMA_BASE  = os.getenv("OLLAMA_URL",   "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral:7b-instruct-q4_K_M")
LLM_TIMEOUT  = int(os.getenv("LLM_TIMEOUT_SEC", "30"))

# In-memory narrative cache: hash → (text, is_llm, ts)
_CACHE: dict[str, tuple[str, bool, str]] = {}


# ── Ollama I/O ────────────────────────────────────────────────────────────────

def check_ollama() -> dict:
    """Return Ollama availability status dict."""
    try:
        req = urllib.request.Request(f"{OLLAMA_BASE}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=2) as r:
            body = json.loads(r.read())
            models = [m["name"] for m in body.get("models", [])]
            return {"available": True, "model": OLLAMA_MODEL,
                    "base_url": OLLAMA_BASE, "loaded_models": models}
    except Exception:
        return {"available": False, "model": OLLAMA_MODEL,
                "base_url": OLLAMA_BASE, "loaded_models": []}


def _call_ollama(prompt: str, max_tokens: int = 350, temperature: float = 0.25) -> str | None:
    """POST to Ollama generate endpoint. Returns text or None on any failure."""
    # Wrap in Mistral instruct format
    wrapped = f"[INST] {prompt} [/INST]"
    payload = json.dumps({
        "model":   OLLAMA_MODEL,
        "prompt":  wrapped,
        "stream":  False,
        "options": {"num_predict": max_tokens, "temperature": temperature},
    }).encode()
    try:
        req = urllib.request.Request(
            f"{OLLAMA_BASE}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=LLM_TIMEOUT) as r:
            body = json.loads(r.read())
            return (body.get("response") or "").strip() or None
    except Exception:
        return None


def _cache_key(narrative_type: str, employee_id: str | None) -> str:
    raw = f"{narrative_type}:{employee_id or 'org'}:{date.today().isoformat()}"
    return hashlib.md5(raw.encode()).hexdigest()


# ── Score helpers (same seed as resilience / ld services) ─────────────────────

def _add_scores(df: pd.DataFrame) -> pd.DataFrame:
    rng      = np.random.default_rng(42)
    sal_rank = df["annual_salary"].rank(pct=True)
    nexus_b  = df["_is_nexus"].astype(float) * 15
    noise    = rng.normal(0, 5, len(df))
    df       = df.copy()
    df["impact_score"] = np.clip(sal_rank * 70 + nexus_b + noise, 0, 100).round(1)

    sal_inv  = 1 - sal_rank
    nexus_r  = df["_is_nexus"].astype(float) * 0.15
    attr_raw = sal_inv * 0.6 + rng.uniform(0, 0.4, len(df)) - nexus_r
    df["attrition_risk"] = np.clip(attr_raw, 0.01, 0.99).round(3)
    return df


# ── PII stripping ─────────────────────────────────────────────────────────────

def _anon_id(employee_id: str) -> str:
    return hashlib.md5(employee_id.encode()).hexdigest()[:5].upper()


def _anon_label(role: str, employee_id: str) -> str:
    return f"[{role}]-[{_anon_id(employee_id)}]"


# ── Pseudo-SHAP driver computation ────────────────────────────────────────────

def _impact_drivers(row: pd.Series, df: pd.DataFrame) -> list[dict]:
    sal_pct   = int(df["annual_salary"].rank(pct=True)[row.name] * 100)
    dept_pct  = int(
        df[df["department"] == row["department"]]["annual_salary"]
        .rank(pct=True).reindex(df.index).get(row.name, 0.5) * 100
    )
    nexus_flag = bool(row.get("_is_nexus", False))
    sen        = str(row.get("seniority_level", "mid")).lower()
    sen_contrib = {"junior": 10, "mid": 18, "senior": 28, "lead": 35, "director": 40, "exec": 45}

    return [
        {
            "factor":       "Salary percentile within organization",
            "value":        f"{sal_pct}th percentile",
            "contribution": round(sal_pct * 0.50, 1),
            "direction":    "positive",
        },
        {
            "factor":       "Seniority and experience tier",
            "value":        sen.capitalize(),
            "contribution": float(sen_contrib.get(sen, 20)),
            "direction":    "positive",
        },
        {
            "factor":       "Collaboration network centrality",
            "value":        "Nexus employee — high betweenness" if nexus_flag else "Standard connectivity",
            "contribution": 15.0 if nexus_flag else 5.0,
            "direction":    "positive",
        },
        {
            "factor":       "Department salary competitiveness",
            "value":        f"{dept_pct}th percentile within {row.get('department','')}",
            "contribution": round(dept_pct * 0.15, 1),
            "direction":    "positive" if dept_pct > 50 else "neutral",
        },
    ]


def _attrition_drivers(row: pd.Series, df: pd.DataFrame) -> list[dict]:
    sal_rank  = df["annual_salary"].rank(pct=True)[row.name]
    float(row["attrition_risk"])
    nexus_flag = bool(row.get("_is_nexus", False))
    sen        = str(row.get("seniority_level", "mid")).lower()

    # Tenure proxy from hire_date
    try:
        hire = pd.to_datetime(row.get("hire_date", "2020-01-01"))
        tenure_yrs = (pd.Timestamp.now() - hire).days / 365.25
    except Exception:
        tenure_yrs = 3.0

    comp_gap = max(0.0, 0.85 - sal_rank)  # positive = below market threshold
    market_pressure = 0.3 if sen in {"lead", "director", "exec", "senior"} else 0.15

    drivers = [
        {
            "factor":       "Compensation relative to market",
            "value":        "Below market threshold" if comp_gap > 0 else "At or above market",
            "contribution": round(comp_gap * 0.6 * 100, 1),
            "direction":    "risk" if comp_gap > 0 else "protective",
        },
        {
            "factor":       "Market demand for this skill set",
            "value":        f"{'High' if market_pressure > 0.2 else 'Moderate'} external demand for {sen} {row.get('role_title','')}",
            "contribution": round(market_pressure * 100, 1),
            "direction":    "risk",
        },
        {
            "factor":       "Tenure stability",
            "value":        f"{tenure_yrs:.1f} years",
            "contribution": round(max(0, (3 - tenure_yrs) / 3 * 0.2 * 100), 1),
            "direction":    "risk" if tenure_yrs < 2 else "protective",
        },
        {
            "factor":       "Network centrality protection",
            "value":        "Nexus role provides departure deterrent" if nexus_flag else "No centrality buffer",
            "contribution": round(0.15 * 100 if nexus_flag else 0, 1),
            "direction":    "protective" if nexus_flag else "neutral",
        },
    ]

    # Sort risk factors first
    drivers.sort(key=lambda d: (0 if d["direction"] == "risk" else 1, -d["contribution"]))
    return drivers


# ── Template narratives ───────────────────────────────────────────────────────

def _tier(score: float) -> str:
    return "high" if score >= 70 else "moderate" if score >= 45 else "developing"


def _risk_label(risk: float) -> str:
    return "critical" if risk >= 0.8 else "high" if risk >= 0.6 else "moderate" if risk >= 0.4 else "low"


def _impact_template(source: dict) -> str:
    role  = source["role"]
    sen   = source["seniority"].capitalize()
    dept  = source["department"]
    score = source["impact_score"]
    nexus = source["is_nexus"]
    tier  = _tier(score)
    dept_avg = source.get("dept_avg_score", 50)
    drivers  = source.get("drivers", [])

    p1 = (
        f"This {sen} {role} in {dept} holds a {tier} organizational impact position "
        f"with a score of {score:.0f}/100"
        + (f", placing them {score - dept_avg:+.0f} points relative to the {dept} department average" if dept_avg else "")
        + ". "
    )
    if drivers:
        top = drivers[0]
        p1 += (
            f"The primary contributor is {top['factor'].lower()} "
            f"({top['value']}), accounting for approximately {top['contribution']:.0f}% of the overall assessment."
        )
    if nexus:
        p1 += (
            " This employee holds a Nexus designation — their collaboration network position "
            "amplifies their organizational impact beyond direct output."
        )

    p2_map = {
        "high":        (
            "This represents a high-retention priority. Replacing this role would carry significant "
            "knowledge transfer costs, recruitment overhead, and a measurable productivity dip during transition. "
            "Proactive retention investment — whether through compensation review, development pathways, "
            "or expanded responsibility — is recommended before any attrition risk escalates."
        ),
        "moderate":    (
            "This employee contributes meaningfully to team capacity. Their score reflects solid competency "
            "and consistent contribution. Targeted development opportunities — particularly in collaboration "
            "visibility or critical skill expansion — could meaningfully elevate their organizational impact."
        ),
        "developing":  (
            "Standard growth-stage profile. Structured mentorship and milestone-based progression "
            "will strengthen contribution over the near term. Consider pairing with higher-impact peers "
            "to accelerate knowledge acquisition and network integration."
        ),
    }
    return f"{p1}\n\n{p2_map[tier]}"


def _attrition_template(source: dict) -> str:
    role    = source["role"]
    sen     = source["seniority"].capitalize()
    dept    = source["department"]
    risk    = source["attrition_risk"]
    label   = _risk_label(risk)
    drivers = source.get("drivers", [])

    urgency = {
        "critical": "Immediate retention intervention is recommended",
        "high":     "Retention attention is warranted",
        "moderate": "This employee warrants monitoring",
        "low":      "Retention risk is within acceptable range",
    }[label]

    p1 = f"{urgency} for this {sen} {role} in {dept} (departure probability: {risk*100:.0f}%). "
    risk_drivers = [d for d in drivers if d["direction"] == "risk"]
    prot_drivers = [d for d in drivers if d["direction"] == "protective"]

    if risk_drivers:
        primary = risk_drivers[0]
        p1 += f"The leading signal is {primary['factor'].lower()} ({primary['value']})."
        if len(risk_drivers) > 1:
            secondary = risk_drivers[1]
            p1 += f" This is compounded by {secondary['factor'].lower()}."

    p2 = ""
    if prot_drivers:
        p2 = f"Protective factors include {prot_drivers[0]['factor'].lower()} ({prot_drivers[0]['value']}), "
        p2 += "which provides a buffer against immediate departure. "

    action_map = {
        "critical": (
            "An executive-level retention conversation is recommended within the next two weeks. "
            "Key levers: market-rate compensation adjustment, expanded leadership scope, or a named "
            "development pathway. Departure at this risk level is likely within the next 6 months without intervention."
        ),
        "high": (
            "A structured check-in with this employee's manager is recommended. "
            "Focus on career trajectory clarity, compensation benchmarking, and any unresolved blockers. "
            "A development investment in the near term — such as a stretch assignment or targeted training — "
            "can materially reduce departure probability."
        ),
        "moderate": (
            "Standard engagement practices apply, with quarterly check-ins recommended. "
            "Watch for compounding signals such as reduced collaboration activity, "
            "increased after-hours disengagement, or salary stagnation approaching 18 months."
        ),
        "low":      (
            "No immediate intervention required. Continue standard engagement cadence."
        ),
    }
    return f"{p1}\n\n{p2}{action_map[label]}"


def _simulation_template(source: dict) -> str:
    budget_pct     = source["budget_pct"]
    source["retained_pct"]
    impact_pct     = source["impact_preserved_pct"]
    n_retained     = source["n_retained"]
    n_total        = source["n_total"]
    dept_summary   = source.get("dept_summary", "")
    skills_note    = source.get("skills_note", "critical skill coverage maintained")
    nexus_count    = source.get("nexus_retained", 0)

    savings = round((1 - budget_pct) * 100, 1)

    p1 = (
        f"This workforce optimization strategy targets a {savings:.0f}% budget reduction, "
        f"resulting in a proposed structure of {n_retained} retained positions "
        f"from a current headcount of {n_total}. "
        f"The simulation preserves {impact_pct:.0f}% of total organizational impact score "
        f"within the adjusted budget envelope — achieving an efficient frontier between cost reduction "
        f"and talent preservation."
    )

    p2 = (
        f"The retention strategy prioritizes high-impact and network-critical roles. "
        f"{nexus_count} Nexus employees are included in the suggested retention list, "
        f"protecting the collaboration infrastructure that supports cross-team knowledge transfer. "
        f"{skills_note.capitalize()}."
        + (f" {dept_summary}" if dept_summary else "")
    )

    p3_impact_threshold = impact_pct
    if p3_impact_threshold >= 90:
        risk_note = (
            "Residual risk is low. The proposed structure retains sufficient depth across all critical functions. "
            "Implementation should be sequenced to allow knowledge transfer within teams before any transitions occur."
        )
    elif p3_impact_threshold >= 75:
        risk_note = (
            "Moderate execution risk exists in departments with below-average retention ratios. "
            "A phased transition plan is recommended, with knowledge documentation initiated 60 days before "
            "any structural changes take effect. Monitor Resilience Score quarterly post-implementation."
        )
    else:
        risk_note = (
            "This scenario carries elevated execution risk. Impact preservation falls below optimal thresholds, "
            "suggesting the budget target may be more aggressive than organizational capacity can safely absorb. "
            "Consider a phased approach or fairness constraint review before finalizing this scenario."
        )
    return f"{p1}\n\n{p2}\n\n{risk_note}"


def _manager_brief_template(source: dict) -> str:
    role    = source["role"]
    sen     = source["seniority"]
    dept    = source["department"]
    risk    = source["attrition_risk"]
    impact  = source["impact_score"]
    drivers = source.get("drivers", [])
    source.get("anon_id", "employee")

    label = _risk_label(risk)
    risk_drivers = [d for d in drivers if d["direction"] == "risk"]
    prot_drivers = [d for d in drivers if d["direction"] == "protective"]

    driver_lines = "\n".join(
        f"  • {d['factor']}: {d['value']}"
        for d in risk_drivers[:3]
    )

    protect_lines = "\n".join(
        f"  • {d['factor']}: {d['value']}"
        for d in prot_drivers[:2]
    ) or "  • No strong protective factors currently identified"

    action_by_driver = []
    for d in risk_drivers[:2]:
        factor = d["factor"].lower()
        if "compensation" in factor:
            action_by_driver.append(
                "Schedule a compensation benchmarking review. If the current salary is below "
                "market median for this role and geography, bring it to parity before the next review cycle."
            )
        elif "market demand" in factor or "skill" in factor:
            action_by_driver.append(
                "Offer a development investment: a named training pathway, a stretch assignment "
                "with expanded scope, or a clear promotion timeline milestone to anchor engagement."
            )
        elif "tenure" in factor:
            action_by_driver.append(
                "Prioritize a structured career progression conversation. "
                "Employees in the first 24 months respond strongly to explicit acknowledgement of their trajectory."
            )
        elif "network" in factor or "centrality" in factor:
            action_by_driver.append(
                "Increase visibility within the organization — cross-team project ownership "
                "or a mentorship role can deepen organizational commitment for central contributors."
            )

    if not action_by_driver:
        action_by_driver.append(
            "Conduct a structured engagement check-in focused on career clarity, "
            "team dynamics, and any unaddressed friction points."
        )

    actions = "\n".join(f"  {i+1}. {a}" for i, a in enumerate(action_by_driver[:3]))

    return (
        f"RETENTION CONVERSATION GUIDE\n"
        f"Profile: {sen.capitalize()} {role} · {dept} · Impact {impact:.0f}/100 · Departure risk {label.upper()}\n\n"
        f"RISK DRIVERS (from predictive model):\n{driver_lines}\n\n"
        f"PROTECTIVE FACTORS:\n{protect_lines}\n\n"
        f"RECOMMENDED CONVERSATION FRAMING:\n"
        f"Open with recognition of the employee's specific contributions to {dept}. "
        f"Frame the conversation around career growth and organizational investment — "
        f"not performance concerns. The goal is to understand what would increase their sense of purpose "
        f"and belonging, not to communicate concern about departure.\n\n"
        f"SUGGESTED ACTIONS:\n{actions}\n\n"
        f"─────────────────────────────────────────────────────────────────\n"
        f"AI-assisted — for context only, not a decision. All retention actions require human judgment."
    )


# ── Prompt builders (PII-free) ────────────────────────────────────────────────

def _impact_prompt(source: dict) -> str:
    anon    = source["anon_id"]
    role    = source["role"]
    sen     = source["seniority"]
    dept    = source["department"]
    score   = source["impact_score"]
    drivers = source.get("drivers", [])

    driver_str = "; ".join(
        f"{d['factor']} ({d['value']}, weight {d['contribution']:.0f}%)"
        for d in drivers[:3]
    )
    return (
        f"You are an HR analytics assistant. Explain the following impact score to a non-technical manager. "
        f"Use plain, encouraging language. Do not mention any names, salaries, or personal identifiers.\n\n"
        f"Employee profile (anonymized): {anon}\n"
        f"Role: {sen} {role} in {dept}\n"
        f"Impact Score: {score:.0f}/100\n"
        f"Top score drivers: {driver_str}\n\n"
        f"Write a concise 2-paragraph explanation in clear business language. "
        f"First paragraph: what the score means and why. Second paragraph: recommended action or context."
    )


def _attrition_prompt(source: dict) -> str:
    anon    = source["anon_id"]
    role    = source["role"]
    sen     = source["seniority"]
    dept    = source["department"]
    risk    = source["attrition_risk"]
    label   = _risk_label(risk)
    drivers = source.get("drivers", [])

    driver_str = "; ".join(
        f"{d['factor']} — {d['value']} ({d['direction']} signal)"
        for d in drivers[:3]
    )
    return (
        f"You are an HR analytics assistant. Explain the following attrition risk to a manager. "
        f"Use supportive, action-oriented language. Do not mention names, salaries, or personal identifiers. "
        f"Never use words like 'fired', 'terminated', or 'eliminated'.\n\n"
        f"Profile (anonymized): {anon}\n"
        f"Role: {sen} {role} in {dept}\n"
        f"Departure probability: {risk*100:.0f}% ({label} risk)\n"
        f"Predictive signals: {driver_str}\n\n"
        f"Write a concise 2-paragraph explanation. "
        f"First paragraph: what the risk signals indicate. "
        f"Second paragraph: suggested retention-focused actions the manager can take."
    )


def _simulation_prompt(source: dict) -> str:
    return (
        f"You are an HR analytics assistant writing an executive summary for a workforce optimization scenario. "
        f"Use professional, data-driven language. Do not mention employee names.\n\n"
        f"Scenario data:\n"
        f"- Budget target: {source['budget_pct']*100:.0f}% of current spend\n"
        f"- Proposed headcount: {source['n_retained']} of {source['n_total']}\n"
        f"- Impact preserved: {source['impact_preserved_pct']:.0f}%\n"
        f"- Nexus employees retained: {source.get('nexus_retained', 0)}\n"
        f"- Skills coverage: {source.get('skills_note', 'maintained')}\n\n"
        f"Write a 3-paragraph executive summary:\n"
        f"Paragraph 1: What the simulation achieved.\n"
        f"Paragraph 2: What was protected and why.\n"
        f"Paragraph 3: Primary risks and recommended next steps."
    )


def _brief_prompt(source: dict) -> str:
    anon    = source["anon_id"]
    role    = source["role"]
    sen     = source["seniority"]
    dept    = source["department"]
    risk    = source["attrition_risk"]
    impact  = source["impact_score"]
    label   = _risk_label(risk)
    drivers = source.get("drivers", [])

    driver_str = "\n".join(
        f"  - {d['factor']}: {d['value']} ({d['direction']})"
        for d in drivers[:3]
    )
    return (
        f"You are an HR analytics assistant helping a manager prepare a retention conversation. "
        f"Use supportive, growth-focused language. Never use 'fire', 'terminate', or 'eliminate'. "
        f"Do not mention names or salaries.\n\n"
        f"Profile (anonymized): {anon}\n"
        f"Role: {sen.capitalize()} {role} in {dept}\n"
        f"Impact score: {impact:.0f}/100 | Departure risk: {label.upper()}\n"
        f"Risk signals:\n{driver_str}\n\n"
        f"Write a structured manager brief with:\n"
        f"1. A 1-sentence risk summary in plain language.\n"
        f"2. Suggested conversation framing (2-3 sentences, retention-focused).\n"
        f"3. Two to three specific, actionable retention suggestions based on the risk signals."
    )


# ── Source data builders ──────────────────────────────────────────────────────

def _build_impact_source(row: pd.Series, df: pd.DataFrame) -> dict:
    dept_avg = float(df[df["department"] == row["department"]]["impact_score"].mean())
    return {
        "anon_id":        _anon_label(str(row.get("role_title", "employee")), str(row["employee_id"])),
        "role":           str(row.get("role_title", "")),
        "seniority":      str(row.get("seniority_level", "mid")),
        "department":     str(row.get("department", "")),
        "impact_score":   float(row["impact_score"]),
        "is_nexus":       bool(row.get("_is_nexus", False)),
        "dept_avg_score": round(dept_avg, 1),
        "drivers":        _impact_drivers(row, df),
    }


def _build_attrition_source(row: pd.Series, df: pd.DataFrame) -> dict:
    return {
        "anon_id":        _anon_label(str(row.get("role_title", "employee")), str(row["employee_id"])),
        "role":           str(row.get("role_title", "")),
        "seniority":      str(row.get("seniority_level", "mid")),
        "department":     str(row.get("department", "")),
        "attrition_risk": float(row["attrition_risk"]),
        "impact_score":   float(row["impact_score"]),
        "is_nexus":       bool(row.get("_is_nexus", False)),
        "drivers":        _attrition_drivers(row, df),
    }


def _build_simulation_source(df: pd.DataFrame, budget_pct: float) -> dict:
    n_total       = len(df)
    n_retained    = int(n_total * budget_pct)
    retained_df   = df.nlargest(n_retained, "impact_score")
    impact_total  = float(df["impact_score"].sum())
    impact_kept   = float(retained_df["impact_score"].sum())
    nexus_retained = int(retained_df["_is_nexus"].sum())

    dept_top  = retained_df["department"].value_counts().index[0] if n_retained else ""
    dept_note = f"The {dept_top} department has the highest retention ratio." if dept_top else ""

    role_counts = retained_df["role_title"].value_counts()
    gaps        = [r for r, c in df["role_title"].value_counts().items() if role_counts.get(r, 0) == 0]
    skills_note = (
        f"{len(gaps)} role type(s) have no retained holders — review for coverage risk"
        if gaps else "critical skill coverage maintained across all role types"
    )

    return {
        "budget_pct":            budget_pct,
        "retained_pct":          round(n_retained / max(n_total, 1) * 100, 1),
        "impact_preserved_pct":  round(impact_kept / max(impact_total, 1) * 100, 1),
        "n_retained":            n_retained,
        "n_total":               n_total,
        "nexus_retained":        nexus_retained,
        "dept_summary":          dept_note,
        "skills_note":           skills_note,
    }


# ── Public generation functions ───────────────────────────────────────────────

def _generate(
    narrative_type: str,
    source: dict,
    prompt_fn,       # type: ignore[type-arg]
    template_fn,     # type: ignore[type-arg]
    employee_id: str | None = None,
) -> dict:
    cache_key = _cache_key(narrative_type, employee_id)
    if cache_key in _CACHE:
        text, is_llm, ts = _CACHE[cache_key]
        return {
            "narrative":    text,
            "is_llm":       is_llm,
            "model":        OLLAMA_MODEL if is_llm else "template",
            "source_data":  source,
            "disclaimer":   "AI-assisted summary — for context only, not a decision",
            "cached":       True,
            "generated_at": ts,
        }

    t0 = time.time()
    prompt   = prompt_fn(source)
    llm_text = _call_ollama(prompt)
    is_llm   = llm_text is not None
    text     = llm_text if is_llm else template_fn(source)
    elapsed  = int((time.time() - t0) * 1000)
    ts       = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    _CACHE[cache_key] = (text, is_llm, ts)

    return {
        "narrative":       text,
        "is_llm":          is_llm,
        "model":           OLLAMA_MODEL if is_llm else "template",
        "source_data":     source,
        "disclaimer":      "AI-assisted summary — for context only, not a decision",
        "cached":          False,
        "generated_at":    ts,
        "generation_ms":   elapsed,
    }


def generate_impact_explanation(scenario: str, size: str, employee_id: str) -> dict:
    org = get_org(scenario, size)
    df  = _add_scores(org.employees.copy().reset_index(drop=True))
    mask = df["employee_id"] == employee_id
    if not mask.any():
        raise ValueError(f"Employee {employee_id} not found")
    row    = df[mask].iloc[0]
    source = _build_impact_source(row, df)
    return _generate("impact", source, _impact_prompt, _impact_template, employee_id)


def generate_attrition_explanation(scenario: str, size: str, employee_id: str) -> dict:
    org = get_org(scenario, size)
    df  = _add_scores(org.employees.copy().reset_index(drop=True))
    mask = df["employee_id"] == employee_id
    if not mask.any():
        raise ValueError(f"Employee {employee_id} not found")
    row    = df[mask].iloc[0]
    source = _build_attrition_source(row, df)
    return _generate("attrition", source, _attrition_prompt, _attrition_template, employee_id)


def generate_simulation_summary(scenario: str, size: str, budget_pct: float) -> dict:
    org    = get_org(scenario, size)
    df     = _add_scores(org.employees.copy().reset_index(drop=True))
    source = _build_simulation_source(df, budget_pct)
    return _generate("simulation", source, _simulation_prompt, _simulation_template,
                     f"sim_{budget_pct:.2f}")


def generate_manager_brief(scenario: str, size: str, employee_id: str) -> dict:
    org = get_org(scenario, size)
    df  = _add_scores(org.employees.copy().reset_index(drop=True))
    mask = df["employee_id"] == employee_id
    if not mask.any():
        raise ValueError(f"Employee {employee_id} not found")
    row    = df[mask].iloc[0]
    source = _build_attrition_source(row, df)  # same data, different template
    return _generate("brief", source, _brief_prompt, _manager_brief_template, employee_id)


# ── Page data builder ─────────────────────────────────────────────────────────

def build_narrative_data(scenario: str, size: str) -> dict:
    """Return page bootstrap data: Ollama status + candidate employee lists."""
    ollama = check_ollama()
    org    = get_org(scenario, size)
    df     = _add_scores(org.employees.copy().reset_index(drop=True))

    def _emp_row(r: pd.Series) -> dict:
        return {
            "employee_id":   str(r["employee_id"]),
            "full_name":     str(r["full_name"]),
            "role_title":    str(r.get("role_title", "")),
            "department":    str(r.get("department", "")),
            "seniority_level": str(r.get("seniority_level", "")),
            "impact_score":  float(r["impact_score"]),
            "attrition_risk":float(r["attrition_risk"]),
            "is_nexus":      bool(r.get("_is_nexus", False)),
        }

    # Top 15 by impact for the impact tab
    top_impact = [_emp_row(r) for _, r in df.nlargest(15, "impact_score").iterrows()]
    # Top 10 by attrition × impact for attrition / brief tabs
    df["_priority"] = df["attrition_risk"] * df["impact_score"] / 100
    top_priority    = [_emp_row(r) for _, r in df.nlargest(10, "_priority").iterrows()]

    # Org-level stats for simulation summary
    org_stats = {
        "n_employees":    len(df),
        "total_payroll":  int(df["annual_salary"].sum()),
        "avg_impact":     round(float(df["impact_score"].mean()), 1),
        "nexus_count":    int(df["_is_nexus"].sum()),
        "high_risk_count":int((df["attrition_risk"] >= 0.6).sum()),
    }

    return {
        "ollama_status":      ollama,
        "top_impact_employees":   top_impact,
        "priority_employees":     top_priority,
        "org_stats":              org_stats,
    }
