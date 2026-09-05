"use client";

import { useCallback, useEffect, useState } from "react";

type Locale = "ru" | "kg" | "en";
type Policy = {
  scheduled_housekeeping_interval_days: number;
  scheduled_linen_change_included: boolean;
  on_demand_housekeeping_price_kgs: number | null;
  on_demand_linen_price_kgs: number | null;
};

type ServiceCode = "HOUSEKEEPING" | "LINEN";

const COPY = {
  ru: {
    eyebrow: "Уборка номера",
    title: "Плановая уборка и дополнительные услуги",
    schedule: (days: number) => `Плановая уборка проводится каждые ${days} дня во время проживания.`,
    linen: "Смена постельного белья входит в плановую уборку.",
    housekeeping: "Дополнительная уборка",
    extraLinen: "Дополнительная смена белья",
    paid: "платно",
    pricePending: "Цена настраивается администрацией",
    request: "Заказать",
    sending: "Отправляем…",
    sent: "Заявка создана. Сотрудник увидит её в Resort OS.",
    duplicate: "Такая активная заявка уже есть.",
    unavailable: "Цена услуги ещё не настроена. Обратитесь на ресепшен.",
  },
  kg: {
    eyebrow: "Бөлмөнү тазалоо",
    title: "Пландуу тазалоо жана кошумча кызматтар",
    schedule: (days: number) => `Жашоо учурунда пландуу тазалоо ар ${days} күн сайын жүргүзүлөт.`,
    linen: "Төшөк жабдыгын алмаштыруу пландуу тазалоого кирет.",
    housekeeping: "Кошумча тазалоо",
    extraLinen: "Төшөк жабдыгын кошумча алмаштыруу",
    paid: "акы төлөнөт",
    pricePending: "Бааны администрация орнотот",
    request: "Заказ кылуу",
    sending: "Жөнөтүлүүдө…",
    sent: "Өтүнмө түзүлдү. Кызматкер аны Resort OS'то көрөт.",
    duplicate: "Мындай активдүү өтүнмө мурунтан бар.",
    unavailable: "Кызматтын баасы азырынча коюлган жок. Ресепшенге кайрылыңыз.",
  },
  en: {
    eyebrow: "Housekeeping",
    title: "Scheduled cleaning and extra services",
    schedule: (days: number) => `Scheduled housekeeping is provided every ${days} days during your stay.`,
    linen: "Bed-linen change is included in scheduled housekeeping.",
    housekeeping: "Extra housekeeping",
    extraLinen: "Extra linen change",
    paid: "paid service",
    pricePending: "Price is being configured by management",
    request: "Request",
    sending: "Sending…",
    sent: "Request created. Staff can now see it in Resort OS.",
    duplicate: "An active request for this service already exists.",
    unavailable: "The service price has not been configured yet. Please contact reception.",
  },
} as const;

function locale(): Locale {
  if (typeof window === "undefined") return "ru";
  const stored = window.localStorage.getItem("three-crowns-guest-language") || window.localStorage.getItem("three-crowns-site-language");
  return stored === "kg" || stored === "en" ? stored : "ru";
}

export default function GuestHousekeepingPolicy({ token }: { token: string }) {
  const [lang, setLang] = useState<Locale>("ru");
  const [policy, setPolicy] = useState<Policy | null>(null);
  const [busy, setBusy] = useState<ServiceCode | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const response = await fetch(`/core/api/v1/guest-os/rooms/${encodeURIComponent(token)}/service-policy`, { credentials: "include", cache: "no-store" });
      if (!response.ok) { setPolicy(null); return; }
      setPolicy(await response.json() as Policy);
    } catch { setPolicy(null); }
  }, [token]);

  useEffect(() => {
    const syncLocale = () => setLang(locale());
    syncLocale();
    window.addEventListener("three-crowns:content-ready", syncLocale);
    void load();
    return () => window.removeEventListener("three-crowns:content-ready", syncLocale);
  }, [load]);

  async function requestService(code: ServiceCode) {
    if (busy) return;
    const price = code === "HOUSEKEEPING" ? policy?.on_demand_housekeeping_price_kgs : policy?.on_demand_linen_price_kgs;
    if (price == null) { setMessage(COPY[lang].unavailable); return; }
    setBusy(code); setMessage(null);
    try {
      const response = await fetch(`/core/api/v1/guest-os/rooms/${encodeURIComponent(token)}/requests`, {
        method: "POST", credentials: "include", headers: { "content-type": "application/json" },
        body: JSON.stringify({ request_code: code, description: null, service_date: null, service_time: null }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        const errorCode = body?.detail?.code;
        if (errorCode === "GUEST_REQUEST_DUPLICATE_ACTIVE") throw new Error("DUPLICATE");
        if (errorCode === "GUEST_SERVICE_PRICE_NOT_CONFIGURED") throw new Error("PRICE");
        throw new Error("FAILED");
      }
      setMessage(COPY[lang].sent);
    } catch (cause) {
      const codeValue = cause instanceof Error ? cause.message : "FAILED";
      setMessage(codeValue === "DUPLICATE" ? COPY[lang].duplicate : codeValue === "PRICE" ? COPY[lang].unavailable : COPY[lang].unavailable);
    } finally { setBusy(null); }
  }

  if (!policy) return null;
  const c = COPY[lang];
  const options: Array<{ code: ServiceCode; title: string; price: number | null }> = [
    { code: "HOUSEKEEPING", title: c.housekeeping, price: policy.on_demand_housekeeping_price_kgs },
    { code: "LINEN", title: c.extraLinen, price: policy.on_demand_linen_price_kgs },
  ];

  return <section className="guest-housekeeping-policy">
    <div className="guest-housekeeping-head"><div><p>{c.eyebrow}</p><h2>{c.title}</h2></div><span>Housekeeping · Resort Core</span></div>
    <div className="guest-housekeeping-included"><strong>{c.schedule(policy.scheduled_housekeeping_interval_days)}</strong>{policy.scheduled_linen_change_included && <span>{c.linen}</span>}</div>
    <div className="guest-housekeeping-options">{options.map((item) => <article key={item.code}><div><small>{c.paid}</small><h3>{item.title}</h3></div><strong>{item.price == null ? c.pricePending : `${item.price.toLocaleString(lang === "en" ? "en-US" : "ru-RU")} KGS`}</strong><button disabled={busy !== null || item.price == null} onClick={() => void requestService(item.code)}>{busy === item.code ? c.sending : c.request}</button></article>)}</div>
    {message && <div className="guest-market-notice">{message}</div>}
  </section>;
}
