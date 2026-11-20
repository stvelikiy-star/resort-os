"""Chef OS: property-local aggregated occupancy, not guest PII."""
import unittest
from datetime import datetime, timezone
from pathlib import Path
import sys
import uuid
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"services"/"api"))
from app.dining_production_snapshots import aggregate_rows, source_fingerprint

NOW=datetime(2026,11,9,12,0,tzinfo=timezone.utc)
def entitlement(stay,stage,adult,child,idx):
    return {"id":uuid.UUID(int=idx),"stay_id":uuid.UUID(int=stay),"stay_status":stage,
            "adultPortions":adult,"childPortions":child,"updatedAt":NOW}

class ChefOccupancyContract(unittest.TestCase):
    def test_active_and_expected_portions_are_separate_and_sum_to_total(self):
        rows=[entitlement(1,"ACTIVE",2,1,1),entitlement(2,"PENDING",1,0,2)]
        result=aggregate_rows(rows)
        self.assertEqual(result["total_portions"],4)
        self.assertEqual(result["current_checked_in_total_portions"],3)
        self.assertEqual(result["current_expected_arrival_total_portions"],1)
        self.assertEqual(result["current_checked_in_stay_count"],1)
        self.assertEqual(result["current_expected_arrival_stay_count"],1)
        self.assertNotIn("stay_id",result)
        self.assertNotIn("guest_name",result)

    def test_two_entitlements_same_stay_count_one_stay(self):
        rows=[entitlement(1,"ACTIVE",2,0,1),entitlement(1,"ACTIVE",1,0,2)]
        result=aggregate_rows(rows)
        self.assertEqual(result["current_checked_in_total_portions"],3)
        self.assertEqual(result["current_checked_in_stay_count"],1)

    def test_pending_cannot_be_reported_as_checked_in(self):
        result=aggregate_rows([entitlement(3,"PENDING",2,2,1)])
        self.assertEqual(result["current_checked_in_total_portions"],0)
        self.assertEqual(result["current_checked_in_stay_count"],0)
        self.assertEqual(result["current_expected_arrival_total_portions"],4)

    def test_empty_day_is_zero_and_fingerprint_unchanged_by_stage(self):
        rows=[entitlement(1,"ACTIVE",1,0,1)]
        changed=[{**rows[0],"stay_status":"PENDING"}]
        self.assertEqual(source_fingerprint(rows),source_fingerprint(changed))
        self.assertEqual(aggregate_rows([])["current_checked_in_total_portions"],0)
        self.assertEqual(aggregate_rows([])["current_expected_arrival_total_portions"],0)

if __name__=="__main__":
    unittest.main()