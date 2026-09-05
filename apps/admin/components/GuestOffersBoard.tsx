"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type ActionType = "GUEST_REQUEST" | "EXTERNAL_URL" | "AI_PROMPT";
type Analytics = { clicks: number; requests: number; external_opens: number; ai_prompts: number };
type Campaign = {
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
  action_type: ActionType;
  request_code?: string | null;
  external_url?: string | null;
  ai_prompt?: string | null;
  active_from?: string | null;
  active_to?: string | null;
  min_adults: number;
  min_children: number;
  min_stay_nights: number;
  max_stay_nights?: number | null;
  priority: number;
  sort_order: number;
  is_active: boolean;
  analytics?: Analytics;
};

type FormState = Omit<Campaign, "id" | "analytics" | "active_from" | "active_to"> & {
  active_from: string;
  active_to: string;
  max_stay_nights: number | "";
};

const REQUEST_CODES = [
  ["TRANSFER", "Трансфер"],
  ["MEALS", "Питание"],
  ["PARKING", "Парковка"],
  ["SAUNA", "Сауна"],
  ["BILLIARDS", "Бильярд"],
  ["EXCURSIONS", "Экскурсии / туры"],
  ["ADMIN", "Администратор"],
  ["HOUSEKEEPING", "Уборка"],
  ["TOWELS", "Полотенца"],
  ["LINEN", "Бельё"],
  ["MAINTENANCE", "Поломка"],
] as const;

const emptyForm: FormState = {
  code: "",
  title_ru: "",
  title_kg: "",
  title_en: "",
  hook_ru: "",
  hook_kg: "",
  hook_en: "",
  cta_ru: "Хочу",
  cta_kg: "Каалайм",
  cta_en: "Request",
  image_url: "",
  action_type: "GUEST_REQUEST",
  request_code: "ADMIN",
  external_url: "",
  ai_prompt: "",
  active_from: "",
  active_to: "",
  min_adults: 0,
  min_children: 0,
  min_stay_nights: 0,
  max_stay_nights: "",
  priority: 100,
  sort_order: 0,
  is_active: false,
};

function toLocalInput(value?: string | null) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const shifted = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return shifted.toISOString().slice(0, 16);
}

function fromCampaign(item: Campaign): FormState {
  return {
    code: item.code,
    title_ru: item.title_ru,
    title_kg: item.title_kg,
    title_en: item.title_en,
    hook_ru: item.hook_ru,
    hook_kg: item.hook_kg,
    hook_en: item.hook_en,
    cta_ru: item.cta_ru,
    cta_kg: item.cta_kg,
    cta_en: item.cta_en,
    image_url: item.image_url || "",
    action_type: item.action_type,
    request_code: item.request_code || "ADMIN",
    external_url: item.external_url || "",
    ai_prompt: item.ai_prompt || "",
    active_from: toLocalInput(item.active_from),
    active_to: toLocalInput(item.active_to),
    min_adults: item.min_adults,
    min_children: item.min_children,
    min_stay_nights: item.min_stay_nights,
    max_stay_nights: item.max_stay_nights ?? "",
    priority: item.priority,
    sort_order: item.sort_order,
    is_active: item.is_active,
  };
}

async function api(path: string, init?: RequestInit) {
  const response = await fetch(path, { cache: "no-store", ...init });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = body?.detail;
    throw new Error(typeof detail === "string" ? detail : detail?.code || "Ошибка Resort Core");
  }
  return body;
}

function localizeAction(item: Campaign) {
  if (item.action_type === "GUEST_REQUEST") return `Заявка · ${item.request_code || "—"}`;
  if (item.action_type === "EXTERNAL_URL") return "Внешний HTTPS-каталог";
  return "AI-сценарий";
}

export default function GuestOffersBoard() {
  const [items, setItems] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const body = await api("/core/api/v1/admin/guest-offers");
      setItems(body.items ?? []);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось загрузить офферы");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const totals = useMemo(() => items.reduce((acc, item) => {
    acc.active += item.is_active ? 1 : 0;
    acc.clicks += item.analytics?.clicks ?? 0;
    acc.requests += item.analytics?.requests ?? 0;
    acc.external += item.analytics?.external_opens ?? 0;
    acc.ai += item.analytics?.ai_prompts ?? 0;
    return acc;
  }, { active: 0, clicks: 0, requests: 0, external: 0, ai: 0 }), [items]);

  function resetForm() {
    setEditingId(null);
    setForm(emptyForm);
    setNotice(null);
  }

  function edit(item: Campaign) {
    setEditingId(item.id);
    setForm(fromCampaign(item));
    setNotice(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function payload() {
    return {
      ...form,
      code: form.code.trim().toUpperCase(),
      image_url: form.image_url?.trim() || null,
      request_code: form.action_type === "GUEST_REQUEST" ? form.request_code : null,
      external_url: form.action_type === "EXTERNAL_URL" ? form.external_url?.trim() || null : null,
      ai_prompt: form.action_type === "AI_PROMPT" ? form.ai_prompt?.trim() || null : null,
      active_from: form.active_from ? new Date(form.active_from).toISOString() : null,
      active_to: form.active_to ? new Date(form.active_to).toISOString() : null,
      max_stay_nights: form.max_stay_nights === "" ? null : Number(form.max_stay_nights),
    };
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy("save");
    setError(null);
    setNotice(null);
    try {
      const path = editingId ? `/core/api/v1/admin/guest-offers/${editingId}` : "/core/api/v1/admin/guest-offers";
      await api(path, {
        method: editingId ? "PUT" : "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload()),
      });
      setNotice(editingId ? "Оффер обновлён." : "Оффер создан. По умолчанию он не должен быть активным, пока вы не проверили контент и действие.");
      resetForm();
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось сохранить оффер");
    } finally {
      setBusy(null);
    }
  }

  async function toggle(item: Campaign) {
    setBusy(item.id);
    setError(null);
    try {
      await api(`/core/api/v1/admin/guest-offers/${item.id}/active`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ is_active: !item.is_active }),
      });
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось изменить статус оффера");
    } finally {
      setBusy(null);
    }
  }

  return <main className="work-shell guest-offers-shell">
    <div className="work-head guest-offers-head">
      <div><p className="eyebrow">Guest OS · upsell control</p><h1>Офферы гостю</h1><p className="subtitle">Управляемые предложения внутри авторизованного кабинета гостя. Оффер создаёт заявку, открывает HTTPS-каталог или запускает AI-сценарий — но не подтверждает цену, наличие, оплату или выполнение услуги.</p></div>
      <button className="btn" onClick={() => void load()}>Обновить</button>
    </div>

    <section className="guest-offer-kpis">
      <article><strong>{items.length}</strong><span>кампаний</span></article>
      <article><strong>{totals.active}</strong><span>активны сейчас</span></article>
      <article><strong>{totals.clicks}</strong><span>кликов</span></article>
      <article><strong>{totals.requests}</strong><span>заявок</span></article>
      <article><strong>{totals.external}</strong><span>переходов наружу</span></article>
      <article><strong>{totals.ai}</strong><span>AI-сценариев</span></article>
    </section>

    {error && <div className="error-box">{error}</div>}
    {notice && <div className="guest-offer-notice">{notice}</div>}

    <section className="guest-offer-layout">
      <form className="guest-offer-editor" onSubmit={submit}>
        <div className="guest-offer-section-head"><div><p className="eyebrow">{editingId ? "Редактирование" : "Новая кампания"}</p><h2>{editingId ? "Изменить оффер" : "Создать оффер"}</h2></div>{editingId && <button type="button" className="btn" onClick={resetForm}>Новый</button>}</div>

        <div className="guest-offer-form-grid">
          <label><span>Код</span><input value={form.code} onChange={(e) => setForm((current) => ({ ...current, code: e.target.value }))} placeholder="TRANSFER_VIP" required /></label>
          <label><span>Действие</span><select value={form.action_type} onChange={(e) => setForm((current) => ({ ...current, action_type: e.target.value as ActionType }))}><option value="GUEST_REQUEST">Заявка сотрудникам</option><option value="EXTERNAL_URL">Внешний HTTPS-каталог</option><option value="AI_PROMPT">AI-сценарий</option></select></label>
          {form.action_type === "GUEST_REQUEST" && <label><span>Тип заявки</span><select value={form.request_code || "ADMIN"} onChange={(e) => setForm((current) => ({ ...current, request_code: e.target.value }))}>{REQUEST_CODES.map(([code, label]) => <option key={code} value={code}>{label}</option>)}</select></label>}
          {form.action_type === "EXTERNAL_URL" && <label className="span-2"><span>HTTPS ссылка</span><input type="url" value={form.external_url || ""} onChange={(e) => setForm((current) => ({ ...current, external_url: e.target.value }))} placeholder="https://partner.example/..." required /></label>}
          {form.action_type === "AI_PROMPT" && <label className="span-2"><span>Стартовый AI-сценарий</span><textarea value={form.ai_prompt || ""} onChange={(e) => setForm((current) => ({ ...current, ai_prompt: e.target.value }))} placeholder="Помоги гостю выбрать вечерний сценарий отдыха на основе подтверждённых сервисов отеля." required /></label>}
          <label className="span-2"><span>Картинка — HTTPS или /media/…</span><input value={form.image_url || ""} onChange={(e) => setForm((current) => ({ ...current, image_url: e.target.value }))} placeholder="/media/three-crowns/spa.webp" /></label>
        </div>

        <fieldset><legend>Русский</legend><div className="guest-offer-form-grid"><label><span>Заголовок</span><input value={form.title_ru} onChange={(e) => setForm((current) => ({ ...current, title_ru: e.target.value }))} required /></label><label><span>CTA</span><input value={form.cta_ru} onChange={(e) => setForm((current) => ({ ...current, cta_ru: e.target.value }))} required /></label><label className="span-2"><span>Hook / предложение</span><textarea value={form.hook_ru} onChange={(e) => setForm((current) => ({ ...current, hook_ru: e.target.value }))} required /></label></div></fieldset>
        <fieldset><legend>Кыргызча</legend><div className="guest-offer-form-grid"><label><span>Заголовок</span><input value={form.title_kg} onChange={(e) => setForm((current) => ({ ...current, title_kg: e.target.value }))} required /></label><label><span>CTA</span><input value={form.cta_kg} onChange={(e) => setForm((current) => ({ ...current, cta_kg: e.target.value }))} required /></label><label className="span-2"><span>Hook / предложение</span><textarea value={form.hook_kg} onChange={(e) => setForm((current) => ({ ...current, hook_kg: e.target.value }))} required /></label></div></fieldset>
        <fieldset><legend>English</legend><div className="guest-offer-form-grid"><label><span>Title</span><input value={form.title_en} onChange={(e) => setForm((current) => ({ ...current, title_en: e.target.value }))} required /></label><label><span>CTA</span><input value={form.cta_en} onChange={(e) => setForm((current) => ({ ...current, cta_en: e.target.value }))} required /></label><label className="span-2"><span>Hook</span><textarea value={form.hook_en} onChange={(e) => setForm((current) => ({ ...current, hook_en: e.target.value }))} required /></label></div></fieldset>

        <fieldset><legend>Период и аудитория</legend><div className="guest-offer-form-grid"><label><span>Активно с</span><input type="datetime-local" value={form.active_from} onChange={(e) => setForm((current) => ({ ...current, active_from: e.target.value }))} /></label><label><span>Активно до</span><input type="datetime-local" value={form.active_to} onChange={(e) => setForm((current) => ({ ...current, active_to: e.target.value }))} /></label><label><span>Мин. взрослых</span><input type="number" min="0" max="30" value={form.min_adults} onChange={(e) => setForm((current) => ({ ...current, min_adults: Number(e.target.value) || 0 }))} /></label><label><span>Мин. детей</span><input type="number" min="0" max="30" value={form.min_children} onChange={(e) => setForm((current) => ({ ...current, min_children: Number(e.target.value) || 0 }))} /></label><label><span>Мин. ночей</span><input type="number" min="0" max="120" value={form.min_stay_nights} onChange={(e) => setForm((current) => ({ ...current, min_stay_nights: Number(e.target.value) || 0 }))} /></label><label><span>Макс. ночей</span><input type="number" min="0" max="120" value={form.max_stay_nights} onChange={(e) => setForm((current) => ({ ...current, max_stay_nights: e.target.value === "" ? "" : Number(e.target.value) }))} /></label><label><span>Приоритет</span><input type="number" min="0" max="10000" value={form.priority} onChange={(e) => setForm((current) => ({ ...current, priority: Number(e.target.value) || 0 }))} /></label><label><span>Порядок</span><input type="number" min="0" max="10000" value={form.sort_order} onChange={(e) => setForm((current) => ({ ...current, sort_order: Number(e.target.value) || 0 }))} /></label></div></fieldset>

        <label className="guest-offer-active-checkbox"><input type="checkbox" checked={form.is_active} onChange={(e) => setForm((current) => ({ ...current, is_active: e.target.checked }))} /><span>Сразу активировать после сохранения</span></label>
        <p className="guest-offer-warning">Активируйте только после проверки RU/KG/EN, действия, периода и ссылки. Внешние действия принимаются только по HTTPS.</p>
        <button className="btn primary guest-offer-save" disabled={busy === "save"}>{busy === "save" ? "Сохраняю…" : editingId ? "Сохранить изменения" : "Создать кампанию"}</button>
      </form>

      <section className="guest-offer-list-panel">
        <div className="guest-offer-section-head"><div><p className="eyebrow">Guest Marketplace</p><h2>Кампании</h2></div><span>{loading ? "Загрузка…" : `${items.length} шт.`}</span></div>
        {!loading && !items.length && <div className="empty">Офферов пока нет. Создайте первый управляемый оффер слева.</div>}
        <div className="guest-offer-list">{items.map((item) => <article key={item.id} className={item.is_active ? "active" : ""}>
          {item.image_url && <div className="guest-offer-thumb" style={{ backgroundImage: `url(${item.image_url})` }} aria-hidden="true" />}
          <div className="guest-offer-card-main"><div className="guest-offer-card-top"><div><small>{item.code}</small><h3>{item.title_ru}</h3></div><span className={item.is_active ? "live" : "off"}>{item.is_active ? "LIVE" : "OFF"}</span></div><p>{item.hook_ru}</p><div className="guest-offer-meta"><span>{localizeAction(item)}</span><span>Приоритет {item.priority}</span><span>Ночей {item.min_stay_nights}–{item.max_stay_nights ?? "∞"}</span></div><div className="guest-offer-analytics"><span><b>{item.analytics?.clicks ?? 0}</b> кликов</span><span><b>{item.analytics?.requests ?? 0}</b> заявок</span><span><b>{item.analytics?.external_opens ?? 0}</b> переходов</span><span><b>{item.analytics?.ai_prompts ?? 0}</b> AI</span></div><div className="guest-offer-card-actions"><button className="btn" onClick={() => edit(item)}>Редактировать</button><button className={item.is_active ? "btn guest-offer-stop" : "btn primary"} disabled={busy === item.id} onClick={() => void toggle(item)}>{item.is_active ? "Выключить" : "Включить"}</button></div></div>
        </article>)}</div>
      </section>
    </section>
  </main>;
}
