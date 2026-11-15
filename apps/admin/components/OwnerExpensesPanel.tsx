"use client";

import {useCallback, useEffect, useState} from "react";

type Category="SUPPLIES"|"UTILITIES"|"PAYROLL"|"MAINTENANCE"|"RENT"|"MARKETING"|"OTHER";
type Method="CASH"|"BANK_TRANSFER"|"CARD"|"OTHER";
type Expense={id:string;expense_date:string;category:Category;title:string;
 amount_kgs:number;settled_kgs:number;outstanding_kgs:number;status:"POSTED"|"VOID";
 supplier_name:string|null;document_reference:string|null;notes:string|null};
type Ledger={items:Expense[];new_expense_id:string;new_settlement_id:string;
 scope:"OWNER_ONLY_PROPERTY_SCOPED";payment_created:false;
 totals:{posted_expenses_kgs:number;settled_against_period_expenses_kgs:number;
  outstanding_kgs:number;posted_count:number};
 truth:"POSTED_OBLIGATION_NOT_AUTOMATIC_PAYMENT_OR_PROFIT"};
const PATH="/core/api/v1/admin/finance/owner/expenses";
const CATEGORIES:Category[]=["SUPPLIES","UTILITIES","PAYROLL","MAINTENANCE","RENT","MARKETING","OTHER"];
const METHODS:Method[]=["CASH","BANK_TRANSFER","CARD","OTHER"];
const money=(value:number)=>new Intl.NumberFormat("ru-RU").format(value)+" сом";
const UUID=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
type Operation={path:string;payload:Record<string,unknown>};

async function exchange(path:string,method:"GET"|"POST"="GET",payload?:Record<string,unknown>){
 const response=await fetch(path,{method,cache:"no-store",headers:method==="POST"?
  {"Content-Type":"application/json"}:undefined,body:payload?JSON.stringify(payload):undefined});
 const data:unknown=await response.json().catch(()=>null);
 if(!response.ok){
  let detail="Сервер не подтвердил операцию";
  if(data&&typeof data==="object"&&"detail" in data){
   const error=(data as {detail:unknown}).detail;
   detail=typeof error==="string"?error:JSON.stringify(error);
  }
  throw new Error(detail);
 }
 return data;
}
function validLedger(value:unknown):value is Ledger {
 if(!value||typeof value!=="object")return false;
 const data=value as Partial<Ledger>;
 const items=data.items;
 if(data.scope!=="OWNER_ONLY_PROPERTY_SCOPED"||data.payment_created!==false||
   data.truth!=="POSTED_OBLIGATION_NOT_AUTOMATIC_PAYMENT_OR_PROFIT"||
   !UUID.test(String(data.new_expense_id))||!UUID.test(String(data.new_settlement_id))||
   !Array.isArray(items)||!data.totals)return false;
 return items.every(item=>UUID.test(item.id)&&Number.isSafeInteger(item.amount_kgs)&&
  Number.isSafeInteger(item.settled_kgs)&&Number.isSafeInteger(item.outstanding_kgs)&&
  item.amount_kgs>0&&item.outstanding_kgs>=0&&item.settled_kgs>=0&&
  item.amount_kgs===item.settled_kgs+item.outstanding_kgs);
}
export default function OwnerExpensesPanel({fromDate,toDate}:{fromDate:string;toDate:string}){
 const [ledger,setLedger]=useState<Ledger|null>(null);
 const [loading,setLoading]=useState(true);
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState<string|null>(null);
 const [unknown,setUnknown]=useState<Operation|null>(null);
 const [title,setTitle]=useState("");
 const [amount,setAmount]=useState("");
 const [category,setCategory]=useState<Category>("SUPPLIES");
 const [date,setDate]=useState(toDate);
 const [supplier,setSupplier]=useState("");
 const [document,setDocument]=useState("");
 const [settlementId,setSettlementId]=useState("");
 const [settleAmount,setSettleAmount]=useState("");
 const [method,setMethod]=useState<Method>("BANK_TRANSFER");
 const [paidOn,setPaidOn]=useState(toDate);
 const load=useCallback(async()=>{
   setLoading(true);setError(null);
   try{
     const raw=await exchange(PATH+"?"+new URLSearchParams({from_date:fromDate,to_date:toDate}));
     if(!validLedger(raw))throw new Error("Недостоверный ответ реестра расходов");
     setLedger(raw);
   }catch(e){setError(e instanceof Error?e.message:String(e));}
   finally{setLoading(false);}
 },[fromDate,toDate]);
 useEffect(()=>{void load();},[load]);
 async function execute(operation:Operation){
   if(busy)return;
   setBusy(true);setUnknown(operation);setError(null);
   try{
     const reply=await exchange(operation.path,"POST",operation.payload);
     if(!reply||typeof reply!=="object"||(reply as {payment_created?:unknown}).payment_created!==false)
       throw new Error("Некорректное подтверждение записи");
     await load();
     setUnknown(null);setTitle("");setAmount("");setSupplier("");setDocument("");setSettleAmount("");
   }catch(e){setError(e instanceof Error?e.message:String(e));}
   finally{setBusy(false);}
 }
 const submitExpense=()=>{
   const numeric=Number(amount);
   if(!ledger||!title.trim()||!Number.isSafeInteger(numeric)||numeric<=0||
      numeric>2_000_000_000||unknown){setError("Укажите корректное название и сумму");return;}
   const operation={path:PATH,payload:{id:ledger.new_expense_id,expense_date:date,
     category,title:title.trim(),amount_kgs:numeric,supplier_name:supplier.trim()||null,
     document_reference:document.trim()||null,notes:null}};
   if(window.confirm("Записать расход "+money(numeric)+"? Это ещё не оплата."))void execute(operation);
 };
 const submitSettlement=(expense:Expense)=>{
   const numeric=Number(settleAmount);
   if(!ledger||!Number.isSafeInteger(numeric)||numeric<=0||
     numeric>expense.outstanding_kgs||unknown){
     setError("Сумма оплаты должна быть положительной и не превышать остаток");return;}
   const operation={path:PATH+"/"+expense.id+"/settlements",payload:{
     id:ledger.new_settlement_id,amount_kgs:numeric,paid_on:paidOn,method,reference:null}};
   if(window.confirm("Вручную записать оплату "+money(numeric)+"? Перевод денег не выполняется."))
     void execute(operation);
 };
 return <section className="finance-section" aria-label="Хозяйственные расходы OWNER">
   <div className="section-head"><h2>Хозяйственные расходы OWNER</h2>
     <button className="btn" type="button" disabled={loading||busy} onClick={()=>void load()}>
       Обновить</button></div>
   <p className="finance-footnote">Возникновение расхода, его ручная оплата и полученные платежи гостей
     учитываются раздельно. Это не расчёт бухгалтерской прибыли или автоматический перевод денег.</p>
   {error&&<p role="alert" className="finance-footnote">{error}</p>}
   {loading&&<p>Загружаю реальные данные…</p>}
   {ledger&&<>
     <div className="finance-state-grid">
       <div><span>Начислено за период</span><strong>{money(ledger.totals.posted_expenses_kgs)}</strong></div>
       <div><span>Оплачено по этим расходам</span><strong>{money(ledger.totals.settled_against_period_expenses_kgs)}</strong></div>
       <div><span>Остаток к оплате</span><strong>{money(ledger.totals.outstanding_kgs)}</strong></div>
     </div>
     {unknown?<div className="finance-notice">
       <strong>Результат записи неизвестен — не создавайте новую операцию.</strong>
       <button type="button" className="btn" disabled={busy}
         onClick={()=>void execute(unknown)}>Повторить с тем же ID</button>
     </div>:<>
       <div className="finance-filters" aria-label="Добавить расход">
         <label><span>Название</span><input value={title} maxLength={150}
           onChange={e=>setTitle(e.target.value)}/></label>
         <label><span>Сумма, сом</span><input type="number" min="1" step="1"
           value={amount} onChange={e=>setAmount(e.target.value)}/></label>
         <label><span>Дата</span><input type="date" value={date}
           onChange={e=>setDate(e.target.value)}/></label>
         <label><span>Категория</span><select value={category}
           onChange={e=>setCategory(e.target.value as Category)}>
           {CATEGORIES.map(x=><option key={x} value={x}>{x}</option>)}
         </select></label>
         <label><span>Поставщик</span><input value={supplier} maxLength={150}
           onChange={e=>setSupplier(e.target.value)}/></label>
         <label><span>Документ</span><input value={document} maxLength={150}
           onChange={e=>setDocument(e.target.value)}/></label>
         <button type="button" className="btn" disabled={busy}
           onClick={submitExpense}>Записать расход</button>
       </div>
     </>}
     <div className="transaction-table-wrap">
       <table className="transaction-table">
         <thead><tr><th>Дата</th><th>Категория / расход</th><th>Сумма</th>
           <th>Оплачено</th><th>Осталось</th><th>Ручная оплата</th></tr></thead>
         <tbody>{ledger.items.length===0?<tr><td colSpan={6}>За период расходов нет.</td></tr>:
          ledger.items.map(item=><tr key={item.id}>
           <td>{item.expense_date}</td>
           <td>{item.category}<small>{item.title}</small>
             <small>{item.supplier_name||"—"}</small></td>
           <td>{money(item.amount_kgs)}</td><td>{money(item.settled_kgs)}</td>
           <td>{money(item.outstanding_kgs)}</td>
           <td>{item.status==="POSTED"&&item.outstanding_kgs>0&&!unknown?<>
             <button type="button" className="btn"
               onClick={()=>setSettlementId(settlementId===item.id?"":item.id)}>
               Записать вручную</button>
             {settlementId===item.id&&<div>
               <input aria-label="Сумма ручной оплаты" type="number" min="1"
                 max={item.outstanding_kgs} step="1" value={settleAmount}
                 onChange={e=>setSettleAmount(e.target.value)}/>
               <input aria-label="Дата ручной оплаты" type="date" value={paidOn}
                 onChange={e=>setPaidOn(e.target.value)}/>
               <select aria-label="Способ ручной оплаты" value={method}
                 onChange={e=>setMethod(e.target.value as Method)}>
                 {METHODS.map(x=><option value={x} key={x}>{x}</option>)}
               </select>
               <button className="btn" type="button" disabled={busy}
                 onClick={()=>submitSettlement(item)}>Сохранить</button>
             </div>}
           </>:"—"}</td>
          </tr>)}</tbody>
       </table>
     </div>
   </>}
 </section>;
}
