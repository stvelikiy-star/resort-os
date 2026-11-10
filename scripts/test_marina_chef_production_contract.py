"""MARINA SMART: Chef production input and COOK draft RBAC fail-closed tests."""
import unittest
import uuid
from datetime import date
from fastapi import HTTPException
from pydantic import ValidationError

from services.api.app.kitchen_menu_management import (
    MenuCreate, ProductionTargetWrite, validate_menu_create_permissions,
    _production_item,
)


def draft(**changes):
    data = {
        "code": "TEST_PL0V", "category": "MAIN",
        "name_ru": "Плов", "name_kg": "Палоо", "name_kz": "Палау",
        "name_en": "Pilaf", "price_kgs": 0,
        "is_active": False, "is_draft": True,
    }
    return MenuCreate(**(data | changes))


class ChefProductionContracts(unittest.TestCase):
    def test_cook_may_create_unpriced_inactive_draft(self):
        self.assertIsNone(validate_menu_create_permissions(draft(), {"role": "COOK"}))

    def test_cook_may_not_publish(self):
        with self.assertRaises(HTTPException) as ctx:
            validate_menu_create_permissions(draft(is_draft=False), {"role": "COOK"})
        self.assertEqual(ctx.exception.status_code, 403)

    def test_cook_may_not_activate(self):
        with self.assertRaises(HTTPException) as ctx:
            validate_menu_create_permissions(draft(is_active=True), {"role": "COOK"})
        self.assertEqual(ctx.exception.status_code, 403)

    def test_cook_may_not_set_selling_price(self):
        with self.assertRaises(HTTPException) as ctx:
            validate_menu_create_permissions(draft(price_kgs=500), {"role": "COOK"})
        self.assertEqual(ctx.exception.status_code, 403)

    def test_manager_may_create_price_draft(self):
        self.assertIsNone(validate_menu_create_permissions(draft(price_kgs=500), {"role": "MANAGER"}))

    def test_owner_may_create_price_draft(self):
        self.assertIsNone(validate_menu_create_permissions(draft(price_kgs=500), {"role": "OWNER"}))

    def test_invalid_meal_rejected(self):
        with self.assertRaises(ValidationError):
            ProductionTargetWrite(service_date=date.today(), meal_type="WRONG",
                                  menu_item_id=uuid.uuid4(), planned_quantity=1)

    def test_negative_planned_rejected(self):
        with self.assertRaises(ValidationError):
            ProductionTargetWrite(service_date=date.today(), meal_type="LUNCH",
                                  menu_item_id=uuid.uuid4(), planned_quantity=-1)

    def test_excess_planned_rejected(self):
        with self.assertRaises(ValidationError):
            ProductionTargetWrite(service_date=date.today(), meal_type="LUNCH",
                                  menu_item_id=uuid.uuid4(), planned_quantity=10001)

    def test_excess_prepared_rejected(self):
        with self.assertRaises(ValidationError):
            ProductionTargetWrite(service_date=date.today(), meal_type="LUNCH",
                                  menu_item_id=uuid.uuid4(), planned_quantity=1,
                                  prepared_quantity=10001)

    def test_valid_portion_count(self):
        x = ProductionTargetWrite(service_date=date.today(), meal_type="BREAKFAST",
                                 menu_item_id=uuid.uuid4(), planned_quantity=20,
                                 prepared_quantity=8)
        self.assertEqual(x.planned_quantity-x.prepared_quantity, 12)

    def test_note_length_rejected(self):
        with self.assertRaises(ValidationError):
            ProductionTargetWrite(service_date=date.today(), meal_type="DINNER",
                                  menu_item_id=uuid.uuid4(), planned_quantity=5,
                                  notes="x"*501)


if __name__ == "__main__":
    unittest.main()
