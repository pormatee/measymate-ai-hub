import hashlib
import json
import unittest

from app.api.v1.ai import generate_response
from app.auth.registry import ClientRegistry
from app.core.runtime import HubRuntime
from app.domain.models import Usage
from app.limits.guard import InMemoryUsageGuard
from app.providers.base import ProviderResult


TOKEN = "mmh_test_client_token_1234567890"


def registry_json(*, enabled=True, rpm=10, daily=100):
    digest = hashlib.sha256(TOKEN.encode("utf-8")).hexdigest()
    return json.dumps([{
        "client_id": "client-a",
        "product_id": "product-a",
        "token_sha256": digest,
        "enabled": enabled,
        "requests_per_minute": rpm,
        "daily_request_quota": daily,
    }])


class FakeAIService:
    def __init__(self):
        self.calls = 0

    def generate(self, request):
        self.calls += 1
        return ProviderResult(text="ok", usage=Usage(input_tokens=2, output_tokens=1, total_tokens=3), finish_reason="stop")


def make_runtime(*, enabled=True, rpm=10, daily=100, clock=None):
    ai = FakeAIService()
    runtime = HubRuntime(
        registry=ClientRegistry.from_json(registry_json(enabled=enabled, rpm=rpm, daily=daily)),
        usage_guard=InMemoryUsageGuard(clock=clock),
        ai_service=ai,
    )
    return runtime, ai


def payload(extra=None):
    data = {"profile": "standard", "messages": [{"role": "user", "content": "hello"}]}
    if extra:
        data.update(extra)
    return data


class Phase2Tests(unittest.TestCase):
    def test_missing_auth_is_401_before_provider(self):
        runtime, ai = make_runtime()
        status, body = generate_response(runtime, payload(), None)
        self.assertEqual(status, 401)
        self.assertEqual(body["error"]["code"], "UNAUTHORIZED")
        self.assertEqual(ai.calls, 0)

    def test_invalid_token_is_401_before_provider(self):
        runtime, ai = make_runtime()
        status, body = generate_response(runtime, payload(), "Bearer wrong")
        self.assertEqual(status, 401)
        self.assertEqual(body["error"]["code"], "UNAUTHORIZED")
        self.assertEqual(ai.calls, 0)

    def test_disabled_client_is_denied(self):
        runtime, ai = make_runtime(enabled=False)
        status, body = generate_response(runtime, payload(), f"Bearer {TOKEN}")
        self.assertEqual(status, 403)
        self.assertEqual(body["error"]["code"], "CLIENT_DISABLED")
        self.assertEqual(ai.calls, 0)

    def test_valid_token_calls_provider(self):
        runtime, ai = make_runtime()
        status, body = generate_response(runtime, payload(), f"Bearer {TOKEN}")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["usage"]["total_tokens"], 3)
        self.assertEqual(ai.calls, 1)

    def test_identity_spoof_is_denied_before_provider(self):
        runtime, ai = make_runtime()
        status, body = generate_response(runtime, payload({"product_id": "other-product"}), f"Bearer {TOKEN}")
        self.assertEqual(status, 403)
        self.assertEqual(body["error"]["code"], "IDENTITY_MISMATCH")
        self.assertEqual(ai.calls, 0)

    def test_rate_limit_blocks_before_provider(self):
        runtime, ai = make_runtime(rpm=1, daily=100, clock=lambda: 1000.0)
        first, _ = generate_response(runtime, payload(), f"Bearer {TOKEN}")
        second, body = generate_response(runtime, payload(), f"Bearer {TOKEN}")
        self.assertEqual(first, 200)
        self.assertEqual(second, 429)
        self.assertEqual(body["error"]["code"], "RATE_LIMITED")
        self.assertEqual(ai.calls, 1)

    def test_daily_quota_blocks_before_provider(self):
        runtime, ai = make_runtime(rpm=10, daily=1, clock=lambda: 1000.0)
        first, _ = generate_response(runtime, payload(), f"Bearer {TOKEN}")
        second, body = generate_response(runtime, payload(), f"Bearer {TOKEN}")
        self.assertEqual(first, 200)
        self.assertEqual(second, 429)
        self.assertEqual(body["error"]["code"], "QUOTA_EXCEEDED")
        self.assertEqual(ai.calls, 1)

    def test_empty_registry_fails_closed(self):
        ai = FakeAIService()
        runtime = HubRuntime(registry=ClientRegistry.from_json("[]"), usage_guard=InMemoryUsageGuard(), ai_service=ai)
        status, body = generate_response(runtime, payload(), f"Bearer {TOKEN}")
        self.assertEqual(status, 503)
        self.assertEqual(body["error"]["code"], "AUTH_NOT_CONFIGURED")
        self.assertEqual(ai.calls, 0)

    def test_registry_contains_hash_not_raw_token(self):
        raw = registry_json()
        self.assertNotIn(TOKEN, raw)
        self.assertIn(hashlib.sha256(TOKEN.encode("utf-8")).hexdigest(), raw)

    def test_invalid_request_does_not_call_provider(self):
        runtime, ai = make_runtime()
        status, body = generate_response(runtime, {"profile": "standard", "messages": []}, f"Bearer {TOKEN}")
        self.assertEqual(status, 400)
        self.assertEqual(body["error"]["code"], "INVALID_REQUEST")
        self.assertEqual(ai.calls, 0)


if __name__ == "__main__":
    unittest.main()
