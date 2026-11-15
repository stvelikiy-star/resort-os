"use client";
import {useEffect,useState,useCallback} from 'react';
import DirectStockReceipt from './DirectStockReceipt';
type StockItem={id:string;name:string;unit:string;balance:string;cost_per_unit_kgs:string;is_sample:boolean};
export default function StoreStaffStock(){
 const [items,setItems]=useState<StockItem[]>([]);
 const [message,setMessage]=useState('');
 const load=useCallback(async()=>{
  try{const r=await fetch('/core/api/v1/kitchen/stock',{cache:'no-store'});if(!r.ok)throw new Error('Доступ к складу: HTTP '+r.status);
   const body=await r.json();if(!Array.isArray(body.items))throw new Error('Неверный ответ склада');setItems(body.items);}
  catch(e){setMessage(e instanceof Error?e.message:'Ошибка склада');}
 },[]);
 useEffect(()=>{void load();const t=window.setInterval(()=>void load(),30000);return()=>clearInterval(t);},[load]);
 return <section className="shift-empty" data-testid="store-staff-stock"><h2>Склад · остатки и приход</h2>
 <p>Операции привязаны к вашей гостинице. Складской приход не является платёжной операцией.</p>
 {items.map(i=><div key={i.id}><strong>{i.name}</strong> · {i.balance} {i.unit}{i.is_sample?' · ТЕСТ':''}</div>)}
 {!items.length?<p>Склад пуст. Добавление номенклатуры доступно владельцу или менеджеру.</p>:null}
 <DirectStockReceipt items={items} onSaved={load}/>
 <button onClick={()=>void load()}>Обновить остатки</button>
 {message?<p role="status">{message}</p>:null}
 </section>;
}
