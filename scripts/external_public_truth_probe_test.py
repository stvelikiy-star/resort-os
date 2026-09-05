#!/usr/bin/env python3
from __future__ import annotations

import unittest

from external_public_truth_probe import REQUIRED_RENDERED_SNIPPETS, analyze_rendered_html, validate_target


class ExternalPublicTruthProbeTest(unittest.TestCase):
    def canonical_html(self) -> str:
        return "<html><body>" + "\n".join(REQUIRED_RENDERED_SNIPPETS) + "</body></html>"

    def test_canonical_rendered_surface_passes(self) -> None:
        self.assertEqual(analyze_rendered_html(self.canonical_html()), [])

    def test_stale_first_night_and_two_day_rule_fail(self) -> None:
        html = self.canonical_html() + " Предоплата за первые сутки. Без оплаты бронь снимается через 2 дня."
        errors = analyze_rendered_html(html)
        self.assertTrue(any("fixed first-night prepayment" in error for error in errors))
        self.assertTrue(any("stale two-day unpaid hold" in error for error in errors))

    def test_unverified_payment_provider_claims_fail(self) -> None:
        html = self.canonical_html() + " Visa и Mastercard онлайн на сайте. Оплата через Элсом."
        errors = analyze_rendered_html(html)
        self.assertTrue(any("unverified online card acquiring" in error for error in errors))
        self.assertTrue(any("unverified elsom payment route" in error for error in errors))

    def test_missing_required_truth_fails(self) -> None:
        errors = analyze_rendered_html("<html><body>Собственный пляж</body></html>")
        self.assertGreaterEqual(len(errors), 3)
        self.assertTrue(any("missing required rendered truth" in error for error in errors))

    def test_https_required_by_default(self) -> None:
        validate_target("https://staging.3korony.com/")
        with self.assertRaises(ValueError):
            validate_target("http://staging.3korony.com/")

    def test_credentials_in_url_are_forbidden(self) -> None:
        with self.assertRaises(ValueError):
            validate_target("https://user:secret@staging.3korony.com/")


if __name__ == "__main__":
    unittest.main()
