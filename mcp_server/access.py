"""What the caller may see: department scope, salary visibility and name redaction.

Built on auth/rbac.py so the MCP server enforces the same rules as the platform:
  - employee-level rows only for departments the role can access;
  - salaries exact, banded or hidden by role;
  - names per the role's PII tier, and never sent to the LLM unless share_names is on.
"""

from __future__ import annotations

from typing import Any

from auth.rbac import AccessControl, Permission
from mcp_server.config import Settings


class AccessDenied(PermissionError):
    pass


class Scope:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.user = settings.user
        self.ac = AccessControl(settings.user)

    # ── permissions ──────────────────────────────────────────────────────
    def require(self, permission: str, action: str) -> None:
        if not self.ac.can(permission):
            raise AccessDenied(
                f"Your role ({self.user.role.label}) cannot {action}. "
                f"Required permission: {permission}."
            )

    @property
    def org_wide(self) -> bool:
        return self.ac.can(Permission.ORG_WIDE_ACCESS) or self.ac.can(Permission.CROSS_DEPT_ACCESS)

    def can_see(self, department: str) -> bool:
        return self.org_wide or self.user.can_access_department(department)

    def check_department(self, department: str | None, known: list[str]) -> None:
        if department is None:
            return
        if department not in known:
            raise ValueError(f"Unknown department {department!r}. Known: {sorted(known)}")
        if not self.can_see(department):
            raise AccessDenied(
                f"Department {department!r} is outside your scope ({', '.join(self.user.departments) or 'none'})."
            )

    def visible_departments(self, known: list[str]) -> list[str]:
        return sorted(d for d in known if self.can_see(d))

    # ── redaction ────────────────────────────────────────────────────────
    def name(self, full_name: str, employee_id: str, role_title: str = "") -> str:
        """Display name sent to the LLM."""
        if self.settings.share_names and self.user.pii_visibility != "masked":
            return full_name
        label = role_title or "Employee"
        return f"{label} #{employee_id}"

    def salary(self, amount: float | int | None) -> Any:
        if amount is None:
            return None
        masked = self.ac.mask_salary(float(amount))
        return int(masked) if isinstance(masked, float) else masked

    @property
    def salary_visible(self) -> bool:
        return self.user.salary_visibility != "masked"

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.user.full_name,
            "role": self.user.role.label,
            "departments": "all" if self.org_wide else self.user.departments,
            "salary_visibility": self.user.salary_visibility,
            "employee_names": (
                "shared" if self.settings.share_names and self.user.pii_visibility != "masked"
                else "redacted (role title + employee ID)"
            ),
            "can_run_simulations": self.ac.can(Permission.RUN_SIMULATION),
            "can_use_overrides": self.ac.can(Permission.OVERRIDE_DECISION),
            "default_dataset": {
                "scenario": self.settings.default_scenario,
                "size": self.settings.default_size,
            },
        }
