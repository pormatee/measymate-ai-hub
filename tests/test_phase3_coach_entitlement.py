import hashlib
import json
import unittest
from datetime import datetime, timezone

from app.api.v1.ai import generate_response, status_response
from app.auth.registry import ClientRegistry
from app.core.runtime import HubRuntime
from app.domain.models import Usage
from app.entitlements.registry import EntitlementRegistry, ProductRegistry
from app.entitlements.service import EntitlementService
from app.limits.guard import InMemoryUsageGuard
from app.providers.base import ProviderResult

TOKEN_A = "mmh_coach_a"
TOKEN_B = "mmh_coach_b"
NOW_DT = datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc)
NOW_TS = NOW_DT.timestamp()

class FakeAIService:
    def __init__(self, total_tokens=3):
        self.calls = 0
        self.total_tokens = total_tokens
    def generate(self, request):
        self.calls += 1
        return ProviderResult(
            text="understood",
            usage=Usage(input_tokens=max(0, self.total_tokens - 1), output_tokens=1, total_tokens=self.total_tokens),
            finish_reason="stop",
        )

def token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def clients(two=False):
    items = [{
        "client_id":"coach-install-a",
        "license_id":"COACH-001",
        "product_id":"coach",
        "token_sha256":token_hash(TOKEN_A),
        "enabled":True,
        "requests_per_minute":20,
        "daily_request_quota":200,
    }]
    if two:
        items.append({
            "client_id":"coach-install-b",
            "license_id":"COACH-001",
            "product_id":"coach",
            "token_sha256":token_hash(TOKEN_B),
            "enabled":True,
            "requests_per_minute":20,
            "daily_request_quota":200,
        })
    return json.dumps(items)

def products(*, enabled=True, mode="AUTO", profiles=None):
    return json.dumps([{
        "product_id":"coach",
        "ai_enabled":enabled,
        "ai_mode":mode,
        "allowed_profiles":profiles or ["coach-understanding"],
    }])

def entitlements(*, ai_enabled=True, expires="2026-12-31T23:59:59Z", quota=100):
    return json.dumps([{
        "license_id":"COACH-001",
        "product_id":"coach",
        "plan":"COACH_AI_MONTHLY",
        "ai_enabled":ai_enabled,
        "expires_at":expires,
        "monthly_token_quota":quota,
    }])

def runtime(*, product_enabled=True, mode="AUTO", entitlement_enabled=True,
            expires="2026-12-31T23:59:59Z", quota=100, two_clients=False, total_tokens=3,
            profiles=None):
    ai = FakeAIService(total_tokens=total_tokens)
    service = EntitlementService(
        ProductRegistry.from_json(products(enabled=product_enabled, mode=mode, profiles=profiles)),
        EntitlementRegistry.from_json(entitlements(ai_enabled=entitlement_enabled, expires=expires, quota=quota)),
        now=lambda: NOW_DT,
    )
    return HubRuntime(
        registry=ClientRegistry.from_json(clients(two=two_clients)),
        usage_guard=InMemoryUsageGuard(clock=lambda: NOW_TS),
        ai_service=ai,
        entitlement_service=service,
    ), ai

def payload(profile="coach-understanding"):
    return {"profile":profile,"messages":[{"role":"user","content":"พนักงานเพิ่งทำรุ่นนี้ครั้งแรก"}],"options":{"max_output_tokens":120}}

class CoachEntitlementTests(unittest.TestCase):
    def test_status_active_coach_entitlement(self):
        rt, _ = runtime()
        status, body = status_response(rt, f"Bearer {TOKEN_A}")
        self.assertEqual(status, 200)
        self.assertTrue(body["ai"]["available"])
        self.assertEqual(body["product_id"], "coach")
        self.assertEqual(body["license_id"], "COACH-001")
        self.assertEqual(body["ai"]["mode"], "AUTO")
        self.assertEqual(body["ai"]["plan"], "COACH_AI_MONTHLY")
        self.assertEqual(body["ai"]["usage"]["quota_tokens"], 100)

    def test_product_kill_switch_off(self):
        rt, ai = runtime(product_enabled=False, mode="OFF")
        status, body = status_response(rt, f"Bearer {TOKEN_A}")
        self.assertEqual(status, 200)
        self.assertFalse(body["ai"]["available"])
        self.assertEqual(body["ai"]["reason"], "PRODUCT_AI_DISABLED")
        status2, body2 = generate_response(rt, payload(), f"Bearer {TOKEN_A}")
        self.assertEqual(status2, 403)
        self.assertEqual(body2["error"]["code"], "PRODUCT_AI_DISABLED")
        self.assertEqual(ai.calls, 0)

    def test_product_mode_off_is_kill_switch_even_if_enabled_flag_true(self):
        rt, ai = runtime(product_enabled=True, mode="OFF")
        status, body = generate_response(rt, payload(), f"Bearer {TOKEN_A}")
        self.assertEqual(status, 403)
        self.assertEqual(body["error"]["code"], "PRODUCT_AI_DISABLED")
        self.assertEqual(ai.calls, 0)

    def test_license_entitlement_off(self):
        rt, ai = runtime(entitlement_enabled=False)
        status, body = generate_response(rt, payload(), f"Bearer {TOKEN_A}")
        self.assertEqual(status, 403)
        self.assertEqual(body["error"]["code"], "AI_ENTITLEMENT_DISABLED")
        self.assertEqual(ai.calls, 0)

    def test_expired_entitlement(self):
        rt, ai = runtime(expires="2026-09-18T23:59:59Z")
        status, body = status_response(rt, f"Bearer {TOKEN_A}")
        self.assertEqual(status, 200)
        self.assertFalse(body["ai"]["available"])
        self.assertEqual(body["ai"]["reason"], "AI_ENTITLEMENT_EXPIRED")
        status2, body2 = generate_response(rt, payload(), f"Bearer {TOKEN_A}")
        self.assertEqual(status2, 403)
        self.assertEqual(body2["error"]["code"], "AI_ENTITLEMENT_EXPIRED")
        self.assertEqual(ai.calls, 0)

    def test_coach_profile_allowed(self):
        rt, ai = runtime()
        status, body = generate_response(rt, payload(), f"Bearer {TOKEN_A}")
        self.assertEqual(status, 200)
        self.assertEqual(body["product_id"], "coach")
        self.assertEqual(body["ai_mode"], "AUTO")
        self.assertEqual(ai.calls, 1)

    def test_profile_not_allowed_for_coach(self):
        rt, ai = runtime()
        status, body = generate_response(rt, payload("standard"), f"Bearer {TOKEN_A}")
        self.assertEqual(status, 403)
        self.assertEqual(body["error"]["code"], "PROFILE_NOT_ALLOWED")
        self.assertEqual(ai.calls, 0)

    def test_monthly_tokens_record_actual_provider_usage(self):
        rt, _ = runtime(quota=100, total_tokens=7)
        generate_response(rt, payload(), f"Bearer {TOKEN_A}")
        status, body = status_response(rt, f"Bearer {TOKEN_A}")
        self.assertEqual(status, 200)
        self.assertEqual(body["ai"]["usage"]["used_tokens"], 7)
        self.assertEqual(body["ai"]["usage"]["remaining_tokens"], 93)

    def test_monthly_quota_blocks_later_request(self):
        rt, ai = runtime(quota=5, total_tokens=3)
        self.assertEqual(generate_response(rt, payload(), f"Bearer {TOKEN_A}")[0], 200)
        self.assertEqual(generate_response(rt, payload(), f"Bearer {TOKEN_A}")[0], 200)
        status, body = generate_response(rt, payload(), f"Bearer {TOKEN_A}")
        self.assertEqual(status, 429)
        self.assertEqual(body["error"]["code"], "MONTHLY_TOKEN_QUOTA_EXCEEDED")
        self.assertEqual(ai.calls, 2)

    def test_status_reports_unavailable_when_monthly_quota_reached(self):
        rt, _ = runtime(quota=3, total_tokens=3)
        generate_response(rt, payload(), f"Bearer {TOKEN_A}")
        status, body = status_response(rt, f"Bearer {TOKEN_A}")
        self.assertEqual(status, 200)
        self.assertFalse(body["ai"]["available"])
        self.assertEqual(body["ai"]["reason"], "MONTHLY_TOKEN_QUOTA_EXCEEDED")
        self.assertEqual(body["ai"]["usage"]["remaining_tokens"], 0)

    def test_monthly_usage_shared_across_installations_same_license(self):
        rt, _ = runtime(two_clients=True, quota=100, total_tokens=9)
        generate_response(rt, payload(), f"Bearer {TOKEN_A}")
        status, body = status_response(rt, f"Bearer {TOKEN_B}")
        self.assertEqual(status, 200)
        self.assertEqual(body["ai"]["usage"]["used_tokens"], 9)

    def test_status_check_does_not_consume_tokens(self):
        rt, ai = runtime(quota=100)
        for _ in range(5):
            status_response(rt, f"Bearer {TOKEN_A}")
        status, body = status_response(rt, f"Bearer {TOKEN_A}")
        self.assertEqual(body["ai"]["usage"]["used_tokens"], 0)
        self.assertEqual(ai.calls, 0)

    def test_missing_entitlement_falls_back_without_provider(self):
        ai = FakeAIService()
        service = EntitlementService(
            ProductRegistry.from_json(products()),
            EntitlementRegistry.from_json("[]"),
            now=lambda: NOW_DT,
        )
        rt = HubRuntime(
            registry=ClientRegistry.from_json(clients()),
            usage_guard=InMemoryUsageGuard(clock=lambda: NOW_TS),
            ai_service=ai,
            entitlement_service=service,
        )
        status, body = status_response(rt, f"Bearer {TOKEN_A}")
        self.assertEqual(status, 200)
        self.assertFalse(body["ai"]["available"])
        self.assertEqual(body["ai"]["reason"], "NO_AI_ENTITLEMENT")
        status2, body2 = generate_response(rt, payload(), f"Bearer {TOKEN_A}")
        self.assertEqual(status2, 403)
        self.assertEqual(body2["error"]["code"], "AI_ENTITLEMENT_DISABLED")
        self.assertEqual(ai.calls, 0)

if __name__ == "__main__":
    unittest.main()
