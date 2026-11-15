import {createLiveModules} from '../src/api/liveModules';
const reqId='11111111-1111-4111-8111-111111111111';
const receiptId='22222222-2222-4222-8222-222222222222';
const stockId='33333333-3333-4333-8333-333333333333';
const response=(body:unknown,status=200):Response=>({ok:status>=200&&status<300,status,json:async()=>body} as Response);

test('procurement list requires server UUIDs and authoritative request status',async()=>{
 const data={items:[{id:reqId,stock_item_id:stockId,stock_name:'Rice',unit:'KG',is_sample:false,
  quantity:'5',received_quantity:'0',status:'REQUESTED',service_date:null,notes:null,
  requested_by_id:reqId,approved_by_id:null,created_at:'2026-11-15T10:00:00Z'}],
  payment_created:false,new_request_id:reqId,new_receipt_id:receiptId};
 const live=createLiveModules('https://test.example',jest.fn(async()=>response(data)) as typeof fetch,'single_property');
 expect((await live.procurementRequests()).new_receipt_id).toBe(receiptId);
 const invalid=createLiveModules('https://test.example',jest.fn(async()=>response({
  ...data,new_request_id:'bad-id'})) as typeof fetch,'single_property');
 await expect(invalid.procurementRequests()).rejects.toMatchObject({code:'UNKNOWN'});
});

test('request retry after unknown network result preserves UUID and payload',async()=>{
 const bodies:string[]=[];
 const transport=jest.fn(async(_url:RequestInfo|URL,init?:RequestInit)=>{
  bodies.push(String(init?.body));
  if(bodies.length===1)throw new TypeError('Lost acknowledgment');
  return response({id:reqId,status:'EXISTS',payment_created:false},201);
 });
 const live=createLiveModules('https://test.example',transport as typeof fetch,'single_property');
 const mutation={request_id:reqId,stock_item_id:stockId,quantity:'5',
  service_date:'2026-11-15',notes:'Kitchen plan'};
 await expect(live.requestKitchenProcurement(mutation)).rejects.toBeDefined();
 await expect(live.requestKitchenProcurement(mutation)).resolves.toMatchObject({status:'EXISTS'});
 expect(bodies).toHaveLength(2);
 expect(JSON.parse(bodies[0])).toEqual(JSON.parse(bodies[1]));
});

test('approval and partial receipt preserve status and never synthesize payment',async()=>{
 const urls:string[]=[];
 const transport=jest.fn(async(url:RequestInfo|URL)=>{
  urls.push(String(url));
  return urls.length===1?
    response({id:reqId,status:'APPROVED',already_processed:false,payment_created:false}):
    response({id:receiptId,request_id:reqId,status:'PARTIAL',already_processed:false,payment_created:false},201);
 });
 const live=createLiveModules('https://test.example',transport as typeof fetch,'single_property');
 await expect(live.approveKitchenProcurement(reqId)).resolves.toMatchObject({payment_created:false});
 await expect(live.receiveKitchenProcurement(reqId,{receipt_id:receiptId,quantity:'2'}))
  .resolves.toMatchObject({status:'PARTIAL',payment_created:false});
 expect(urls[0]).toContain('/'+reqId+'/approve');
 expect(urls[1]).toContain('/'+reqId+'/receive');
});

test('invalid new request or receipt cannot reach transport',async()=>{
 const transport=jest.fn(async()=>response({}));
 const live=createLiveModules('https://test.example',transport as typeof fetch,'single_property');
 await expect(live.requestKitchenProcurement({request_id:reqId,stock_item_id:stockId,
  quantity:'0',service_date:null,notes:null})).rejects.toMatchObject({code:'BAD_REQUEST'});
 await expect(live.receiveKitchenProcurement(reqId,{receipt_id:'bad-id',quantity:'2'}))
  .rejects.toMatchObject({code:'BAD_REQUEST'});
 expect(transport).not.toHaveBeenCalled();
});
