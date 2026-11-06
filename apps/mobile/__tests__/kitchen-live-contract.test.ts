import { kitchenItemName } from '../src/i18n/kitchenLabels';
import { kitchenWorkload } from '../src/roles/kitchenSummary';
import { diningProductionSnapshotsResponse } from '../src/api/contractValidation';
import type { KitchenOrder } from '../src/api/liveModules';

const realOrder: KitchenOrder = {
  id:'order-1',order_number:'K-01',status:'NEW',source:'GUEST_OS',meal_type:'DINNER',guest_count:2,
  table_code:null,room_code:'M-101',total_kgs:750,notes:null,
  items:[
    {id:'item-1',name_ru:'Плов',name_kg:'Палоо',name_en:'Plov',name_kz:'Палау',quantity:2},
    {id:'item-2',name_ru:'Чай',name_kg:'Чай',name_en:'Tea',name_kz:'Шай',quantity:1},
  ],
};
function snapshot() {
  const meals=(['BREAKFAST','LUNCH','DINNER'] as const).map((meal_type,i)=>({
    service_date:'2026-11-06',meal_type,current_adult_portions:i+1,current_child_portions:i,
    current_total_portions:2*i+1,current_entitlement_count:1,state:'OPEN',
    cutoff_status:'BEFORE_CUTOFF',frozen_total_portions:null,delta_total_portions:null,
    changed_since_snapshot:false,meal_start:null,cutoff_at:null,
  }));
  return {from_date:'2026-11-06',through_date:'2026-11-06',days:[{service_date:'2026-11-06',meals}]};
}
describe('real Kitchen API contract',()=>{
  it('uses name_ru/kg/en/kz correctly (server has no name field)',()=>{
    expect(kitchenItemName(realOrder.items[0],'ru')).toBe('Плов');
    expect(kitchenItemName(realOrder.items[0],'kg')).toBe('Палоо');
    expect(kitchenItemName(realOrder.items[0],'en')).toBe('Plov');
    expect(kitchenItemName(realOrder.items[0],'kz')).toBe('Палау');
    expect(kitchenItemName({name_ru:'Суп'},'en')).toBe('Суп');
  });
  it('shows actual guest extras by dish and room without assuming included entitlement',()=>{
    expect(kitchenWorkload([realOrder],'kg')).toMatchObject({
      totalActive:1,newOrders:1,unknownDishOrders:0,
      dishesToPrepare:[
        {name:'Палоо',quantity:2,destinations:['M-101']},
        {name:'Чай',quantity:1,destinations:['M-101']},
      ],
    });
  });
  it('allows zero included portions without claiming that all hotel guests have none',()=>{
    const raw=snapshot();
    raw.days[0].meals[0].current_adult_portions=0;
    raw.days[0].meals[0].current_total_portions=0;
    const parsed=diningProductionSnapshotsResponse(raw);
    expect(parsed.days[0].meals[0].current_total_portions).toBe(0);
  });
  it('accepts correctly frozen counts and delta and rejects a mismatched delta',()=>{
    const raw=snapshot();
    const meal=raw.days[0].meals[0];
    meal.state='FROZEN';
    meal.frozen_total_portions=2; meal.delta_total_portions=-1; meal.changed_since_snapshot=true;
    expect(diningProductionSnapshotsResponse(raw).days[0].meals[0].delta_total_portions).toBe(-1);
    meal.delta_total_portions=0;
    expect(()=>diningProductionSnapshotsResponse(raw)).toThrow('contract mismatch');
  });
  it('rejects missing meal types and invalid totals without fallback data',()=>{
    const raw=snapshot();
    raw.days[0].meals.pop();
    expect(()=>diningProductionSnapshotsResponse(raw)).toThrow('contract mismatch');
    raw.days[0].meals=snapshot().days[0].meals;
    raw.days[0].meals[0].current_total_portions=999;
    expect(()=>diningProductionSnapshotsResponse(raw)).toThrow('contract mismatch');
  });
});
