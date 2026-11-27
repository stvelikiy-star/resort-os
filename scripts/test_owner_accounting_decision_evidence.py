"""Fail-closed tests for immutable accounting approval evidence.

This is not a recognized-profit workflow; the decision endpoint must remain
disabled by default, scoped to staging, and unavailable in shared preview.
"""
import os
import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services/api"))
from app.owner_accounting_journal import JournalDecision, _decision_preview_guard


class AccountingDecisionEvidenceTests(unittest.TestCase):
    def test_decision_reason_is_nonblank(self):
        for reason in ("", " ", "  short ", "\n  "):
            with self.subTest(reason=reason):
                with self.assertRaises(ValueError):
                    JournalDecision(id=uuid.uuid4(), action="APPROVE", reason=reason)

    def test_unsupported_action_rejected(self):
        with self.assertRaises(ValueError):
            JournalDecision(id=uuid.uuid4(), action="POST_TO_LEDGER",
                            reason="Accounting posting must not be inferred")

    def test_guard_disabled_by_default(self):
        with patch.dict(os.environ, {
            "APP_ENV": "staging",
            "MARINA_SHARED_AUTH_PREVIEW_ENABLED": "false",
        }, clear=True):
            with self.assertRaises(HTTPException) as ctx:
                _decision_preview_guard()
            self.assertEqual(ctx.exception.status_code, 503)

    def test_guard_never_enabled_in_production(self):
        with patch.dict(os.environ, {
            "APP_ENV": "production",
            "MARINA_SHARED_AUTH_PREVIEW_ENABLED": "false",
            "MARINA_ACCOUNTING_DECISION_EVIDENCE_ENABLED": "true",
        }, clear=True):
            with self.assertRaises(HTTPException):
                _decision_preview_guard()

    def test_guard_rejects_shared_preview(self):
        with patch.dict(os.environ, {
            "APP_ENV": "staging",
            "MARINA_SHARED_AUTH_PREVIEW_ENABLED": "true",
            "MARINA_ACCOUNTING_DECISION_EVIDENCE_ENABLED": "true",
        }, clear=True):
            with self.assertRaises(HTTPException):
                _decision_preview_guard()

    def test_narrow_staging_gate(self):
        with patch.dict(os.environ, {
            "APP_ENV": "staging",
            "MARINA_SHARED_AUTH_PREVIEW_ENABLED": "false",
            "MARINA_ACCOUNTING_DECISION_EVIDENCE_ENABLED": "true",
        }, clear=True):
            self.assertIsNone(_decision_preview_guard())


if __name__ == "__main__":
    unittest.main()
