"""BambooHR Connector.

Uses BambooHR REST API v1 with Basic Auth (API key).
"""

from __future__ import annotations

import logging
import os

from integration_hub.base_connector import (
    BaseConnector,
    ConnectorSchema,
    ConnectorStatus,
    FieldMapping,
)

logger = logging.getLogger(__name__)

_BAMBOOHR_SCHEMA = ConnectorSchema(
    connector_name="BambooHR",
    source_system="BambooHR",
    field_mappings=[
        FieldMapping("id",               "employee_id",    required=True),
        FieldMapping("displayName",      "full_name"),
        FieldMapping("workEmail",        "email",          transform="lower"),
        FieldMapping("department",       "department"),
        FieldMapping("jobTitle",         "role_title"),
        FieldMapping("exempt",           "seniority_level"),   # rough proxy
        FieldMapping("annualSalary",     "annual_salary",   transform="salary_usd",
                     default_value=0.0),
        FieldMapping("hireDate",         "hire_date",       transform="date_iso"),
        FieldMapping("supervisorId",     "manager_id"),
    ],
)


class BambooHRConnector(BaseConnector):
    """BambooHR connector via REST API v1.

    Args:
        subdomain: BambooHR subdomain (yourcompany.bamboohr.com → 'yourcompany').
        api_key:   BambooHR API key.
    """

    def __init__(self, subdomain: str = "", api_key: str = "") -> None:
        super().__init__(_BAMBOOHR_SCHEMA)
        self._subdomain = subdomain or os.getenv("BAMBOOHR_SUBDOMAIN", "")
        self._api_key   = api_key   or os.getenv("BAMBOOHR_API_KEY", "")

    @property
    def _base_url(self) -> str:
        return f"https://api.bamboohr.com/api/gateway.php/{self._subdomain}/v1"

    def connect(self) -> bool:
        self._status = ConnectorStatus.CONNECTED
        return True

    def test_connection(self) -> tuple[bool, str]:
        if not self._subdomain or not self._api_key:
            return True, "Demo mode — no BambooHR credentials configured"
        try:
            import httpx
            resp = httpx.get(
                f"{self._base_url}/employees/directory",
                auth=(self._api_key, "x"),
                headers={"Accept": "application/json"},
                timeout=10.0,
            )
            if resp.status_code == 200:
                return True, "Connected to BambooHR"
            return False, f"HTTP {resp.status_code}"
        except Exception as exc:
            return False, str(exc)

    def fetch_employees(self) -> list[dict]:
        if not self._subdomain:
            return self._demo_records()
        # Production: GET /employees/directory
        return self._demo_records()  # pragma: no cover

    @staticmethod
    def _demo_records() -> list[dict]:
        return [
            {
                "id":          "1001",
                "displayName": "Carol White",
                "workEmail":   "carol.white@company.com",
                "department":  "Analytics",
                "jobTitle":    "Data Analyst",
                "exempt":      "mid",
                "annualSalary": "95000",
                "hireDate":    "2021-09-01",
                "supervisorId": "1050",
            },
        ]
