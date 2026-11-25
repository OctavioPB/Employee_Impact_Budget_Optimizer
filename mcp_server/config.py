"""Server settings and the caller's identity, read from environment variables.

Each person runs their own MCP server process (stdio) with their own identity, so the
identity is configuration, not a login. For a shared HTTP deployment, put a real
identity provider in front of the server (see docs/MCP_SERVER.md).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from auth.rbac import DEMO_USERS_BY_EMAIL, DEMO_USERS_BY_ID, Role, User

_SCENARIOS = ("A", "B", "C")
_SIZES = ("small", "medium", "large")


class ConfigError(ValueError):
    """Raised when the server is started with an invalid or missing configuration."""


@dataclass(frozen=True)
class Settings:
    user: User
    default_scenario: str = "A"
    default_size: str = "small"
    # Employee names leave the machine only when explicitly allowed: the LLM on the other
    # end of the connection may be a hosted model, and EIBO's design principle is that
    # employee data stays inside the organization. IDs, roles and scores are always sent.
    share_names: bool = False
    audit_log_dir: str = field(default="audit_logs")


def _flag(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def user_from_env(env: dict[str, str]) -> User:
    """Resolve the caller.

    EIBO_MCP_USER   a demo user id or email (e.g. U004 / jordan@demo.eibo), or
    EIBO_MCP_ROLE   viewer | analyst | manager | director | executive | admin
    EIBO_MCP_DEPARTMENTS  comma-separated departments the role is scoped to
    EIBO_MCP_NAME / EIBO_MCP_EMAIL  optional display identity for the audit trail
    """
    ref = env.get("EIBO_MCP_USER", "").strip()
    if ref:
        user = DEMO_USERS_BY_ID.get(ref) or DEMO_USERS_BY_EMAIL.get(ref.lower())
        if user is None:
            raise ConfigError(f"EIBO_MCP_USER={ref!r} is not a known user id or email.")
        return user

    role_name = env.get("EIBO_MCP_ROLE", "").strip()
    if not role_name:
        raise ConfigError(
            "No identity configured. Set EIBO_MCP_USER (e.g. U004) or EIBO_MCP_ROLE "
            "(+ EIBO_MCP_DEPARTMENTS). See docs/MCP_SERVER.md."
        )
    try:
        role = Role.from_string(role_name)
    except ValueError as exc:
        raise ConfigError(str(exc)) from exc
    departments = [d.strip() for d in env.get("EIBO_MCP_DEPARTMENTS", "").split(",") if d.strip()]
    if role in (Role.VIEWER, Role.ANALYST, Role.MANAGER) and not departments:
        raise ConfigError(f"Role {role.label} is department-scoped: set EIBO_MCP_DEPARTMENTS.")
    return User(
        user_id=env.get("EIBO_MCP_USER_ID", "mcp-user"),
        full_name=env.get("EIBO_MCP_NAME", f"MCP {role.label}"),
        email=env.get("EIBO_MCP_EMAIL", "mcp-user@local"),
        role=role,
        departments=departments,
    )


def settings_from_env(env: dict[str, str] | None = None) -> Settings:
    env = dict(os.environ if env is None else env)
    scenario = env.get("EIBO_MCP_SCENARIO", "A").strip().upper()
    size = env.get("EIBO_MCP_SIZE", "small").strip().lower()
    if scenario not in _SCENARIOS:
        raise ConfigError(f"EIBO_MCP_SCENARIO must be one of {_SCENARIOS}.")
    if size not in _SIZES:
        raise ConfigError(f"EIBO_MCP_SIZE must be one of {_SIZES}.")
    return Settings(
        user=user_from_env(env),
        default_scenario=scenario,
        default_size=size,
        share_names=_flag(env.get("EIBO_MCP_SHARE_NAMES")),
        audit_log_dir=env.get("EIBO_MCP_AUDIT_DIR", "audit_logs"),
    )
