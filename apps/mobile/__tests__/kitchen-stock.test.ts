import { createLiveModules } from '../src/api/liveModules';
const stock={items:[{id:'11111111-1111-4111-8111-111111111111',name:'[ТЕСТ] Яйца',unit:'PCS',balance:'6.000000',cost_per_unit_kgs:'12.0000',is_sample:true}],
  production_cost_kgs:'68.00000',inventory_deducted_only_on_explicit_consume:true};
const ack={consumed_portions:2,already_processed:false,cost_kgs:'68.00000',payment_created:false};
const response=(status:number,payload:unknown):Response=>({ok:status>=200&&status<300,status,json:async()=>payload} as Response);
test('reads verified per-hotel stock without inventing balances',async()=>{
  const transport=jest.fn(async()=>response(200,stock));
  const m=createLiveModules('https://aska.example',transport as typeof fetch,'single_property');
  await expect(m.kitchenStock()).resolves.toEqual(stock);
  expect(transport.mock.calls.length).toBe(1);
});
test('requires explicit consume acknowledgment and no fake payment',async()=>{
  const transport=jest.fn(async()=>response(200,ack));
  const m=createLiveModules('https://aska.example',transport as typeof fetch,'single_property');
  await expect(m.consumeKitchenStock('22222222-2222-4222-8222-222222222222')).resolves.toEqual(ack);
});
test('rejects malformed negative stock and fabricated paid acknowledgments',async()=>{
  const badStock=createLiveModules('https://aska.example',jest.fn(async()=>response(200,{...stock,items:[{...stock.items[0],balance:'-1'}]})) as typeof fetch,'single_property');
  await expect(badStock.kitchenStock()).rejects.toMatchObject({code:'UNKNOWN'});
  const badAck=createLiveModules('https://aska.example',jest.fn(async()=>response(200,{...ack,payment_created:true})) as typeof fetch,'single_property');
  await expect(badAck.consumeKitchenStock('22222222-2222-4222-8222-222222222222')).rejects.toMatchObject({code:'UNKNOWN'});
});
test('does not substitute demo inventory for an unavailable live stock service',async()=>{
  const m=createLiveModules('https://aska.example',jest.fn(async()=>response(404,{detail:'Not Found'})) as typeof fetch,'single_property');
  await expect(m.kitchenStock()).rejects.toBeDefined();
});

test('validates stock receipts and does not turn receipt into a payment',async()=>{
  const payload={id:'33333333-3333-4333-8333-333333333333',quantity:'1.000000',payment_created:false};
  const fetchMock=jest.fn(async()=>response(201,payload));
  const api=createLiveModules('https://aska.example',fetchMock as typeof fetch,'single_property');
  await expect(api.receiveKitchenStock(stock.items[0].id,'1')).resolves.toEqual(payload);
  expect(fetchMock).toHaveBeenCalledTimes(1);
  await expect(api.receiveKitchenStock(stock.items[0].id,'-1')).rejects.toMatchObject({code:'BAD_REQUEST'});
  expect(fetchMock).toHaveBeenCalledTimes(1);
});
