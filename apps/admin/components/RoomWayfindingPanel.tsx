"use client";

import { FormEvent, useEffect, useState } from "react";

type Wayfinding = { latitude: number | null; longitude: number | null; parking_label: string; directions: string; walkthrough_video_url: string; map_url: string | null };
const initial: Wayfinding = {latitude:null,longitude:null,parking_label:"",directions:"",walkthrough_video_url:"",map_url:null};
export default function RoomWayfindingPanel({roomId}: {roomId:string}) {
  const [form,setForm]=useState<Wayfinding>(initial);
  const [loading,setLoading]=useState(true);
  const [busy,setBusy]=useState(false);
  const [notice,setNotice]=useState("");
  useEffect(()=>{
    let live=true;
    setLoading(true);
    fetch(`/core/api/v1/admin/rooms/${roomId}/wayfinding`,{cache:"no-store"})
      .then(async r=>{if(!r.ok)throw Error("Не удалось загрузить навигацию");return r.json()})
      .then(body=>{if(live)setForm({...initial,...body.wayfinding})})
      .catch(e=>{if(live)setNotice(e.message)})
      .finally(()=>{if(live)setLoading(false)});
    return()=>{live=false};
  },[roomId]);
  async function save(e:FormEvent) {
    e.preventDefault();
    setBusy(true);setNotice("");
    try {
      const res=await fetch(`/core/api/v1/admin/rooms/${roomId}/wayfinding`,{
        method:"PUT",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({latitude:form.latitude,longitude:form.longitude,parking_label:form.parking_label,
          directions:form.directions,walkthrough_video_url:form.walkthrough_video_url})
      });
      const body=await res.json();
      if(!res.ok)throw Error(typeof body.detail==="string"?body.detail:"Не удалось сохранить");
      setForm(body.wayfinding);setNotice("Маршрут сохранён в карточке номера.");
    } catch(e) {setNotice(e instanceof Error?e.message:"Ошибка сохранения")}finally{setBusy(false)}
  }
  return <section aria-label="Навигация к номеру" style={{padding:"18px 0"}}>
    <h3>Маршрут к номеру / коттеджу</h3>
    <p>Дополнительно для большой территории: GPS, парковка и видео прохода. PIN замка и пароли сюда не вводите.</p>
    {loading?<p>Загрузка маршрута…</p>:<form onSubmit={save} style={{display:"grid",gap:10}}>
      <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(150px,1fr))",gap:10}}>
        <label>Широта (GPS)<input aria-label="Широта" type="number" min="-90" max="90" step="any" value={form.latitude??""} onChange={e=>setForm(v=>({...v,latitude:e.target.value===""?null:Number(e.target.value)}))}/></label>
        <label>Долгота (GPS)<input aria-label="Долгота" type="number" min="-180" max="180" step="any" value={form.longitude??""} onChange={e=>setForm(v=>({...v,longitude:e.target.value===""?null:Number(e.target.value)}))}/></label>
      </div>
      <label>Парковочное место<input maxLength={100} value={form.parking_label} onChange={e=>setForm(v=>({...v,parking_label:e.target.value}))} placeholder="Например, P-14"/></label>
      <label>Как пройти<textarea rows={3} maxLength={1200} value={form.directions} onChange={e=>setForm(v=>({...v,directions:e.target.value}))} placeholder="От ворот направо, мимо корпуса 2…"/></label>
      <label>HTTPS-ссылка на видео прохода<input type="url" maxLength={500} value={form.walkthrough_video_url} onChange={e=>setForm(v=>({...v,walkthrough_video_url:e.target.value}))} placeholder="https://…"/></label>
      <div style={{display:"flex",gap:12,flexWrap:"wrap",alignItems:"center"}}>
        <button type="submit" className="btn primary" disabled={busy}>{busy?"Сохранение…":"Сохранить маршрут"}</button>
        {form.map_url&&<a href={form.map_url} rel="noopener noreferrer" target="_blank">Проверить точку на карте ↗</a>}
      </div>
      {notice&&<p role="status">{notice}</p>}
    </form>}
  </section>;
}
