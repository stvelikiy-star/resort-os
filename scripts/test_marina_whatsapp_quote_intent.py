"""Offline WhatsApp quote extraction regression tests."""
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "api"))
from app.whatsapp_quote_intent import extract_quote_intent

TODAY = date(2026, 11, 27)


def message(text, direction="INBOUND", content_type="TEXT"):
    return {"text": text, "direction": direction, "content_type": content_type}


class QuoteIntentTests(unittest.TestCase):
    def extract(self, text):
        return extract_quote_intent([message(text)], TODAY)

    def test_russian_explicit(self):
        result = self.extract("С 05.12.2026 по 07.12.2026, 2 взрослых, 1 ребёнок")
        self.assertEqual(result, {"intent": "availability", "search": {
            "check_in": "2026-12-05", "check_out": "2026-12-07", "adults": 2, "children": 1}})

    def test_english_no_children(self):
        result = self.extract("2026-12-05 to 2026-12-07, 2 adults, no children")
        self.assertEqual(result["search"]["children"], 0)

    def test_kyrgyz_explicit(self):
        result = self.extract("2026-12-05 чейин 2026-12-07, 2 чоң киши, 1 бала")
        self.assertEqual(result["search"]["children"], 1)

    def test_consecutive_guest_messages(self):
        result = extract_quote_intent([
            message("05.12.2026 — 07.12.2026"),
            message("2 взрослых без детей")], TODAY)
        self.assertEqual(result["intent"], "availability")

    def test_incomplete_or_ambiguous(self):
        for text in (
            "5–7 декабря, 2 взрослых, без детей",
            "2026-12-05 to 2026-12-07, 2 adults",
            "2026-12-05 to 2026-12-07, 2 adults or 3 adults, no children",
            "2026-12-05 to 2026-12-07, 2 adults, 1 child, no children",
            "2026-12-05 to 2026-12-07 or 2026-12-10, 2 adults, no children",
            "2026-12-05 to 2026-12-07, 0 adults, no children",
            "2026-12-07 to 2026-12-05, 2 adults, no children",
            "2026-11-01 to 2026-11-02, 2 adults, no children",
            "2026-12-05 to 2027-04-07, 2 adults, no children",
            "31.02.2027 по 05.03.2027, 2 взрослых, без детей",
        ):
            with self.subTest(text=text):
                self.assertIsNone(self.extract(text)["search"])

    def test_staff_handoff_overrides_quote(self):
        for text in ("Верните оплату", "Please cancel my reservation", "Нужен администратор",
                     "Refund: 2026-12-05 to 2026-12-07, 2 adults, no children"):
            self.assertEqual(self.extract(text), {"intent": "staff_review", "search": None})

    def test_ignore_old_and_assistant_data(self):
        result = extract_quote_intent([
            message("2026-12-05 to 2026-12-07, 2 adults, no children"),
            message("Please confirm", "OUTBOUND"),
            message("Actually, different dates")], TODAY)
        self.assertIsNone(result["search"])

    def test_ignore_non_text(self):
        self.assertEqual(extract_quote_intent([message("2026-12-05 to 2026-12-07, 2 adults, no children", content_type="IMAGE")], TODAY)["intent"], "clarify")

    def test_public_faq(self):
        self.assertEqual(self.extract("Есть парковка?"), {"intent": "consultation", "search": None})


if __name__ == "__main__":
    unittest.main()
