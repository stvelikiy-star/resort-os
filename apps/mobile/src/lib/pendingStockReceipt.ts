import { StockReceipt, StockReceiptAck, stockReceipt, stockReceiptAck } from '../api/stockReceipt';
import { getDurableItem, removeDurableItem, setDurableItem } from './storage';
const active=new Set<string>();
function key(hotel:string,user:string):string {
 if(hotel.length>263||!/^[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*$/.test(hotel)||!/^[A-Za-z0-9_-]{1,100}$/.test(user))throw new Error('Invalid stock receipt identity');
 return 'marina.stock.receipt.v1.'+hotel+'.'+user;
}
export async function readStockReceipt(hotel:string,user:string):Promise<StockReceipt|null>{
 const raw=await getDurableItem(key(hotel,user));return raw===null?null:stockReceipt(JSON.parse(raw));
}
/** Persist BEFORE sending. Every failure retains the exact payload for explicit replay. */
export async function executeStockReceipt(hotel:string,user:string,create:(()=>Promise<StockReceipt>)|null,
 send:(payload:StockReceipt)=>Promise<StockReceiptAck>):Promise<StockReceiptAck>{
 const storageKey=key(hotel,user);if(active.has(storageKey))throw new Error('Stock receipt is busy');active.add(storageKey);
 try{
  let pending=await readStockReceipt(hotel,user);
  if(create){
   if(pending)throw new Error('Review pending stock receipt first');
   pending=stockReceipt(await create());
   if(await readStockReceipt(hotel,user))throw new Error('Pending receipt changed');
   await setDurableItem(storageKey,JSON.stringify(pending));
  }
  if(!pending)throw new Error('No pending stock receipt');
  const result=stockReceiptAck(await send(pending),pending);
  const current=await readStockReceipt(hotel,user);
  if(JSON.stringify(current)!==JSON.stringify(pending))throw new Error('Stock receipt journal changed');
  await removeDurableItem(storageKey);return result;
 }finally{active.delete(storageKey);}
}
