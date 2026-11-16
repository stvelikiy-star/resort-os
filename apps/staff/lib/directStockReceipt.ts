export type DirectReceipt={movement_id:string;stock_item_id:string;quantity:string;notes:string};
export const receiptUuid=(v:unknown):v is string=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(v);
export function receiptQuantity(v:string):string{
 if(!/^(?:0|[1-9]\d{0,9})(?:\.\d{1,6})?$/.test(v))throw new Error('Укажите положительное количество, до 6 знаков после запятой');
 const [whole,fraction='']=v.split('.');const f=fraction.replace(/0+$/,'');const result=whole+(f?'.'+f:'');
 if(result==='0')throw new Error('Количество должно быть положительным');return result;
}
export function parseReceipt(v:unknown):DirectReceipt{
 if(!v||typeof v!=='object')throw new Error('Повреждён журнал прихода');const x=v as DirectReceipt;
 if(!receiptUuid(x.movement_id)||!receiptUuid(x.stock_item_id)||typeof x.notes!=='string'||x.notes.length>500||typeof x.quantity!=='string')throw new Error('Повреждён журнал прихода');
 return {movement_id:x.movement_id,stock_item_id:x.stock_item_id,quantity:receiptQuantity(x.quantity),notes:x.notes};
}
export async function receiptIdentity():Promise<string>{
 const r=await fetch('/core/api/v1/auth/me',{cache:'no-store'});if(!r.ok)throw new Error('Подтвердите вход в систему');
 const me=await r.json();
 if(!receiptUuid(me.id)||typeof me.property_code!=='string'||!['OWNER','MANAGER','STORE_STAFF'].includes(me.role))throw new Error('Нет права на приход склада');
 return 'marina.stock.receipt.v1:'+JSON.stringify([window.location.origin,me.property_id??me.property_code,me.id]);
}
export function readReceipt(key:string):DirectReceipt|null{
 const raw=localStorage.getItem(key);return raw===null?null:parseReceipt(JSON.parse(raw));
}
export async function sendReceipt(payload:DirectReceipt):Promise<void>{
 const r=await fetch('/core/api/v1/kitchen/stock/receipts',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
 if(!r.ok)throw new Error('Приход не подтверждён: HTTP '+r.status+'. Повторите сохранённую операцию.');
 const x=await r.json();
 if(x.id!==payload.movement_id||x.stock_item_id!==payload.stock_item_id||typeof x.quantity!=='string'||
  receiptQuantity(x.quantity)!==payload.quantity||typeof x.already_processed!=='boolean'||x.payment_created!==false||
  typeof x.unit_cost_kgs!=='string'||!/^\d+(?:\.\d+)?$/.test(x.unit_cost_kgs))throw new Error('Неверное подтверждение прихода');
}
