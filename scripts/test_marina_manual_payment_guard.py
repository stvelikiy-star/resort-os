"""Static release guard: MARINA manual payments opt-in, QR disabled end-to-end."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class ManualPaymentGuard(unittest.TestCase):
    def test_manual_methods_without_qr(self):
        ui = (ROOT / "apps/admin/components/ReservationFolioPanel.tsx").read_text()
        api = (ROOT / "services/api/app/reservation_payments.py").read_text()
        compose = (ROOT / "compose.marina-fleet.yaml").read_text()
        for method in ("CASH", "CARD_POS", "BANK_TRANSFER", "OTHER"):
            self.assertIn(f'["{method}",', ui)
            self.assertIn(f'"{method}"', api)
        self.assertNotIn('["QR_CASHLESS",', ui)
        self.assertIn("PAYMENT_METHOD_NOT_ALLOWED", api)
        self.assertIn('ENABLE_SERVICE_POINT_QR: "false"', compose)
        self.assertIn('ENABLE_MKASSA: "false"', compose)
        self.assertIn("MARINA_FLEET_ENABLE_MANUAL_PAYMENTS:-false", compose)

if __name__ == "__main__":
    unittest.main()
