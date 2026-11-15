import type { IngredientRequirements } from '../api/kitchenRecipes';
import type { KitchenStockSnapshot } from '../api/liveModules';

export interface ProcurementGap {
  name: string;
  unit: string;
  required: string;
  available: string;
  shortage: string;
  is_sample: boolean;
}

function units(value: string): number {
  if (!/^(?:0|[1-9]\d*)(?:\.\d{1,6})?$/.test(value)) throw new Error('Invalid inventory decimal');
  const amount = Math.round(Number(value) * 1_000_000);
  if (!Number.isSafeInteger(amount) || amount < 0) throw new Error('Unsafe inventory decimal');
  return amount;
}
function display(value: number): string {
  const str = (value / 1_000_000).toFixed(6);
  return str.replace(/\.?0+$/, '');
}
function key(name: string, unit: string): string {
  return name.trim().toLocaleLowerCase().replace(/\s+/g, ' ') + '\u0000' + unit;
}

/** Read-only planning aid. No stock movement, reservation, or financial posting. */
export function procurementGaps(
  requirements: IngredientRequirements,
  stock: KitchenStockSnapshot,
): ProcurementGap[] {
  const inventory = new Map<string, number>();
  for (const item of stock.items) {
    // Never offset real demand with synthetic stock, or sample demand with real stock.
    if (item.is_sample !== requirements.contains_sample_data) continue;
    const id = key(item.name, item.unit);
    inventory.set(id, (inventory.get(id) ?? 0) + units(item.balance));
  }
  return requirements.items.map(item => {
    const required = units(item.remaining_quantity);
    const available = inventory.get(key(item.name, item.unit)) ?? 0;
    return {
      name: item.name, unit: item.unit, required: display(required),
      available: display(available), shortage: display(Math.max(0, required - available)),
      is_sample: requirements.contains_sample_data,
    };
  }).filter(row => Number(row.shortage) > 0);
}
