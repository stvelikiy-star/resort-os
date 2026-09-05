"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type Locale = "ru" | "kg" | "en";
type GuestContext = { authenticated: boolean; active_stay: boolean; room: { code: string }; guest: { first_name: string } | null };
type MenuItem = { id: string; code: string; category: string; name_ru: string; name_kg: string; name_en: string; price_kgs: number; is_active: boolean; is_draft: boolean; sort_order: number; meal_types?: string[] };
type AiMessage = { role: "user" | "assistant"; content: string };
type OfferAction = "GUEST_REQUEST" | "EXTERNAL_URL" | "AI_PROMPT";
type OfferCampaign = {
  id: string;
  code: string;
  title_ru: string;
  title_kg: string;
  title_en: string;
  hook_ru: string;
  hook_kg: string;
  hook_en: string;
  cta_ru: string;
  cta_kg: string;
  cta_en: string;
  image_url?: string | null;
  action_type: OfferAction;
  request_code?: string | null;
  external_url?: string | null;
  ai_prompt?: string | null;
};

const copy = {
  ru: {
    eyebrow: "Для вашего отдыха",
    title: "Всё, что можно заказать — в одном месте",
    intro: "Меню кухни, услуги отеля и персональные предложения. Заказ или заявка сразу попадает в Resort OS — сотрудник подтверждает доступность и условия.",
    dining: "Меню на сегодня",
    diningNote: "Только блюда, которые кухня утвердила и опубликовала на текущую дату. Стоп-лист исчезает у гостя автоматически.",
    noMenu: "Кухня ещё не опубликовала доступное меню на сегодня. Уточните у администратора.",
    guests: "Гостей",
    comment: "Комментарий к заказу",
    commentPlaceholder: "Например: без лука, приборы на двоих",
    total: "Итого по меню",
    order: "Заказать в номер",
    ordering: "Отправляем заказ…",
    ordered: (number: string, total: number) => `Заказ ${number} создан · ${total.toLocaleString("ru-RU")} сом. Кухня увидит его в своей очереди.`,
    offers: "Предложения для вас",
    offersNote: "Эти предложения управляются отелем. Услуга не подтверждается автоматически: сотрудник подтверждает наличие, цену и финальные условия там, где это требуется.",
    requested: "Заявка отправлена",
    opened: "Открываем…",
    offerError: "Не удалось выполнить действие. Обратитесь к администратору.",
    aiTitle: "AI-консьерж",
    aiNote: "Спросите об отеле, территории, отдыхе и услугах. AI отвечает только по подтверждённым данным Resort Core.",
    aiPlaceholder: "Например: что можно сделать вечером?",
    aiSend: "Спросить",
    aiThinking: "Проверяю…",
    aiError: "AI сейчас недоступен. Можно отправить заявку администратору.",
  },
  kg: {
    eyebrow: "Эс алууңуз үчүн",
    title: "Заказ кылууга боло турган нерселердин баары бир жерде",
    intro: "Ашкана менюсу, мейманкана кызматтары жана жеке сунуштар. Заказ же өтүнмө Resort OS системасына түшөт — кызматкер жеткиликтүүлүктү жана шарттарды ырастайт.",
    dining: "Бүгүнкү меню",
    diningNote: "Ашкана бүгүнкү күнгө ырастап, жарыялаган тамактар гана көрсөтүлөт. Стоп-лист коноктон автоматтык түрдө жашырылат.",
    noMenu: "Ашкана бүгүнкү жеткиликтүү менюну азырынча жарыялаган жок. Администратордон тактаңыз.",
    guests: "Коноктор",
    comment: "Заказга комментарий",
    commentPlaceholder: "Мисалы: пиязсыз, эки кишиге прибор",
    total: "Меню боюнча сумма",
    order: "Бөлмөгө заказ кылуу",
    ordering: "Заказ жөнөтүлүүдө…",
    ordered: (number: string, total: number) => `Заказ ${number} түзүлдү · ${total.toLocaleString("ru-RU")} сом. Ашкана аны кезекте көрөт.`,
    offers: "Сиз үчүн сунуштар",
    offersNote: "Бул сунуштарды мейманкана башкарат. Кызмат автоматтык түрдө ырасталбайт; керек болгон жерде бааны, жеткиликтүүлүктү жана акыркы шарттарды кызматкер ырастайт.",
    requested: "Өтүнмө жөнөтүлдү",
    opened: "Ачылууда…",
    offerError: "Аракет аткарылган жок. Администраторго кайрылыңыз.",
    aiTitle: "AI-консьерж",
    aiNote: "Мейманкана, аймак, эс алуу жана кызматтар тууралуу сураңыз. AI Resort Core'догу ырасталган маалыматтар боюнча гана жооп берет.",
    aiPlaceholder: "Мисалы: кечинде эмне кылса болот?",
    aiSend: "Суроо берүү",
    aiThinking: "Текшерип жатам…",
    aiError: "AI азыр жеткиликсиз. Администраторго өтүнмө жөнөтсөңүз болот.",
  },
  en: {
    eyebrow: "For your stay",
    title: "Everything you can request, in one place",
    intro: "Kitchen menu, hotel services and personal offers. Every order or request goes straight into Resort OS for staff confirmation.",
    dining: "Today’s menu",
    diningNote: "Only dishes explicitly approved and published by the kitchen for the current hotel date are shown. Sold-out items disappear automatically.",
    noMenu: "The kitchen has not published an available guest menu for today yet. Please ask the administrator.",
    guests: "Guests",
    comment: "Order note",
    commentPlaceholder: "For example: no onion, cutlery for two",
    total: "Menu total",
    order: "Order to room",
    ordering: "Sending order…",
    ordered: (number: string, total: number) => `Order ${number} created · ${total.toLocaleString("en-US")} KGS. The kitchen can now see it in its queue.`,
    offers: "Recommended for you",
    offersNote: "These offers are managed by the hotel. Services are not auto-confirmed; staff confirm availability, price and final terms where required.",
    requested: "Request sent",
    opened: "Opening…",
    offerError: "The action could not be completed. Please contact the administrator.",
    aiTitle: "AI concierge",
    aiNote: "Ask about the hotel, resort, stay and services. AI answers only from verified Resort Core facts.",
    aiPlaceholder: "For example: what can we do this evening?",
    aiSend: "Ask",
    aiThinking: "Checking…",
    aiError: "AI is unavailable right now. You can send an administrator request.",
  },
} as const;

function currentLocale(): Locale {
  if (typeof window === "undefined") return "ru";
  const stored = window.localStorage.getItem("three-crowns-guest-language") || window.localStorage.getItem("three-crowns-site-language");
  return stored === "kg" || stored === "en" ? stored : "ru";
}

function localized(item: OfferCampaign, locale: Locale) {
  if (locale === "kg") return { title: item.title_kg, hook: item.hook_kg, cta: item.cta_kg };
  if (locale === "en") return { title: item.title_en, hook: item.hook_en, cta: item.cta_en };
  return { title: item.title_ru, hook: item.hook_ru, cta: item.cta_ru };
}

function offerGlyph(action: OfferAction) {
  if (action === "EXTERNAL_URL") return "↗";
  if (action === "AI_PROMPT") return "AI";
  return "+";
}

export default function GuestMarketplace({ token }: { token: string }) {
  const [locale, setLocale] = useState<Locale>("ru");
  const [authenticated, setAuthenticated] = useState(false);
  const [menu, setMenu] = useState<MenuItem[]>([]);
  const [serviceDate, setServiceDate] = useState<string | null>(null);
  const [offers, setOffers] = useState<OfferCampaign[]>([]);
  const [qty, setQty] = useState<Record<string, number>>({});
  const [guestCount, setGuestCount] = useState(1);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [offerBusy, setOfferBusy] = useState<string | null>(null);
  const [offerDone, setOfferDone] = useState<string | null>(null);
  const [offerError, setOfferError] = useState<string | null>(null);
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

      const [menuResponse, offersResponse] = await Promise.all([
        fetch(`/core/api/v1/guest-os/rooms/${encodeURIComponent(token)}/kitchen/menu`, { credentials: "include", cache: "no-store" }),
        fetch(`/core/api/v1/guest-os/rooms/${encodeURIComponent(token)}/offers`, { credentials: "include", cache: "no-store" }),
      ]);

      if (menuResponse.ok) {
        const menuBody = await menuResponse.json() as { service_date?: string; items?: MenuItem[] };
        setServiceDate(menuBody.service_date || null);
        setMenu((menuBody.items ?? []).filter((item) => item.is_active && !item.is_draft));
      } else {
        setMenu([]);
      }

      if (offersResponse.ok) {
        const offerBody = await offersResponse.json() as { items?: OfferCampaign[] };
        setOffers(offerBody.items ?? []);
      } else {
        setOffers([]);
      }
    } catch {
      setAuthenticated(false);
      setMenu([]);
      setOffers([]);
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
      await load();
    } catch {
      setNotice(locale === "en" ? "The order could not be created. Please contact the administrator." : locale === "kg" ? "Заказ түзүлгөн жок. Администраторго кайрылыңыз." : "Не удалось создать заказ. Обратитесь к администратору.");
    } finally { setBusy(false); }
  }

  async function recordOfferEvent(offer: OfferCampaign, eventType: "CLICK" | "REQUEST" | "EXTERNAL_OPEN" | "AI_PROMPT") {
    await fetch(`/core/api/v1/guest-os/rooms/${encodeURIComponent(token)}/offers/${encodeURIComponent(offer.id)}/events`, {
      method: "POST",
      credentials: "include",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ event_type: eventType }),
    }).catch(() => undefined);
  }

  async function askAiText(text: string) {
    if (!text.trim() || aiBusy) return;
    const next = [...aiMessages, { role: "user" as const, content: text.trim() }];
    setAiOpen(true);
    setAiMessages(next);
    setAiInput("");
    setAiBusy(true);
    setAiError(null);
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

  async function askAi(event: FormEvent) {
    event.preventDefault();
    await askAiText(aiInput);
  }

  async function activateOffer(offer: OfferCampaign) {
    if (offerBusy) return;
    const content = localized(offer, locale);
    setOfferBusy(offer.id);
    setOfferDone(null);
    setOfferError(null);
    void recordOfferEvent(offer, "CLICK");
    try {
      if (offer.action_type === "GUEST_REQUEST") {
        if (!offer.request_code) throw new Error("MISSING_REQUEST_CODE");
        const response = await fetch(`/core/api/v1/guest-os/rooms/${encodeURIComponent(token)}/requests`, {
          method: "POST", credentials: "include", headers: { "content-type": "application/json" },
          body: JSON.stringify({ request_code: offer.request_code, description: `Guest offer ${offer.code}: ${content.title}`, service_date: null, service_time: null }),
        });
        if (!response.ok) throw new Error("REQUEST_FAILED");
        await recordOfferEvent(offer, "REQUEST");
        setOfferDone(offer.id);
      } else if (offer.action_type === "EXTERNAL_URL") {
        if (!offer.external_url || !offer.external_url.startsWith("https://")) throw new Error("INVALID_EXTERNAL_URL");
        await recordOfferEvent(offer, "EXTERNAL_OPEN");
        window.open(offer.external_url, "_blank", "noopener,noreferrer");
        setOfferDone(offer.id);
      } else {
        if (!offer.ai_prompt) throw new Error("MISSING_AI_PROMPT");
        await recordOfferEvent(offer, "AI_PROMPT");
        setOfferDone(offer.id);
        await askAiText(offer.ai_prompt);
      }
    } catch {
      setOfferError(c.offerError);
    } finally {
      setOfferBusy(null);
    }
  }

  if (!authenticated) return null;

  return <section className="guest-marketplace" aria-label={c.title}>
    <div className="guest-marketplace-intro"><p>{c.eyebrow}</p><h2>{c.title}</h2><span>{c.intro}</span></div>

    <div className="guest-marketplace-grid">
      <article className="guest-dining-market">
        <div className="guest-market-head"><div><small>Kitchen · Resort Core{serviceDate ? ` · ${serviceDate}` : ""}</small><h3>{c.dining}</h3><p>{c.diningNote}</p></div><b>{menu.length}</b></div>
        {!menu.length ? <div className="guest-market-empty">{c.noMenu}</div> : <form onSubmit={createOrder}>
          <div className="guest-menu-groups">{grouped.map(([category, items]) => <section key={category}><div className="guest-menu-category">{category}</div>{items.map((item) => <label className="guest-menu-item" key={item.id}><span><strong>{locale === "kg" ? item.name_kg : locale === "en" ? item.name_en : item.name_ru}</strong><small>{item.price_kgs.toLocaleString(locale === "en" ? "en-US" : "ru-RU")} KGS{item.meal_types?.length ? ` · ${item.meal_types.join(" / ")}` : ""}</small></span><input type="number" min="0" max="20" value={qty[item.id] ?? 0} onChange={(event) => setQty((current) => ({ ...current, [item.id]: Math.max(0, Number(event.target.value) || 0) }))} /></label>)}</section>)}</div>
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
      </aside>
    </div>

    {offers.length > 0 && <>
      <div className="guest-offers-head"><div><p>{c.eyebrow}</p><h3>{c.offers}</h3></div><span>{c.offersNote}</span></div>
      {offerError && <div className="guest-market-notice guest-offer-action-error">{offerError}</div>}
      <div className="guest-offer-grid">{offers.map((offer) => {
        const content = localized(offer, locale);
        return <article key={offer.id} className="guest-managed-offer">
          {offer.image_url && <div className="guest-managed-offer-image" style={{ backgroundImage: `url(${offer.image_url})` }} aria-hidden="true" />}
          <i>{offerGlyph(offer.action_type)}</i><small>{offer.code}</small><h4>{content.title}</h4><p>{content.hook}</p><button disabled={offerBusy === offer.id} onClick={() => void activateOffer(offer)}>{offerDone === offer.id ? (offer.action_type === "GUEST_REQUEST" ? c.requested : c.opened) : content.cta}</button>
        </article>;
      })}</div>
    </>}
  </section>;
}
