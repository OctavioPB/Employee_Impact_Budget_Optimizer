"""Structured logging configuration for EIBO.

Provides two logging profiles:
  - Production: JSON-structured output to stdout (machine-parseable)
  - Development: human-readable colored output

Usage:
    from utils.logging_config import configure_logging
    configure_logging(mode="production")   # or "development"
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any

# ---------------------------------------------------------------------------
# JSON formatter
# ---------------------------------------------------------------------------

class JsonFormatter(logging.Formatter):
    """Emit each log record as a single JSON object on stdout."""

    _RESERVED = {"message", "timestamp", "level", "logger", "module", "function", "line"}

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level":     record.levelname,
            "logger":    record.name,
            "module":    record.module,
            "function":  record.funcName,
            "line":      record.lineno,
            "message":   record.getMessage(),
        }

        # Attach any extra fields set by the caller
        for key, value in record.__dict__.items():
            if key not in self._RESERVED and not key.startswith("_") and key not in {
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "thread", "threadName", "exc_info", "exc_text",
            }:
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


# ---------------------------------------------------------------------------
# Human-readable dev formatter
# ---------------------------------------------------------------------------

_LEVEL_COLORS = {
    "DEBUG":    "\033[37m",    # grey
    "INFO":     "\033[36m",    # cyan
    "WARNING":  "\033[33m",    # yellow
    "ERROR":    "\033[31m",    # red
    "CRITICAL": "\033[35;1m",  # bright magenta
}
_RESET = "\033[0m"


class DevFormatter(logging.Formatter):
    """Colorized human-readable formatter for development."""

    _FMT = "{color}[{level:<8}]{reset} {ts}  {name:<35} {msg}"

    def format(self, record: logging.LogRecord) -> str:
        color = _LEVEL_COLORS.get(record.levelname, "")
        ts = datetime.fromtimestamp(record.created).strftime("%H:%M:%S.%f")[:-3]
        line = self._FMT.format(
            color=color, level=record.levelname, reset=_RESET,
            ts=ts, name=record.name[:35], msg=record.getMessage(),
        )
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def configure_logging(
    mode: str = "auto",
    level: str | None = None,
    root_logger: str = "",
) -> None:
    """Configure the root (or named) logger.

    Args:
        mode:        "production" | "development" | "auto".
                     "auto" reads LOG_MODE env var; defaults to development.
        level:       Log level string ("DEBUG", "INFO", etc.).
                     Falls back to LOG_LEVEL env var, then INFO.
        root_logger: Logger name to configure. Empty string = root logger.
    """
    if mode == "auto":
        mode = os.getenv("LOG_MODE", "development")

    resolved_level = getattr(
        logging,
        (level or os.getenv("LOG_LEVEL", "INFO")).upper(),
        logging.INFO,
    )

    handler = logging.StreamHandler(sys.stdout)
    if mode == "production":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(DevFormatter())

    log = logging.getLogger(root_logger)
    log.setLevel(resolved_level)
    log.handlers.clear()
    log.addHandler(handler)
    log.propagate = root_logger != ""


def get_logger(name: str) -> logging.Logger:
    """Return a named logger, inheriting root configuration."""
    return logging.getLogger(name)


def configure_production() -> None:
    """Shortcut: JSON structured logging at INFO level."""
    configure_logging(mode="production", level="INFO")


def configure_development() -> None:
    """Shortcut: colorized dev logging at DEBUG level."""
    configure_logging(mode="development", level="DEBUG")
