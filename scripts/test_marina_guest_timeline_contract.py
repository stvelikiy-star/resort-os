#!/usr/bin/env python3
"""Guest history must reference canonical payment and review rows, not duplicate them."""
import ast
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
crm=(ROOT/"services/api/app/guest_crm.py").read_text()
panel=(ROOT/"apps/admin/components/GuestCrmEnrichmentPanel.tsx").read_text()

class GuestHistoryTruth(unittest.TestCase):
    def test_existing_history_service_not_new_ledger(self):
        ast.parse(crm)
        self.assertIn('FROM payments p',crm)
        self.assertIn('JOIN reservations r ON r.id=p."reservationId"',crm)
        self.assertIn('WHERE r."propertyId"=$1 AND p."reservationId"=ANY($2::uuid[])',crm)
        self.assertIn('FROM guest_stay_reviews',crm)
        self.assertIn('"booking_payments": payments_by_reservation',crm)
        self.assertIn('LIMIT 150',crm)
        self.assertIn('[:5]',crm)
        self.assertNotIn('INSERT INTO payments',crm)
        self.assertNotIn('INSERT INTO guest_stay_reviews',crm)

    def test_finance_truth_and_caution_are_visible(self):
        self.assertIn('Оплаты связанной брони',panel)
        self.assertIn('это не означает, что платил именно данный гость',panel)
        self.assertIn('guest_review',panel)
        self.assertIn('booking_payments?',panel)
        self.assertIn('<details className="guest-crm-requests">',panel)

if __name__=="__main__":unittest.main()
