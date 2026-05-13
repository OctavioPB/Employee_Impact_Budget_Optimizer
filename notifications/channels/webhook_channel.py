"""Webhook notification channel — delivers payloads via HTTP POST.

Compatible with Slack Incoming Webhooks, Microsoft Teams connectors,
and any custom HTTP endpoint.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

import httpx

from notifications.engine import Notification, NotificationBundle, NotificationPriority

logger = logging.getLogger(__name__)

_PRIORITY_EMOJI = {
    NotificationPriority.LOW:      "ℹ️",
    NotificationPriority.MEDIUM:   "⚠️",
    NotificationPriority.HIGH:     "🔴",
    NotificationPriority.CRITICAL: "🚨",
}


class WebhookChannel:
    """HTTP webhook channel with Slack/Teams-compatible payloads.

    Args:
        url: Webhook endpoint URL.
        headers: Additional request headers (e.g. Authorization).
        timeout: Request timeout in seconds.
        format: Payload format — "slack" | "teams" | "generic".
    """

    def __init__(
        self,
        url:     str,
        headers: Optional[dict[str, str]] = None,
        timeout: float = 10.0,
        format:  str   = "generic",
    ) -> None:
        self._url     = url
        self._headers = {"Content-Type": "application/json", **(headers or {})}
        self._timeout = timeout
        self._format  = format

    def deliver(self, notification: Notification) -> None:
        payload = self._build_payload(notification)
        self._post(payload)

    def deliver_bundle(self, bundle: NotificationBundle) -> None:
        payload = {
            "type":  "bundle",
            "title": bundle.title,
            "items": [n.to_dict() for n in bundle.notifications],
        }
        self._post(payload)

    def _build_payload(self, n: Notification) -> dict:
        emoji = _PRIORITY_EMOJI.get(n.priority, "")
        if self._format == "slack":
            return {
                "text": f"{emoji} *{n.title}*",
                "attachments": [{
                    "text":   n.body,
                    "footer": f"EIBO · {n.source}",
                    "color":  "#003366",
                }],
            }
        if self._format == "teams":
            return {
                "@type":      "MessageCard",
                "@context":   "https://schema.org/extensions",
                "summary":    n.title,
                "themeColor": "003366",
                "sections":   [{"activityTitle": n.title, "activityText": n.body}],
            }
        return n.to_dict()

    def _post(self, payload: dict) -> None:
        try:
            resp = httpx.post(
                self._url,
                headers=self._headers,
                content=json.dumps(payload),
                timeout=self._timeout,
            )
            resp.raise_for_status()
            logger.info("Webhook delivered to %s (status %d)", self._url, resp.status_code)
        except httpx.HTTPError as exc:
            logger.error("Webhook delivery failed: %s", exc)
            raise
