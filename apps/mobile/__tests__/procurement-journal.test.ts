import {executeProcurement,readProcurement,PendingProcurement} from '../src/lib/pendingProcurement';
const mockRecords=new Map<string,string>();
const mockWrite=jest.fn(async(k:string,v:string)=>{mockRecords.set(k,v);});
const mockRemove=jest.fn(async(k:string)=>{mockRecords.delete(k);});
jest.mock('../src/lib/storage',()=>({getDurableItem:async(k:string)=>mockRecords.get(k)??null,
 setDurableItem:(k:string,v:string)=>mockWrite(k,v),removeDurableItem:(k:string)=>mockRemove(k)}));
const req='11111111-1111-4111-8111-111111111111',receipt='22222222-2222-4222-8222-222222222222',item='33333333-3333-4333-8333-333333333333';
const request:PendingProcurement={kind:'REQUEST',request_id:req,stock_item_id:item,quantity:'10',service_date:'2026-11-16',notes:'Kitchen'};
const receive:PendingProcurement={kind:'RECEIVE',receipt_id:receipt,requestId:req,quantity:'2'};
const ack=(op:PendingProcurement)=>op.kind==='REQUEST'?{id:op.request_id,status:'EXISTS',payment_created:false}:
 {id:op.receipt_id,request_id:op.requestId,status:'PARTIAL',already_processed:true,payment_created:false};
beforeEach(()=>{mockRecords.clear();mockWrite.mockClear().mockImplementation(async(k,v)=>{mockRecords.set(k,v);});mockRemove.mockClear().mockImplementation(async(k)=>{mockRecords.delete(k);});});
test.each([request,receive])('persist $kind before POST and replay exact operation after restart',async op=>{
 const send=jest.fn(async saved=>{expect(await readProcurement('hotel.example','user')).toEqual(saved);throw new Error('lost ack');});
 await expect(executeProcurement('hotel.example','user',async()=>op,send)).rejects.toThrow('lost ack');
 const retry=jest.fn(async()=>ack(op));await executeProcurement('hotel.example','user',null,retry);
 expect(retry).toHaveBeenCalledWith(op);expect(await readProcurement('hotel.example','user')).toBeNull();
});
test('storage failure prevents POST and never falls back to memory',async()=>{
 mockWrite.mockRejectedValue(new Error('storage unavailable'));const send=jest.fn();
 await expect(executeProcurement('hotel.example','user',async()=>request,send)).rejects.toThrow('storage unavailable');expect(send).not.toHaveBeenCalled();
});
test('mismatched ack retains journal, blocks a new action and isolates identities',async()=>{
 await expect(executeProcurement('hotel.example','user',async()=>receive,async()=>({...ack(receive),request_id:item}))).rejects.toThrow('Unverified');
 const create=jest.fn(async()=>request);await expect(executeProcurement('hotel.example','user',create,async()=>ack(request))).rejects.toThrow('pending');expect(create).not.toHaveBeenCalled();
 expect(await readProcurement('other.example','user')).toBeNull();expect(await readProcurement('hotel.example','other')).toBeNull();
});
test('concurrent local submissions send once',async()=>{
 let finish!:(x:unknown)=>void;const waiting=new Promise(r=>{finish=r;});const send=jest.fn(()=>waiting);
 const first=executeProcurement('hotel.example','user',async()=>receive,send);
 await expect(executeProcurement('hotel.example','user',async()=>receive,send)).rejects.toThrow('busy');
 finish(ack(receive));await first;expect(send).toHaveBeenCalledTimes(1);
});
test('failed journal removal retains the operation for safe replay',async()=>{
 mockRemove.mockRejectedValueOnce(new Error('disk'));await expect(executeProcurement('hotel.example','user',async()=>request,async()=>ack(request))).rejects.toThrow('disk');
 expect(await readProcurement('hotel.example','user')).toEqual(request);
 await executeProcurement('hotel.example','user',null,async()=>ack(request));expect(await readProcurement('hotel.example','user')).toBeNull();
});
test('corrupt or impossible-date journals block sending',async()=>{
 for(const op of [{...request,service_date:'2026-02-30'},{...receive,quantity:'0'},{...request,notes:123}]){
  mockRecords.set('marina.procurement.v1.hotel.example.user',JSON.stringify(op));const send=jest.fn();
  await expect(executeProcurement('hotel.example','user',null,send)).rejects.toThrow();expect(send).not.toHaveBeenCalled();
 }
});
