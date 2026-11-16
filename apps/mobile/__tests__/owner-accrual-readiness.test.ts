import {financeSummaryResponse,verifyOwnerAccrualReadiness} from '../src/api/contractValidation';

const accrual={
 scope:'OWNER_ONLY_PROPERTY_SCOPED',
 period:{from:'2026-11-16',to:'2026-11-16',timezone:'Asia/Bishkek',currency:'KGS'},
 posted_owner_obligations:{
  posted_total_kgs:'1600.0000',non_stock_obligations_candidate_kgs:'1000.0000',
  stock_overlap_review_kgs:'600.0000',posted_count:2,
  categories_kgs:{SUPPLIES:'600.0000',UTILITIES:'1000.0000',PAYROLL:'0.0000',
    MAINTENANCE:'0.0000',RENT:'0.0000',MARKETING:'0.0000',OTHER:'0.0000'},
  status:'CLASSIFICATION_REQUIRED',matching_supplier_invoice_count:1,
  matching_supplier_invoice_kgs:'600.0000',
 },
 kitchen_cost_movements:{
  production_cost_candidate_kgs:'300.0000',loss_cost_candidate_kgs:'25.0000',
  receipt_inventory_inflow_kgs:'700.0000',
  supplier_return_inventory_debit_kgs:'100.0000',
  sample_movement_gross_kgs:'0.0000',costs_are_reconciled_to_revenue:false,
 },
 revenue_source_candidates:{
  served_dining_orders_count:2,served_dining_face_value_kgs:'800.0000',
  served_without_linked_folio_count:1,served_without_linked_folio_kgs:'200.0000',
  served_with_active_folio_count:1,served_with_active_folio_kgs:'600.0000',
  disputed_dining_folio_count:0,
  manual_folio_active_count:1,manual_folio_face_value_kgs:'100.0000',
  manual_folio_without_service_date_count:0,
  checked_out_reservations_count:1,checked_out_booked_total_kgs:'5000.0000',
  amounts_are_not_additive_or_recognized:true,
 },
 source_valuation:{
  inventory_valuation_status:'MOVEMENT_BASED',
  source_mismatch_count:0,
  supplier_return_credit_minus_stock_cost_kgs:'40.0000',
  supplier_payables_outstanding_kgs:'300.0000',
 },
 recognition:{
  status:'REQUIRES_APPROVED_RECOGNITION_LEDGER',
  blockers:['RECOGNIZED_REVENUE_LEDGER_NOT_APPROVED'],
  recognized_revenue_kgs:null,recognized_expenses_kgs:null,recognized_profit_kgs:null,
  completeness_verified:false,customer_payments_are_revenue:false,
  supplier_settlements_are_expenses:false,receipts_are_expenses:false,
  source_candidates_are_recognized:false,
 },
};
const summary={
 range:{from:'2026-11-16',to:'2026-11-16',currency:'KGS'},
 period_payments:{received_kgs:10000,pending_created_kgs:0,received_count:1},
 receivables_snapshot:{outstanding_kgs:0,debtor_count:0},
 active_reservations_snapshot:{reservation_count:0,outstanding_kgs:0},
 owner_accrual_readiness_snapshot:accrual,
};

test('OWNER summary accepts confirmed candidates but never invents recognized profit',()=>{
 expect(financeSummaryResponse(summary).owner_accrual_readiness_snapshot?.recognition.recognized_profit_kgs).toBeNull();
 expect(financeSummaryResponse(summary).owner_accrual_readiness_snapshot?.kitchen_cost_movements.production_cost_candidate_kgs).toBe('300.0000');
});
test('legacy MANAGER summary without OWNER report remains supported',()=>{
 const {owner_accrual_readiness_snapshot:_ignored,...manager}=summary;
 expect(financeSummaryResponse(manager).owner_accrual_readiness_snapshot).toBeUndefined();
});
test('fail closed: fabricated recognized profit, double-counting, invalid blocked data',()=>{
 const bad=[
  {...accrual,recognition:{...accrual.recognition,recognized_profit_kgs:'123.0000'}},
  {...accrual,recognition:{...accrual.recognition,completeness_verified:true}},
  {...accrual,recognition:{...accrual.recognition,customer_payments_are_revenue:true}},
  {...accrual,recognition:{...accrual.recognition,source_candidates_are_recognized:true}},
  {...accrual,revenue_source_candidates:{...accrual.revenue_source_candidates,amounts_are_not_additive_or_recognized:false}},
  {...accrual,kitchen_cost_movements:{...accrual.kitchen_cost_movements,receipt_inventory_inflow_kgs:'not-money'}},
  {...accrual,posted_owner_obligations:{...accrual.posted_owner_obligations,non_stock_obligations_candidate_kgs:'-100.0000'}},
 ];
 bad.forEach(v=>expect(()=>verifyOwnerAccrualReadiness(v)).toThrow());
});
