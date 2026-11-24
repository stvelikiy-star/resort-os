"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type OrderLine = { id:string; menu_item_id:string; name_ru:string; quantity:number; status:string };
type ServedOrder = { id:string; order_number:string; status:string; completed_at:string|null; items:OrderLine[] };
type Batch = { id:string; menu_item_id:string; name_ru:string; service_date:string; prepared_quantity:number; meal_type:string };
type Allocation = { id:string; order_item_id:string; production_target_id:string; portions:number; cost_kgs:string; menu_name:string };
type AllocationRead = { order_id:string; items:Allocation[] };

async function api(path:string, init?:RequestInit):Promise<Record<string,unknown>> {
  const response=await fetch("/core/api/v1/kitchen/"+path, {cache:"no-store",...init});
  const body:unknown=await response.json().catch(()=>null);
  const data=body && typeof body==="object" && !Array.isArray(body) ? body as Record<string,unknown> : {};
  if(!response.ok) {
    const raw=data.detail;
    const detail=raw && typeof raw==="object" && "code" in raw ? String((raw as {code:string}).code) :
      typeof raw==="string" ? raw : "HTTP "+response.status;
    if(response.status===401) throw new Error("SESSION_EXPIRED");
    throw new Error(detail);
  }
  return data;
}

function localDate(date:Date):string {
  return [date.getFullYear(),String(date.getMonth()+1).padStart(2,"0"),String(date.getDate()).padStart(2,"0")].join("-");
}
function dateAgo(days:number):string {
  const d=new Date();d.setDate(d.getDate()-days);return localDate(d);
}

/** COOK only. Writes an auditable assignment; does NOT charge guest or book profit. */
export default function CookBatchAssignments({onEnd}:{onEnd:()=>void}) {
  const [fromDate,setFromDate]=useState(()=>dateAgo(6));
  const [throughDate,setThroughDate]=useState(()=>dateAgo(0));
  const [orders,setOrders]=useState<ServedOrder[]>([]);
  const [batches,setBatches]=useState<Batch[]>([]);
  const [orderId,setOrderId]=useState("");
  const [lineId,setLineId]=useState("");
  const [batchId,setBatchId]=useState("");
  const [portions,setPortions]=useState("1");
  const [existing,setExisting]=useState<Allocation[]>([]);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const [notice,setNotice]=useState("");
  // Keep one operation UUID after an uncertain HTTP result; retry is idempotent.
  const operationId=useRef<string|null>(null);
  const refresh=useCallback(async()=>{
    if(throughDate<fromDate)throw new Error("Конец периода раньше начала");
    const from=new Date(fromDate+"T12:00:00"),to=new Date(throughDate+"T12:00:00");
    if((to.getTime()-from.getTime())/86400000>31)throw new Error("Максимальный период — 32 дня");
    const [ordersResult,targetsResult]=await Promise.all([
      api("orders?status=SERVED"),
      api("production-targets?from_date="+encodeURIComponent(fromDate)+"&through_date="+encodeURIComponent(throughDate)),
    ]);
    if(!Array.isArray(ordersResult.items)||!Array.isArray(targetsResult.items))throw new Error("Неверный формат данных кухни");
    const served=(ordersResult.items as ServedOrder[]).filter(o=>o.status==="SERVED"&&
      !!o.completed_at&&localDate(new Date(o.completed_at))>=fromDate&&
      localDate(new Date(o.completed_at))<=throughDate);
    setOrders(served);
    setBatches(targetsResult.items as Batch[]);
  },[fromDate,throughDate]);
  const refreshAllocations=useCallback(async()=>{
    if(!orderId){setExisting([]);return;}
    const details=await api("orders/"+encodeURIComponent(orderId)+"/batch-allocations") as unknown as AllocationRead;
    if(details.order_id!==orderId||!Array.isArray(details.items))throw new Error("Неподтверждённый список партий");
    setExisting(details.items);
  },[orderId]);

  useEffect(()=>{void refresh().catch(e=>{
    if(e instanceof Error&&e.message==="SESSION_EXPIRED"){onEnd();return;}
    setError(e instanceof Error?e.message:"Не удалось загрузить поданные заказы");
  });},[refresh,onEnd]);
  useEffect(()=>{void refreshAllocations().catch(e=>{
    if(e instanceof Error&&e.message==="SESSION_EXPIRED"){onEnd();return;}
    setError(e instanceof Error?e.message:"Не удалось прочитать партии заказа");
  });},[refreshAllocations,onEnd]);
  const selected=orders.find(o=>o.id===orderId);
  const line=selected?.items.find(x=>x.id===lineId&&x.status==="SERVED");
  const consumed=existing.filter(a=>a.order_item_id===lineId).reduce((n,a)=>n+a.portions,0);
  const left=Math.max(0,(line?.quantity??0)-consumed);
  const options=batches.filter(t=>!!line && t.menu_item_id===line.menu_item_id&&t.prepared_quantity>0 &&
    !!selected?.completed_at && t.service_date<=localDate(new Date(selected.completed_at)));
  const valid=!!selected&&!!line&&options.some(t=>t.id===batchId)&&Number.isSafeInteger(Number(portions))&&
    Number(portions)>=1&&Number(portions)<=left;

  async function save(){
    if(busy||!valid||!selected)return;
    setBusy(true);setError("");setNotice("");
    if(!operationId.current)operationId.current=crypto.randomUUID();
    try{
      const outcome=await api("orders/"+encodeURIComponent(selected.id)+"/batch-allocations",{
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({id:operationId.current,order_item_id:lineId,production_target_id:batchId,portions:Number(portions)}),
      });
      if(outcome.source!=="OPERATOR_ATTESTED"||outcome.recognized_profit_posted!==false)
        throw new Error("Сервер вернул неподтверждённый результат операции");
      setNotice(outcome.already_processed?
        "Привязка уже зарегистрирована — повторного расхода нет.":
        "Партия привязана к выданному блюду. Учтённая стоимость: "+outcome.cost_kgs+" сом. Прибыль не начислялась.");
      operationId.current=null;
      await refreshAllocations();
    }catch(e){
      if(e instanceof Error&&e.message==="SESSION_EXPIRED"){onEnd();return;}
      setError(e instanceof Error?e.message:"Неизвестный результат. Повторите запрос с тем же кодом операции.");
    }finally{setBusy(false);}
  }
  return <section className="shift-card" data-testid="cook-batch-attribution">
    <h2>Партии → выданные блюда</h2>
    <p>Выберите конкретную приготовленную партию для уже выданного заказа. Это учёт партии, не списание склада повторно и не бухгалтерская прибыль.</p>
    <label>С даты <input aria-label="Партии с даты" type="date" value={fromDate} onChange={e=>setFromDate(e.target.value)}/></label>
    <label>По дату <input aria-label="Партии по дату" type="date" value={throughDate} onChange={e=>setThroughDate(e.target.value)}/></label>
    <button type="button" disabled={busy} onClick={()=>void refresh().catch(e=>setError(e instanceof Error?e.message:"Ошибка загрузки"))}>Обновить заказы и партии</button>
    <label>Выданный заказ
      <select aria-label="Выданный заказ" value={orderId} onChange={e=>{
        setOrderId(e.target.value);setLineId("");setBatchId("");setError("");setNotice("");operationId.current=null;
      }}>
        <option value="">Выберите заказ</option>
        {orders.map(o=><option key={o.id} value={o.id}>{o.order_number} · {o.completed_at?.slice(0,10)}</option>)}
      </select>
    </label>
    {orderId&&<label>Блюдо и количество
      <select aria-label="Блюдо заказа" value={lineId} onChange={e=>{
        setLineId(e.target.value);setBatchId("");setNotice("");operationId.current=null;
      }}>
        <option value="">Выберите блюдо</option>
        {selected?.items.filter(x=>x.status==="SERVED").map(x=>
          <option key={x.id} value={x.id}>{x.name_ru} · {x.quantity} порц.</option>)}
      </select>
    </label>}
    {line&&<>
      <p>Всего выдано: {line.quantity}; уже привязано: {consumed}; осталось привязать: {left} порц.</p>
      <label>Фактически использованная партия
        <select aria-label="Производственная партия" value={batchId} onChange={e=>{
          setBatchId(e.target.value);setNotice("");operationId.current=null;
        }}>
          <option value="">Выберите партию</option>
          {options.map(t=><option key={t.id} value={t.id}>{t.name_ru} · {t.service_date} · {t.meal_type} · приготовлено {t.prepared_quantity}</option>)}
        </select>
      </label>
      {!options.length&&<p>Нет подходящей партии: проверьте план приготовления и реальное списание продуктов.</p>}
      <label>Количество порций
        <input aria-label="Отпущено порций из партии" type="number" min="1" max={left} step="1"
          value={portions} onChange={e=>{setPortions(e.target.value);operationId.current=null;}}/>
      </label>
      <button type="button" className="shift-primary" disabled={busy||!valid} onClick={()=>void save()}>
        {busy?"Сохраняю…":"Подтвердить привязку партии"}
      </button>
    </>}
    {!!existing.length&&<div aria-label="Ранее подтверждённые партии">
      <h3>Уже записано</h3>
      {existing.map(a=><p key={a.id}>{a.menu_name} · {a.portions} порц. · {a.cost_kgs} сом · партия {a.production_target_id.slice(0,8)}</p>)}
    </div>}
    {notice&&<p role="status">{notice}</p>}
    {error&&<p role="alert">{error}</p>}
  </section>;
}
