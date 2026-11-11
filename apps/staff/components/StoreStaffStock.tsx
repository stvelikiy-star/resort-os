"use client";
import {useEffect,useState,useCallback} from 'react';
type StockItem={id:string;name:string;unit:string;balance:string;cost_per_unit_kgs:string;is_sample:boolean};
export default function StoreStaffStock(){
 const [items,setItems]=useState<StockItem[]>([]);
 const [selected,setSelected]=useState('');const [qty,setQty]=useState('');
 const [busy,setBusy]=useState(false);const [message,setMessage]=useState('');
 const load=useCallback(async()=>{
  try{const r=await fetch('/core/api/v1/kitchen/stock',{cache:'no-store'});if(!r.ok)throw new Error('Доступ к складу: HTTP '+r.status);
   const body=await r.json();if(!Array.isArray(body.items))throw new Error('Неверный ответ склада');setItems(body.items);}
  catch(e){setMessage(e instanceof Error?e.message:'Ошибка склада');}
 },[]);
 useEffect(()=>{void load();const t=window.setInterval(()=>void load(),30000);return()=>clearInterval(t);},[load]);
 const receipt=async()=>{
  if(busy)return;
  const q=qty.replace(',','.');if(!selected||!/^(?:0|[1-9]\d*)(?:\.\d{1,6})?$/.test(q)||Number(q)<=0){setMessage('Укажите продукт и положительное количество');return;}
  if(!window.confirm('Записать приход '+q+' на выбранный продукт?'))return;
  setBusy(true);setMessage('');try{
   const r=await fetch('/core/api/v1/kitchen/stock/receipts',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({stock_item_id:selected,quantity:q,notes:'Приход через STORE_STAFF'})});
   if(!r.ok)throw new Error('Сервер отклонил приход: HTTP '+r.status);
   const result=await r.json();if(result.payment_created!==false)throw new Error('Ошибка подтверждения прихода');
   setQty('');setMessage('Приход записан в PostgreSQL, платёж не создан.');await load();
  }catch(e){setMessage(e instanceof Error?e.message:'Ошибка записи');}finally{setBusy(false);}
 };
 return <section className="shift-empty" data-testid="store-staff-stock"><h2>Склад · остатки и приход</h2>
 <p>Операции привязаны к вашей гостинице. Складской приход не является платёжной операцией.</p>
 {items.map(i=><div key={i.id}><strong>{i.name}</strong> · {i.balance} {i.unit}{i.is_sample?' · ТЕСТ':''}</div>)}
 {!items.length?<p>Склад пуст. Добавление номенклатуры доступно владельцу или менеджеру.</p>:null}
 <label>Продукт <select aria-label="Продукт прихода" value={selected} onChange={e=>setSelected(e.target.value)}>
 <option value="">Выберите продукт</option>{items.map(i=><option key={i.id} value={i.id}>{i.name} · {i.unit}</option>)}</select></label>
 <label>Количество <input aria-label="Количество прихода" type="number" min="0.000001" step="0.000001" value={qty} onChange={e=>setQty(e.target.value)} /></label>
 <button disabled={!selected||!qty||busy} onClick={()=>void receipt()}>Записать приход</button>
 <button disabled={busy} onClick={()=>void load()}>Обновить остатки</button>
 {message?<p role="status">{message}</p>:null}
 </section>;
}
