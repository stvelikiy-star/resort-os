"""Strict fail-closed P0 accounting proposal contracts; no external DB required."""
import sys
import unittest
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services/api"))
from app.owner_accounting_journal import JournalLine, JournalProposal, fingerprint, validate_balanced


def proposal(**changes):
    payload = {
        "id": uuid.uuid4(), "source_type": "REVENUE_SOURCE",
        "source_id": uuid.uuid4(), "accounting_date": date(2026, 11, 16),
        "policy_version": "UNAPPROVED-v1", "reason": "Reconciliation only",
        "lines": [
            {"account_code": "1000", "side": "DEBIT", "amount_kgs": "333.3333"},
            {"account_code": "4000", "side": "CREDIT", "amount_kgs": "333.3333"},
        ],
    }
    payload.update(changes)
    return JournalProposal.model_validate(payload)


class ProposedAccountingJournalTests(unittest.TestCase):
    def test_exact_balancing(self):
        self.assertEqual(validate_balanced(proposal().lines), Decimal("333.3333"))

    def test_one_unit_difference_blocks(self):
        body = proposal(lines=[
            {"account_code": "1000", "side": "DEBIT", "amount_kgs": "333.3333"},
            {"account_code": "4000", "side": "CREDIT", "amount_kgs": "333.3332"},
        ])
        with self.assertRaises(ValueError):
            validate_balanced(body.lines)

    def test_fingerprint_does_not_depend_on_retry_operation_id(self):
        body = proposal()
        changed_id = body.model_copy(update={"id": uuid.uuid4()})
        self.assertEqual(fingerprint(body), fingerprint(changed_id))

    def test_modified_amount_changes_payload_fingerprint(self):
        body = proposal()
        edited = body.model_copy(update={"lines": [
            JournalLine(account_code="1000", side="DEBIT", amount_kgs=Decimal("100")),
            JournalLine(account_code="4000", side="CREDIT", amount_kgs=Decimal("100"))
        ]})
        self.assertNotEqual(fingerprint(body), fingerprint(edited))

    def test_explicit_source_allowlist(self):
        with self.assertRaises(ValueError):
            proposal(source_type="SUPPLIER_OBLIGATION")

    def test_rejects_invalid_decimal_and_float_precision(self):
        for amount in ("NaN", "Infinity", "1.00001", "-1"):
            with self.subTest(amount=amount):
                with self.assertRaises(ValueError):
                    JournalLine(account_code="1000", side="DEBIT", amount_kgs=amount)

    def test_cannot_confuse_proposal_with_posted_profit(self):
        self.assertNotIn("POSTED", ["PENDING_ACCOUNTANT_APPROVAL"])


if __name__ == "__main__":
    unittest.main()
