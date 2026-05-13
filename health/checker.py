"""Health checker — lightweight service health inspection for EIBO.

Returns structured health status for all platform components without
requiring a live database connection (gracefully degrades to DEGRADED).
"""

from __future__ import annotations

import importlib
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    HEALTHY   = "healthy"
    DEGRADED  = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """Health status of a single platform component."""
    name:        str
    status:      HealthStatus
    message:     str       = ""
    latency_ms:  float     = 0.0
    metadata:    dict      = field(default_factory=dict)

    @property
    def is_healthy(self) -> bool:
        return self.status == HealthStatus.HEALTHY

    def to_dict(self) -> dict:
        return {
            "name":       self.name,
            "status":     self.status.value,
            "message":    self.message,
            "latency_ms": round(self.latency_ms, 2),
            "metadata":   self.metadata,
        }


@dataclass
class HealthReport:
    """Aggregated health report across all components."""
    components:   list[ComponentHealth]
    generated_at: str

    @property
    def overall_status(self) -> HealthStatus:
        statuses = {c.status for c in self.components}
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        if HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY

    @property
    def is_healthy(self) -> bool:
        return self.overall_status == HealthStatus.HEALTHY

    def to_dict(self) -> dict:
        return {
            "overall_status": self.overall_status.value,
            "generated_at":   self.generated_at,
            "components":     [c.to_dict() for c in self.components],
            "summary": {
                "total":     len(self.components),
                "healthy":   sum(1 for c in self.components if c.status == HealthStatus.HEALTHY),
                "degraded":  sum(1 for c in self.components if c.status == HealthStatus.DEGRADED),
                "unhealthy": sum(1 for c in self.components if c.status == HealthStatus.UNHEALTHY),
            },
        }


# ---------------------------------------------------------------------------
# Individual component checkers
# ---------------------------------------------------------------------------

def _timed(fn: Callable[[], ComponentHealth]) -> ComponentHealth:
    """Run a check and attach wall-clock latency."""
    t0 = time.perf_counter()
    result = fn()
    result.latency_ms = (time.perf_counter() - t0) * 1000
    return result


def check_python_imports() -> ComponentHealth:
    """Verify that all required third-party packages are importable."""
    required = [
        "pandas", "numpy", "sklearn", "pulp", "networkx",
        "duckdb", "plotly", "httpx", "streamlit",
    ]
    missing = []
    for pkg in required:
        try:
            importlib.import_module(pkg)
        except ImportError:
            missing.append(pkg)

    if missing:
        return ComponentHealth(
            name="python_imports",
            status=HealthStatus.UNHEALTHY,
            message=f"Missing packages: {', '.join(missing)}",
        )
    return ComponentHealth(
        name="python_imports",
        status=HealthStatus.HEALTHY,
        message=f"All {len(required)} required packages importable",
        metadata={"packages_checked": required},
    )


def check_duckdb() -> ComponentHealth:
    """Verify DuckDB can execute an in-memory query."""
    try:
        import duckdb
        conn = duckdb.connect(":memory:")
        result = conn.execute("SELECT 42 AS n").fetchone()
        conn.close()
        if result and result[0] == 42:
            return ComponentHealth(
                name="duckdb",
                status=HealthStatus.HEALTHY,
                message="DuckDB in-memory query succeeded",
            )
        return ComponentHealth(name="duckdb", status=HealthStatus.DEGRADED,
                               message="Unexpected query result")
    except Exception as exc:
        return ComponentHealth(name="duckdb", status=HealthStatus.UNHEALTHY,
                               message=str(exc))


def check_ilp_solver() -> ComponentHealth:
    """Verify PuLP CBC solver is available."""
    try:
        import pulp
        prob = pulp.LpProblem("health_check", pulp.LpMaximize)
        x = pulp.LpVariable("x", lowBound=0, upBound=1)
        prob += x
        prob += x <= 1
        solver = pulp.PULP_CBC_CMD(msg=False)
        status = prob.solve(solver)
        if pulp.LpStatus[status] == "Optimal":
            return ComponentHealth(
                name="ilp_solver",
                status=HealthStatus.HEALTHY,
                message="PuLP CBC solver operational",
            )
        return ComponentHealth(name="ilp_solver", status=HealthStatus.DEGRADED,
                               message=f"Solver status: {pulp.LpStatus[status]}")
    except Exception as exc:
        return ComponentHealth(name="ilp_solver", status=HealthStatus.UNHEALTHY,
                               message=str(exc))


def check_notification_engine() -> ComponentHealth:
    """Verify notification engine singleton is accessible."""
    try:
        from notifications.engine import get_notification_engine
        engine = get_notification_engine()
        stats = engine.stats()
        return ComponentHealth(
            name="notification_engine",
            status=HealthStatus.HEALTHY,
            message="Notification engine operational",
            metadata={"total_notifications": stats.get("total", 0)},
        )
    except Exception as exc:
        return ComponentHealth(name="notification_engine", status=HealthStatus.UNHEALTHY,
                               message=str(exc))


def check_workflow_registry() -> ComponentHealth:
    """Verify the workflow registry has flows registered."""
    try:
        from workflows.engine import get_registry
        import workflows.data_pipeline_flow  # noqa: F401 — triggers registration
        import workflows.model_retraining_flow  # noqa: F401
        import workflows.report_generation_flow  # noqa: F401
        reg = get_registry()
        n_flows = len(reg.all_flows())
        if n_flows == 0:
            return ComponentHealth(name="workflow_registry", status=HealthStatus.DEGRADED,
                                   message="Registry has no registered flows")
        return ComponentHealth(
            name="workflow_registry",
            status=HealthStatus.HEALTHY,
            message=f"{n_flows} workflow(s) registered",
            metadata={"flow_names": [f.flow_name for f in reg.all_flows()]},
        )
    except Exception as exc:
        return ComponentHealth(name="workflow_registry", status=HealthStatus.UNHEALTHY,
                               message=str(exc))


def check_audit_logger() -> ComponentHealth:
    """Verify the audit logger singleton is initialised."""
    try:
        from audit.logger import get_audit_logger
        al = get_audit_logger()
        stats = al.stats()
        return ComponentHealth(
            name="audit_logger",
            status=HealthStatus.HEALTHY,
            message="Audit logger operational",
            metadata={"total_events": stats.get("total_events", 0)},
        )
    except Exception as exc:
        return ComponentHealth(name="audit_logger", status=HealthStatus.UNHEALTHY,
                               message=str(exc))


def check_environment_variables() -> ComponentHealth:
    """Check that required runtime environment variables are configured."""
    optional_production = [
        "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_HOST",
        "DUCKDB_PATH", "SECRET_KEY",
    ]
    missing = [v for v in optional_production if not os.getenv(v)]

    if len(missing) == len(optional_production):
        return ComponentHealth(
            name="environment_variables",
            status=HealthStatus.DEGRADED,
            message="Running in demo mode — no production env vars configured",
            metadata={"missing": missing},
        )
    if missing:
        return ComponentHealth(
            name="environment_variables",
            status=HealthStatus.DEGRADED,
            message=f"Partial configuration: {len(missing)} var(s) missing",
            metadata={"missing": missing},
        )
    return ComponentHealth(
        name="environment_variables",
        status=HealthStatus.HEALTHY,
        message="All production environment variables configured",
    )


def check_rbac() -> ComponentHealth:
    """Verify RBAC module loads and demo users are accessible."""
    try:
        from auth.rbac import DEMO_USERS, Role
        if not DEMO_USERS:
            return ComponentHealth(name="rbac", status=HealthStatus.DEGRADED,
                                   message="No demo users configured")
        roles_present = {u.role for u in DEMO_USERS}
        return ComponentHealth(
            name="rbac",
            status=HealthStatus.HEALTHY,
            message=f"RBAC operational — {len(DEMO_USERS)} demo users, {len(roles_present)} roles",
        )
    except Exception as exc:
        return ComponentHealth(name="rbac", status=HealthStatus.UNHEALTHY,
                               message=str(exc))


# ---------------------------------------------------------------------------
# Health checker orchestrator
# ---------------------------------------------------------------------------

_DEFAULT_CHECKS: list[Callable[[], ComponentHealth]] = [
    check_python_imports,
    check_duckdb,
    check_ilp_solver,
    check_notification_engine,
    check_workflow_registry,
    check_audit_logger,
    check_environment_variables,
    check_rbac,
]


class HealthChecker:
    """Run all registered component checks and return a HealthReport."""

    def __init__(self, checks: Optional[list[Callable[[], ComponentHealth]]] = None) -> None:
        self._checks = checks or _DEFAULT_CHECKS

    def run(self) -> HealthReport:
        from datetime import datetime
        components = []
        for check_fn in self._checks:
            try:
                component = _timed(check_fn)
            except Exception as exc:
                component = ComponentHealth(
                    name=getattr(check_fn, "__name__", "unknown"),
                    status=HealthStatus.UNHEALTHY,
                    message=f"Check crashed: {exc}",
                )
            components.append(component)
            logger.debug("Health check '%s': %s", component.name, component.status.value)

        return HealthReport(
            components=components,
            generated_at=datetime.utcnow().isoformat() + "Z",
        )

    def run_check(self, check_fn: Callable[[], ComponentHealth]) -> ComponentHealth:
        return _timed(check_fn)


def get_health_summary() -> dict:
    """Convenience function: run all checks and return a dict."""
    return HealthChecker().run().to_dict()
