import unittest
from pathlib import Path

from app.main import VERSION, coach_html_body, coach_html_path, health_body, route_path


class Phase5SameOriginCoachTests(unittest.TestCase):
    def test_phase5_version_and_health(self):
        self.assertEqual(VERSION, "0.5.0-termux")
        self.assertEqual(health_body()["phase"], "coach-same-origin-v1")

    def test_route_path_ignores_query_string(self):
        self.assertEqual(route_path("/coach/?v=3"), "/coach/")
        self.assertEqual(route_path("/v1/ai/status?x=1"), "/v1/ai/status")

    def test_coach_html_is_bundled(self):
        path = coach_html_path()
        self.assertTrue(path.is_file())
        data = coach_html_body()
        self.assertIn(b"V2.0.3", data)
        self.assertIn(b"SAME-ORIGIN", data)

    def test_coach_html_uses_same_origin_hub(self):
        text = coach_html_body().decode("utf-8")
        self.assertIn("location.origin", text)
        self.assertIn("timeoutMs=15000", text)
        self.assertIn("AI Hub URL (", text)

    def test_coach_html_keeps_ai_guardrail(self):
        text = coach_html_body().decode("utf-8")
        self.assertIn("AI ไม่ตัดสินสาเหตุ", text)
        self.assertIn("trusted", text)


if __name__ == "__main__":
    unittest.main()
