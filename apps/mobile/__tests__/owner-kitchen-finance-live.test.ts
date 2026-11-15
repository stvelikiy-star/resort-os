import {createLiveModules} from '../src/api/liveModules';

const row=(amount:string)=>({cost_kgs:amount,movement_count:1});
const movements={
 RECEIPT:row('600'),PRODUCTION:row('400'),WASTE:row('0'),SPOILAGE:row('75'),
};
const sample={
 RECEIPT:row('0'),PRODUCTION:row('0'),WASTE:row('0'),SPOILAGE:row('0'),
};
const report={
 scope:'OWNER_ONLY_PROPERTY_SCOPED',period:{from:'2026-11-15',to:'2026-11-15',timezone:'Asia/Bishkek'},
 real_inventory_movements:movements,sample_inventory_movements:sample,
 real_production_cost_kgs:'400',real_loss_cost_kgs:'75',
 real_total_consumption_and_loss_cost_kgs:'475',
 current_stock:{
  real_value_at_current_item_cost_kgs:'125',
  sample_value_at_current_item_cost_kgs:'0',
  negative_balance_items:0,item_count:1,valuation_as_of:'CURRENT_NOT_PERIOD_END',
 },
 procurement_exposure:{
  approved_unreceived_at_current_item_cost_kgs:'0',
  unapproved_requests_at_current_item_cost_kgs:'100',
  approved_open_request_count:0,pending_approval_count:1,
  settled_supplier_payables_kgs:null,
 },
 truth:{report_type:'MANAGEMENT_OPERATIONAL_COSTS_NOT_ACCOUNTING',payment_created:false,
   profit:'NOT_AVAILABLE_WITHOUT_RECOGNIZED_REVENUE_AND_EXPENSE_LEDGER',
   receipt:'Inventory only',consumption:'No Payment',procurement:'Estimate',inventory:'Current'},
};
const response=(value:unknown):Response=>({ok:true,status:200,json:async()=>value} as Response);

test('OWNER kitchen finance shows exact operational facts and does not synthesize profit or payments',async()=>{
 const transport=jest.fn(async(_url:RequestInfo|URL)=>response(report));
 const live=createLiveModules('https://test.example',transport as typeof fetch,'single_property');
 const data=await live.ownerKitchenManagement('2026-11-15','2026-11-15');
 expect(data.real_loss_cost_kgs).toBe('75');
 expect(data.real_inventory_movements.SPOILAGE.cost_kgs).toBe('75');
 expect(data.real_total_consumption_and_loss_cost_kgs).toBe('475');
 expect(data.procurement_exposure.settled_supplier_payables_kgs).toBeNull();
 expect(data.truth.payment_created).toBe(false);
 expect(String(transport.mock.calls[0]?.[0])).toContain(
  '/api/v1/admin/finance/owner/kitchen-operations?from_date=2026-11-15&to_date=2026-11-15');
});

test('OWNER finance fail-closed if backend returns fabricated profit or costs',async()=>{
 const bad=[{...report,truth:{...report.truth,profit:'100000'}},
  {...report,real_loss_cost_kgs:'-75'},
  {...report,procurement_exposure:{...report.procurement_exposure,settled_supplier_payables_kgs:'100'}},
  {...report,real_inventory_movements:{...movements,SPOILAGE:{cost_kgs:'garbage',movement_count:1}}}];
 for(const item of bad){
  const live=createLiveModules('https://test.example',
   jest.fn(async()=>response(item)) as typeof fetch,'single_property');
  await expect(live.ownerKitchenManagement('2026-11-15','2026-11-15'))
   .rejects.toMatchObject({code:'UNKNOWN'});
 }
});
