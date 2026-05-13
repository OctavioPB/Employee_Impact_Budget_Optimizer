"""Base Connector — abstract interface for HRIS/ERP integration connectors.

All connectors implement this interface. The DataMapper handles field mapping
between external HRIS schemas and the EIBO internal schema.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Connector status
# ---------------------------------------------------------------------------

class ConnectorStatus(str, Enum):
    CONFIGURED   = "configured"
    CONNECTED    = "connected"
    DISCONNECTED = "disconnected"
    ERROR        = "error"
    SYNCING      = "syncing"


class SyncMode(str, Enum):
    FULL        = "full"        # replace all records
    INCREMENTAL = "incremental" # add/update changed records since last sync


# ---------------------------------------------------------------------------
# Sync result
# ---------------------------------------------------------------------------

@dataclass
class SyncResult:
    """Result of a connector sync operation."""
    connector_name:  str
    sync_mode:       SyncMode
    started_at:      str
    finished_at:     str       = ""
    records_fetched: int       = 0
    records_inserted: int      = 0
    records_updated: int       = 0
    records_skipped: int       = 0
    errors:          list[str] = field(default_factory=list)
    warnings:        list[str] = field(default_factory=list)
    duration_s:      float     = 0.0
    success:         bool      = True

    @property
    def total_changes(self) -> int:
        return self.records_inserted + self.records_updated


# ---------------------------------------------------------------------------
# Field mapping
# ---------------------------------------------------------------------------

@dataclass
class FieldMapping:
    """Maps one external field to one EIBO field with optional transformation."""
    source_field:    str
    target_field:    str
    transform:       Optional[str] = None   # "upper" | "lower" | "date_iso" | "salary_usd"
    default_value:   Any           = None
    required:        bool          = False


@dataclass
class ConnectorSchema:
    """Complete field mapping for a connector."""
    connector_name:   str
    source_system:    str           # e.g. "Workday", "BambooHR"
    field_mappings:   list[FieldMapping] = field(default_factory=list)

    # EIBO canonical fields and their expected types
    _CANONICAL_FIELDS = {
        "employee_id":    str,
        "full_name":      str,
        "email":          str,
        "department":     str,
        "role_title":     str,
        "seniority_level": str,
        "annual_salary":  float,
        "hire_date":      str,
        "manager_id":     str,
    }

    def apply(self, record: dict[str, Any]) -> dict[str, Any]:
        """Apply field mappings to transform a source record to EIBO schema."""
        out: dict[str, Any] = {}
        for mapping in self.field_mappings:
            val = record.get(mapping.source_field, mapping.default_value)
            if val is None:
                if mapping.required:
                    logger.warning("Required field '%s' missing in record",
                                   mapping.source_field)
                continue
            val = self._transform(val, mapping.transform)
            out[mapping.target_field] = val
        return out

    @staticmethod
    def _transform(value: Any, transform: Optional[str]) -> Any:
        if transform is None or value is None:
            return value
        if transform == "upper":
            return str(value).upper()
        if transform == "lower":
            return str(value).lower()
        if transform == "date_iso":
            if isinstance(value, datetime):
                return value.date().isoformat()
            return str(value)[:10]  # assume YYYY-MM-DD prefix
        if transform == "salary_usd":
            return float(str(value).replace(",", "").replace("$", ""))
        return value

    def apply_batch(self, records: list[dict]) -> pd.DataFrame:
        return pd.DataFrame([self.apply(r) for r in records])


# ---------------------------------------------------------------------------
# Abstract base connector
# ---------------------------------------------------------------------------

class BaseConnector(ABC):
    """Abstract base class for all HRIS/ERP connectors.

    Subclasses implement `connect()`, `fetch_employees()`, and optionally
    `fetch_performance()` and `fetch_skills()`.
    """

    def __init__(self, schema: ConnectorSchema) -> None:
        self._schema  = schema
        self._status  = ConnectorStatus.CONFIGURED
        self._last_sync: Optional[datetime] = None

    @property
    def name(self) -> str:
        return self._schema.connector_name

    @property
    def source_system(self) -> str:
        return self._schema.source_system

    @property
    def status(self) -> ConnectorStatus:
        return self._status

    @property
    def last_sync_at(self) -> Optional[str]:
        return self._last_sync.isoformat() if self._last_sync else None

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection. Returns True on success."""

    @abstractmethod
    def test_connection(self) -> tuple[bool, str]:
        """Test connectivity. Returns (ok, message)."""

    @abstractmethod
    def fetch_employees(self) -> list[dict]:
        """Fetch raw employee records from the source system."""

    def fetch_performance(self) -> list[dict]:
        """Fetch performance records (optional)."""
        return []

    def fetch_skills(self) -> list[dict]:
        """Fetch employee skills (optional)."""
        return []

    def sync(self, mode: SyncMode = SyncMode.INCREMENTAL) -> SyncResult:
        """Run a full sync cycle: connect → fetch → map → return."""
        import time as _time
        started = _time.perf_counter()
        started_at = datetime.utcnow().isoformat() + "Z"
        result = SyncResult(
            connector_name=self.name,
            sync_mode=mode,
            started_at=started_at,
        )

        try:
            if not self.connect():
                raise ConnectionError(f"Cannot connect to {self.source_system}")

            raw_records = self.fetch_employees()
            result.records_fetched = len(raw_records)
            mapped = self._schema.apply_batch(raw_records)
            result.records_inserted = len(mapped)
            self._last_sync = datetime.utcnow()
            self._status = ConnectorStatus.CONNECTED

        except Exception as exc:
            result.success = False
            result.errors.append(str(exc))
            self._status = ConnectorStatus.ERROR
            logger.error("Sync failed for %s: %s", self.name, exc)

        duration = _time.perf_counter() - started
        result.finished_at = datetime.utcnow().isoformat() + "Z"
        result.duration_s  = round(duration, 3)
        return result

    def status_dict(self) -> dict:
        return {
            "connector":    self.name,
            "source":       self.source_system,
            "status":       self._status.value,
            "last_sync_at": self.last_sync_at,
        }
