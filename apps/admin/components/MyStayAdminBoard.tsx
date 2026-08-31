"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type Reservation={id:string;bookingNumber:string;status:string;checkIn:string;checkOut:string;firstName?:string|null;phone?:string|null;room_code?:string|null;room_type_name?:string|null};
type Issued={reservation_id:string;booking_number:string;pin:string;activation_token:string;guest_url:string;expires_at:string};
type Meal="BREAKFAST"|"LUNCH"|"DINNER";
function d(v:string){return String(v).slice(0,10)}

export default function MyStayAdminBoard(){
  const [reservations,setReservations]=useState<Reservation[]>([]);
  const [query,setQuery]=useState("");
  const [selected,setSelected]=useState<Reservation|null>(null);
  const [issued,setIssued]=useState<Issued|null>(null);
  const [error,setError]=useState("");
  const [notice,setNotice]=useState("");
  const [busy,setBusy]=useState(false);
  const [mealDate,setMealDate]=useState(new Date().toISOString().slice(0,10));
  const [meal,setMeal]=useState<Meal>("BREAKFAST");
  const [included,setIncluded]=useState(false);

  const load=useCallback(async()=>{
    setBusy(true);setError("");
    try{
      const r=await fetch("/core/api/v1/admin/reception/reservations?limit=500",{cache:"no-store"});
      if(!r.ok)throw new Error("Нет доступа к бронированиям");
      const b=await r.json();
      setReservations((b.items||[]).filter((x:Reservation)=>["CHECKED_IN","GUARANTEED"].includes(x.status)));
    }catch(e){setError(e instanceof Error?e.message:"Ошибка")}finally{setBusy(false)}
  },[]);
  useEffect(()=>{void load()},[load]);

  const list=useMemo(()=>{
    const q=query.trim().toLowerCase();if(!q)return reservations;
    return reservations.filter(r=>[r.bookingNumber,r.firstName,r.phone,r.room_code].some(v=>String(v||"").toLowerCase().includes(q)));
  },[reservations,query]);

  async function issue(){
    if(!selected)return;setBusy(true);setError("");setNotice("");
    try{
      const r=await fetch(`/core/api/v1/admin/my-stay/reservations/${selected.id}/issue`,{method:"POST"});
      const b=await r.json().catch(()=>({}));
      if(!r.ok)throw new Error(typeof b.detail==="string"?b.detail:"Не удалось выпустить доступ");
      setIssued(b);setNotice("Новый QR и PIN выпущены. Предыдущие гостевые сессии отозваны.");
    }catch(e){setError(e instanceof Error?e.message:"Ошибка")}finally{setBusy(false)}
  }

  async function revoke(){
    if(!selected)return;setBusy(true);setError("");setNotice("");
    try{
      const r=await fetch(`/core/api/v1/admin/my-stay/reservations/${selected.id}/revoke`,{method:"POST"});
      if(!r.ok)throw new Error();setIssued(null);setNotice("Доступ гостя отозван.");
    }catch{setError("Не удалось отозвать доступ")}finally{setBusy(false)}
  }

  async function saveMeal(e:FormEvent){
    e.preventDefault();if(!selected)return;setBusy(true);setError("");setNotice("");
    try{
      const r=await fetch(`/core/api/v1/admin/my-stay/reservations/${selected.id}/meal-plan`,{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({service_date:mealDate,meal_type:meal,included})});
      if(!r.ok)throw new Error();setNotice("План питания сохранён.");
    }catch{setError("Не удалось сохранить питание")}finally{setBusy(false)}
  }

  const qrSrc=issued?`/core/api/v1/admin/my-stay/qr.svg?value=${encodeURIComponent(issued.guest_url)}`:"";

  return <main className="myadmin-shell">
    <header><div><p>Три Короны · Resort OS</p><h1>MY STAY / QR гостя</h1><span>Доступ гостя, питание и цифровой сервис проживания</span></div></header>
    {error&&<div className="myadmin-error">{error}</div>}
    {notice&&<div className="myadmin-error" style={{borderColor:"rgba(16,120,70,.35)"}}>{notice}</div>}
    <div className="myadmin-grid">
      <section className="myadmin-panel"><h2>Активные и будущие проживания</h2><input className="myadmin-search" placeholder="Бронь, имя, телефон, номер" value={query} onChange={e=>setQuery(e.target.value)}/><div className="myadmin-list">{list.map(r=><button key={r.id} className={selected?.id===r.id?"active":""} onClick={()=>{setSelected(r);setIssued(null);setNotice("")}}><div><strong>{r.room_code?`№ ${r.room_code}`:"Без номера"} · {r.firstName||r.bookingNumber}</strong><span>{r.bookingNumber} · {r.status}</span></div><small>{d(r.checkIn)} → {d(r.checkOut)}</small></button>)}</div></section>
      <section className="myadmin-panel">{!selected?<div className="myadmin-empty">Выберите проживание слева.</div>:<><p className="myadmin-eyebrow">{selected.bookingNumber}</p><h2>{selected.firstName||"Гость"} · № {selected.room_code||"—"}</h2><div className="myadmin-actions"><button className="primary" onClick={issue} disabled={busy}>Выпустить / перевыпустить QR</button><button onClick={revoke} disabled={busy}>Отозвать доступ</button></div>{issued&&<div className="myadmin-credential"><div style={{display:"grid",gridTemplateColumns:"minmax(0,1fr) 180px",gap:16,alignItems:"center"}}><div><div><span>PIN гостя</span><strong>{issued.pin}</strong></div><label>Ссылка MY STAY<input readOnly value={issued.guest_url}/></label><small>QR содержит одноразовый activation token во fragment (#). После успешной активации token уничтожается. Повторный выпуск автоматически отзывает старые гостевые сессии.</small></div><img src={qrSrc} alt={`QR MY STAY ${issued.booking_number}`} width={180} height={180} style={{width:"180px",height:"180px",background:"white",borderRadius:12,padding:6}}/></div></div>}<form className="myadmin-meal" onSubmit={saveMeal}><h3>Питание проживания</h3><input type="date" value={mealDate} onChange={e=>setMealDate(e.target.value)}/><select value={meal} onChange={e=>setMeal(e.target.value as Meal)}><option value="BREAKFAST">Завтрак</option><option value="LUNCH">Обед</option><option value="DINNER">Ужин</option></select><label><input type="checkbox" checked={included} onChange={e=>setIncluded(e.target.checked)}/> Включено в проживание на эту дату</label><button className="primary" disabled={busy}>Сохранить питание</button></form></>}</section>
    </div>
  </main>;
}
