"""OWNER per-menu/date cost provenance is an estimate, never booked COGS."""
import unittest
import uuid
from datetime import date
from decimal import Decimal
from app.owner_served_kitchen_cost_trace import reconcile_menu_day


class OwnerServedKitchenCostTraceTest(unittest.TestCase):
    def test_same_day_production_served_and_unallocated(self):
        menu = uuid.UUID("10000000-0000-4000-8000-000000000001")
        today = date(2026, 11, 24)
        data = reconcile_menu_day([
            {"menu_item_id": menu, "service_date": today, "meal_type": "LUNCH",
             "prepared_portions": 10, "deducted_portions": 10, "cost_kgs": Decimal("120")},
        ], [
            {"menu_item_id": menu, "service_date": today, "served_portions": 7},
        ])
        self.assertEqual(data["status"], "CANDIDATE_NOT_RECOGNIZED")
        self.assertFalse(data["batch_to_order_link_verified"])
        self.assertFalse(data["served_cost_is_accounting_cogs"])
        self.assertEqual(data["totals"]["production_cost_kgs"], "120.0000")
        self.assertEqual(data["totals"]["proportional_served_cost_candidate_kgs"], "84.0000")
        self.assertEqual(data["totals"]["unallocated_production_cost_candidate_kgs"], "36.0000")
        self.assertEqual(data["items"][0]["produced_not_matched_to_served_portions"], 3)

    def test_unproduced_portions_must_not_invent_cost(self):
        menu = uuid.UUID("10000000-0000-4000-8000-000000000001")
        today = date(2026, 11, 24)
        data = reconcile_menu_day([
            {"menu_item_id": menu, "service_date": today, "meal_type": "DINNER",
             "prepared_portions": 2, "deducted_portions": 2, "cost_kgs": Decimal("20")},
        ], [{"menu_item_id": menu, "service_date": today, "served_portions": 5}])
        self.assertEqual(data["totals"]["proportional_served_cost_candidate_kgs"], "20.0000")
        self.assertEqual(data["totals"]["served_without_same_day_production_portions"], 3)
        self.assertEqual(data["items"][0]["served_without_same_day_production_portions"], 3)

    def test_service_date_and_menu_are_not_cross_matched(self):
        menu = uuid.UUID("10000000-0000-4000-8000-000000000001")
        day = date(2026, 11, 24)
        other_day = date(2026, 11, 25)
        data = reconcile_menu_day([
            {"menu_item_id": menu, "service_date": day, "meal_type": "BREAKFAST",
             "prepared_portions": 4, "deducted_portions": 4, "cost_kgs": Decimal("40")},
        ], [{"menu_item_id": menu, "service_date": other_day, "served_portions": 4}])
        self.assertEqual(data["totals"]["proportional_served_cost_candidate_kgs"], "0.0000")
        self.assertEqual(data["totals"]["unallocated_production_cost_candidate_kgs"], "40.0000")
        self.assertEqual(data["totals"]["served_without_same_day_production_portions"], 4)

    def test_multiple_targets_same_item_date_not_double_counted(self):
        menu = uuid.UUID("10000000-0000-4000-8000-000000000001")
        day = date(2026, 11, 24)
        data = reconcile_menu_day([
            {"menu_item_id": menu, "service_date": day, "meal_type": "BREAKFAST",
             "prepared_portions": 4, "deducted_portions": 4, "cost_kgs": Decimal("40")},
            {"menu_item_id": menu, "service_date": day, "meal_type": "DINNER",
             "prepared_portions": 6, "deducted_portions": 6, "cost_kgs": Decimal("90")},
        ], [{"menu_item_id": menu, "service_date": day, "served_portions": 5}])
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["meal_type_count"], 2)
        self.assertEqual(data["totals"]["production_cost_kgs"], "130.0000")
        self.assertEqual(data["totals"]["proportional_served_cost_candidate_kgs"], "65.0000")
        self.assertEqual(data["totals"]["unallocated_production_cost_candidate_kgs"], "65.0000")

    def test_without_production_reports_unresolved_not_zero_cost_claim(self):
        menu = uuid.UUID("10000000-0000-4000-8000-000000000001")
        data = reconcile_menu_day([], [{"menu_item_id": menu,
            "service_date": date(2026, 11, 24), "served_portions": 2}])
        self.assertEqual(data["totals"]["served_without_same_day_production_portions"], 2)
        self.assertEqual(data["items"][0]["deducted_portions"], 0)
        self.assertFalse(data["items"][0]["batch_match_verified"])


if __name__ == "__main__":
    unittest.main()
