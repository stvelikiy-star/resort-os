"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import type { GuestFactsLocale } from "../lib/ownerApprovedGuestFacts";

type GuestRequestItem = {
  id: string;
  request_code: string;
  type: string;
  status: "OPEN" | "IN_PROGRESS" | "IN_INSPECTION" | "DONE" | "CANCELLED";
  title: string;
  description?: string | null;
  service_date?: string | null;
  service_time?: string | null;
  created_at: string;
  updated_at: string;
};

const REQUEST_CODES = ["HOUSEKEEPING", "TOWELS", "LINEN", "MAINTENANCE", "TRANSFER", "MEALS", "PARKING", "SAUNA", "BILLIARDS", "EXCURSIONS", "ADMIN"] as const;
type RequestCode = (typeof REQUEST_CODES)[number];

const COPY = {
  ru: {
    eyebrow: "Сервис во время проживания",
    title: "Заявка в отель",
    intro: "Выберите услугу — заявка попадёт в Resort Core и будет видна ответственному сотруднику. Дополнительные услуги не меняют стоимость проживания автоматически.",
    choose: "Что нужно",
    note: "Комментарий",
    notePlaceholder: "Например: принесите, пожалуйста, 2 больших полотенца",
    date: "Дата, если нужна",
    time: "Время, если нужно",
    send: "Отправить заявку",
    sending: "Отправляем…",
    sent: "Заявка создана",
    duplicate: "Такая активная заявка уже есть.",
    error: "Не удалось создать заявку. Попробуйте ещё раз или обратитесь на ресепшен.",
    mine: "Мои заявки",
    empty: "Активных и прошлых заявок пока нет.",
    refresh: "Обновить",
    cancel: "Отменить",
    status: { OPEN: "Новая", IN_PROGRESS: "В работе", IN_INSPECTION: "На проверке", DONE: "Выполнено", CANCELLED: "Отменено" },
    labels: { HOUSEKEEPING: "Уборка", TOWELS: "Полотенца", LINEN: "Замена белья", MAINTENANCE: "Поломка / ремонт", TRANSFER: "Трансфер", MEALS: "Питание", PARKING: "Парковка", SAUNA: "Сауна", BILLIARDS: "Бильярд", EXCURSIONS: "Экскурсии", ADMIN: "Администратор" },
  },
  kg: {
    eyebrow: "Жашоо учурундагы сервис",
    title: "Мейманканага өтүнмө",
    intro: "Кызматты тандаңыз — өтүнмө Resort Core аркылуу жооптуу кызматкерге жетет. Кошумча кызматтар жашоонун баасын автоматтык өзгөртпөйт.",
    choose: "Эмне керек",
    note: "Комментарий",
    notePlaceholder: "Мисалы: 2 чоң сүлгү алып келиңизчи",
    date: "Керек болсо дата",
    time: "Керек болсо убакыт",
    send: "Өтүнмө жөнөтүү",
    sending: "Жөнөтүлүүдө…",
    sent: "Өтүнмө түзүлдү",
    duplicate: "Мындай активдүү өтүнмө бар.",
    error: "Өтүнмө түзүлгөн жок. Кайра аракет кылыңыз же ресепшенге кайрылыңыз.",
    mine: "Менин өтүнмөлөрүм",
    empty: "Азырынча өтүнмөлөр жок.",
    refresh: "Жаңыртуу",
    cancel: "Жокко чыгаруу",
    status: { OPEN: "Жаңы", IN_PROGRESS: "Аткарылууда", IN_INSPECTION: "Текшерүүдө", DONE: "Аткарылды", CANCELLED: "Жокко чыгарылды" },
    labels: { HOUSEKEEPING: "Тазалоо", TOWELS: "Сүлгү", LINEN: "Төшөк жабдыгын алмаштыруу", MAINTENANCE: "Бузулуу / оңдоо", TRANSFER: "Трансфер", MEALS: "Тамактануу", PARKING: "Унаа токтотуучу жай", SAUNA: "Сауна", BILLIARDS: "Бильярд", EXCURSIONS: "Экскурсиялар", ADMIN: "Администратор" },
  },
  en: {
    eyebrow: "Service during your stay",
    title: "Request hotel service",
    intro: "Choose what you need. The request goes through Resort Core to the responsible staff workflow. Extra services never change the accommodation total automatically.",
    choose: "What do you need",
    note: "Comment",
    notePlaceholder: "For example: please bring 2 large towels",
    date: "Date, if needed",
    time: "Time, if needed",
    send: "Send request",
    sending: "Sending…",
    sent: "Request created",
    duplicate: "An active request of this kind already exists.",
    error: "The request could not be created. Try again or contact reception.",
    mine: "My requests",
    empty: "No requests yet.",
    refresh: "Refresh",
    cancel: "Cancel",
    status: { OPEN: "New", IN_PROGRESS: "In progress", IN_INSPECTION: "Inspection", DONE: "Done", CANCELLED: "Cancelled" },
    labels: { HOUSEKEEPING: "Room cleaning", TOWELS: "Towels", LINEN: "Bed linen", MAINTENANCE: "Maintenance", TRANSFER: "Transfer", MEALS: "Meals", PARKING: "Parking", SAUNA: "Sauna", BILLIARDS: "Billiards", EXCURSIONS: "Excursions", ADMIN: "Administrator" },
  },
} as const;

function localeFromBrowser(): GuestFactsLocale {
  if (typeof window === "undefined") return "ru";
  const query = new URLSearchParams(window.location.search).get("lang");
  if (query === "ru" || query === "kg" || query === "en") return query;
  const stored = window.localStorage.getItem("three-crowns-site-language");
  return stored === "kg" || stored === "en" ? stored : "ru";
}

function formatDateTime(value: string, locale: GuestFactsLocale) {
  const lang = locale === "kg" ? "ky-KG" : locale === "en" ? "en-GB" : "ru-RU";
  return new Date(value).toLocaleString(lang, { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

export default function GuestRequestsPanel({ token }: { token: string }) {
  const [locale, setLocale] = useState<GuestFactsLocale>("ru");
  const [visible, setVisible] = useState(false);
  const [items, setItems] = useState<GuestRequestItem[]>([]);
  const [requestCode, setRequestCode] = useState<RequestCode>("TOWELS");
  const [description, setDescription] = useState("");
  const [serviceDate, setServiceDate] = useState("");
  const [serviceTime, setServiceTime] = useState("");
  const [sending, setSending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => setLocale(localeFromBrowser()), []);
  const copy = COPY[locale];

  const load = useCallback(async () => {
    try {
      const response = await fetch(`/core/api/v1/guest-os/rooms/${encodeURIComponent(token)}/requests`, {
        credentials: "include",
        cache: "no-store",
      });
      if (response.status === 401 || response.status === 404) {
        setVisible(false);
        setItems([]);
        return;
      }
      if (!response.ok) return;
      const body = await response.json() as { items?: GuestRequestItem[] };
      setItems(body.items ?? []);
      setVisible(true);
    } catch {
      // Guest OS itself already owns the network-error surface. Keep this panel quiet.
    }
  }, [token]);

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(), 15000);
    return () => window.clearInterval(timer);
  }, [load]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSending(true);
    setMessage(null);
    try {
      const response = await fetch(`/core/api/v1/guest-os/rooms/${encodeURIComponent(token)}/requests`, {
        method: "POST",
        credentials: "include",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          request_code: requestCode,
          description: description.trim() || null,
          service_date: serviceDate || null,
          service_time: serviceTime || null,
        }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        setMessage(body?.detail?.code === "GUEST_REQUEST_DUPLICATE_ACTIVE" ? copy.duplicate : copy.error);
        return;
      }
      setDescription("");
      setServiceDate("");
      setServiceTime("");
      setMessage(copy.sent);
      await load();
    } catch {
      setMessage(copy.error);
    } finally {
      setSending(false);
    }
  }

  async function cancel(taskId: string) {
    setMessage(null);
    try {
      const response = await fetch(`/core/api/v1/guest-os/rooms/${encodeURIComponent(token)}/requests/${taskId}/cancel`, {
        method: "POST",
        credentials: "include",
      });
      if (!response.ok) {
        setMessage(copy.error);
        return;
      }
      await load();
    } catch {
      setMessage(copy.error);
    }
  }

  const active = useMemo(() => items.filter((item) => item.status !== "DONE" && item.status !== "CANCELLED").length, [items]);

  if (!visible) return null;

  return (
    <section className="guest-requests-shell" aria-label={copy.title}>
      <div className="guest-requests-card guest-requests-create">
        <p className="guest-requests-eyebrow">{copy.eyebrow}</p>
        <h2>{copy.title}</h2>
        <p>{copy.intro}</p>
        <form onSubmit={submit}>
          <label>{copy.choose}
            <select value={requestCode} onChange={(event) => setRequestCode(event.target.value as RequestCode)}>
              {REQUEST_CODES.map((code) => <option key={code} value={code}>{copy.labels[code]}</option>)}
            </select>
          </label>
          <label>{copy.note}
            <textarea value={description} maxLength={1200} onChange={(event) => setDescription(event.target.value)} placeholder={copy.notePlaceholder} />
          </label>
          <div className="guest-requests-datetime">
            <label>{copy.date}<input type="date" value={serviceDate} onChange={(event) => setServiceDate(event.target.value)} /></label>
            <label>{copy.time}<input type="time" value={serviceTime} onChange={(event) => setServiceTime(event.target.value)} /></label>
          </div>
          {message && <div className="guest-requests-message" role="status">{message}</div>}
          <button type="submit" disabled={sending}>{sending ? copy.sending : copy.send}</button>
        </form>
      </div>

      <div className="guest-requests-card guest-requests-list">
        <div className="guest-requests-list-head">
          <div><p className="guest-requests-eyebrow">{copy.mine}</p><h2>{items.length}<small>{active ? ` · ${active}` : ""}</small></h2></div>
          <button onClick={() => void load()}>{copy.refresh}</button>
        </div>
        {!items.length ? <p className="guest-requests-empty">{copy.empty}</p> : (
          <div className="guest-requests-items">
            {items.map((item) => {
              const code = (REQUEST_CODES.includes(item.request_code as RequestCode) ? item.request_code : "ADMIN") as RequestCode;
              return <article key={item.id} data-request-status={item.status}>
                <div className="guest-requests-item-top">
                  <strong>{copy.labels[code]}</strong>
                  <span>{copy.status[item.status]}</span>
                </div>
                {item.description && <p>{item.description}</p>}
                <small>{formatDateTime(item.created_at, locale)}{item.service_date ? ` · ${item.service_date}` : ""}{item.service_time ? ` · ${item.service_time}` : ""}</small>
                {item.status === "OPEN" && <button onClick={() => void cancel(item.id)}>{copy.cancel}</button>}
              </article>;
            })}
          </div>
        )}
      </div>
    </section>
  );
}
