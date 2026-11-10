import {
  diningMealPlanAck, diningStaysResponse, diningStayEntitlementsResponse,
} from '../src/api/contractValidation';
import type { MealPlanDraft } from '../src/api/liveModules';

const STAY='be3d4a10-8d4e-4fbc-9fe3-a95e1f3165e6';
const OTHER='6f75d49b-a70e-4527-9414-1282ce957d72';
const draft:MealPlanDraft={
  from_date:'2026-11-07',through_date:'2026-11-07',meals:['BREAKFAST'],
  adult_portions:2,child_portions:1,notes:null,replace_range:false,
};
describe('real Dining Entitlement contract',()=>{
  it('admits a real stay list, not fabricated reservations',()=>{
    const x=diningStaysResponse({local_date:'2026-11-06',items:[{
      stay_id:STAY,stay_status:'PENDING',reservation_id:OTHER,reservation_status:'GUARANTEED',
      booking_number:'BOOK-1',check_in:'2026-11-07',check_out:'2026-11-09',
      adults:2,children:1,guest_name:'Synthetic Test',room_code:'M-101',entitlement_count:0,
    }]});
    expect(x.items[0].entitlement_count).toBe(0);
    expect(x.items[0].guest_name).toBe('Synthetic Test');
  });
  it('accepts only the exact stay in readback',()=>{
    const raw={stay:{id:STAY,booking_number:'BOOK-1',check_in:'2026-11-07',
      check_out:'2026-11-09',guest_name:'Synthetic Test',room_code:'M-101'},
      items:[{id:OTHER,stay_id:STAY,service_date:'2026-11-07',meal_type:'BREAKFAST',
        adult_portions:2,child_portions:1,status:'ACTIVE',notes:null}]};
    expect(diningStayEntitlementsResponse(raw,STAY).items).toHaveLength(1);
    expect(()=>diningStayEntitlementsResponse(raw,OTHER)).toThrow('contract mismatch');
  });
  it('verifies server echo of stay and exact meal count',()=>{
    const ack={stay_id:STAY,updated_items:1,from_date:draft.from_date,
      through_date:draft.through_date,meals:['BREAKFAST'],adult_portions:2,child_portions:1};
    expect(diningMealPlanAck(ack,STAY,draft).updated_items).toBe(1);
    expect(()=>diningMealPlanAck({...ack,stay_id:OTHER},STAY,draft)).toThrow('contract mismatch');
    expect(()=>diningMealPlanAck({...ack,adult_portions:3},STAY,draft)).toThrow('contract mismatch');
    expect(()=>diningMealPlanAck({...ack,meals:['DINNER']},STAY,draft)).toThrow('contract mismatch');
  });
});
