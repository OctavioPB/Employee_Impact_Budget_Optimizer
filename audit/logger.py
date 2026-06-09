"""Audit Logger — structured event logging for EIBO compliance.

Captures all platform events: data access, simulations, overrides, exports,
configuration changes, and failed access attempts.

Events are stored in a rotating JSON-lines file and optionally in an
in-memory ring buffer for fast querying in the audit viewer.
"""

from __future__ import annotations

import json
import logging
import threading
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Event categories
# ---------------------------------------------------------------------------

class EventCategory(str, Enum):
    ACCESS          = "access"
    SIMULATION      = "simulation"
    OVERRIDE        = "override"
    EXPORT          = "export"
    AUTH            = "auth"
    ADMIN           = "admin"
    CONFIG          = "config"
    SECURITY        = "security"


class EventSeverity(str, Enum):
    INFO     = "info"
    WARNING  = "warning"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Audit event dataclass
# ---------------------------------------------------------------------------

@dataclass
class AuditEvent:
    """A single immutable audit log entry."""
    event_id:    str
    timestamp:   str                    # ISO 8601
    category:    EventCategory
    severity:    EventSeverity
    user_id:     str
    user_email:  str
    user_role:   str
    action:      str                    # e.g. "run_simulation"
    resource:    str                    # e.g. "budget_scenario_A"
    detail:      str                    # human-readable summary
    ip_address:  str = "local"
    session_id:  str = ""
    outcome:     str = "success"        # "success" | "failure" | "blocked"
    metadata:    dict = None            # extra key-value pairs

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> dict:
        d = asdict(self)
        d["category"] = self.category.value
        d["severity"] = self.severity.value
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


# ---------------------------------------------------------------------------
# Audit Logger singleton
# ---------------------------------------------------------------------------

class AuditLogger:
    """Thread-safe singleton audit logger.

    Writes JSON-lines to disk and maintains an in-memory ring buffer
    of the last `buffer_size` events for fast admin queries.
    """

    _instance: AuditLogger | None = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs) -> AuditLogger:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialised = False
        return cls._instance

    def __init__(
        self,
        log_dir: str | Path = "audit_logs",
        buffer_size: int = 5_000,
    ) -> None:
        if self._initialised:
            return
        self._log_dir    = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._log_file   = self._log_dir / "audit.jsonl"
        self._buffer: deque[AuditEvent] = deque(maxlen=buffer_size)
        self._counter    = 0
        self._write_lock = threading.Lock()
        self._initialised = True

    def log(
        self,
        category:   EventCategory,
        action:     str,
        resource:   str,
        detail:     str,
        user_id:    str = "system",
        user_email: str = "system",
        user_role:  str = "system",
        severity:   EventSeverity = EventSeverity.INFO,
        outcome:    str = "success",
        session_id: str = "",
        metadata:   dict | None = None,
    ) -> AuditEvent:
        """Write an audit event to disk and buffer."""
        with self._write_lock:
            self._counter += 1
            event = AuditEvent(
                event_id   = f"EVT-{self._counter:08d}",
                timestamp  = datetime.utcnow().isoformat() + "Z",
                category   = category,
                severity   = severity,
                user_id    = user_id,
                user_email = user_email,
                user_role  = user_role,
                action     = action,
                resource   = resource,
                detail     = detail,
                outcome    = outcome,
                session_id = session_id,
                metadata   = metadata or {},
            )
            self._buffer.append(event)
            try:
                with open(self._log_file, "a", encoding="utf-8") as fh:
                    fh.write(event.to_json() + "\n")
            except OSError as e:
                logger.error("Failed to write audit event to disk: %s", e)
            return event

    # ------------------------------------------------------------------
    # Query API
    # ------------------------------------------------------------------

    def query(
        self,
        category:   EventCategory | None = None,
        user_id:    str | None = None,
        user_email: str | None = None,
        action:     str | None = None,
        outcome:    str | None = None,
        severity:   EventSeverity | None = None,
        since:      datetime | None = None,
        until:      datetime | None = None,
        limit:      int = 500,
    ) -> list[AuditEvent]:
        """Query the in-memory buffer. Disk fallback not needed for Streamlit demos."""
        results = []
        for event in reversed(self._buffer):
            if category   and event.category   != category:   continue
            if user_id    and event.user_id     != user_id:    continue
            if user_email and event.user_email  != user_email: continue
            if action     and action.lower() not in event.action.lower(): continue
            if outcome    and event.outcome     != outcome:    continue
            if severity   and event.severity    != severity:   continue
            if since:
                ev_ts = datetime.fromisoformat(event.timestamp.rstrip("Z"))
                if ev_ts < since:
                    continue
            if until:
                ev_ts = datetime.fromisoformat(event.timestamp.rstrip("Z"))
                if ev_ts > until:
                    continue
            results.append(event)
            if len(results) >= limit:
                break
        return results

    def recent(self, n: int = 100) -> list[AuditEvent]:
        return list(reversed(list(self._buffer)))[:n]

    def stats(self) -> dict:
        events = list(self._buffer)
        by_category: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        failures = 0
        for e in events:
            by_category[e.category.value] = by_category.get(e.category.value, 0) + 1
            by_severity[e.severity.value] = by_severity.get(e.severity.value, 0) + 1
            if e.outcome != "success":
                failures += 1
        return {
            "total_events":    len(events),
            "by_category":     by_category,
            "by_severity":     by_severity,
            "failure_count":   failures,
            "buffer_capacity": self._buffer.maxlen,
        }

    def export_jsonl(self) -> str:
        """Return all buffered events as a JSON-lines string."""
        return "\n".join(e.to_json() for e in self._buffer)


# ---------------------------------------------------------------------------
# Module-level singleton + convenience functions
# ---------------------------------------------------------------------------

_audit: AuditLogger | None = None


def get_audit_logger(log_dir: str | Path = "audit_logs") -> AuditLogger:
    """Return (and initialise if needed) the module-level AuditLogger singleton."""
    global _audit
    if _audit is None:
        _audit = AuditLogger(log_dir=log_dir)
    return _audit


def log_access(
    user_id: str, user_email: str, user_role: str,
    resource: str, detail: str,
    outcome: str = "success", session_id: str = "",
) -> AuditEvent:
    return get_audit_logger().log(
        category=EventCategory.ACCESS, action="view",
        resource=resource, detail=detail,
        user_id=user_id, user_email=user_email, user_role=user_role,
        outcome=outcome, session_id=session_id,
    )


def log_simulation(
    user_id: str, user_email: str, user_role: str,
    resource: str, detail: str, metadata: dict | None = None,
) -> AuditEvent:
    return get_audit_logger().log(
        category=EventCategory.SIMULATION, action="run_simulation",
        resource=resource, detail=detail,
        user_id=user_id, user_email=user_email, user_role=user_role,
        metadata=metadata,
    )


def log_override(
    user_id: str, user_email: str, user_role: str,
    resource: str, detail: str, metadata: dict | None = None,
) -> AuditEvent:
    return get_audit_logger().log(
        category=EventCategory.OVERRIDE, action="override_decision",
        resource=resource, detail=detail,
        severity=EventSeverity.WARNING,
        user_id=user_id, user_email=user_email, user_role=user_role,
        metadata=metadata,
    )


def log_export(
    user_id: str, user_email: str, user_role: str,
    resource: str, detail: str,
) -> AuditEvent:
    return get_audit_logger().log(
        category=EventCategory.EXPORT, action="export",
        resource=resource, detail=detail,
        user_id=user_id, user_email=user_email, user_role=user_role,
    )


def log_auth(
    user_email: str, action: str, outcome: str = "success",
) -> AuditEvent:
    return get_audit_logger().log(
        category=EventCategory.AUTH, action=action,
        resource="authentication", detail=f"{action} for {user_email}",
        user_id="system", user_email=user_email, user_role="unknown",
        outcome=outcome,
        severity=EventSeverity.WARNING if outcome != "success" else EventSeverity.INFO,
    )


def log_security(
    user_id: str, user_email: str, user_role: str,
    action: str, resource: str, detail: str,
) -> AuditEvent:
    return get_audit_logger().log(
        category=EventCategory.SECURITY, action=action,
        resource=resource, detail=detail,
        user_id=user_id, user_email=user_email, user_role=user_role,
        severity=EventSeverity.CRITICAL, outcome="blocked",
    )


def log_admin(
    user_id: str, user_email: str, user_role: str,
    action: str, resource: str, detail: str,
) -> AuditEvent:
    return get_audit_logger().log(
        category=EventCategory.ADMIN, action=action,
        resource=resource, detail=detail,
        user_id=user_id, user_email=user_email, user_role=user_role,
        severity=EventSeverity.WARNING,
    )
