"""
services/structured_logger.py — Structured JSON & Contextual Logging.

Adapted and evolved from reference_repos/short-video-maker
(src/logger.ts, src/config.ts - Pino JSON logger conventions).
Eliminates unstructured text console dumping and provides thread-safe,
machine-parseable JSON logs with ISO-8601 UTC timestamps, PID tracking,
and contextual metadata (task_id, scene_idx, duration_sec, render_phase)
while strictly redacting API secrets via services.log_sanitizer.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import sys
import traceback
from typing import Any, Dict, Optional

from services.log_sanitizer import sanitize_payload, sanitize_log


class JSONLogFormatter(logging.Formatter):
    """
    Formats LogRecords into single-line JSON objects adhering to Pino/Cloud logging standards:
    {
      "timestamp": "2026-09-27T15:30:00.123Z",
      "level": "INFO",
      "logger": "ffmpeg_graph",
      "message": "...",
      "pid": 1234,
      "thread": "MainThread",
      "extra": {...},
      "exception": {...}
    }
    """

    def __init__(self, sanitize: bool = True):
        super().__init__()
        self.sanitize = sanitize

    def format(self, record: logging.LogRecord) -> str:
        # Standard base attributes
        msg = record.getMessage()
        if self.sanitize:
            msg = sanitize_log(msg)

        iso_time = datetime.datetime.fromtimestamp(
            record.created, tz=datetime.timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        log_entry: Dict[str, Any] = {
            "timestamp": iso_time,
            "level": record.levelname,
            "logger": record.name,
            "message": msg,
            "pid": record.process,
            "thread": record.threadName,
        }

        # Extract extra structured context (exclude built-in record attributes)
        standard_attrs = {
            "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
            "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
            "created", "msecs", "relativeCreated", "thread", "threadName",
            "processName", "process", "message",
        }
        extra_fields: Dict[str, Any] = {}
        for key, value in record.__dict__.items():
            if key not in standard_attrs and not key.startswith("_"):
                extra_fields[key] = value

        if extra_fields:
            if self.sanitize:
                extra_fields = sanitize_payload(extra_fields)
            log_entry["context"] = extra_fields

        # Include exception stack traces if present
        if record.exc_info:
            exc_type, exc_val, exc_tb = record.exc_info
            log_entry["exception"] = {
                "type": getattr(exc_type, "__name__", str(exc_type)),
                "message": sanitize_log(str(exc_val)),
                "stack": [sanitize_log(line) for line in traceback.format_tb(exc_tb)],
            }

        return json.dumps(log_entry, ensure_ascii=False)


class TextLogFormatter(logging.Formatter):
    """
    Human-readable, aligned text console formatter for interactive development.
    """

    def __init__(self, sanitize: bool = True):
        fmt = "%(asctime)s [%(levelname)-7s] %(name)s (PID:%(process)d): %(message)s"
        datefmt = "%Y-%m-%d %H:%M:%S"
        super().__init__(fmt=fmt, datefmt=datefmt)
        self.sanitize = sanitize

    def format(self, record: logging.LogRecord) -> str:
        text = super().format(record)
        if self.sanitize:
            text = sanitize_log(text)
        return text


class StructuredLoggerAdapter(logging.LoggerAdapter):
    """
    Adapter that allows fluent binding of contextual parameters.
    Example:
      log = get_structured_logger("render_worker").bind(task_id="abc-123", scene=1)
      log.info("Processing scene")
    """

    def __init__(self, logger: logging.Logger, extra: Optional[Dict[str, Any]] = None):
        super().__init__(logger, extra or {})

    def process(self, msg: Any, kwargs: Any) -> tuple[Any, Any]:
        extra = dict(self.extra)
        if "extra" in kwargs:
            extra.update(kwargs["extra"])
        kwargs["extra"] = extra
        return msg, kwargs

    def bind(self, **kwargs: Any) -> StructuredLoggerAdapter:
        """Returns a new StructuredLoggerAdapter with additional merged context."""
        new_extra = dict(self.extra)
        new_extra.update(kwargs)
        return StructuredLoggerAdapter(self.logger, new_extra)


def get_structured_logger(name: str = "shorts_app", **context: Any) -> StructuredLoggerAdapter:
    """Creates or retrieves a logger wrapped in StructuredLoggerAdapter with bound context."""
    logger = logging.getLogger(name)
    return StructuredLoggerAdapter(logger, context)


def setup_structured_logging(
    level: str = "INFO",
    json_format: Optional[bool] = None,
    stream: Optional[Any] = None,
) -> logging.Handler:
    """
    Configures root logging with either JSONLogFormatter or TextLogFormatter.
    If json_format is None, checks environment variables:
      SHORTS_LOG_JSON=1 or LOG_FORMAT=json.
    """
    if json_format is None:
        env_val = os.getenv("SHORTS_LOG_JSON", os.getenv("LOG_FORMAT", "")).strip().lower()
        json_format = env_val in ("1", "true", "json")

    handler = logging.StreamHandler(stream or sys.stdout)
    if json_format:
        handler.setFormatter(JSONLogFormatter())
    else:
        handler.setFormatter(TextLogFormatter())

    root = logging.getLogger()
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root.setLevel(numeric_level)

    # Avoid duplicate handlers if reconfigured
    root.handlers = [h for h in root.handlers if not isinstance(h, logging.StreamHandler)]
    root.addHandler(handler)

    return handler
