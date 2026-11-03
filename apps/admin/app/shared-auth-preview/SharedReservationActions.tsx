"use client";

import { FormEvent, useEffect, useState } from "react";
import SharedManualPaymentPanel from "./SharedManualPaymentPanel";

type Reservation = { id:string; bookingNumber:string; status:string; checkIn:string; checkOut:string;
  totalKgs:number; paidKgs:number; remainingKgs:number };
type Schedule = {
  reservation:{id:string;status:string;check_in:string;check_out:string;stored_total_kgs:number;version:string};
  schedule:Array<{room_id:string;room_code:string;start:string;end:string}>;
  local_today:string;
};
type Preview = {
  reservation:{id:string;version:string;stored_total_kgs:number};
  proposed_check_in:string; proposed_check_out:string; can_commit:boolean;
  conflicts:unknown[];
  pricing:{suggested_total_kgs:number|null;delta_kgs:number|null;stored_total_will_change_on_commit:boolean};
};
type FinanceReview = {reservation_id:string;unpaid_cancel_path_eligible:boolean;requires_manual_review:boolean};

export default function SharedReservationActions({booking,onExpired,onUpdated}:{
  booking:Reservation; onExpired:()=>void; onUpdated:()=>Promise<void>;
}) {
  const [schedule,setSchedule] = useState<Schedule|null>(null);
  const [from,setFrom] = useState(booking.checkIn);
  const [until,setUntil] = useState(booking.checkOut);
  const [preview,setPreview] = useState<Preview|null>(null);
  const [busy,setBusy] = useState(false);
  const [notice,setNotice] = useState("");
  const [error,setError] = useState("");

  useEffect(()=>{
    setSchedule(null);setPreview(null);setFrom(booking.checkIn);setUntil(booking.checkOut);
    setNotice("");setError("");
  },[booking.id,booking.status,booking.checkIn,booking.checkOut]);

  async function checked(url:string,init?:RequestInit):Promise<Response>{
    const response=await fetch(url,{cache:"no-store",...init});
    if(response.status===401) {onExpired();throw new Error("EXPIRED_SESSION");}
    return response;
  }
  async function loadSchedule() {
    if(busy) return;
    setBusy(true);setError("");setNotice("");setPreview(null);
    try{
      const response=await checked("/core/api/v1/admin/pms/reservations/"+booking.id+"/schedule");
      if(!response.ok) throw new Error("schedule read failed");
      const data=await response.json() as Schedule;
      if(data.reservation?.id!==booking.id || !data.reservation.version ||
         !Array.isArray(data.schedule)) throw new Error("invalid scoped schedule");
      setSchedule(data);
      setFrom(data.reservation.check_in);setUntil(data.reservation.check_out);
    }catch{
      setSchedule(null);
      setError("Текущий график брони не подтверждён. Изменения заблокированы.");
    }finally{setBusy(false);}
  }
  const editable=booking.status==="GUARANTEED" && schedule?.reservation.status==="GUARANTEED" &&
    schedule.schedule.length===1 && Boolean(schedule.reservation.version);
  const segment=editable && schedule ? [{
    room_id:schedule.schedule[0].room_id,start:from,end:until,
  }] : [];
  const quoteValid=Boolean(
    preview && schedule && segment.length===1 && preview.can_commit &&
    preview.reservation?.id===booking.id &&
    preview.reservation.version===schedule.reservation.version &&
    preview.proposed_check_in===from && preview.proposed_check_out===until &&
    preview.pricing.stored_total_will_change_on_commit===false &&
    Array.isArray(preview.conflicts) && preview.conflicts.length===0
  );
  function invalidate(){setPreview(null);setError("");setNotice("");}
  async function previewChange(event:FormEvent) {
    event.preventDefault();
    if(busy || !editable || !segment.length) return;
    setPreview(null);setError("");setNotice("");
    if(from<schedule!.local_today || until<=from) {setError("Проверьте новые даты.");return;}
    setBusy(true);
    try{
      const response=await checked("/core/api/v1/admin/pms/reservations/"+booking.id+"/schedule/preview",{
        method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({segments:segment}),
      });
      if(!response.ok) throw new Error("schedule preview failed");
      const data=await response.json() as Preview;
      if(!data.can_commit || data.reservation?.id!==booking.id ||
         data.reservation?.version!==schedule!.reservation.version ||
         data.proposed_check_in!==from || data.proposed_check_out!==until ||
         data.pricing.stored_total_will_change_on_commit!==false ||
         !Array.isArray(data.conflicts) || data.conflicts.length>0)
        throw new Error("unverified quote");
      setPreview(data);
    }catch{setError("Сервер не подтвердил изменение дат или свободный номер. Сохранение заблокировано.");}
    finally{setBusy(false);}
  }
  async function confirmChange(){
    if(busy || !quoteValid || !schedule || !preview || !segment.length) return;
    const priceText=preview.pricing.suggested_total_kgs===null?
      "Новая стоимость не определена — требуется отдельная проверка.":
      "Рекомендованная стоимость "+preview.pricing.suggested_total_kgs+" KGS.";
    if(!window.confirm("Сохранить новые даты? "+priceText+
      " ВАЖНО: сумма брони "+booking.totalKgs+" KGS автоматически не изменится.")) return;
    setBusy(true);setPreview(null);setError("");setNotice("");
    try{
      const response=await checked("/core/api/v1/admin/pms/reservations/"+booking.id+"/schedule/commit",{
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({segments:segment,expected_version:schedule.reservation.version}),
      });
      if(response.status===409){setError("График изменился или номер занят. Загрузите текущую бронь заново.");return;}
      if(!response.ok) throw new Error("commit failed");
      const data=await response.json();
      if(data.ok!==true || data.reservation_id!==booking.id ||
         data.check_in!==from || data.check_out!==until ||
         data.stored_total_kgs!==booking.totalKgs) throw new Error("unverified commit");
      setSchedule(null);
      setNotice("Даты подтверждены сервером. Сумма брони не пересчитана; проверьте финансовые условия.");
      try {await onUpdated();}
      catch {setError("Даты изменены, но список не обновился. Откройте раздел заново.");}
    }catch{
      setError("Результат изменения дат не подтверждён. Проверьте бронь перед повтором.");
    }finally{setBusy(false);}
  }
  async function cancelUnpaid() {
    if(busy || booking.status!=="GUARANTEED") return;
    setBusy(true);setError("");setNotice("");setPreview(null);
    try{
      const review=await checked("/core/api/v1/admin/booking/reservations/"+booking.id+"/cancellation-finance-review");
      if(!review.ok) throw new Error("no review");
      const data=await review.json() as FinanceReview;
      if(data.reservation_id!==booking.id || !data.unpaid_cancel_path_eligible || data.requires_manual_review){
        setError("Отмена недоступна: существует оплата, история проживания или открытые начисления. Нужна финансовая проверка.");
        return;
      }
      if(!window.confirm("Отменить неоплаченную PMS-бронь "+booking.bookingNumber+
        " и освободить номер? Возврат денег НЕ выполняется.")) return;
      const response=await checked("/core/api/v1/admin/pms/reservations/"+booking.id+"/cancel",{
        method:"POST",
      });
      if(response.status===409){setError("Состояние брони изменилось. Требуется повторная проверка.");return;}
      if(!response.ok) throw new Error("cancel failed");
      const result=await response.json();
      if(result.reservation_id!==booking.id || result.status!=="CANCELLED" ||
         result.payment_refunded!==false || !(result.released_blocks>=1)) throw new Error("unverified cancellation");
      setNotice("Бронь отменена сервером, номер освобождён. Денежный возврат не производился.");
      try {await onUpdated();}
      catch {setError("Отмена подтверждена, но список не обновился. Откройте раздел заново.");}
    }catch{
      setError("Отмена не подтверждена. Не повторяйте действие до проверки текущего статуса.");
    }finally{setBusy(false);}
  }
  return <section aria-label={"Управление бронью "+booking.bookingNumber}>
    <h3>Управление · {booking.bookingNumber}</h3>
    <p>Статус: {booking.status}. Учтено {booking.paidKgs} из {booking.totalKgs} KGS.</p>
    {booking.status==="GUARANTEED" && <>
      <button className="btn" type="button" disabled={busy}
        onClick={()=>void loadSchedule()}>Загрузить график</button>
      {editable && schedule && <form aria-label="Изменение дат брони" onSubmit={e=>void previewChange(e)}>
        <p>Номер: {schedule.schedule[0].room_code}. Изменяется один непрерывный период.</p>
        <label>Новый заезд<input type="date" required min={schedule.local_today}
          disabled={busy} value={from} onChange={e=>{setFrom(e.target.value);invalidate();}} /></label>
        <label>Новый выезд<input type="date" required disabled={busy}
          value={until} onChange={e=>{setUntil(e.target.value);invalidate();}} /></label>
        <button className="btn" type="submit" disabled={busy}>Проверить новые даты</button>
      </form>}
      {schedule && !editable && <p>Для сложного графика требуется полная шахматка; операция здесь закрыта.</p>}
      {quoteValid && preview && <div role="status">
        <p>Сервер подтвердил даты. Предложенная стоимость: {preview.pricing.suggested_total_kgs??"не определена"} KGS.</p>
        <p><strong>Текущая сумма {booking.totalKgs} KGS не изменится автоматически.</strong></p>
        <button className="btn primary" disabled={busy} type="button"
          onClick={()=>void confirmChange()}>Сохранить даты</button>
      </div>}
      <button className="btn" type="button" disabled={busy}
        onClick={()=>void cancelUnpaid()}>Отменить неоплаченную бронь</button>
      <SharedManualPaymentPanel reservationId={booking.id} bookingNumber={booking.bookingNumber}
        onExpired={onExpired} onUpdated={onUpdated} />
    </>}
    {notice && <p role="status">{notice}</p>}
    {error && <p role="alert">{error}</p>}
  </section>;
}
