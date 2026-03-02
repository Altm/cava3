from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
from time import time


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    remaining: int
    retry_after_seconds: int
    reset_in_seconds: int


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, *, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        now = time()
        with self._lock:
            bucket = self._hits[key]
            cutoff = now - window_seconds
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            if len(bucket) >= limit:
                first_hit = bucket[0] if bucket else now
                retry_after = max(1, int((first_hit + window_seconds) - now))
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    retry_after_seconds=retry_after,
                    reset_in_seconds=retry_after,
                )

            bucket.append(now)
            remaining = max(0, limit - len(bucket))
            reset_in = window_seconds

            if len(self._hits) > 50000:
                self._cleanup(now=now, window_seconds=window_seconds)

            return RateLimitResult(
                allowed=True,
                remaining=remaining,
                retry_after_seconds=0,
                reset_in_seconds=reset_in,
            )

    def _cleanup(self, *, now: float, window_seconds: int) -> None:
        cutoff = now - window_seconds
        for key in list(self._hits.keys()):
            bucket = self._hits[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if not bucket:
                self._hits.pop(key, None)
