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

function priceSortValue(item: AvailabilityResult) {
  if (!item.pricing.sellable || item.pricing.total_kgs == null) return Number.MAX_SAFE_INTEGER;
  return item.pricing.total_kgs;
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
  const sortedResults = useMemo(() => {
    if (!results) return [];
    return [...results.results].sort((left, right) => {
      if (left.pricing.sellable !== right.pricing.sellable) return left.pricing.sellable ? -1 : 1;
      if (priceSortValue(left) !== priceSortValue(right)) return priceSortValue(left) - priceSortValue(right);
      return left.room_type_name.localeCompare(right.room_type_name, "ru");
    });
  }, [results]);

  function changeCheckIn(value: string) {
    const minimumCheckout = addDays(value, 1);
    setSearch((current) => ({
      ...current,
      checkIn: value,
      checkOut: !current.checkOut || current.checkOut <= value ? minimumCheckout : current.checkOut,
    }));
    setResults(null);
    setSelected(null);
    setSuccess(null);
  }

  function selectRoom(item: AvailabilityResult) {
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
      setError("Не удалось проверить наличие. Попробуйте ещё раз или свяжитесь с менеджером.");
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
      setSuccess(`Заявка ${payload.id.slice(0, 8).toUpperCase()} принята. Менеджер свяжется с вами для согласования деталей и предоплаты.`);
      setGuestName("");
      setPhone("");
      setEmail("");
      setSelected(null);
    } catch {
      setError("Не удалось отправить заявку. Повторите отправку или свяжитесь с менеджером по телефону.");
    } finally {
      setSending(false);
    }
  }

  return (
    <section className="booking-shell" id="booking" aria-label="Поиск свободных номеров">
      <form className="booking-bar" onSubmit={findRooms}>
        <label className="booking-field"><span>Заезд</span><input type="date" min={today()} value={search.checkIn} onChange={(event) => changeCheckIn(event.target.value)} required /></label>
        <label className="booking-field"><span>Выезд</span><input type="date" min={addDays(search.checkIn || today(), 1)} value={search.checkOut} onChange={(event) => { setSearch({ ...search, checkOut: event.target.value }); setResults(null); setSelected(null); setSuccess(null); }} required /></label>
        <label className="booking-field"><span>Взрослые</span><select value={search.adults} onChange={(event) => { setSearch({ ...search, adults: Number(event.target.value) }); setResults(null); setSelected(null); }}>{[1,2,3,4,5,6].map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
        <label className="booking-field"><span>Дети</span><select value={search.children} onChange={(event) => { setSearch({ ...search, children: Number(event.target.value) }); setResults(null); setSelected(null); }}>{[0,1,2,3,4].map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
        <button className="search-button" disabled={loading}>{loading ? "Проверяем…" : "Найти номер"}</button>
      </form>

      <div aria-live="polite">
        {error && <div className="booking-notice error">{error}</div>}
        {success && <div className="booking-notice success">{success}<strong> Заявка ещё не является подтверждённой бронью.</strong></div>}
      </div>

      {results && (
        <div className="availability" id="availability">
          <div className="availability-head">
            <div><span className="eyebrow dark">Свободные варианты</span><h2>{results.nights} {results.nights === 1 ? "ночь" : "ночей"}</h2></div>
            <p>{results.check_in} → {results.check_out} · {results.adults} взр.{results.children ? ` · ${results.children} дет.` : ""}</p>
          </div>

          {sortedResults.length === 0 ? (
            <div className="no-results"><strong>На выбранные даты подходящих свободных номеров не найдено.</strong><span>Попробуйте соседние даты или свяжитесь с менеджером: </span><a href="tel:+996558085002">+996 558 08 50 02</a></div>
          ) : (
            <div className="availability-grid">
              {sortedResults.map((item) => {
                const meal = mealLabel(item.pricing.nights);
                const isSelected = selected?.room_type_id === item.room_type_id;
                return <article className={`availability-card ${isSelected ? "selected" : ""}`} key={item.room_type_id}>
                  <div>
                    <span className="availability-count">Свободно: {item.available_count}</span>
                    <h3>{item.room_type_name}</h3>
                    <p>{item.capacity_adults} осн. мест{item.area ? ` · ${item.area} м²` : ""}</p>
                  </div>
                  <div className="availability-price">
                    {item.pricing.sellable && item.pricing.total_kgs !== null ? <><strong>{money(item.pricing.total_kgs)} сом</strong><small>за весь период{meal ? ` · ${meal}` : ""}</small></> : <><strong>По запросу</strong><small>тариф требует подтверждения менеджером</small></>}
                  </div>
                  <button className={isSelected ? "primary-button" : "outline-button"} onClick={() => selectRoom(item)} type="button">{item.pricing.sellable ? (isSelected ? "Выбрано" : "Оставить заявку") : "Уточнить у менеджера"}</button>
                </article>;
              })}
            </div>
          )}

          {selected && (
            <form className="request-form" id="request-form" onSubmit={sendRequest}>
              <div className="request-title"><span className="eyebrow dark">Заявка менеджеру</span><h3>{selected.room_type_name}</h3><p>Передадим выбранные даты и категорию менеджеру. Он свяжется с вами и согласует дальнейшие условия бронирования и предоплаты.</p></div>
              <label><span>Имя</span><input value={guestName} onChange={(event) => setGuestName(event.target.value)} minLength={2} required placeholder="Как к вам обращаться" autoComplete="name" /></label>
              <label><span>Телефон</span><input value={phone} onChange={(event) => setPhone(event.target.value)} minLength={5} required placeholder="+996 …" autoComplete="tel" inputMode="tel" /></label>
              <label><span>Email, если нужен</span><input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="name@example.com" autoComplete="email" /></label>
              <button className="primary-button" disabled={sending}>{sending ? "Отправляем…" : "Отправить заявку"}</button>
              <small className="request-disclaimer">Отправка заявки не блокирует номер автоматически. Подтверждение брони делает менеджер.</small>
            </form>
          )}
        </div>
      )}
    </section>
  );
}
