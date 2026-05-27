"""
EIBO Python Client SDK — Sprint 19
Typed wrapper for the /api/v1/ public API.

Usage:
    from eibo_client import EiboClient

    client = EiboClient(api_key="eibo_analyst_…", base_url="http://eibo.internal")
    kpis   = client.dashboard(scenario="A", size="medium")
    print(kpis.headcount, kpis.avg_impact_score)
"""

from __future__ import annotations

import urllib.request
import urllib.error
import json
from dataclasses import dataclass, field


# ── Response types ────────────────────────────────────────────────────────────

@dataclass
class DashboardKPIs:
    scenario:         str
    size:             str
    headcount:        int
    departments:      int
    avg_impact_score: float
    avg_attrition:    float
    nexus_count:      int
    total_payroll:    float
    scope:            str


@dataclass
class ImpactEmployee:
    employee_id:    str
    role_title:     str
    department:     str
    seniority:      str
    impact_score:   float
    attrition_risk: float
    is_nexus:       bool
    annual_salary:  int | None = None


@dataclass
class ImpactData:
    scenario:  str
    size:      str
    scope:     str
    count:     int
    employees: list[ImpactEmployee] = field(default_factory=list)


@dataclass
class AttritionDistribution:
    critical: int
    high:     int
    moderate: int
    low:      int


@dataclass
class AttritionSummary:
    scenario:      str
    size:          str
    headcount:     int
    avg_risk:      float
    distribution:  AttritionDistribution
    nexus_at_risk: int


@dataclass
class OHIDeptRow:
    department: str
    ohi_score:  float
    grade:      str
    headcount:  int


@dataclass
class OHISummary:
    scenario:        str
    size:            str
    composite_score: float
    grade:           str
    sub_indices:     list[dict]
    department_ohi:  list[OHIDeptRow] = field(default_factory=list)


@dataclass
class ForecastMonth:
    month_offset:    int
    forecast_budget: float
    lower_80:        float
    upper_80:        float


@dataclass
class ForecastData:
    scenario:         str
    size:             str
    monthly_baseline: float
    annual_budget:    float
    forecast_horizon: int
    forecast:         list[ForecastMonth] = field(default_factory=list)


# ── Client ────────────────────────────────────────────────────────────────────

class EiboError(Exception):
    """Raised when the EIBO API returns a non-2xx response."""


class EiboClient:
    """
    Minimal HTTP client for the EIBO v1 API.

    Args:
        api_key:  API key (eibo_<scope>_<token>). Use sandbox key for testing.
        base_url: Base URL of the EIBO backend (default: http://localhost:8000).
        timeout:  Request timeout in seconds (default: 30).
    """

    SANDBOX_KEY = "eibo_demo_sandbox0000000000000000"

    def __init__(
        self,
        api_key:  str  = SANDBOX_KEY,
        base_url: str  = "http://localhost:8000",
        timeout:  int  = 30,
    ):
        self._key     = api_key
        self._base    = base_url.rstrip("/")
        self._timeout = timeout

    def _get(self, path: str, **params) -> dict:
        qs  = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{self._base}{path}{'?' + qs if qs else ''}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {self._key}"})
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(errors="replace")
            raise EiboError(f"HTTP {exc.code}: {body}") from exc

    # ── Public methods ─────────────────────────────────────────────────────────

    def health(self) -> dict:
        """Ping the v1 API. Returns {'status': 'ok', 'version': 'v1'}."""
        return self._get("/api/v1/health")

    def dashboard(self, scenario: str = "A", size: str = "small") -> DashboardKPIs:
        """Org-level KPI summary."""
        d = self._get("/api/v1/dashboard", scenario=scenario, size=size)
        return DashboardKPIs(**{k: d[k] for k in DashboardKPIs.__dataclass_fields__})

    def impact(
        self,
        scenario: str = "A",
        size:     str = "small",
        limit:    int = 100,
    ) -> ImpactData:
        """Impact scores for up to `limit` employees."""
        d    = self._get("/api/v1/impact", scenario=scenario, size=size, limit=limit)
        emps = [ImpactEmployee(**{k: e.get(k) for k in ImpactEmployee.__dataclass_fields__}) for e in d.get("employees", [])]
        return ImpactData(
            scenario=d["scenario"], size=d["size"], scope=d["scope"],
            count=d["count"], employees=emps,
        )

    def attrition_summary(self, scenario: str = "A", size: str = "small") -> AttritionSummary:
        """Org-level attrition risk distribution."""
        d    = self._get("/api/v1/attrition-summary", scenario=scenario, size=size)
        dist = AttritionDistribution(**d["distribution"])
        return AttritionSummary(
            scenario=d["scenario"], size=d["size"], headcount=d["headcount"],
            avg_risk=d["avg_risk"], distribution=dist, nexus_at_risk=d["nexus_at_risk"],
        )

    def ohi(self, scenario: str = "A", size: str = "small") -> OHISummary:
        """OHI composite score and department breakdown."""
        d     = self._get("/api/v1/ohi", scenario=scenario, size=size)
        depts = [OHIDeptRow(**row) for row in d.get("department_ohi", [])]
        return OHISummary(
            scenario=d["scenario"], size=d["size"],
            composite_score=d["composite_score"], grade=d["grade"],
            sub_indices=d.get("sub_indices", []), department_ohi=depts,
        )

    def forecast(self, scenario: str = "A", size: str = "small") -> ForecastData:
        """6-month budget forecast with confidence bands."""
        d      = self._get("/api/v1/forecast", scenario=scenario, size=size)
        months = [ForecastMonth(**m) for m in d.get("forecast", [])]
        return ForecastData(
            scenario=d["scenario"], size=d["size"],
            monthly_baseline=d["monthly_baseline"], annual_budget=d["annual_budget"],
            forecast_horizon=d["forecast_horizon"], forecast=months,
        )
