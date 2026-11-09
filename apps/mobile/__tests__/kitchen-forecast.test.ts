import { kitchenForecast } from '../src/roles/kitchenForecast';
import type { DiningProductionSnapshots, DiningProductionSnapshotMeal } from '../src/api/liveModules';

const meal = (name: DiningProductionSnapshotMeal['meal_type'], adult: number, child: number,
  extra: Partial<DiningProductionSnapshotMeal> = {}): DiningProductionSnapshotMeal => ({
  service_date: '2026-11-12', meal_type: name,
  current_adult_portions: adult, current_child_portions: child,
  current_total_portions: adult + child, current_entitlement_count: 1,
  state: 'OPEN', cutoff_status: 'BEFORE_CUTOFF',
  frozen_total_portions: null, delta_total_portions: null,
  changed_since_snapshot: false, meal_start: null, cutoff_at: null, ...extra,
});
describe('chef forecast: verified included-meal demand only', () => {
  it('does not invent anything without server snapshots', () => {
    expect(kitchenForecast(null)).toBeNull();
  });
  it('counts adult/child portions per service without treating them as unique guests or stock', () => {
    const source: DiningProductionSnapshots = {from_date:'2026-11-12',through_date:'2026-11-13',days:[
      {service_date:'2026-11-12',meals:[meal('BREAKFAST',3,2),meal('LUNCH',1,1),meal('DINNER',0,0)]},
      {service_date:'2026-11-13',meals:[meal('BREAKFAST',4,2),meal('LUNCH',0,0),meal('DINNER',2,0)]},
    ]};
    expect(kitchenForecast(source)).toMatchObject({
      days:2, portions:15, adultPortions:10, childPortions:5,
      byMeal:{BREAKFAST:11,LUNCH:2,DINNER:2},
      changesAfterFreeze:0,unconfiguredMeals:0,
    });
  });
  it('reports frozen-plan deltas, including decreases, separately', () => {
    const frozen=meal('BREAKFAST',2,0,{
      state:'FROZEN', frozen_total_portions:5, delta_total_portions:-3, changed_since_snapshot:true,
      cutoff_status:'UNCONFIGURED',
    });
    const v: DiningProductionSnapshots={from_date:'2026-11-12',through_date:'2026-11-12',days:[
      {service_date:'2026-11-12',meals:[frozen,meal('LUNCH',0,0),meal('DINNER',0,0)]},
    ]};
    expect(kitchenForecast(v)).toMatchObject({portions:2,netPortionDelta:-3,changesAfterFreeze:1,frozenMeals:1,unconfiguredMeals:1});
  });
});