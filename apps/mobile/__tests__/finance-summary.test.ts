import { createLiveModules } from '../src/api/liveModules';
import { canReadFinance } from '../src/api/financeAccess';
import { financeSummaryResponse } from '../src/api/contractValidation';
import type { AuthUser } from '../src/api/types';

const user = (role: AuthUser['role'], grants: string[]): AuthUser =>
  ({ id:'staff',username:'staff',display_name:'Staff',role,property_code:'HOTEL_A',module_permissions:grants });
const summary = {
  range:{from:'2026-10-07',to:'2026-11-05',currency:'KGS'},
  period_payments:{received_kgs:4700,pending_created_kgs:900,received_count:2},
  receivables_snapshot:{outstanding_kgs:1200,debtor_count:1},
  active_reservations_snapshot:{outstanding_kgs:800,reservation_count:3},
};
function response(status:number, data:unknown=summary):Response {
  return { ok:status>=200&&status<300,status,json:async()=>data } as Response;
}
it('allows only OWNER/MANAGER with FINANCE grants; not reception or a manager without permission',()=>{
  expect(canReadFinance(user('OWNER',['FINANCE']))).toBe(true);
  expect(canReadFinance(user('MANAGER',['FINANCE']))).toBe(true);
  expect(canReadFinance(user('MANAGER',['PMS']))).toBe(false);
  expect(canReadFinance(user('RECEPTION',['FINANCE']))).toBe(false);
});
it('reads confirmed finance/summary aggregates in shared mode, without bypassing 503 modules',async()=>{
  const transport=jest.fn(async (_url: string, _init?: RequestInit)=>response(200));
  const live=createLiveModules('https://platform.example',transport as typeof fetch,'shared_auth_preview');
  await expect(live.financeSummary('2026-10-07','2026-11-05')).resolves.toEqual(summary);
  expect(transport).toHaveBeenCalledTimes(1);
  expect(String(transport.mock.calls[0][0])).toBe('https://platform.example/api/v1/admin/finance/summary?from_date=2026-10-07&to_date=2026-11-05');
  expect(financeSummaryResponse(summary).period_payments.received_kgs).toBe(4700);
});
it('propagates HTTP 403 without showing finances',async()=>{
  const transport=jest.fn(async()=>response(403));
  await expect(createLiveModules('https://platform.example',transport as typeof fetch,'shared_auth_preview')
    .financeSummary('2026-10-07','2026-11-05')).rejects.toMatchObject({code:'FORBIDDEN'});
});
it('propagates HTTP 503 rather than substituting DEMO or zero finance totals',async()=>{
  const transport=jest.fn(async()=>response(503));
  await expect(createLiveModules('https://platform.example',transport as typeof fetch,'shared_auth_preview')
    .financeSummary('2026-10-07','2026-11-05')).rejects.toMatchObject({code:'UNKNOWN'});
  expect(transport).toHaveBeenCalledTimes(2); // GET retry policy, never an invented fallback
});
it('rejects malformed or missing financial measurements',()=>{
  expect(()=>financeSummaryResponse({ ...summary, period_payments:{received_count:2} })).toThrow();
});
