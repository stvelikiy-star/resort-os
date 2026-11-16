import { createLiveModules } from '../src/api/liveModules';
import { ApiError } from '../src/api/types';

const ORIGIN='https://staff.example.com/core';
const ID='11111111-1111-4111-8111-111111111111';
const STAY='22222222-2222-4222-8222-222222222222';
const TABLE='33333333-3333-4333-8333-333333333333';
const TARGET='44444444-4444-4444-8444-444444444444';
const ORDER='55555555-5555-4555-8555-555555555555';
const CHARGE='66666666-6666-4666-8666-666666666666';
const session={id:ID,stay_id:STAY,reservation_id:ORDER,table_id:TABLE,table_code:'A1',
  guest_name:'Synthetic Guest',room_code:'101',service_date:'2026-11-15',status:'SEATED',
  party_size:2,waiter_id:null,booking_number:'QA-1'};
const folio={id:ORDER,order_number:'ORD-1',guest_name:'Synthetic Guest',table_code:'A1',
  room_code:'101',total_kgs:750,folio_charge_id:null,eligible_to_post:true,financial_truth:'NOT_POSTED'};
function res(body:unknown,status=200):Response {
  return {ok:status>=200 && status<300,status,json:async()=>body} as Response;
}
const full=(f:jest.Mock)=>createLiveModules(ORIGIN,f as typeof fetch,'single_property');

it('loads live active seating and rejects fake/invalid response values',async()=>{
  const fetcher=jest.fn().mockResolvedValueOnce(res({service_date:'2026-11-15',items:[session]}))
    .mockResolvedValueOnce(res({items:[{...session,party_size:'2'}]}));
  await expect(full(fetcher).diningSeatingSessions()).resolves.toEqual([session]);
  await expect(full(fetcher).diningSeatingSessions()).rejects.toMatchObject({code:'UNKNOWN'});
  expect(new URL(fetcher.mock.calls[0][0]).pathname).toBe('/core/api/v1/dining/sessions');
  expect(new URL(fetcher.mock.calls[0][0]).search).toBe('?status=ACTIVE');
});

it('creates a real seating with stay/table/date and checks server acknowledgement',async()=>{
  const fetcher=jest.fn().mockResolvedValueOnce(res(session,201))
    .mockResolvedValueOnce(res({...session,table_id:TARGET},201));
  const api=full(fetcher);
  await expect(api.createDiningSeatingSession(STAY,TABLE,'2026-11-15')).resolves.toEqual(session);
  const [url,init]=fetcher.mock.calls[0];
  expect(new URL(url).pathname).toBe('/core/api/v1/dining/sessions');
  expect(init.method).toBe('POST');
  expect(JSON.parse(init.body)).toEqual({stay_id:STAY,table_id:TABLE,service_date:'2026-11-15',status:'SEATED'});
  await expect(api.createDiningSeatingSession(STAY,TABLE,'2026-11-15')).rejects.toMatchObject({code:'UNKNOWN'});
});

it('accepts RELEASED only with matching server status and session id',async()=>{
  const fetcher=jest.fn().mockResolvedValueOnce(res({...session,status:'RELEASED'}))
    .mockResolvedValueOnce(res({...session,status:'SEATED'}));
  const api=full(fetcher);
  await expect(api.setDiningSeatingStatus(ID,'RELEASED')).resolves.toMatchObject({id:ID,status:'RELEASED'});
  expect(fetcher.mock.calls[0][1].method).toBe('PATCH');
  await expect(api.setDiningSeatingStatus(ID,'RELEASED')).rejects.toMatchObject({code:'UNKNOWN'});
});

it('moves to available target via server and checks returned table id',async()=>{
  const fetcher=jest.fn().mockResolvedValueOnce(res({...session,table_id:TARGET}))
    .mockResolvedValueOnce(res(session));
  const api=full(fetcher);
  await expect(api.moveDiningSeatingSession(ID,TARGET)).resolves.toMatchObject({table_id:TARGET});
  const [url,init]=fetcher.mock.calls[0];
  expect(new URL(url).pathname).toBe('/core/api/v1/dining/sessions/'+ID+'/move');
  expect(JSON.parse(init.body)).toEqual({target_table_id:TARGET,waiter_mode:'KEEP'});
  await expect(api.moveDiningSeatingSession(ID,TARGET)).rejects.toMatchObject({code:'UNKNOWN'});
});

it('lists folio charges separately from payments and strictly verifies no payment creation',async()=>{
  const accepted={order_id:ORDER,charge_id:CHARGE,idempotent_replay:false,payment_created:false,
    financial_truth:'OPEN_FOLIO_CHARGE_NOT_PAYMENT'};
  const fetcher=jest.fn().mockResolvedValueOnce(res({items:[folio],truth:'not a payment'}))
    .mockResolvedValueOnce(res(accepted,201)).mockResolvedValueOnce(res({...accepted,payment_created:true},201));
  const api=full(fetcher);
  await expect(api.diningFolioOrders()).resolves.toEqual([folio]);
  await expect(api.postDiningFolioCharge(ORDER)).resolves.toEqual(accepted);
  await expect(api.postDiningFolioCharge(ORDER)).rejects.toMatchObject({code:'UNKNOWN'});
  expect(new URL(fetcher.mock.calls[1][0]).pathname).toBe('/core/api/v1/dining/orders/'+ORDER+'/folio');
});

it('fails closed in shared preview and on unsafe route ids',async()=>{
  const fetcher=jest.fn();
  const shared=createLiveModules(ORIGIN,fetcher,'shared_auth_preview');
  await expect(shared.diningSeatingSessions()).rejects.toThrow(/unavailable/);
  await expect(shared.diningFolioOrders()).rejects.toThrow(/unavailable/);
  await expect(full(fetcher).postDiningFolioCharge('../other')).rejects.toBeInstanceOf(ApiError);
  await expect(full(fetcher).moveDiningSeatingSession(ID,'../other')).rejects.toBeInstanceOf(ApiError);
  expect(fetcher).not.toHaveBeenCalled();
});

it('does not automatically retry a seating POST after lost response',async()=>{
  const fetcher=jest.fn().mockRejectedValue(new Error('network dropped'));
  await expect(full(fetcher).createDiningSeatingSession(STAY,TABLE,'2026-11-15'))
    .rejects.toMatchObject({code:'OFFLINE'});
  expect(fetcher).toHaveBeenCalledTimes(1);
});
