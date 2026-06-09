"""
Sprint 19 — API key management for the public v1 API.
Keys are stored in-memory (demo). In production, persist to PostgreSQL.
"""

import hashlib
import secrets
import time

_SCOPES = ["viewer", "analyst", "manager", "director", "executive", "demo"]

_SCOPE_SALARY_ACCESS = {"manager", "director", "executive"}


class ApiKey:
    def __init__(
        self,
        key_id:     str,
        key_prefix: str,
        key_hash:   str,
        label:      str,
        scope:      str,
        created_at: float,
        last_used:  float = 0.0,
        rate_limit: int   = 100,
        revoked:    bool  = False,
    ):
        self.key_id     = key_id
        self.key_prefix = key_prefix
        self.key_hash   = key_hash
        self.label      = label
        self.scope      = scope
        self.created_at = created_at
        self.last_used  = last_used
        self.rate_limit = rate_limit
        self.revoked    = revoked
        # token-bucket state (in-memory)
        self._tokens      = float(rate_limit)
        self._last_refill = time.monotonic()


_KEYS: dict[str, ApiKey] = {}

_SANDBOX_KEY    = "eibo_demo_sandbox0000000000000000"
_SANDBOX_KEY_ID = "sandbox_demo"


def _init_sandbox() -> None:
    if _SANDBOX_KEY_ID in _KEYS:
        return
    _KEYS[_SANDBOX_KEY_ID] = ApiKey(
        key_id     = _SANDBOX_KEY_ID,
        key_prefix = _SANDBOX_KEY[:12],
        key_hash   = hashlib.sha256(_SANDBOX_KEY.encode()).hexdigest(),
        label      = "Sandbox (demo data only)",
        scope      = "demo",
        created_at = time.time(),
    )


_init_sandbox()


def create_key(label: str, scope: str, rate_limit: int = 100) -> tuple[str, ApiKey]:
    if scope not in _SCOPES:
        raise ValueError(f"Invalid scope '{scope}'. Allowed: {_SCOPES}")
    raw_key = f"eibo_{scope}_{secrets.token_hex(16)}"
    key_id  = secrets.token_hex(8)
    entry   = ApiKey(
        key_id     = key_id,
        key_prefix = raw_key[:12],
        key_hash   = hashlib.sha256(raw_key.encode()).hexdigest(),
        label      = label,
        scope      = scope,
        created_at = time.time(),
        rate_limit = rate_limit,
    )
    _KEYS[key_id] = entry
    return raw_key, entry


def list_keys() -> list[ApiKey]:
    return [k for k in _KEYS.values() if not k.revoked]


def revoke_key(key_id: str) -> bool:
    if key_id == _SANDBOX_KEY_ID:
        return False  # sandbox key is permanent
    if key_id in _KEYS and not _KEYS[key_id].revoked:
        _KEYS[key_id].revoked = True
        return True
    return False


def _find_by_hash(raw_key: str) -> ApiKey | None:
    h = hashlib.sha256(raw_key.encode()).hexdigest()
    for entry in _KEYS.values():
        if not entry.revoked and entry.key_hash == h:
            return entry
    return None


def _consume_token(entry: ApiKey) -> bool:
    now     = time.monotonic()
    elapsed = now - entry._last_refill
    entry._tokens       = min(entry.rate_limit, entry._tokens + elapsed * (entry.rate_limit / 60.0))
    entry._last_refill  = now
    if entry._tokens >= 1.0:
        entry._tokens -= 1.0
        return True
    return False


def authenticate(raw_key: str) -> ApiKey | None:
    """Return the ApiKey if valid and within rate limit, None otherwise."""
    entry = _find_by_hash(raw_key)
    if entry is None:
        return None
    if not _consume_token(entry):
        return None
    entry.last_used = time.time()
    return entry


def key_allows_salary(scope: str) -> bool:
    return scope in _SCOPE_SALARY_ACCESS


def get_sandbox_key() -> str:
    return _SANDBOX_KEY
