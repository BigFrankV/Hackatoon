from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from time import monotonic


class InMemoryRateLimiter:
    """Simple in-process sliding-window rate limiter.

    Limitations: state is local to the process and not shared across workers.
    This is acceptable for single-process development/small deployments; use
    Redis or equivalent for multi-worker production.
    """

    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def hit(self, key: str, *, limit: int, window_seconds: int) -> bool:
        """Register a hit and return True when the request is allowed."""
        now = monotonic()
        cutoff = now - window_seconds
        async with self._lock:
            bucket = self._events[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                return False
            bucket.append(now)
            return True

    async def reset(self) -> None:
        async with self._lock:
            self._events.clear()


login_rate_limiter = InMemoryRateLimiter()
