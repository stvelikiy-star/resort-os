"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type Lang = "ru" | "en" | "ky";
type Guest = { guest_name: string; booking_number: string; check_in: string; check_out: string; room_code?: string | null; room_type?: string | null; currency: string };
type MenuItem = { id: string; name: string; description?: string | null; priceKgs: number; availableQty?: number | null; includedInMealPlan: boolean };
type OrderSummary = { dining_orders: any[]; service_requests: any[]; charges: any[] };

const T = {
  ru: { title:"MY STAY", hello:"Добро пожаловать", pin:"PIN гостя", activate:"Открыть мой отдых", bad:"Не удалось войти. Проверьте PIN на ресепшене.", dining:"Питание", clean:"Уборка", repair:"Ремонт", transfer:"Трансфер", tours:"Туры", orders:"Мои заказы", breakfast:"Завтрак", lunch:"Обед", dinner:"Ужин", menu:"Меню", included:"Включено в питание", order:"Заказать", empty:"Меню ещё не опубликовано", request:"Отправить заявку", description:"Комментарий", sent:"Заявка отправлена", room:"Номер", checkout:"Выезд", total:"Итого", folio:"Начислится на номер", noOrders:"Пока нет заказов", logout:"Выйти", back:"Назад" },
  en: { title:"MY STAY", hello:"Welcome", pin:"Guest PIN", activate:"Open my stay", bad:"Could not sign in. Check your PIN at reception.", dining:"Dining", clean:"Housekeeping", repair:"Maintenance", transfer:"Transfer", tours:"Tours", orders:"My orders", breakfast:"Breakfast", lunch:"Lunch", dinner:"Dinner", menu:"Menu", included:"Included in meal plan", order:"Place order", empty:"Menu has not been published yet", request:"Send request", description:"Comment", sent:"Request sent", room:"Room", checkout:"Checkout", total:"Total", folio:"Will be charged to the room", noOrders:"No orders yet", logout:"Logout", back:"Back" },
  ky: { title:"MY STAY", hello:"Кош келиңиз", pin:"Конок PIN", activate:"Менин эс алуумду ачуу", bad:"Кирүү мүмкүн болгон жок. PIN-кодду ресепшнден текшериңиз.", dining:"Тамактануу", clean:"Тазалоо", repair:"Оңдоо", transfer:"Трансфер", tours:"Турлар", orders:"Менин заказдарым", breakfast:"Эртең мененки", lunch:"Түшкү", dinner:"Кечки", menu:"Меню", included:"Тамактанууга кирет", order:"Заказ берүү", empty:"Меню азырынча жарыяланган жок", request:"Өтүнмө жөнөтүү", description:"Комментарий", sent:"Өтүнмө жөнөтүлдү", room:"Бөлмө", checkout:"Чыгуу", total:"Жалпы", folio:"Бөлмөнүн эсебине кошулат", noOrders:"Азырынча заказ жок", logout:"Чыгуу", back:"Артка" }
} as const;

function money(value:number){ return new Intl.NumberFormat("ru-RU").format(value) + " сом"; }
function today(){ return new Date().toISOString().slice(0,10); }

export default function MyStayClient(){
  const [lang,setLang]=useState<Lang>("ru"); const tr=T[lang];
  const [guest,setGuest]=useState<Guest|null>(null); const [checking,setChecking]=useState(true);
  const [activation,setActivation]=useState(""); const [pin,setPin]=useState(""); const [authError,setAuthError]=useState("");
  const [view,setView]=useState<"HOME"|"DINING"|"REQUEST"|"ORDERS">("HOME");
  const [requestKind,setRequestKind]=useState<"HOUSEKEEPING"|"MAINTENANCE"|"TRANSFER"|"EXCURSIONS">("HOUSEKEEPING");
  const [requestText,setRequestText]=useState(""); const [notice,setNotice]=useState("");
  const [meal,setMeal]=useState<"BREAKFAST"|"LUNCH"|"DINNER">("LUNCH"); const [serviceDate,setServiceDate]=useState(today());
  const [menu,setMenu]=useState<MenuItem[]>([]); const [mealIncluded,setMealIncluded]=useState(false); const [cart,setCart]=useState<Record<string,number>>({});
  const [orders,setOrders]=useState<OrderSummary|null>(null); const [busy,setBusy]=useState(false);

  const loadMe=useCallback(async()=>{
    try{ const r=await fetch("/core/api/v1/guest/me",{cache:"no-store"}); if(!r.ok){setGuest(null);return;} setGuest(await r.json()); }
    finally{setChecking(false);}
  },[]);

  useEffect(()=>{
    const fragment=new URLSearchParams(window.location.hash.replace(/^#/,""));
    const token=fragment.get("activate")||""; if(token) setActivation(token);
    void loadMe();
  },[loadMe]);

  async function activate(e:FormEvent){ e.preventDefault(); setBusy(true);setAuthError("");
    try{ const r=await fetch("/core/api/v1/guest/activate",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({activation_token:activation,pin})}); if(!r.ok) throw new Error(); history.replaceState(null,"",window.location.pathname); setActivation("");setPin(""); await loadMe(); }
    catch{setAuthError(tr.bad);} finally{setBusy(false);} }

  async function logout(){ await fetch("/core/api/v1/guest/logout",{method:"POST"}).catch(()=>undefined); setGuest(null);setView("HOME"); }

  const loadMenu=useCallback(async()=>{ if(!guest)return; setBusy(true); try{const q=new URLSearchParams({service_date:serviceDate,meal_type:meal}); const r=await fetch(`/core/api/v1/guest/menu?${q}`,{cache:"no-store"}); if(!r.ok)throw new Error(); const b=await r.json(); setMenu(b.items||[]);setMealIncluded(Boolean(b.meal_plan_included));setCart({});}catch{setMenu([]);}finally{setBusy(false);}},[guest,serviceDate,meal]);
  useEffect(()=>{if(view==="DINING")void loadMenu();},[view,loadMenu]);

  const total=useMemo(()=>menu.reduce((sum,item)=>{const q=cart[item.id]||0;const unit=mealIncluded&&item.includedInMealPlan?0:item.priceKgs;return sum+q*unit;},0),[menu,cart,mealIncluded]);

  async function placeOrder(){ const items=Object.entries(cart).filter(([,q])=>q>0).map(([menu_item_id,quantity])=>({menu_item_id,quantity})); if(!items.length)return; setBusy(true);setNotice(""); try{const r=await fetch("/core/api/v1/guest/dining/orders",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({service_date:serviceDate,meal_type:meal,items})});const b=await r.json().catch(()=>({}));if(!r.ok)throw new Error(typeof b.detail==="string"?b.detail:"Order failed");setCart({});setNotice(`${tr.sent} · ${money(b.total_kgs||0)}`);}catch(e){setNotice(e instanceof Error?e.message:"Ошибка");}finally{setBusy(false);}}

  function openRequest(kind:typeof requestKind){setRequestKind(kind);setRequestText("");setNotice("");setView("REQUEST");}
  async function sendRequest(e:FormEvent){e.preventDefault();setBusy(true);setNotice("");try{const r=await fetch("/core/api/v1/guest/requests",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({kind:requestKind,description:requestText,priority:requestKind==="MAINTENANCE"?"HIGH":"NORMAL"})});const b=await r.json().catch(()=>({}));if(!r.ok)throw new Error(b.detail?.code||b.detail||"Request failed");setRequestText("");setNotice(tr.sent);}catch(e){setNotice(e instanceof Error?e.message:"Ошибка");}finally{setBusy(false);}}
  async function loadOrders(){setView("ORDERS");setBusy(true);try{const r=await fetch("/core/api/v1/guest/orders",{cache:"no-store"});setOrders(r.ok?await r.json():null);}finally{setBusy(false);}}

  if(checking) return <main className="mystay-center"><div className="mystay-card"><div className="mystay-mark">III</div><h1>Три Короны</h1><p>MY STAY</p></div></main>;
  if(!guest) return <main className="mystay-center"><form className="mystay-card mystay-login" onSubmit={activate}><div className="mystay-mark">III</div><p className="mystay-eyebrow">Три Короны · Resort & SPA</p><h1>{tr.title}</h1><p>{activation?tr.hello:"Отсканируйте QR, выданный при заселении."}</p><div className="mystay-lang"><button type="button" onClick={()=>setLang("ru")}>RU</button><button type="button" onClick={()=>setLang("en")}>EN</button><button type="button" onClick={()=>setLang("ky")}>KG</button></div>{activation&&<><label><span>{tr.pin}</span><input inputMode="numeric" pattern="[0-9]{6}" maxLength={6} value={pin} onChange={e=>setPin(e.target.value.replace(/\D/g,"").slice(0,6))} required autoFocus /></label>{authError&&<div className="mystay-error">{authError}</div>}<button className="mystay-primary" disabled={busy||pin.length!==6}>{tr.activate}</button></>}</form></main>;

  return <main className="mystay-shell">
    <header className="mystay-head"><div><p className="mystay-eyebrow">Три Короны · {tr.title}</p><h1>{tr.hello}, {guest.guest_name}</h1><p>{tr.room}: <b>{guest.room_code||"—"}</b> · {tr.checkout}: {String(guest.check_out).slice(0,10)}</p></div><div className="mystay-head-actions"><div className="mystay-lang"><button onClick={()=>setLang("ru")}>RU</button><button onClick={()=>setLang("en")}>EN</button><button onClick={()=>setLang("ky")}>KG</button></div><button className="mystay-link" onClick={logout}>{tr.logout}</button></div></header>
    {view!=="HOME"&&<button className="mystay-back" onClick={()=>{setView("HOME");setNotice("");}}>← {tr.back}</button>}
    {notice&&<div className="mystay-notice">{notice}</div>}

    {view==="HOME"&&<section className="mystay-grid">
      <button className="mystay-tile featured" onClick={()=>setView("DINING")}><span>🍽</span><strong>{tr.dining}</strong><small>Завтрак · Обед · Ужин</small></button>
      <button className="mystay-tile" onClick={()=>openRequest("HOUSEKEEPING")}><span>🧹</span><strong>{tr.clean}</strong><small>Удобное время и комментарий</small></button>
      <button className="mystay-tile" onClick={()=>openRequest("MAINTENANCE")}><span>🔧</span><strong>{tr.repair}</strong><small>Сообщить о неисправности</small></button>
      <button className="mystay-tile" onClick={()=>openRequest("TRANSFER")}><span>🚐</span><strong>{tr.transfer}</strong><small>Манас · Тамчы · Бишкек</small></button>
      <button className="mystay-tile" onClick={()=>openRequest("EXCURSIONS")}><span>🗺</span><strong>{tr.tours}</strong><small>Подобрать поездку</small></button>
      <button className="mystay-tile" onClick={loadOrders}><span>🧾</span><strong>{tr.orders}</strong><small>Статусы и начисления</small></button>
    </section>}

    {view==="DINING"&&<section className="mystay-panel"><div className="mystay-panel-head"><div><p className="mystay-eyebrow">{tr.dining}</p><h2>{tr.menu}</h2></div><input type="date" value={serviceDate} onChange={e=>setServiceDate(e.target.value)} /></div><div className="mystay-tabs">{(["BREAKFAST","LUNCH","DINNER"] as const).map(m=><button key={m} className={meal===m?"active":""} onClick={()=>setMeal(m)}>{m==="BREAKFAST"?tr.breakfast:m==="LUNCH"?tr.lunch:tr.dinner}</button>)}</div>{mealIncluded&&<div className="mystay-included">✓ {tr.included}</div>}<div className="mystay-menu">{!busy&&menu.length===0&&<div className="mystay-empty">{tr.empty}</div>}{menu.map(item=>{const free=mealIncluded&&item.includedInMealPlan;const q=cart[item.id]||0;return <article key={item.id} className="mystay-menu-item"><div><h3>{item.name}</h3>{item.description&&<p>{item.description}</p>}<strong>{free?tr.included:money(item.priceKgs)}</strong>{item.availableQty!=null&&<small>Осталось: {item.availableQty}</small>}</div><div className="mystay-stepper"><button onClick={()=>setCart(c=>({...c,[item.id]:Math.max(0,q-1)}))}>−</button><b>{q}</b><button onClick={()=>setCart(c=>({...c,[item.id]:q+1}))}>+</button></div></article>})}</div>{Object.values(cart).some(q=>q>0)&&<div className="mystay-cart"><div><small>{tr.total}</small><strong>{money(total)}</strong><span>{total>0?tr.folio:tr.included}</span></div><button className="mystay-primary" onClick={placeOrder} disabled={busy}>{tr.order}</button></div>}</section>}

    {view==="REQUEST"&&<form className="mystay-panel mystay-request" onSubmit={sendRequest}><p className="mystay-eyebrow">{requestKind}</p><h2>{requestKind==="HOUSEKEEPING"?tr.clean:requestKind==="MAINTENANCE"?tr.repair:requestKind==="TRANSFER"?tr.transfer:tr.tours}</h2><label><span>{tr.description}</span><textarea value={requestText} onChange={e=>setRequestText(e.target.value)} minLength={2} maxLength={2000} placeholder={requestKind==="HOUSEKEEPING"?"Например: пожалуйста, после 15:00":"Напишите детали запроса"} required /></label><button className="mystay-primary" disabled={busy}>{tr.request}</button></form>}

    {view==="ORDERS"&&<section className="mystay-panel"><p className="mystay-eyebrow">{tr.orders}</p><h2>{guest.booking_number}</h2>{busy&&<div className="mystay-empty">…</div>}{orders&&!orders.dining_orders.length&&!orders.service_requests.length&&<div className="mystay-empty">{tr.noOrders}</div>}<div className="mystay-history">{orders?.dining_orders.map(o=><article key={o.id}><strong>🍽 {o.mealType} · {o.serviceDate}</strong><span>{o.status} · {money(o.totalKgs)}</span></article>)}{orders?.service_requests.map(o=><article key={o.id}><strong>✓ {o.title}</strong><span>{o.status}</span></article>)}{orders?.charges.map(c=><article key={c.id}><strong>₸ {c.description}</strong><span>{money(c.amountKgs)} · {c.status}</span></article>)}</div></section>}
  </main>;
}
