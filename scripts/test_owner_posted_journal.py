"""Safety gates for the staged OWNER posted ledger."""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services/api"))
from app.owner_posted_journal import PostAccounting, guard


class PostingGuardTests(unittest.TestCase):
    def test_invalid_reason_rejected(self):
        with self.assertRaises(ValidationError):
            PostAccounting(id=uuid4(),action="POST",reason="       ")

    def test_invalid_action_rejected(self):
        with self.assertRaises(ValidationError):
            PostAccounting(id=uuid4(),action="APPROVE",reason="Independent review")

    def test_production_blocked_even_with_all_flags(self):
        env=dict(APP_ENV="production",MARINA_SHARED_AUTH_PREVIEW_ENABLED="false",
                 MARINA_ACCOUNTING_DECISION_EVIDENCE_ENABLED="true",
                 MARINA_ACCOUNTING_POSTING_ENABLED="true")
        with patch.dict(os.environ,env,clear=True),self.assertRaises(HTTPException) as r:
            guard()
        self.assertEqual(r.exception.status_code,503)

    def test_disabled_by_default(self):
        with patch.dict(os.environ,{"APP_ENV":"staging"},clear=True),self.assertRaises(HTTPException):
            guard()

    def test_shared_preview_blocked(self):
        env=dict(APP_ENV="staging",MARINA_SHARED_AUTH_PREVIEW_ENABLED="true",
                 MARINA_ACCOUNTING_DECISION_EVIDENCE_ENABLED="true",
                 MARINA_ACCOUNTING_POSTING_ENABLED="true")
        with patch.dict(os.environ,env,clear=True),self.assertRaises(HTTPException):
            guard()

    def test_explicit_isolated_staging_allowed(self):
        env=dict(APP_ENV="staging",MARINA_SHARED_AUTH_PREVIEW_ENABLED="false",
                 MARINA_ACCOUNTING_DECISION_EVIDENCE_ENABLED="true",
                 MARINA_ACCOUNTING_POSTING_ENABLED="true")
        with patch.dict(os.environ,env,clear=True):
            self.assertIsNone(guard())


if __name__=="__main__":
    unittest.main()
