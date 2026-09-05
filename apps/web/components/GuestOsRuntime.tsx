"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";

import { GuestFactsLocale, ownerApprovedGuestFacts } from "../lib/ownerApprovedGuestFacts";

type GuestContext = {
  qr_valid: boolean;
  authenticated: boolean;
  verification_required: boolean;
  active_stay: boolean;
  room: {
    code: string;
    name: string;
    room_type_name: string;
    building_or_zone?: string | null;
    floor?: string | null;
  };
  guest: { first_name: string } | null;
  stay: { check_in: string; check_out: string } | null;
  privacy: string;
};

type LoadState = "loading" | "ready" | "invalid" | "error";

const COPY = {
  ru: {
    brand: "Три Короны",
    kicker: "Guest OS · цифровой консьерж",
    loading: "Проверяем QR комнаты…",
    invalidTitle: "QR недоступен",
    invalidText: "Этот QR не найден или был заменён. Обратитесь на ресепшен.",
    genericTitle: "Информация о номере",
    noStay: "Сейчас за этим номером нет активного проживания. QR остаётся постоянным и будет готов для следующего заезда.",
    verifyTitle: "Подтвердите, что вы гость номера",
    verifyText: "Введите 6-значный код Guest OS, который вы получили при заселении. Сам QR не раскрывает данные проживающего.",
    pin: "Код Guest OS",
    submit: "Открыть Guest OS",
    verifying: "Проверяем…",
    wrongPin: "Код не подошёл. Проверьте цифры или обратитесь на ресепшен.",
    rateLimit: "Слишком много попыток. Доступ временно ограничен — обратитесь на ресепшен или попробуйте позже.",
    pinExpired: "Код больше не действует. Попросите ресепшен выдать новый код Guest OS.",
    welcome: "Добро пожаловать",
    room: "Номер",
    stay: "Проживание",
    services: "Что вам может понадобиться",
    servicesIntro: "Заявки из Guest OS уже передаются через Resort Core ответственному сотруднику. Статус выполнения можно отслеживать ниже в разделе «Мои заявки».",
    contact: "Администратор",
    contactText: "Нужна помощь сейчас? Напишите менеджеру или позвоните на ресепшен.",
    whatsapp: "Написать в WhatsApp",
    call: "Позвонить",
    rules: "Правила проживания",
    logout: "Выйти из Guest OS",
    privacy: "Ваши контактные и паспортные данные здесь не показываются. Доступ действует только для активного проживания.",
    error: "Не удалось открыть Guest OS. Проверьте интернет и попробуйте ещё раз.",
  },
  kg: {
    brand: "Үч Таажы",
    kicker: "Guest OS · санарип консьерж",
    loading: "Бөлмөнүн QR кодун текшерип жатабыз…",
    invalidTitle: "QR жеткиликсиз",
    invalidText: "Бул QR табылган жок же алмаштырылган. Ресепшенге кайрылыңыз.",
    genericTitle: "Бөлмө тууралуу маалымат",
    noStay: "Азыр бул бөлмөдө активдүү жашоо жок. QR туруктуу бойдон калат жана кийинки конок үчүн даяр болот.",
    verifyTitle: "Бул бөлмөнүн коногу экениңизди ырастоо",
    verifyText: "Катталууда берилген 6 орундуу Guest OS кодун киргизиңиз. QR өзү коноктун жеке маалыматтарын ачпайт.",
    pin: "Guest OS коду",
    submit: "Guest OS ачуу",
    verifying: "Текшерүүдө…",
    wrongPin: "Код туура эмес. Сандарды текшериңиз же ресепшенге кайрылыңыз.",
    rateLimit: "Аракеттер өтө көп болду. Кирүү убактылуу чектелди — ресепшенге кайрылыңыз же кийинчерээк аракет кылыңыз.",
    pinExpired: "Коддун мөөнөтү бүттү. Ресепшенден жаңы Guest OS кодун сураңыз.",
    welcome: "Кош келиңиз",
    room: "Бөлмө",
    stay: "Жашоо",
    services: "Сизге керектүү кызматтар",
    servicesIntro: "Guest OS аркылуу түзүлгөн өтүнмөлөр Resort Core аркылуу жооптуу кызматкерге дароо жөнөтүлөт. Аткарылышын төмөндөгү «Менин өтүнмөлөрүм» бөлүмүнөн көзөмөлдөй аласыз.",
    contact: "Администратор",
    contactText: "Азыр жардам керекпи? Менеджерге жазыңыз же ресепшенге чалыңыз.",
    whatsapp: "WhatsApp аркылуу жазуу",
    call: "Чалуу",
    rules: "Жашоо эрежелери",
    logout: "Guest OS чыгуу",
    privacy: "Бул жерде байланыш жана паспорт маалыматтары көрсөтүлбөйт. Кирүү активдүү жашоо мезгилинде гана иштейт.",
    error: "Guest OS ачылган жок. Интернет байланышын текшерип, кайра аракет кылыңыз.",
  },
  en: {
    brand: "Three Crowns",
    kicker: "Guest OS · digital concierge",
    loading: "Checking the room QR…",
    invalidTitle: "QR unavailable",
    invalidText: "This QR was not found or has been replaced. Please contact reception.",
    genericTitle: "Room information",
    noStay: "There is no active stay assigned to this room right now. The permanent QR remains ready for the next guest.",
    verifyTitle: "Confirm that you are staying in this room",
    verifyText: "Enter the 6-digit Guest OS code issued at check-in. The room QR itself never reveals guest identity.",
    pin: "Guest OS code",
    submit: "Open Guest OS",
    verifying: "Checking…",
    wrongPin: "That code did not match. Check the digits or contact reception.",
    rateLimit: "Too many attempts. Access is temporarily limited — contact reception or try again later.",
    pinExpired: "This code has expired. Ask reception for a new Guest OS code.",
    welcome: "Welcome",
    room: "Room",
    stay: "Stay",
    services: "What you may need",
    servicesIntro: "Guest OS requests are already routed through Resort Core to the responsible team. You can track progress below in My Requests.",
    contact: "Administrator",
    contactText: "Need help now? Message the manager or call reception.",
    whatsapp: "Message on WhatsApp",
    call: "Call reception",
    rules: "Hotel rules",
    logout: "Sign out of Guest OS",
    privacy: "Contact and passport details are never displayed here. Access is valid only for the active stay.",
    error: "Guest OS could not be opened. Check your connection and try again.",
  },
} as const;

function localeFromBrowser(): GuestFactsLocale {
  if (typeof window === "undefined") return "ru";
  const query = new URLSearchParams(window.location.search).get("lang");
  if (query === "ru" || query === "kg" || query === "en") return query;
  const stored = window.localStorage.getItem("three-crowns-site-language");
  return stored === "kg" || stored === "en" ? stored : "ru";
}

function fmtDate(value: string, locale: GuestFactsLocale) {
  const lang = locale === "kg" ? "ky-KG" : locale === "en" ? "en-GB" : "ru-RU";
  return new Date(`${value}T00:00:00`).toLocaleDateString(lang, { day: "2-digit", month: "short", year: "numeric" });
}

export default function GuestOsRuntime({ token }: { token: string }) {
  const [locale, setLocale] = useState<GuestFactsLocale>("ru");
  const [state, setState] = useState<LoadState>("loading");
  const [context, setContext] = useState<GuestContext | null>(null);
  const [pin, setPin] = useState("");
  const [verifyState, setVerifyState] = useState<"idle" | "loading">("idle");
  const [verifyError, setVerifyError] = useState<string | null>(null);

  useEffect(() => setLocale(localeFromBrowser()), []);
  const copy = COPY[locale];
  const facts = ownerApprovedGuestFacts[locale];

  const load = useCallback(async () => {
    setState("loading");
    try {
      const response = await fetch(`/core/api/v1/guest-os/rooms/${encodeURIComponent(token)}`, {
        credentials: "include",
        cache: "no-store",
      });
      if (response.status === 404) {
        setContext(null);
        setState("invalid");
        return;
      }
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      setContext((await response.json()) as GuestContext);
      setState("ready");
    } catch {
      setContext(null);
      setState("error");
    }
  }, [token]);

  useEffect(() => { void load(); }, [load]);

  async function verify(event: FormEvent) {
    event.preventDefault();
    if (!/^\d{6}$/.test(pin)) return;
    setVerifyState("loading");
    setVerifyError(null);
    try {
      const response = await fetch(`/core/api/v1/guest-os/rooms/${encodeURIComponent(token)}/verify`, {
        method: "POST",
        credentials: "include",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ pin }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        const code = body?.detail?.code;
        setVerifyError(code === "PIN_RATE_LIMIT" ? copy.rateLimit : code === "PIN_EXPIRED" ? copy.pinExpired : copy.wrongPin);
        return;
      }
      setPin("");
      await load();
    } catch {
      setVerifyError(copy.error);
    } finally {
      setVerifyState("idle");
    }
  }

  async function logout() {
    await fetch("/core/api/v1/guest-os/logout", { method: "POST", credentials: "include" }).catch(() => null);
    setContext(null);
    await load();
  }

  const serviceCards = useMemo(
    () => facts.services.cards.filter((card) => !["PARKING", "TABLE_TENNIS"].includes(card.code)),
    [facts],
  );

  return (
    <main className="guest-os-page">
      <div className="guest-os-glow" aria-hidden="true" />
      <section className="guest-os-shell">
        <header className="guest-os-brand">
          <div className="guest-os-crown">III</div>
          <div><strong>{copy.brand}</strong><span>{copy.kicker}</span></div>
          <div className="guest-os-languages" aria-label="Language">
            {(["ru", "kg", "en"] as GuestFactsLocale[]).map((item) => (
              <button key={item} className={locale === item ? "active" : ""} onClick={() => setLocale(item)}>{item.toUpperCase()}</button>
            ))}
          </div>
        </header>

        {state === "loading" && <div className="guest-os-state"><span className="guest-os-spinner" />{copy.loading}</div>}
        {state === "invalid" && <div className="guest-os-panel guest-os-centered"><h1>{copy.invalidTitle}</h1><p>{copy.invalidText}</p><a href="tel:+996558085002" className="guest-os-primary">{copy.call}</a></div>}
        {state === "error" && <div className="guest-os-panel guest-os-centered"><h1>{copy.error}</h1><button className="guest-os-primary" onClick={() => void load()}>↻</button></div>}

        {state === "ready" && context && !context.active_stay && (
          <div className="guest-os-panel guest-os-centered">
            <p className="guest-os-eyebrow">{copy.genericTitle}</p>
            <h1>№ {context.room.code}</h1>
            <p>{context.room.room_type_name}</p>
            <div className="guest-os-room-meta">{[context.room.building_or_zone, context.room.floor].filter(Boolean).join(" · ")}</div>
            <p className="guest-os-muted">{copy.noStay}</p>
          </div>
        )}

        {state === "ready" && context?.active_stay && !context.authenticated && (
          <div className="guest-os-panel guest-os-verify">
            <div className="guest-os-room-chip">№ {context.room.code} · {context.room.room_type_name}</div>
            <p className="guest-os-eyebrow">{copy.kicker}</p>
            <h1>{copy.verifyTitle}</h1>
            <p>{copy.verifyText}</p>
            <form onSubmit={verify}>
              <label htmlFor="guest-os-pin">{copy.pin}</label>
              <input
                id="guest-os-pin"
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={6}
                value={pin}
                onChange={(event) => setPin(event.target.value.replace(/\D/g, "").slice(0, 6))}
                placeholder="••••••"
                aria-describedby={verifyError ? "guest-os-error" : undefined}
              />
              {verifyError && <div id="guest-os-error" className="guest-os-error" role="alert">{verifyError}</div>}
              <button className="guest-os-primary" disabled={pin.length !== 6 || verifyState === "loading"}>{verifyState === "loading" ? copy.verifying : copy.submit}</button>
            </form>
          </div>
        )}

        {state === "ready" && context?.authenticated && context.guest && context.stay && (
          <>
            <section className="guest-os-welcome guest-os-panel">
              <p className="guest-os-eyebrow">{copy.welcome}</p>
              <h1>{context.guest.first_name}</h1>
              <div className="guest-os-stay-grid">
                <div><span>{copy.room}</span><strong>№ {context.room.code}</strong><small>{context.room.room_type_name}</small></div>
                <div><span>{copy.stay}</span><strong>{fmtDate(context.stay.check_in, locale)}</strong><small>→ {fmtDate(context.stay.check_out, locale)}</small></div>
              </div>
            </section>

            <section className="guest-os-services">
              <p className="guest-os-eyebrow">{copy.services}</p>
              <p className="guest-os-services-intro">{copy.servicesIntro}</p>
              <div className="guest-os-service-grid">
                {serviceCards.map((card) => (
                  <article key={card.code} className="guest-os-service-card">
                    <span>{card.code.slice(0, 2)}</span>
                    <h2>{card.title}</h2>
                    <p>{card.text}</p>
                    {card.href && card.cta ? (
                      card.href.startsWith("/") ? <Link href={card.href}>{card.cta} →</Link> : <a href={card.href} target="_blank" rel="noreferrer">{card.cta} →</a>
                    ) : null}
                  </article>
                ))}
              </div>
            </section>

            <section className="guest-os-panel guest-os-contact">
              <p className="guest-os-eyebrow">{copy.contact}</p>
              <h2>{copy.contactText}</h2>
              <div className="guest-os-actions">
                <a className="guest-os-primary" href="https://wa.me/996558085008" target="_blank" rel="noreferrer">{copy.whatsapp}</a>
                <a className="guest-os-secondary" href="tel:+996558085002">{copy.call}</a>
                <Link className="guest-os-secondary" href={locale === "ru" ? "/rules" : `/rules?lang=${locale}`}>{copy.rules}</Link>
              </div>
            </section>

            <p className="guest-os-privacy">{copy.privacy}</p>
            <button className="guest-os-logout" onClick={() => void logout()}>{copy.logout}</button>
          </>
        )}
      </section>
    </main>
  );
}
