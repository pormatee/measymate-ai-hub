import hashlib
import json
import unittest
from datetime import datetime, timezone

from app.api.v1.ai import generate_response
from app.auth.registry import ClientRegistry
from app.core.config import Settings
from app.core.runtime import HubRuntime
from app.domain.models import Usage
from app.entitlements.registry import EntitlementRegistry, ProductRegistry
from app.entitlements.service import EntitlementService
from app.limits.guard import InMemoryUsageGuard
from app.providers.base import ProviderResult
from app.providers.router import ProviderRouter


TOKEN = "mmh_cbi_semantic_profile"
NOW = datetime(2026, 9, 20, 0, 0, tzinfo=timezone.utc)


def sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class FakeAIService:
    def __init__(self):
        self.calls = 0
        self.last_request = None

    def generate(self, request):
        self.calls += 1
        self.last_request = request
        return ProviderResult(
            text='{"status":"UNDERSTOOD","intent":"search_place","slots":{"category":"vegetarian"},"confidence":0.9,"missing_information":[],"ambiguity":[]}',
            usage=Usage(input_tokens=20, output_tokens=10, total_tokens=30),
            finish_reason="stop",
        )


def make_runtime(*, profiles=None, product_id="locallife"):
    clients = json.dumps([{
        "client_id": "locallife-cbi-shadow-1",
        "license_id": "LOCALLIFE-CBI-SHADOW-001",
        "product_id": product_id,
        "token_sha256": sha(TOKEN),
        "enabled": True,
        "requests_per_minute": 20,
        "daily_request_quota": 200,
    }])

    products = json.dumps([{
        "product_id": product_id,
        "ai_enabled": True,
        "ai_mode": "AUTO",
        "allowed_profiles": profiles or ["cbi-semantic"],
    }])

    entitlements = json.dumps([{
        "license_id": "LOCALLIFE-CBI-SHADOW-001",
        "product_id": product_id,
        "plan": "CBI_SHADOW",
        "ai_enabled": True,
        "expires_at": "2026-12-31T23:59:59Z",
        "monthly_token_quota": 1000,
    }])

    ai = FakeAIService()

    runtime = HubRuntime(
        registry=ClientRegistry.from_json(clients),
        usage_guard=InMemoryUsageGuard(clock=lambda: NOW.timestamp()),
        ai_service=ai,
        entitlement_service=EntitlementService(
            ProductRegistry.from_json(products),
            EntitlementRegistry.from_json(entitlements),
            now=lambda: NOW,
        ),
    )
    return runtime, ai


class CBISemanticProfileTests(unittest.TestCase):
    def test_router_accepts_cbi_semantic_profile(self):
        settings = Settings()
        provider = ProviderRouter(settings).for_profile("cbi-semantic")
        self.assertIsNotNone(provider)

    def test_authenticated_product_can_use_cbi_semantic_when_entitled(self):
        runtime, ai = make_runtime()
        payload = {
            "profile": "cbi-semantic",
            "messages": [
                {
                    "role": "system",
                    "content": "CBI locked semantic-understanding prompt.",
                },
                {
                    "role": "user",
                    "content": '{"current_user_text":"หาร้านไม่กินเนื้อ"}',
                },
            ],
            "options": {"max_output_tokens": 700},
        }

        status, body = generate_response(
            runtime,
            payload,
            f"Bearer {TOKEN}",
        )

        self.assertEqual(status, 200)
        self.assertEqual(body["product_id"], "locallife")
        self.assertEqual(ai.calls, 1)
        self.assertEqual(ai.last_request.profile, "cbi-semantic")

    def test_profile_must_be_allowed_by_product_policy(self):
        runtime, ai = make_runtime(profiles=["standard"])

        status, body = generate_response(
            runtime,
            {
                "profile": "cbi-semantic",
                "messages": [
                    {"role": "user", "content": "test"},
                ],
            },
            f"Bearer {TOKEN}",
        )

        self.assertEqual(status, 403)
        self.assertEqual(body["error"]["code"], "PROFILE_NOT_ALLOWED")
        self.assertEqual(ai.calls, 0)

    def test_identity_stays_bound_to_bearer_token(self):
        runtime, ai = make_runtime()

        status, body = generate_response(
            runtime,
            {
                "profile": "cbi-semantic",
                "product_id": "other-product",
                "messages": [
                    {"role": "user", "content": "test"},
                ],
            },
            f"Bearer {TOKEN}",
        )

        self.assertEqual(status, 403)
        self.assertEqual(body["error"]["code"], "IDENTITY_MISMATCH")
        self.assertEqual(ai.calls, 0)


if __name__ == "__main__":
    unittest.main()
