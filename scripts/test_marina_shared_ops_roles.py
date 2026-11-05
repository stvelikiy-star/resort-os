"""Negative contract: custom OPS module grants cannot promote a staff role."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "api"))
from app.operations import allowed_types_for_user, has_full_operations_access


class OpsRoleBoundaryTests(unittest.TestCase):
    def test_default_line_roles_see_only_their_task_types(self):
        expected = {"MAID": {"HOUSEKEEPING"}, "TECHNICIAN": {"MAINTENANCE"},
                    "COOK": set(), "WAITER": set(), "RECEPTION": set()}
        for role, types in expected.items():
            with self.subTest(role=role):
                user = {"role":role,"module_permissions_custom":False,
                        "module_permissions":[]}
                self.assertEqual(allowed_types_for_user(user),types)
                self.assertFalse(has_full_operations_access(user))

    def test_custom_ops_is_not_a_role_promotion(self):
        expected = {"MAID":{"HOUSEKEEPING"}, "TECHNICIAN":{"MAINTENANCE"},
                    "COOK":set(),"WAITER":set(),"RECEPTION":set(),"AGENT":set()}
        for role, types in expected.items():
            with self.subTest(role=role):
                user = {"role":role,"module_permissions_custom":True,
                        "module_permissions":["OPS","PMS","RESERVATIONS"]}
                self.assertEqual(allowed_types_for_user(user),types)
                self.assertFalse(has_full_operations_access(user),
                                 "Custom OPS is not manager authority")

    def test_revoked_ops_denies_all_task_types(self):
        for role in ("OWNER","MANAGER","MAID","TECHNICIAN","COOK"):
            with self.subTest(role=role):
                user={"role":role,"module_permissions_custom":True,
                      "module_permissions":["PMS"]}
                self.assertEqual(allowed_types_for_user(user),set())
                self.assertFalse(has_full_operations_access(user))

    def test_owners_and_managers_keep_management_authority_only_with_ops(self):
        for role in ("OWNER","MANAGER"):
            for custom in (False,True):
                with self.subTest(role=role,custom=custom):
                    user={"role":role,"module_permissions_custom":custom,
                          "module_permissions":["OPS"] if custom else []}
                    self.assertEqual(allowed_types_for_user(user),
                                     {"HOUSEKEEPING","MAINTENANCE","GUEST_REQUEST"})
                    self.assertTrue(has_full_operations_access(user))

    def test_unknown_roles_and_no_module_cannot_claim_management(self):
        for role in ("INVALID","",None):
            with self.subTest(role=role):
                user={"role":role,"module_permissions_custom":True,
                      "module_permissions":["OPS"]}
                self.assertEqual(allowed_types_for_user(user),set())
                self.assertFalse(has_full_operations_access(user))


if __name__ == "__main__":
    unittest.main()
