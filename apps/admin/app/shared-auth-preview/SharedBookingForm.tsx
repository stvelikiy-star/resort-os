"use client";

import { FormEvent, useState } from "react";

type Room = { id: string; code: string; name: string };
type BookingQuote = {
  room: { id: string };
  check_in: string;
  check_out: string;
  can_commit: boolean;
  pricing: { source: string; total_kgs: number | null };
};
type CommitReply = {
  reservation_id: string; room_id: string; status: string;
  booking_number: string; total_kgs: number;
};

function hotelDate(offset: number) {
  const d = new Date();
  d.setDate(d.getDate() + offset);
  const pad = (v: number) => String(v).padStart(2, "0");
  return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate());
}

/** Shared staging only. All authority, price and availability stay on the server. */
export default function SharedBookingForm({
  rooms, onExpired, coreRateOnly = false,
}: {
  rooms: Room[];
  onExpired: () => void;
  coreRateOnly?: boolean;
}) {
  const [roomId, setRoomId] = useState("");
  const [checkIn, setCheckIn] = useState(hotelDate(2));
  const [checkOut, setCheckOut] = useState(hotelDate(4));
  const [guestName, setGuestName] = useState("");
  const [phone, setPhone] = useState("");
  const [quote, setQuote] = useState<BookingQuote | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [success, setSuccess] = useState("");

  const fields = { room_id: roomId, check_in: checkIn, check_out: checkOut, adults: 2, children: 0, guest_phone: phone };
  const priceAllowed = (source: string) => source === "CORE_RATE" ||
    (!coreRateOnly && source === "MANAGER_OVERRIDE");
  const validQuote = quote &&
    quote.room.id === roomId && quote.check_in === checkIn && quote.check_out === checkOut &&
    quote.can_commit === true && Number.isSafeInteger(quote.pricing.total_kgs) &&
    Number(quote.pricing.total_kgs) > 0 &&
    priceAllowed(quote.pricing.source) &&
    rooms.some(room => room.id === roomId);
  function invalidate() {
    setQuote(null);
    setNotice("");
    setSuccess("");
  }

  async function preview(e: FormEvent) {
    e.preventDefault();
    if (busy) return;
    setQuote(null);
    setSuccess("");
    setNotice("");
    if (!rooms.some(room => room.id === roomId) || checkOut <= checkIn) {
      setNotice("Выберите номер и корректные даты проживания.");
      return;
    }
    setBusy(true);
    try {
      const response = await fetch("/core/api/v1/admin/pms/reservations/new/preview", {
        method: "POST", cache: "no-store", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(fields),
      });
      if (response.status === 401) { onExpired(); return; }
      if (!response.ok) throw new Error("preview failed");
      const data = await response.json() as BookingQuote;
      if (data.room?.id !== roomId || data.check_in !== checkIn || data.check_out !== checkOut ||
          !data.can_commit || !Number.isSafeInteger(data.pricing?.total_kgs) ||
          Number(data.pricing.total_kgs) <= 0 ||
          !priceAllowed(data.pricing.source)) {
        throw new Error("unavailable or unverified quote");
      }
      setQuote(data);
    } catch {
      setNotice("Свободные даты и стоимость не подтверждены сервером. Создание брони заблокировано.");
    } finally {
      setBusy(false);
    }
  }

  async function commit() {
    if (!validQuote || !quote || busy) return;
    if (!window.confirm("Создать бронь по подтверждённой сервером цене " +
      quote.pricing.total_kgs + " KGS? Оплата не взимается.")) return;
    setBusy(true);
    setNotice("");
    setSuccess("");
    // A quote is consumable once: do not expose automatic retries after unknown outcomes.
    setQuote(null);
    try {
      const response = await fetch("/core/api/v1/admin/pms/reservations/new/commit", {
        method: "POST", cache: "no-store", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...fields, guest_name: guestName.trim(), phone: phone.trim(),
          expected_total_kgs: quote.pricing.total_kgs,
          expected_pricing_source: quote.pricing.source,
        }),
      });
      if (response.status === 401) { onExpired(); return; }
      if (response.status === 409) {
        setNotice("Цена, даты или доступность изменились. Проверьте бронирования, затем получите новый расчёт.");
        return;
      }
      if (!response.ok) throw new Error("commit failed");
      const data = await response.json() as CommitReply;
      if (response.status !== 201 || !/^[0-9a-f-]{36}$/i.test(data.reservation_id) ||
          data.room_id !== roomId || data.status !== "GUARANTEED" ||
          data.total_kgs !== quote.pricing.total_kgs) throw new Error("invalid commit reply");
      setSuccess("Бронирование " + data.booking_number + " создано сервером. " +
        "Оплата не проведена. Для обновления шахматки откройте раздел повторно.");
    } catch {
      setNotice("Результат отправки не подтверждён. Сначала проверьте существующие брони; " +
        "не отправляйте запрос повторно вслепую.");
    } finally {
      setBusy(false);
    }
  }

  return <section aria-label="Создание бронирования">
    <h3>Новая бронь · без оплаты</h3>
    <p>Проверка свободных дат и итоговой цены выполняется сервером своей гостиницы.</p>
    <form aria-label="Форма бронирования" onSubmit={e => void preview(e)}>
      <label>Номер<select required disabled={busy} value={roomId} onChange={e => { setRoomId(e.target.value); invalidate(); }}>
        <option value="">Выберите номер</option>
        {rooms.map(room => <option key={room.id} value={room.id}>{room.code} · {room.name}</option>)}
      </select></label>
      <label>Заезд<input type="date" required min={hotelDate(0)} disabled={busy} value={checkIn}
        onChange={e => { setCheckIn(e.target.value); invalidate(); }} /></label>
      <label>Выезд<input type="date" required disabled={busy} value={checkOut}
        onChange={e => { setCheckOut(e.target.value); invalidate(); }} /></label>
      <label>Имя гостя<input required minLength={2} maxLength={160} disabled={busy}
        value={guestName} onChange={e => { setGuestName(e.target.value); invalidate(); }} /></label>
      <label>Телефон гостя<input required minLength={5} maxLength={40} disabled={busy}
        value={phone} onChange={e => { setPhone(e.target.value); invalidate(); }} /></label>
      <button className="btn" type="submit" disabled={busy}>Проверить доступность и цену</button>
    </form>
    {validQuote && quote && <div role="status">
      <p>Подтверждённая стоимость: <strong>{quote.pricing.total_kgs} KGS</strong></p>
      <button className="btn primary" type="button" disabled={busy} onClick={() => void commit()}>
        Подтвердить бронь
      </button>
    </div>}
    {notice && <p role="alert">{notice}</p>}
    {success && <p role="status">{success}</p>}
  </section>;
}
