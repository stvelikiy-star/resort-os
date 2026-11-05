"use client";

import { FormEvent, useRef, useState } from "react";

type Readiness = {
  reservation_id:string;currency:string;status:string;remaining_kgs:number;
  provider_connected:boolean;payment_link:null;acquiring_status:string;
};
type Receipt = {
  idempotent_replay:boolean;payment_id:string;reservation_id:string;
  payment:{amount_kgs:number;method:string;status:string;provider:string};
  finance:{paid_kgs:number;remaining_kgs:number};
};
const METHODS = [
  ["CASH","Наличные"],
  ["CARD_POS","Терминал POS (получено)"],
  ["BANK_TRANSFER","Банковский перевод (получено)"],
  ["OTHER","Другой подтверждённый способ"],
] as const;

/** Records an already-received manual payment; never initiates acquiring. */
export default function SharedManualPaymentPanel({
  reservationId,bookingNumber,onExpired,onUpdated,
}:{
  reservationId:string;bookingNumber:string;onExpired:()=>void;onUpdated:()=>Promise<void>;
}){
  const [open,setOpen]=useState(false);
  const [busy,setBusy]=useState(false);
  const [review,setReview]=useState<Readiness|null>(null);
  const [amount,setAmount]=useState("");
  const [method,setMethod]=useState<(typeof METHODS)[number][0]>("CASH");
  const [acknowledged,setAcknowledged]=useState(false);
  const [note,setNote]=useState("");
  const [notice,setNotice]=useState("");
  const [error,setError]=useState("");
  const [unverified,setUnverified]=useState(false);
  const submittedKey=useRef<string|null>(null);

  async function checkBalance(){
    if(busy || unverified) return;
    setBusy(true);setError("");setNotice("");setReview(null);
    try{
      const res=await fetch("/core/api/v1/admin/booking/reservations/"+reservationId+
        "/acquiring-readiness",{cache:"no-store"});
      if(res.status===401){onExpired();return;}
      if(!res.ok) throw new Error("readiness failed");
      const data=await res.json() as Readiness;
      if(data.reservation_id!==reservationId || data.currency!=="KGS" ||
         !Number.isSafeInteger(data.remaining_kgs) || data.remaining_kgs<0 ||
         data.provider_connected!==false || data.payment_link!==null ||
         data.acquiring_status!=="NOT_CONFIGURED")
        throw new Error("invalid readiness");
      setReview(data);
    }catch{setError("Остаток не подтверждён сервером. Запись оплаты заблокирована.");}
    finally{setBusy(false);}
  }
  const parsed=Number(amount);
  const canRecord=Boolean(review && !unverified && !busy && acknowledged &&
    Number.isSafeInteger(parsed) && parsed>0 && parsed<=review.remaining_kgs &&
    METHODS.some(([key])=>key===method));
  async function record(e:FormEvent){
    e.preventDefault();
    if(!canRecord || !review || submittedKey.current) return;
    if(!window.confirm("Подтвердите: "+parsed+" KGS по брони "+bookingNumber+
      " УЖЕ фактически получены? Запись в системе не списывает средства и не подтверждает банк.")) return;
    setBusy(true);setError("");setNotice("");setReview(null);
    const key=crypto.randomUUID();
    submittedKey.current=key;
    try{
      const res=await fetch("/core/api/v1/admin/booking/reservations/"+reservationId+"/payments",{
        method:"POST",cache:"no-store",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({amount_kgs:parsed,method,idempotency_key:key,note:note.trim()||null}),
      });
      if(res.status===401){onExpired();setUnverified(true);return;}
      if(res.status===409){setUnverified(true);
        setError("Сервер отклонил запись: остаток или данные изменились. Проверьте финансовый журнал перед повтором.");
        return;}
      if(res.status!==201) throw new Error("unconfirmed");
      const data=await res.json() as Receipt;
      if(data.reservation_id!==reservationId || !data.payment_id ||
         data.payment.amount_kgs!==parsed || data.payment.method!==method ||
         data.payment.status!=="RECEIVED" || data.payment.provider!=="MANAGER_MANUAL" ||
         data.idempotent_replay!==false) throw new Error("invalid server receipt");
      setNotice("Учтена ранее полученная оплата "+parsed+" KGS. Это внутренняя запись, не банковское списание.");
      setAmount("");setAcknowledged(false);setNote("");
      submittedKey.current=null;
      try{await onUpdated();}
      catch{setError("Платёж записан сервером, но список не обновился. Обновите бронирования.");}
    }catch{
      setUnverified(true);
      setError("Результат операции не подтверждён. Не отправляйте оплату повторно вслепую; проверьте бухгалтерский журнал.");
    }finally{setBusy(false);}
  }

  return <section aria-label={"Внутренняя оплата "+bookingNumber}>
    <button className="btn" type="button" disabled={busy}
      onClick={()=>{setOpen(x=>!x);setReview(null);setError("");}}>
      {open?"Скрыть учёт оплаты":"Записать полученную оплату"}
    </button>
    {open && <>
      <p><strong>Только внутренняя запись фактически полученных средств.</strong>
        Карта не списывается, ссылки на оплату и возвраты не создаются.</p>
      <button className="btn" type="button" disabled={busy || unverified}
        onClick={()=>void checkBalance()}>Проверить остаток</button>
      {review && <form aria-label="Форма ручной оплаты" onSubmit={e=>void record(e)}>
        <p>По данным гостиницы осталось: <strong>{review.remaining_kgs} KGS</strong>.</p>
        <label>Полученная сумма, KGS<input type="number" required min={1}
          max={review.remaining_kgs} step={1} disabled={busy}
          value={amount} onChange={e=>setAmount(e.target.value)}/></label>
        <label>Способ получения<select disabled={busy} value={method}
          onChange={e=>setMethod(e.target.value as typeof method)}>
          {METHODS.map(([key,label])=><option key={key} value={key}>{label}</option>)}
        </select></label>
        <label>Примечание<input maxLength={500} disabled={busy} value={note}
          onChange={e=>setNote(e.target.value)}/></label>
        <label><input type="checkbox" checked={acknowledged} disabled={busy}
          onChange={e=>setAcknowledged(e.target.checked)}/>
          Деньги действительно уже получены, я проверил(а) сумму</label>
        <button className="btn primary" type="submit" disabled={!canRecord}>
          Записать полученную сумму
        </button>
      </form>}
      {unverified && <p role="alert">Повторная отправка в этом сеансе заблокирована до проверки финансовых записей.</p>}
      {notice && <p role="status">{notice}</p>}
      {error && <p role="alert">{error}</p>}
    </>}
  </section>;
}
