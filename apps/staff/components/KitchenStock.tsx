"use client";
import { useCallback, useEffect, useState } from "react";
import styles from "./ChefProduction.module.css";

type Item = { id:string; name:string; unit:"KG"|"L"|"PCS"; balance:string; cost_per_unit_kgs:string; is_sample:boolean };
type Stock = { items:Item[]; production_cost_kgs:string; inventory_deducted_only_on_explicit_consume:boolean };
type Target = { id:string; name_ru:string; menu_item_id:string; service_date:string; meal_type:"BREAKFAST"|"LUNCH"|"DINNER"|"OTHER"; planned_quantity:number; prepared_quantity:number; notes?:string|null };

async function stockApi(path:string, init?:RequestInit):Promise<Record<string,unknown>> {
  const response = await fetch("/core/api/v1/kitchen/stock" + path, {
    cache:"no-store",...init,
  });
  const body:unknown = await response.json().catch(()=>null);
  const payload = body && typeof body === "object" && !Array.isArray(body) ? body as Record<string,unknown> : {};
  if (!response.ok) throw new Error(typeof payload.detail === "string" ? payload.detail : "Операция склада недоступна ("+response.status+")");
  return payload;
}

export default function KitchenStock({fromDate,throughDate,userRole}:{fromDate:string;throughDate:string;userRole:string}) {
  const canReceive = userRole === "OWNER" || userRole === "MANAGER";
  const canConsume = userRole === "MANAGER" || userRole === "COOK";
  const [data,setData] = useState<Stock|null>(null);
  const [targets,setTargets] = useState<Target[]>([]);
  const [preparedDraft,setPreparedDraft] = useState<Record<string,string>>({});
  const [error,setError] = useState("");
  const [notice,setNotice] = useState("");
  const [busy,setBusy] = useState(false);
  const [name,setName] = useState("");
  const [unit,setUnit] = useState<Item["unit"]>("KG");
  const [cost,setCost] = useState("0");
  const [sample,setSample] = useState(true);
  const [selected,setSelected] = useState("");
  const [quantity,setQuantity] = useState("1");
  const load = useCallback(async () => {
    try {
      const [stockResult,planResponse] = await Promise.all([
        stockApi(""),fetch("/core/api/v1/kitchen/production-targets?from_date="+encodeURIComponent(fromDate)+"&through_date="+encodeURIComponent(throughDate),{cache:"no-store"}),
      ]);
      if(!planResponse.ok) throw new Error("План кухни недоступен ("+planResponse.status+")");
      const plan:unknown = await planResponse.json();
      if(!Array.isArray(stockResult.items) || !plan || typeof plan!=="object" || !Array.isArray((plan as {items?:unknown}).items))
        throw new Error("Неверный формат данных склада");
      setData(stockResult as unknown as Stock);
      setTargets((plan as {items:Target[]}).items);
      setPreparedDraft(Object.fromEntries((plan as {items:Target[]}).items.map(item=>[item.id,String(item.prepared_quantity)])));
      setError("");
    } catch(e) {setError(e instanceof Error?e.message:"Не удалось загрузить склад");}
  },[fromDate,throughDate]);
  useEffect(()=>{void load();const timer=window.setInterval(()=>void load(),30000);return ()=>window.clearInterval(timer);},[load]);
  const mutate = async (path:string,body:object) => {
    if(busy)return;
    setBusy(true);setError("");setNotice("");
    try {
      const result=await stockApi(path,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
      setNotice(path==="/consume" ? (result.already_processed ? "Порции уже списаны. Повторного расхода нет." : "Списано порций: "+result.consumed_portions+" · себестоимость "+result.cost_kgs+" сом") : "Складская операция сохранена");
      await load();
    }catch(e){setError(e instanceof Error?e.message:"Не удалось сохранить операцию");}
    finally{setBusy(false);}
  };
  const savePrepared = async (target:Target) => {
    const prepared=Number(preparedDraft[target.id]);
    if (!Number.isSafeInteger(prepared) || prepared<0 || prepared>target.planned_quantity) {
      setError("Укажите количество от 0 до плана без дробных значений");return;
    }
    if(busy)return;
    setBusy(true);setError("");setNotice("");
    try {
      const response=await fetch("/core/api/v1/kitchen/production-targets",{
        method:"PUT",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({service_date:target.service_date,meal_type:target.meal_type,menu_item_id:target.menu_item_id,
          planned_quantity:target.planned_quantity,prepared_quantity:prepared,notes:target.notes??null}),
      });
      if(!response.ok)throw new Error("Не удалось сохранить количество приготовленных порций ("+response.status+")");
      setNotice("Количество приготовленных порций записано в MARINA SMART. Для фактического расхода выполните списание.");
      await load();
    }catch(e){setError(e instanceof Error?e.message:"Ошибка сохранения порций");}
    finally{setBusy(false);}
  };
  return <section className={styles.day} data-testid="kitchen-stock">
    <div className={styles.head}><div><h2>Склад · продукты и списания</h2><small>Отдельно от платежей. Учебные остатки нельзя смешивать с реальными.</small></div><button onClick={()=>void load()}>Обновить склад</button></div>
    {error?<p role="alert" className={styles.error}>{error}</p>:null}
    {notice?<p role="status" className={styles.notice}>{notice}</p>:null}
    {data?<>
      {data.items.length ? data.items.map(item=><p key={item.id}><strong>{item.name}</strong> · {item.balance} {item.unit} · {item.cost_per_unit_kgs} сом/{item.unit}{item.is_sample?" · ТЕСТ":""}</p>) : <p>Продукты ещё не добавлены.</p>}
      <p className={styles.notice}>Учётная себестоимость списаний: {data.production_cost_kgs} сом. Это не полученная оплата и не прибыль.</p>
      {canReceive?<div className={styles.controls}>
        <h3>Добавить продукт</h3>
        <label>Наименование<input aria-label="Наименование продукта" value={name} maxLength={120} onChange={e=>setName(e.target.value)}/></label>
        <label>Единица<select aria-label="Единица продукта" value={unit} onChange={e=>setUnit(e.target.value as Item["unit"])}><option value="KG">кг</option><option value="L">л</option><option value="PCS">шт</option></select></label>
        <label>Себестоимость за единицу, сом<input aria-label="Себестоимость за единицу" type="number" min="0" step="0.0001" value={cost} onChange={e=>setCost(e.target.value)}/></label>
        <label><input type="checkbox" checked={sample} onChange={e=>setSample(e.target.checked)}/>Учебный продукт</label>
        <button disabled={busy||!name.trim()||!cost||Number(cost)<0} onClick={()=>void mutate("/items",{name,unit,cost_per_unit_kgs:cost,is_sample:sample})}>Добавить продукт</button>
        <h3>Приход продуктов</h3>
        <label>Продукт<select aria-label="Продукт прихода" value={selected} onChange={e=>setSelected(e.target.value)}><option value="">Выберите продукт</option>{data.items.map(item=><option key={item.id} value={item.id}>{item.name} · {item.unit}{item.is_sample?" (тест)":""}</option>)}</select></label>
        <label>Количество<input aria-label="Количество прихода" type="number" min="0.000001" step="0.000001" value={quantity} onChange={e=>setQuantity(e.target.value)}/></label>
        <button disabled={busy||!selected||Number(quantity)<=0} onClick={()=>void mutate("/receipts",{stock_item_id:selected,quantity,notes:"Приход через кабинет склада"})}>Записать приход</button>
      </div>:null}
      {canConsume?<div className={styles.controls}><h3>Списание по приготовленным порциям</h3>
        {targets.map(t=><div key={t.id}>
          <p><strong>{t.name_ru}</strong> · {t.service_date} · план {t.planned_quantity} порц.</p>
          <label>Приготовлено<input aria-label={"Приготовлено: "+t.name_ru} type="number" min="0" max={t.planned_quantity} step="1"
            value={preparedDraft[t.id]??String(t.prepared_quantity)} onChange={e=>setPreparedDraft(prev=>({...prev,[t.id]:e.target.value}))}/></label>
          <button disabled={busy} onClick={()=>void savePrepared(t)}>Сохранить количество</button>
          <button disabled={busy||t.prepared_quantity===0} onClick={()=>void mutate("/consume",{production_target_id:t.id})}>Списать продукты</button>
        </div>)}
        {!targets.length?<p>Нет производственных заданий для выбранных дат.</p>:null}
        <p>Списание допускается только по утверждённой рецептуре и при достаточном остатке. Повторный запрос не списывает продукты дважды.</p>
      </div>:null}
    </>:null}
  </section>;
}
