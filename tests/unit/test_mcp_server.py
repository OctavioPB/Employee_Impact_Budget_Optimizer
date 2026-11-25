"""EIBO MCP server: tools, RBAC scoping, redaction, language, audit and transports."""

import asyncio
import json
import os
import sys
from pathlib import Path

import pytest
from mcp.client import Client
from starlette.testclient import TestClient

from mcp_server.__main__ import BearerTokenMiddleware
from mcp_server.config import ConfigError, settings_from_env
from mcp_server.server import build_server

REPO = Path(__file__).resolve().parents[2]
_BANNED = ("terminat", "fired", "layoff", "laid off", "eliminat")


def _call(env: dict, tool: str, args: dict | None = None, tmp_path: Path | None = None):
    env = {**env, "EIBO_MCP_AUDIT_DIR": str(tmp_path or REPO / "audit_logs")}

    async def go():
        async with Client(build_server(settings_from_env(env))) as c:
            return await c.call_tool(tool, args or {})

    return asyncio.run(go())


def _text(result) -> str:
    return " ".join(getattr(b, "text", "") for b in result.content)


MANAGER = {"EIBO_MCP_USER": "U004"}     # Jordan Lee, Manager, Engineering
ANALYST = {"EIBO_MCP_USER": "U005"}     # Casey Patel, Analyst, Engineering + Analytics
VIEWER = {"EIBO_MCP_USER": "U006"}      # Robin Zhao, Viewer, Operations
EXECUTIVE = {"EIBO_MCP_USER": "U002"}   # Morgan Chen, Executive, org-wide


# ── configuration ────────────────────────────────────────────────────────────

def test_identity_is_required():
    with pytest.raises(ConfigError):
        settings_from_env({})


def test_department_scoped_roles_need_departments():
    with pytest.raises(ConfigError):
        settings_from_env({"EIBO_MCP_ROLE": "manager"})
    s = settings_from_env({"EIBO_MCP_ROLE": "manager", "EIBO_MCP_DEPARTMENTS": "Sales, Marketing"})
    assert s.user.departments == ["Sales", "Marketing"]


def test_unknown_user_is_rejected():
    with pytest.raises(ConfigError):
        settings_from_env({"EIBO_MCP_USER": "nobody"})


# ── discovery ────────────────────────────────────────────────────────────────

def test_all_tools_are_read_only_and_structured():
    async def go():
        async with Client(build_server(settings_from_env(MANAGER))) as c:
            return (await c.list_tools()).tools, (await c.list_resources()).resources, (await c.list_prompts()).prompts

    tools, resources, prompts = asyncio.run(go())
    assert len(tools) >= 10
    for t in tools:
        assert t.annotations.read_only_hint is True, t.name
        assert t.annotations.destructive_hint is False, t.name
        assert t.output_schema, t.name
        assert t.description, t.name
    assert {str(r.uri) for r in resources} == {"eibo://guide/methodology", "eibo://guide/language"}
    assert {p.name for p in prompts} == {"prepare_retention_conversation", "review_budget_scenario", "team_health_check"}


# ── scoping ──────────────────────────────────────────────────────────────────

def test_manager_sees_only_own_department(tmp_path):
    r = _call(MANAGER, "list_employees", {"limit": 100}, tmp_path)
    assert not r.is_error
    assert {e["department"] for e in r.structured_content["employees"]} == {"Engineering"}


def test_out_of_scope_department_is_denied(tmp_path):
    r = _call(MANAGER, "list_employees", {"department": "Sales"}, tmp_path)
    assert r.is_error and "outside your scope" in _text(r)


def test_out_of_scope_employee_profile_is_denied(tmp_path):
    sales = _call(EXECUTIVE, "list_employees", {"department": "Sales", "limit": 1}, tmp_path)
    eid = sales.structured_content["employees"][0]["employee_id"]
    r = _call(MANAGER, "employee_profile", {"employee_id": eid}, tmp_path)
    assert r.is_error and "outside your scope" in _text(r)


def test_executive_sees_whole_org(tmp_path):
    r = _call(EXECUTIVE, "org_overview", {}, tmp_path)
    assert r.structured_content["departments_outside_scope"] == 0


# ── masking ──────────────────────────────────────────────────────────────────

def test_salary_masking_follows_role(tmp_path):
    mgr = _call(MANAGER, "list_employees", {"limit": 1}, tmp_path).structured_content["employees"][0]
    ana = _call(ANALYST, "list_employees", {"limit": 1}, tmp_path).structured_content["employees"][0]
    vie = _call(VIEWER, "list_employees", {"limit": 1}, tmp_path).structured_content["employees"][0]
    assert isinstance(mgr["annual_salary"], int)
    assert isinstance(ana["annual_salary"], str) and "–" in ana["annual_salary"]   # band
    assert "annual_salary" not in vie and "attrition_risk" not in vie


def test_names_redacted_by_default_and_opt_in(tmp_path):
    default = _call(MANAGER, "list_employees", {"limit": 1}, tmp_path).structured_content["employees"][0]
    assert default["name"].endswith(f"#{default['employee_id']}")
    shared = _call({**MANAGER, "EIBO_MCP_SHARE_NAMES": "1"}, "list_employees", {"limit": 1}, tmp_path)
    assert "#" not in shared.structured_content["employees"][0]["name"]
    viewer = _call({**VIEWER, "EIBO_MCP_SHARE_NAMES": "1"}, "list_employees", {"limit": 1}, tmp_path)
    assert viewer.structured_content["employees"][0]["name"].endswith("#" + viewer.structured_content["employees"][0]["employee_id"])


def test_names_inside_other_outputs_are_redacted(tmp_path):
    r = _call(EXECUTIVE, "succession_depth", {}, tmp_path).structured_content
    names = [r_["leader"] for r_ in r["leaders"]] + [n for r_ in r["leaders"] for i in (1, 2, 3) for n in r_[f"depth_{i}"]]
    assert names and all("#" in n for n in names)


# ── permissions ──────────────────────────────────────────────────────────────

def test_viewer_cannot_simulate(tmp_path):
    r = _call(VIEWER, "simulate_budget", {"budget_pct": 80}, tmp_path)
    assert r.is_error and "cannot run simulations" in _text(r)


def test_analyst_cannot_use_overrides(tmp_path):
    r = _call(ANALYST, "simulate_budget", {"budget_pct": 80, "force_retain": ["5AC236BE"]}, tmp_path)
    assert r.is_error and "override" in _text(r)


def test_viewer_cannot_see_pay_equity(tmp_path):
    assert _call(VIEWER, "pay_equity", {}, tmp_path).is_error


# ── content ──────────────────────────────────────────────────────────────────

def test_simulation_uses_approved_language(tmp_path):
    r = _call(MANAGER, "simulate_budget", {"budget_pct": 70}, tmp_path)
    assert not r.is_error
    body = json.dumps(r.structured_content).lower()
    assert "not_retained_in_simulation" in body and "suggestion" in body
    assert not any(word in body for word in _BANNED)
    assert set(r.structured_content["your_departments"]) == {"Engineering"}


def test_compare_budget_scenarios(tmp_path):
    rows = _call(ANALYST, "compare_budget_scenarios", {"budget_pcts": [70, 90]}, tmp_path).structured_content["scenarios"]
    assert [r["budget_pct"] for r in rows] == [70, 90]
    assert rows[0]["suggested_retention_count"] <= rows[1]["suggested_retention_count"]


@pytest.mark.parametrize("tool,args", [
    ("org_health", {}), ("knowledge_risks", {}), ("retention_risks", {"min_risk_band": "Moderate"}),
    ("resilience_stress_test", {"scenario_type": "targeted_departure", "n": 3}), ("fairness_audit", {}),
    ("pay_equity", {}), ("whoami", {}),
])
def test_tools_run_for_a_manager(tool, args, tmp_path):
    r = _call(MANAGER, tool, args, tmp_path)
    assert not r.is_error, _text(r)
    assert r.structured_content


def test_profile_includes_context(tmp_path):
    eid = _call(MANAGER, "list_employees", {"limit": 1}, tmp_path).structured_content["employees"][0]["employee_id"]
    p = _call(MANAGER, "employee_profile", {"employee_id": eid.lower()}, tmp_path).structured_content
    assert p["employee_id"] == eid and "retention_driver" in p and "knowledge" in p and "pay_position" in p


def test_every_call_is_audited(tmp_path):
    from audit.logger import EventCategory, get_audit_logger

    _call(MANAGER, "simulate_budget", {"budget_pct": 80}, tmp_path)
    # The audit logger is a per-process singleton: query it rather than a specific file
    last = get_audit_logger().recent(1)[0]
    assert last.action == "mcp:simulate_budget"
    assert last.user_email == "jordan@demo.eibo"
    assert last.category == EventCategory.SIMULATION


# ── transports ───────────────────────────────────────────────────────────────

def test_http_requires_bearer_token():
    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    client = TestClient(BearerTokenMiddleware(app, "x" * 40))
    assert client.get("/mcp").status_code == 401
    assert client.get("/mcp", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert client.get("/mcp", headers={"Authorization": "Bearer " + "x" * 40}).status_code == 200


def test_stdio_end_to_end():
    from mcp import StdioServerParameters

    params = StdioServerParameters(
        command=sys.executable, args=["-m", "mcp_server"], cwd=str(REPO),
        env={**os.environ, "EIBO_MCP_USER": "U004", "EIBO_MCP_AUDIT_DIR": str(REPO / "audit_logs")},
    )

    async def go():
        async with Client(params) as c:
            return await c.call_tool("whoami", {})

    r = asyncio.run(go())
    assert not r.is_error and r.structured_content["role"] == "Manager"


def test_http_mode_refuses_to_start_without_a_strong_token(monkeypatch, capsys):
    from mcp_server.__main__ import main

    monkeypatch.setenv("EIBO_MCP_USER", "U004")
    monkeypatch.delenv("EIBO_MCP_TOKEN", raising=False)
    assert main(["--transport", "http"]) == 2
    monkeypatch.setenv("EIBO_MCP_TOKEN", "short")
    assert main(["--transport", "http"]) == 2
    assert "EIBO_MCP_TOKEN" in capsys.readouterr().err


def test_missing_identity_exits_with_config_error(monkeypatch, capsys):
    from mcp_server.__main__ import main

    for var in ("EIBO_MCP_USER", "EIBO_MCP_ROLE"):
        monkeypatch.delenv(var, raising=False)
    assert main([]) == 2
    assert "configuration error" in capsys.readouterr().err
