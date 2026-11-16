"""Unit tests for documented OWNER corrections; not accounting recognition."""
import sys
import unittest
from decimal import Decimal
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"services/api"))
from app.owner_revenue_corrections import validate_correction, ALL_KINDS


def totals(**changes):
    base={k:Decimal('0') for k in ALL_KINDS}
    return {**base,**{k:Decimal(str(v)) for k,v in changes.items()}}


class DocumentedCorrectionTest(unittest.TestCase):
    def test_discount_and_cancellation_can_never_exceed_face_value(self):
        self.assertTrue(validate_correction('DISCOUNT','LODGING',
                         Decimal('100'),Decimal('333'),
                         totals(CANCELLATION='233')))
        with self.assertRaises(ValueError):
            validate_correction('CANCELLATION','LODGING',Decimal('234'),
                                Decimal('333'),totals(DISCOUNT='100'))

    def test_tax_and_package_are_classifiers_not_cash(self):
        self.assertTrue(validate_correction('PACKAGE_SPLIT','DINING',
                         Decimal('200'),Decimal('333'),totals(DISCOUNT='30')))
        self.assertTrue(validate_correction('TAX_COMPONENT','LODGING',
                         Decimal('20'),Decimal('333'),totals(DISCOUNT='30')))
        with self.assertRaises(ValueError):
            validate_correction('PACKAGE_SPLIT','UNALLOCATED',
                                Decimal('200'),Decimal('333'),totals())
        with self.assertRaises(ValueError):
            validate_correction('PACKAGE_SPLIT','DINING',
                                Decimal('304'),Decimal('333'),totals(DISCOUNT='30'))

    def test_refund_is_a_distinct_evidence_bucket(self):
        self.assertTrue(validate_correction('REFUND','UNALLOCATED',
                         Decimal('50'),Decimal('100'),totals(CANCELLATION='100')))
        with self.assertRaises(ValueError):
            validate_correction('REFUND','UNALLOCATED',Decimal('51'),
                                Decimal('100'),totals(REFUND='50'))

    def test_reject_invalid_or_negative(self):
        for kind,amount in [('UNKNOWN',Decimal('1')),
                            ('DISCOUNT',Decimal('-1')),('DISCOUNT',Decimal('0'))]:
            with self.subTest(kind=kind,amount=amount):
                with self.assertRaises(ValueError):
                    validate_correction(kind,'LODGING',amount,Decimal('500'),totals())


if __name__=='__main__':
    unittest.main()
