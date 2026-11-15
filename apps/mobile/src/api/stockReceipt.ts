import { ApiError } from './types';
export type StockReceipt = {movement_id:string;stock_item_id:string;quantity:string;notes:string};
export type StockReceiptAck = {id:string;stock_item_id:string;quantity:string;already_processed:boolean;unit_cost_kgs:string;payment_created:false};
export const receiptUuid = (v:unknown):v is string => typeof v==='string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(v);
export function receiptQuantity(value:string):string {
 if(!/^(?:0|[1-9]\d{0,9})(?:\.\d{1,6})?$/.test(value)) throw new ApiError('BAD_REQUEST','Invalid stock quantity');
 const [whole, fraction='']=value.split('.'); const trimmed=fraction.replace(/0+$/,'');
 const result=whole+(trimmed?'.'+trimmed:'');
 if(result==='0') throw new ApiError('BAD_REQUEST','Positive stock quantity required');
 return result;
}
export function stockReceipt(value:unknown):StockReceipt {
 if(!value||typeof value!=='object') throw new Error('Invalid stock receipt journal');
 const x=value as StockReceipt;
 if(!receiptUuid(x.movement_id)||!receiptUuid(x.stock_item_id)||typeof x.quantity!=='string'||typeof x.notes!=='string'||x.notes.length>500)
  throw new Error('Invalid stock receipt journal');
 return {movement_id:x.movement_id,stock_item_id:x.stock_item_id,quantity:receiptQuantity(x.quantity),notes:x.notes};
}
export function stockReceiptAck(value:unknown,receipt:StockReceipt):StockReceiptAck {
 if(!value||typeof value!=='object') throw new ApiError('UNKNOWN','Unverified stock receipt');
 const x=value as StockReceiptAck;
 if(x.id!==receipt.movement_id||x.stock_item_id!==receipt.stock_item_id||typeof x.quantity!=='string'||
  typeof x.already_processed!=='boolean'||x.payment_created!==false||typeof x.unit_cost_kgs!=='string'||!/^\d+(?:\.\d+)?$/.test(x.unit_cost_kgs))
  throw new ApiError('UNKNOWN','Unverified stock receipt');
 try{if(receiptQuantity(x.quantity)!==receiptQuantity(receipt.quantity))throw new Error();}
 catch{throw new ApiError('UNKNOWN','Stock receipt quantity mismatch');}
 return x;
}
