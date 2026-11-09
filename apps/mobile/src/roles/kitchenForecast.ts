import type { DiningProductionSnapshots } from '../api/liveModules';

export type MealName = 'BREAKFAST' | 'LUNCH' | 'DINNER';
export interface KitchenForecast {
  days: number;
  portions: number;
  adultPortions: number;
  childPortions: number;
  byMeal: Record<MealName, number>;
  changesAfterFreeze: number;
  netPortionDelta: number;
  unconfiguredMeals: number;
  frozenMeals: number;
}

/** Sum service portions, not unique people or kg of food.
 * Forecast comes ONLY from server-verified active stay meal entitlements.
 * Extra restaurant orders and pantry purchases require separate sources. */
export function kitchenForecast(data: DiningProductionSnapshots | null): KitchenForecast | null {
  if (!data) return null;
  const forecast: KitchenForecast = {
    days: data.days.length, portions: 0, adultPortions: 0, childPortions: 0,
    byMeal: { BREAKFAST: 0, LUNCH: 0, DINNER: 0 },
    changesAfterFreeze: 0, netPortionDelta: 0, unconfiguredMeals: 0, frozenMeals: 0,
  };
  for (const day of data.days) for (const meal of day.meals) {
    forecast.portions += meal.current_total_portions;
    forecast.adultPortions += meal.current_adult_portions;
    forecast.childPortions += meal.current_child_portions;
    forecast.byMeal[meal.meal_type] += meal.current_total_portions;
    if (meal.state === 'FROZEN') {
      forecast.frozenMeals++;
      if (meal.changed_since_snapshot) {
        forecast.changesAfterFreeze++;
        forecast.netPortionDelta += meal.delta_total_portions ?? 0;
      }
    }
    if (meal.cutoff_status === 'UNCONFIGURED') forecast.unconfiguredMeals++;
  }
  return forecast;
}