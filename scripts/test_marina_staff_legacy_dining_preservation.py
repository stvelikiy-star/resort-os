"""Preserve previously existing DINING_STAFF portal entry only for single-property legacy sessions."""
from pathlib import Path
import re
import unittest

source=(Path(__file__).resolve().parents[1]/'apps/staff/components/StaffRoleGateway.tsx').read_text()
class LegacyDiningStaffPreservation(unittest.TestCase):
 def test_legacy_role_remains_recognized(self):
  self.assertRegex(source,r'OPERATIONAL_ROLES = new Set<Role>\(\[[^\]]*"DINING_STAFF"')
  self.assertIn('DINING_STAFF: "Питание"',source)
 def test_kitchen_navigation_kept_without_shared_grant(self):
  self.assertIn('mode === "single_property" && user.role === "DINING_STAFF"',source)
  self.assertIn('href="/kitchen"',source)
  self.assertIn('<GuestRequestShiftPanel />',source)
 def test_new_dining_roles_and_shared_boundaries_retained(self):
  for value in ('"COOK"','"WAITER"','isSharedDiningUser','module_permissions.includes("DINING")'):
   self.assertIn(value,source)
  shared=source.split('function isSharedDiningUser(',1)[1].split('export default function',1)[0]
  self.assertNotIn('DINING_STAFF',shared)
if __name__=='__main__':unittest.main()
