"""Sprint 19 — Webhook management endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.webhook_service import (
    EVENT_TYPES,
    WebhookRegistration,
    delete_webhook,
    list_webhooks,
    register_webhook,
    set_active,
    test_webhook,
)

router = APIRouter()


class WebhookCreateRequest(BaseModel):
    url:    str        = Field(min_length=1)
    events: list[str]
    label:  str        = Field(min_length=1, max_length=80)
    secret: str        = Field(default="")


class WebhookPatchRequest(BaseModel):
    active: bool


def _wh_dict(wh: WebhookRegistration) -> dict:
    return {
        "webhook_id":    wh.webhook_id,
        "url":           wh.url,
        "events":        wh.events,
        "label":         wh.label,
        "active":        wh.active,
        "created_at":    wh.created_at,
        "secret_hint":   wh.secret[:6] + "…",
        "total_deliveries": len(wh.delivery_log),
        "last_delivery": wh.delivery_log[-1] if wh.delivery_log else None,
    }


@router.get("/v1/webhooks/event-types")
def get_event_types() -> list[str]:
    return EVENT_TYPES


@router.get("/v1/webhooks")
def get_webhooks() -> list[dict]:
    return [_wh_dict(wh) for wh in list_webhooks()]


@router.post("/v1/webhooks")
def create_webhook(body: WebhookCreateRequest) -> dict:
    try:
        wh = register_webhook(body.url, body.events, body.label, body.secret)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    result = _wh_dict(wh)
    result["secret"] = wh.secret  # shown once on creation
    return result


@router.delete("/v1/webhooks/{webhook_id}")
def remove_webhook(webhook_id: str) -> dict:
    if not delete_webhook(webhook_id):
        raise HTTPException(status_code=404, detail="Webhook not found")
    return {"status": "deleted", "webhook_id": webhook_id}


@router.patch("/v1/webhooks/{webhook_id}")
def patch_webhook(webhook_id: str, body: WebhookPatchRequest) -> dict:
    if not set_active(webhook_id, body.active):
        raise HTTPException(status_code=404, detail="Webhook not found")
    return {"status": "updated", "webhook_id": webhook_id, "active": body.active}


@router.post("/v1/webhooks/{webhook_id}/test")
async def send_test_event(webhook_id: str) -> dict:
    try:
        result = await test_webhook(webhook_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return result
