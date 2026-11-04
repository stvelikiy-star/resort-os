"""P0 compatibility checks against the canonical task API (no test DB required)."""
import sys
from pathlib import Path
import unittest

from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "api"))
from app.operations import TaskCreate, allowed_types_for_user, has_full_operations_access
from app.operations_assignment import AssigneePatch
from app.staff_task_reports import (
    ChecklistItem, TaskCompletionReport, SHARED_HOUSEKEEPING_CODES,
)
from app.app_entry import app


def checked_items():
    return [{"code": code, "label": code, "done": True}
            for code in sorted(SHARED_HOUSEKEEPING_CODES)]


class ServerMobileTaskContractTests(unittest.TestCase):
    def test_exactly_one_canonical_route_per_method(self):
        routes = [(route.path, method) for route in app.routes
                  for method in getattr(route, "methods", ()) or ()]
        for method, path in (
            ("PATCH", "/api/v1/ops/tasks/{task_id}/assignee"),
            ("POST", "/api/v1/ops/tasks/{task_id}/complete-report"),
        ):
            self.assertEqual(routes.count((path, method)), 1,
                             "Duplicate server route could silently bypass RBAC")

    def test_task_create_keeps_legacy_optional_assignee(self):
        payload = TaskCreate(type="HOUSEKEEPING", title="Daily cleaning")
        self.assertIsNone(payload.assigned_to_id)
        self.assertEqual(payload.type, "HOUSEKEEPING")

    def test_assignment_requires_explicit_uuid_or_null(self):
        with self.assertRaises(ValidationError):
            AssigneePatch()
        self.assertIsNone(AssigneePatch(assigned_to_id=None).assigned_to_id)
        with self.assertRaises(ValidationError):
            AssigneePatch(assigned_to_id="URL-not-a-uuid")

    def test_shared_checklist_codes_match_mobile_contract(self):
        self.assertEqual(
            SHARED_HOUSEKEEPING_CODES,
            {"BED_LINEN", "BATHROOM", "SURFACES", "AMENITIES", "FINAL_CHECK"},
        )
        payload = TaskCompletionReport(
            summary="Checked room after cleaning", checklist=checked_items(),
            evidence_urls=[],
        )
        self.assertEqual(len(payload.checklist), 5)
        self.assertTrue(all(isinstance(item, ChecklistItem) for item in payload.checklist))

    def test_invalid_report_payloads_fail_validation(self):
        with self.assertRaises(ValidationError):
            TaskCompletionReport(summary=" ", checklist=checked_items())
        with self.assertRaises(ValidationError):
            TaskCompletionReport(summary="ok", checklist=checked_items(),
                                 evidence_urls=["file:///tmp/unsafe-photo.jpg"])
        with self.assertRaises(ValidationError):
            TaskCompletionReport(summary="ok", checklist=checked_items(),
                                 evidence_urls=["https://example.test/photo.jpg"] * 9)
        # Shared-specific photo and exact checklist denial is verified through
        # real isolated HTTP, not inferred from the legacy Pydantic model.

    def test_custom_grants_cannot_escalate_line_roles(self):
        for role in ("MAID", "TECHNICIAN", "RECEPTION", "WAITER", "COOK"):
            with self.subTest(role=role):
                user = {"role": role, "module_permissions_custom": True,
                        "module_permissions": ["OPS", "STAFF"]}
                self.assertFalse(has_full_operations_access(user))
                self.assertNotIn("GUEST_REQUEST", allowed_types_for_user(user))

    def test_management_revoke_denies_assignment(self):
        for role in ("OWNER", "MANAGER"):
            user = {"role": role, "module_permissions_custom": True,
                    "module_permissions": ["PMS"]}
            self.assertFalse(has_full_operations_access(user))
            self.assertEqual(allowed_types_for_user(user), set())


if __name__ == "__main__":
    unittest.main()
