"""Pure deterministic nightly and kitchen-folio source qualification tests."""
import sys
import unittest
from datetime import date
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"services/api"))

from app.owner_delivered_revenue import allocate_nights,qualify_delivered_stay,classify_served_order


class DeliveredRevenueCandidates(unittest.TestCase):
    def test_1000_som_3_nights_split_exactly(self):
        start=date(2026,11,10);end=date(2026,11,13)
        entire=allocate_nights(1000,start,end,start,end)
        self.assertEqual([(d.isoformat(),v) for d,v in entire],
                         [("2026-11-10",334),("2026-11-11",333),("2026-11-12",333)])
        self.assertEqual(sum(n for _,n in entire),1000)
        self.assertEqual(allocate_nights(1000,start,end,start,start),[(start,334)])
        self.assertEqual(allocate_nights(1000,start,end,end,end),[])
        self.assertEqual(sum(n for _,n in allocate_nights(1000,start,end,date(2026,11,11),end)),666)

    def test_small_price_many_nights_has_no_spurious_cents(self):
        a=allocate_nights(1,date(2026,11,10),date(2026,11,13),
                          date(2026,11,10),date(2026,11,12))
        self.assertEqual([v for _,v in a],[1,0,0])

    def test_refuse_bad_night_source(self):
        for total,s,e in [(-1,date(2026,11,10),date(2026,11,11)),
                          (10,date(2026,11,10),date(2026,11,10))]:
            with self.assertRaises(ValueError):
                allocate_nights(total,s,e,s,e)

    def test_actual_delivery_must_match_booked_nights(self):
        row={"reservation_status":"CHECKED_OUT","stay_count":1,
             "stay_status":"CHECKED_OUT","actual_in":date(2026,11,10),
             "actual_out":date(2026,11,13),"has_room_assignment":True,
             "checkIn":date(2026,11,10),"checkOut":date(2026,11,13),
             "totalKgs":1000}
        self.assertIsNone(qualify_delivered_stay(row))
        self.assertEqual(qualify_delivered_stay({**row,"actual_in":date(2026,11,11)}),
                         "ACTUAL_NIGHTS_DIFFER_FROM_BOOKED_NIGHTS")
        self.assertEqual(qualify_delivered_stay({**row,"stay_count":0}),
                         "MISSING_OR_MULTIPLE_ACTUAL_STAYS")
        self.assertEqual(qualify_delivered_stay({**row,"has_room_assignment":False}),
                         "MISSING_PHYSICAL_ROOM_ASSIGNMENT")
        self.assertEqual(qualify_delivered_stay({**row,"stay_count":2}),
                         "MISSING_OR_MULTIPLE_ACTUAL_STAYS")

    def test_dining_order_is_single_source_and_cannot_add_linked_folio_again(self):
        d=date(2026,11,11)
        from uuid import uuid4
        id=uuid4()
        row={"id":id,"status":"SERVED","totalKgs":350,
             "folio_id":uuid4(),"folio_status":"OPEN",
             "source_type":"KITCHEN_ORDER","source_id":id,
             "folio_amount":350,"service_date":d,"served_local_date":d}
        self.assertIsNone(classify_served_order(row))
        self.assertEqual(classify_served_order({**row,"folio_amount":349}),
                         "FOLIO_AMOUNT_MISMATCH")
        self.assertEqual(classify_served_order({**row,"folio_status":"WAIVED"}),
                         "FOLIO_VOID_OR_WAIVED")
        self.assertEqual(classify_served_order({**row,"source_id":uuid4()}),
                         "FOLIO_SOURCE_MISMATCH")
        self.assertEqual(classify_served_order({**row,"folio_id":None}),
                         "SERVED_ORDER_NOT_LINKED_TO_FOLIO")
        self.assertEqual(classify_served_order({**row,"service_date":date(2026,11,12)}),
                         "FOLIO_SERVICE_DATE_MISMATCH")


if __name__=="__main__":
    unittest.main()
