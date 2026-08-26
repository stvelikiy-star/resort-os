"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { trackPublicEvent } from "../lib/publicAnalytics";

type AvailableRoom = { id: string; code: string };
type PricingNight = { date: string; price_kgs: number | null; meal_included?: string; status: string };
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
type SearchState = { checkIn: string; checkOut: string; adults: number; children: number };

const localIsoDate = () => {
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
const formatDate = (iso: string) => {
  const [year, month, day] = iso.split("-").map(Number);
  return new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "short" }).format(new Date(year, month - 1, day));
};
function nightsLabel(value: number) {
  const mod10 = value % 10;
  const mod100 = value % 100;
  if (mod10 === 1 && mod100 !== 11) return `${value} ночь`;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return `${value} ночи`;
  return `${value} ночей`;
}
function mealLabel(nights: PricingNight[]) {
  const values = Array.from(new Set(nights.map((night) => night.meal_included).filter(Boolean)));
  if (values.length !== 1) return values.length > 1 ? "Условия питания меняются по датам" : null;
  if (values[0] === "BREAKFAST") return "Завтрак включён";
  if (values[0] === "NONE") return "Без питания";
  return null;
}
function priceSortValue(item: AvailabilityResult) {
  return !item.pricing.sellable || item.pricing.total_kgs == null ? Number.MAX_SAFE_INTEGER : item.pricing.total_kgs;
}

export default function BookingWidget() {
  const [minimumDate, setMinimumDate] = useState("");
  const [search, setSearch] = useState<SearchState>({ checkIn: "", checkOut: "", adults: 2, children: 0 });
  const [results, setResults] = useState<AvailabilityResponse | null>(null);
  const [selected, setSelected] = useState<AvailabilityResult | null>(null);
  const [guestName, setGuestName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    const initial = localIsoDate();
    setMinimumDate(initial);
    setSearch({ checkIn: initial, checkOut: addDays(initial, 2), adults: 2, children: 0 });
  }, []);

  const validDates = useMemo(
    () => Boolean(search.checkIn && search.checkOut && search.checkOut > search.checkIn),
    [search.checkIn, search.checkOut],
  );
  const sortedResults = useMemo(() => {
    if (!results) return [];
    return [...results.results].sort((left, right) => {
      if (left.pricing.sellable !== right.pricing.sellable) return left.pricing.sellable ? -1 : 1;
      if (priceSortValue(left) !== priceSortValue(right)) return priceSortValue(left) - priceSortValue(right);
      return left.room_type_name.localeCompare(right.room_type_name, "ru");
    });
  }, [results]);

  function resetResultState() {
    setResults(null);
    setSelected(null);
    setError(null);
    setSuccess(null);
  }

  function changeCheckIn(value: string) {
    const minimumCheckout = value ? addDays(value, 1) : "";
    setSearch((current) => ({
      ...current,
      checkIn: value,
      checkOut: !current.checkOut || current.checkOut <= value ? minimumCheckout : current.checkOut,
    }));
    resetResultState();
  }

  function selectRoom(item: AvailabilityResult) {
    trackPublicEvent("booking_room_selected", {
      room_type_code: item.room_type_code,
      sellable: item.pricing.sellable,
      quoted_total_kgs: item.pricing.total_kgs,
      available_count: item.available_count,
    });
    setSelected(item);
    setSuccess(null);
    setError(null);
    requestAnimationFrame(() => document.getElementById("request-form")?.scrollIntoView({ behavior: "smooth", block: "center" }));
  }

  async function findRooms(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSuccess(null);
    setSelected(null);
    if (!validDates) {
      setError("Проверьте даты заезда и выезда.");
      return;
    }

    trackPublicEvent("booking_search_started", {
      adults: search.adults,
      children: search.children,
    });
    setLoading(true);
    setResults(null);

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
      trackPublicEvent("booking_search_succeeded", {
        nights: payload.nights,
        adults: payload.adults,
        children: payload.children,
        room_type_count: payload.results.length,
        available_room_count: payload.results.reduce((sum, item) => sum + item.available_count, 0),
        sellable_type_count: payload.results.filter((item) => item.pricing.sellable).length,
      });
      requestAnimationFrame(() => document.getElementById("availability")?.scrollIntoView({ behavior: "smooth", block: "start" }));
    } catch {
      trackPublicEvent("booking_search_failed", {
        adults: search.adults,
        children: search.children,
      });
      setError("Не удалось проверить наличие. Попробуйте ещё раз или свяжитесь с менеджером.");
    } finally {
      setLoading(false);
    }
  }

  async function sendRequest(event: FormEvent) {
    event.preventDefault();
    if (!selected || !results) return;

    const analyticsPayload = {
      room_type_code: selected.room_type_code,
      nights: results.nights,
      adults: results.adults,
      children: results.children,
      quoted_total_kgs: selected.pricing.total_kgs,
    };
    trackPublicEvent("booking_request_started", analyticsPayload);
    setSending(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await fetch("/core/api/v1/booking/requests", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          guest_name: guestName.trim(),
          phone: phone.trim(),
          email: email.trim() || null,
          check_in: results.check_in,
          check_out: results.check_out,
          adults: results.adults,
          children: results.children,
          room_type_code: selected.room_type_code,
          source: "WEB",
        }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = body as { id: string };
      trackPublicEvent("booking_request_succeeded", analyticsPayload);
      setSuccess(`Заявка ${payload.id.slice(0, 8).toUpperCase()} принята. Менеджер свяжется с вами для согласования условий и предоплаты.`);
      setGuestName("");
      setPhone("");
      setEmail("");
      setSelected(null);
    } catch {
      trackPublicEvent("booking_request_failed", analyticsPayload);
      setError("Не удалось отправить заявку. Повторите отправку или свяжитесь с менеджером по телефону.");
    } finally {
      setSending(false);
    }
  }

  return (
    <section className="booking-shell" id="booking" aria-labelledby="booking-title" aria-busy={loading || sending}>
      <div className="booking-intro">
        <div><p className="eyebrow">Проверка наличия</p><h2 id="booking-title">Найдите номер на ваши даты</h2></div>
        <p><span className="live-dot" aria-hidden="true" /> Наличие и цена одного номера — из системы отеля</p>
      </div>

      <form className="booking-bar" onSubmit={findRooms}>
        <label className="booking-field"><span>Заезд</span><input type="date" min={minimumDate || undefined} value={search.checkIn} onChange={(event) => changeCheckIn(event.target.value)} required /></label>
        <label className="booking-field"><span>Выезд</span><input type="date" min={search.checkIn ? addDays(search.checkIn, 1) : minimumDate || undefined} value={search.checkOut} onChange={(event) => { setSearch({ ...search, checkOut: event.target.value }); resetResultState(); }} required /></label>
        <label className="booking-field"><span>Взрослые</span><select value={search.adults} onChange={(event) => { setSearch({ ...search, adults: Number(event.target.value) }); resetResultState(); }}>{[1, 2, 3, 4].map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
        <label className="booking-field"><span>Дети</span><select value={search.children} onChange={(event) => { setSearch({ ...search, children: Number(event.target.value) }); resetResultState(); }}>{[0, 1, 2, 3, 4].map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
        <button className="search-button" type="submit" disabled={loading || !validDates}>{loading ? "Проверяем…" : "Найти номер"}</button>
      </form>

      <div className="booking-feedback" aria-live="polite" aria-atomic="true">
        {error && <div className="booking-notice error" role="alert">{error}</div>}
        {success && <div className="booking-notice success" role="status">{success}<strong>Заявка ещё не является подтверждённой бронью.</strong></div>}
      </div>

      {results && <div className="availability" id="availability">
        <div className="availability-head">
          <div><p className="eyebrow">Свободные варианты</p><h2>{nightsLabel(results.nights)}</h2></div>
          <p>{formatDate(results.check_in)} → {formatDate(results.check_out)} · {results.adults} взр.{results.children ? ` · ${results.children} дет. · детские места — по подтверждению менеджера` : ""}</p>
        </div>

        {sortedResults.length === 0
          ? <div className="no-results"><strong>На выбранные даты подходящих свободных номеров не найдено.</strong><span>Попробуйте соседние даты или позвоните в бронирование.</span><a href="tel:+996558085002">+996 558 08 50 02</a></div>
          : <div className="availability-grid">{sortedResults.map((item) => {
              const meal = mealLabel(item.pricing.nights);
              const isSelected = selected?.room_type_id === item.room_type_id;
              return <article className={`availability-card ${isSelected ? "selected" : ""}`} key={item.room_type_id}>
                <div className="availability-card-top"><span className="availability-count">Свободно: {item.available_count}</span><span className="availability-code">{item.room_type_code}</span></div>
                <h3>{item.room_type_name}</h3>
                <p className="availability-meta">{item.capacity_adults} осн. мест{item.area ? ` · ${item.area} м²` : ""}{results.children > 0 && !item.children_capacity_confirmed ? " · детские места уточняются" : ""}</p>
                <div className="availability-price">{item.pricing.sellable && item.pricing.total_kgs !== null
                  ? <><strong>{money(item.pricing.total_kgs)} сом</strong><small>за весь период{meal ? ` · ${meal}` : ""}</small></>
                  : <><strong>По запросу</strong><small>тариф требует подтверждения менеджером</small></>}
                </div>
                <button className={isSelected ? "button button-dark" : "button button-outline"} onClick={() => selectRoom(item)} type="button" aria-pressed={isSelected}>{item.pricing.sellable ? (isSelected ? "Выбрано" : "Оставить заявку") : "Уточнить у менеджера"}</button>
              </article>;
            })}</div>}

        {selected && <form className="request-form" id="request-form" onSubmit={sendRequest}>
          <div className="request-title"><p className="eyebrow">Заявка менеджеру</p><h3>{selected.room_type_name}</h3><p>Передадим выбранные даты и категорию. Менеджер согласует условия и предоплату.</p></div>
          <label><span>Имя</span><input value={guestName} onChange={(event) => setGuestName(event.target.value)} minLength={2} required placeholder="Как к вам обращаться" autoComplete="name" /></label>
          <label><span>Телефон</span><input value={phone} onChange={(event) => setPhone(event.target.value)} minLength={5} required placeholder="+996 …" autoComplete="tel" inputMode="tel" /></label>
          <label><span>Email, если нужен</span><input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="name@example.com" autoComplete="email" /></label>
          <button className="button button-dark request-submit" type="submit" disabled={sending}>{sending ? "Отправляем…" : "Отправить заявку"}</button>
          <small className="request-disclaimer">Отправка заявки не блокирует номер автоматически. Подтверждение брони делает менеджер после согласования условий и предоплаты.</small>
        </form>}
      </div>}
    </section>
  );
}
