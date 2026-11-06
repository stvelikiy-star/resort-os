import type { KitchenOrder } from '../api/liveModules';

/** Derived solely from the currently returned kitchen orders.
 * No inferred meal service (breakfast/lunch/dinner), delivery ETA or menu choices.
 * If a meal-plan API exists later, it must be admitted with a separate contract. */
export interface DishDemand { name: string; quantity: number; destinations: string[] }
export interface KitchenWorkload {
  totalActive: number; newOrders: number; preparing: number; ready: number;
  unknownDishOrders: number; dishesToPrepare: DishDemand[];
}
export function kitchenWorkload(orders: readonly KitchenOrder[]): KitchenWorkload {
  const active = orders.filter(o => o.status !== 'SERVED' && o.status !== 'CANCELLED');
  const toPrepare = active.filter(o => ['NEW', 'ACCEPTED', 'COOKING'].includes(o.status));
  const dishes = new Map<string, {name:string;quantity:number;destinations:Set<string>}>();
  let unknownDishOrders = 0;
  for(const order of toPrepare) {
    if (!Array.isArray(order.items) || order.items.length === 0) unknownDishOrders++;
    const location = order.table_code ? order.table_code : order.room_code ? order.room_code : '—';
    for (const item of order.items ?? []) {
      const name = typeof item.name === 'string' ? item.name.trim() : '';
      const qty = typeof item.quantity === 'number' && Number.isSafeInteger(item.quantity) && item.quantity > 0
        ? item.quantity : 0;
      if (!name || !qty) continue;
      const key = name.toLocaleLowerCase();
      const entry = dishes.get(key) ?? { name, quantity: 0, destinations: new Set<string>() };
      entry.quantity += qty;
      entry.destinations.add(location);
      dishes.set(key, entry);
    }
  }
  return {
    totalActive: active.length, newOrders: active.filter(o=>o.status==='NEW').length,
    preparing: active.filter(o=>o.status==='ACCEPTED'||o.status==='COOKING').length,
    ready: active.filter(o=>o.status==='READY').length,
    unknownDishOrders,
    dishesToPrepare: [...dishes.values()].map(d => ({
      name: d.name, quantity: d.quantity, destinations: [...d.destinations].sort(),
    })).sort((a,b)=>b.quantity-a.quantity || a.name.localeCompare(b.name)),
  };
}
