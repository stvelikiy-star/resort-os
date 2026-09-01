"use client";

import { useEffect, useMemo, useState } from "react";

type Locale = "ru" | "kg" | "en";

type PinPayload = {
  reservation_id?: string;
  stay_id?: string;
  room_code?: string;
  guest_access_pin: string;
  guest_access_pin_valid_for_hours?: number;
  guest_access_pin_display_once?: boolean;
};

type Phrase = { ru: string; kg: string; en: string };

const STORAGE_KEY = "three-crowns-admin-locale";

const exact: Record<string, Phrase> = {
  "OWNER OPERATIONS · MTD": { ru: "ОПЕРАЦИИ ВЛАДЕЛЬЦА · С НАЧАЛА МЕСЯЦА", kg: "ЭЭСИНИН ОПЕРАЦИЯЛАРЫ · АЙ БАШЫНАН", en: "OWNER OPERATIONS · MONTH TO DATE" },
  "GUEST SERVICES · СОЗДАНО": { ru: "СЕРВИС ГОСТЕЙ · СОЗДАНО", kg: "КОНок СЕРВИСИ · ТҮЗҮЛДҮ", en: "GUEST SERVICES · CREATED" },
  "GUEST SERVICES · АКТИВНЫЕ": { ru: "СЕРВИС ГОСТЕЙ · АКТИВНЫЕ", kg: "КОНок СЕРВИСИ · АКТИВДҮҮ", en: "GUEST SERVICES · ACTIVE" },
  "СРЕДНЕЕ ЗАКРЫТИЕ GUEST SERVICES": { ru: "СРЕДНЕЕ ВРЕМЯ ЗАКРЫТИЯ СЕРВИСНЫХ ЗАЯВОК", kg: "СЕРВИСТИК ӨТҮНМДӨРДҮ ЖАБУУНУН ОРТОЧО УБАКТЫСЫ", en: "AVERAGE GUEST SERVICE CLOSE TIME" },
  "SLA GUEST SERVICES": { ru: "SLA СЕРВИСА ГОСТЕЙ", kg: "КОНок СЕРВИСИНИН SLA КӨРСӨТКҮЧҮ", en: "GUEST SERVICES SLA" },
  "HOUSEKEEPING · ЗАВЕРШЕНО": { ru: "УБОРКА · ЗАВЕРШЕНО", kg: "ТАЗАЛОО · БҮТТҮ", en: "HOUSEKEEPING · COMPLETED" },
  "HOUSEKEEPING · СРОЧНО": { ru: "УБОРКА · СРОЧНО", kg: "ТАЗАЛОО · ШАШЫЛЫШ", en: "HOUSEKEEPING · URGENT" },
  "MAINTENANCE · ЗАВЕРШЕНО": { ru: "РЕМОНТ · ЗАВЕРШЕНО", kg: "ОҢДОО · БҮТТҮ", en: "MAINTENANCE · COMPLETED" },
  "NOT_CONFIGURED": { ru: "НЕ НАСТРОЕНО", kg: "ЖӨНДӨЛГӨН ЭМЕС", en: "NOT CONFIGURED" },
  "PMS_SCHEDULE_MUTATION": { ru: "ИЗМЕНЕНИЕ ГРАФИКА В PMS", kg: "PMS ГРАФИГИН ӨЗГӨРТҮҮ", en: "PMS SCHEDULE CHANGE" },
  "MANAGER_CREATE_RESERVATION_FROM_GRID": { ru: "МЕНЕДЖЕР СОЗДАЛ БРОНЬ ИЗ ШАХМАТКИ", kg: "МЕНЕДЖЕР ШАХМАТКАДАН БРОНЬ ТҮЗДҮ", en: "MANAGER CREATED RESERVATION FROM GRID" },
  "CHECK_IN": { ru: "ЗАЕЗД", kg: "КИРҮҮ", en: "CHECK-IN" },
  "CHECK_OUT": { ru: "ВЫЕЗД", kg: "ЧЫГУУ", en: "CHECK-OUT" },
  "GUEST_PIN_REISSUE": { ru: "ПЕРЕВЫДАЧА КОДА GUEST OS", kg: "GUEST OS КОДУН КАЙРА БЕРҮҮ", en: "GUEST OS PIN REISSUED" },
  "HOUSEKEEPING": { ru: "УБОРКА", kg: "ТАЗАЛОО", en: "HOUSEKEEPING" },
  "MAINTENANCE": { ru: "РЕМОНТ", kg: "ОҢДОО", en: "MAINTENANCE" },
  "DONE": { ru: "ЗАВЕРШЕНО", kg: "БҮТТҮ", en: "DONE" },
  "IN_PROGRESS": { ru: "В РАБОТЕ", kg: "АТКАРЫЛУУДА", en: "IN PROGRESS" },
  "IN_INSPECTION": { ru: "НА ПРОВЕРКЕ", kg: "ТЕКШЕРҮҮДӨ", en: "IN INSPECTION" },
  "CLEAN": { ru: "ГОТОВ", kg: "ДАЯР", en: "CLEAN" },
  "DIRTY": { ru: "НУЖНА УБОРКА", kg: "ТАЗАЛОО КЕРЕК", en: "DIRTY" },
  "TECH_BLOCK": { ru: "ТЕХНИЧЕСКАЯ БЛОКИРОВКА", kg: "ТЕХНИКАЛЫК БЛОК", en: "TECH BLOCK" },
  "UNKNOWN": { ru: "НЕ УКАЗАНО", kg: "КӨРСӨТҮЛГӨН ЭМЕС", en: "UNKNOWN" },
  "SUCCESS": { ru: "УСПЕШНО", kg: "ИЙГИЛИКТҮҮ", en: "SUCCESS" },
  "NORMAL": { ru: "ОБЫЧНЫЙ", kg: "КАДИМКИ", en: "NORMAL" },
  "URGENT": { ru: "СРОЧНО", kg: "ШАШЫЛЫШ", en: "URGENT" },
  "HIGH": { ru: "ВЫСОКИЙ", kg: "ЖОГОРКУ", en: "HIGH" },
  "LOW": { ru: "НИЗКИЙ", kg: "ТӨМӨН", en: "LOW" },
  "ACTIVE": { ru: "АКТИВНО", kg: "АКТИВДҮҮ", en: "ACTIVE" },
  "GUARANTEED": { ru: "ГАРАНТИРОВАНА", kg: "КЕПИЛДЕНГЕН", en: "GUARANTEED" },
  "CHECKED_IN": { ru: "ПРОЖИВАЕТ", kg: "ЖАШАП ЖАТАТ", en: "CHECKED IN" },
  "CHECKED_OUT": { ru: "ВЫЕХАЛ", kg: "ЧЫГЫП КЕТТИ", en: "CHECKED OUT" },
  "CANCELLED": { ru: "ОТМЕНЕНО", kg: "ЖОККО ЧЫГАРЫЛДЫ", en: "CANCELLED" },
  "NO_SHOW": { ru: "НЕ ЗАЕХАЛ", kg: "КЕЛГЕН ЖОК", en: "NO SHOW" },
  "OWNER": { ru: "ВЛАДЕЛЕЦ", kg: "ЭЭСИ", en: "OWNER" },
  "MANAGER": { ru: "МЕНЕДЖЕР", kg: "МЕНЕДЖЕР", en: "MANAGER" },
  "RECEPTION": { ru: "РЕСЕПШЕН", kg: "РЕСЕПШЕН", en: "RECEPTION" },
  "MAID": { ru: "ГОРНИЧНАЯ", kg: "БӨЛМӨ КЫЗМАТКЕРИ", en: "MAID" },
  "TECHNICIAN": { ru: "ТЕХНИК", kg: "ТЕХНИК", en: "TECHNICIAN" },
  "DINING_STAFF": { ru: "РЕСТОРАН", kg: "РЕСТОРАН КЫЗМАТКЕРИ", en: "DINING STAFF" },
  "STORE_STAFF": { ru: "МАГАЗИН", kg: "ДҮКӨН КЫЗМАТКЕРИ", en: "STORE STAFF" },
  "Request": { ru: "Заявка", kg: "Өтүнмө", en: "Request" },
};

const common: Phrase[] = [
  { ru: "Главная", kg: "Башкы", en: "Home" },
  { ru: "Супершахматка", kg: "Супершахматка", en: "Super Grid" },
  { ru: "CRM / Заявки", kg: "CRM / Өтүнмөлөр", en: "CRM / Requests" },
  { ru: "Ресепшен / Брони", kg: "Ресепшен / Брондор", en: "Reception / Reservations" },
  { ru: "Сервис гостя", kg: "Конок сервиси", en: "Guest Services" },
  { ru: "Гости / История", kg: "Коноктор / Тарых", en: "Guests / History" },
  { ru: "QR номеров", kg: "Бөлмө QR", en: "Room QR" },
  { ru: "QR зон", kg: "Аймак QR", en: "Zone QR" },
  { ru: "Рост / Отзывы", kg: "Өсүү / Пикирлер", en: "Growth / Reviews" },
  { ru: "Выйти", kg: "Чыгуу", en: "Sign out" },
  { ru: "Обновить", kg: "Жаңыртуу", en: "Refresh" },
  { ru: "Брони и проживание", kg: "Брондор жана жашоо", en: "Reservations and stays" },
  { ru: "Карточка брони", kg: "Бронь карточкасы", en: "Reservation details" },
  { ru: "Закрыть", kg: "Жабуу", en: "Close" },
  { ru: "Гость", kg: "Конок", en: "Guest" },
  { ru: "Без имени", kg: "Аты жок", en: "No name" },
  { ru: "Текущий/рабочий номер", kg: "Учурдагы бөлмө", en: "Current room" },
  { ru: "Проживание", kg: "Жашоо", en: "Stay" },
  { ru: "Источник", kg: "Булак", en: "Source" },
  { ru: "График проживания", kg: "Жашоо графиги", en: "Stay schedule" },
  { ru: "Внутренние платежи по брони", kg: "Бронь боюнча ички төлөмдөр", en: "Reservation payments" },
  { ru: "Стоимость", kg: "Баасы", en: "Total" },
  { ru: "Подтверждено менеджером", kg: "Менеджер ырастаган", en: "Manager confirmed" },
  { ru: "Остаток", kg: "Калдык", en: "Balance" },
  { ru: "Задачи по номерам проживания", kg: "Бөлмө боюнча тапшырмалар", en: "Room tasks" },
  { ru: "Журнал действий", kg: "Аракеттер журналы", en: "Activity log" },
  { ru: "Проблемные номера", kg: "Көйгөйлүү бөлмөлөр", en: "Problem rooms" },
  { ru: "Повторяющиеся поломки", kg: "Кайталанган бузулуулар", en: "Recurring faults" },
  { ru: "Номера с повторными ремонтами", kg: "Кайталанган оңдоосу бар бөлмөлөр", en: "Rooms with repeat repairs" },
  { ru: "Сервис, уборка и ремонты", kg: "Сервис, тазалоо жана оңдоо", en: "Service, housekeeping and maintenance" },
  { ru: "только факты Resort Core", kg: "Resort Core фактылары гана", en: "Resort Core facts only" },
  { ru: "СОЗДАНО", kg: "ТҮЗҮЛДҮ", en: "CREATED" },
  { ru: "АКТИВНЫЕ", kg: "АКТИВДҮҮ", en: "ACTIVE" },
  { ru: "ЗАВЕРШЕНО", kg: "БҮТТҮ", en: "COMPLETED" },
  { ru: "СРОЧНО", kg: "ШАШЫЛЫШ", en: "URGENT" },
  { ru: "ПРОБЛЕМНЫЕ НОМЕРА", kg: "КӨЙГӨЙЛҮҮ БӨЛМӨЛӨР", en: "PROBLEM ROOMS" },
  { ru: "ПОВТОРЯЮЩИЕСЯ ПОЛОМКИ", kg: "КАЙТАЛАНГАН БУЗУЛУУЛАР", en: "RECURRING FAULTS" },
  { ru: "Заезд", kg: "Кирүү", en: "Check-in" },
  { ru: "Выезд", kg: "Чыгуу", en: "Check-out" },
  { ru: "Карточка", kg: "Карточка", en: "Details" },
  { ru: "Оплата", kg: "Төлөм", en: "Payment" },
  { ru: "Даты", kg: "Күндөр", en: "Dates" },
  { ru: "Активные", kg: "Активдүү", en: "Active" },
  { ru: "Заезды сегодня", kg: "Бүгүн кире тургандар", en: "Arrivals today" },
  { ru: "Выезды сегодня", kg: "Бүгүн чыга тургандар", en: "Departures today" },
  { ru: "Ожидают заезд", kg: "Кирүүнү күтөт", en: "Awaiting check-in" },
  { ru: "Проживают", kg: "Жашап жатышат", en: "Checked in" },
  { ru: "Выехали", kg: "Чыгып кетишти", en: "Checked out" },
  { ru: "Все", kg: "Баары", en: "All" },
  { ru: "Дата отеля", kg: "Мейманкана күнү", en: "Hotel date" },
  { ru: "Номер на заезд", kg: "Кирүү бөлмөсү", en: "Arrival room" },
  { ru: "Текущий номер", kg: "Учурдагы бөлмө", en: "Current room" },
  { ru: "Последний номер", kg: "Акыркы бөлмө", en: "Last room" },
  { ru: "Оплачено полностью", kg: "Толук төлөндү", en: "Paid in full" },
  { ru: "Переселение", kg: "Көчүрүү", en: "Room move" },
  { ru: "Готов", kg: "Даяр", en: "Ready" },
  { ru: "Нужна уборка", kg: "Тазалоо керек", en: "Needs cleaning" },
  { ru: "На проверке", kg: "Текшерүүдө", en: "In inspection" },
  { ru: "Ремонт", kg: "Оңдоо", en: "Maintenance" },
  { ru: "Не указан", kg: "Көрсөтүлгөн эмес", en: "Not specified" },
];

const phraseIndex = new Map<string, Phrase>();
for (const phrase of common) {
  phraseIndex.set(phrase.ru, phrase);
  phraseIndex.set(phrase.kg, phrase);
  phraseIndex.set(phrase.en, phrase);
}
for (const [key, phrase] of Object.entries(exact)) {
  phraseIndex.set(key, phrase);
  phraseIndex.set(phrase.ru, phrase);
  phraseIndex.set(phrase.kg, phrase);
  phraseIndex.set(phrase.en, phrase);
}

const tokenReplacements: Record<Locale, Array<[RegExp, string]>> = {
  ru: [
    [/\bGUEST SERVICES\b/g, "СЕРВИС ГОСТЕЙ"],
    [/\bHOUSEKEEPING\b/g, "УБОРКА"],
    [/\bMAINTENANCE\b/g, "РЕМОНТ"],
    [/\bNOT_CONFIGURED\b/g, "НЕ НАСТРОЕНО"],
    [/\bOWNER OPERATIONS\b/g, "ОПЕРАЦИИ ВЛАДЕЛЬЦА"],
    [/\bMTD\b/g, "С НАЧАЛА МЕСЯЦА"],
    [/\bDONE\b/g, "ЗАВЕРШЕНО"],
    [/\bIN_PROGRESS\b/g, "В РАБОТЕ"],
    [/\bIN_INSPECTION\b/g, "НА ПРОВЕРКЕ"],
    [/\bSUCCESS\b/g, "УСПЕШНО"],
    [/\bNORMAL\b/g, "ОБЫЧНЫЙ"],
  ],
  kg: [
    [/\bGUEST SERVICES\b/g, "КОНок СЕРВИСИ"],
    [/\bHOUSEKEEPING\b/g, "ТАЗАЛОО"],
    [/\bMAINTENANCE\b/g, "ОҢДОО"],
    [/\bNOT_CONFIGURED\b/g, "ЖӨНДӨЛГӨН ЭМЕС"],
    [/\bOWNER OPERATIONS\b/g, "ЭЭСИНИН ОПЕРАЦИЯЛАРЫ"],
    [/\bMTD\b/g, "АЙ БАШЫНАН"],
    [/\bDONE\b/g, "БҮТТҮ"],
    [/\bIN_PROGRESS\b/g, "АТКАРЫЛУУДА"],
    [/\bIN_INSPECTION\b/g, "ТЕКШЕРҮҮДӨ"],
    [/\bSUCCESS\b/g, "ИЙГИЛИКТҮҮ"],
    [/\bNORMAL\b/g, "КАДИМКИ"],
  ],
  en: [
    [/\bСЕРВИС ГОСТЕЙ\b/g, "GUEST SERVICES"],
    [/\bУБОРКА\b/g, "HOUSEKEEPING"],
    [/\bРЕМОНТ\b/g, "MAINTENANCE"],
    [/\bНЕ НАСТРОЕНО\b/g, "NOT CONFIGURED"],
    [/\bОПЕРАЦИИ ВЛАДЕЛЬЦА\b/g, "OWNER OPERATIONS"],
    [/\bС НАЧАЛА МЕСЯЦА\b/g, "MONTH TO DATE"],
    [/\bЗАВЕРШЕНО\b/g, "COMPLETED"],
    [/\bВ РАБОТЕ\b/g, "IN PROGRESS"],
    [/\bНА ПРОВЕРКЕ\b/g, "IN INSPECTION"],
    [/\bУСПЕШНО\b/g, "SUCCESS"],
    [/\bОБЫЧНЫЙ\b/g, "NORMAL"],
  ],
};

function translateText(source: string, locale: Locale): string {
  const trimmed = source.trim();
  if (!trimmed) return source;
  const direct = phraseIndex.get(trimmed);
  let translated = direct ? direct[locale] : trimmed;
  if (!direct && exact[trimmed]) translated = exact[trimmed][locale];
  for (const [pattern, replacement] of tokenReplacements[locale]) {
    translated = translated.replace(pattern, replacement);
  }
  const prefix = source.slice(0, source.indexOf(trimmed));
  const suffix = source.slice(source.indexOf(trimmed) + trimmed.length);
  return `${prefix}${translated}${suffix}`;
}

function requestUrl(input: RequestInfo | URL): string {
  if (typeof input === "string") return input;
  if (input instanceof URL) return input.toString();
  return input.url;
}

export default function AdminExperienceRuntime() {
  const [locale, setLocale] = useState<Locale>("ru");
  const [pin, setPin] = useState<PinPayload | null>(null);
  const [currentReservationId, setCurrentReservationId] = useState<string | null>(null);
  const [currentReservationCheckedIn, setCurrentReservationCheckedIn] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [pinBusy, setPinBusy] = useState(false);
  const [pinError, setPinError] = useState<string | null>(null);
  const originalText = useMemo(() => new WeakMap<Text, { source: string; rendered: string }>(), []);
  const originalAttrs = useMemo(() => new WeakMap<Element, Map<string, { source: string; rendered: string }>>(), []);

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === "ru" || stored === "kg" || stored === "en") setLocale(stored);
  }, []);

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, locale);
    document.documentElement.lang = locale === "kg" ? "ky" : locale;
  }, [locale]);

  useEffect(() => {
    function translateNode(node: Node) {
      if (node.nodeType === Node.TEXT_NODE) {
        const text = node as Text;
        const current = text.nodeValue || "";
        if (!current.trim()) return;
        const previous = originalText.get(text);
        const source = previous && current === previous.rendered ? previous.source : current;
        const rendered = translateText(source, locale);
        originalText.set(text, { source, rendered });
        if (current !== rendered) text.nodeValue = rendered;
        return;
      }
      if (!(node instanceof Element)) return;
      if (node.matches("script,style,code,pre,[data-i18n-skip]")) return;
      for (const attr of ["placeholder", "title", "aria-label"]) {
        if (!node.hasAttribute(attr)) continue;
        const current = node.getAttribute(attr) || "";
        const attrMap = originalAttrs.get(node) || new Map<string, { source: string; rendered: string }>();
        const previous = attrMap.get(attr);
        const source = previous && current === previous.rendered ? previous.source : current;
        const rendered = translateText(source, locale);
        attrMap.set(attr, { source, rendered });
        originalAttrs.set(node, attrMap);
        if (current !== rendered) node.setAttribute(attr, rendered);
      }
      for (const child of Array.from(node.childNodes)) translateNode(child);
    }

    translateNode(document.body);
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        if (mutation.type === "characterData") translateNode(mutation.target);
        for (const added of Array.from(mutation.addedNodes)) translateNode(added);
      }
      setDetailOpen(Boolean(document.querySelector(".reservation-detail")));
    });
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
    setDetailOpen(Boolean(document.querySelector(".reservation-detail")));
    return () => observer.disconnect();
  }, [locale, originalAttrs, originalText]);

  useEffect(() => {
    const originalFetch = window.fetch.bind(window);
    window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = requestUrl(input);
      const response = await originalFetch(input, init);

      if (/\/core\/api\/v1\/admin\/stays\/reservations\/[0-9a-f-]+\/check-in(?:\?|$)/i.test(url) && response.ok) {
        void response.clone().json().then((body) => {
          if (body?.guest_access_pin) {
            setPin(body as PinPayload);
            setPinError(null);
          }
        }).catch(() => undefined);
      }

      const detailMatch = url.match(/\/core\/api\/v1\/admin\/booking\/reservations\/([0-9a-f-]+)(?:\?|$)/i);
      if (detailMatch && response.ok) {
        void response.clone().json().then((body) => {
          setCurrentReservationId(detailMatch[1]);
          setCurrentReservationCheckedIn(body?.reservation?.status === "CHECKED_IN");
        }).catch(() => undefined);
      }
      return response;
    };
    return () => { window.fetch = originalFetch; };
  }, []);

  async function reissuePin() {
    if (!currentReservationId) return;
    if (!window.confirm(locale === "en" ? "Issue a new Guest OS PIN? The previous PIN will stop working." : locale === "kg" ? "Жаңы Guest OS кодун бересизби? Мурунку код иштебей калат." : "Выдать новый код Guest OS? Предыдущий PIN перестанет работать.")) return;
    setPinBusy(true);
    setPinError(null);
    try {
      const response = await fetch(`/core/api/v1/admin/guest-access/reservations/${currentReservationId}/pin`, { method: "POST" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof body?.detail === "string" ? body.detail : body?.detail?.code || "PIN_REISSUE_FAILED");
      setPin(body as PinPayload);
    } catch (error) {
      setPinError(error instanceof Error ? error.message : "PIN_REISSUE_FAILED");
    } finally {
      setPinBusy(false);
    }
  }

  async function copyPin() {
    if (!pin?.guest_access_pin) return;
    await navigator.clipboard.writeText(pin.guest_access_pin);
  }

  const labels = {
    ru: { language: "Язык", reissue: "Новый код Guest OS", title: "Код Guest OS выдан", room: "Номер", code: "Код гостя", valid: "Действует 24 часа", once: "Показывается только один раз. Передайте код гостю сейчас.", copy: "Скопировать код", close: "Закрыть", error: "Не удалось выдать новый код" },
    kg: { language: "Тил", reissue: "Жаңы Guest OS коду", title: "Guest OS коду берилди", room: "Бөлмө", code: "Конок коду", valid: "24 саат жарактуу", once: "Бир гана жолу көрсөтүлөт. Кодду конокко азыр бериңиз.", copy: "Кодду көчүрүү", close: "Жабуу", error: "Жаңы кодду берүү мүмкүн болгон жок" },
    en: { language: "Language", reissue: "New Guest OS PIN", title: "Guest OS PIN issued", room: "Room", code: "Guest PIN", valid: "Valid for 24 hours", once: "Shown only once. Give this PIN to the guest now.", copy: "Copy PIN", close: "Close", error: "Could not issue a new PIN" },
  }[locale];

  return <>
    <div className="admin-locale-switcher" data-i18n-skip>
      <span>{labels.language}</span>
      {(["ru", "kg", "en"] as Locale[]).map((value) => <button key={value} type="button" className={locale === value ? "active" : ""} onClick={() => setLocale(value)}>{value.toUpperCase()}</button>)}
    </div>

    {detailOpen && currentReservationCheckedIn && <button type="button" className="guest-pin-reissue" data-i18n-skip onClick={reissuePin} disabled={pinBusy}>{pinBusy ? "…" : labels.reissue}</button>}
    {pinError && <div className="guest-pin-runtime-error" data-i18n-skip>{labels.error}: {pinError}</div>}

    {pin && <div className="guest-pin-backdrop" data-i18n-skip role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setPin(null); }}>
      <section className="guest-pin-modal" role="dialog" aria-modal="true" aria-label={labels.title}>
        <p>{labels.title}</p>
        <h2>{pin.room_code ? `${labels.room} ${pin.room_code}` : labels.code}</h2>
        <div className="guest-pin-value">{pin.guest_access_pin}</div>
        <strong>{labels.valid}</strong>
        <small>{labels.once}</small>
        <div className="guest-pin-actions"><button type="button" onClick={copyPin}>{labels.copy}</button><button type="button" onClick={() => setPin(null)}>{labels.close}</button></div>
      </section>
    </div>}
  </>;
}
