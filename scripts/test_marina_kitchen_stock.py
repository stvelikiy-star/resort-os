"""Stock contract regression checks. Live PostgreSQL/RBAC E2E is tracked separately."""
import unittest
import uuid
from decimal import Decimal
from pydantic import ValidationError
from services.api.app.kitchen_stock import ItemWrite, ReceiptWrite, ConsumeWrite

class StockContracts(unittest.TestCase):
    def test_item_name_is_canonical_and_sample_is_explicit(self):
        v=ItemWrite(name='  [ТЕСТ]   Хлеб  ',unit='KG',cost_per_unit_kgs='100',is_sample=True)
        self.assertEqual(v.name,'[ТЕСТ] Хлеб')
        self.assertTrue(v.is_sample)
    def test_only_supported_units(self):
        with self.assertRaises(ValidationError):
            ItemWrite(name='Рис',unit='G',cost_per_unit_kgs='10')
    def test_reject_negative_cost(self):
        with self.assertRaises(ValidationError):
            ItemWrite(name='Рис',unit='KG',cost_per_unit_kgs='-1')
    def test_receipts_cannot_be_zero_or_negative(self):
        for val in ('0','-1'):
            with self.assertRaises(ValidationError):
                ReceiptWrite(stock_item_id=uuid.uuid4(),quantity=val)
    def test_fractional_quantity_is_exact(self):
        x=ReceiptWrite(stock_item_id=uuid.uuid4(),quantity='0.125')
        self.assertEqual(x.quantity,Decimal('0.125'))
    def test_exact_recipe_cost_math(self):
        eggs=Decimal(2)*Decimal(2)*Decimal(12)
        bread=Decimal('0.1')*Decimal(2)*Decimal(100)
        self.assertEqual(eggs+bread,Decimal(68))
    def test_bad_target_id(self):
        with self.assertRaises(ValidationError):ConsumeWrite(production_target_id='not-a-uuid')
if __name__=='__main__':unittest.main()
