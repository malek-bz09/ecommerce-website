"""A small rate limiter: at most N requests per minute from one IP address.

Counts are kept in this process's memory. That's right for one server process;
with several processes or servers each keeps its own count, so a shared store
(e.g. Redis) would be needed then. See backend/README.md.
"""

import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import Request

from app.core.errors import AppError

WINDOW_SECONDS = 60


class RateLimiter:
    """Use as a dependency: Depends(RateLimiter("login", lambda: 5))."""

    # Shared by every limiter: {(name, ip): times of recent requests}
    _hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)
    _lock = threading.Lock()  # sync routes run in several threads at once

    def __init__(self, name: str, limit: Callable[[], int]):
        self.name = name
        self.limit = limit  # a function, so the number is read from settings when used

    def __call__(self, request: Request) -> None:
        ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        with self._lock:
            if len(self._hits) > 10_000:  # don't grow forever: drop IPs not seen recently
                for key in [k for k, v in self._hits.items() if not v or v[-1] <= now - WINDOW_SECONDS]:
                    del self._hits[key]
            hits = self._hits[(self.name, ip)]
            # Forget requests older than the window
            while hits and hits[0] <= now - WINDOW_SECONDS:
                hits.popleft()
            if len(hits) >= self.limit():
                retry_after = int(hits[0] + WINDOW_SECONDS - now) + 1
                raise AppError(429, "Too many attempts. Please wait a minute and try again.",
                               retryAfter=retry_after)
            hits.append(now)

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            cls._hits.clear()
