import { diningProductionSnapshotsResponse } from '../src/api/contractValidation';

const basic = {
  from_date:'2026-11-09',through_date:'2026-11-09',
  days:[{service_date:'2026-11-09',meals:(['BREAKFAST','LUNCH','DINNER'] as const).map(meal_type=>({
    service_date:'2026-11-09',meal_type,
    current_adult_portions:4,current_child_portions:1,current_total_portions:5,current_entitlement_count:2,
    state:'OPEN',cutoff_status:'BEFORE_CUTOFF',changed_since_snapshot:false,
  }))}],
};
const withStages=()=>{
  const raw=JSON.parse(JSON.stringify(basic));
  raw.days[0].checked_in_stays_with_meals=1;
  raw.days[0].expected_arrival_stays_with_meals=1;
  for(const meal of raw.days[0].meals){
    meal.current_checked_in_adult_portions=2;
    meal.current_checked_in_child_portions=1;
    meal.current_checked_in_total_portions=3;
    meal.current_checked_in_stay_count=1;
    meal.current_expected_arrival_adult_portions=2;
    meal.current_expected_arrival_child_portions=0;
    meal.current_expected_arrival_total_portions=2;
    meal.current_expected_arrival_stay_count=1;
  }
  return raw;
};
describe('Chef hotel stay-stage totals truth and privacy',()=>{
  it('accepts exact verified Core meal-stage breakdown',()=>{
    const data=diningProductionSnapshotsResponse(withStages());
    expect(data.days[0].checked_in_stays_with_meals).toBe(1);
    expect(data.days[0].meals[0].current_checked_in_total_portions).toBe(3);
  });
  it('allows older RC409 to omit newer data without fabricating checked-in guests',()=>{
    expect(diningProductionSnapshotsResponse(basic).days[0].checked_in_stays_with_meals).toBeUndefined();
  });
  it('rejects incomplete or inconsistent server stage totals',()=>{
    const bad=withStages();bad.days[0].meals[0].current_checked_in_total_portions=99;
    expect(()=>diningProductionSnapshotsResponse(bad)).toThrow();
    const missing=withStages();delete missing.days[0].meals[0].current_expected_arrival_stay_count;
    expect(()=>diningProductionSnapshotsResponse(missing)).toThrow();
  });
  it('never treats distinct stay counts as unique individual people',()=>{
    const data=diningProductionSnapshotsResponse(withStages());
    expect(data.days[0].checked_in_stays_with_meals).toBe(1);
    expect(data.days[0].meals[0].current_checked_in_total_portions).toBe(3);
  });
});