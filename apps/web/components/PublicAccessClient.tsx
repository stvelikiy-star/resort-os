"use client";

import { useCallback, useEffect, useState } from "react";

type Lang="ru"|"en"|"ky";
type Quote={code:string;name:string;kind:string;price_kgs:number;currency:string;payment_required:boolean};
type Intent={intent_id:string;token:string;amount_kgs:number;expires_at:string;checkout_url:string};
const copy={
  ru:{brand:"Три Короны",title:"Доступ по QR",price:"Стоимость входа",pay:"Оплатить",checking:"Проверить оплату",paid:"Оплата подтверждена",unlock:"Открыть дверь",opened:"Дверь открыта на 7 секунд",closed:"Доступ пока не оплачен",unavailable:"Этот QR сейчас недоступен",provider:"Онлайн-оплата пока не подключена. Дверь остаётся закрытой.",failed:"Замок не подтвердил открытие. Обратитесь к сотруднику.",safe:"Оплата не является ключом. После подтверждения система выдаёт одноразовый доступ и открывает только эту точку."},
  en:{brand:"Three Crowns",title:"QR access",price:"Entry price",pay:"Pay",checking:"Check payment",paid:"Payment confirmed",unlock:"Unlock door",opened:"Door unlocked for 7 seconds",closed:"Payment is not confirmed yet",unavailable:"This QR access point is unavailable",provider:"Online payment is not connected yet. The door remains locked.",failed:"The lock did not confirm opening. Please contact staff.",safe:"Payment is not a key. After confirmation, the system issues one-time access for this exact access point."},
  ky:{brand:"Үч Таажы",title:"QR аркылуу кирүү",price:"Кирүү баасы",pay:"Төлөө",checking:"Төлөмдү текшерүү",paid:"Төлөм ырасталды",unlock:"Эшикти ачуу",opened:"Эшик 7 секундга ачылды",closed:"Төлөм азырынча ырастала элек",unavailable:"Бул QR кирүү чекити жеткиликсиз",provider:"Онлайн төлөм азырынча туташкан эмес. Эшик жабык бойдон калат.",failed:"Кулпу ачылганын ырастаган жок. Кызматкерге кайрылыңыз.",safe:"Төлөм ачкыч эмес. Ырасталгандан кийин система ушул кирүү чекити үчүн бир жолку уруксат берет."}
} as const;

function money(v:number,lang:Lang){return new Intl.NumberFormat(lang==="en"?"en-US":lang==="ky"?"ky-KG":"ru-RU").format(v)+" сом"}

export default function PublicAccessClient({code}:{code:string}){
  const [lang,setLang]=useState<Lang>("ru");const t=copy[lang];
  const [quote,setQuote]=useState<Quote|null>(null),[intent,setIntent]=useState<Intent|null>(null),[status,setStatus]=useState<string>(""),[notice,setNotice]=useState(""),[busy,setBusy]=useState(false),[missing,setMissing]=useState(false);
  const loadQuote=useCallback(async()=>{try{const r=await fetch(`/core/api/v1/public/access/${encodeURIComponent(code)}`,{cache:"no-store"});if(!r.ok){setMissing(true);return}setQuote(await r.json())}catch{setMissing(true)}},[code]);
  useEffect(()=>{void loadQuote()},[loadQuote]);

  async function checkout(){setBusy(true);setNotice("");try{const r=await fetch(`/core/api/v1/public/access/${encodeURIComponent(code)}/checkout`,{method:"POST"});const b=await r.json().catch(()=>({}));if(!r.ok){setNotice(r.status===503?t.provider:(b.detail||t.unavailable));return}setIntent(b);setStatus("PENDING");sessionStorage.setItem(`access:${b.intent_id}`,b.token);window.open(b.checkout_url,"_blank","noopener,noreferrer")}finally{setBusy(false)}}
  async function checkPayment(){if(!intent)return;setBusy(true);setNotice("");try{const r=await fetch(`/core/api/v1/public/access/intents/${intent.intent_id}/status`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({token:intent.token})});const b=await r.json().catch(()=>({}));if(!r.ok){setNotice(b.detail||t.unavailable);return}setStatus(b.status);setNotice(b.status==="PAID"?t.paid:t.closed)}finally{setBusy(false)}}
  async function unlock(){if(!intent)return;setBusy(true);setNotice("");try{const r=await fetch(`/core/api/v1/public/access/intents/${intent.intent_id}/unlock`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({token:intent.token})});if(!r.ok){setNotice(t.failed);return}setStatus("USED");setNotice(t.opened)}finally{setBusy(false)}}

  return <main className="public-access-shell"><section className="public-access-card"><div className="public-access-mark">III</div><div className="public-access-lang"><button onClick={()=>setLang("ru")}>RU</button><button onClick={()=>setLang("en")}>EN</button><button onClick={()=>setLang("ky")}>KG</button></div><p className="public-access-eyebrow">{t.brand} · Resort OS</p><h1>{t.title}</h1>{missing&&<div className="public-access-error">{t.unavailable}</div>}{quote&&<><h2>{quote.name}</h2><div className="public-access-price"><span>{t.price}</span><strong>{money(quote.price_kgs,lang)}</strong></div><p className="public-access-safe">{t.safe}</p>{!intent&&<button className="public-access-primary" onClick={checkout} disabled={busy||!quote.payment_required}>{t.pay}</button>}{intent&&status!=="PAID"&&status!=="USED"&&<button className="public-access-primary" onClick={checkPayment} disabled={busy}>{t.checking}</button>}{intent&&status==="PAID"&&<button className="public-access-primary" onClick={unlock} disabled={busy}>{t.unlock}</button>}{notice&&<div className="public-access-notice">{notice}</div>}</>}</section></main>
}
