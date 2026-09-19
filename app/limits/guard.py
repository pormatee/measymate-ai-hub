import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone

from app.auth.models import ClientContext
from app.core.errors import MonthlyTokenQuotaExceededError, QuotaExceededError, RateLimitedError

class InMemoryUsageGuard:
    """Development limiter.

    Request/rate state and monthly token counters are in memory and reset when
    the Hub restarts. Production persistence is required before paid rollout.
    """
    def __init__(self, clock=None):
        self._clock = clock or time.time
        self._minute_windows = defaultdict(deque)
        self._daily_counts = defaultdict(int)
        self._monthly_tokens = defaultdict(int)
        self._lock = threading.Lock()

    def _now(self) -> float:
        return float(self._clock())

    @staticmethod
    def _month_id(now: float) -> str:
        return datetime.fromtimestamp(now, tz=timezone.utc).strftime("%Y-%m")

    def check_and_consume_request(self, client: ClientContext, monthly_token_quota: int) -> None:
        now = self._now()
        minute_cutoff = now - 60.0
        day_id = int(now // 86400)
        month_id = self._month_id(now)
        client_key = client.client_id
        license_key = (client.license_id, client.product_id, month_id)
        with self._lock:
            window = self._minute_windows[client_key]
            while window and window[0] <= minute_cutoff:
                window.popleft()
            if len(window) >= client.requests_per_minute:
                raise RateLimitedError("Rate limit exceeded.")
            daily_key = (client_key, day_id)
            if self._daily_counts[daily_key] >= client.daily_request_quota:
                raise QuotaExceededError("Daily quota exceeded.")
            if self._monthly_tokens[license_key] >= monthly_token_quota:
                raise MonthlyTokenQuotaExceededError("Monthly AI token quota exceeded.")
            window.append(now)
            self._daily_counts[daily_key] += 1

    def record_tokens(self, client: ClientContext, total_tokens: int) -> None:
        if total_tokens < 0:
            return
        now = self._now()
        month_id = self._month_id(now)
        key = (client.license_id, client.product_id, month_id)
        with self._lock:
            self._monthly_tokens[key] += int(total_tokens)

    def monthly_usage(self, client: ClientContext, monthly_token_quota: int) -> dict:
        now = self._now()
        month_id = self._month_id(now)
        key = (client.license_id, client.product_id, month_id)
        with self._lock:
            used = int(self._monthly_tokens[key])
        remaining = max(0, int(monthly_token_quota) - used)
        return {
            "month": month_id,
            "used_tokens": used,
            "quota_tokens": int(monthly_token_quota),
            "remaining_tokens": remaining,
        }

    # Backward-compatible helper for Phase 2 tests/callers.
    def check_and_consume(self, client: ClientContext) -> None:
        self.check_and_consume_request(client, monthly_token_quota=2**63 - 1)
