"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { formatPublicDate, formatPublicNumber, localizeRoomTypeName, localeIntl, PublicLocale, resolveClientLocale } from "../lib/publicLocale";
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

const COPY = {
  ru: {
    eyebrow: "Проверка наличия", title: "Найдите номер на ваши даты", live: "Наличие и стоимость обновляются из системы отеля",
    checkIn: "Заезд", checkOut: "Выезд", adults: "Взрослые", children: "Дети", checking: "Проверяем…", find: "Найти номер",
    dateError: "Проверьте даты заезда и выезда.", searchError: "Не удалось проверить наличие. Попробуйте ещё раз или свяжитесь с менеджером.",
    submitError: "Не удалось отправить заявку. Повторите отправку или свяжитесь с менеджером по телефону.",
    success: (id: string) => `Заявка ${id} принята. Менеджер свяжется с вами для согласования условий и предоплаты.`,
    notReservation: "Заявка ещё не является подтверждённой бронью.", available: "Свободные варианты", childConfirm: "детские места — по подтверждению менеджера",
    noRooms: "На выбранные даты подходящих свободных номеров не найдено.", tryDates: "Попробуйте соседние даты или позвоните в бронирование.",
    free: "Свободно", yourDates: "На ваши даты", childrenReview: "детские места уточняются", fullPeriod: "за весь период", onRequest: "По запросу", managerPrice: "стоимость подтвердит менеджер",
    selected: "Выбрано", request: "Оставить заявку", askManager: "Уточнить у менеджера", requestEyebrow: "Заявка менеджеру", requestIntro: "Передадим выбранные даты и категорию. Менеджер согласует условия и предоплату.",
    name: "Имя", namePlaceholder: "Как к вам обращаться", phone: "Телефон", email: "Email, если нужен", sending: "Отправляем…", send: "Отправить заявку",
    disclaimer: "Отправка заявки не блокирует номер автоматически. Подтверждение брони делает менеджер после согласования условий и предоплаты.",
    breakfast: "Завтрак включён", noMeal: "Без питания", mixedMeal: "Условия питания меняются по датам", currency: "сом",
  },
  kg: {
    eyebrow: "Бош орундарды текшерүү", title: "Даталарыңызга ылайык номер табыңыз", live: "Бош орундар жана баа мейманкананын системасынан жаңыланат",
    checkIn: "Келүү", checkOut: "Кетүү", adults: "Чоңдор", children: "Балдар", checking: "Текшерилүүдө…", find: "Номер табуу",
    dateError: "Келүү жана кетүү даталарын текшериңиз.", searchError: "Бош орундарды текшерүү мүмкүн болгон жок. Кайра аракет кылыңыз же менеджер менен байланышыңыз.",
    submitError: "Өтүнмө жөнөтүлгөн жок. Кайра аракет кылыңыз же менеджерге чалыңыз.",
    success: (id: string) => `Өтүнмө ${id} кабыл алынды. Менеджер шарттарды жана алдын ала төлөмдү макулдашуу үчүн сиз менен байланышат.`,
    notReservation: "Өтүнмө азырынча ырасталган бронь эмес.", available: "Бош варианттар", childConfirm: "балдардын орундары менеджердин ырастоосу менен",
    noRooms: "Тандалган даталарга ылайыктуу бош номерлер табылган жок.", tryDates: "Жакын даталарды текшериңиз же брондоо бөлүмүнө чалыңыз.",
    free: "Бош", yourDates: "Сиздин даталарга", childrenReview: "балдардын орундары такталат", fullPeriod: "бүт мезгил үчүн", onRequest: "Суроо боюнча", managerPrice: "бааны менеджер ырастайт",
    selected: "Тандалды", request: "Өтүнмө калтыруу", askManager: "Менеджерден тактоо", requestEyebrow: "Менеджерге өтүнмө", requestIntro: "Тандалган даталарды жана категорияны өткөрүп беребиз. Менеджер шарттарды жана алдын ала төлөмдү макулдашат.",
    name: "Аты-жөнү", namePlaceholder: "Сизге кантип кайрылалы", phone: "Телефон", email: "Email, керек болсо", sending: "Жөнөтүлүүдө…", send: "Өтүнмө жөнөтүү",
    disclaimer: "Өтүнмө жөнөтүү номерди автоматтык түрдө кармабайт. Бронду менеджер шарттар жана алдын ала төлөм макулдашылгандан кийин ырастайт.",
    breakfast: "Эртең мененки тамак кирет", noMeal: "Тамак-ашсыз", mixedMeal: "Тамактануу шарттары даталарга жараша өзгөрөт", currency: "сом",
  },
  en: {
    eyebrow: "Live availability", title: "Find a room for your dates", live: "Availability and pricing are updated from the hotel system",
    checkIn: "Check-in", checkOut: "Check-out", adults: "Adults", children: "Children", checking: "Checking…", find: "Find a room",
    dateError: "Please check your arrival and departure dates.", searchError: "We could not check availability. Please try again or contact the manager.",
    submitError: "We could not send the request. Please try again or call the manager.",
    success: (id: string) => `Request ${id} has been received. A manager will contact you to agree the terms and prepayment.`,
    notReservation: "The request is not yet a confirmed reservation.", available: "Available options", childConfirm: "children’s places require manager confirmation",
    noRooms: "No suitable available rooms were found for the selected dates.", tryDates: "Try nearby dates or call reservations.",
    free: "Available", yourDates: "For your dates", childrenReview: "children’s places to be confirmed", fullPeriod: "for the full stay", onRequest: "On request", managerPrice: "price will be confirmed by the manager",
    selected: "Selected", request: "Send request", askManager: "Ask the manager", requestEyebrow: "Request to manager", requestIntro: "We will pass on your selected dates and category. The manager will agree the terms and prepayment.",
    name: "Name", namePlaceholder: "How should we address you?", phone: "Phone", email: "Email, optional", sending: "Sending…", send: "Send request",
    disclaimer: "Submitting a request does not automatically hold a room. A manager confirms the reservation after the terms and prepayment are agreed.",
    breakfast: "Breakfast included", noMeal: "No meals", mixedMeal: "Meal terms vary by date", currency: "KGS",
  },
};

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

function nightsLabel(value: number, locale: PublicLocale) {
  if (locale === "en") return `${value} ${value === 1 ? "night" : "nights"}`;
  if (locale === "kg") return `${value} түн`;
  const mod10 = value % 10;
  const mod100 = value % 100;
  if (mod10 === 1 && mod100 !== 11) return `${value} ночь`;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return `${value} ночи`;
  return `${value} ночей`;
}
function adultsLabel(value: number, locale: PublicLocale) {
  if (locale === "en") return `${value} ${value === 1 ? "adult" : "adults"}`;
  if (locale === "kg") return `${value} чоң киши`;
  return value === 1 ? "1 взрослый" : `${value} взрослых`;
}
function childrenLabel(value: number, locale: PublicLocale) {
  if (locale === "en") return `${value} ${value === 1 ? "child" : "children"}`;
  if (locale === "kg") return `${value} бала`;
  if (value === 1) return "1 ребёнок";
  if (value >= 2 && value <= 4) return `${value} ребёнка`;
  return `${value} детей`;
}
function mealLabel(nights: PricingNight[], locale: PublicLocale) {
  const values = Array.from(new Set(nights.map((night) => night.meal_included).filter(Boolean)));
  const c = COPY[locale];
  if (values.length !== 1) return values.length > 1 ? c.mixedMeal : null;
  if (values[0] === "BREAKFAST") return c.breakfast;
  if (values[0] === "NONE") return c.noMeal;
  return null;
}
function priceSortValue(item: AvailabilityResult) {
  return !item.pricing.sellable || item.pricing.total_kgs == null ? Number.MAX_SAFE_INTEGER : item.pricing.total_kgs;
}

export default function BookingWidget() {
  const [locale, setLocale] = useState<PublicLocale>("ru");
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
  const c = COPY[locale];

  useEffect(() => {
    const initial = localIsoDate();
    setMinimumDate(initial);
    setSearch({ checkIn: initial, checkOut: addDays(initial, 2), adults: 2, children: 0 });
  }, []);

  useEffect(() => {
    const updateLocale = () => setLocale(resolveClientLocale());
    updateLocale();
    window.addEventListener("three-crowns:content-ready", updateLocale);
    return () => window.removeEventListener("three-crowns:content-ready", updateLocale);
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
      return localizeRoomTypeName(left.room_type_name, locale).localeCompare(localizeRoomTypeName(right.room_type_name, locale), localeIntl[locale]);
    });
  }, [results, locale]);

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
      setError(c.dateError);
      return;
    }

    trackPublicEvent("booking_search_started", { adults: search.adults, children: search.children });
    setLoading(true);
    setResults(null);

    try {
      const params = new URLSearchParams({ check_in: search.checkIn, check_out: search.checkOut, adults: String(search.adults), children: String(search.children) });
      const response = await fetch(`/core/api/v1/booking/check-availability?${params}`, { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = (await response.json()) as AvailabilityResponse;
      setResults(payload);
      trackPublicEvent("booking_search_succeeded", {
        nights: payload.nights, adults: payload.adults, children: payload.children, room_type_count: payload.results.length,
        available_room_count: payload.results.reduce((sum, item) => sum + item.available_count, 0), sellable_type_count: payload.results.filter((item) => item.pricing.sellable).length,
      });
      requestAnimationFrame(() => document.getElementById("availability")?.scrollIntoView({ behavior: "smooth", block: "start" }));
    } catch {
      trackPublicEvent("booking_search_failed", { adults: search.adults, children: search.children });
      setError(c.searchError);
    } finally {
      setLoading(false);
    }
  }

  async function sendRequest(event: FormEvent) {
    event.preventDefault();
    if (!selected || !results) return;

    const analyticsPayload = { room_type_code: selected.room_type_code, nights: results.nights, adults: results.adults, children: results.children, quoted_total_kgs: selected.pricing.total_kgs };
    trackPublicEvent("booking_request_started", analyticsPayload);
    setSending(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await fetch("/core/api/v1/booking/requests", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          guest_name: guestName.trim(), phone: phone.trim(), email: email.trim() || null,
          check_in: results.check_in, check_out: results.check_out, adults: results.adults, children: results.children,
          room_type_code: selected.room_type_code, source: "WEB",
        }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = body as { id: string };
      trackPublicEvent("booking_request_succeeded", analyticsPayload);
      setSuccess(c.success(payload.id.slice(0, 8).toUpperCase()));
      setGuestName(""); setPhone(""); setEmail(""); setSelected(null);
    } catch {
      trackPublicEvent("booking_request_failed", analyticsPayload);
      setError(c.submitError);
    } finally {
      setSending(false);
    }
  }

  return (
    <section className="booking-shell" id="booking" aria-labelledby="booking-title" aria-busy={loading || sending}>
      <div className="booking-intro">
        <div><p className="eyebrow">{c.eyebrow}</p><h2 id="booking-title">{c.title}</h2></div>
        <p><span className="live-dot" aria-hidden="true" /> {c.live}</p>
      </div>

      <form className="booking-bar" onSubmit={findRooms}>
        <label className="booking-field"><span>{c.checkIn}</span><input type="date" min={minimumDate || undefined} value={search.checkIn} onChange={(event) => changeCheckIn(event.target.value)} required /></label>
        <label className="booking-field"><span>{c.checkOut}</span><input type="date" min={search.checkIn ? addDays(search.checkIn, 1) : minimumDate || undefined} value={search.checkOut} onChange={(event) => { setSearch({ ...search, checkOut: event.target.value }); resetResultState(); }} required /></label>
        <label className="booking-field"><span>{c.adults}</span><select value={search.adults} onChange={(event) => { setSearch({ ...search, adults: Number(event.target.value) }); resetResultState(); }}>{[1, 2, 3, 4].map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
        <label className="booking-field"><span>{c.children}</span><select value={search.children} onChange={(event) => { setSearch({ ...search, children: Number(event.target.value) }); resetResultState(); }}>{[0, 1, 2, 3, 4].map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
        <button className="search-button" type="submit" disabled={loading || !validDates}>{loading ? c.checking : c.find}</button>
      </form>

      <div className="booking-feedback" aria-live="polite" aria-atomic="true">
        {error && <div className="booking-notice error" role="alert">{error}</div>}
        {success && <div className="booking-notice success" role="status">{success}<strong>{c.notReservation}</strong></div>}
      </div>

      {results && <div className="availability" id="availability">
        <div className="availability-head">
          <div><p className="eyebrow">{c.available}</p><h2>{nightsLabel(results.nights, locale)}</h2></div>
          <p>{formatPublicDate(results.check_in, locale)} → {formatPublicDate(results.check_out, locale)} · {adultsLabel(results.adults, locale)}{results.children ? ` · ${childrenLabel(results.children, locale)} · ${c.childConfirm}` : ""}</p>
        </div>

        {sortedResults.length === 0
          ? <div className="no-results"><strong>{c.noRooms}</strong><span>{c.tryDates}</span><a href="tel:+996558085002">+996 558 08 50 02</a></div>
          : <div className="availability-grid">{sortedResults.map((item) => {
              const meal = mealLabel(item.pricing.nights, locale);
              const isSelected = selected?.room_type_id === item.room_type_id;
              const roomName = localizeRoomTypeName(item.room_type_name, locale);
              return <article className={`availability-card ${isSelected ? "selected" : ""}`} key={item.room_type_id}>
                <div className="availability-card-top"><span className="availability-count">{c.free}: {item.available_count}</span><span className="availability-code">{c.yourDates}</span></div>
                <h3>{roomName}</h3>
                <p className="availability-meta">{adultsLabel(item.capacity_adults, locale)}{item.area ? ` · ${item.area} м²` : ""}{results.children > 0 && !item.children_capacity_confirmed ? ` · ${c.childrenReview}` : ""}</p>
                <div className="availability-price">{item.pricing.sellable && item.pricing.total_kgs !== null
                  ? <><strong>{formatPublicNumber(item.pricing.total_kgs, locale)} {c.currency}</strong><small>{c.fullPeriod}{meal ? ` · ${meal}` : ""}</small></>
                  : <><strong>{c.onRequest}</strong><small>{c.managerPrice}</small></>}
                </div>
                <button className={isSelected ? "button button-dark" : "button button-outline"} onClick={() => selectRoom(item)} type="button" aria-pressed={isSelected}>{item.pricing.sellable ? (isSelected ? c.selected : c.request) : c.askManager}</button>
              </article>;
            })}</div>}

        {selected && <form className="request-form" id="request-form" onSubmit={sendRequest}>
          <div className="request-title"><p className="eyebrow">{c.requestEyebrow}</p><h3>{localizeRoomTypeName(selected.room_type_name, locale)}</h3><p>{c.requestIntro}</p></div>
          <label><span>{c.name}</span><input value={guestName} onChange={(event) => setGuestName(event.target.value)} minLength={2} required placeholder={c.namePlaceholder} autoComplete="name" /></label>
          <label><span>{c.phone}</span><input value={phone} onChange={(event) => setPhone(event.target.value)} minLength={5} required placeholder="+996 …" autoComplete="tel" inputMode="tel" /></label>
          <label><span>{c.email}</span><input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="name@example.com" autoComplete="email" /></label>
          <button className="button button-dark request-submit" type="submit" disabled={sending}>{sending ? c.sending : c.send}</button>
          <small className="request-disclaimer">{c.disclaimer}</small>
        </form>}
      </div>}
    </section>
  );
}
