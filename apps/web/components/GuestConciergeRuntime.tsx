"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type Locale = "ru" | "kg" | "en";
type RequestCode = "HOUSEKEEPING" | "TOWELS" | "LINEN" | "MAINTENANCE" | "TRANSFER" | "MEALS" | "PARKING" | "SAUNA" | "BILLIARDS" | "EXCURSIONS" | "ADMIN";
type RequestStatus = "OPEN" | "IN_PROGRESS" | "IN_INSPECTION" | "DONE" | "CANCELLED";

type GuestContext = {
  qr_valid: boolean;
  authenticated: boolean;
  verification_required: boolean;
  active_stay: boolean;
  room: { code: string; name: string; room_type_name: string };
  guest: { first_name: string } | null;
  stay: { check_in: string; check_out: string } | null;
};

type GuestRequest = {
  id: string;
  request_code: string;
  status: RequestStatus;
  description?: string | null;
  service_date?: string | null;
  service_time?: string | null;
  created_at: string;
};

type Service = { code: RequestCode; icon: string; title: string; note: string };

const STORAGE_KEY = "three-crowns-guest-language";
const SITE_STORAGE_KEY = "three-crowns-site-language";

const COPY = {
  ru: {
    property: "Три Короны",
    product: "Цифровой консьерж",
    language: "Язык",
    loading: "Открываем цифровой консьерж…",
    invalidTitle: "Код номера недоступен",
    invalidText: "Код не найден или был заменён. Обратитесь на ресепшен.",
    noStayTitle: "Номер готов к следующему заезду",
    noStayText: "Сейчас за этим номером нет активного проживания.",
    room: "Номер",
    verifyTitle: "Подтвердите проживание",
    verifyText: "Введите шестизначный код, который вы получили на ресепшене при заселении.",
    pin: "Код гостя",
    open: "Открыть кабинет",
    checking: "Проверяем…",
    wrong: "Код не подошёл. Проверьте цифры или обратитесь на ресепшен.",
    expired: "Срок действия кода закончился. Попросите ресепшен выдать новый код.",
    limited: "Слишком много попыток. Попробуйте позже или обратитесь на ресепшен.",
    error: "Не удалось загрузить кабинет. Проверьте соединение и попробуйте снова.",
    retry: "Повторить",
    hello: "Добро пожаловать",
    stay: "Ваше проживание",
    from: "с",
    to: "по",
    checkout: "Выезд до 12:00",
    quick: "Что нужно сейчас?",
    quickNote: "Большинство услуг можно запросить за несколько нажатий.",
    myRequests: "Мои заявки",
    noRequests: "Заявок пока нет.",
    refresh: "Обновить",
    newRequest: "Новая заявка",
    service: "Услуга",
    date: "Дата",
    time: "Время",
    comment: "Комментарий",
    commentPlaceholder: "Уточните детали, если нужно",
    send: "Отправить",
    sending: "Отправляем…",
    sent: "Заявка отправлена. Статус появится в разделе «Мои заявки».",
    cancel: "Отменить",
    close: "Закрыть",
    mealsTitle: "Питание",
    mealsNote: "Выберите приём пищи и количество гостей. Конкретное меню подтверждает столовая.",
    meal: "Приём пищи",
    breakfast: "Завтрак",
    lunch: "Обед",
    dinner: "Ужин",
    adults: "Взрослые",
    children: "Дети",
    estimated: "Расчёт по действующему прайсу",
    mealWarning: "Включённое в проживание питание определяется вашей бронью. Здесь показана стоимость дополнительного питания.",
    transferTitle: "Трансфер",
    origin: "Откуда",
    destination: "Куда",
    vehicle: "Автомобиль",
    sedan: "Седан",
    minivan: "Минивэн",
    manas: "Аэропорт Манас",
    tamchy: "Аэропорт Тамчы",
    bishkek: "Бишкек",
    hotel: "Три Короны",
    other: "Другое место",
    luggage: "Багаж / особые пожелания",
    serviceInfo: "После отправки сотрудник подтвердит доступность, время и окончательные условия.",
    rules: "Правила и информация",
    rulesText: "Заезд с 14:00. Выезд до 12:00. По вопросам проживания, услуг и безопасности обращайтесь на ресепшен.",
    contacts: "Связаться с отелем",
    call: "Позвонить на ресепшен",
    message: "Написать менеджеру",
    signOut: "Закрыть гостевой доступ",
    status: { OPEN: "Принято", IN_PROGRESS: "В работе", IN_INSPECTION: "На проверке", DONE: "Выполнено", CANCELLED: "Отменено" },
    services: {
      HOUSEKEEPING: ["Уборка", "Уборка номера в удобное время"],
      TOWELS: ["Полотенца", "Принести чистые полотенца"],
      LINEN: ["Бельё", "Замена постельного белья"],
      MAINTENANCE: ["Ремонт", "Сообщить о проблеме в номере"],
      MEALS: ["Питание", "Завтрак, обед или ужин"],
      TRANSFER: ["Трансфер", "Поездка в аэропорт или город"],
      SAUNA: ["Сауна", "Запросить удобное время"],
      BILLIARDS: ["Бильярд", "Запросить посещение"],
      EXCURSIONS: ["Экскурсии", "Подобрать и запросить поездку"],
      PARKING: ["Парковка", "Помощь с парковкой"],
      ADMIN: ["Помощь", "Связаться с администратором"],
    },
  },
  kg: {
    property: "Үч Таажы",
    product: "Санарип жардамчы",
    language: "Тил",
    loading: "Санарип жардамчы ачылууда…",
    invalidTitle: "Бөлмө коду жеткиликсиз",
    invalidText: "Код табылган жок же алмаштырылган. Ресепшенге кайрылыңыз.",
    noStayTitle: "Бөлмө кийинки конокко даяр",
    noStayText: "Азыр бул бөлмөдө активдүү жашоо жок.",
    room: "Бөлмө",
    verifyTitle: "Жашооңузду ырастаңыз",
    verifyText: "Катталууда ресепшенден алган алты орундуу кодду киргизиңиз.",
    pin: "Конок коду",
    open: "Кабинетти ачуу",
    checking: "Текшерилүүдө…",
    wrong: "Код туура эмес. Сандарды текшериңиз же ресепшенге кайрылыңыз.",
    expired: "Коддун мөөнөтү бүттү. Ресепшенден жаңы код сураңыз.",
    limited: "Аракеттер өтө көп болду. Кийин аракет кылыңыз же ресепшенге кайрылыңыз.",
    error: "Кабинет ачылган жок. Байланышты текшерип, кайра аракет кылыңыз.",
    retry: "Кайра аракет кылуу",
    hello: "Кош келиңиз",
    stay: "Сиздин жашооңуз",
    from: "баштап",
    to: "чейин",
    checkout: "Чыгуу саат 12:00гө чейин",
    quick: "Азыр эмне керек?",
    quickNote: "Көпчүлүк кызматтарды бир нече басуу менен сураса болот.",
    myRequests: "Менин өтүнмөлөрүм",
    noRequests: "Азырынча өтүнмөлөр жок.",
    refresh: "Жаңыртуу",
    newRequest: "Жаңы өтүнмө",
    service: "Кызмат",
    date: "Күн",
    time: "Убакыт",
    comment: "Комментарий",
    commentPlaceholder: "Керек болсо маалымат кошуңуз",
    send: "Жөнөтүү",
    sending: "Жөнөтүлүүдө…",
    sent: "Өтүнмө жөнөтүлдү. Абалы «Менин өтүнмөлөрүм» бөлүмүндө көрүнөт.",
    cancel: "Жокко чыгаруу",
    close: "Жабуу",
    mealsTitle: "Тамактануу",
    mealsNote: "Тамактануу убактысын жана коноктордун санын тандаңыз. Так менюну ашкана ырастайт.",
    meal: "Тамактануу",
    breakfast: "Эртең мененки тамак",
    lunch: "Түшкү тамак",
    dinner: "Кечки тамак",
    adults: "Чоңдор",
    children: "Балдар",
    estimated: "Учурдагы баа боюнча эсеп",
    mealWarning: "Жашоого кирген тамактануу сиздин бронуңуз боюнча аныкталат. Бул жерде кошумча тамактануунун баасы көрсөтүлөт.",
    transferTitle: "Трансфер",
    origin: "Кайдан",
    destination: "Кайда",
    vehicle: "Унаа",
    sedan: "Седан",
    minivan: "Минивэн",
    manas: "Манас аэропорту",
    tamchy: "Тамчы аэропорту",
    bishkek: "Бишкек",
    hotel: "Үч Таажы",
    other: "Башка жер",
    luggage: "Жүк / өзгөчө каалоо",
    serviceInfo: "Жөнөткөндөн кийин кызматкер жеткиликтүүлүктү, убакытты жана акыркы шарттарды ырастайт.",
    rules: "Эрежелер жана маалымат",
    rulesText: "Кирүү саат 14:00дөн. Чыгуу саат 12:00гө чейин. Жашоо, кызматтар жана коопсуздук боюнча ресепшенге кайрылыңыз.",
    contacts: "Мейманкана менен байланыш",
    call: "Ресепшенге чалуу",
    message: "Менеджерге жазуу",
    signOut: "Конок кирүүсүн жабуу",
    status: { OPEN: "Кабыл алынды", IN_PROGRESS: "Аткарылууда", IN_INSPECTION: "Текшерүүдө", DONE: "Аткарылды", CANCELLED: "Жокко чыгарылды" },
    services: {
      HOUSEKEEPING: ["Тазалоо", "Бөлмөнү ыңгайлуу убакта тазалоо"],
      TOWELS: ["Сүлгүлөр", "Таза сүлгү алып келүү"],
      LINEN: ["Төшөк жабдыгы", "Төшөк жабдыгын алмаштыруу"],
      MAINTENANCE: ["Оңдоо", "Бөлмөдөгү көйгөйдү билдирүү"],
      MEALS: ["Тамактануу", "Эртең мененки, түшкү же кечки тамак"],
      TRANSFER: ["Трансфер", "Аэропортко же шаарга баруу"],
      SAUNA: ["Сауна", "Ыңгайлуу убакытты суроо"],
      BILLIARDS: ["Бильярд", "Келүү убактысын суроо"],
      EXCURSIONS: ["Экскурсиялар", "Саякат тандоо жана өтүнмө берүү"],
      PARKING: ["Унаа токтотуу", "Унаа токтотууга жардам"],
      ADMIN: ["Жардам", "Администратор менен байланышуу"],
    },
  },
  en: {
    property: "Three Crowns",
    product: "Digital concierge",
    language: "Language",
    loading: "Opening your digital concierge…",
    invalidTitle: "Room code unavailable",
    invalidText: "This code was not found or has been replaced. Please contact reception.",
    noStayTitle: "Room ready for the next arrival",
    noStayText: "There is no active stay assigned to this room right now.",
    room: "Room",
    verifyTitle: "Confirm your stay",
    verifyText: "Enter the six-digit code issued by reception at check-in.",
    pin: "Guest code",
    open: "Open guest area",
    checking: "Checking…",
    wrong: "That code did not match. Check the digits or contact reception.",
    expired: "This code has expired. Ask reception for a new code.",
    limited: "Too many attempts. Try later or contact reception.",
    error: "The guest area could not be loaded. Check your connection and try again.",
    retry: "Try again",
    hello: "Welcome",
    stay: "Your stay",
    from: "from",
    to: "to",
    checkout: "Check-out by 12:00",
    quick: "What do you need now?",
    quickNote: "Most hotel services can be requested in just a few taps.",
    myRequests: "My requests",
    noRequests: "No requests yet.",
    refresh: "Refresh",
    newRequest: "New request",
    service: "Service",
    date: "Date",
    time: "Time",
    comment: "Comment",
    commentPlaceholder: "Add details if needed",
    send: "Send request",
    sending: "Sending…",
    sent: "Request sent. Its status will appear under My requests.",
    cancel: "Cancel",
    close: "Close",
    mealsTitle: "Dining",
    mealsNote: "Choose a meal and number of guests. The dining team confirms the actual menu.",
    meal: "Meal",
    breakfast: "Breakfast",
    lunch: "Lunch",
    dinner: "Dinner",
    adults: "Adults",
    children: "Children",
    estimated: "Estimate from the current price list",
    mealWarning: "Meal inclusion depends on your reservation. The prices shown here are for additional meals.",
    transferTitle: "Transfer",
    origin: "From",
    destination: "To",
    vehicle: "Vehicle",
    sedan: "Sedan",
    minivan: "Minivan",
    manas: "Manas Airport",
    tamchy: "Tamchy Airport",
    bishkek: "Bishkek",
    hotel: "Three Crowns",
    other: "Other location",
    luggage: "Luggage / special request",
    serviceInfo: "After submission, staff will confirm availability, timing and final conditions.",
    rules: "Rules and information",
    rulesText: "Check-in is from 14:00. Check-out is by 12:00. Contact reception for stay, service or safety questions.",
    contacts: "Contact the hotel",
    call: "Call reception",
    message: "Message manager",
    signOut: "Close guest access",
    status: { OPEN: "Received", IN_PROGRESS: "In progress", IN_INSPECTION: "Under review", DONE: "Completed", CANCELLED: "Cancelled" },
    services: {
      HOUSEKEEPING: ["Housekeeping", "Clean the room at a convenient time"],
      TOWELS: ["Towels", "Bring fresh towels"],
      LINEN: ["Bed linen", "Replace bed linen"],
      MAINTENANCE: ["Maintenance", "Report a room issue"],
      MEALS: ["Dining", "Breakfast, lunch or dinner"],
      TRANSFER: ["Transfer", "Airport or city transfer"],
      SAUNA: ["Sauna", "Request a convenient time"],
      BILLIARDS: ["Billiards", "Request a visit"],
      EXCURSIONS: ["Excursions", "Choose and request a trip"],
      PARKING: ["Parking", "Get parking assistance"],
      ADMIN: ["Help", "Contact an administrator"],
    },
  },
} as const;

const SERVICE_ORDER: RequestCode[] = ["MEALS", "HOUSEKEEPING", "TRANSFER", "MAINTENANCE", "SAUNA", "EXCURSIONS", "TOWELS", "LINEN", "BILLIARDS", "ADMIN"];
const SERVICE_ICONS: Record<RequestCode, string> = { MEALS: "🍽", HOUSEKEEPING: "✦", TRANSFER: "↗", MAINTENANCE: "⌁", SAUNA: "♨", EXCURSIONS: "⌖", TOWELS: "▤", LINEN: "▧", BILLIARDS: "●", PARKING: "P", ADMIN: "?" };

function initialLocale(): Locale {
  if (typeof window === "undefined") return "ru";
  const query = new URLSearchParams(window.location.search).get("lang");
  if (query === "ru" || query === "kg" || query === "en") return query;
  const local = window.localStorage.getItem(STORAGE_KEY) || window.localStorage.getItem(SITE_STORAGE_KEY);
  return local === "kg" || local === "en" ? local : "ru";
}

function dateLabel(value: string, locale: Locale) {
  const lang = locale === "kg" ? "ky-KG" : locale === "en" ? "en-GB" : "ru-RU";
  return new Date(`${value}T00:00:00`).toLocaleDateString(lang, { day: "numeric", month: "short" });
}

export default function GuestConciergeRuntime({ token }: { token: string }) {
  const [locale, setLocale] = useState<Locale>("ru");
  const [context, setContext] = useState<GuestContext | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "invalid" | "error">("loading");
  const [pin, setPin] = useState("");
  const [pinMessage, setPinMessage] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);
  const [requests, setRequests] = useState<GuestRequest[]>([]);
  const [selected, setSelected] = useState<RequestCode | null>(null);
  const [comment, setComment] = useState("");
  const [serviceDate, setServiceDate] = useState("");
  const [serviceTime, setServiceTime] = useState("");
  const [sending, setSending] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [meal, setMeal] = useState<"breakfast" | "lunch" | "dinner">("lunch");
  const [adults, setAdults] = useState(1);
  const [children, setChildren] = useState(0);
  const [origin, setOrigin] = useState("hotel");
  const [destination, setDestination] = useState("tamchy");
  const [vehicle, setVehicle] = useState("sedan");

  useEffect(() => setLocale(initialLocale()), []);
  const copy = COPY[locale];

  function chooseLocale(next: Locale) {
    setLocale(next);
    window.localStorage.setItem(STORAGE_KEY, next);
    window.localStorage.setItem(SITE_STORAGE_KEY, next);
    document.documentElement.lang = next === "kg" ? "ky" : next;
  }

  const loadContext = useCallback(async () => {
    try {
      const response = await fetch(`/core/api/v1/guest-os/rooms/${encodeURIComponent(token)}`, { credentials: "include", cache: "no-store" });
      if (response.status === 404) { setContext(null); setState("invalid"); return; }
      if (!response.ok) throw new Error();
      setContext(await response.json() as GuestContext);
      setState("ready");
    } catch { setContext(null); setState("error"); }
  }, [token]);

  const loadRequests = useCallback(async () => {
    try {
      const response = await fetch(`/core/api/v1/guest-os/rooms/${encodeURIComponent(token)}/requests`, { credentials: "include", cache: "no-store" });
      if (!response.ok) { setRequests([]); return; }
      const body = await response.json() as { items?: GuestRequest[] };
      setRequests(body.items ?? []);
    } catch { setRequests([]); }
  }, [token]);

  useEffect(() => { void loadContext(); }, [loadContext]);
  useEffect(() => {
    if (!context?.authenticated) return;
    void loadRequests();
    const timer = window.setInterval(() => void loadRequests(), 15000);
    return () => window.clearInterval(timer);
  }, [context?.authenticated, loadRequests]);

  async function verify(event: FormEvent) {
    event.preventDefault();
    if (!/^\d{6}$/.test(pin)) return;
    setChecking(true); setPinMessage(null);
    try {
      const response = await fetch(`/core/api/v1/guest-os/rooms/${encodeURIComponent(token)}/verify`, { method: "POST", credentials: "include", headers: { "content-type": "application/json" }, body: JSON.stringify({ pin }) });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        const code = body?.detail?.code;
        setPinMessage(code === "PIN_EXPIRED" ? copy.expired : code === "PIN_RATE_LIMIT" ? copy.limited : copy.wrong);
        return;
      }
      setPin(""); await loadContext();
    } catch { setPinMessage(copy.error); }
    finally { setChecking(false); }
  }

  function mealPrice() {
    const adult = meal === "breakfast" ? 500 : meal === "lunch" ? 750 : 650;
    const child = meal === "breakfast" ? 400 : meal === "lunch" ? 550 : 450;
    return adult * adults + child * children;
  }

  function descriptionFor(code: RequestCode) {
    if (code === "MEALS") {
      const mealName = copy[meal];
      return `${mealName}; ${copy.adults}: ${adults}; ${copy.children}: ${children}${comment.trim() ? `; ${copy.comment}: ${comment.trim()}` : ""}`;
    }
    if (code === "TRANSFER") {
      const from = copy[origin as "hotel" | "manas" | "tamchy" | "bishkek" | "other"];
      const to = copy[destination as "hotel" | "manas" | "tamchy" | "bishkek" | "other"];
      const car = vehicle === "minivan" ? copy.minivan : copy.sedan;
      return `${copy.origin}: ${from}; ${copy.destination}: ${to}; ${copy.vehicle}: ${car}${comment.trim() ? `; ${copy.luggage}: ${comment.trim()}` : ""}`;
    }
    return comment.trim() || null;
  }

  async function sendRequest(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    setSending(true); setNotice(null);
    try {
      const response = await fetch(`/core/api/v1/guest-os/rooms/${encodeURIComponent(token)}/requests`, {
        method: "POST", credentials: "include", headers: { "content-type": "application/json" },
        body: JSON.stringify({ request_code: selected, description: descriptionFor(selected), service_date: serviceDate || null, service_time: serviceTime || null }),
      });
      if (!response.ok) throw new Error();
      setNotice(copy.sent); setComment(""); setServiceDate(""); setServiceTime("");
      await loadRequests();
    } catch { setNotice(copy.error); }
    finally { setSending(false); }
  }

  async function cancelRequest(id: string) {
    const response = await fetch(`/core/api/v1/guest-os/rooms/${encodeURIComponent(token)}/requests/${id}/cancel`, { method: "POST", credentials: "include" }).catch(() => null);
    if (response?.ok) await loadRequests();
  }

  async function logout() {
    await fetch("/core/api/v1/guest-os/logout", { method: "POST", credentials: "include" }).catch(() => null);
    setContext(null); setRequests([]); await loadContext();
  }

  const services: Service[] = useMemo(() => SERVICE_ORDER.map((code) => ({ code, icon: SERVICE_ICONS[code], title: copy.services[code][0], note: copy.services[code][1] })), [copy]);

  return <main className="concierge-page">
    <header className="concierge-topbar">
      <div className="concierge-brand"><span>III</span><div><strong>{copy.property}</strong><small>{copy.product}</small></div></div>
      <div className="concierge-langs" aria-label={copy.language}>{(["ru", "kg", "en"] as Locale[]).map((item) => <button key={item} onClick={() => chooseLocale(item)} aria-pressed={locale === item}>{item.toUpperCase()}</button>)}</div>
    </header>

    {state === "loading" && <section className="concierge-state">{copy.loading}</section>}
    {state === "invalid" && <section className="concierge-state"><h1>{copy.invalidTitle}</h1><p>{copy.invalidText}</p></section>}
    {state === "error" && <section className="concierge-state"><h1>{copy.error}</h1><button onClick={() => void loadContext()}>{copy.retry}</button></section>}

    {state === "ready" && context && !context.active_stay && <section className="concierge-state"><p>{copy.room} {context.room.code}</p><h1>{copy.noStayTitle}</h1><p>{copy.noStayText}</p></section>}

    {state === "ready" && context?.active_stay && !context.authenticated && <section className="concierge-auth">
      <span className="concierge-room-chip">{copy.room} {context.room.code}</span>
      <h1>{copy.verifyTitle}</h1><p>{copy.verifyText}</p>
      <form onSubmit={verify}><label>{copy.pin}<input inputMode="numeric" autoComplete="one-time-code" maxLength={6} value={pin} onChange={(e) => setPin(e.target.value.replace(/\D/g, "").slice(0, 6))} placeholder="••••••" /></label>{pinMessage && <div className="concierge-error">{pinMessage}</div>}<button disabled={checking || pin.length !== 6}>{checking ? copy.checking : copy.open}</button></form>
    </section>}

    {state === "ready" && context?.authenticated && context.stay && <>
      <section className="concierge-hero">
        <div><p>{copy.hello}{context.guest?.first_name ? `, ${context.guest.first_name}` : ""}</p><h1>{copy.room} {context.room.code}</h1></div>
        <div className="concierge-stay"><strong>{copy.stay}</strong><span>{dateLabel(context.stay.check_in, locale)} — {dateLabel(context.stay.check_out, locale)}</span><small>{copy.checkout}</small></div>
      </section>

      <section className="concierge-section"><div className="concierge-heading"><div><h2>{copy.quick}</h2><p>{copy.quickNote}</p></div></div><div className="concierge-actions">{services.slice(0, 6).map((service) => <button key={service.code} onClick={() => { setSelected(service.code); setNotice(null); }}><span>{service.icon}</span><strong>{service.title}</strong><small>{service.note}</small></button>)}</div></section>

      <section className="concierge-section concierge-requests"><div className="concierge-heading"><h2>{copy.myRequests}</h2><button onClick={() => void loadRequests()}>{copy.refresh}</button></div>{!requests.length ? <p className="concierge-empty">{copy.noRequests}</p> : <div className="concierge-request-list">{requests.map((item) => { const code = (SERVICE_ORDER.includes(item.request_code as RequestCode) || item.request_code === "PARKING" ? item.request_code : "ADMIN") as RequestCode; return <article key={item.id}><div><strong>{copy.services[code][0]}</strong><span data-status={item.status}>{copy.status[item.status]}</span></div>{item.description && <p>{item.description}</p>} {item.status === "OPEN" && <button onClick={() => void cancelRequest(item.id)}>{copy.cancel}</button>}</article>; })}</div>}</section>

      <section className="concierge-section"><div className="concierge-heading"><h2>{copy.rules}</h2></div><div className="concierge-info-grid"><article><p>{copy.rulesText}</p></article><article><h3>{copy.contacts}</h3><a href="tel:+996558085002">{copy.call}</a><a href="https://wa.me/996558085008" target="_blank" rel="noreferrer">{copy.message}</a></article></div></section>
      <button className="concierge-signout" onClick={() => void logout()}>{copy.signOut}</button>
    </>}

    {selected && <div className="concierge-modal-backdrop" role="presentation" onMouseDown={(e) => { if (e.target === e.currentTarget) setSelected(null); }}><section className="concierge-modal" role="dialog" aria-modal="true"><div className="concierge-modal-head"><div><small>{copy.newRequest}</small><h2>{selected === "MEALS" ? copy.mealsTitle : selected === "TRANSFER" ? copy.transferTitle : copy.services[selected][0]}</h2></div><button onClick={() => setSelected(null)} aria-label={copy.close}>×</button></div><p>{selected === "MEALS" ? copy.mealsNote : selected === "TRANSFER" ? copy.serviceInfo : copy.services[selected][1]}</p><form onSubmit={sendRequest}>
      {selected === "MEALS" && <><label>{copy.meal}<select value={meal} onChange={(e) => setMeal(e.target.value as typeof meal)}><option value="breakfast">{copy.breakfast}</option><option value="lunch">{copy.lunch}</option><option value="dinner">{copy.dinner}</option></select></label><div className="concierge-two"><label>{copy.adults}<input type="number" min="0" max="10" value={adults} onChange={(e) => setAdults(Number(e.target.value))} /></label><label>{copy.children}<input type="number" min="0" max="10" value={children} onChange={(e) => setChildren(Number(e.target.value))} /></label></div><div className="concierge-estimate"><span>{copy.estimated}</span><strong>{mealPrice().toLocaleString()} сом</strong><small>{copy.mealWarning}</small></div></>}
      {selected === "TRANSFER" && <><div className="concierge-two"><label>{copy.origin}<select value={origin} onChange={(e) => setOrigin(e.target.value)}><option value="hotel">{copy.hotel}</option><option value="manas">{copy.manas}</option><option value="tamchy">{copy.tamchy}</option><option value="bishkek">{copy.bishkek}</option><option value="other">{copy.other}</option></select></label><label>{copy.destination}<select value={destination} onChange={(e) => setDestination(e.target.value)}><option value="hotel">{copy.hotel}</option><option value="manas">{copy.manas}</option><option value="tamchy">{copy.tamchy}</option><option value="bishkek">{copy.bishkek}</option><option value="other">{copy.other}</option></select></label></div><label>{copy.vehicle}<select value={vehicle} onChange={(e) => setVehicle(e.target.value)}><option value="sedan">{copy.sedan}</option><option value="minivan">{copy.minivan}</option></select></label></>}
      <div className="concierge-two"><label>{copy.date}<input type="date" value={serviceDate} onChange={(e) => setServiceDate(e.target.value)} /></label><label>{copy.time}<input type="time" value={serviceTime} onChange={(e) => setServiceTime(e.target.value)} /></label></div><label>{selected === "TRANSFER" ? copy.luggage : copy.comment}<textarea value={comment} onChange={(e) => setComment(e.target.value)} placeholder={copy.commentPlaceholder} maxLength={1200} /></label>{notice && <div className="concierge-notice">{notice}</div>}<button className="concierge-submit" disabled={sending}>{sending ? copy.sending : copy.send}</button></form></section></div>}
  </main>;
}
