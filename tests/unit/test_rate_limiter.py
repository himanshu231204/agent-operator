"""Unit tests for rate limiter."""

from __future__ import annotations

import time

import pytest

from app.policies.rate_limit import RateLimiter


class TestRateLimiter:
    def test_initial_burst_allows_requests(self):
        limiter = RateLimiter(requests_per_minute=10)
        for _ in range(10):
            assert limiter.acquire("tool_a") is True

    def test_exceeding_burst_blocks(self):
        limiter = RateLimiter(requests_per_minute=5)
        for _ in range(5):
            assert limiter.acquire("tool_a") is True
        assert limiter.acquire("tool_a") is False

    def test_refill_after_time(self):
        limiter = RateLimiter(requests_per_minute=60)  # 1 token per second
        # Drain the bucket
        for _ in range(60):
            assert limiter.acquire("tool_a") is True
        assert limiter.acquire("tool_a") is False
        # Wait for refill
        time.sleep(1.1)
        assert limiter.acquire("tool_a") is True

    def test_separate_buckets_per_tool(self):
        limiter = RateLimiter(requests_per_minute=2)
        assert limiter.acquire("tool_a") is True
        assert limiter.acquire("tool_a") is True
        assert limiter.acquire("tool_a") is False
        # tool_b has its own bucket
        assert limiter.acquire("tool_b") is True

    def test_reset_single_bucket(self):
        limiter = RateLimiter(requests_per_minute=2)
        limiter.acquire("tool_a")
        limiter.acquire("tool_a")
        assert limiter.acquire("tool_a") is False
        limiter.reset("tool_a")
        assert limiter.acquire("tool_a") is True

    def test_reset_all_buckets(self):
        limiter = RateLimiter(requests_per_minute=2)
        limiter.acquire("tool_a")
        limiter.acquire("tool_a")
        limiter.acquire("tool_b")
        limiter.acquire("tool_b")
        limiter.reset()
        assert limiter.acquire("tool_a") is True
        assert limiter.acquire("tool_b") is True

    def test_invalid_rpm_raises(self):
        with pytest.raises(ValueError, match="requests_per_minute must be >= 1"):
            RateLimiter(requests_per_minute=0)
