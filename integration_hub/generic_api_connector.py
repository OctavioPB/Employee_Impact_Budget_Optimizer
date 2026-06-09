"""Generic REST API Connector — configuration-driven connector for any HRIS REST API.

Supports Basic Auth, Bearer token, and API key authentication.
Field mappings are specified at runtime via ConnectorSchema.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from integration_hub.base_connector import (
    BaseConnector,
    ConnectorSchema,
    ConnectorStatus,
)

logger = logging.getLogger(__name__)


class GenericAPIConnector(BaseConnector):
    """Configurable REST API connector.

    Args:
        name:       Connector display name.
        schema:     ConnectorSchema defining field mappings.
        base_url:   API base URL.
        employees_endpoint: Path to employee list endpoint.
        auth_type:  "none" | "basic" | "bearer" | "api_key".
        auth_config: Dict with auth credentials (keys depend on auth_type).
        list_key:   JSON key in response that holds the employee array.
                    None = response is already an array.
        extra_headers: Additional request headers.
        timeout:    HTTP timeout in seconds.
    """

    _AUTH_TYPES = ("none", "basic", "bearer", "api_key")

    def __init__(
        self,
        name:                str,
        schema:              ConnectorSchema,
        base_url:            str,
        employees_endpoint:  str = "/employees",
        auth_type:           str = "none",
        auth_config:         dict[str, str] | None = None,
        list_key:            str | None = None,
        extra_headers:       dict[str, str] | None = None,
        timeout:             float = 15.0,
    ) -> None:
        super().__init__(schema)
        self._base_url   = base_url.rstrip("/")
        self._endpoint   = employees_endpoint
        self._auth_type  = auth_type
        self._auth_cfg   = auth_config or {}
        self._list_key   = list_key
        self._headers    = {"Accept": "application/json", **(extra_headers or {})}
        self._timeout    = timeout
        # Inject name into schema
        schema.connector_name = name

    def connect(self) -> bool:
        ok, _ = self.test_connection()
        self._status = ConnectorStatus.CONNECTED if ok else ConnectorStatus.ERROR
        return ok

    def test_connection(self) -> tuple[bool, str]:
        try:
            resp = self._get(self._endpoint, params={"limit": "1"})
            return True, f"Connected (HTTP {resp.status_code})"
        except Exception as exc:
            return False, str(exc)

    def fetch_employees(self) -> list[dict]:
        try:
            resp  = self._get(self._endpoint)
            data  = resp.json()
            items = data.get(self._list_key, data) if self._list_key else data
            if not isinstance(items, list):
                logger.error("Expected list at key '%s', got %s",
                             self._list_key, type(items).__name__)
                return []
            logger.info("Fetched %d employee records from %s", len(items), self._base_url)
            return items
        except Exception as exc:
            logger.error("Fetch failed: %s", exc)
            return []

    def _get(self, path: str, params: dict | None = None) -> httpx.Response:
        url  = self._base_url + path
        auth = self._build_auth()
        return httpx.get(
            url,
            headers=self._headers,
            auth=auth,
            params=params,
            timeout=self._timeout,
        )

    def _build_auth(self) -> Any:
        if self._auth_type == "basic":
            return (self._auth_cfg.get("username", ""),
                    self._auth_cfg.get("password", ""))
        if self._auth_type == "bearer":
            self._headers["Authorization"] = f"Bearer {self._auth_cfg.get('token', '')}"
        if self._auth_type == "api_key":
            key_name = self._auth_cfg.get("header_name", "X-API-Key")
            self._headers[key_name] = self._auth_cfg.get("api_key", "")
        return None


# ---------------------------------------------------------------------------
# Registry of configured generic connectors (for the UI)
# ---------------------------------------------------------------------------

class ConnectorRegistry:
    """Lightweight registry for configured connectors."""

    def __init__(self) -> None:
        self._connectors: dict[str, BaseConnector] = {}

    def register(self, connector: BaseConnector) -> None:
        self._connectors[connector.name] = connector

    def get(self, name: str) -> BaseConnector | None:
        return self._connectors.get(name)

    def all(self) -> list[BaseConnector]:
        return list(self._connectors.values())

    def status_summary(self) -> list[dict]:
        return [c.status_dict() for c in self._connectors.values()]


_registry: ConnectorRegistry | None = None


def get_connector_registry() -> ConnectorRegistry:
    global _registry
    if _registry is None:
        from integration_hub.bamboohr_connector import BambooHRConnector
        from integration_hub.workday_connector import WorkdayConnector
        _registry = ConnectorRegistry()
        _registry.register(WorkdayConnector())
        _registry.register(BambooHRConnector())
    return _registry
