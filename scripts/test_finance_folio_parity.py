"""Folio charges are operational receivables, not automatically received payments."""
import unittest
from datetime import date
from uuid import uuid4
from services.api.app.hotel_finance import reservation_ledger_item

class FolioReceivables(unittest.TestCase):
    def row(self, *, status='GUARANTEED', accommodation=5000, extras=500, paid=0):
        return {'id':uuid4(),'bookingNumber':'TEST-ONLY','status':status,
                'checkIn':date(2026,12,6),'checkOut':date(2026,12,7),
                'totalKgs':accommodation,'extras_kgs':extras,'received_kgs':paid,
                'received_count':0,'last_received_at':None,'firstName':'ТЕСТ',
                'lastName':'MARINA','phone':'000','room_code':'TEST_ROOM'}
    def test_folio_extras_increase_receivable_not_received(self):
        a=reservation_ledger_item(self.row())
        self.assertEqual((a['accommodation_kgs'],a['extras_kgs'],a['total_kgs']), (5000,500,5500))
        self.assertEqual((a['received_kgs'],a['remaining_kgs']), (0,5500))
    def test_payment_is_subtracted_once(self):
        a=reservation_ledger_item(self.row(paid=2000))
        self.assertEqual((a['total_kgs'],a['remaining_kgs'],a['overpaid_kgs']), (5500,3500,0))
    def test_cancelled_accommodation_not_due(self):
        a=reservation_ledger_item(self.row(status='CANCELLED',paid=0,extras=0))
        self.assertEqual((a['total_kgs'],a['remaining_kgs']), (0,0))
    def test_overpayment(self):
        a=reservation_ledger_item(self.row(paid=6000))
        self.assertEqual((a['remaining_kgs'],a['overpaid_kgs']), (0,500))
if __name__=='__main__': unittest.main()
