"use client";

import { ChangeEvent, useEffect, useMemo, useState } from "react";

type Locale = "ru" | "kg" | "en";
type Content = Record<string, Record<string, string>>;
type ContentItem = {
  locale: Locale;
  draft: Content;
  published: Content;
  version: number;
  published_version: number;
  published_at: string | null;
  updated_at: string | null;
  source: string;
};

const LOCALES: { code: Locale; label: string }[] = [
  { code: "ru", label: "Русский" },
  { code: "kg", label: "Кыргызча" },
  { code: "en", label: "English" },
];

const FIELDS = [
  { section: "hero", label: "Первый экран", fields: [
    ["eyebrow", "Надзаголовок"], ["title", "Главный заголовок"], ["copy", "Описание"],
    ["primary_cta", "Главная кнопка"], ["secondary_cta", "Вторая кнопка"],
  ] },
  { section: "booking", label: "Бронирование", fields: [
    ["eyebrow", "Надзаголовок"], ["title", "Заголовок"], ["intro", "Описание"],
  ] },
  { section: "advantages", label: "Преимущества", fields: [
    ["eyebrow", "Надзаголовок"], ["title", "Заголовок"], ["intro", "Описание"],
  ] },
  { section: "groups", label: "Групповые заезды", fields: [
    ["eyebrow", "Надзаголовок"], ["title", "Заголовок"], ["copy", "Описание"],
  ] },
  { section: "contacts", label: "Контакты", fields: [
    ["phone", "Телефон бронирования"], ["whatsapp", "WhatsApp менеджера"], ["email", "Email"], ["address", "Адрес"],
  ] },
  { section: "seo", label: "SEO", fields: [
    ["title", "Title страницы"], ["description", "Meta description"],
  ] },
] as const;

function cloneContent(value: Content): Content {
  return JSON.parse(JSON.stringify(value)) as Content;
}

export default function SiteContentBoard() {
  const [items, setItems] = useState<ContentItem[]>([]);
  const [locale, setLocale] = useState<Locale>("ru");
  const [drafts, setDrafts] = useState<Record<Locale, Content> | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/core/api/v1/admin/site/content", { cache: "no-store" });
      if (!response.ok) throw new Error(`CMS ${response.status}`);
      const payload = (await response.json()) as { items: ContentItem[] };
      setItems(payload.items);
      const next = {} as Record<Locale, Content>;
      for (const entry of payload.items) next[entry.locale] = cloneContent(entry.draft);
      setDrafts(next);
    } catch {
      setError("Контент API недоступен. Проверьте Resort Core и Prisma-миграцию 1_site_content.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);

  const currentMeta = useMemo(() => items.find((item) => item.locale === locale), [items, locale]);
  const current = drafts?.[locale];

  function change(section: string, key: string, event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) {
    const value = event.target.value;
    setDrafts((previous) => {
      if (!previous) return previous;
      const next = { ...previous, [locale]: cloneContent(previous[locale]) };
      next[locale][section] = { ...(next[locale][section] || {}), [key]: value };
      return next;
    });
    setMessage(null);
  }

  async function saveDraft() {
    if (!current) return;
    setSaving(true); setError(null); setMessage(null);
    try {
      const response = await fetch(`/core/api/v1/admin/site/content/${locale}/draft`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: current }),
      });
      if (!response.ok) throw new Error(`SAVE ${response.status}`);
      setMessage("Черновик сохранён. На публичном сайте ничего не изменилось.");
      await load();
    } catch {
      setError("Не удалось сохранить черновик.");
    } finally { setSaving(false); }
  }

  async function publish() {
    if (!current) return;
    setSaving(true); setError(null); setMessage(null);
    try {
      const saved = await fetch(`/core/api/v1/admin/site/content/${locale}/draft`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: current }),
      });
      if (!saved.ok) throw new Error(`SAVE ${saved.status}`);
      const response = await fetch(`/core/api/v1/admin/site/content/${locale}/publish`, { method: "POST" });
      if (!response.ok) throw new Error(`PUBLISH ${response.status}`);
      setMessage("Опубликовано. Публичный сайт получит новую версию через Core.");
      await load();
    } catch {
      setError("Не удалось опубликовать контент.");
    } finally { setSaving(false); }
  }

  function exportJson() {
    if (!drafts) return;
    const blob = new Blob([JSON.stringify(drafts, null, 2)], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `three-crowns-site-content-${new Date().toISOString().slice(0, 10)}.json`;
    link.click();
    URL.revokeObjectURL(url);
  }

  async function importJson(file: File | null) {
    if (!file) return;
    try {
      const parsed = JSON.parse(await file.text()) as Record<Locale, Content>;
      if (!parsed.ru || !parsed.kg || !parsed.en) throw new Error("LOCALES");
      setDrafts({ ru: parsed.ru, kg: parsed.kg, en: parsed.en });
      setMessage("JSON загружен в редактор. Нажмите «Сохранить» или «Опубликовать» для каждого языка.");
    } catch {
      setError("Неверный JSON контента.");
    }
  }

  if (loading) return <main className="content-board"><div className="content-state">Загружаю контент сайта…</div></main>;
  if (!current || !drafts) return <main className="content-board"><div className="content-state error">{error || "Контент не найден"}</div></main>;

  return (
    <main className="content-board">
      <header className="content-head">
        <div>
          <p className="eyebrow">Сайт / Контент</p>
          <h1>Редактор публичного сайта</h1>
          <p>Тексты и SEO хранятся в Core. Доступность, цены и брони остаются отдельной доменной правдой PMS.</p>
        </div>
        <div className="content-head-actions">
          <button className="btn" onClick={exportJson}>Экспорт JSON</button>
          <label className="btn file-btn">Импорт JSON<input type="file" accept="application/json" onChange={(event) => void importJson(event.target.files?.[0] || null)} /></label>
        </div>
      </header>

      <section className="content-status-row">
        <div className="locale-tabs">{LOCALES.map((entry) => <button key={entry.code} className={locale === entry.code ? "active" : ""} onClick={() => setLocale(entry.code)}>{entry.label}</button>)}</div>
        <div className="publish-status">
          <span>Черновик v{currentMeta?.version ?? 0}</span>
          <span>Опубликовано v{currentMeta?.published_version ?? 0}</span>
          <span>{currentMeta?.published_at ? new Date(currentMeta.published_at).toLocaleString("ru-RU") : "Ещё не публиковалось"}</span>
        </div>
      </section>

      {message && <div className="content-message success">{message}</div>}
      {error && <div className="content-message error">{error}</div>}

      <div className="content-grid">
        {FIELDS.map((group) => (
          <section className="content-card" key={group.section}>
            <div className="content-card-head"><h2>{group.label}</h2><span>{group.section}</span></div>
            {group.fields.map(([key, label]) => {
              const multiline = ["copy", "intro", "description", "address"].includes(key);
              return <label className="content-field" key={key}><span>{label}</span>{multiline ? <textarea rows={3} value={current[group.section]?.[key] || ""} onChange={(event) => change(group.section, key, event)} /> : <input value={current[group.section]?.[key] || ""} onChange={(event) => change(group.section, key, event)} />}</label>;
            })}
          </section>
        ))}
      </div>

      <footer className="content-savebar">
        <div><strong>Публикация безопасна для броней</strong><span>CMS меняет только тексты/SEO. Номерной фонд, цены, inventory и заявки остаются в Core.</span></div>
        <div><button className="btn" disabled={saving} onClick={() => void saveDraft()}>Сохранить черновик</button><button className="btn primary" disabled={saving} onClick={() => void publish()}>{saving ? "Сохраняю…" : "Опубликовать на сайте"}</button></div>
      </footer>
    </main>
  );
}
