import {Platform} from 'react-native';
import {receiptQuantity,receiptUuid} from '../api/stockReceipt';
import {getDurableItem,setDurableItem,removeDurableItem} from './storage';

export type PendingProcurement =
 | {kind:'REQUEST';request_id:string;stock_item_id:string;quantity:string;service_date:string|null;notes:string|null}
 | {kind:'RECEIVE';requestId:string;receipt_id:string;quantity:string;document_line_id?:string|null};
const active=new Set<string>();
function key(hotel:string,user:string){
 if(hotel.length>263||!/^[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*$/.test(hotel)||!/^[A-Za-z0-9_-]{1,100}$/.test(user))throw new Error('Invalid procurement identity');
 return 'marina.procurement.v1.'+hotel+'.'+user;
}
export function procurementOperation(value:unknown):PendingProcurement{
 if(!value||typeof value!=='object')throw new Error('Invalid procurement journal');
 const x=value as PendingProcurement;
 if(typeof x.quantity!=='string')throw new Error('Invalid procurement quantity');
 const quantity=receiptQuantity(x.quantity);
 if(x.kind==='RECEIVE'&&receiptUuid(x.requestId)&&receiptUuid(x.receipt_id))
  return {kind:x.kind,requestId:x.requestId,receipt_id:x.receipt_id,quantity,
   document_line_id:x.document_line_id==null?null:(receiptUuid(x.document_line_id)?x.document_line_id:(()=>{throw new Error('Invalid supplier source ID');})())};
 if(x.kind==='REQUEST'&&receiptUuid(x.request_id)&&receiptUuid(x.stock_item_id)&&
   (x.notes===null||(typeof x.notes==='string'&&x.notes.length<=500))&&
   (x.service_date===null||(typeof x.service_date==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x.service_date)&&
    Number.isFinite(Date.parse(x.service_date))&&new Date(x.service_date).toISOString().slice(0,10)===x.service_date)))
  return {kind:x.kind,request_id:x.request_id,stock_item_id:x.stock_item_id,quantity,service_date:x.service_date,notes:x.notes};
 throw new Error('Invalid procurement journal');
}
export async function readProcurement(hotel:string,user:string):Promise<PendingProcurement|null>{
 const raw=await getDurableItem(key(hotel,user));return raw===null?null:procurementOperation(JSON.parse(raw));
}
function confirmed(value:unknown,op:PendingProcurement){
 if(!value||typeof value!=='object')throw new Error('Unverified procurement acknowledgment');
 const x=value as Record<string,unknown>;
 if(x.payment_created!==false)throw new Error('Unverified procurement acknowledgment');
 if(op.kind==='REQUEST'&&x.id===op.request_id&&['REQUESTED','EXISTS'].includes(String(x.status)))return;
 if(op.kind==='RECEIVE'&&x.id===op.receipt_id&&x.request_id===op.requestId&&
    ['PARTIAL','RECEIVED'].includes(String(x.status))&&typeof x.already_processed==='boolean'&&
    (op.document_line_id==null||x.document_line_id===op.document_line_id))return;
 throw new Error('Unverified procurement acknowledgment');
}
/** Save the complete operation before POST; only explicit replay may send it again. */
export async function executeProcurement(hotel:string,user:string,create:(()=>Promise<PendingProcurement>)|null,
 send:(op:PendingProcurement)=>Promise<unknown>):Promise<void>{
 const storageKey=key(hotel,user);
 const run=async()=>{
  if(active.has(storageKey))throw new Error('Procurement is busy');active.add(storageKey);
  try{
   let op=await readProcurement(hotel,user);
   if(create){
    if(op)throw new Error('Review pending procurement first');
    op=procurementOperation(await create());
    if(await readProcurement(hotel,user))throw new Error('Pending procurement changed');
    await setDurableItem(storageKey,JSON.stringify(op));
   }
   if(!op)throw new Error('No pending procurement');
   confirmed(await send(op),op);
   if(JSON.stringify(await readProcurement(hotel,user))!==JSON.stringify(op))throw new Error('Procurement journal changed');
   await removeDurableItem(storageKey);
  }finally{active.delete(storageKey);}
 };
 if(Platform.OS==='web'){
  if(!globalThis.navigator?.locks)throw new Error('Browser operation locks unavailable');
  await globalThis.navigator.locks.request(storageKey,run);
 }else await run();
}
