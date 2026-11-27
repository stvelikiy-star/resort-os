import {financeSummaryResponse,verifyOwnerAccrualReadiness} from '../src/api/contractValidation';

const delivered={
 scope:'OWNER_ONLY_PROPERTY_SCOPED',
 period:{from:'2026-11-16',to:'2026-11-16',timezone:'Asia/Bishkek',currency:'KGS'},
 accommodation:{
  qualified_reservations:1,delivered_booked_nights_count:1,
  allocated_booking_face_value_kgs:'334',
  night_preview_limit:500,night_preview_truncated:false,
  night_preview:[{reservation_id:'abc',service_date:'2026-11-16',
    allocated_booking_face_value_kgs:'334'}],
  excluded_reservations_count:0,exclusion_reasons:{},
  qualified_source:'CHECKED_OUT_RESERVATION_WITH_MATCHED_ACTUAL_STAY',
  rate_quality:'BOOKING_TOTAL_DISTRIBUTED_EVENLY_NOT_APPROVED_NIGHTLY_RATE',
 },
 dining:{
  served_orders_count:1,served_orders_face_value_kgs:'350',
  served_with_matching_folio_count:1,
  single_source_folio_linked_candidate_kgs:'350',
  excluded_orders_count:0,exclusion_reasons:{},
  non_dining_active_folio_charges:0,non_dining_folio_face_value_kgs:'0',
  non_dining_undated_folio_count:0,kitchen_and_folio_double_counted:false,
 },
 recognition:{
  recognized_lodging_revenue_kgs:null,recognized_dining_revenue_kgs:null,
  recognized_other_services_revenue_kgs:null,recognized_total_revenue_kgs:null,
  status:'SERVICE_DELIVERY_CANDIDATES_NOT_ACCOUNTING_POSTINGS',
  requires_rate_package_tax_discount_and_refund_reconciliation:true,
  requires_approved_immutable_revenue_journal:true,
  cash_received_as_revenue:false,automatic_posting:false,
 },
};
const accrual={
 documented_source_corrections:{
  recorded_corrections_count:5,reversed_corrections_count:1,
  active_by_kind_kgs:{DISCOUNT:'0.0000',PACKAGE_SPLIT:'200.0000',
    CANCELLATION:'30.0000',REFUND:'10.0000',TAX_COMPONENT:'20.0000'},
  metadata_only_documents_not_independently_verified:true,
  server_verified_document_bytes_count:5,missing_document_bytes_count:0,
  all_recorded_document_bytes_available:true,
  document_issuer_authenticity_independently_verified:false,
  refunds_are_cash_evidence_not_recognized_revenue:true,
  tax_and_packages_are_classifications_not_expenses:true,
  recognized_revenue_kgs:null,recognized_profit_kgs:null,
  status:'SOURCE_CORRECTIONS_NOT_ACCOUNTING_POSTINGS',
 },

 source_approval_journal:{
  approval_events_count:3,reversal_events_count:1,
  active_room_nights_count:1,active_served_dining_count:1,
  active_source_face_value_kgs:'683.0000',
  status:'SOURCE_APPROVAL_NOT_ACCOUNTING_RECOGNITION',
  recognized_revenue_kgs:null,recognized_profit_kgs:null,
 },

 delivered_revenue_sources:delivered,
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
  {...accrual,source_approval_journal:{...accrual.source_approval_journal,
    recognized_revenue_kgs:'683.0000'}},
  {...accrual,documented_source_corrections:{
    ...accrual.documented_source_corrections,
    recognized_revenue_kgs:'100.0000'}},
  {...accrual,documented_source_corrections:{
    ...accrual.documented_source_corrections,
    metadata_only_documents_not_independently_verified:false}},
  {...accrual,documented_source_corrections:{
    ...accrual.documented_source_corrections,
    server_verified_document_bytes_count:4}},
  {...accrual,documented_source_corrections:{
    ...accrual.documented_source_corrections,
    document_issuer_authenticity_independently_verified:true}},
  {...accrual,documented_source_corrections:{
    ...accrual.documented_source_corrections,
    refunds_are_cash_evidence_not_recognized_revenue:false}},
  {...accrual,documented_source_corrections:{
    ...accrual.documented_source_corrections,
    active_by_kind_kgs:{...accrual.documented_source_corrections.active_by_kind_kgs,
      DISCOUNT:'-1.0000'}}},

  {...accrual,source_approval_journal:{...accrual.source_approval_journal,
    reversal_events_count:4}},
  {...accrual,source_approval_journal:{...accrual.source_approval_journal,
    status:'ACCOUNTING_RECOGNIZED'}},
  {...accrual,recognition:{...accrual.recognition,customer_payments_are_revenue:true}},
  {...accrual,recognition:{...accrual.recognition,source_candidates_are_recognized:true}},
  {...accrual,delivered_revenue_sources:{...delivered,recognition:{
    ...delivered.recognition,recognized_total_revenue_kgs:'684.0000'}}},
  {...accrual,delivered_revenue_sources:{...delivered,dining:{
    ...delivered.dining,kitchen_and_folio_double_counted:true}}},
  {...accrual,delivered_revenue_sources:{...delivered,accommodation:{
    ...delivered.accommodation,allocated_booking_face_value_kgs:'-334'}}},
  {...accrual,revenue_source_candidates:{...accrual.revenue_source_candidates,amounts_are_not_additive_or_recognized:false}},
  {...accrual,kitchen_cost_movements:{...accrual.kitchen_cost_movements,receipt_inventory_inflow_kgs:'not-money'}},
  {...accrual,posted_owner_obligations:{...accrual.posted_owner_obligations,non_stock_obligations_candidate_kgs:'-100.0000'}},
 ];
 bad.forEach(v=>expect(()=>verifyOwnerAccrualReadiness(v)).toThrow());
});

const ledger={
 scope:'PROPERTY_SCOPED_READ_ONLY_PERIOD_DIAGNOSTIC',
 period:{from:summary.range.from,to:summary.range.to},
 counts:{lodging_expected:2,lodging_verified:1,dining_expected:1,dining_verified:1,
  other_service_expected:1,other_service_verified:1,expense_expected:1,expense_verified:1,
  cogs_expected:1,cogs_verified:0,refund_payment_expected:1,refund_payment_verified:0,
  package_entitlement_count:1,package_portions_count:2,refund_undated_count:0,
  active_corrections:0,unmatched_approved_sources:0},
 blockers:['FULL_PERIOD_POLICY_AND_CLOSE_NOT_VERIFIED'],
 posted_ledger_subtotals:{posting_line_count:3,revenue_kgs:'550.0000',expense_cogs_kgs:'700.0000',contribution_kgs:'-150.0000'},
 period_completeness_verified:false,recognized_profit_kgs:null,currency:'KGS',
};
test('mobile uses the same guarded OWNER ledger and preserves exact negative subtotal',()=>{
 expect(financeSummaryResponse({...summary,owner_ledger_period_coverage:ledger})
  .owner_ledger_period_coverage?.posted_ledger_subtotals.contribution_kgs).toBe('-150.0000');
});
test('mobile rejects stale period, fabricated final profit and impossible coverage',()=>{
 for(const bad of [
  {...ledger,period:{...ledger.period,to:'2026-11-17'}},
  {...ledger,recognized_profit_kgs:'150.0000'},
  {...ledger,period_completeness_verified:true},
  {...ledger,counts:{...ledger.counts,refund_payment_verified:2}},
  {...ledger,posted_ledger_subtotals:{...ledger.posted_ledger_subtotals,revenue_kgs:'NaN'}},
  {...ledger,blockers:[]},
 ]) expect(()=>financeSummaryResponse({...summary,owner_ledger_period_coverage:bad})).toThrow();
 const {owner_accrual_readiness_snapshot:_,...manager}=summary;
 expect(()=>financeSummaryResponse({...manager,owner_ledger_period_coverage:ledger})).toThrow();
});
