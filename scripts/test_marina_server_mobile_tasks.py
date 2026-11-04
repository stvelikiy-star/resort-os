"""P0 server-side mobile task contracts: fail closed without a connected hotel."""
import sys
from pathlib import Path
import unittest

from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "api"))
from app.operations import (
    HOUSEKEEPING_REQUIRED_CODES,
    HousekeepingChecklistItem, HousekeepingCompletionReport,
    TaskAssigneePatch, TaskCreate, allowed_types_for_user,
    has_full_operations_access, router,
)


def checked_items():
    return [
        {"code": code, "label": code, "done": True}
        for code in sorted(HOUSEKEEPING_REQUIRED_CODES)
    ]


class ServerMobileTaskContractTests(unittest.TestCase):
    def test_task_routes_are_registered_and_not_duplicate(self):
        paths = [route.path for route in router.routes]
        for path in ("/api/v1/ops/tasks/{task_id}/assignee",
                     "/api/v1/ops/tasks/{task_id}/complete-report"):
            self.assertEqual(paths.count(path), 1)

    def test_existing_task_create_remains_backward_compatible(self):
        payload = TaskCreate(type="HOUSEKEEPING", title="Test daily cleaning")
        self.assertIsNone(payload.assigned_to_id)
        self.assertEqual(payload.status if hasattr(payload, "status") else payload.type,
                         "HOUSEKEEPING")

    def test_assignment_requires_explicit_intent(self):
        with self.assertRaises(ValidationError):
            TaskAssigneePatch()
        self.assertIsNone(TaskAssigneePatch(assigned_to_id=None).assigned_to_id)
        with self.assertRaises(ValidationError):
            TaskAssigneePatch(assigned_to_id="foreign-text-not-uuid")

    def test_five_reviewed_checklist_items(self):
        self.assertEqual(
            HOUSEKEEPING_REQUIRED_CODES,
            {"BED_LINEN", "BATHROOM", "SURFACES", "AMENITIES", "FINAL_CHECK"},
        )
        data = HousekeepingCompletionReport(
            summary="Checked room after cleaning", checklist=checked_items(),
            evidence_urls=[],
        )
        self.assertEqual(len(data.checklist), 5)
        self.assertTrue(all(isinstance(i, HousekeepingChecklistItem) for i in data.checklist))

    def test_report_rejects_missing_checklist_and_unreviewed_uploads(self):
        with self.assertRaises(ValidationError):
            HousekeepingCompletionReport(summary="ok", checklist=checked_items()[:-1])
        with self.assertRaises(ValidationError):
            HousekeepingCompletionReport(
                summary="ok", checklist=checked_items(),
                evidence_urls=["https://unverified.example/test.jpg"],
            )
        with self.assertRaises(ValidationError):
            HousekeepingCompletionReport(summary=" ", checklist=checked_items())

    def test_custom_ops_still_cannot_promote_non_manager(self):
        for role in ("MAID", "TECHNICIAN", "RECEPTION", "WAITER", "COOK"):
            with self.subTest(role=role):
                user = {"role": role, "module_permissions_custom": True,
                        "module_permissions": ["OPS", "STAFF"]}
                self.assertFalse(has_full_operations_access(user))
                self.assertNotIn("GUEST_REQUEST", allowed_types_for_user(user))

    def test_manager_revocation_disables_assignment(self):
        for role in ("OWNER", "MANAGER"):
            user = {"role": role, "module_permissions_custom": True,
                    "module_permissions": ["PMS"]}
            self.assertFalse(has_full_operations_access(user))
            self.assertEqual(allowed_types_for_user(user), set())


if __name__ == "__main__":
    unittest.main()
