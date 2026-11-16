import {executeStockReceipt,readStockReceipt} from '../src/lib/pendingStockReceipt';
import {StockReceipt} from '../src/api/stockReceipt';
const mockRecords=new Map<string,string>();
const mockWrite=jest.fn(async(key:string,value:string)=>{mockRecords.set(key,value);});
jest.mock('../src/lib/storage',()=>({getDurableItem:async(k:string)=>mockRecords.get(k)??null,
 setDurableItem:(k:string,v:string)=>mockWrite(k,v),removeDurableItem:async(k:string)=>{mockRecords.delete(k);}}));
const receipt:StockReceipt={movement_id:'11111111-1111-4111-8111-111111111111',stock_item_id:'22222222-2222-4222-8222-222222222222',quantity:'10',notes:'Receipt'};
const ack={id:receipt.movement_id,stock_item_id:receipt.stock_item_id,quantity:'10.000000',already_processed:true,unit_cost_kgs:'2.5000',payment_created:false as const};
beforeEach(()=>{mockRecords.clear();mockWrite.mockClear();mockWrite.mockImplementation(async(k,v)=>{mockRecords.set(k,v);});});
test('persist before network and replay exact operation after lost ack',async()=>{
 const send=jest.fn(async(payload:StockReceipt)=>{expect(await readStockReceipt('hotel.example','user')).toEqual(payload);throw new Error('timeout after commit');});
 await expect(executeStockReceipt('hotel.example','user',async()=>receipt,send)).rejects.toThrow('timeout');
 const restored=await readStockReceipt('hotel.example','user');expect(restored).toEqual(receipt);
 const retry=jest.fn(async()=>ack);
 await executeStockReceipt('hotel.example','user',null,retry);
 expect(retry).toHaveBeenCalledWith(receipt);expect(await readStockReceipt('hotel.example','user')).toBeNull();
});
test('storage failure blocks the network',async()=>{
 mockWrite.mockRejectedValue(new Error('storage unavailable'));const send=jest.fn(async()=>ack);
 await expect(executeStockReceipt('hotel.example','user',async()=>receipt,send)).rejects.toThrow('storage unavailable');expect(send).not.toHaveBeenCalled();
});
test('mismatched acknowledgement preserves journal and prevents a new receipt',async()=>{
 await expect(executeStockReceipt('hotel.example','user',async()=>receipt,async()=>({...ack,quantity:'11'}))).rejects.toThrow();
 expect(await readStockReceipt('hotel.example','user')).toEqual(receipt);
 await expect(executeStockReceipt('hotel.example','user',async()=>({...receipt,quantity:'12'}),async()=>ack)).rejects.toThrow('pending');
 expect(await readStockReceipt('other.example','user')).toBeNull();expect(await readStockReceipt('hotel.example','other-user')).toBeNull();
});
