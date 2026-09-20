import unittest
from pathlib import Path

from app.main import coach_html_body


class CoachV204StabilityTests(unittest.TestCase):
    def setUp(self):
        self.text = coach_html_body().decode("utf-8")

    def test_v204_runtime_marker(self):
        self.assertIn("V2.0.4", self.text)
        self.assertIn("Verification Completeness", self.text)

    def test_verification_requires_three_parts(self):
        self.assertIn("function verificationAssessment", self.text)
        self.assertIn("hasTarget:!!x.target", self.text)
        self.assertIn("hasAmount:!!x.amount", self.text)
        self.assertIn("hasCriterion:!!x.criterion", self.text)
        self.assertIn("complete:!!x.target&&!!x.amount&&!!x.criterion", self.text)
        self.assertIn("ตอบเฉพาะส่วนที่ยังขาดได้ ไม่ต้องพิมพ์ใหม่ทั้งหมด", self.text)

    def test_100_unit_alone_is_not_used_as_pass_criterion(self):
        # Regression guard: a number belongs to amount/duration, not automatically to pass criterion.
        start = self.text.index("function verificationAssessment")
        end = self.text.index("function preventionIsSpecific", start)
        block = self.text[start:end]
        self.assertIn("x.amount", block)
        self.assertNotIn("const hasCriterion=/(\\d", block)

    def test_ai_understanding_timeout_is_longer_than_old_six_seconds(self):
        self.assertIn("AI_UNDERSTAND_TIMEOUT_MS=20000", self.text)
        self.assertNotIn('},6000);const p=body?.proposal', self.text)
        self.assertIn("AI ใช้เวลานานเกินกำหนด", self.text)

    def test_quota_falls_back_to_no_ai(self):
        self.assertIn("โควตา AI เดือนนี้หมดแล้ว", self.text)
        self.assertIn("Coach ใช้ No-AI ต่อ", self.text)

    def test_typo_normalization_keeps_original_case_data_path(self):
        self.assertIn("function normalizeCommonTypos", self.text)
        self.assertIn("ข้นขั้นตอน", self.text)
        self.assertIn("A to Shipping", self.text)


if __name__ == "__main__":
    unittest.main()
