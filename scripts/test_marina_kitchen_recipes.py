"""Recipe validation and exact arithmetic regressions."""
import unittest
from datetime import date
from pydantic import ValidationError
from services.api.app.kitchen_recipes import RecipeWrite, ingredient_requirements


def row(recipe=None, planned=20, prepared=8, item="dish-1"):
    return {"recipe":recipe, "plannedQuantity":planned, "preparedQuantity":prepared,
            "menuItemId":item, "nameRu":"Учебный плов", "serviceDate":date(2026,11,11)}


def recipe(norm="0.1", unit="KG", status="APPROVED", sample=True):
    return {"version":1, "updated_at":"2026-11-11T00:00:00Z", "status":status,
            "is_sample":sample, "ingredients":[{"name":"Рис","unit":unit,"quantity_per_portion":norm}]}


class RecipeContracts(unittest.TestCase):
    def test_exact_plan_prepared_and_remaining(self):
        data=ingredient_requirements([row(recipe())])
        self.assertTrue(data["is_complete"])
        self.assertTrue(data["contains_sample_data"])
        self.assertFalse(data["inventory_deducted"])
        self.assertEqual(data["items"],[{"name":"Рис","unit":"KG","planned_quantity":"2",
            "prepared_quantity":"0.8","remaining_quantity":"1.2"}])

    def test_aggregates_shared_products_without_float_drift(self):
        data=ingredient_requirements([row(recipe("0.000001"),3,1),row(recipe("0.000001"),7,4,"dish-2")])
        self.assertEqual(data["items"][0]["planned_quantity"],"0.00001")
        self.assertEqual(data["items"][0]["remaining_quantity"],"0.000005")

    def test_scientific_input_is_serialized_as_plain_decimal(self):
        value = RecipeWrite(expected_version=0, ingredients=[
            {"name":"Рис","unit":"KG","quantity_per_portion":"1e-3"}])
        self.assertEqual(value.model_dump(mode="json")["ingredients"][0]["quantity_per_portion"],"0.001")

    def test_units_are_kept_separate(self):
        data=ingredient_requirements([row(recipe(unit="KG")),row(recipe(unit="PCS"))])
        self.assertEqual(len(data["items"]),2)

    def test_missing_and_draft_recipes_remain_incomplete(self):
        for value in (None,recipe(status="DRAFT")):
            data=ingredient_requirements([row(value)])
            self.assertFalse(data["is_complete"])
            self.assertFalse(data["items"])
            self.assertEqual(data["missing_recipes"][0]["menu_item_id"],"dish-1")

    def test_zero_plan_does_not_require_recipe(self):
        data=ingredient_requirements([row(None,0,0)])
        self.assertTrue(data["is_complete"])

    def test_partial_coverage_is_explicit(self):
        data=ingredient_requirements([row(recipe()),row(None,item="dish-2")])
        self.assertFalse(data["is_complete"])
        self.assertEqual(len(data["items"]),1)
        self.assertEqual(len(data["missing_recipes"]),1)

    def test_invalid_norms_and_units_rejected(self):
        for norm in ("0","-1","NaN","Infinity","0.0000001","1001"):
            with self.assertRaises(ValidationError):
                RecipeWrite(expected_version=0,**{k:v for k,v in recipe(norm).items()
                    if k not in ("version","updated_at")})
        with self.assertRaises(ValidationError):
            RecipeWrite(expected_version=0,status="APPROVED",ingredients=[
                {"name":"Рис","unit":"G","quantity_per_portion":"1"}])

    def test_blank_and_duplicate_names_rejected(self):
        for ingredients in (
            [{"name":"  ","unit":"KG","quantity_per_portion":"1"}],
            [{"name":name,"unit":"KG","quantity_per_portion":"1"} for name in ("Рис"," рис ")],
        ):
            with self.assertRaises(ValidationError):
                RecipeWrite(expected_version=0,ingredients=ingredients)


if __name__=="__main__":
    unittest.main()
