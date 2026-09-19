import hashlib
import json
import unittest
from datetime import datetime, timezone

from app.api.v1.coach import normalize_context, normalize_proposal, understand_response
from app.auth.registry import ClientRegistry
from app.core.cors import allowed_cors_origin, parse_cors_origins
from app.core.runtime import HubRuntime
from app.domain.models import Usage
from app.entitlements.registry import EntitlementRegistry, ProductRegistry
from app.entitlements.service import EntitlementService
from app.limits.guard import InMemoryUsageGuard
from app.providers.base import ProviderResult

TOKEN = "mmh_coach_bridge"
NOW = datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc)


def sha(v):
    return hashlib.sha256(v.encode()).hexdigest()


def clients(product="coach"):
    return json.dumps([{
        "client_id":"coach-install-1", "license_id":"COACH-001", "product_id":product,
        "token_sha256":sha(TOKEN), "enabled":True, "requests_per_minute":20, "daily_request_quota":200,
    }])


def products(product="coach", enabled=True):
    return json.dumps([{
        "product_id":product, "ai_enabled":enabled, "ai_mode":"AUTO", "allowed_profiles":["coach-understanding"],
    }])


def entitlements(product="coach", enabled=True):
    return json.dumps([{
        "license_id":"COACH-001", "product_id":product, "plan":"COACH_AI_TRIAL", "ai_enabled":enabled,
        "expires_at":"2026-12-31T23:59:59Z", "monthly_token_quota":1000,
    }])


class FakeAIService:
    def __init__(self, text):
        self.text = text
        self.calls = 0
        self.last_request = None
    def generate(self, request):
        self.calls += 1
        self.last_request = request
        return ProviderResult(text=self.text, usage=Usage(input_tokens=50, output_tokens=20, total_tokens=70), finish_reason="stop")


def runtime(text, product="coach", product_enabled=True, entitlement_enabled=True):
    ai = FakeAIService(text)
    rt = HubRuntime(
        registry=ClientRegistry.from_json(clients(product)),
        usage_guard=InMemoryUsageGuard(clock=lambda: NOW.timestamp()),
        ai_service=ai,
        entitlement_service=EntitlementService(
            ProductRegistry.from_json(products(product, product_enabled)),
            EntitlementRegistry.from_json(entitlements(product, entitlement_enabled)),
            now=lambda: NOW,
        ),
    )
    return rt, ai


def payload():
    return {
        "stage":"occ", "goal":"เข้าใจเหตุที่ทำให้เกิด", "process":"label_tape", "failure_mode":"misalignment",
        "known_facts":["Tape เกยขอบ", "เกิดหลังเปลี่ยนรุ่น"],
        "latest_answer":"พนักงานใหม่ยังไม่ชำนาญรุ่นนี้",
        "experience_refs":["เคสเก่า: model change; reference only"],
    }


class Phase4CoachBrowserBridgeTests(unittest.TestCase):
    def test_cors_allows_only_configured_origin(self):
        allowed = parse_cors_origins('["null","https://example.com"]')
        self.assertEqual(allowed_cors_origin("null", allowed), "null")
        self.assertEqual(allowed_cors_origin("https://example.com", allowed), "https://example.com")
        self.assertIsNone(allowed_cors_origin("https://evil.example", allowed))

    def test_context_is_bounded_and_requires_latest_answer(self):
        c = normalize_context(payload())
        self.assertEqual(c["stage"], "occ")
        self.assertEqual(len(c["experience_refs"]), 1)
        with self.assertRaises(Exception):
            normalize_context({"stage":"occ", "latest_answer":""})

    def test_understand_uses_locked_coach_profile_and_system_prompt(self):
        text = json.dumps({"intent":"answer","answerType":"cause","entities":["new_operator"],"relevance":0.9,"ambiguities":[],"contradictions":[],"questionCandidates":["รุ่นนี้ต่างจากรุ่นเดิมตรงไหนที่ทำให้แยกยาก?"],"reasoningGaps":[],"confidence":0.88}, ensure_ascii=False)
        rt, ai = runtime(text)
        status, body = understand_response(rt, payload(), f"Bearer {TOKEN}")
        self.assertEqual(status, 200)
        self.assertFalse(body["trusted"])
        self.assertEqual(body["proposal"]["answerType"], "cause")
        self.assertEqual(ai.calls, 1)
        self.assertEqual(ai.last_request.profile, "coach-understanding")
        self.assertEqual(ai.last_request.messages[0].role, "system")
        self.assertIn("must NOT decide the root cause", ai.last_request.messages[0].content)

    def test_forbidden_provider_fields_are_discarded(self):
        text = json.dumps({"intent":"answer","answerType":"cause","rootCause":"operator training","recommendedAction":"train","gatePass":True,"stageAdvance":"root","confidence":0.9})
        rt, _ = runtime(text)
        status, body = understand_response(rt, payload(), f"Bearer {TOKEN}")
        self.assertEqual(status, 200)
        self.assertNotIn("rootCause", body["proposal"])
        self.assertNotIn("recommendedAction", body["proposal"])
        self.assertNotIn("gatePass", body["proposal"])
        self.assertNotIn("stageAdvance", body["proposal"])

    def test_invalid_provider_json_fails_safely(self):
        rt, _ = runtime("not-json")
        status, body = understand_response(rt, payload(), f"Bearer {TOKEN}")
        self.assertEqual(status, 503)
        self.assertEqual(body["error"]["code"], "PROVIDER_UNAVAILABLE")

    def test_non_coach_product_cannot_use_coach_endpoint(self):
        rt, ai = runtime('{}', product="other")
        status, body = understand_response(rt, payload(), f"Bearer {TOKEN}")
        self.assertEqual(status, 403)
        self.assertEqual(body["error"]["code"], "PROFILE_NOT_ALLOWED")
        self.assertEqual(ai.calls, 0)

    def test_entitlement_off_blocks_before_provider(self):
        rt, ai = runtime('{}', entitlement_enabled=False)
        status, body = understand_response(rt, payload(), f"Bearer {TOKEN}")
        self.assertEqual(status, 403)
        self.assertEqual(body["error"]["code"], "AI_ENTITLEMENT_DISABLED")
        self.assertEqual(ai.calls, 0)

    def test_usage_is_recorded_on_understanding_call(self):
        rt, _ = runtime('{"intent":"answer","answerType":"fact","confidence":0.8}')
        self.assertEqual(understand_response(rt, payload(), f"Bearer {TOKEN}")[0], 200)
        client = rt.registry.authenticate(f"Bearer {TOKEN}")
        usage = rt.usage_guard.monthly_usage(client, 1000)
        self.assertEqual(usage["used_tokens"], 70)

    def test_normalizer_bounds_scores_and_lists(self):
        p = normalize_proposal({"intent":"bad","answerType":"bad","relevance":7,"confidence":-2,"entities":["a"],"questionCandidates":["q1","q2","q3","q4"]})
        self.assertEqual(p["intent"], "other")
        self.assertEqual(p["answerType"], "other")
        self.assertEqual(p["relevance"], 1.0)
        self.assertEqual(p["confidence"], 0.0)
        self.assertEqual(len(p["questionCandidates"]), 3)


if __name__ == "__main__":
    unittest.main()
