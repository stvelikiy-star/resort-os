"use client";

import { FormEvent, useMemo, useState } from "react";

type AvailableRoom = {
  id: string;
  code: string;
};

type PricingNight = {
  date: string;
  price_kgs: number | null;
  meal_included?: string;
  status: string;
};

type AvailabilityResult = {
  room_type_id: string;
  room_type_code: string;
  room_type_name: string;
  capacity_adults: number;
  capacity_children: number | null;
  children_capacity_confirmed: boolean;
  area: string | null;
  available_count: number;
  available_rooms: AvailableRoom[];
  pricing: {
    sellable: boolean;
    total_kgs: number | null;
    reason: string | null;
    nights: PricingNight[];
  };
};

type AvailabilityResponse = {
  check_in: string;
  check_out: string;
  nights: number;
  adults: number;
  children: number;
  results: AvailabilityResult[];
};

type SearchState = {
  checkIn: string;
  checkOut: string;
  adults: number;
  children: number;
};

const today = () => {
  const value = new Date();
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
};

const addDays = (iso: string, days: number) => {
  const [year, month, day] = iso.split("-").map(Number);
  const value = new Date(year, month - 1, day);
  value.setDate(value.getDate() + days);
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
};

const money = (value: number) => new Intl.NumberFormat("ru-RU").format(value);

function mealLabel(nights: PricingNight[]) {
  const values = Array.from(new Set(nights.map((night) => night.meal_included).filter(Boolean)));
  if (values.length !== 1) return values.length > 1 ? "Условия питания меняются по датам" : null;
  if (values[0] === "BREAKFAST") return "Завтрак включён";
  if (values[0] === "NONE") return "Без питания";
  return null;
}

export default function BookingWidget() {
  const initial = today();
  const [search, setSearch] = useState<SearchState>({ checkIn: initial, checkOut: addDays(initial, 2), adults: 2, children: 0 });
  const [results, setResults] = useState<AvailabilityResponse | null>(null);
  const [selected, setSelected] = useState<AvailabilityResult | null>(null);
  const [guestName, setGuestName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const validDates = useMemo(() => search.checkIn && search.checkOut && search.checkOut > search.checkIn, [search]);

  async function findRooms(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSuccess(null);
    setSelected(null);
    if (!validDates) {
      setError("Проверьте даты заезда и выезда.");
      return;
    }

    setLoading(true);
    try {
      const params = new URLSearchParams({
        check_in: search.checkIn,
        check_out: search.checkOut,
        adults: String(search.adults),
        children: String(search.children),
      });
      const response = await fetch(`/core/api/v1/booking/check-availability?${params}`, { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = (await response.json()) as AvailabilityResponse;
      setResults(payload);
      requestAnimationFrame(() => document.getElementById("availability")?.scrollIntoView({ behavior: "smooth", block: "start" }));
    } catch {
      setError("Не удалось проверить наличие. Попробуйте ещё раз или свяжитесь с отелем.");
    } finally {
      setLoading(false);
    }
  }

  async function sendRequest(event: FormEvent) {
    event.preventDefault();
    if (!selected || !results) return;
    setSending(true);
    setError(null);
    setSuccess(null);
    try {
      const response = await fetch("/core/api/v1/booking/requests", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          guest_name: guestName,
          phone,
          email: email || null,
          check_in: results.check_in,
          check_out: results.check_out,
          adults: results.adults,
          children: results.children,
          room_type_code: selected.room_type_code,
          source: "WEB",
        }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = (await response.json()) as { id: string };
      setSuccess(`Заявка принята · ${payload.id.slice(0, 8).toUpperCase()}. Менеджер свяжется для согласования и предоплаты.`);
      setGuestName("");
      setPhone("");
      setEmail("");
    } catch {
      setError("Не удалось отправить заявку. Данные не потеряны — повторите отправку или свяжитесь с отелем.");
    } finally {
      setSending(false);
    }
  }

  return (
    <section className="booking-shell" id="booking" aria-label="Поиск свободных номеров">
      <form className="booking-bar" onSubmit={findRooms}>
        <label className="booking-field"><span>Заезд</span><input type="date" min={today()} value={search.checkIn} onChange={(e) => setSearch({ ...search, checkIn: e.target.value })} required /></label>
        <label className="booking-field"><span>Выезд</span><input type="date" min={search.checkIn || today()} value={search.checkOut} onChange={(e) => setSearch({ ...search, checkOut: e.target.value })} required /></label>
        <label className="booking-field"><span>Взрослые</span><select value={search.adults} onChange={(e) => setSearch({ ...search, adults: Number(e.target.value) })}>{[1,2,3,4,5,6].map((v) => <option key={v} value={v}>{v}</option>)}</select></label>
        <label className="booking-field"><span>Дети</span><select value={search.children} onChange={(e) => setSearch({ ...search, children: Number(e.target.value) })}>{[0,1,2,3,4].map((v) => <option key={v} value={v}>{v}</option>)}</select></label>
        <button className="search-button" disabled={loading}>{loading ? "Проверяем…" : "Найти номер"}</button>
      </form>

      {error && <div className="booking-notice error">{error}</div>}
      {success && <div className="booking-notice success">{success}<strong> Заявка не является бронью до подтверждённой предоплаты.</strong></div>}

      {results && (
        <div className="availability" id="availability">
          <div className="availability-head">
            <div><span className="eyebrow dark">Свободные варианты</span><h2>{results.nights} {results.nights === 1 ? "ночь" : "ночей"}</h2></div>
            <p>{results.check_in} → {results.check_out} · {results.adults} взр.{results.children ? ` · ${results.children} дет.` : ""}</p>
          </div>

          {results.results.length === 0 ? (
            <div className="no-results">На выбранные даты подходящих свободных номеров не найдено. Измените даты или количество гостей.</div>
          ) : (
            <div className="availability-grid">
              {results.results.map((item) => {
                const meal = mealLabel(item.pricing.nights);
                return <article className="availability-card" key={item.room_type_id}>
                  <div>
                    <span className="availability-count">Свободно: {item.available_count}</span>
                    <h3>{item.room_type_name}</h3>
                    <p>{item.capacity_adults} осн. мест{item.area ? ` · ${item.area} м²` : ""}</p>
                  </div>
                  <div className="availability-price">
                    {item.pricing.sellable && item.pricing.total_kgs !== null ? <><strong>{money(item.pricing.total_kgs)} сом</strong><small>за весь период{meal ? ` · ${meal}` : ""}</small></> : <><strong>По запросу</strong><small>тариф требует подтверждения</small></>}
                  </div>
                  <button className="outline-button" onClick={() => setSelected(item)} type="button">Оставить заявку</button>
                </article>;
              })}
            </div>
          )}

          {selected && (
            <form className="request-form" onSubmit={sendRequest}>
              <div className="request-title"><span className="eyebrow dark">Заявка</span><h3>{selected.room_type_name}</h3><p>Мы передадим выбранные даты менеджеру. Действующая бронь появляется только после согласования и подтверждённой предоплаты.</p></div>
              <label><span>Имя</span><input value={guestName} onChange={(e) => setGuestName(e.target.value)} minLength={2} required placeholder="Как к вам обращаться" /></label>
              <label><span>Телефон / WhatsApp</span><input value={phone} onChange={(e) => setPhone(e.target.value)} minLength={5} required placeholder="+996 …" /></label>
              <label><span>Email, если нужен</span><input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@example.com" /></label>
              <button className="primary-button" disabled={sending}>{sending ? "Отправляем…" : "Отправить заявку"}</button>
            </form>
          )}
        </div>
      )}
    </section>
  );
}
