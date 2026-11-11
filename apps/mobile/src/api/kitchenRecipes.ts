import { ApiError } from './types';
import { safeRouteId } from './routeId';

export type RecipeUnit = 'KG' | 'L' | 'PCS';
export interface RecipeIngredient { name: string; unit: RecipeUnit; quantity_per_portion: string }
export interface KitchenRecipe {
  version: number; status: 'DRAFT' | 'APPROVED'; is_sample: boolean;
  updated_at: string; ingredients: RecipeIngredient[];
}
export interface IngredientRequirements {
  basis: 'PRODUCTION_PORTIONS'; is_complete: boolean; contains_sample_data: boolean;
  inventory_deducted: false;
  items: { name: string; unit: RecipeUnit; planned_quantity: string; prepared_quantity: string; remaining_quantity: string }[];
  missing_recipes: { menu_item_id: string; name_ru: string; service_date: string }[];
}
export type RecipeInput = Omit<KitchenRecipe, 'version' | 'updated_at'> & { expected_version: number };

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new ApiError('UNKNOWN', 'Invalid recipe contract');
  return value as Record<string, unknown>;
}
function text(value: unknown): string {
  if (typeof value !== 'string' || !value.trim()) throw new ApiError('UNKNOWN', 'Invalid recipe text');
  return value;
}
function decimal(value: unknown): string {
  if (typeof value !== 'string' || !/^\d{1,20}(?:\.\d{1,6})?$/.test(value)) {
    throw new ApiError('UNKNOWN', 'Invalid ingredient quantity');
  }
  return value;
}
function unit(value: unknown): RecipeUnit {
  if (value !== 'KG' && value !== 'L' && value !== 'PCS') throw new ApiError('UNKNOWN', 'Invalid ingredient unit');
  return value;
}
export function kitchenRecipe(value: unknown): KitchenRecipe | null {
  if (value === null || value === undefined) return null;
  const row = object(value);
  if (!Number.isSafeInteger(row.version) || Number(row.version) < 1 ||
      (row.status !== 'DRAFT' && row.status !== 'APPROVED') ||
      typeof row.is_sample !== 'boolean' || !Array.isArray(row.ingredients) || !row.ingredients.length) {
    throw new ApiError('UNKNOWN', 'Invalid recipe contract');
  }
  return { version: Number(row.version), status: row.status, is_sample: row.is_sample,
    updated_at: text(row.updated_at), ingredients: row.ingredients.map(value => {
      const item = object(value);
      const quantity = decimal(item.quantity_per_portion);
      if (Number(quantity) <= 0 || Number(quantity) > 1000) throw new ApiError('UNKNOWN', 'Invalid per-portion norm');
      return { name: text(item.name), unit: unit(item.unit), quantity_per_portion: quantity };
    }) };
}
export function ingredientRequirements(value: unknown): IngredientRequirements | undefined {
  if (value === undefined) return undefined;
  const row = object(value);
  if (row.basis !== 'PRODUCTION_PORTIONS' || typeof row.is_complete !== 'boolean' ||
      typeof row.contains_sample_data !== 'boolean' || row.inventory_deducted !== false ||
      !Array.isArray(row.items) || !Array.isArray(row.missing_recipes)) {
    throw new ApiError('UNKNOWN', 'Invalid ingredient requirements');
  }
  if (row.is_complete && row.missing_recipes.length) throw new ApiError('UNKNOWN', 'Incomplete recipe coverage');
  return {
    basis: 'PRODUCTION_PORTIONS', is_complete: row.is_complete,
    contains_sample_data: row.contains_sample_data, inventory_deducted: false,
    items: row.items.map(value => {
      const item = object(value);
      return { name: text(item.name), unit: unit(item.unit), planned_quantity: decimal(item.planned_quantity),
        prepared_quantity: decimal(item.prepared_quantity), remaining_quantity: decimal(item.remaining_quantity) };
    }),
    missing_recipes: row.missing_recipes.map(value => {
      const item = object(value);
      return { menu_item_id: safeRouteId(text(item.menu_item_id)), name_ru: text(item.name_ru), service_date: text(item.service_date) };
    }),
  };
}
