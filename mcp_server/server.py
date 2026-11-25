"""EIBO MCP server: workforce decision support for Managers and People Analysts.

Exposes the platform's analytics to MCP clients (Claude Desktop, Claude Code, other
LLM hosts) as read-only tools, plus methodology/language resources and guided prompts.

Every tool:
  - checks the caller's RBAC permission (auth/rbac.py);
  - returns employee-level rows only for departments in the caller's scope;
  - masks salaries by role and redacts names unless EIBO_MCP_SHARE_NAMES is on;
  - writes an entry to the audit trail.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any, Literal

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from audit.logger import EventCategory, get_audit_logger
from auth.rbac import Permission
from backend.services import (
    compensation_service,
    data_service,
    fairness_service,
    knowledge_service,
    mobility_service,
    ohi_service,
    resilience_service,
)
from mcp_server.access import AccessDenied, Scope
from mcp_server.config import Settings

_REPO_ROOT = Path(__file__).resolve().parents[1]

INSTRUCTIONS = """\
EIBO is a workforce decision-support platform. It suggests; people decide.

How to use these tools well:
- Start with `whoami` to learn the caller's role, department scope and what is masked.
- All data is the organization's synthetic demo dataset unless stated otherwise.
- Impact scores (0-100) combine KPI history, collaboration-network position, skill
  criticality and replacement cost. Impact percentile is the rank within the org.
- Attrition risk (0-1) is a heuristic estimate of voluntary departure, framed as a
  retention opportunity, never as a verdict about a person.
- Budget simulations are suggestions. Say "suggested retention" and "not retained in
  simulation"; never say terminate, fire, cut or eliminate. Remind the user that final
  decisions, overrides and their rationale belong to people.
- Employee names may be redacted to "<role> #<ID>" for privacy; use the ID in follow-ups.
- Read `eibo://guide/methodology` before explaining how a number was produced, and
  `eibo://guide/language` before drafting anything an employee or manager will read.
"""

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)

Scenario = Annotated[
    Literal["A", "B", "C"] | None,
    Field(description="Demo organization: A growing company, B restructuring, C merger. Defaults to the server setting."),
]
OrgSize = Annotated[
    Literal["small", "medium", "large"] | None,
    Field(description="Organization size: small (50), medium (500), large (5,000). Defaults to the server setting."),
]

_RISK_BANDS = ((0.81, "Critical"), (0.61, "High"), (0.31, "Moderate"), (0.0, "Low"))
_BAND_ORDER = {"Low": 0, "Moderate": 1, "High": 2, "Critical": 3}

METHODOLOGY = """\
# EIBO methodology (what the numbers mean)

## Impact score (0-100)
100 x (0.40 KPI + 0.30 network + 0.20 skills + 0.10 replacement cost), each component
min-max normalized. KPI uses quarterly history with a trend term; network uses degree,
betweenness, eigenvector and PageRank centrality on the collaboration graph; skills use
criticality and uniqueness of held critical skills. Scores cluster roughly between 25
and 75, so compare people by **impact percentile** (rank within the org, 0-100).

## Attrition risk (0-1)
Demo heuristic: lower pay relative to peers raises risk, network-critical ("nexus")
employees get a small discount. Bands: Low < 0.31 <= Moderate < 0.61 <= High < 0.81 <= Critical.
It is a probability for a profile, not a prediction about an individual.

## Budget simulation
Integer linear program: maximize sum(impact_percentile - headcount_cost) over retained
people, subject to the budget (salary), force-retain/exclude overrides, and optionally
one leader per team and one holder per critical skill. headcount_cost (default 10)
makes each seat cost something, so the plan prefers higher-impact people over simply
keeping the most people, and may leave budget unused on purpose.

## Organizational Health Index
Weighted composite: financial health 20%, talent risk 20%, knowledge resilience 20%,
leadership pipeline 15%, compensation equity 15%, collaboration density 10%.

## Fairness audit
EEOC four-fifths rule plus chi-square significance on model outputs and simulated
selections. Demographic groups in the demo are synthetic proxies.

## Known limits
Data is synthetic. Attrition risk is not yet the trained ML model. Findings need human
and, for fairness or pay equity, legal interpretation.
"""

LANGUAGE_GUIDE = """\
# Language guide for anything people will read

Use                                   | Never use
------------------------------------- | -----------------------------------------
suggested retention                   | recommended for termination
not retained in simulation            | terminated, fired, cut, eliminated, laid off
structure optimization / strategy     | reduction plan, layoffs
retention opportunity                 | flight risk as a label for a person
Organizational nexus / critical talent| expendable, low performer

Principles:
- The model suggests; people decide. State that overrides with a written rationale are expected.
- Show uncertainty: risk is a probability for a profile, not a verdict about a person.
- Behind every record is a person with a career. Lead with context (role, skills,
  contribution), not cost.
- Never rank people as "worst" or "most expensive".
"""


def _risk_band(risk: float) -> str:
    return next(label for floor, label in _RISK_BANDS if risk >= floor)


class ToolContext:
    """Per-call data access bound to one caller's scope."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.scope = Scope(settings)
        log_dir = Path(settings.audit_log_dir)
        self.audit = get_audit_logger(log_dir if log_dir.is_absolute() else _REPO_ROOT / log_dir)

    # ── dataset helpers ──────────────────────────────────────────────────
    def dataset(self, scenario: str | None, size: str | None) -> tuple[str, str]:
        return (scenario or self.settings.default_scenario, size or self.settings.default_size)

    def people(self, sc: str, sz: str) -> dict[str, dict]:
        """Employee rows keyed by the platform's short employee ID, with percentile and seniority."""
        dash = data_service.build_dashboard_data(sc, sz)
        org = data_service.get_org(sc, sz)
        short = org.employees["employee_id"].astype(str).str[:8].str.upper()
        seniority = dict(zip(short, org.employees["seniority_level"], strict=True))
        hire = dict(zip(short, org.employees["hire_date"].astype(str), strict=True))
        pct = data_service._impact_percentiles(dash["employee_table"])
        rows = {}
        for e in dash["employee_table"]:
            eid = e["employee_id"]
            rows[eid] = {**e, "seniority_level": seniority.get(eid), "hire_date": hire.get(eid),
                         "impact_percentile": pct[eid]}
        return rows

    def name_map(self, people: dict[str, dict]) -> dict[str, str]:
        """full name -> display name, for redacting names embedded in other services' output."""
        return {p["full_name"]: self.scope.name(p["full_name"], eid, p["role_title"]) for eid, p in people.items()}

    def employee_brief(self, p: dict) -> dict[str, Any]:
        row = {
            "employee_id": p["employee_id"],
            "name": self.scope.name(p["full_name"], p["employee_id"], p["role_title"]),
            "role_title": p["role_title"],
            "department": p["department"],
            "team": p["team_name"],
            "seniority": p.get("seniority_level"),
            "impact_score": p["impact_score"],
            "impact_percentile": p["impact_percentile"],
            "is_nexus": p["is_nexus"],
            "top_skill": p["top_skill"],
        }
        if self.scope.ac.can(Permission.VIEW_PREDICTIVE):
            row["attrition_risk"] = p["attrition_risk"]
            row["risk_band"] = _risk_band(p["attrition_risk"])
        if self.scope.salary_visible:
            row["annual_salary"] = self.scope.salary(p["annual_salary"])
        return row

    def log(self, tool: str, resource: str, detail: str, category: EventCategory = EventCategory.ACCESS) -> None:
        u = self.settings.user
        self.audit.log(
            category=category, action=f"mcp:{tool}", resource=resource, detail=detail,
            user_id=u.user_id, user_email=u.email, user_role=u.role.label,
        )


def _tool_errors(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Turn access and validation problems into clean MCP tool errors."""

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return fn(*args, **kwargs)
        except AccessDenied as exc:
            raise ToolError(f"Access denied: {exc}") from exc
        except (ValueError, KeyError) as exc:
            raise ToolError(str(exc)) from exc

    return wrapper


def build_server(settings: Settings) -> MCPServer:
    ctx = ToolContext(settings)
    scope = ctx.scope
    server = MCPServer(
        name="eibo",
        title="EIBO Workforce Decision Support",
        description="Impact, retention risk, budget simulation and organizational health for managers and people analysts.",
        instructions=INSTRUCTIONS,
        version="1.0.0",
        log_level="WARNING",
    )

    # ── Identity ─────────────────────────────────────────────────────────
    @server.tool(title="Who am I", annotations=READ_ONLY)
    @_tool_errors
    def whoami(scenario: Scenario = None, size: OrgSize = None) -> dict[str, Any]:
        """Your role, department scope, what is masked, and the departments in the dataset.

        Call this first: it tells you which other tools and departments are available."""
        sc, sz = ctx.dataset(scenario, size)
        depts = sorted({p["department"] for p in ctx.people(sc, sz).values()})
        ctx.log("whoami", f"{sc}/{sz}", "identity and scope")
        return {**scope.describe(), "dataset": {"scenario": sc, "size": sz},
                "departments_in_dataset": depts, "departments_you_can_see": scope.visible_departments(depts)}

    # ── Overview ─────────────────────────────────────────────────────────
    @server.tool(title="Organization overview", annotations=READ_ONLY)
    @_tool_errors
    def org_overview(scenario: Scenario = None, size: OrgSize = None) -> dict[str, Any]:
        """Headcount, payroll vs budget, average impact, nexus employees and per-department summary.

        Organization totals are always shown; department rows only for departments in your scope."""
        scope.require(Permission.VIEW_DASHBOARD, "view the dashboard")
        sc, sz = ctx.dataset(scenario, size)
        d = data_service.build_dashboard_data(sc, sz)
        depts = [r for r in d["dept_summary"] if scope.can_see(r["department"])]
        ctx.log("org_overview", f"{sc}/{sz}", "dashboard summary")
        return {
            "org_name": d["org_name"], "scenario": sc, "size": sz,
            "headcount": d["total_headcount"],
            "annual_payroll": d["total_spend"], "annual_budget": d["total_budget"],
            "budget_variance_pct": d["budget_variance_pct"],
            "avg_impact_score": d["avg_impact_score"],
            "nexus_employees": d["n_nexus_employees"],
            "teams_with_high_avg_attrition_risk": d["n_at_risk_teams"],
            "departments": [{k: r[k] for k in ("department", "headcount", "total_spend", "annual_budget",
                                               "budget_variance_pct", "avg_impact", "fragility_avg")} for r in depts],
            "departments_outside_scope": len(d["dept_summary"]) - len(depts),
        }

    # ── People ───────────────────────────────────────────────────────────
    @server.tool(title="List employees", annotations=READ_ONLY)
    @_tool_errors
    def list_employees(
        department: Annotated[str | None, Field(description="Limit to one department (must be in your scope).")] = None,
        sort_by: Literal["impact", "attrition_risk", "salary"] = "impact",
        nexus_only: Annotated[bool, Field(description="Only organizational-nexus employees.")] = False,
        min_risk_band: Literal["Low", "Moderate", "High", "Critical"] = "Low",
        limit: Annotated[int, Field(ge=1, le=100)] = 25,
        scenario: Scenario = None,
        size: OrgSize = None,
    ) -> dict[str, Any]:
        """Employees in your scope with impact score/percentile, nexus flag, top skill,
        and (if your role allows) attrition risk and salary."""
        scope.require(Permission.VIEW_EMPLOYEE_LIST, "list employees")
        sc, sz = ctx.dataset(scenario, size)
        people = ctx.people(sc, sz)
        scope.check_department(department, list({p["department"] for p in people.values()}))
        if sort_by == "attrition_risk" or min_risk_band != "Low":
            scope.require(Permission.VIEW_PREDICTIVE, "see attrition risk")
        if sort_by == "salary" and not scope.salary_visible:
            raise AccessDenied("salary is masked for your role")
        rows = [p for p in people.values()
                if scope.can_see(p["department"])
                and (department is None or p["department"] == department)
                and (not nexus_only or p["is_nexus"])
                and _BAND_ORDER[_risk_band(p["attrition_risk"])] >= _BAND_ORDER[min_risk_band]]
        key = {"impact": "impact_score", "attrition_risk": "attrition_risk", "salary": "annual_salary"}[sort_by]
        rows.sort(key=lambda p: p[key], reverse=True)
        ctx.log("list_employees", f"{sc}/{sz}", f"department={department} sort={sort_by} n={len(rows)}")
        return {"total_matching": len(rows), "employees": [ctx.employee_brief(p) for p in rows[:limit]]}

    @server.tool(title="Employee profile", annotations=READ_ONLY)
    @_tool_errors
    def employee_profile(
        employee_id: Annotated[str, Field(description="8-character employee ID, e.g. 5AC236BE.")],
        scenario: Scenario = None,
        size: OrgSize = None,
    ) -> dict[str, Any]:
        """Everything EIBO knows about one employee: impact, retention risk and its main driver,
        knowledge domains (single-knowledge-holder flags), pay position and career mobility."""
        scope.require(Permission.VIEW_EMPLOYEE_LIST, "view employee profiles")
        sc, sz = ctx.dataset(scenario, size)
        people = ctx.people(sc, sz)
        eid = employee_id.strip().upper()
        if eid not in people:
            raise ValueError(f"No employee with ID {eid!r} in scenario {sc}/{sz}.")
        p = people[eid]
        if not scope.can_see(p["department"]):
            raise AccessDenied(f"employee {eid} is in {p['department']}, outside your scope")

        profile: dict[str, Any] = {**ctx.employee_brief(p), "hire_date": p.get("hire_date"), "avg_kpi": p["avg_kpi"]}
        if scope.ac.can(Permission.VIEW_PREDICTIVE):
            attr = next((e for e in data_service.build_attrition_data(sc, sz)["employees"] if e["employee_id"] == eid), None)
            if attr:
                profile["retention_driver"] = attr["top_driver"]
        know = next((e for e in knowledge_service.build_knowledge_data(sc, sz)["employees"] if e["employee_id"] == eid), None)
        if know:
            profile["knowledge"] = {
                "knowledge_loss_score": know["knowledge_loss_score"],
                "domains_held": know["domain_count"],
                "single_knowledge_holder_for": know["skh_domains"],
            }
        if scope.salary_visible:
            comp = next((e for e in compensation_service.build_compensation_data(sc, sz)["employees"] if e["employee_id"] == eid), None)
            if comp:
                profile["pay_position"] = {"comp_ratio": comp["comp_ratio"], "market_tier": comp["market_tier"]}
        mob = next((e for e in mobility_service.build_mobility_data(sc, sz)["career_paths"] if e["employee_id"] == eid), None)
        if mob:
            profile["mobility"] = {"stagnation_score": mob["stagnation_score"],
                                   "current_skills": mob.get("current_skills", [])}
        ctx.log("employee_profile", f"{sc}/{sz}/{eid}", "employee profile")
        return profile

    @server.tool(title="Retention risks", annotations=READ_ONLY)
    @_tool_errors
    def retention_risks(
        department: Annotated[str | None, Field(description="Limit to one department in your scope.")] = None,
        min_risk_band: Literal["Moderate", "High", "Critical"] = "High",
        limit: Annotated[int, Field(ge=1, le=50)] = 15,
        scenario: Scenario = None,
        size: OrgSize = None,
    ) -> dict[str, Any]:
        """Employees in your scope whose retention needs attention, with the main driver for each.

        Frame these as retention opportunities: what to address, not who is leaving."""
        scope.require(Permission.VIEW_PREDICTIVE, "see retention risk")
        sc, sz = ctx.dataset(scenario, size)
        people = ctx.people(sc, sz)
        scope.check_department(department, list({p["department"] for p in people.values()}))
        drivers = {e["employee_id"]: e["top_driver"] for e in data_service.build_attrition_data(sc, sz)["employees"]}
        rows = [p for p in people.values()
                if scope.can_see(p["department"])
                and (department is None or p["department"] == department)
                and _BAND_ORDER[_risk_band(p["attrition_risk"])] >= _BAND_ORDER[min_risk_band]]
        rows.sort(key=lambda p: p["attrition_risk"], reverse=True)
        ctx.log("retention_risks", f"{sc}/{sz}", f"department={department} band>={min_risk_band} n={len(rows)}")
        return {
            "total_matching": len(rows),
            "nexus_among_them": sum(p["is_nexus"] for p in rows),
            "employees": [{**ctx.employee_brief(p), "retention_driver": drivers.get(p["employee_id"])} for p in rows[:limit]],
        }

    # ── Budget simulation ────────────────────────────────────────────────
    def _simulate(sc: str, sz: str, budget_pct: float, leadership: bool, skills: bool,
                  headcount_cost: float, force_retain: list[str], exclude: list[str]) -> dict:
        return data_service.run_simulation(sc, sz, budget_pct, force_retain, exclude, leadership, skills, headcount_cost)

    @server.tool(title="Simulate a budget scenario", annotations=READ_ONLY)
    @_tool_errors
    def simulate_budget(
        budget_pct: Annotated[float, Field(ge=10, le=200, description="Budget as % of current team budgets, e.g. 80.")],
        leadership_coverage: Annotated[bool, Field(description="Every team keeps at least one leader.")] = True,
        critical_skills_coverage: Annotated[bool, Field(description="Every critical skill keeps at least one holder.")] = True,
        headcount_cost: Annotated[float, Field(ge=0, le=50, description="Impact-percentile points charged per person kept (0 = headcount is free).")] = 10,
        force_retain: Annotated[list[str] | None, Field(description="Employee IDs the plan must keep (requires override permission).")] = None,
        exclude: Annotated[list[str] | None, Field(description="Employee IDs left out of the simulation (requires override permission).")] = None,
        scenario: Scenario = None,
        size: OrgSize = None,
    ) -> dict[str, Any]:
        """Run the retention optimizer for a budget and return the suggested plan.

        Nothing is saved or acted on. Results are suggestions: people decide, and say
        "not retained in simulation", never terminate/cut/fire."""
        scope.require(Permission.RUN_SIMULATION, "run simulations")
        if force_retain or exclude:
            scope.require(Permission.OVERRIDE_DECISION, "use force-retain or exclude overrides")
        sc, sz = ctx.dataset(scenario, size)
        r = _simulate(sc, sz, budget_pct, leadership_coverage, critical_skills_coverage, headcount_cost,
                      [i.upper() for i in force_retain or []], [i.upper() for i in exclude or []])
        people = ctx.people(sc, sz)
        mine = [e for e in r["employees"] if scope.can_see(e["department"])]
        by_dept: dict[str, dict[str, int]] = {}
        for e in mine:
            d = by_dept.setdefault(e["department"], {"suggested_retention": 0, "not_retained_in_simulation": 0})
            d["suggested_retention" if e["retained"] else "not_retained_in_simulation"] += 1
        top = [e for e in r["employees"] if e["impact_percentile"] > 80]
        ctx.log("simulate_budget", f"{sc}/{sz}", f"budget={budget_pct}% leadership={leadership_coverage} "
                f"skills={critical_skills_coverage} cost={headcount_cost} overrides={bool(force_retain or exclude)}",
                EventCategory.SIMULATION)
        return {
            "feasible": r["feasible"],
            "infeasibility_reason": r["infeasibility_reason"],
            "budget_pct": budget_pct,
            "suggested_retention_count": r["retained_count"],
            "not_retained_in_simulation_count": r["at_risk_count"],
            "budget_used_pct": r["budget_used_pct"],
            "total_impact_retained": r["total_impact"],
            "top_impact_quintile_kept": f"{sum(e['retained'] for e in top)}/{len(top)}",
            "constraints": r["constraints"],
            "objective": r["objective"],
            "your_departments": by_dept,
            "not_retained_in_simulation": [
                ctx.employee_brief(people[e["employee_id"]]) for e in mine if not e["retained"]
            ][:50],
            "note": "Simulation output is a suggestion for human review. Overrides with a written rationale are expected.",
        }

    @server.tool(title="Compare budget scenarios", annotations=READ_ONLY)
    @_tool_errors
    def compare_budget_scenarios(
        budget_pcts: Annotated[list[float], Field(min_length=1, max_length=6, description="Budgets to compare, e.g. [70, 80, 90].")],
        leadership_coverage: bool = True,
        critical_skills_coverage: bool = True,
        headcount_cost: Annotated[float, Field(ge=0, le=50)] = 10,
        scenario: Scenario = None,
        size: OrgSize = None,
    ) -> dict[str, Any]:
        """Side-by-side summary of the suggested plan at several budget levels (no per-person rows)."""
        scope.require(Permission.RUN_SIMULATION, "run simulations")
        sc, sz = ctx.dataset(scenario, size)
        rows = []
        for pct in budget_pcts:
            if not 10 <= pct <= 200:
                raise ValueError(f"budget_pct {pct} must be between 10 and 200")
            r = _simulate(sc, sz, pct, leadership_coverage, critical_skills_coverage, headcount_cost, [], [])
            top = [e for e in r["employees"] if e["impact_percentile"] > 80]
            rows.append({
                "budget_pct": pct, "feasible": r["feasible"],
                "suggested_retention_count": r["retained_count"],
                "not_retained_in_simulation_count": r["at_risk_count"],
                "budget_used_pct": r["budget_used_pct"],
                "total_impact_retained": r["total_impact"],
                "top_impact_quintile_kept": f"{sum(e['retained'] for e in top)}/{len(top)}",
                "teams_with_leader": f"{r['constraints']['leadership']['covered']}/{r['constraints']['leadership']['total']}",
                "critical_skills_covered": f"{r['constraints']['critical_skills']['covered']}/{r['constraints']['critical_skills']['total']}",
            })
        ctx.log("compare_budget_scenarios", f"{sc}/{sz}", f"budgets={budget_pcts}", EventCategory.SIMULATION)
        return {"scenarios": rows}

    # ── Organizational health and structure ──────────────────────────────
    @server.tool(title="Organizational health", annotations=READ_ONLY)
    @_tool_errors
    def org_health(scenario: Scenario = None, size: OrgSize = None) -> dict[str, Any]:
        """Organizational Health Index: overall grade, six weighted sub-indices, trend,
        alerts and per-department scores for your scope."""
        scope.require(Permission.VIEW_DASHBOARD, "view organizational health")
        sc, sz = ctx.dataset(scenario, size)
        d = ohi_service.build_ohi_data(sc, sz)
        ctx.log("org_health", f"{sc}/{sz}", "OHI summary")
        return {
            "summary": d["summary"],
            "sub_indices": {k: {f: v.get(f) for f in ("score", "weight", "grade", "detail") if f in v}
                            for k, v in d["sub_indices"].items()},
            "alert": d["alert"],
            "departments": [{k: r[k] for k in ("department", "score", "grade", "headcount", "avg_impact", "avg_attrition")}
                            for r in d["dept_ohi"] if scope.can_see(r["department"])],
            "retention_scenarios_preview": d["decision_preview"],
        }

    @server.tool(title="Knowledge concentration risks", annotations=READ_ONLY)
    @_tool_errors
    def knowledge_risks(
        department: Annotated[str | None, Field(description="Limit the transfer roadmap to one department in your scope.")] = None,
        scenario: Scenario = None,
        size: OrgSize = None,
    ) -> dict[str, Any]:
        """Knowledge domains held by a single person or by nobody, and the suggested
        knowledge-transfer roadmap for your scope."""
        scope.require(Permission.VIEW_STRATEGIC, "view knowledge risks")
        sc, sz = ctx.dataset(scenario, size)
        people = ctx.people(sc, sz)
        scope.check_department(department, list({p["department"] for p in people.values()}))
        names = ctx.name_map(people)
        d = knowledge_service.build_knowledge_data(sc, sz)
        risky = [{"domain": x["name"], "criticality": x["criticality"], "holders": x["holder_count"],
                  "single_knowledge_holder": x["is_skh"], "uncovered": x["is_uncovered"],
                  "primary_holder": names.get(x.get("primary_holder"), x.get("primary_holder"))}
                 for x in d["domains"] if x["is_skh"] or x["is_uncovered"]]
        roadmap = [{"domain": x["domain_name"], "criticality": x["criticality"],
                    "current_holder": names.get(x["current_holder"], x["current_holder"]),
                    "department": x["current_holder_dept"],
                    "suggested_successor": names.get(x.get("successor"), x.get("successor"))}
                   for x in d["transfer_roadmap"]
                   if scope.can_see(x["current_holder_dept"]) and (department is None or x["current_holder_dept"] == department)]
        ctx.log("knowledge_risks", f"{sc}/{sz}", f"department={department}")
        return {"summary": d["summary"], "at_risk_domains": risky, "transfer_roadmap": roadmap}

    @server.tool(title="Succession depth", annotations=READ_ONLY)
    @_tool_errors
    def succession_depth(
        department: Annotated[str | None, Field(description="Limit to one department in your scope.")] = None,
        scenario: Scenario = None,
        size: OrgSize = None,
    ) -> dict[str, Any]:
        """For each leader in your scope: who could step up now (depth 1), with
        development (depth 2) or longer term (depth 3), and where there is no successor."""
        scope.require(Permission.VIEW_STRATEGIC, "view succession plans")
        sc, sz = ctx.dataset(scenario, size)
        people = ctx.people(sc, sz)
        scope.check_department(department, list({p["department"] for p in people.values()}))
        names = ctx.name_map(people)
        rows = [{"leader": names.get(r["leader_name"], r["leader_name"]), "role_title": r["role_title"],
                 "department": r["department"], "succession_gap": r["succession_gap"],
                 **{f"depth_{i}": [names.get(n, n) for n in r[f"depth_{i}"]] for i in (1, 2, 3)}}
                for r in mobility_service.build_mobility_data(sc, sz)["succession"]
                if scope.can_see(r["department"]) and (department is None or r["department"] == department)]
        ctx.log("succession_depth", f"{sc}/{sz}", f"department={department}")
        return {"leaders": rows, "gaps": sum(r["succession_gap"] for r in rows)}

    @server.tool(title="Resilience stress test", annotations=READ_ONLY)
    @_tool_errors
    def resilience_stress_test(
        scenario_type: Literal["targeted_departure", "department_shock", "competitive_poaching",
                               "leadership_vacuum", "skill_crisis"],
        n: Annotated[int, Field(ge=1, le=50, description="People affected (targeted_departure, competitive_poaching).")] = 5,
        department: Annotated[str | None, Field(description="Department for department_shock / leadership_vacuum.")] = None,
        scenario: Scenario = None,
        size: OrgSize = None,
    ) -> dict[str, Any]:
        """Simulate a disruption and its knock-on departures: how many people would follow,
        the financial impact, skills left uncovered, and the change in resilience score."""
        scope.require(Permission.VIEW_STRATEGIC, "run resilience stress tests")
        sc, sz = ctx.dataset(scenario, size)
        people = ctx.people(sc, sz)
        scope.check_department(department, list({p["department"] for p in people.values()}))
        params: dict[str, Any] = {"n": n}
        if department:
            params["department"] = department
        df = resilience_service._add_scores(data_service.get_org(sc, sz).employees.copy().reset_index(drop=True))
        r = resilience_service.run_disruption_scenario(df, scenario_type, params)
        ctx.log("resilience_stress_test", f"{sc}/{sz}", f"type={scenario_type} params={params}")
        return {k: r[k] for k in ("scenario_label", "primary_count", "total_departed", "cascade_multiplier",
                                  "financial_impact", "orphaned_skills", "teams_below_minimum",
                                  "resilience_before", "resilience_after", "resilience_delta")}

    # ── Fairness and pay ─────────────────────────────────────────────────
    @server.tool(title="Fairness audit", annotations=READ_ONLY)
    @_tool_errors
    def fairness_audit(scenario: Scenario = None, size: OrgSize = None) -> dict[str, Any]:
        """EEOC four-fifths and chi-square checks on impact scores, attrition risk and simulated
        selections. A flag is a prompt for investigation, not a legal conclusion."""
        scope.require(Permission.VIEW_PREDICTIVE, "view the fairness audit")
        sc, sz = ctx.dataset(scenario, size)
        d = fairness_service.build_fairness_data(sc, sz)
        flags = [{"dimension": row["dimension"], "model": row["model"], "group": g["group"],
                  "adverse_impact_ratio": g["adverse_impact_ratio"]}
                 for row in d["eeoc_analysis"] for g in row["groups"] if not g["eeoc_pass"]]
        ctx.log("fairness_audit", f"{sc}/{sz}", f"flags={len(flags)}")
        return {"summary": d["summary"], "eeoc_flags": flags, "note": d["note"]}

    @server.tool(title="Pay equity", annotations=READ_ONLY)
    @_tool_errors
    def pay_equity(
        department: Annotated[str | None, Field(description="Limit to one department in your scope.")] = None,
        scenario: Scenario = None,
        size: OrgSize = None,
    ) -> dict[str, Any]:
        """Market position and pay gaps (raw and seniority-adjusted) for departments in your scope,
        plus the employees where a pay correction has the best retention return."""
        scope.require(Permission.VIEW_PREDICTIVE, "view pay equity")
        if not scope.salary_visible:
            raise AccessDenied("salary data is masked for your role")
        sc, sz = ctx.dataset(scenario, size)
        people = ctx.people(sc, sz)
        scope.check_department(department, list({p["department"] for p in people.values()}))
        d = compensation_service.build_compensation_data(sc, sz)
        mine = lambda dept: scope.can_see(dept) and (department is None or dept == department)  # noqa: E731
        roi = [{**ctx.employee_brief(people[r["employee_id"]]), "comp_ratio": r["comp_ratio"],
                "correction_cost": scope.salary(r["correction_cost"])}
               for r in d["retention_roi"] if r["employee_id"] in people and mine(r["department"])]
        ctx.log("pay_equity", f"{sc}/{sz}", f"department={department}")
        return {"summary": d["summary"],
                "department_gaps": [r for r in d["dept_equity"] if mine(r["department"])],
                "best_retention_return_corrections": roi}

    # ── Resources ────────────────────────────────────────────────────────
    @server.resource("eibo://guide/methodology", name="methodology", title="How EIBO numbers are produced",
                     mime_type="text/markdown")
    def methodology() -> str:
        return METHODOLOGY

    @server.resource("eibo://guide/language", name="language-guide", title="Approved language for people decisions",
                     mime_type="text/markdown")
    def language_guide() -> str:
        return LANGUAGE_GUIDE

    # ── Prompts ──────────────────────────────────────────────────────────
    @server.prompt(title="Prepare a retention conversation")
    def prepare_retention_conversation(employee_id: str) -> str:
        """For managers: prepare a supportive 1:1 with an employee whose retention needs attention."""
        return (
            f"Help me prepare a retention conversation with employee {employee_id}.\n"
            f"1. Call `employee_profile` for {employee_id}.\n"
            "2. Read `eibo://guide/language`.\n"
            "3. Draft: what this person contributes (impact percentile, skills, knowledge they hold), "
            "the likely retention driver, 3-5 open questions to understand their situation, and "
            "concrete options I could offer.\n"
            "Treat the risk score as a profile-level probability, not a verdict. Do not mention "
            "the score or the model to the employee."
        )

    @server.prompt(title="Review a budget scenario")
    def review_budget_scenario(budget_pct: str = "80") -> str:
        """For people analysts: review a budget scenario before it goes to decision-makers."""
        return (
            f"Review a {budget_pct}% budget scenario.\n"
            f"1. Call `compare_budget_scenarios` with [{budget_pct}, and two nearby levels].\n"
            f"2. Call `simulate_budget` at {budget_pct}% with leadership and critical-skills coverage on.\n"
            "3. Call `fairness_audit` and `knowledge_risks`.\n"
            "Summarize: what the plan suggests, what it gives up (coverage, top-impact people, knowledge "
            "held by a single person), fairness flags, and the questions decision-makers should answer. "
            "Use the language in `eibo://guide/language`."
        )

    @server.prompt(title="Team health check")
    def team_health_check(department: str) -> str:
        """For managers: a quick health check of one department."""
        return (
            f"Run a health check for the {department} department.\n"
            "Call `org_health`, then `retention_risks`, `knowledge_risks` and `succession_depth`, "
            f"each with department={department!r}. Report strengths, the three most important risks, and "
            "one concrete next step for each. Frame risks as retention and development opportunities."
        )

    return server
