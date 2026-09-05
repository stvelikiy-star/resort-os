"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type Locale = "ru" | "kg" | "en";
type GuestContext = { authenticated: boolean; active_stay: boolean; room: { code: string }; guest: { first_name: string } | null };
type MenuItem = { id: string; code: string; category: string; name_ru: string; name_kg: string; name_en: string; price_kgs: number; is_active: boolean; is_draft: boolean; sort_order: number };
type AiMessage = { role: "user" | "assistant"; content: string };

type OfferCode = "TRANSFER" | "SAUNA" | "BILLIARDS" | "EXCURSIONS" | "ADMIN";

const KOL_MARKETPLACE_URL = process.env.NEXT_PUBLIC_KOL_MARKETPLACE_URL || "";

const copy = {
  ru: {
    eyebrow: "Для вашего отдыха",
    title: "Всё, что можно заказать — в одном месте",
    intro: "Меню кухни, услуги отеля и персональные предложения. Заказ или заявка сразу попадает в Resort OS — сотрудник подтверждает доступность и условия.",
    dining: "Меню для гостя сейчас",
    diningNote: "Показываем только активные позиции, которые не помечены как черновик.",
    noMenu: "Опубликованного меню сейчас нет. Уточните у администратора.",
    guests: "Гостей",
    comment: "Комментарий к заказу",
    commentPlaceholder: "Например: без лука, приборы на двоих",
    total: "Итого по меню",
    order: "Заказать в номер",
    ordering: "Отправляем заказ…",
    ordered: (number: string, total: number) => `Заказ ${number} создан · ${total.toLocaleString("ru-RU")} сом. Кухня увидит его в своей очереди.`,
    offers: "Предложения для вас",
    offersNote: "Мы не подтверждаем услугу автоматически: сотрудник принимает заявку и связывается с вами при необходимости.",
    want: "Хочу",
    requested: "Заявка отправлена",
    aiTitle: "AI-консьерж",
    aiNote: "Спросите об отеле, территории, отдыхе и услугах. AI отвечает только по подтверждённым данным Resort Core.",
    aiPlaceholder: "Например: что можно сделать вечером?",
    aiSend: "Спросить",
    aiThinking: "Проверяю…",
    aiError: "AI сейчас недоступен. Можно отправить заявку администратору ниже.",
    kolTitle: "Ещё больше сервисов",
    kolText: "Откройте подключённый каталог KÖL, если хотите заказать дополнительные партнёрские услуги или доставку.",
    kolOpen: "Открыть KÖL",
  },
  kg: {
    eyebrow: "Эс алууңуз үчүн",
    title: "Заказ кылууга боло турган нерселердин баары бир жерде",
    intro: "Ашкана менюсу, мейманкана кызматтары жана жеке сунуштар. Заказ же өтүнмө Resort OS системасына түшөт — кызматкер жеткиликтүүлүктү жана шарттарды ырастайт.",
    dining: "Конок үчүн азыркы меню",
    diningNote: "Активдүү жана черновик эмес позициялар гана көрсөтүлөт.",
    noMenu: "Азыр жарыяланган меню жок. Администратордон тактаңыз.",
    guests: "Коноктор",
    comment: "Заказга комментарий",
    commentPlaceholder: "Мисалы: пиязсыз, эки кишиге прибор",
    total: "Меню боюнча сумма",
    order: "Бөлмөгө заказ кылуу",
    ordering: "Заказ жөнөтүлүүдө…",
    ordered: (number: string, total: number) => `Заказ ${number} түзүлдү · ${total.toLocaleString("ru-RU")} сом. Ашкана аны кезекте көрөт.`,
    offers: "Сиз үчүн сунуштар",
    offersNote: "Кызмат автоматтык түрдө ырасталбайт: кызматкер өтүнмөнү кабыл алып, керек болсо сиз менен байланышат.",
    want: "Каалайм",
    requested: "Өтүнмө жөнөтүлдү",
    aiTitle: "AI-консьерж",
    aiNote: "Мейманкана, аймак, эс алуу жана кызматтар тууралуу сураңыз. AI Resort Core'догу ырасталган маалыматтар боюнча гана жооп берет.",
    aiPlaceholder: "Мисалы: кечинде эмне кылса болот?",
    aiSend: "Суроо берүү",
    aiThinking: "Текшерип жатам…",
    aiError: "AI азыр жеткиликсиз. Төмөндө администраторго өтүнмө жөнөтсөңүз болот.",
    kolTitle: "Дагы кызматтар",
    kolText: "Эгер кошумча өнөктөш кызматтарын же жеткирүүнү кааласаңыз, туташкан KÖL каталогун ачыңыз.",
    kolOpen: "KÖL ачуу",
  },
  en: {
    eyebrow: "For your stay",
    title: "Everything you can request, in one place",
    intro: "Kitchen menu, hotel services and personal offers. Every order or request goes straight into Resort OS for staff confirmation.",
    dining: "Guest menu available now",
    diningNote: "Only active, non-draft menu items are shown.",
    noMenu: "There is no published menu right now. Please ask an administrator.",
    guests: "Guests",
    comment: "Order note",
    commentPlaceholder: "For example: no onion, cutlery for two",
    total: "Menu total",
    order: "Order to room",
    ordering: "Sending order…",
    ordered: (number: string, total: number) => `Order ${number} created · ${total.toLocaleString("en-US")} KGS. The kitchen can now see it in its queue.`,
    offers: "Recommended for you",
    offersNote: "Services are not auto-confirmed. Staff receive the request and confirm availability and final terms.",
    want: "Request",
    requested: "Request sent",
    aiTitle: "AI concierge",
    aiNote: "Ask about the hotel, resort, stay and services. AI answers only from verified Resort Core facts.",
    aiPlaceholder: "For example: what can we do this evening?",
    aiSend: "Ask",
    aiThinking: "Checking…",
    aiError: "AI is unavailable right now. You can send an administrator request below.",
    kolTitle: "More services",
    kolText: "Open the connected KÖL catalogue for additional partner services or delivery, when enabled by the hotel.",
    kolOpen: "Open KÖL",
  },
} as const;

const offerCopy: Record<Locale, Array<{ code: OfferCode; icon: string; title: string; hook: string }>> = {
  ru: [
    { code: "TRANSFER", icon: "↗", title: "Трансфер без лишних звонков", hook: "Сообщите маршрут — менеджер подтвердит машину, время и условия." },
    { code: "SAUNA", icon: "♨", title: "Тёплый вечер", hook: "Запросите сауну на удобное время. Доступность подтверждает администратор." },
    { code: "EXCURSIONS", icon: "⌖", title: "Увидеть больше Иссык-Куля", hook: "Оставьте заявку — подберём экскурсию под ваш день и состав гостей." },
    { code: "BILLIARDS", icon: "●", title: "Бильярд после ужина", hook: "Попросите забронировать удобное время — сотрудник подтвердит." },
    { code: "ADMIN", icon: "AI", title: "Нужна идея?", hook: "Администратор поможет собрать день: питание, поездка, отдых и сервисы." },
  ],
  kg: [
    { code: "TRANSFER", icon: "↗", title: "Трансфер — ашыкча чалуусуз", hook: "Маршрутту жазыңыз — менеджер унааны, убакытты жана шарттарды ырастайт." },
    { code: "SAUNA", icon: "♨", title: "Жылуу кеч", hook: "Ыңгайлуу убакытка сауна сураңыз. Жеткиликтүүлүктү администратор ырастайт." },
    { code: "EXCURSIONS", icon: "⌖", title: "Ысык-Көлдү көбүрөөк көрүңүз", hook: "Өтүнмө калтырыңыз — күнүңүзгө ылайык саякат сунуштайбыз." },
    { code: "BILLIARDS", icon: "●", title: "Кечки бильярд", hook: "Ыңгайлуу убакыт сураңыз — кызматкер ырастайт." },
    { code: "ADMIN", icon: "AI", title: "Идея керекпи?", hook: "Администратор тамактануу, саякат жана эс алуу боюнча күндү чогултууга жардам берет." },
  ],
  en: [
    { code: "TRANSFER", icon: "↗", title: "Transfer without extra calls", hook: "Send the route and a manager will confirm the vehicle, time and terms." },
    { code: "SAUNA", icon: "♨", title: "A warmer evening", hook: "Request a sauna time. Availability is confirmed by the administrator." },
    { code: "EXCURSIONS", icon: "⌖", title: "See more of Issyk-Kul", hook: "Send a request and staff will help match an excursion to your day." },
    { code: "BILLIARDS", icon: "●", title: "Billiards after dinner", hook: "Ask for a convenient time and staff will confirm availability." },
    { code: "ADMIN", icon: "AI", title: "Need an idea?", hook: "An administrator can help combine dining, trips, relaxation and hotel services." },
  ],
};

function currentLocale(): Locale {
  if (typeof window === "undefined") return "ru";
  const stored = window.localStorage.getItem("three-crowns-guest-language") || window.localStorage.getItem("three-crowns-site-language");
  return stored === "kg" || stored === "en" ? stored : "ru";
}

export default function GuestMarketplace({ token }: { token: string }) {
  const [locale, setLocale] = useState<Locale>("ru");
  const [authenticated, setAuthenticated] = useState(false);
  const [menu, setMenu] = useState<MenuItem[]>([]);
  const [qty, setQty] = useState<Record<string, number>>({});
  const [guestCount, setGuestCount] = useState(1);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [offerBusy, setOfferBusy] = useState<OfferCode | null>(null);
  const [offerDone, setOfferDone] = useState<OfferCode | null>(null);
  const [aiOpen, setAiOpen] = useState(false);
  const [aiInput, setAiInput] = useState("");
  const [aiBusy, setAiBusy] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);
  const [aiMessages, setAiMessages] = useState<AiMessage[]>([]);

  useEffect(() => {
    const sync = () => setLocale(currentLocale());
    sync();
    window.addEventListener("three-crowns:content-ready", sync);
    return () => window.removeEventListener("three-crowns:content-ready", sync);
  }, []);

  const load = useCallback(async () => {
    try {
      const contextResponse = await fetch(`/core/api/v1/guest-os/rooms/${encodeURIComponent(token)}`, { credentials: "include", cache: "no-store" });
      if (!contextResponse.ok) { setAuthenticated(false); return; }
      const context = await contextResponse.json() as GuestContext;
      if (!context.authenticated || !context.active_stay) { setAuthenticated(false); return; }
      setAuthenticated(true);
      const menuResponse = await fetch(`/core/api/v1/guest-os/rooms/${encodeURIComponent(token)}/kitchen/menu`, { credentials: "include", cache: "no-store" });
      if (!menuResponse.ok) { setMenu([]); return; }
      const menuBody = await menuResponse.json() as { items?: MenuItem[] };
      setMenu((menuBody.items ?? []).filter((item) => item.is_active && !item.is_draft));
    } catch {
      setAuthenticated(false);
      setMenu([]);
    }
  }, [token]);

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(), 20000);
    return () => window.clearInterval(timer);
  }, [load]);

  const selected = useMemo(() => menu.filter((item) => (qty[item.id] ?? 0) > 0), [menu, qty]);
  const total = selected.reduce((sum, item) => sum + item.price_kgs * (qty[item.id] ?? 0), 0);
  const grouped = useMemo(() => {
    const map = new Map<string, MenuItem[]>();
    menu.forEach((item) => map.set(item.category, [...(map.get(item.category) ?? []), item]));
    return [...map.entries()];
  }, [menu]);
  const c = copy[locale];

  async function createOrder(event: FormEvent) {
    event.preventDefault();
    if (!selected.length || busy) return;
    setBusy(true); setNotice(null);
    try {
      const response = await fetch(`/core/api/v1/guest-os/rooms/${encodeURIComponent(token)}/kitchen/orders`, {
        method: "POST", credentials: "include", headers: { "content-type": "application/json" },
        body: JSON.stringify({ guest_count: guestCount, notes: note.trim() || null, items: selected.map((item) => ({ menu_item_id: item.id, quantity: qty[item.id] })) }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof body?.detail === "string" ? body.detail : "ORDER_FAILED");
      setNotice(c.ordered(body.order_number || "—", Number(body.total_kgs || total)));
      setQty({}); setNote("");
    } catch {
      setNotice(locale === "en" ? "The order could not be created. Please contact the administrator." : locale === "kg" ? "Заказ түзүлгөн жок. Администраторго кайрылыңыз." : "Не удалось создать заказ. Обратитесь к администратору.");
    } finally { setBusy(false); }
  }

  async function requestOffer(code: OfferCode, title: string) {
    if (offerBusy) return;
    setOfferBusy(code); setOfferDone(null);
    try {
      const response = await fetch(`/core/api/v1/guest-os/rooms/${encodeURIComponent(token)}/requests`, {
        method: "POST", credentials: "include", headers: { "content-type": "application/json" },
        body: JSON.stringify({ request_code: code, description: `Guest offer: ${title}`, service_date: null, service_time: null }),
      });
      if (!response.ok) throw new Error();
      setOfferDone(code);
    } catch {
      setOfferDone(null);
    } finally { setOfferBusy(null); }
  }

  async function askAi(event: FormEvent) {
    event.preventDefault();
    const text = aiInput.trim();
    if (!text || aiBusy) return;
    const next = [...aiMessages, { role: "user" as const, content: text }];
    setAiMessages(next); setAiInput(""); setAiBusy(true); setAiError(null);
    try {
      const response = await fetch("/core/api/v1/public/ai-admin/chat", {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ messages: next.slice(-10), locale }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error();
      setAiMessages((current) => [...current, { role: "assistant", content: String(body.answer || "") }]);
    } catch {
      setAiError(c.aiError);
    } finally { setAiBusy(false); }
  }

  if (!authenticated) return null;

  return <section className="guest-marketplace" aria-label={c.title}>
    <div className="guest-marketplace-intro"><p>{c.eyebrow}</p><h2>{c.title}</h2><span>{c.intro}</span></div>

    <div className="guest-marketplace-grid">
      <article className="guest-dining-market">
        <div className="guest-market-head"><div><small>Kitchen · Resort Core</small><h3>{c.dining}</h3><p>{c.diningNote}</p></div><b>{menu.length}</b></div>
        {!menu.length ? <div className="guest-market-empty">{c.noMenu}</div> : <form onSubmit={createOrder}>
          <div className="guest-menu-groups">{grouped.map(([category, items]) => <section key={category}><div className="guest-menu-category">{category}</div>{items.map((item) => <label className="guest-menu-item" key={item.id}><span><strong>{locale === "kg" ? item.name_kg : locale === "en" ? item.name_en : item.name_ru}</strong><small>{item.price_kgs.toLocaleString(locale === "en" ? "en-US" : "ru-RU")} KGS</small></span><input type="number" min="0" max="20" value={qty[item.id] ?? 0} onChange={(event) => setQty((current) => ({ ...current, [item.id]: Math.max(0, Number(event.target.value) || 0) }))} /></label>)}</section>)}</div>
          <div className="guest-order-fields"><label>{c.guests}<input type="number" min="1" max="20" value={guestCount} onChange={(event) => setGuestCount(Math.max(1, Number(event.target.value) || 1))} /></label><label>{c.comment}<input value={note} maxLength={1000} onChange={(event) => setNote(event.target.value)} placeholder={c.commentPlaceholder} /></label></div>
          <div className="guest-order-total"><span>{c.total}</span><strong>{total.toLocaleString(locale === "en" ? "en-US" : "ru-RU")} KGS</strong></div>
          {notice && <div className="guest-market-notice">{notice}</div>}
          <button className="guest-market-primary" disabled={!selected.length || busy}>{busy ? c.ordering : c.order}</button>
        </form>}
      </article>

      <aside className="guest-market-side">
        <article className="guest-ai-card">
          <div className="guest-market-head"><div><small>AI · verified facts</small><h3>{c.aiTitle}</h3><p>{c.aiNote}</p></div><button className="guest-ai-toggle" onClick={() => setAiOpen((value) => !value)}>{aiOpen ? "×" : "AI"}</button></div>
          {aiOpen && <div className="guest-ai-body">
            <div className="guest-ai-prompts">{(locale === "en" ? ["What can we do this evening?", "Tell me about the beach and spa", "Help plan tomorrow"] : locale === "kg" ? ["Кечинде эмне кылса болот?", "Пляж жана SPA тууралуу айтып бер", "Эртеңки күндү пландап бер"] : ["Что можно сделать вечером?", "Расскажи про пляж и SPA", "Помоги спланировать завтра"]).map((prompt) => <button key={prompt} onClick={() => setAiInput(prompt)}>{prompt}</button>)}</div>
            <div className="guest-ai-messages">{aiMessages.map((message, index) => <div key={`${message.role}-${index}`} data-role={message.role}>{message.content}</div>)}{aiBusy && <div data-role="assistant">{c.aiThinking}</div>}{aiError && <div className="guest-ai-error">{aiError}</div>}</div>
            <form onSubmit={askAi}><input value={aiInput} maxLength={1600} onChange={(event) => setAiInput(event.target.value)} placeholder={c.aiPlaceholder} /><button disabled={!aiInput.trim() || aiBusy}>{c.aiSend}</button></form>
          </div>}
        </article>

        {KOL_MARKETPLACE_URL && <article className="guest-kol-card"><small>KÖL · partner bridge</small><h3>{c.kolTitle}</h3><p>{c.kolText}</p><a href={KOL_MARKETPLACE_URL} target="_blank" rel="noreferrer">{c.kolOpen} ↗</a></article>}
      </aside>
    </div>

    <div className="guest-offers-head"><div><p>{c.eyebrow}</p><h3>{c.offers}</h3></div><span>{c.offersNote}</span></div>
    <div className="guest-offer-grid">{offerCopy[locale].map((offer) => <article key={offer.code}><i>{offer.icon}</i><h4>{offer.title}</h4><p>{offer.hook}</p><button disabled={offerBusy === offer.code} onClick={() => void requestOffer(offer.code, offer.title)}>{offerDone === offer.code ? c.requested : c.want}</button></article>)}</div>
  </section>;
}
