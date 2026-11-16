"use client";
import {useCallback,useEffect,useRef,useState} from 'react';
import {receiptIdentity,receiptQuantity,receiptUuid} from '../lib/directStockReceipt';

type Purchase={id:string;stock_item_id:string;stock_name:string;unit:string;status:string;quantity:string;received_quantity:string};
type Source={id:string;stock_item_id:string;supplier_name:string;document_reference:string;remaining_quantity:string;unit_cost_kgs:string};
type Saved={requestId:string;receipt_id:string;quantity:string;document_line_id:string};

function parseSaved(value:unknown):Saved{
 if(!value||typeof value!=='object')throw new Error('Повреждён журнал закупочной приёмки');
 const x=value as Saved;
 if(!receiptUuid(x.requestId)||!receiptUuid(x.receipt_id)||!receiptUuid(x.document_line_id)||
    typeof x.quantity!=='string')throw new Error('Повреждён журнал закупочной приёмки');
 return {requestId:x.requestId,receipt_id:x.receipt_id,
  quantity:receiptQuantity(x.quantity),document_line_id:x.document_line_id};
}
function read(key:string):Saved|null{
 const value=localStorage.getItem(key);return value===null?null:parseSaved(JSON.parse(value));
}
async function json(path:string,init?:RequestInit):Promise<Record<string,unknown>>{
 const response=await fetch('/core/api/v1'+path,{cache:'no-store',...init});
 const body:unknown=await response.json().catch(()=>null);
 if(!response.ok)throw new Error('Операция недоступна: HTTP '+response.status);
 if(!body||typeof body!=='object'||Array.isArray(body))throw new Error('Неверный ответ API');
 return body as Record<string,unknown>;
}
/** Procurement receives are separate from unlinked direct stock movements. */
export default function ProcurementInvoiceReceipt({onSaved}:{onSaved:()=>Promise<unknown>}){
 const [scope,setScope]=useState('');
 const [pending,setPending]=useState<Saved|null>(null);
 const [requests,setRequests]=useState<Purchase[]>([]);
 const [sources,setSources]=useState<Source[]>([]);
 const [selectedRequest,setSelectedRequest]=useState('');
 const [selectedSource,setSelectedSource]=useState('');
 const [quantity,setQuantity]=useState('');
 const [ready,setReady]=useState(false);
 const [busy,setBusy]=useState(false);
 const [message,setMessage]=useState('');
 const lock=useRef(false);
 const reload=useCallback(async()=>{
  setReady(false);
  try{
   const identity=await receiptIdentity();
   const storage='marina.procurement.invoice.receipt.v1:'+identity;
   const previous=read(storage);
   setScope(storage);setPending(previous);
   const [ledger,documentSources]=await Promise.all([
    json('/kitchen/procurement/requests'),
    json('/kitchen/procurement/supplier-lines'),
   ]);
   if(!receiptUuid(ledger.new_receipt_id)||!Array.isArray(ledger.items)||
     documentSources.scope!=='CURRENT_HOTEL_RECEIPT_SOURCES'||
     documentSources.payment_created!==false||!Array.isArray(documentSources.items))
     throw new Error('Требуется совместимая версия API закупок');
   const items=(ledger.items as unknown[]).filter((x):x is Purchase=>
     !!x&&typeof x==='object'&&receiptUuid((x as Purchase).id)&&
     receiptUuid((x as Purchase).stock_item_id)&&
     ['APPROVED','PARTIAL'].includes((x as Purchase).status));
   const invoiceLines=(documentSources.items as unknown[]).filter((x):x is Source=>
     !!x&&typeof x==='object'&&receiptUuid((x as Source).id)&&receiptUuid((x as Source).stock_item_id));
   setRequests(items);setSources(invoiceLines);setReady(true);setMessage('');
  }catch(e){setMessage(e instanceof Error?e.message:'Невозможно проверить закупочную приёмку');}
 },[]);
 useEffect(()=>{void reload();const changed=()=>void reload();window.addEventListener('storage',changed);
  return ()=>window.removeEventListener('storage',changed);},[reload]);
 const submit=async(replay:boolean)=>{
  if(lock.current||!ready||!scope)return;
  let entered='';
  if(!replay){
   try{entered=receiptQuantity(quantity.replace(',','.'));}
   catch(e){setMessage(e instanceof Error?e.message:'Неверное количество');return;}
   const target=requests.find(x=>x.id===selectedRequest);
   const source=sources.find(x=>x.id===selectedSource);
   if(!target||!source||target.stock_item_id!==source.stock_item_id||
      Number(entered)>Number(source.remaining_quantity)){
    setMessage('Выберите подходящую накладную с достаточным остатком');return;
   }
   if(!window.confirm('Принять '+entered+' '+target.unit+' по накладной '+source.document_reference+'?'))return;
  }
  lock.current=true;setBusy(true);setMessage('');
  try{
   if(!navigator.locks)throw new Error('Нужен HTTPS-браузер с Web Locks');
   await navigator.locks.request(scope,async()=>{
    if('marina.procurement.invoice.receipt.v1:'+await receiptIdentity()!==scope)
      throw new Error('Гостиница или пользователь изменились');
    let saved=read(scope);
    if(!replay){
     if(saved)throw new Error('Есть неподтверждённая операция; новую создавать нельзя');
     const response=await json('/kitchen/procurement/requests');
     if(!receiptUuid(response.new_receipt_id))throw new Error('Нет нового ID прихода');
     saved=parseSaved({requestId:selectedRequest,receipt_id:response.new_receipt_id,
                       quantity:entered,document_line_id:selectedSource});
     if(read(scope))throw new Error('Журнал изменился');
     localStorage.setItem(scope,JSON.stringify(saved));setPending(saved);
    }
    if(!saved)throw new Error('Сохранённая операция отсутствует');
    const ack=await json('/kitchen/procurement/requests/'+encodeURIComponent(saved.requestId)+'/receive',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({receipt_id:saved.receipt_id,quantity:saved.quantity,
                           document_line_id:saved.document_line_id}),
    });
    if(ack.id!==saved.receipt_id||ack.request_id!==saved.requestId||
       ack.document_line_id!==saved.document_line_id||
       !['PARTIAL','RECEIVED'].includes(String(ack.status))||
       typeof ack.already_processed!=='boolean'||ack.payment_created!==false)
      throw new Error('Результат прихода не подтверждён');
    if(JSON.stringify(read(scope))!==JSON.stringify(saved))
      throw new Error('Журнал изменился, требуется сверка');
    localStorage.removeItem(scope);setPending(null);setQuantity('');
   });
   setMessage('Приход и накладная записаны одним действием, повторного движения нет');
   await onSaved();await reload();
  }catch(e){setMessage(e instanceof Error?e.message:'Неизвестный результат, повторите ту же операцию');}
  finally{lock.current=false;setBusy(false);}
 };
 const target=requests.find(x=>x.id===selectedRequest);
 const available=sources.filter(x=>x.stock_item_id===target?.stock_item_id&&Number(x.remaining_quantity)>0);
 const blocked=busy||!ready||!!pending;
 return <section data-testid="procurement-invoice-receipt">
  <h3>Приёмка закупки по накладной</h3>
  <p>Накладную предварительно регистрирует OWNER. Здесь записывается поступление без платежа.</p>
  {pending?<div role="alert"><p>Неподтверждённый приход сохранён; новая операция заблокирована.</p>
   <p data-testid="pending-invoice-receipt">{pending.receipt_id} · {pending.quantity} · {pending.document_line_id}</p>
   <button disabled={busy||!ready} onClick={()=>void submit(true)}>Повторить ту же приёмку</button>
  </div>:null}
  <label>Заявка <select aria-label="Заявка закупки" disabled={blocked} value={selectedRequest}
    onChange={e=>{setSelectedRequest(e.target.value);setSelectedSource('');}}>
    <option value="">Выберите утверждённую заявку</option>
    {requests.map(x=><option key={x.id} value={x.id}>{x.stock_name} · {x.received_quantity}/{x.quantity} {x.unit}</option>)}
  </select></label>
  <label>Накладная <select aria-label="Накладная поставщика" disabled={blocked||!target}
    value={selectedSource} onChange={e=>setSelectedSource(e.target.value)}>
    <option value="">Выберите накладную</option>
    {available.map(x=><option key={x.id} value={x.id}>{x.supplier_name} · {x.document_reference} · {x.remaining_quantity} {target?.unit}</option>)}
  </select></label>
  <label>Количество прихода <input aria-label="Количество приёмки закупки"
    disabled={blocked} type="number" min="0.000001" step="0.000001"
    value={quantity} onChange={e=>setQuantity(e.target.value)}/></label>
  <button disabled={blocked||!selectedSource||!selectedRequest||!quantity}
    onClick={()=>void submit(false)}>Принять по накладной</button>
  {!ready?<button disabled={busy} onClick={()=>void reload()}>Проверить доступ</button>:null}
  {message?<p role="status">{message}</p>:null}
 </section>;
}
