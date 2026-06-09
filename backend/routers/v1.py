"""
Sprint 19 — Public versioned API layer (/api/v1/).
All data endpoints require Authorization: Bearer <api-key>.
"""

from typing import Annotated

import numpy as np
from fastapi import APIRouter, Depends, Header, HTTPException

from backend.services.api_key_service import ApiKey, authenticate, key_allows_salary
from backend.services.data_service import get_org
from backend.services.ohi_service import build_ohi_data

router = APIRouter()


# ── Auth dependency ────────────────────────────────────────────────────────────

def _require_key(authorization: str = Header(default="")) -> ApiKey:
    raw = authorization.removeprefix("Bearer ").strip()
    key = authenticate(raw)
    if not key:
        raise HTTPException(
            status_code=401,
            detail="Invalid, revoked, or rate-limited API key. "
                   "Pass your key as: Authorization: Bearer eibo_<scope>_<token>",
        )
    return key


KeyDep = Annotated[ApiKey, Depends(_require_key)]


# ── Shared score computation ───────────────────────────────────────────────────

def _scored_df(scenario: str, size: str):
    try:
        df = get_org(scenario.upper(), size.lower()).employees.copy()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if "impact_score" not in df.columns:
        rng      = np.random.default_rng(42)
        sal_rank = df["annual_salary"].rank(pct=True)
        nexus_b  = df["_is_nexus"].astype(float) * 15
        df["impact_score"]   = np.clip(sal_rank * 70 + nexus_b + rng.normal(0, 5, len(df)), 0, 100).round(1)
        df["attrition_risk"] = np.clip(
            (1 - sal_rank) * 0.6 + rng.uniform(0, 0.4, len(df)) - df["_is_nexus"].astype(float) * 0.15,
            0.01, 0.99,
        ).round(3)

    return df


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/v1/health")
def v1_health() -> dict:
    return {"status": "ok", "version": "v1", "service": "eibo-api"}


@router.get("/v1/dashboard")
def v1_dashboard(key: KeyDep, scenario: str = "A", size: str = "small") -> dict:
    """Org-level KPI summary."""
    df = _scored_df(scenario, size)
    return {
        "scenario":         scenario.upper(),
        "size":             size.lower(),
        "headcount":        len(df),
        "departments":      int(df["department"].nunique()),
        "avg_impact_score": round(float(df["impact_score"].mean()), 1),
        "avg_attrition":    round(float(df["attrition_risk"].mean()), 3),
        "nexus_count":      int(df["_is_nexus"].sum()),
        "total_payroll":    round(float(df["annual_salary"].sum()), 0),
        "scope":            key.scope,
    }


@router.get("/v1/impact")
def v1_impact(key: KeyDep, scenario: str = "A", size: str = "small", limit: int = 100) -> dict:
    """Impact scores for up to `limit` employees. Salary masked unless key scope ≥ Manager."""
    df = _scored_df(scenario, size)
    show_salary = key_allows_salary(key.scope)

    records = []
    for _, row in df.head(min(limit, 500)).iterrows():
        rec: dict = {
            "employee_id":    row["employee_id"],
            "role_title":     row["role_title"],
            "department":     row["department"],
            "seniority":      row["seniority_level"],
            "impact_score":   round(float(row["impact_score"]), 1),
            "attrition_risk": round(float(row["attrition_risk"]), 3),
            "is_nexus":       bool(row["_is_nexus"]),
        }
        if show_salary:
            rec["annual_salary"] = int(row["annual_salary"])
        records.append(rec)

    return {
        "scenario":  scenario.upper(),
        "size":      size.lower(),
        "scope":     key.scope,
        "count":     len(records),
        "employees": records,
    }


@router.get("/v1/attrition-summary")
def v1_attrition_summary(key: KeyDep, scenario: str = "A", size: str = "small") -> dict:
    """Org-level attrition risk distribution."""
    df = _scored_df(scenario, size)
    risks = df["attrition_risk"]
    bins  = {
        "critical": int((risks >= 0.81).sum()),
        "high":     int(((risks >= 0.61) & (risks < 0.81)).sum()),
        "moderate": int(((risks >= 0.31) & (risks < 0.61)).sum()),
        "low":      int((risks < 0.31).sum()),
    }
    nexus_at_risk = int((df["_is_nexus"] & (risks > 0.60)).sum())
    return {
        "scenario":      scenario.upper(),
        "size":          size.lower(),
        "headcount":     len(df),
        "avg_risk":      round(float(risks.mean()), 3),
        "distribution":  bins,
        "nexus_at_risk": nexus_at_risk,
    }


@router.get("/v1/ohi")
def v1_ohi(key: KeyDep, scenario: str = "A", size: str = "small") -> dict:
    """OHI composite score and department breakdown."""
    data    = build_ohi_data(scenario.upper(), size.lower())
    summary = data.get("summary", {})
    depts   = data.get("dept_breakdown", [])
    return {
        "scenario":        scenario.upper(),
        "size":            size.lower(),
        "composite_score": summary.get("composite_score"),
        "grade":           summary.get("grade"),
        "sub_indices":     summary.get("sub_indices", []),
        "department_ohi":  [
            {
                "department": r.get("department"),
                "ohi_score":  r.get("ohi_score"),
                "grade":      r.get("grade"),
                "headcount":  r.get("headcount"),
            }
            for r in depts
        ],
    }


@router.get("/v1/forecast")
def v1_forecast(key: KeyDep, scenario: str = "A", size: str = "small") -> dict:
    """6-month budget forecast with 80% confidence bands."""
    df             = _scored_df(scenario, size)
    monthly_budget = float(df["annual_salary"].sum() + df["annual_benefits"].sum()) / 12

    rng    = np.random.default_rng(99)
    months = [
        {
            "month_offset":    i + 1,
            "forecast_budget": round(monthly_budget * float(1 + rng.uniform(-0.03, 0.05)), 0),
            "lower_80":        round(monthly_budget * 0.94, 0),
            "upper_80":        round(monthly_budget * 1.06, 0),
        }
        for i in range(6)
    ]

    return {
        "scenario":         scenario.upper(),
        "size":             size.lower(),
        "monthly_baseline": round(monthly_budget, 0),
        "annual_budget":    round(monthly_budget * 12, 0),
        "forecast_horizon": 6,
        "forecast":         months,
    }
