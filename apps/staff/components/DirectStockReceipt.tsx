"use client";
import {useCallback,useEffect,useRef,useState} from 'react';
import {DirectReceipt,parseReceipt,readReceipt,receiptIdentity,receiptQuantity,receiptUuid,sendReceipt} from '../lib/directStockReceipt';
type Item={id:string;name:string;unit:string};
/** Shared by STORE_STAFF and kitchen; journals contain no credentials. */
export default function DirectStockReceipt({items,onSaved}:{items:Item[];onSaved:()=>Promise<unknown>}){
 const [scope,setScope]=useState('');const [pending,setPending]=useState<DirectReceipt|null>(null);
 const [selected,setSelected]=useState('');const [quantity,setQuantity]=useState('');
 const [ready,setReady]=useState(false);const [busy,setBusy]=useState(false);const [message,setMessage]=useState('');
 const lock=useRef(false);
 const refresh=useCallback(async()=>{
  setReady(false);try{const key=await receiptIdentity();setScope(key);setPending(readReceipt(key));setReady(true);}
  catch(e){setMessage(e instanceof Error?e.message:'Журнал прихода недоступен');}
 },[]);
 useEffect(()=>{void refresh();const changed=()=>void refresh();window.addEventListener('storage',changed);return()=>window.removeEventListener('storage',changed);},[refresh]);
 const submit=async(resume:boolean)=>{
  if(lock.current||!ready||!scope)return;
  let q='';try{if(!resume){q=receiptQuantity(quantity.replace(',','.'));if(!receiptUuid(selected))throw new Error('Выберите продукт');}}
  catch(e){setMessage(e instanceof Error?e.message:'Проверьте количество');return;}
  if(!resume&&!window.confirm('Записать приход '+q+' на выбранный продукт?'))return;
  lock.current=true;setBusy(true);setMessage('');
  try{
   if(!navigator.locks)throw new Error('Для безопасного прихода используйте браузер с поддержкой Web Locks (HTTPS).');
   await navigator.locks.request(scope,async()=>{
    if(await receiptIdentity()!==scope)throw new Error('Пользователь или гостиница изменились. Обновите страницу.');
    let record=readReceipt(scope);
    if(!resume){
     if(record)throw new Error('Сначала подтвердите сохранённый приход');
     const response=await fetch('/core/api/v1/kitchen/stock',{cache:'no-store'});
     if(!response.ok)throw new Error('Не удалось получить ID операции');
     const stock=await response.json();if(!receiptUuid(stock.new_receipt_movement_id))throw new Error('Обновите сервер для безопасного прихода');
     record=parseReceipt({movement_id:stock.new_receipt_movement_id,stock_item_id:selected,quantity:q,notes:'Direct staff stock receipt'});
     if(readReceipt(scope))throw new Error('Сохранённый приход изменился');
     localStorage.setItem(scope,JSON.stringify(record));setPending(record);
    }
    if(!record)throw new Error('Сохранённый приход не найден');
    await sendReceipt(record);
    if(JSON.stringify(readReceipt(scope))!==JSON.stringify(record))throw new Error('Журнал изменился; требуется сверка');
    localStorage.removeItem(scope);setPending(null);setQuantity('');setMessage('Приход подтверждён. Повторного движения и платежа нет.');
   });
   await onSaved();
  }catch(e){setMessage(e instanceof Error?e.message:'Результат не подтверждён. Повторите сохранённую операцию.');}
  finally{await refresh();lock.current=false;setBusy(false);}
 };
 const blocked=busy||!ready||!!pending;
 return <div data-testid="direct-stock-receipt">
 <h3>Приход продуктов</h3>
 {pending?<div role="alert"><p>Есть неподтверждённый приход. Новый приход заблокирован.</p>
 <p data-testid="pending-receipt">{pending.movement_id} · {pending.quantity} · {pending.stock_item_id}</p>
 <button disabled={busy||!ready} onClick={()=>void submit(true)}>Проверить / повторить тот же приход</button></div>:null}
 <label>Продукт <select aria-label="Продукт прихода" disabled={blocked} value={selected} onChange={e=>setSelected(e.target.value)}>
 <option value="">Выберите продукт</option>{items.map(i=><option key={i.id} value={i.id}>{i.name} · {i.unit}</option>)}</select></label>
 <label>Количество <input aria-label="Количество прихода" disabled={blocked} type="number" min="0.000001" step="0.000001" value={quantity} onChange={e=>setQuantity(e.target.value)}/></label>
 <button disabled={blocked||!selected||!quantity} onClick={()=>void submit(false)}>Записать приход</button>
 {!ready?<button disabled={busy} onClick={()=>void refresh()}>Проверить доступ к журналу</button>:null}
 {message?<p role="status">{message}</p>:null}
 </div>;
}
