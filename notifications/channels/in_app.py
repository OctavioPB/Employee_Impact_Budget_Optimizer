"""In-app notification channel — stores delivered notifications in the engine store.

The in-app channel is the default; all notifications go through it. The Streamlit
UI reads from the engine's NotificationStore directly.
"""

from __future__ import annotations

import logging

from notifications.engine import Notification, NotificationStore

logger = logging.getLogger(__name__)


class InAppChannel:
    """Delivers notifications to the in-app store (no-op: already stored by engine)."""

    def __init__(self, store: NotificationStore) -> None:
        self._store = store

    def deliver(self, notification: Notification) -> None:
        # Already in the store from NotificationEngine.send()
        logger.debug("In-app delivered: %s", notification.notification_id)

    def deliver_bundle(self, bundle) -> None:
        logger.debug("In-app bundle delivered: %d items", len(bundle.notifications))
