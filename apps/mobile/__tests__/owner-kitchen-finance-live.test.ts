import {createLiveModules} from '../src/api/liveModules';

const row=(amount:string)=>({cost_kgs:amount,movement_count:1});
const movements={
 RECEIPT:row('600'),PRODUCTION:row('400'),WASTE:row('0'),SPOILAGE:row('75'),
 SUPPLIER_RETURN:row('75'),
};
const sample={
 RECEIPT:row('0'),PRODUCTION:row('0'),WASTE:row('0'),SPOILAGE:row('0'),
 SUPPLIER_RETURN:row('0'),
};
const sourceReconciliation={
 inventory:{
  real_book_inventory_value_kgs:'125.0000',sample_book_inventory_value_kgs:'0.0000',
  real_catalog_estimate_kgs:'125.0000',sample_catalog_estimate_kgs:'0.0000',
  valuation_status:'MOVEMENT_BASED',invalid_item_count:0,item_count:1,
  as_of:'CURRENT_SNAPSHOT_NOT_PERIOD_END',
  linked_source:{receipt_count:1,original_stock_cost_kgs:'500.0000',
   invoice_source_cost_kgs:'600.0000',legacy_invoice_vs_stock_cost_delta_kgs:'100.0000',
   source_mismatch_count:1,source_status:'REVIEW_LEGACY_LINKED_RECEIPT_COST'},
 },
 supplier_documents:{
  document_count:1,gross_obligations_kgs:'600.0000',manual_settlements_kgs:'200.0000',
  credit_notes_kgs:'100.0000',outstanding_payables_kgs:'300.0000',
  return_count:1,return_stock_carrying_cost_kgs:'75.0000',
  return_credit_minus_stock_cost_kgs:'25.0000',payables_status:'RECORDED_OBLIGATIONS_BALANCED',
 },
 financial_truth:{
  recognized_revenue_kgs:null,recognized_profit_kgs:null,
  is_recognized_profit_complete:false,supplier_settlements_are_customer_payments:false,
  stock_receipts_are_expenses:false,stock_return_credit_difference_recognized:false,
  scope:'CURRENT_PROPERTY_POSTED_FACTS_NOT_PERIOD_END',
 },
};
const report={
 scope:'OWNER_ONLY_PROPERTY_SCOPED',period:{from:'2026-11-15',to:'2026-11-15',timezone:'Asia/Bishkek'},
 real_inventory_movements:movements,sample_inventory_movements:sample,
 real_production_cost_kgs:'400',real_loss_cost_kgs:'75',
 real_total_consumption_and_loss_cost_kgs:'475',
 real_supplier_return_stock_debit_kgs:'75',
 source_reconciliation:sourceReconciliation,
 current_stock:{
  real_value_at_current_item_cost_kgs:'125',
  sample_value_at_current_item_cost_kgs:'0',
  real_book_inventory_value_kgs:'125.0000',
  sample_book_inventory_value_kgs:'0.0000',
  valuation_status:'MOVEMENT_BASED',invalid_item_count:0,
  negative_balance_items:0,item_count:1,valuation_as_of:'CURRENT_NOT_PERIOD_END',
 },
 procurement_exposure:{
  approved_unreceived_at_current_item_cost_kgs:'0',
  unapproved_requests_at_current_item_cost_kgs:'100',
  approved_open_request_count:0,pending_approval_count:1,
  settled_supplier_payables_kgs:'200.0000',
  gross_supplier_obligations_kgs:'600.0000',
  credited_supplier_payables_kgs:'100.0000',
  outstanding_supplier_payables_kgs:'300.0000',
 },
 truth:{report_type:'MANAGEMENT_OPERATIONAL_COSTS_NOT_ACCOUNTING',payment_created:false,
   profit:'NOT_AVAILABLE_WITHOUT_RECOGNIZED_REVENUE_AND_EXPENSE_LEDGER',
   receipt:'Inventory only',consumption:'No Payment',procurement:'Estimate',
   inventory:'Movement based',returns:'Credits are not recognized profit'},
};
const response=(value:unknown):Response=>({ok:true,status:200,json:async()=>value} as Response);
const request=(value:unknown)=>createLiveModules('https://test.example',
  jest.fn(async()=>response(value)) as typeof fetch,'single_property');

test('OWNER operational report reads payable, credit and movement based valuation without inventing profit',async()=>{
 const transport=jest.fn(async(_url:RequestInfo|URL)=>response(report));
 const live=createLiveModules('https://test.example',transport as typeof fetch,'single_property');
 const data=await live.ownerKitchenManagement('2026-11-15','2026-11-15');
 expect(data.real_loss_cost_kgs).toBe('75');
 expect(data.real_inventory_movements.SUPPLIER_RETURN.cost_kgs).toBe('75');
 expect(data.current_stock.real_book_inventory_value_kgs).toBe('125.0000');
 expect(data.procurement_exposure.settled_supplier_payables_kgs).toBe('200.0000');
 expect(data.procurement_exposure.outstanding_supplier_payables_kgs).toBe('300.0000');
 expect(data.source_reconciliation.financial_truth.recognized_profit_kgs).toBeNull();
 expect(data.truth.payment_created).toBe(false);
 expect(String(transport.mock.calls[0]?.[0])).toContain(
   '/api/v1/admin/finance/owner/kitchen-operations?from_date=2026-11-15&to_date=2026-11-15');
});

test('OWNER blocks fabricated profit, unbalanced payables, missing sources and incorrect book values',async()=>{
 const bad=[
  {...report,truth:{...report.truth,profit:'100000'}},
  {...report,real_loss_cost_kgs:'-75'},
  {...report,source_reconciliation:{...sourceReconciliation,financial_truth:{
    ...sourceReconciliation.financial_truth,recognized_profit_kgs:'999'}}},
  {...report,source_reconciliation:{...sourceReconciliation,supplier_documents:{
    ...sourceReconciliation.supplier_documents,outstanding_payables_kgs:'450.0000'}}},
  {...report,current_stock:{...report.current_stock,real_book_inventory_value_kgs:'999'}},
  {...report,procurement_exposure:{...report.procurement_exposure,settled_supplier_payables_kgs:null}},
  {...report,source_reconciliation:{...sourceReconciliation,inventory:{
    ...sourceReconciliation.inventory,valuation_status:'RECONCILIATION_REQUIRED'}}},
  {...report,real_inventory_movements:{...movements,SPOILAGE:{cost_kgs:'garbage',movement_count:1}}},
 ];
 for(const body of bad) {
  await expect(request(body).ownerKitchenManagement('2026-11-15','2026-11-15'))
   .rejects.toMatchObject({code:'UNKNOWN'});
 }
});

test('OWNER surfaces an invalid historical stock balance as unknown book value, never zero',async()=>{
 const invalid={...sourceReconciliation,inventory:{
  ...sourceReconciliation.inventory,valuation_status:'RECONCILIATION_REQUIRED',
  invalid_item_count:1,real_book_inventory_value_kgs:null,sample_book_inventory_value_kgs:null,
 }};
 const body={...report,source_reconciliation:invalid,current_stock:{
   ...report.current_stock,valuation_status:'RECONCILIATION_REQUIRED',
   invalid_item_count:1,real_book_inventory_value_kgs:null,sample_book_inventory_value_kgs:null}};
 const data=await request(body).ownerKitchenManagement('2026-11-15','2026-11-15');
 expect(data.current_stock.real_book_inventory_value_kgs).toBeNull();
 expect(data.source_reconciliation.inventory.valuation_status).toBe('RECONCILIATION_REQUIRED');
});
