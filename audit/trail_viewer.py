"""Audit Trail Viewer — queryable interface over the audit log.

Provides DataFrame views, summary statistics, and export helpers
for use in the admin UI.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from audit.logger import AuditEvent, AuditLogger, EventCategory, EventSeverity, get_audit_logger

# ---------------------------------------------------------------------------
# TrailViewer
# ---------------------------------------------------------------------------

class TrailViewer:
    """Provides structured views over the audit log for the admin panel."""

    def __init__(self, audit: AuditLogger | None = None) -> None:
        self._audit = audit or get_audit_logger()

    # ------------------------------------------------------------------
    # DataFrame builders
    # ------------------------------------------------------------------

    def events_df(
        self,
        category:   EventCategory | None = None,
        user_email: str | None = None,
        action:     str | None = None,
        outcome:    str | None = None,
        severity:   EventSeverity | None = None,
        hours_back: int | None = None,
        limit:      int = 500,
    ) -> pd.DataFrame:
        """Return filtered audit events as a DataFrame."""
        since = (datetime.utcnow() - timedelta(hours=hours_back)) if hours_back else None
        events = self._audit.query(
            category=category,
            user_email=user_email,
            action=action,
            outcome=outcome,
            severity=severity,
            since=since,
            limit=limit,
        )
        return self._to_df(events)

    def recent_df(self, n: int = 50) -> pd.DataFrame:
        return self._to_df(self._audit.recent(n))

    def _to_df(self, events: list[AuditEvent]) -> pd.DataFrame:
        if not events:
            return pd.DataFrame(columns=[
                "timestamp", "event_id", "category", "severity",
                "user_email", "user_role", "action", "resource", "detail", "outcome",
            ])
        rows = []
        for e in events:
            rows.append({
                "timestamp":   e.timestamp,
                "event_id":    e.event_id,
                "category":    e.category.value,
                "severity":    e.severity.value,
                "user_email":  e.user_email,
                "user_role":   e.user_role,
                "action":      e.action,
                "resource":    e.resource,
                "detail":      e.detail,
                "outcome":     e.outcome,
            })
        df = pd.DataFrame(rows)
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        return df.sort_values("timestamp", ascending=False).reset_index(drop=True)

    # ------------------------------------------------------------------
    # Summary statistics
    # ------------------------------------------------------------------

    def activity_by_user(self, hours_back: int = 24) -> pd.DataFrame:
        df = self.events_df(hours_back=hours_back, limit=5_000)
        if df.empty:
            return pd.DataFrame(columns=["user_email", "user_role", "event_count", "last_active"])
        grouped = (
            df.groupby(["user_email", "user_role"])
            .agg(event_count=("event_id", "count"), last_active=("timestamp", "max"))
            .reset_index()
            .sort_values("event_count", ascending=False)
        )
        return grouped

    def event_volume_by_hour(self, hours_back: int = 24) -> pd.DataFrame:
        df = self.events_df(hours_back=hours_back, limit=5_000)
        if df.empty:
            return pd.DataFrame(columns=["hour", "count"])
        df["hour"] = df["timestamp"].dt.floor("h")
        return (
            df.groupby("hour")
            .size()
            .rename("count")
            .reset_index()
            .sort_values("hour")
        )

    def failure_summary(self, hours_back: int = 24) -> pd.DataFrame:
        df = self.events_df(hours_back=hours_back, outcome="failure", limit=1_000)
        if df.empty:
            return pd.DataFrame(columns=["category", "action", "user_email", "count"])
        return (
            df.groupby(["category", "action", "user_email"])
            .size()
            .rename("count")
            .reset_index()
            .sort_values("count", ascending=False)
        )

    def security_events(self, hours_back: int = 72) -> pd.DataFrame:
        return self.events_df(
            category=EventCategory.SECURITY,
            hours_back=hours_back,
            limit=200,
        )

    def stats(self) -> dict:
        return self._audit.stats()

    def export_csv(self, hours_back: int | None = None) -> str:
        df = self.events_df(hours_back=hours_back, limit=10_000)
        return df.to_csv(index=False)

    def export_jsonl(self) -> str:
        return self._audit.export_jsonl()
