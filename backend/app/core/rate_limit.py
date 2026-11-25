from __future__ import annotations

import asyncio
from collections import deque
from time import monotonic


class InMemoryRateLimiter:
    """Simple in-process sliding-window rate limiter.

    Limitations: state is local to the process and not shared across workers.
    This is acceptable for single-process development/small deployments; use
    Redis or equivalent for multi-worker production.
    """

    def __init__(
        self,
        *,
        max_entries: int = 10_000,
        cleanup_interval_seconds: int = 60,
    ) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be positive")
        if cleanup_interval_seconds < 1:
            raise ValueError("cleanup_interval_seconds must be positive")
        self._events: dict[str, deque[float]] = {}
        self._windows: dict[str, int] = {}
        self._max_entries = max_entries
        self._cleanup_interval_seconds = cleanup_interval_seconds
        self._next_cleanup_at = 0.0
        self._lock = asyncio.Lock()

    def _prune_expired(self, now: float, *, force: bool = False) -> None:
        if not force and now < self._next_cleanup_at:
            return

        for key, bucket in list(self._events.items()):
            cutoff = now - self._windows[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if not bucket:
                del self._events[key]
                del self._windows[key]

        self._next_cleanup_at = now + self._cleanup_interval_seconds

    async def hit(self, key: str, *, limit: int, window_seconds: int) -> bool:
        """Register a hit and return True when the request is allowed."""
        now = monotonic()
        cutoff = now - window_seconds
        async with self._lock:
            self._prune_expired(now)
            bucket = self._events.get(key)
            if bucket is not None:
                self._windows[key] = window_seconds
            else:
                if len(self._events) >= self._max_entries:
                    self._prune_expired(now, force=True)
                if len(self._events) >= self._max_entries:
                    return False
                bucket = deque()
                self._events[key] = bucket
                self._windows[key] = window_seconds

            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                return False
            bucket.append(now)
            return True

    async def reset(self) -> None:
        async with self._lock:
            self._events.clear()
            self._windows.clear()
            self._next_cleanup_at = 0.0


login_rate_limiter = InMemoryRateLimiter()
