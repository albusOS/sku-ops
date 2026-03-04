"""Structured logging — JSON in deployed environments, pretty in development.

Usage in server.py:
    from shared.infrastructure.logging_config import setup_logging
    setup_logging()

All log records automatically include request_id / user_id / org_id when
the request_id middleware has set them in contextvars.
"""
from __future__ import annotations

import logging
import os
import sys
from contextvars import ContextVar

from pythonjsonlogger import jsonlogger

# ── Context vars (set by request_id middleware) ───────────────────────────────

request_id_var: ContextVar[str] = ContextVar("request_id", default="")
user_id_var: ContextVar[str] = ContextVar("user_id", default="")
org_id_var: ContextVar[str] = ContextVar("org_id", default="")


# ── Custom JSON formatter ─────────────────────────────────────────────────────

class ContextJsonFormatter(jsonlogger.JsonFormatter):
    """Injects request context into every JSON log line."""

    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict) -> None:
        super().add_fields(log_record, record, message_dict)
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        rid = request_id_var.get("")
        if rid:
            log_record["request_id"] = rid
        uid = user_id_var.get("")
        if uid:
            log_record["user_id"] = uid
        oid = org_id_var.get("")
        if oid:
            log_record["org_id"] = oid


# ── Pretty formatter for development ─────────────────────────────────────────

class DevFormatter(logging.Formatter):
    """Human-readable colored output for local development."""

    COLORS = {
        "DEBUG": "\033[36m",     # cyan
        "INFO": "\033[32m",      # green
        "WARNING": "\033[33m",   # yellow
        "ERROR": "\033[31m",     # red
        "CRITICAL": "\033[1;31m",  # bold red
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        rid = request_id_var.get("")
        prefix = f"[{rid[:8]}] " if rid else ""
        msg = super().format(record)
        return f"{color}{prefix}{msg}{self.RESET}"


# ── Setup ─────────────────────────────────────────────────────────────────────

def setup_logging() -> None:
    """Configure root logger. Call once at startup before any other logging."""
    from shared.infrastructure.config import is_deployed

    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    # Clear any existing handlers (e.g. from basicConfig)
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    if is_deployed:
        formatter = ContextJsonFormatter(
            fmt="%(asctime)s %(level)s %(logger)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    else:
        formatter = DevFormatter(
            fmt="%(asctime)s %(name)-25s %(levelname)-7s %(message)s",
            datefmt="%H:%M:%S",
        )

    handler.setFormatter(formatter)
    root.addHandler(handler)

    # Quiet noisy third-party loggers
    for name in ("uvicorn.access", "httpcore", "httpx", "asyncio"):
        logging.getLogger(name).setLevel(logging.WARNING)
