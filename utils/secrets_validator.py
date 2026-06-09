"""Secrets and environment variable validator for EIBO.

Validates that required secrets are present, non-empty, and not
using placeholder/default values before the application starts.

Usage:
    from utils.secrets_validator import validate_secrets, SecretsReport
    report = validate_secrets()
    if not report.is_demo_safe:
        raise RuntimeError(report.summary)
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from enum import StrEnum


class SecretStatus(StrEnum):
    PRESENT = "present"      # set and passes strength checks
    WEAK    = "weak"         # set but uses a placeholder/default value
    MISSING = "missing"      # not set or empty


@dataclass
class SecretCheck:
    """Result for a single secret."""
    name:    str
    status:  SecretStatus
    reason:  str = ""


@dataclass
class SecretsReport:
    """Aggregated validation report for all checked secrets."""
    checks:     list[SecretCheck]
    demo_mode:  bool = False

    @property
    def missing(self) -> list[str]:
        return [c.name for c in self.checks if c.status == SecretStatus.MISSING]

    @property
    def weak(self) -> list[str]:
        return [c.name for c in self.checks if c.status == SecretStatus.WEAK]

    @property
    def present(self) -> list[str]:
        return [c.name for c in self.checks if c.status == SecretStatus.PRESENT]

    @property
    def is_production_ready(self) -> bool:
        """True only when all secrets are PRESENT (no missing or weak)."""
        return not self.missing and not self.weak

    @property
    def is_demo_safe(self) -> bool:
        """True in demo mode (skips production secret requirements)."""
        if self.demo_mode:
            return True
        return self.is_production_ready

    @property
    def summary(self) -> str:
        parts = []
        if self.missing:
            parts.append(f"Missing: {', '.join(self.missing)}")
        if self.weak:
            parts.append(f"Weak/placeholder: {', '.join(self.weak)}")
        if not parts:
            return "All secrets validated successfully."
        return " | ".join(parts)

    def to_dict(self) -> dict:
        return {
            "production_ready": self.is_production_ready,
            "demo_safe":        self.is_demo_safe,
            "summary":          self.summary,
            "missing":          self.missing,
            "weak":             self.weak,
            "present":          self.present,
        }


# ---------------------------------------------------------------------------
# Placeholder detection
# ---------------------------------------------------------------------------

_PLACEHOLDER_PATTERNS = re.compile(
    r"^(change.?me|placeholder|your.?password|your.?secret|secret|password"
    r"|admin|test|1234|12345|default|example|sample|replace.?me"
    r"|<.*>|\{.*\}|\[.*\])$",
    re.IGNORECASE,
)

_MIN_SECRET_LENGTH = 16  # minimum characters for high-entropy secrets


def _check_secret(
    name: str,
    required: bool = True,
    min_length: int = 1,
    check_placeholder: bool = False,
) -> SecretCheck:
    """Evaluate a single environment variable."""
    value = os.getenv(name, "").strip()

    if not value:
        if required:
            return SecretCheck(name=name, status=SecretStatus.MISSING,
                               reason="Environment variable not set or empty")
        return SecretCheck(name=name, status=SecretStatus.MISSING,
                           reason="Optional — not configured")

    if check_placeholder and _PLACEHOLDER_PATTERNS.match(value):
        return SecretCheck(name=name, status=SecretStatus.WEAK,
                           reason="Value looks like a placeholder/default")

    if len(value) < min_length:
        return SecretCheck(name=name, status=SecretStatus.WEAK,
                           reason=f"Too short: {len(value)} chars (minimum {min_length})")

    return SecretCheck(name=name, status=SecretStatus.PRESENT)


# ---------------------------------------------------------------------------
# Secret definitions
# ---------------------------------------------------------------------------

_SECRET_DEFINITIONS = [
    # Database
    {"name": "POSTGRES_USER",     "required": True, "min_length": 1, "check_placeholder": True},
    {"name": "POSTGRES_PASSWORD", "required": True, "min_length": 8, "check_placeholder": True},
    {"name": "POSTGRES_HOST",     "required": True, "min_length": 1, "check_placeholder": False},
    {"name": "POSTGRES_DB",       "required": True, "min_length": 1, "check_placeholder": False},
    # Application security
    {"name": "SECRET_KEY",        "required": True, "min_length": _MIN_SECRET_LENGTH,
         "check_placeholder": True},
    # Email (optional in demo)
    {"name": "SMTP_HOST",         "required": False, "min_length": 1, "check_placeholder": False},
    {"name": "SMTP_USER",         "required": False, "min_length": 1, "check_placeholder": True},
    {"name": "SMTP_PASSWORD",     "required": False, "min_length": 1, "check_placeholder": True},
]

_DEMO_REQUIRED = ["SECRET_KEY"]  # minimum secrets even in demo mode


def validate_secrets(
    demo_mode: bool | None = None,
    definitions: list[dict] | None = None,
) -> SecretsReport:
    """Run all secret checks and return a SecretsReport.

    Args:
        demo_mode: If None, auto-detects from DEMO_MODE_ENABLED env var.
        definitions: Custom list of secret definitions (for testing).
    """
    if demo_mode is None:
        demo_mode = os.getenv("DEMO_MODE_ENABLED", "true").lower() in ("true", "1", "yes")

    defs = definitions or _SECRET_DEFINITIONS
    if demo_mode:
        # In demo mode, only check the truly essential secrets
        defs = [d for d in defs if d["name"] in _DEMO_REQUIRED]

    checks = [_check_secret(**d) for d in defs]
    return SecretsReport(checks=checks, demo_mode=demo_mode)


def assert_production_secrets() -> None:
    """Raise RuntimeError if any required production secret fails validation."""
    report = validate_secrets(demo_mode=False)
    if not report.is_production_ready:
        raise RuntimeError(
            f"Production secrets validation failed: {report.summary}\n"
            "Set all required environment variables before starting in production mode."
        )
