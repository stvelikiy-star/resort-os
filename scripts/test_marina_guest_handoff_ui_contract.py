"""Static policy guards for the feature-flagged Guest AI confirmation flow.

This catches accidental removal of strict gates; NOT a substitute for browser E2E.
"""
import re
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
COMP=(ROOT/"apps/web/components/GuestAiAssistant.tsx").read_text()
PARENT=(ROOT/"apps/web/components/GuestConciergeRuntime.tsx").read_text()
SERVER=(ROOT/"services/api/app/guest_assistant.py").read_text()

class GuestHandoffUiSourceContract(unittest.TestCase):
    def test_opt_in_off_by_default(self):
        self.assertIn('NEXT_PUBLIC_MARINA_GUEST_HANDOFF_ENABLED === "true"', COMP)
        self.assertIn('HUMAN_HANDOFF_UI_ENABLED && option', COMP)

    def test_guest_consent_is_separate_from_ai_answer(self):
        self.assertIn("handoffConfirm", COMP)
        self.assertIn("requires_explicit_guest_action === true", COMP)
        self.assertIn("item.task_created === false", COMP)
        self.assertIn('!handoffConfirm || handoffBusy || handoffPending.current', COMP)
        self.assertIn('setHandoffConfirm(true)', COMP)
        self.assertIn('requestHumanHelp()', COMP)
        self.assertNotIn('requestHumanHelp();\n      setQuestion', COMP)

    def test_canonical_server_route_only(self):
        self.assertIn('/core/api/v1/guest-os/rooms/', COMP)
        self.assertIn('encodeURIComponent(token)}/requests', COMP)
        self.assertIn('JSON.stringify({ request_code: "ADMIN", description: handoffQuestion || null })', COMP)
        self.assertIn('response.status !== 201', COMP)
        self.assertIn('GUEST_REQUEST_DUPLICATE_ACTIVE', COMP)
        self.assertIn('No tools are available', SERVER)

    def test_parent_request_list_refreshed_without_auto_retry(self):
        self.assertIn('onHandoffRequested={() => { void loadRequests(); }}', PARENT)
        self.assertIn('no auto retry', COMP.lower())
        self.assertIn('setHandoffAvailable(false)', COMP)

    def test_four_existing_guest_languages_preserved(self):
        for locale in ("ru:", "kg:", "kz:", "en:"):
            self.assertIn(locale, COMP)
        for action in ("handoffNote", "confirm", "duplicate", "handoffError"):
            self.assertGreaterEqual(COMP.count(action),4)

if __name__=="__main__":
    unittest.main()
