import { createLiveModules } from '../src/api/liveModules';
import { agentServiceDraft, agentServiceList } from '../src/api/agentServices';
const RID = '33333333-3333-4333-8333-333333333333';
const list = {reservation_id:RID,preview_limit:200,preview_truncated:false,items:[{
  id:'44444444-4444-4444-8444-444444444444',reservation_id:RID,service_code:'TRANSFER',status:'DONE',
  service_date:'2026-11-15',service_time:'10:30',description:'Reception',
}]};
const response = (value: unknown) => ({ok:true,status:200,json:async()=>value}) as Response;
test('own reservation read uses existing endpoint and preserves actual status', async () => {
  const transport = jest.fn(async(_url:RequestInfo|URL, _init?:RequestInit)=>response(list));
  const api = createLiveModules('https://hotel.example',transport as typeof fetch,'single_property');
  expect((await api.agentGuestServices(RID)).items[0].status).toBe('DONE');
  expect(String(transport.mock.calls[0][0])).toContain('/api/v1/admin/guest-services?reservation_id='+RID+'&status=ALL');
});
test('foreign IDs, unknown statuses, bad dates and duplicate rows fail closed', () => {
  for (const invalid of [
    {...list,reservation_id:'other'}, {...list,preview_limit:0}, {...list,preview_truncated:undefined},
    {...list,items:[{...list.items[0],reservation_id:'other'}]},
    {...list,items:[{...list.items[0],status:'ASSUMED_SUCCESS'}]},
    {...list,items:[{...list.items[0],service_code:'TOWELS'}]},
    {...list,items:[{...list.items[0],service_date:'2026-02-30'}]},
    {...list,items:[list.items[0],list.items[0]]},
  ]) expect(()=>agentServiceList(invalid,RID)).toThrow();
});
test('schedule and note are normalized without device timezone conversion', async () => {
  const transport = jest.fn(async(_url:RequestInfo|URL, _init?:RequestInit)=>response({id:'task',reservation_id:RID,service_code:'TRANSFER'}));
  const api = createLiveModules('https://hotel.example',transport as typeof fetch,'single_property');
  await api.addAgentGuestService(RID,'TRANSFER',{service_date:'2026-11-15',service_time:'10:30',description:' Reception '});
  expect(JSON.parse(String(transport.mock.calls[0][1]?.body))).toMatchObject({
    reservation_id:RID,service_date:'2026-11-15',service_time:'10:30',description:'Reception',
  });
});
test('invalid schedule or excessively long note never sends a request', () => {
  for (const invalid of [{service_date:'2026-02-30'},{service_time:'10:30'},
    {service_date:'2026-11-15',service_time:'24:00'},{description:'x'.repeat(2001)}])
    expect(()=>agentServiceDraft(invalid)).toThrow();
});
