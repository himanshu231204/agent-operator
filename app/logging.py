"""Structured logging setup (PROJECT.md section 39, AGENTS.md section 19).

Every log line is structured JSON (or console-rendered in development) and
carries correlation identifiers (request_id, task_id, run_id, step_id,
tool_call_id) via structlog context binding. Secrets must never be logged;
callers are responsible for not passing sensitive values into log calls.
"""

from __future__ import annotations

import logging
import sys

import structlog

from app.config import Settings


def configure_logging(settings: Settings) -> None:
    """Configure stdlib logging + structlog for the whole process."""

    log_level = getattr(logging, settings.logging.level.upper(), logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer()
        if settings.logging.json_format
        else structlog.dev.ConsoleRenderer()
    )

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a structlog bound logger, optionally namespaced."""

    return structlog.get_logger(name)


def bind_context(**kwargs: object) -> None:
    """Bind correlation identifiers (request_id, task_id, run_id, ...) to context."""

    structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:
    structlog.contextvars.clear_contextvars()
