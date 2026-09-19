import threading
import time
from collections import defaultdict, deque

from app.auth.models import ClientContext
from app.core.errors import QuotaExceededError, RateLimitedError


class InMemoryUsageGuard:
    """Phase 2 development limiter.

    State is intentionally in memory for now. It resets when the Hub restarts.
    Production persistence belongs to the hardening/deployment phase.
    """

    def __init__(self, clock=None):
        self._clock = clock or time.time
        self._minute_windows = defaultdict(deque)
        self._daily_counts = defaultdict(int)
        self._lock = threading.Lock()

    def check_and_consume(self, client: ClientContext) -> None:
        now = float(self._clock())
        minute_cutoff = now - 60.0
        day_id = int(now // 86400)
        client_key = client.client_id

        with self._lock:
            window = self._minute_windows[client_key]
            while window and window[0] <= minute_cutoff:
                window.popleft()

            if len(window) >= client.requests_per_minute:
                raise RateLimitedError("Rate limit exceeded.")

            daily_key = (client_key, day_id)
            if self._daily_counts[daily_key] >= client.daily_request_quota:
                raise QuotaExceededError("Daily quota exceeded.")

            window.append(now)
            self._daily_counts[daily_key] += 1
