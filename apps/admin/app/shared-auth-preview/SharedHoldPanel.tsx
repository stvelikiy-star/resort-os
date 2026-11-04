"use client";

import { FormEvent, useState } from "react";

type Room = { id: string; code: string; name: string };
type Hold = {
  id: string; roomId: string; checkIn: string; checkOut: string;
  guestName: string; expiresAt: string;
};
type HoldReply = { id: string; status: "HELD" | "RELEASED"; expires_at?: string };

function later(days: number) {
  const d = new Date();
  d.setDate(d.getDate() + days);
  const pad = (v: number) => String(v).padStart(2, "0");
  return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate());
}

/** Only for the opt-in shared staging Admin. The server owns inventory and tenant rules. */
export default function SharedHoldPanel({rooms,onExpired}:{
  rooms: Room[]; onExpired: () => void;
}) {
  const [open,setOpen] = useState(false);
  const [busy,setBusy] = useState(false);
  const [roomId,setRoomId] = useState("");
  const [from,setFrom] = useState(later(6));
  const [until,setUntil] = useState(later(8));
  const [guest,setGuest] = useState("");
  const [phone,setPhone] = useState("");
  const [holds,setHolds] = useState<Hold[] | null>(null);
  const [notice,setNotice] = useState("");
  const [error,setError] = useState("");

  async function fetchList() {
    const res = await fetch("/core/api/v1/admin/pms/holds",{cache:"no-store"});
    if (res.status === 401) { onExpired(); throw new Error("expired"); }
    if (!res.ok) throw new Error("list");
    const data = await res.json() as {holds?:Hold[]};
    if (!Array.isArray(data.holds)) throw new Error("invalid");
    setHolds(data.holds);
  }
  async function showHolds() {
    if (busy) return;
    if (open) { setOpen(false); setHolds(null); return; }
    setOpen(true);
    setBusy(true); setError(""); setNotice("");
    try { await fetchList(); }
    catch { setError("Список удержаний не подтверждён. Обновите данные."); }
    finally { setBusy(false); }
  }
  async function createHold(e:FormEvent) {
    e.preventDefault();
    if (busy) return;
    if (!rooms.some(room => room.id === roomId) || until <= from) {
      setError("Выберите номер и корректные даты."); return;
    }
    if (!window.confirm("Заблокировать номер на 60 минут без бронирования и оплаты?")) return;
    setBusy(true);setNotice("");setError("");
    try {
      const res = await fetch("/core/api/v1/admin/pms/holds",{
        method:"POST",cache:"no-store",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({room_id:roomId,check_in:from,check_out:until,
          guest_name:guest.trim(),guest_phone:phone.trim()}),
      });
      if (res.status === 401) {onExpired();return;}
      if (res.status === 409) {
        setError("Номер уже занят или удерживается. Выберите другие даты.");return;
      }
      if (!res.ok) throw new Error("unconfirmed hold");
      const data = await res.json() as HoldReply;
      if (res.status !== 201 || data.status !== "HELD" ||
          !/^[0-9a-f-]{36}$/i.test(data.id) || !data.expires_at) {
        throw new Error("invalid hold receipt");
      }
      setNotice("HOLD подтверждён сервером до " + data.expires_at +
        ". Он истекает автоматически через 60 минут.");
      try {await fetchList();}
      catch {setError("Удержание создано, но список не обновился. Перезагрузите список.");}
    } catch {
      setError("Результат удержания не подтверждён. Сначала обновите список; не повторяйте запрос вслепую.");
    } finally {setBusy(false);}
  }
  async function releaseHold(hold:Hold) {
    if (busy) return;
    if (!window.confirm("Освободить удержание номера? Это нельзя отменить.")) return;
    setBusy(true);setError("");setNotice("");
    try {
      const res = await fetch("/core/api/v1/admin/pms/holds/" + hold.id,{
        method:"DELETE",cache:"no-store",
      });
      if (res.status === 401) {onExpired();return;}
      if (!res.ok) throw new Error("release");
      const data = await res.json() as HoldReply;
      if (data.id !== hold.id || data.status !== "RELEASED") throw new Error("unverified release");
      setNotice("HOLD освобождён сервером.");
      try {await fetchList();}
      catch {setError("Освобождение подтверждено, но список не обновился. Обновите список.");}
    } catch {
      setError("Освобождение не подтверждено. Проверьте актуальные удержания перед повтором.");
    } finally {setBusy(false);}
  }

  return <section aria-label="HOLD гостиницы">
    <h3>HOLD · удержание номера на 60 минут</h3>
    <p>Удержание не является бронью и не списывает оплату. Действует только для вашей гостиницы.</p>
    <button className="btn" disabled={busy} type="button"
      onClick={()=>void showHolds()}>{open?"Скрыть HOLD":"Показать HOLD"}</button>
    {open && <>
      <form aria-label="Форма HOLD" onSubmit={e=>void createHold(e)}>
        <label>Номер HOLD<select required disabled={busy} value={roomId}
          onChange={e=>setRoomId(e.target.value)}>
          <option value="">Выберите номер</option>
          {rooms.map(room=><option key={room.id} value={room.id}>{room.code} · {room.name}</option>)}
        </select></label>
        <label>Заезд HOLD<input type="date" required min={later(0)} disabled={busy}
          value={from} onChange={e=>setFrom(e.target.value)} /></label>
        <label>Выезд HOLD<input type="date" required disabled={busy}
          value={until} onChange={e=>setUntil(e.target.value)} /></label>
        <label>Гость HOLD<input required minLength={2} maxLength={160} disabled={busy}
          value={guest} onChange={e=>setGuest(e.target.value)} /></label>
        <label>Телефон HOLD<input required minLength={5} maxLength={40} disabled={busy}
          value={phone} onChange={e=>setPhone(e.target.value)} /></label>
        <button className="btn primary" type="submit" disabled={busy}>Удержать на 60 минут</button>
      </form>
      <button className="btn" type="button" disabled={busy} onClick={()=>{
        setBusy(true);setError("");
        void fetchList().catch(()=>setError("Не удалось обновить HOLD.")).finally(()=>setBusy(false));
      }}>Обновить HOLD</button>
      {holds && <div aria-label="Активные HOLD">
        {!holds.length && <p>Активных удержаний нет.</p>}
        {holds.map(hold=><div key={hold.id}>
          <p><strong>{rooms.find(room=>room.id===hold.roomId)?.code || "Номер"}</strong>
            {" · "}{hold.guestName} · {hold.checkIn} — {hold.checkOut}
            {" · до "}{hold.expiresAt}</p>
          <button className="btn" type="button" disabled={busy}
            onClick={()=>void releaseHold(hold)}>Освободить HOLD</button>
        </div>)}
      </div>}
    </>}
    {notice && <p role="status">{notice}</p>}
    {error && <p role="alert">{error}</p>}
  </section>;
}
