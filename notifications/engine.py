"""Notification Engine — intelligent alerting with smart bundling and multi-channel dispatch.

Manages notification lifecycle: creation → routing → delivery → deduplication.
Supports in-app, email, and webhook channels with per-user preferences.
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from uuid import uuid4

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class NotificationType(str, Enum):
    RISK_ALERT        = "risk_alert"
    WORKFLOW_STATUS   = "workflow_status"
    COLLABORATION     = "collaboration"
    SYSTEM            = "system"
    MODEL_DRIFT       = "model_drift"
    BUDGET_ALERT      = "budget_alert"
    ATTRITION_ALERT   = "attrition_alert"


class NotificationPriority(str, Enum):
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"


class NotificationChannel(str, Enum):
    IN_APP  = "in_app"
    EMAIL   = "email"
    WEBHOOK = "webhook"


class DeliveryStatus(str, Enum):
    PENDING   = "pending"
    DELIVERED = "delivered"
    FAILED    = "failed"
    BUNDLED   = "bundled"   # absorbed into a digest bundle
    READ      = "read"


# ---------------------------------------------------------------------------
# Notification dataclass
# ---------------------------------------------------------------------------

@dataclass
class Notification:
    """A single platform notification."""
    notification_id: str
    notification_type: NotificationType
    priority:          NotificationPriority
    title:             str
    body:              str
    source:            str              # e.g. "early_warning", "workflow_engine"
    created_at:        datetime
    target_user_ids:   list[str]        # empty = broadcast to all
    channel:           NotificationChannel = NotificationChannel.IN_APP
    status:            DeliveryStatus  = DeliveryStatus.PENDING
    read_by:           set[str]        = field(default_factory=set)
    metadata:          dict            = field(default_factory=dict)
    bundle_key:        str             = ""   # used by bundler to group related alerts

    def mark_read(self, user_id: str) -> None:
        self.read_by.add(user_id)
        if set(self.target_user_ids) - self.read_by == set():
            self.status = DeliveryStatus.READ

    def is_read_by(self, user_id: str) -> bool:
        return user_id in self.read_by

    def to_dict(self) -> dict:
        return {
            "notification_id":   self.notification_id,
            "notification_type": self.notification_type.value,
            "priority":          self.priority.value,
            "title":             self.title,
            "body":              self.body,
            "source":            self.source,
            "created_at":        self.created_at.isoformat(),
            "channel":           self.channel.value,
            "status":            self.status.value,
        }


@dataclass
class NotificationBundle:
    """A digest bundle grouping multiple related notifications."""
    bundle_id:    str
    bundle_key:   str
    notifications: list[Notification]
    created_at:   datetime
    title:        str = ""
    summary:      str = ""

    def __post_init__(self) -> None:
        if not self.title:
            self.title = f"{len(self.notifications)} alerts bundled"
        if not self.summary:
            types = {n.notification_type.value for n in self.notifications}
            self.summary = f"Types: {', '.join(sorted(types))}"


# ---------------------------------------------------------------------------
# User notification preferences
# ---------------------------------------------------------------------------

@dataclass
class NotificationPreferences:
    """Per-user channel and frequency preferences."""
    user_id:           str
    channels:          set[NotificationChannel] = field(
        default_factory=lambda: {NotificationChannel.IN_APP}
    )
    # Per-type frequency: "immediate" | "hourly" | "daily" | "disabled"
    type_frequencies:  dict[str, str] = field(default_factory=dict)
    do_not_disturb:    bool           = False
    dnd_start_hour:    int            = 22
    dnd_end_hour:      int            = 8
    bundle_window_min: int            = 15   # bundle alerts within this window

    def frequency_for(self, ntype: NotificationType) -> str:
        return self.type_frequencies.get(ntype.value, "immediate")

    def is_dnd_active(self) -> bool:
        if not self.do_not_disturb:
            return False
        now_h = datetime.utcnow().hour
        if self.dnd_start_hour > self.dnd_end_hour:
            return now_h >= self.dnd_start_hour or now_h < self.dnd_end_hour
        return self.dnd_start_hour <= now_h < self.dnd_end_hour


# ---------------------------------------------------------------------------
# In-memory notification store
# ---------------------------------------------------------------------------

class NotificationStore:
    """Thread-safe in-memory notification store with ring-buffer semantics."""

    def __init__(self, max_size: int = 1_000) -> None:
        self._lock    = threading.Lock()
        self._store:  dict[str, Notification] = {}
        self._order:  list[str] = []          # insertion order
        self._max     = max_size

    def add(self, n: Notification) -> None:
        with self._lock:
            if n.notification_id in self._store:
                return
            if len(self._order) >= self._max:
                oldest = self._order.pop(0)
                del self._store[oldest]
            self._store[n.notification_id] = n
            self._order.append(n.notification_id)

    def get(self, notification_id: str) -> Notification | None:
        return self._store.get(notification_id)

    def for_user(
        self,
        user_id:      str,
        unread_only:  bool = False,
        ntype:        NotificationType | None = None,
        priority:     NotificationPriority | None = None,
        limit:        int = 100,
    ) -> list[Notification]:
        results = []
        for nid in reversed(self._order):
            n = self._store[nid]
            # Targeting: empty target_user_ids = broadcast
            if n.target_user_ids and user_id not in n.target_user_ids:
                continue
            if unread_only and n.is_read_by(user_id):
                continue
            if ntype and n.notification_type != ntype:
                continue
            if priority and n.priority != priority:
                continue
            if n.status == DeliveryStatus.BUNDLED:
                continue
            results.append(n)
            if len(results) >= limit:
                break
        return results

    def unread_count(self, user_id: str) -> int:
        return sum(
            1 for nid in self._order
            if not self._store[nid].is_read_by(user_id)
            and (not self._store[nid].target_user_ids
                 or user_id in self._store[nid].target_user_ids)
            and self._store[nid].status not in (DeliveryStatus.BUNDLED, DeliveryStatus.READ)
        )

    def mark_all_read(self, user_id: str) -> int:
        count = 0
        for nid in self._order:
            n = self._store[nid]
            if not n.is_read_by(user_id):
                n.mark_read(user_id)
                count += 1
        return count

    def all_notifications(self, limit: int = 500) -> list[Notification]:
        return [self._store[nid] for nid in reversed(self._order)][:limit]

    def stats(self) -> dict:
        total = len(self._order)
        by_type: dict[str, int] = defaultdict(int)
        by_priority: dict[str, int] = defaultdict(int)
        for nid in self._order:
            n = self._store[nid]
            by_type[n.notification_type.value] += 1
            by_priority[n.priority.value] += 1
        return {
            "total":       total,
            "by_type":     dict(by_type),
            "by_priority": dict(by_priority),
        }


# ---------------------------------------------------------------------------
# Smart bundler
# ---------------------------------------------------------------------------

class NotificationBundler:
    """Groups related notifications within a time window into digest bundles."""

    def __init__(self, window_minutes: int = 15) -> None:
        self._window = timedelta(minutes=window_minutes)
        self._pending: dict[str, list[Notification]] = defaultdict(list)
        self._last_flush: datetime = datetime.utcnow()

    def add(self, notification: Notification) -> NotificationBundle | None:
        """Add a notification. Returns a bundle if the window has elapsed."""
        key = notification.bundle_key or notification.notification_type.value
        self._pending[key].append(notification)
        return None

    def flush(self) -> list[NotificationBundle]:
        """Create bundles from pending notifications grouped by key."""
        bundles = []
        for key, notifications in self._pending.items():
            if len(notifications) >= 2:
                bundle = NotificationBundle(
                    bundle_id=str(uuid4()),
                    bundle_key=key,
                    notifications=notifications,
                    created_at=datetime.utcnow(),
                )
                for n in notifications:
                    n.status = DeliveryStatus.BUNDLED
                bundles.append(bundle)
        self._pending.clear()
        self._last_flush = datetime.utcnow()
        return bundles


# ---------------------------------------------------------------------------
# Notification Engine
# ---------------------------------------------------------------------------

class NotificationEngine:
    """Central dispatcher: create → bundle → route → deliver notifications.

    Usage:
        engine = NotificationEngine()
        engine.send(
            ntype=NotificationType.RISK_ALERT,
            priority=NotificationPriority.HIGH,
            title="Attrition spike detected",
            body="Engineering team at-risk rate rose to 35%.",
            source="early_warning",
        )
    """

    def __init__(
        self,
        store:          NotificationStore | None = None,
        bundle_window_m: int = 15,
    ) -> None:
        self._store    = store or NotificationStore()
        self._bundler  = NotificationBundler(window_minutes=bundle_window_m)
        self._prefs:   dict[str, NotificationPreferences] = {}
        self._channels: dict[NotificationChannel, object] = {}
        self._bundles:  list[NotificationBundle] = []

    # ------------------------------------------------------------------
    # Channel registration
    # ------------------------------------------------------------------

    def register_channel(self, channel: NotificationChannel, handler: object) -> None:
        """Register a delivery handler for a channel.

        Handler must implement `deliver(notification)` or `deliver_bundle(bundle)`.
        """
        self._channels[channel] = handler

    # ------------------------------------------------------------------
    # Preferences
    # ------------------------------------------------------------------

    def set_preferences(self, prefs: NotificationPreferences) -> None:
        self._prefs[prefs.user_id] = prefs

    def get_preferences(self, user_id: str) -> NotificationPreferences:
        return self._prefs.get(user_id, NotificationPreferences(user_id=user_id))

    # ------------------------------------------------------------------
    # Send
    # ------------------------------------------------------------------

    def send(
        self,
        ntype:          NotificationType,
        priority:       NotificationPriority,
        title:          str,
        body:           str,
        source:         str,
        target_user_ids: list[str] | None = None,
        channel:        NotificationChannel = NotificationChannel.IN_APP,
        metadata:       dict | None = None,
        bundle_key:     str = "",
    ) -> Notification:
        """Create and dispatch a notification."""
        n = Notification(
            notification_id  = str(uuid4()),
            notification_type= ntype,
            priority         = priority,
            title            = title,
            body             = body,
            source           = source,
            created_at       = datetime.utcnow(),
            target_user_ids  = target_user_ids or [],
            channel          = channel,
            metadata         = metadata or {},
            bundle_key       = bundle_key or ntype.value,
        )
        self._store.add(n)
        self._bundler.add(n)
        self._dispatch(n)
        logger.info("Notification sent: [%s] %s", priority.value, title)
        return n

    # ------------------------------------------------------------------
    # Convenience senders
    # ------------------------------------------------------------------

    def send_risk_alert(
        self, title: str, body: str, priority: NotificationPriority,
        source: str = "early_warning", target_user_ids: list[str] | None = None,
    ) -> Notification:
        return self.send(
            ntype=NotificationType.RISK_ALERT, priority=priority,
            title=title, body=body, source=source,
            target_user_ids=target_user_ids, bundle_key="risk_alert",
        )

    def send_workflow_status(
        self, title: str, body: str,
        success: bool = True, source: str = "workflow_engine",
    ) -> Notification:
        return self.send(
            ntype=NotificationType.WORKFLOW_STATUS,
            priority=NotificationPriority.LOW if success else NotificationPriority.HIGH,
            title=title, body=body, source=source,
            bundle_key="workflow_status",
        )

    def send_system(self, title: str, body: str, source: str = "system") -> Notification:
        return self.send(
            ntype=NotificationType.SYSTEM,
            priority=NotificationPriority.LOW,
            title=title, body=body, source=source,
        )

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def for_user(self, user_id: str, unread_only: bool = False,
                 limit: int = 50) -> list[Notification]:
        return self._store.for_user(user_id, unread_only=unread_only, limit=limit)

    def unread_count(self, user_id: str) -> int:
        return self._store.unread_count(user_id)

    def mark_read(self, notification_id: str, user_id: str) -> bool:
        n = self._store.get(notification_id)
        if n:
            n.mark_read(user_id)
            return True
        return False

    def mark_all_read(self, user_id: str) -> int:
        return self._store.mark_all_read(user_id)

    def flush_bundles(self) -> list[NotificationBundle]:
        bundles = self._bundler.flush()
        self._bundles.extend(bundles)
        return bundles

    def all_bundles(self) -> list[NotificationBundle]:
        return list(reversed(self._bundles))

    def stats(self) -> dict:
        return self._store.stats()

    # ------------------------------------------------------------------
    # Internal dispatch
    # ------------------------------------------------------------------

    def _dispatch(self, notification: Notification) -> None:
        handler = self._channels.get(notification.channel)
        if handler and hasattr(handler, "deliver"):
            try:
                handler.deliver(notification)
                notification.status = DeliveryStatus.DELIVERED
            except Exception as exc:
                logger.error("Delivery failed for %s: %s",
                             notification.notification_id, exc)
                notification.status = DeliveryStatus.FAILED
        else:
            notification.status = DeliveryStatus.DELIVERED


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_engine: NotificationEngine | None = None


def get_notification_engine() -> NotificationEngine:
    global _engine
    if _engine is None:
        _engine = NotificationEngine()
        _seed_demo_notifications(_engine)
    return _engine


def _seed_demo_notifications(engine: NotificationEngine) -> None:
    """Populate the engine with realistic demo notifications."""
    demos = [
        (NotificationType.ATTRITION_ALERT, NotificationPriority.CRITICAL,
         "Critical attrition risk: Engineering",
         "7 of 12 at-risk employees are in Engineering. Immediate retention actions recommended.",
         "early_warning"),
        (NotificationType.RISK_ALERT, NotificationPriority.HIGH,
         "Nexus employee attrition risk elevated",
         "Maria Torres (betweenness centrality 0.82) now shows 74% attrition risk.",
         "early_warning"),
        (NotificationType.BUDGET_ALERT, NotificationPriority.HIGH,
         "Q3 spend trajectory exceeds target",
         "Current monthly run rate is 112% of plan. Projected overspend: $340K by quarter-end.",
         "budget_forecaster"),
        (NotificationType.WORKFLOW_STATUS, NotificationPriority.LOW,
         "Data pipeline completed",
         "Bronze → Silver → Gold pipeline ran successfully. 487 records refreshed.",
         "workflow_engine"),
        (NotificationType.MODEL_DRIFT, NotificationPriority.MEDIUM,
         "Impact model drift detected",
         "SHAP feature importance shifted >15% in Engineering dept. Retraining recommended.",
         "model_monitor"),
        (NotificationType.WORKFLOW_STATUS, NotificationPriority.MEDIUM,
         "Attrition model retraining queued",
         "Monthly retraining scheduled for 02:00 UTC. Estimated duration: 8 min.",
         "workflow_engine"),
        (NotificationType.SYSTEM, NotificationPriority.LOW,
         "Audit log export completed",
         "30-day GDPR report generated and available for download in the Admin panel.",
         "compliance"),
        (NotificationType.COLLABORATION, NotificationPriority.LOW,
         "Strategic plan shared with you",
         "Alex Rivera shared '2026 Target Structure' with your team for review.",
         "strategic_planner"),
        (NotificationType.RISK_ALERT, NotificationPriority.MEDIUM,
         "Team fragility threshold exceeded",
         "Product team fragility score is 0.78 (threshold: 0.55). 3 single-skill holders identified.",
         "early_warning"),
        (NotificationType.SYSTEM, NotificationPriority.LOW,
         "Weekly risk digest ready",
         "Your automated risk digest for the week of 2026-05-11 is available.",
         "risk_digest"),
    ]
    for ntype, priority, title, body, source in demos:
        engine.send(ntype=ntype, priority=priority, title=title,
                    body=body, source=source)
