"""
Sprint 19 — Webhook registration and delivery service.
Webhooks are stored in-memory (demo). In production, persist to PostgreSQL.
"""

import hashlib
import hmac
import json
import secrets
import time


EVENT_TYPES = [
    "attrition.risk.threshold_crossed",
    "impact.score.updated",
    "simulation.completed",
    "ohi.alert",
    "notification.created",
]


class WebhookRegistration:
    def __init__(
        self,
        webhook_id:  str,
        url:         str,
        events:      list[str],
        secret:      str,
        label:       str,
        active:      bool  = True,
        created_at:  float = 0.0,
    ):
        self.webhook_id   = webhook_id
        self.url          = url
        self.events       = events
        self.secret       = secret
        self.label        = label
        self.active       = active
        self.created_at   = created_at or time.time()
        self.delivery_log: list[dict] = []


_WEBHOOKS: dict[str, WebhookRegistration] = {}


def register_webhook(url: str, events: list[str], label: str, secret: str = "") -> WebhookRegistration:
    invalid = [e for e in events if e not in EVENT_TYPES]
    if invalid:
        raise ValueError(f"Unknown event types: {invalid}. Valid: {EVENT_TYPES}")
    webhook_id = secrets.token_hex(8)
    secret     = secret or secrets.token_hex(24)
    wh = WebhookRegistration(
        webhook_id = webhook_id,
        url        = url,
        events     = events,
        secret     = secret,
        label      = label,
    )
    _WEBHOOKS[webhook_id] = wh
    return wh


def list_webhooks() -> list[WebhookRegistration]:
    return list(_WEBHOOKS.values())


def delete_webhook(webhook_id: str) -> bool:
    return bool(_WEBHOOKS.pop(webhook_id, None))


def set_active(webhook_id: str, active: bool) -> bool:
    if webhook_id not in _WEBHOOKS:
        return False
    _WEBHOOKS[webhook_id].active = active
    return True


def get_webhook(webhook_id: str) -> WebhookRegistration | None:
    return _WEBHOOKS.get(webhook_id)


def _sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.digest(secret.encode(), body, "sha256").hex()


async def _deliver(wh: WebhookRegistration, event_type: str, payload: dict, attempt: int = 1) -> dict:
    import httpx

    body = json.dumps({"event": event_type, "payload": payload, "ts": time.time()}).encode()
    sig  = _sign(wh.secret, body)
    log: dict = {"event": event_type, "attempt": attempt, "ts": time.time(), "status": "pending"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                wh.url,
                content=body,
                headers={
                    "Content-Type":    "application/json",
                    "X-EIBO-Signature": sig,
                    "User-Agent":      "EIBO-Webhook/1.0",
                },
            )
        log["http_status"] = resp.status_code
        log["status"]      = "delivered" if resp.is_success else f"http_{resp.status_code}"
    except Exception as exc:
        log["status"] = "failed"
        log["error"]  = str(exc)

    wh.delivery_log = (wh.delivery_log + [log])[-50:]
    return log


async def emit_event(event_type: str, payload: dict) -> list[dict]:
    if event_type not in EVENT_TYPES:
        raise ValueError(f"Unknown event type '{event_type}'")
    results = []
    for wh in _WEBHOOKS.values():
        if wh.active and event_type in wh.events:
            log = await _deliver(wh, event_type, payload)
            results.append({"webhook_id": wh.webhook_id, **log})
    return results


async def test_webhook(webhook_id: str) -> dict:
    wh = _WEBHOOKS.get(webhook_id)
    if wh is None:
        raise ValueError(f"Webhook '{webhook_id}' not found")
    return await _deliver(
        wh, "notification.created",
        {"message": "EIBO webhook connectivity test", "demo": True},
    )
