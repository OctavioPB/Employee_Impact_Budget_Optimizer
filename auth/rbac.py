"""Role-Based Access Control (RBAC) — 6-tier permission model for EIBO.

Role hierarchy (lowest to highest):
  Viewer → Analyst → Manager → Director → Executive → Admin

Data-level isolation enforced via department scope and PII tiers.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Role definitions
# ---------------------------------------------------------------------------

class Role(IntEnum):
    """Ordered role levels — higher value = more access."""
    VIEWER    = 1
    ANALYST   = 2
    MANAGER   = 3
    DIRECTOR  = 4
    EXECUTIVE = 5
    ADMIN     = 6

    @property
    def label(self) -> str:
        return self.name.title()

    @property
    def description(self) -> str:
        return _ROLE_DESCRIPTIONS[self]

    @classmethod
    def from_string(cls, s: str) -> "Role":
        try:
            return cls[s.upper()]
        except KeyError:
            raise ValueError(f"Unknown role: {s!r}. Valid roles: {[r.name for r in cls]}")


_ROLE_DESCRIPTIONS: dict[Role, str] = {
    Role.VIEWER:    "Read-only access to dashboards. Cannot run simulations.",
    Role.ANALYST:   "Run simulations and create scenarios. Cannot make final decisions.",
    Role.MANAGER:   "Full access to own department(s). Can run simulations and override.",
    Role.DIRECTOR:  "Multi-department access. Includes strategic planning features.",
    Role.EXECUTIVE: "Organisation-wide access to all features except system administration.",
    Role.ADMIN:     "System configuration, user management, and full audit access.",
}


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------

class Permission:
    """All permission constants used throughout the platform."""
    # Dashboard
    VIEW_DASHBOARD      = "view_dashboard"
    VIEW_EMPLOYEE_LIST  = "view_employee_list"

    # Salary visibility
    VIEW_SALARY_FULL    = "view_salary_full"      # exact figures
    VIEW_SALARY_RANGE   = "view_salary_range"     # band/range only
    VIEW_SALARY_MASKED  = "view_salary_masked"    # no salary data

    # PII
    VIEW_PII_FULL       = "view_pii_full"         # name + all details
    VIEW_PII_PARTIAL    = "view_pii_partial"      # name + role only
    VIEW_PII_MASKED     = "view_pii_masked"       # anonymised IDs

    # Simulation
    RUN_SIMULATION      = "run_simulation"
    SAVE_SCENARIO       = "save_scenario"
    EXPORT_RESULTS      = "export_results"

    # Overrides
    OVERRIDE_DECISION   = "override_decision"
    ANNOTATE_DECISION   = "annotate_decision"

    # Strategic planning
    VIEW_STRATEGIC      = "view_strategic"
    EDIT_STRATEGIC      = "edit_strategic"

    # Predictive
    VIEW_PREDICTIVE     = "view_predictive"

    # Admin
    MANAGE_USERS        = "manage_users"
    VIEW_AUDIT_LOG      = "view_audit_log"
    EXPORT_AUDIT_LOG    = "export_audit_log"
    MANAGE_CONFIG       = "manage_config"
    VIEW_HEALTH         = "view_health"

    # Data scope
    CROSS_DEPT_ACCESS   = "cross_dept_access"
    ORG_WIDE_ACCESS     = "org_wide_access"


# ---------------------------------------------------------------------------
# Role → Permission mapping
# ---------------------------------------------------------------------------

_ROLE_PERMISSIONS: dict[Role, set[str]] = {
    Role.VIEWER: {
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_EMPLOYEE_LIST,
        Permission.VIEW_SALARY_MASKED,
        Permission.VIEW_PII_MASKED,
    },
    Role.ANALYST: {
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_EMPLOYEE_LIST,
        Permission.VIEW_SALARY_RANGE,
        Permission.VIEW_PII_PARTIAL,
        Permission.RUN_SIMULATION,
        Permission.SAVE_SCENARIO,
        Permission.EXPORT_RESULTS,
        Permission.VIEW_PREDICTIVE,
        Permission.VIEW_STRATEGIC,
    },
    Role.MANAGER: {
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_EMPLOYEE_LIST,
        Permission.VIEW_SALARY_FULL,
        Permission.VIEW_PII_FULL,
        Permission.RUN_SIMULATION,
        Permission.SAVE_SCENARIO,
        Permission.EXPORT_RESULTS,
        Permission.OVERRIDE_DECISION,
        Permission.ANNOTATE_DECISION,
        Permission.VIEW_PREDICTIVE,
        Permission.VIEW_STRATEGIC,
        Permission.EDIT_STRATEGIC,
    },
    Role.DIRECTOR: {
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_EMPLOYEE_LIST,
        Permission.VIEW_SALARY_FULL,
        Permission.VIEW_PII_FULL,
        Permission.RUN_SIMULATION,
        Permission.SAVE_SCENARIO,
        Permission.EXPORT_RESULTS,
        Permission.OVERRIDE_DECISION,
        Permission.ANNOTATE_DECISION,
        Permission.VIEW_PREDICTIVE,
        Permission.VIEW_STRATEGIC,
        Permission.EDIT_STRATEGIC,
        Permission.CROSS_DEPT_ACCESS,
        Permission.VIEW_HEALTH,
    },
    Role.EXECUTIVE: {
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_EMPLOYEE_LIST,
        Permission.VIEW_SALARY_FULL,
        Permission.VIEW_PII_FULL,
        Permission.RUN_SIMULATION,
        Permission.SAVE_SCENARIO,
        Permission.EXPORT_RESULTS,
        Permission.OVERRIDE_DECISION,
        Permission.ANNOTATE_DECISION,
        Permission.VIEW_PREDICTIVE,
        Permission.VIEW_STRATEGIC,
        Permission.EDIT_STRATEGIC,
        Permission.CROSS_DEPT_ACCESS,
        Permission.ORG_WIDE_ACCESS,
        Permission.VIEW_HEALTH,
        Permission.VIEW_AUDIT_LOG,
    },
    Role.ADMIN: {
        # Admin inherits all permissions
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_EMPLOYEE_LIST,
        Permission.VIEW_SALARY_FULL,
        Permission.VIEW_PII_FULL,
        Permission.RUN_SIMULATION,
        Permission.SAVE_SCENARIO,
        Permission.EXPORT_RESULTS,
        Permission.OVERRIDE_DECISION,
        Permission.ANNOTATE_DECISION,
        Permission.VIEW_PREDICTIVE,
        Permission.VIEW_STRATEGIC,
        Permission.EDIT_STRATEGIC,
        Permission.CROSS_DEPT_ACCESS,
        Permission.ORG_WIDE_ACCESS,
        Permission.MANAGE_USERS,
        Permission.VIEW_AUDIT_LOG,
        Permission.EXPORT_AUDIT_LOG,
        Permission.MANAGE_CONFIG,
        Permission.VIEW_HEALTH,
    },
}


# ---------------------------------------------------------------------------
# User dataclass
# ---------------------------------------------------------------------------

@dataclass
class User:
    """Represents an authenticated platform user."""
    user_id: str
    full_name: str
    email: str
    role: Role
    departments: list[str] = field(default_factory=list)  # scoped departments
    is_active: bool = True

    def has_permission(self, permission: str) -> bool:
        return permission in _ROLE_PERMISSIONS.get(self.role, set())

    def can_access_department(self, dept: str) -> bool:
        if self.has_permission(Permission.ORG_WIDE_ACCESS):
            return True
        if self.has_permission(Permission.CROSS_DEPT_ACCESS):
            return True
        return dept in self.departments

    @property
    def salary_visibility(self) -> str:
        if self.has_permission(Permission.VIEW_SALARY_FULL):
            return "full"
        if self.has_permission(Permission.VIEW_SALARY_RANGE):
            return "range"
        return "masked"

    @property
    def pii_visibility(self) -> str:
        if self.has_permission(Permission.VIEW_PII_FULL):
            return "full"
        if self.has_permission(Permission.VIEW_PII_PARTIAL):
            return "partial"
        return "masked"


# ---------------------------------------------------------------------------
# Permission checker (convenience API)
# ---------------------------------------------------------------------------

class AccessControl:
    """Stateless permission checker.

    Usage:
        ac = AccessControl(current_user)
        if ac.can(Permission.RUN_SIMULATION):
            ...
        filtered_df = ac.filter_employees(employees_df)
    """

    def __init__(self, user: User) -> None:
        self._user = user

    def can(self, permission: str) -> bool:
        return self._user.has_permission(permission)

    def require(self, permission: str) -> None:
        """Raise PermissionError if user lacks the permission."""
        if not self.can(permission):
            raise PermissionError(
                f"User {self._user.email!r} (role={self._user.role.label}) "
                f"does not have permission: {permission!r}"
            )

    def filter_departments(self, departments: list[str]) -> list[str]:
        """Return only departments the user may access."""
        if self.can(Permission.ORG_WIDE_ACCESS) or self.can(Permission.CROSS_DEPT_ACCESS):
            return departments
        return [d for d in departments if self._user.can_access_department(d)]

    def mask_salary(self, salary: float) -> str | float:
        vis = self._user.salary_visibility
        if vis == "full":
            return salary
        if vis == "range":
            band = (int(salary) // 20_000) * 20_000
            return f"${band:,}–${band + 20_000:,}"
        return "***"

    def mask_pii(self, name: str, employee_id: str) -> str:
        if self._user.pii_visibility == "masked":
            return f"EMP-{employee_id[-4:]}"
        return name

    @property
    def user(self) -> User:
        return self._user


# ---------------------------------------------------------------------------
# Demo user registry (for Streamlit demo mode)
# ---------------------------------------------------------------------------

DEMO_USERS: list[User] = [
    User("U001", "Alex Rivera",    "alex@demo.eibo",      Role.ADMIN,
         departments=[], is_active=True),
    User("U002", "Morgan Chen",    "morgan@demo.eibo",    Role.EXECUTIVE,
         departments=[], is_active=True),
    User("U003", "Sam Thompson",   "sam@demo.eibo",       Role.DIRECTOR,
         departments=["Engineering", "Product"], is_active=True),
    User("U004", "Jordan Lee",     "jordan@demo.eibo",    Role.MANAGER,
         departments=["Engineering"], is_active=True),
    User("U005", "Casey Patel",    "casey@demo.eibo",     Role.ANALYST,
         departments=["Engineering", "Analytics"], is_active=True),
    User("U006", "Robin Zhao",     "robin@demo.eibo",     Role.VIEWER,
         departments=["Operations"], is_active=True),
]

DEMO_USERS_BY_ID: dict[str, User] = {u.user_id: u for u in DEMO_USERS}
DEMO_USERS_BY_EMAIL: dict[str, User] = {u.email: u for u in DEMO_USERS}


def get_demo_user(role: Role = Role.ADMIN) -> User:
    """Return the first demo user with the given role."""
    for u in DEMO_USERS:
        if u.role == role:
            return u
    return DEMO_USERS[0]
