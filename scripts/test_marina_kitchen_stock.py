"""Stock contract regression checks. Live PostgreSQL/RBAC E2E is tracked separately."""
import unittest
import uuid
from decimal import Decimal
from pydantic import ValidationError
from fastapi import HTTPException
from services.api.app.kitchen_inventory_valuation import weighted_unit_cost,debit_cost
from services.api.app.kitchen_stock import ItemWrite, ReceiptWrite, ConsumeWrite, LossWrite

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
                ReceiptWrite(movement_id=uuid.uuid4(),stock_item_id=uuid.uuid4(),quantity=val)
    def test_fractional_quantity_is_exact(self):
        x=ReceiptWrite(movement_id=uuid.uuid4(),stock_item_id=uuid.uuid4(),quantity='0.125')
        self.assertEqual(x.quantity,Decimal('0.125'))
    def test_exact_recipe_cost_math(self):
        eggs=Decimal(2)*Decimal(2)*Decimal(12)
        bread=Decimal('0.1')*Decimal(2)*Decimal(100)
        self.assertEqual(eggs+bread,Decimal(68))
    def test_stock_losses_require_reason_and_positive_quantity(self):
        x=LossWrite(movement_id=uuid.uuid4(),stock_item_id=uuid.uuid4(),
                    kind="SPOILAGE",quantity="0.250000",reason="  Expired   stock  ")
        self.assertEqual(x.reason,"Expired stock")
        self.assertEqual(x.quantity,Decimal("0.250000"))
        for kind in ("RECEIPT","PRODUCTION","OTHER"):
            with self.assertRaises(ValidationError):
                LossWrite(movement_id=uuid.uuid4(),stock_item_id=uuid.uuid4(),
                          kind=kind,quantity="1",reason="Expired stock")
        for quantity in ("0","-0.1"):
            with self.assertRaises(ValidationError):
                LossWrite(movement_id=uuid.uuid4(),stock_item_id=uuid.uuid4(),
                          kind="WASTE",quantity=quantity,reason="Unusable stock")
        for reason in ("", "x", "   "):
            with self.assertRaises(ValidationError):
                LossWrite(movement_id=uuid.uuid4(),stock_item_id=uuid.uuid4(),
                          kind="WASTE",quantity="1",reason=reason)

    def test_weighted_average_uses_stock_receipt_cost_not_catalog(self):
        # 5 units at invoice 123.4567 and 5 at a historic receipt price 100:
        # 1117.2835 / 10 = 111.72835 => 111.7284 per unit (4dp).
        inventory_value=Decimal("5")*Decimal("123.4567")+Decimal("5")*Decimal("100")
        cost=debit_cost(Decimal("10"),inventory_value,Decimal("2"))
        self.assertEqual(cost,Decimal("111.7284"))
        self.assertEqual(cost*Decimal("2"),Decimal("223.4568"))
        remainder=inventory_value-cost*Decimal("2")
        self.assertEqual(weighted_unit_cost(Decimal("8"),remainder),Decimal("111.7283"))

    def test_valuation_fails_closed_on_inconsistent_historical_opening(self):
        for qty,value in (("0","0"),("2","-1"),("-1","100")):
            with self.subTest(qty=qty,value=value),self.assertRaises(HTTPException) as exc:
                weighted_unit_cost(Decimal(qty),Decimal(value))
            self.assertEqual(exc.exception.status_code,409)
        with self.assertRaises(HTTPException):
            debit_cost(Decimal("2"),Decimal("100"),Decimal("3"))

    def test_bad_target_id(self):
        with self.assertRaises(ValidationError):ConsumeWrite(production_target_id='not-a-uuid')
if __name__=='__main__':unittest.main()
