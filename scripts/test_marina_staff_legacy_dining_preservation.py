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
 def test_waiter_gets_direct_shift_navigation(self):
  self.assertIn('user.role === "WAITER"',source)
  self.assertIn('href="/waiter"',source)
 def test_waiter_order_never_injects_stay_id(self):
  waiter=(Path(__file__).resolve().parents[1]/'apps/staff/components/WaiterEntry.tsx').read_text()
  kitchen=(Path(__file__).resolve().parents[1]/'services/api/app/kitchen.py').read_text()
  order=waiter.split('async function createOrder(',1)[1].split('if (checking)',1)[0]
  self.assertIn('table_id: orderTable',order)
  self.assertNotIn('stay_id:',order)
  self.assertIn('WAITER_TABLE_ORDER_ONLY',kitchen)
 def test_waiter_long_table_labels_fit_mobile(self):
  css=(Path(__file__).resolve().parents[1]/'apps/staff/components/WaiterEntry.module.css').read_text()
  self.assertRegex(css,r'\\.section select\\s*\\{[^}]*width:100%;[^}]*min-width:0;[^}]*max-width:100%;')
if __name__=='__main__':unittest.main()
