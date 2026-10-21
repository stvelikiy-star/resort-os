"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useMarinaGuestLocale } from "../lib/marinaGuestLocale";

type Saved = { rating: number; comment: string };
const copy = {
  ru: { title:"Оцените ваше проживание", intro:"Расскажите, как проходит отдых. Оценку увидит управляющий гостиницы.", comment:"Ваше мнение", placeholder:"Что понравилось или что нам исправить?", save:"Сохранить отзыв", saved:"Спасибо! Отзыв сохранён в истории вашего проживания.", error:"Не удалось сохранить. Убедитесь, что гостевой кабинет открыт по вашему PIN.", waiting:"Открывается после подтверждения проживания", urgent:"Спасибо за обратную связь. Управляющий увидит ваше обращение.", label:"Ваша оценка", kol:"КЁЛь · доставка и услуги", kolInfo:"Здесь появятся предложения КЁЛь после подключения отдельного защищённого сервиса. Сейчас заказы КЁЛь не принимаются." },
  kg: { title:"Жашооңузга баа бериңиз", intro:"Эс алууңуз тууралуу айтып бериңиз. Баа мейманкананын жетекчисине көрүнөт.", comment:"Сиздин пикириңиз", placeholder:"Эмне жакты же эмнени оңдошубуз керек?", save:"Пикирди сактоо", saved:"Рахмат! Пикириңиз жашоо тарыхында сакталды.", error:"Сакталбады. Конок кабинети PIN менен ачылганын текшериңиз.", waiting:"Жашоону ырастагандан кийин жеткиликтүү", urgent:"Рахмат. Жетекчи кайрылууңузду көрөт.", label:"Сиздин бааңыз", kol:"КЁЛь · жеткирүү жана кызматтар", kolInfo:"КЁЛь коопсуз туташтырылгандан кийин кызматтар пайда болот. Азыр буйрутма кабыл алынбайт." },
  kz: { title:"Тұруыңызды бағалаңыз", intro:"Демалысыңыз туралы айтыңыз. Бағаны қонақүй басшысы көреді.", comment:"Пікіріңіз", placeholder:"Не ұнады немесе нені жақсарту керек?", save:"Пікірді сақтау", saved:"Рақмет! Пікіріңіз тұру тарихына сақталды.", error:"Сақтау мүмкін болмады. Қонақ кабинеті PIN арқылы ашылғанын тексеріңіз.", waiting:"Тұру расталғаннан кейін қолжетімді", urgent:"Рақмет. Басшы пікіріңізді көреді.", label:"Сіздің бағаңыз", kol:"КЁЛь · жеткізу және қызметтер", kolInfo:"КЁЛь қауіпсіз қосылғаннан кейін қызметтер қолжетімді болады. Әзірге тапсырыс қабылданбайды." },
  en: { title:"Rate your stay", intro:"Share your experience. The hotel manager can read your feedback.", comment:"Your feedback", placeholder:"What worked well, or what should we improve?", save:"Save feedback", saved:"Thank you! Your feedback is now in your stay history.", error:"Could not save. Please verify your guest session with your PIN.", waiting:"Available after verifying your stay", urgent:"Thank you. The hotel manager can review your concern.", label:"Your rating", kol:"KÖL · delivery and services", kolInfo:"KÖL offerings will appear after a separate secure integration. Orders are not available yet." },
} as const;

export default function GuestStayReview({ token }: { token: string }) {
  const [active,setActive] = useState(false);
  const [reviewLinks,setReviewLinks] = useState<{google:string|null;gis:string|null;yandex:string|null}>({google:null,gis:null,yandex:null});
  const [locale] = useMarinaGuestLocale();
  const t = copy[locale];
  const [rating,setRating] = useState(5);
  const [comment,setComment] = useState("");
  const [saved,setSaved] = useState(false);
  const [busy,setBusy] = useState(false);
  const [notice,setNotice] = useState("");
  const refreshAccess = useCallback(async () => {
    try {
      const response = await fetch(`/core/api/v1/guest-os/rooms/${encodeURIComponent(token)}`, {credentials:"include",cache:"no-store"});
      const body = response.ok ? await response.json() : null;
      const authorized = Boolean(body?.authenticated && body?.active_stay);
      setActive(authorized);
      if (!authorized) { setComment(""); setRating(5); setSaved(false); setNotice(""); setReviewLinks({google:null,gis:null,yandex:null}); }
    } catch {setActive(false)}
  },[token]);
  useEffect(() => {
    void refreshAccess();
    window.addEventListener("marina:guest-session-updated",refreshAccess);
    return ()=>window.removeEventListener("marina:guest-session-updated",refreshAccess);
  },[refreshAccess]);
  useEffect(() => {
    if (!active) { setReviewLinks({google:null,gis:null,yandex:null}); return; }
    fetch(`/core/api/v1/guest-os/rooms/${encodeURIComponent(token)}/review-links`,{credentials:"include",cache:"no-store"})
      .then(res=>res.ok?res.json():null)
      .then(data=>{if(data?.available_to_all_ratings) setReviewLinks({google:data.google||null,gis:data.gis||null,yandex:data.yandex||null});})
      .catch(()=>{});
    let live = true;
    fetch(`/core/api/v1/guest-os/rooms/${encodeURIComponent(token)}/review`, {credentials:"include",cache:"no-store"})
      .then(async res=>res.ok ? res.json() : null)
      .then(data=>{if(live && data?.review){setRating(data.review.rating);setComment(data.review.comment || "");setSaved(true);}})
      .catch(()=>{});
    return ()=>{live=false};
  },[active,token]);
  async function save(e:FormEvent) {
    e.preventDefault();
    if(!active || busy) return;
    setBusy(true);setNotice("");
    try {
      const res = await fetch(`/core/api/v1/guest-os/rooms/${encodeURIComponent(token)}/review`,{
        method:"PUT",credentials:"include",headers:{"content-type":"application/json"},body:JSON.stringify({rating,comment})
      });
      if(!res.ok)throw new Error("Not saved");
      setSaved(true);setNotice(rating<=3 ? t.urgent : t.saved);
    } catch {setNotice(t.error)} finally {setBusy(false)}
  }
  return <div className="guest-marketplace-host" style={{maxWidth:1060,margin:"22px auto",padding:"0 16px"}}>
    <section className="guest-os-panel" aria-label={t.title} style={{padding:24,marginBottom:16}}>
      <h2>{t.title}</h2><p>{t.intro}</p>
      {!active?<p>{t.waiting}</p>:<form onSubmit={save}>
        <div role="group" aria-label={t.label} style={{display:"flex",flexWrap:"wrap",gap:9,margin:"16px 0"}}>
          {[1,2,3,4,5].map(n=><button key={n} type="button" aria-pressed={rating===n} onClick={()=>{setRating(n);setSaved(false)}} style={{padding:"10px 13px",borderRadius:12,border:"1px solid #c8d5cb",background:rating===n?"#e4efe8":"#fff",fontWeight:750}}>{n}★</button>)}
        </div>
        <label style={{display:"grid",gap:8}}>{t.comment}<textarea maxLength={2000} rows={4} value={comment} onChange={e=>{setComment(e.target.value);setSaved(false)}} placeholder={t.placeholder} style={{width:"100%",padding:12,font:"inherit",borderRadius:10,border:"1px solid #c8d5cb"}} /></label>
        <button type="submit" className="guest-os-primary" disabled={busy || saved} style={{marginTop:15}}>{busy?"…":t.save}</button>
        {notice&&<p role="status">{notice}</p>}
      </form>}
      {active && Object.values(reviewLinks).some(Boolean) && <aside style={{marginTop:18}}>
        <strong>{locale==="ru"?"Публичный отзыв — по вашему желанию":locale==="kg"?"Ачык пикир — каалооңуз боюнча":locale==="kz"?"Ашық пікір — өз қалауыңыз бойынша":"Public review — your choice"}</strong>
        <p>{locale==="ru"?"Можно оставить честный отзыв на карте независимо от оценки.":locale==="kg"?"Баага карабастан, картада чынчыл пикир калтырсаңыз болот.":locale==="kz"?"Бағаңызға қарамастан картаға шынайы пікір қалдыра аласыз.":"You may leave an honest public review regardless of your rating."}</p>
        <div style={{display:"flex",gap:12,flexWrap:"wrap"}}>
          {([["Google Maps",reviewLinks.google],["2GIS",reviewLinks.gis],["Яндекс Карты",reviewLinks.yandex]] as const).map(([label,url])=>url?<a key={label} href={url} target="_blank" rel="noopener noreferrer">{label} ↗</a>:null)}
        </div>
      </aside>}
    </section>
    <section className="guest-os-panel" aria-label={t.kol} style={{padding:24}}>
      <h2>{t.kol}</h2><p>{t.kolInfo}</p>
    </section>
  </div>;
}
