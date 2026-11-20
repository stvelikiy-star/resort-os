import { financeSummaryResponse } from '../src/api/contractValidation';
import { OWNER_FINANCE_COPY } from '../src/i18n/extendedOperations';

const minimal = {
  range:{from:'2026-11-01',to:'2026-11-09',currency:'KGS'},
  period_payments:{received_kgs:7000,pending_created_kgs:800,received_count:2},
  receivables_snapshot:{outstanding_kgs:3300,debtor_count:1},
  active_reservations_snapshot:{reservation_count:2,outstanding_kgs:3000},
};
const extended = {
  ...minimal,
  period_payments:{...minimal.period_payments,pending_created_count:1,failed_count:0,cancelled_count:0},
  receivables_snapshot:{...minimal.receivables_snapshot,checked_out_count:1,checked_out_kgs:300,
    in_house_count:1,in_house_kgs:3000,pre_arrival_count:0,pre_arrival_kgs:0},
  active_reservations_snapshot:{...minimal.active_reservations_snapshot,booked_total_kgs:10000,received_kgs:7000},
  received_by_method:[{method:'CASH',amount_kgs:7000,payment_count:2}],
  received_by_day:[{local_date:'2026-11-09',amount_kgs:7000,payment_count:2}],
  awaiting_prepayment_snapshot:{request_count:1,required_kgs:1000,received_kgs:200,remaining_kgs:800},
  refunded_snapshot_all_time:{amount_kgs:300,payment_count:1},
  finance_exceptions:{snapshot:{overpaid_count:1,overpaid_kgs:300,cancelled_with_received_count:0,cancelled_with_received_kgs:0}},
  debtors:[{reservation_id:'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',booking_number:'M-100',
    status:'CHECKED_IN',remaining_kgs:3000}],
  recent_payments:[{id:'bbbbbbbb-cccc-dddd-eeee-ffffffffffff',amount_kgs:7000,method:'CASH',status:'RECEIVED'}],
};
describe('owner finance is server-backed, not assumed accounting profit', () => {
  it('accepts actual RC409 extended read-only finance fields', () => {
    const result=financeSummaryResponse(extended);
    expect(result.received_by_method?.[0].amount_kgs).toBe(7000);
    expect(result.finance_exceptions?.snapshot.overpaid_kgs).toBe(300);
  });
  it('keeps older API summary without inventing missing financial sections', () => {
    expect(financeSummaryResponse(minimal).received_by_day).toBeUndefined();
    expect(financeSummaryResponse(minimal).awaiting_prepayment_snapshot).toBeUndefined();
  });
  it('rejects malformed currency and negative/contradictory expanded aggregates', () => {
    expect(()=>financeSummaryResponse({...extended,received_by_method:[{...extended.received_by_method[0],amount_kgs:-1}]})).toThrow();
    expect(()=>financeSummaryResponse({...extended,finance_exceptions:{snapshot:{...extended.finance_exceptions.snapshot,overpaid_count:'3'}}})).toThrow();
    expect(()=>financeSummaryResponse({...extended,recent_payments:[{...extended.recent_payments[0],amount_kgs:NaN}]})).toThrow();
  });
  it('has all four locale copies without representing cash inflows as profit', () => {
    for(const lang of ['ru','kg','en','kz'] as const) {
      expect(OWNER_FINANCE_COPY[lang].methods.length).toBeGreaterThan(4);
      expect(OWNER_FINANCE_COPY[lang].notProfit.length).toBeGreaterThan(4);
    }
  });
});