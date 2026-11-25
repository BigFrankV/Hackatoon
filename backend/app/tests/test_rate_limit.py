from __future__ import annotations

import pytest

from app.core import rate_limit
from app.core.rate_limit import InMemoryRateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_removes_expired_keys_when_capacity_is_reached(monkeypatch):
    now = 0.0
    monkeypatch.setattr(rate_limit, "monotonic", lambda: now)
    limiter = InMemoryRateLimiter(max_entries=1, cleanup_interval_seconds=60)

    assert await limiter.hit("old-key", limit=10, window_seconds=60) is True
    assert await limiter.hit("new-key", limit=10, window_seconds=60) is False

    now = 61.0
    assert await limiter.hit("new-key", limit=10, window_seconds=60) is True
    assert "old-key" not in limiter._events
    assert len(limiter._events) == 1
