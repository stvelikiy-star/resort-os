#!/usr/bin/env python3
"""Offline Finik merchant QR contract. No network, merchant keys or live money."""
from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "api"))
from app.flex_qr_provider import (  # noqa: E402
    FinikMerchantConfig,
    build_finik_qr_intent,
    parse_unverified_finik_webhook,
)

INVOICE = "00000000-0000-0000-0000-00000000000a"
INTENT = "00000000-0000-0000-0000-00000000000b"
MERCHANT = FinikMerchantConfig(
    account_id="ci-only-merchant-id",
    display_name="MARINA FLEX",
    callback_url="https://billing.ms.go.kg/api/webhooks/finik",
    return_url="https://billing.ms.go.kg/billing/receipt",
    merchant_hostname="billing.ms.go.kg",
)


class VerifiedInvoiceToQrDraft(unittest.TestCase):
    def qr(self, *, config=MERCHANT, amount=Decimal("11300.50"), approved=True, lang="ru"):
        return build_finik_qr_intent(
            invoice_id=INVOICE, payment_intent_id=INTENT,
            verified_issued_invoice=approved,
            outstanding_kg=amount, config=config, language=lang,
        )

    def test_full_payload_is_not_an_issued_qr_or_payment(self):
        draft = self.qr()
        self.assertEqual(draft.provider, "FINIK_WEB_SDK")
        self.assertEqual(draft.amount_kg, Decimal("11300.50"))
        self.assertIsNone(draft.payment_page_url)
        self.assertFalse(draft.confirmed)
        self.assertEqual(draft.request_body["PaymentId"], INTENT)
        self.assertEqual(draft.request_body["Amount"], Decimal("11300.50"))
        self.assertEqual(draft.request_body["CardType"], "FINIK_QR")
        self.assertEqual(draft.request_body["Data"]["webhookUrl"], MERCHANT.callback_url)
        self.assertEqual(draft.request_body["Lang"], "ru")

    def test_kyrgyz_russian_english_only(self):
        for code in ("ru", "ky", "en"):
            self.assertEqual(self.qr(lang=code).request_body["Lang"], code)
        with self.assertRaises(ValueError):
            self.qr(lang="fr")

    def test_never_create_qr_for_unissued_or_unpaid_invoice(self):
        for amount,approved in ((Decimal("100"),False),(Decimal("0"),True),(Decimal("-1"),True)):
            with self.subTest(amount=amount,approved=approved):
                with self.assertRaises(ValueError):
                    self.qr(amount=amount,approved=approved)

    def test_reject_open_redirect_and_insecure_webhook(self):
        invalid = (
            replace(MERCHANT, callback_url="http://billing.ms.go.kg/api/webhooks/finik"),
            replace(MERCHANT, return_url="https://evil.example/login"),
            replace(MERCHANT, callback_url="https://billing.ms.go.kg.evil.com/webhooks"),
            replace(MERCHANT, callback_url="https://billing.ms.go.kg@evil.com/webhooks"),
            replace(MERCHANT, callback_url="https://billing.ms.go.kg/api/webhooks?token=secret"),
            replace(MERCHANT, callback_url="https://billing.ms.go.kg/api/webhooks#token"),
            replace(MERCHANT, merchant_hostname="evil.com"),
        )
        for config in invalid:
            with self.subTest(config=config), self.assertRaises(ValueError):
                self.qr(config=config)

    def test_wrong_server_origin_ids_and_unbounded_amount(self):
        with self.assertRaises(ValueError):
            build_finik_qr_intent(
                invoice_id="untrusted", payment_intent_id=INTENT,
                verified_issued_invoice=True, outstanding_kg=Decimal("10"),
                config=MERCHANT,
            )
        with self.assertRaises((TypeError,ValueError)):
            self.qr(amount=1.5)


class WebhookStaysUnverified(unittest.TestCase):
    def webhook(self, status="success", amount="125.00"):
        return {
            "id": "operation_001_DEBIT",
            "transactionId": "provider-event-001",
            "status": status,
            "amount": amount,
            "fields": {"paymentId": INTENT},
        }

    def test_success_claim_is_not_verified_bank_cash(self):
        untrusted = parse_unverified_finik_webhook(self.webhook())
        self.assertEqual(untrusted.claimed_status, "success")
        self.assertEqual(untrusted.provider_transaction_id, "provider-event-001")
        self.assertEqual(untrusted.requested_payment_id, INTENT)
        self.assertEqual(untrusted.claimed_amount, Decimal("125.00"))
        self.assertEqual(untrusted.verification_state, "UNTRUSTED")

    def test_cancelled_claim_still_unverified(self):
        self.assertEqual(
            parse_unverified_finik_webhook(self.webhook(status="CANCELED")).verification_state,
            "UNTRUSTED",
        )

    def test_forged_or_malformed_webhook_never_accepted(self):
        invalid = (
            {},
            {"fields": {"paymentId": INTENT}, "amount": "50", "status": "success"},
            {**self.webhook(), "transactionId": ""},
            {**self.webhook(), "fields": {"paymentId": "forged"}},
            {**self.webhook(), "amount": "0"},
            {**self.webhook(), "amount": 2.5},
            {**self.webhook(), "amount": -2},
        )
        for payload in invalid:
            with self.subTest(payload=payload), self.assertRaises((TypeError, ValueError)):
                parse_unverified_finik_webhook(payload)


if __name__ == "__main__":
    unittest.main(verbosity=2)
