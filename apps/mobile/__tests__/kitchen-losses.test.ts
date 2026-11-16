import {createLiveModules} from '../src/api/liveModules';

const uuid='11111111-1111-4111-8111-111111111111';
const stockId='22222222-2222-4222-8222-222222222222';
const goodResponse=(body:unknown,status=200):Response=>({
  ok:status>=200&&status<300,status,json:async()=>body,
} as Response);

test('mobile stock includes a server-issued UUID for safe loss retry',async()=>{
  const transport=jest.fn(async()=>goodResponse({
    items:[{id:stockId,name:'Rice',unit:'KG',cost_per_unit_kgs:'100',
      is_sample:false,balance:'9'}],
    production_cost_kgs:'0',inventory_deducted_only_on_explicit_consume:true,
    new_loss_movement_id:uuid,
  }));
  const live=createLiveModules('https://test.example',transport as typeof fetch,'single_property');
  const stock=await live.kitchenStock();
  expect(stock.new_loss_movement_id).toBe(uuid);
  expect(stock.items[0].balance).toBe('9');
  const missing=createLiveModules('https://test.example',jest.fn(async()=>goodResponse({
    items:[],production_cost_kgs:'0',inventory_deducted_only_on_explicit_consume:true,
  })) as typeof fetch,'single_property');
  await expect(missing.kitchenStock()).resolves.toEqual({
    items:[],production_cost_kgs:'0',inventory_deducted_only_on_explicit_consume:true,
  });
  const invalid=createLiveModules('https://test.example',jest.fn(async()=>goodResponse({
    items:[],production_cost_kgs:'0',inventory_deducted_only_on_explicit_consume:true,
    new_loss_movement_id:'bad-id',
  })) as typeof fetch,'single_property');
  await expect(invalid.kitchenStock()).rejects.toBeDefined();
});

test('mobile preserves mutation UUID and payload for idempotent loss retry',async()=>{
  const transport=jest.fn(async()=>goodResponse({
    id:uuid,already_processed:false,quantity:'0.75',cost_kgs:'75',payment_created:false,
  },201));
  const live=createLiveModules('https://test.example',transport as typeof fetch,'single_property');
  const payload={movement_id:uuid,stock_item_id:stockId,kind:'SPOILAGE' as const,
    quantity:'0.75',reason:'  Spoiled   ingredients  '};
  const ack=await live.reportKitchenLoss(payload);
  expect(ack.payment_created).toBe(false);
  expect(ack.id).toBe(uuid);
  const args=transport.mock.calls[0] as unknown as [RequestInfo|URL,RequestInit];
  expect(String(args[0])).toContain('/api/v1/kitchen/stock/losses');
  expect(JSON.parse(String(args[1].body))).toEqual({
    movement_id:uuid,stock_item_id:stockId,kind:'SPOILAGE',quantity:'0.75',
    reason:'Spoiled ingredients',
  });
});

test('mobile rejects invalid loss before issuing any HTTP request',async()=>{
  const transport=jest.fn(async()=>goodResponse({}));
  const live=createLiveModules('https://test.example',transport as typeof fetch,'single_property');
  for(const reason of ['', 'x']){
    await expect(live.reportKitchenLoss({
      movement_id:uuid,stock_item_id:stockId,kind:'WASTE',quantity:'1',
      reason,
    })).rejects.toMatchObject({code:'BAD_REQUEST'});
  }
  await expect(live.reportKitchenLoss({
    movement_id:uuid,stock_item_id:stockId,kind:'WASTE',quantity:'0',reason:'Expired',
  })).rejects.toMatchObject({code:'BAD_REQUEST'});
  expect(transport).not.toHaveBeenCalled();
});

test('loss ledger returns actual actors, costs and reasons',async()=>{
  const transport=jest.fn(async()=>goodResponse({
    financial_truth:'INVENTORY_LOSS_NOT_PAYMENT',
    items:[{id:uuid,stock_item_id:stockId,stock_name:'Rice',unit:'KG',
      is_sample:false,kind:'WASTE',quantity:'1',unit_cost_kgs:'100',
      cost_kgs:'100',reason:'Lost batch',created_by_id:uuid,
      created_at:'2026-11-15T10:00:00+00:00'}],
  }));
  const live=createLiveModules('https://test.example',transport as typeof fetch,'single_property');
  const records=await live.kitchenLosses();
  expect(records).toHaveLength(1);
  expect(records[0].created_by_id).toBe(uuid);
  expect(records[0].cost_kgs).toBe('100');
});

test('network uncertainty retries the identical movement ID without a second client operation',async()=>{
  const bodies:string[]=[];
  const transport=jest.fn(async(_url:RequestInfo|URL,init?:RequestInit)=>{
    bodies.push(String(init?.body));
    if(bodies.length===1) throw new TypeError('Network request failed after server commit');
    return goodResponse({id:uuid,already_processed:true,quantity:'0.75',cost_kgs:'75',payment_created:false},201);
  });
  const live=createLiveModules('https://test.example',transport as typeof fetch,'single_property');
  const pending={movement_id:uuid,stock_item_id:stockId,kind:'SPOILAGE' as const,
    quantity:'0.75',reason:'Expired product'};
  await expect(live.reportKitchenLoss(pending)).rejects.toBeDefined();
  const retry=await live.reportKitchenLoss(pending);
  expect(retry.already_processed).toBe(true);
  expect(transport).toHaveBeenCalledTimes(2);
  expect(JSON.parse(bodies[0])).toEqual(JSON.parse(bodies[1]));
  expect(JSON.parse(bodies[0]).movement_id).toBe(uuid);
});
