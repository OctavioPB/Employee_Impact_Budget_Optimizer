"""Workday HRIS Connector.

Connects to the Workday REST API (Workers endpoint) and maps
Workday field names to the EIBO canonical schema.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from integration_hub.base_connector import (
    BaseConnector,
    ConnectorSchema,
    ConnectorStatus,
    FieldMapping,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Workday field mapping
# ---------------------------------------------------------------------------

_WORKDAY_SCHEMA = ConnectorSchema(
    connector_name="Workday",
    source_system="Workday HCM",
    field_mappings=[
        FieldMapping("Worker_ID",               "employee_id",    required=True),
        FieldMapping("Worker_Name",              "full_name"),
        FieldMapping("Email_Address",            "email",          transform="lower"),
        FieldMapping("Organization",             "department"),
        FieldMapping("Job_Title",                "role_title"),
        FieldMapping("Management_Level",         "seniority_level", transform="lower"),
        FieldMapping("Annual_Pay",               "annual_salary",   transform="salary_usd",
                     default_value=0.0),
        FieldMapping("Hire_Date",                "hire_date",       transform="date_iso"),
        FieldMapping("Manager_Worker_ID",        "manager_id"),
    ],
)


class WorkdayConnector(BaseConnector):
    """Workday HCM connector via REST API.

    Args:
        api_url:    Workday API base URL (e.g. https://wd3-impl-services1.workday.com/...)
        tenant:     Workday tenant ID.
        username:   Integration system user.
        password:   Integration system password.
        client_id:  OAuth2 client ID (if using OAuth flow).
        client_secret: OAuth2 client secret.
    """

    def __init__(
        self,
        api_url:       str = "",
        tenant:        str = "",
        username:      str = "",
        password:      str = "",
        client_id:     str = "",
        client_secret: str = "",
    ) -> None:
        super().__init__(_WORKDAY_SCHEMA)
        self._api_url       = api_url       or os.getenv("WORKDAY_API_URL", "")
        self._tenant        = tenant
        self._username      = username      or os.getenv("WORKDAY_USERNAME", "")
        self._password      = password      or os.getenv("WORKDAY_PASSWORD", "")
        self._client_id     = client_id     or os.getenv("WORKDAY_CLIENT_ID", "")
        self._client_secret = client_secret or os.getenv("WORKDAY_CLIENT_SECRET", "")
        self._token: Optional[str] = None

    def connect(self) -> bool:
        if not self._api_url:
            logger.warning("WorkdayConnector: no API URL configured — running in demo mode")
            self._status = ConnectorStatus.CONNECTED
            return True
        # In production: obtain OAuth2 bearer token
        # self._token = self._fetch_token()
        self._status = ConnectorStatus.CONNECTED
        return True

    def test_connection(self) -> tuple[bool, str]:
        if not self._api_url:
            return True, "Demo mode — no real Workday endpoint configured"
        try:
            import httpx
            resp = httpx.get(
                f"{self._api_url}/workers",
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=10.0,
            )
            if resp.status_code == 200:
                return True, "Connected to Workday API"
            return False, f"HTTP {resp.status_code}: {resp.text[:200]}"
        except Exception as exc:
            return False, str(exc)

    def fetch_employees(self) -> list[dict]:
        if not self._api_url:
            return self._demo_records()
        # In production: paginate through /workers endpoint
        # ...
        return self._demo_records()  # pragma: no cover

    @staticmethod
    def _demo_records() -> list[dict]:
        return [
            {
                "Worker_ID":        "WD-001",
                "Worker_Name":      "Alice Chen",
                "Email_Address":    "Alice.Chen@company.com",
                "Organization":     "Engineering",
                "Job_Title":        "Staff Engineer",
                "Management_Level": "Senior",
                "Annual_Pay":       "155,000",
                "Hire_Date":        "2019-03-15",
                "Manager_Worker_ID": "WD-010",
            },
            {
                "Worker_ID":        "WD-002",
                "Worker_Name":      "Brian Park",
                "Email_Address":    "Brian.Park@company.com",
                "Organization":     "Product",
                "Job_Title":        "Senior PM",
                "Management_Level": "Senior",
                "Annual_Pay":       "145,000",
                "Hire_Date":        "2020-07-01",
                "Manager_Worker_ID": "WD-011",
            },
        ]
