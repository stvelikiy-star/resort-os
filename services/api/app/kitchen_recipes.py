"""Versioned per-portion recipes and exact production ingredient requirements."""
from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, Literal, Mapping

from pydantic import BaseModel, Field, field_serializer, field_validator, model_validator


class RecipeIngredient(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    unit: Literal["KG", "L", "PCS"]
    quantity_per_portion: Decimal = Field(
        gt=0, le=1000, max_digits=10, decimal_places=6, allow_inf_nan=False,
    )

    @field_serializer("quantity_per_portion")
    def serialize_quantity(self, value: Decimal) -> str:
        return format(value.normalize(), "f")

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("Ingredient name is required")
        return value


class RecipeDefinition(BaseModel):
    status: Literal["DRAFT", "APPROVED"] = "DRAFT"
    is_sample: bool = False
    ingredients: list[RecipeIngredient] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def unique_ingredients(self):
        keys = [(item.name.casefold(), item.unit) for item in self.ingredients]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate ingredient and unit")
        return self


class RecipeWrite(RecipeDefinition):
    expected_version: int = Field(ge=0)


class SavedRecipe(RecipeDefinition):
    version: int = Field(ge=1)
    updated_at: str


def read_recipe(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = json.loads(value)
    return SavedRecipe.model_validate(value).model_dump(mode="json")


def ingredient_requirements(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    totals: dict[tuple[str, str], dict[str, Any]] = {}
    missing = []
    sample = False
    for row in rows:
        if row["plannedQuantity"] == 0:
            continue
        recipe = read_recipe(row["recipe"])
        if recipe is None or recipe["status"] != "APPROVED":
            missing.append({
                "menu_item_id": str(row["menuItemId"]), "name_ru": row["nameRu"],
                "service_date": row["serviceDate"].isoformat(),
            })
            continue
        sample = sample or recipe["is_sample"]
        for ingredient in recipe["ingredients"]:
            key = (ingredient["name"].casefold(), ingredient["unit"])
            total = totals.setdefault(key, {
                "name": ingredient["name"], "unit": ingredient["unit"],
                "planned_quantity": Decimal(0), "prepared_quantity": Decimal(0),
                "remaining_quantity": Decimal(0),
            })
            norm = Decimal(ingredient["quantity_per_portion"])
            total["planned_quantity"] += norm * row["plannedQuantity"]
            total["prepared_quantity"] += norm * row["preparedQuantity"]
            total["remaining_quantity"] += norm * (row["plannedQuantity"] - row["preparedQuantity"])
    items = []
    for _, total in sorted(totals.items()):
        items.append({
            **total,
            **{key: format(total[key].normalize(), "f") for key in
               ("planned_quantity", "prepared_quantity", "remaining_quantity")},
        })
    return {
        "basis": "PRODUCTION_PORTIONS", "is_complete": not missing,
        "contains_sample_data": sample, "inventory_deducted": False,
        "items": items, "missing_recipes": missing,
    }
