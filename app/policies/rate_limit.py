"""Rate limiting (token bucket per tool name).

Provides in-process rate limiting for tool execution to prevent
runaway loops from hammering external APIs. Uses a simple token
bucket algorithm: tokens refill at a fixed rate, and each tool
call consumes one token.
"""

from __future__ import annotations

import time


class RateLimiter:
    """Token bucket rate limiter.

    Each tool name gets its own bucket. Tokens refill at
    ``requests_per_minute / 60`` tokens per second, up to a burst
    of ``requests_per_minute`` tokens.

    Example::

        limiter = RateLimiter(requests_per_minute=60)
        if limiter.acquire("web_search"):
            # proceed with tool call
        else:
            # rate limited
    """

    def __init__(self, *, requests_per_minute: int = 60) -> None:
        if requests_per_minute < 1:
            raise ValueError("requests_per_minute must be >= 1")
        self._rpm = requests_per_minute
        self._refill_rate = requests_per_minute / 60.0  # tokens per second
        self._max_tokens = float(requests_per_minute)
        self._tokens: dict[str, float] = {}
        self._last_refill: dict[str, float] = {}

    def _refill(self, tool_name: str) -> None:
        now = time.monotonic()
        last = self._last_refill.get(tool_name, now)
        elapsed = now - last
        current = self._tokens.get(tool_name, self._max_tokens)
        new_tokens = min(current + elapsed * self._refill_rate, self._max_tokens)
        self._tokens[tool_name] = new_tokens
        self._last_refill[tool_name] = now

    def acquire(self, tool_name: str) -> bool:
        """Attempt to acquire a token for *tool_name*.

        Returns ``True`` if the call is allowed, ``False`` if rate limited.
        """
        self._refill(tool_name)
        current = self._tokens.get(tool_name, self._max_tokens)
        if current >= 1.0:
            self._tokens[tool_name] = current - 1.0
            return True
        return False

    def reset(self, tool_name: str | None = None) -> None:
        """Reset the bucket for *tool_name*, or all buckets if ``None``."""
        if tool_name is None:
            self._tokens.clear()
            self._last_refill.clear()
        else:
            self._tokens.pop(tool_name, None)
            self._last_refill.pop(tool_name, None)
