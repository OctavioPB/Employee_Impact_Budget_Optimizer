"""Input sanitization utilities for EIBO.

All user-supplied strings and numeric values entering the platform pass
through these helpers before being used in queries, file paths, or HTML output.
Prevents XSS, path traversal, and injection vectors at the system boundary.
"""

from __future__ import annotations

import html
import re
import unicodedata
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_STRING_DEFAULT  = 500
_MAX_DEPT_NAME       = 100
_MAX_ROLE_TITLE      = 150
_MAX_FREE_TEXT       = 2_000

_MIN_BUDGET          = 0.0
_MAX_BUDGET          = 1_000_000_000.0   # 1 billion USD ceiling

# Patterns that signal injection attempts
_SQL_INJECTION_PATTERNS = re.compile(
    r"(--|;|\bDROP\b|\bINSERT\b|\bSELECT\b|\bUPDATE\b|\bDELETE\b"
    r"|\bUNION\b|\bEXEC\b|\bEXECUTE\b|\bxp_|\bCAST\b|\bCONVERT\b)",
    re.IGNORECASE,
)

_XSS_PATTERNS = re.compile(
    r"(<script|javascript:|on\w+=|<iframe|<object|<embed|<link|<meta)",
    re.IGNORECASE,
)

_PATH_TRAVERSAL_PATTERNS = re.compile(r"\.\./|\.\.\\|%2e%2e|%252e")

# Allowed characters for identifiers (UUIDs, employee IDs)
_UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
# Loose ID: alphanumeric + hyphen/underscore, 1–64 chars
_LOOSE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")


# ---------------------------------------------------------------------------
# String sanitizers
# ---------------------------------------------------------------------------

def sanitize_string(
    value: str,
    max_length: int = _MAX_STRING_DEFAULT,
    allow_html: bool = False,
    strip_newlines: bool = False,
) -> str:
    """General-purpose string sanitizer.

    - Normalises unicode to NFC
    - Strips leading/trailing whitespace
    - Truncates to max_length
    - HTML-escapes unless allow_html=True
    - Optionally collapses newlines to spaces
    """
    if not isinstance(value, str):
        value = str(value)
    value = unicodedata.normalize("NFC", value).strip()
    if strip_newlines:
        value = value.replace("\n", " ").replace("\r", " ")
    value = value[:max_length]
    if not allow_html:
        value = html.escape(value)
    return value


def sanitize_department_name(name: str) -> str:
    """Sanitize a department name: letters, numbers, spaces, hyphens only."""
    name = sanitize_string(name, max_length=_MAX_DEPT_NAME, strip_newlines=True)
    # Remove characters not suitable for a department label
    name = re.sub(r"[^A-Za-z0-9 &\-_/]", "", html.unescape(name)).strip()
    return name[:_MAX_DEPT_NAME]


def sanitize_role_title(title: str) -> str:
    """Sanitize a job title."""
    title = sanitize_string(title, max_length=_MAX_ROLE_TITLE, strip_newlines=True)
    title = re.sub(r"[^A-Za-z0-9 ,.\-_&']", "", html.unescape(title)).strip()
    return title[:_MAX_ROLE_TITLE]


def sanitize_free_text(text: str) -> str:
    """Sanitize free-text annotation/comment: allow printable chars, strip HTML."""
    return sanitize_string(text, max_length=_MAX_FREE_TEXT, allow_html=False)


# ---------------------------------------------------------------------------
# Identifier validators
# ---------------------------------------------------------------------------

def sanitize_employee_id(value: str) -> Optional[str]:
    """Return sanitized employee ID or None if the format is invalid.

    Accepts UUID format or a loose alphanumeric ID (1–64 chars).
    """
    value = value.strip()
    if _UUID_PATTERN.match(value) or _LOOSE_ID_PATTERN.match(value):
        return value
    return None


def sanitize_department_filter(dept: str) -> Optional[str]:
    """Return a safe department name suitable for use in query filters, or None."""
    cleaned = sanitize_department_name(dept)
    if not cleaned or len(cleaned) < 2:
        return None
    return cleaned


# ---------------------------------------------------------------------------
# Numeric sanitizers
# ---------------------------------------------------------------------------

def sanitize_budget_value(value: float | int | str) -> float:
    """Clamp a budget value to [_MIN_BUDGET, _MAX_BUDGET] and return as float."""
    try:
        v = float(str(value).replace(",", "").replace("$", ""))
    except (ValueError, TypeError):
        return 0.0
    return max(_MIN_BUDGET, min(_MAX_BUDGET, v))


def sanitize_percentage(value: float | int | str) -> float:
    """Clamp percentage to [0.0, 100.0]."""
    try:
        v = float(value)
    except (ValueError, TypeError):
        return 0.0
    return max(0.0, min(100.0, v))


def sanitize_positive_int(value: int | str, max_value: int = 100_000) -> int:
    """Sanitize to a non-negative integer in [0, max_value]."""
    try:
        v = int(float(str(value)))
    except (ValueError, TypeError):
        return 0
    return max(0, min(max_value, v))


# ---------------------------------------------------------------------------
# Threat detection
# ---------------------------------------------------------------------------

class ThreatDetected(ValueError):
    """Raised when a sanitization check detects an active attack pattern."""

    def __init__(self, threat_type: str, value: str) -> None:
        self.threat_type = threat_type
        super().__init__(f"{threat_type} pattern detected in input: {value[:80]!r}")


def assert_no_sql_injection(value: str) -> str:
    """Raise ThreatDetected if the string contains SQL injection patterns."""
    if _SQL_INJECTION_PATTERNS.search(value):
        raise ThreatDetected("SQL_INJECTION", value)
    return value


def assert_no_xss(value: str) -> str:
    """Raise ThreatDetected if the string contains XSS patterns."""
    if _XSS_PATTERNS.search(value):
        raise ThreatDetected("XSS", value)
    return value


def assert_no_path_traversal(value: str) -> str:
    """Raise ThreatDetected if the string contains path traversal patterns."""
    if _PATH_TRAVERSAL_PATTERNS.search(value):
        raise ThreatDetected("PATH_TRAVERSAL", value)
    return value


def is_safe_input(value: str) -> bool:
    """Return True if the value passes all threat checks."""
    try:
        assert_no_sql_injection(value)
        assert_no_xss(value)
        assert_no_path_traversal(value)
        return True
    except ThreatDetected:
        return False


def sanitize_and_validate(value: str, max_length: int = _MAX_STRING_DEFAULT) -> str:
    """Sanitize string and assert it contains no threat patterns.

    Raises ThreatDetected for active attack patterns.
    Returns sanitized, HTML-escaped string for safe use.
    """
    assert_no_sql_injection(value)
    assert_no_xss(value)
    assert_no_path_traversal(value)
    return sanitize_string(value, max_length=max_length)
