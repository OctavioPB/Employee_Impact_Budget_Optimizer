"""Sprint 19 — API key management endpoints (Admin panel)."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.api_key_service import (
    _SCOPES,
    authenticate,
    create_key,
    get_sandbox_key,
    list_keys,
    revoke_key,
)

router = APIRouter()


class CreateKeyRequest(BaseModel):
    label:      str = Field(min_length=1, max_length=80)
    scope:      str = Field(default="analyst")
    rate_limit: int = Field(default=100, ge=10, le=10000)


@router.get("/v1/api-keys")
def get_api_keys() -> list[dict]:
    return [
        {
            "key_id":     k.key_id,
            "key_prefix": k.key_prefix,
            "label":      k.label,
            "scope":      k.scope,
            "created_at": k.created_at,
            "last_used":  k.last_used,
            "rate_limit": k.rate_limit,
        }
        for k in list_keys()
    ]


@router.post("/v1/api-keys")
def create_api_key(body: CreateKeyRequest) -> dict:
    try:
        raw_key, entry = create_key(body.label, body.scope, body.rate_limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "key_id":     entry.key_id,
        "key":        raw_key,
        "key_prefix": entry.key_prefix,
        "label":      entry.label,
        "scope":      entry.scope,
        "rate_limit": entry.rate_limit,
        "created_at": entry.created_at,
        "warning":    "Store this key securely — it will not be shown again.",
    }


@router.delete("/v1/api-keys/{key_id}")
def delete_api_key(key_id: str) -> dict:
    if not revoke_key(key_id):
        raise HTTPException(status_code=404, detail="Key not found or cannot be revoked")
    return {"status": "revoked", "key_id": key_id}


@router.post("/v1/api-keys/verify")
def verify_api_key(body: dict) -> dict:
    raw_key = body.get("key", "")
    entry   = authenticate(raw_key)
    if entry is None:
        raise HTTPException(status_code=401, detail="Invalid or rate-limited key")
    return {"valid": True, "scope": entry.scope, "label": entry.label, "rate_limit": entry.rate_limit}


@router.get("/v1/api-keys/scopes")
def list_scopes() -> list[str]:
    return _SCOPES


@router.get("/v1/api-keys/sandbox")
def get_sandbox() -> dict:
    """Return the pre-seeded sandbox key (demo data only, safe to expose)."""
    return {"key": get_sandbox_key(), "scope": "demo", "label": "Sandbox (demo data only)"}
