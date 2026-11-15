import {createLiveModules} from '../src/api/liveModules';

const record={
 scope:'OWNER_ONLY_PROPERTY_SCOPED',
 period:{from:'2026-11-15',to:'2026-11-15',currency:'KGS',timezone:'Asia/Bishkek'},
 customer_payments_received_kgs:3000,customer_payments_received_count:3,
 owner_expense_manual_settlements_kgs:300,owner_expense_manual_settlements_count:1,
 observed_recorded_difference_kgs:2700,
 owner_expenses_posted_for_period_kgs:1000,owner_expenses_posted_count:1,
 all_time_unsettled_expenses_kgs:700,
 truth:{report_type:'OBSERVED_CASH_RECORDS_NOT_RECOGNIZED_PROFIT',
  recognized_profit_kgs:null,verified_bank_balance_kgs:null,
  refunds_reconciled:false,completeness_verified:false,payment_created:false,
  reason:'Not a complete statement'},
};
const response=(value:unknown):Response=>({ok:true,status:200,json:async()=>value} as Response);

test('OWNER cash comparison is read-only and never produces profit or bank balance',async()=>{
 const transport=jest.fn(async(_url:RequestInfo|URL)=>response(record));
 const live=createLiveModules('https://test.example',transport as typeof fetch,'single_property');
 const data=await live.ownerRecordedCashMovements('2026-11-15','2026-11-15');
 expect(data.customer_payments_received_kgs).toBe(3000);
 expect(data.owner_expense_manual_settlements_kgs).toBe(300);
 expect(data.observed_recorded_difference_kgs).toBe(2700);
 expect(data.truth.recognized_profit_kgs).toBeNull();
 expect(data.truth.verified_bank_balance_kgs).toBeNull();
 expect(String(transport.mock.calls[0]?.[0])).toContain(
   '/api/v1/admin/finance/owner/recorded-cash-movements?from_date=2026-11-15&to_date=2026-11-15');
});

test('invalid cash arithmetic, fake profit or omitted cash flow limitations fail closed',async()=>{
 for(const invalid of [
  {...record,observed_recorded_difference_kgs:5000},
  {...record,truth:{...record.truth,recognized_profit_kgs:2700}},
  {...record,truth:{...record.truth,refunds_reconciled:true}},
  {...record,truth:{...record.truth,completeness_verified:true}},
  {...record,owner_expense_manual_settlements_kgs:-300},
 ]){
  const live=createLiveModules('https://test.example',
    jest.fn(async()=>response(invalid)) as typeof fetch,'single_property');
  await expect(live.ownerRecordedCashMovements('2026-11-15','2026-11-15'))
   .rejects.toMatchObject({code:'UNKNOWN'});
 }
});
