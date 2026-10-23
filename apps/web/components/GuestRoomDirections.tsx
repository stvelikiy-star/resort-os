"use client";
import { useEffect, useState } from "react";
import { useMarinaGuestLocale } from "../lib/marinaGuestLocale";
type Route={latitude:number|null;longitude:number|null;parking_label:string;directions:string;walkthrough_video_url:string;map_url:string|null};
const lang={
 ru:{title:"Как найти ваш номер",parking:"Парковка",directions:"Как пройти",map:"Открыть карту",video:"Видео маршрута",noRoute:"Маршрут пока не добавлен гостиницей."},
 kg:{title:"Бөлмөңүздү кантип табасыз",parking:"Унаа токтотуучу жай",directions:"Кантип баруу керек",map:"Картаны ачуу",video:"Жол видеосу",noRoute:"Мейманкана маршрутту азырынча кошо элек."},
 kz:{title:"Бөлмеңізді қалай табуға болады",parking:"Тұрақ",directions:"Қалай баруға болады",map:"Картаны ашу",video:"Бағыт видеосы",noRoute:"Қонақүй маршрутты әлі қоспаған."},
 en:{title:"Find your room",parking:"Parking",directions:"Directions",map:"Open map",video:"Walkthrough video",noRoute:"The hotel has not added directions yet."},
} as const;
export default function GuestRoomDirections({token}:{token:string}){
 const [locale]=useMarinaGuestLocale();
 const [route,setRoute]=useState<Route|null>(null);
 const [verified,setVerified]=useState(false);
 useEffect(()=>{
   let live=true;
   async function refresh(){
     try {
       const r=await fetch(`/core/api/v1/guest-os/rooms/${encodeURIComponent(token)}/wayfinding`,{credentials:"include",cache:"no-store"});
       if(!live)return;
       if(!r.ok){setVerified(false);setRoute(null);return}
       const data=await r.json();
       if(live){setVerified(true);setRoute(data.wayfinding)}
     }catch{if(live){setVerified(false);setRoute(null)}}
   }
   void refresh();
   window.addEventListener("marina:guest-session-updated",refresh);
   return()=>{live=false;window.removeEventListener("marina:guest-session-updated",refresh)};
 },[token]);
 if(!verified)return null;
 const t=lang[locale];
 return <section className="guest-os-panel" style={{maxWidth:1030,margin:"16px auto",padding:24}} aria-label={t.title}>
   <h2>{t.title}</h2>
   {!route?.map_url&&!route?.directions&&!route?.parking_label&&!route?.walkthrough_video_url?<p>{t.noRoute}</p>:<>
    {route.parking_label&&<p><strong>{t.parking}:</strong> {route.parking_label}</p>}
    {route.directions&&<p><strong>{t.directions}:</strong> {route.directions}</p>}
    <div style={{display:"flex",flexWrap:"wrap",gap:16}}>
      {route.map_url&&<a href={route.map_url} target="_blank" rel="noopener noreferrer">{t.map} ↗</a>}
      {route.walkthrough_video_url&&<a href={route.walkthrough_video_url} target="_blank" rel="noopener noreferrer">{t.video} ↗</a>}
    </div>
   </>}
 </section>
}