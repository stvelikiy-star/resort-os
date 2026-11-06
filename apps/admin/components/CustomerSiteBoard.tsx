"use client";

import { useEffect, useState } from "react";

type Locale = "ru" | "kg" | "en";
type Content = {
  hero: { title: string; subtitle: string };
  contacts: { phone: string; whatsapp: string; email: string; address: string };
  seo: { title: string; description: string };
};
type CmsItem = {
  locale: Locale;
  draft: Partial<Content>;
  published_version: number;
  version: number;
  published_at: string | null;
};

const LOCALES: { code: Locale; label: string }[] = [
  { code: "ru", label: "Русский" },
  { code: "kg", label: "Кыргызча" },
  { code: "en", label: "English" },
];
const FIELD_SECTIONS = [
  { id: "hero", label: "Первый экран", fields: [["title", "Название гостиницы"], ["subtitle", "Описание гостиницы"]] },
  { id: "contacts", label: "Контакты", fields: [["phone", "Телефон"], ["whatsapp", "WhatsApp"], ["email", "Email"], ["address", "Адрес"]] },
  { id: "seo", label: "SEO", fields: [["title", "Заголовок страницы"], ["description", "Описание для поиска"]] },
] as const;

function emptyContent(): Content {
  return { hero: { title: "", subtitle: "" }, contacts: { phone: "", whatsapp: "", email: "", address: "" }, seo: { title: "", description: "" } };
}

function normalized(value?: Partial<Content>): Content {
  const blank = emptyContent();
  return {
    hero: { ...blank.hero, ...value?.hero },
    contacts: { ...blank.contacts, ...value?.contacts },
    seo: { ...blank.seo, ...value?.seo },
  };
}

export default function CustomerSiteBoard() {
  const [locale, setLocale] = useState<Locale>("ru");
  const [drafts, setDrafts] = useState<Record<Locale, Content> | null>(null);
  const [items, setItems] = useState<CmsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    try {
      const response = await fetch("/core/api/v1/admin/site/content", { cache: "no-store" });
      if (!response.ok) throw new Error(`CMS ${response.status}`);
      const data = (await response.json()) as { mode: string; items: CmsItem[] };
      if (data.mode !== "customer") throw new Error("CUSTOMER_MODE_REQUIRED");
      const drafts = { ru: emptyContent(), kg: emptyContent(), en: emptyContent() };
      for (const item of data.items) {
        if (item.locale in drafts) drafts[item.locale] = normalized(item.draft);
      }
      setDrafts(drafts);
      setItems(data.items);
      setError("");
    } catch {
      setError("Не удалось загрузить данные сайта этой гостиницы.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);

  function edit(section: keyof Content, key: string, value: string) {
    setDrafts((prev) => {
      if (!prev) return prev;
      const current = prev[locale];
      return { ...prev, [locale]: { ...current, [section]: { ...current[section], [key]: value } } };
    });
    setNotice("");
  }

  async function update(publish: boolean) {
    if (!drafts || saving) return;
    if (publish && !window.confirm("Опубликовать текст и контакты этой гостиницы на её публичном сайте?")) return;
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const current = drafts[locale];
      const saved = await fetch(`/core/api/v1/admin/site/content/${locale}/draft`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: current }),
      });
      if (!saved.ok) {
        const result = await saved.json().catch(() => ({})) as { detail?: unknown };
        throw new Error(`Черновик отклонён (${saved.status}): ${typeof result.detail === "string" ? result.detail : "проверьте все поля"}`);
      }
      if (publish) {
        const published = await fetch(`/core/api/v1/admin/site/content/${locale}/publish`, { method: "POST" });
        if (!published.ok) throw new Error(`Публикация отклонена (${published.status})`);
      }
      await load();
      setNotice(publish ? "Версия опубликована для выбранного языка." : "Черновик сохранён. Публичный сайт не изменился.");
    } catch (exception) {
      setError(exception instanceof Error ? exception.message : "Не удалось сохранить изменения.");
    } finally {
      setSaving(false);
    }
  }

  const selected = drafts?.[locale];
  const meta = items.find((item) => item.locale === locale);

  return (
    <main className="content-board">
      <header className="content-head">
        <div>
          <p className="eyebrow">MARINA SMART / Сайт гостиницы</p>
          <h1>Собственный сайт вашей гостиницы</h1>
          <p>Никаких общих шаблонных контактов и чужих фотографий. Заполните данные на каждом языке. До публикации сайт показывает нейтральную страницу.</p>
        </div>
      </header>
      {loading && <div className="content-state">Загружаю контент…</div>}
      {error && <div role="alert" className="content-message error">{error}</div>}
      {notice && <div role="status" className="content-message success">{notice}</div>}
      {!loading && selected && (
        <>
          <section className="content-status-row">
            <div className="locale-tabs">
              {LOCALES.map((language) => (
                <button key={language.code} type="button" className={locale === language.code ? "active" : ""} onClick={() => setLocale(language.code)}>
                  {language.label}
                </button>
              ))}
            </div>
            <div className="publish-status">
              <span>Черновик v{meta?.version ?? 0}</span>
              <span>Публикация v{meta?.published_version ?? 0}</span>
              <span>{meta?.published_at ? new Date(meta.published_at).toLocaleString("ru-RU") : "Не опубликовано"}</span>
            </div>
          </section>
          <div className="content-grid">
            {FIELD_SECTIONS.map((section) => (
              <section className="content-card" key={section.id}>
                <div className="content-card-head"><h2>{section.label}</h2></div>
                {section.fields.map(([key, label]) => {
                  const value = (selected[section.id] as Record<string, string>)[key] ?? "";
                  const multiline = key === "subtitle" || key === "description" || key === "address";
                  return (
                    <label className="content-field" key={key}>
                      <span>{label}</span>
                      {multiline ? (
                        <textarea rows={3} value={value ?? ""} onChange={(event) => edit(section.id, key, event.target.value)} />
                      ) : (
                        <input value={value ?? ""} onChange={(event) => edit(section.id, key, event.target.value)} />
                      )}
                    </label>
                  );
                })}
              </section>
            ))}
          </div>
          <div className="content-head-actions">
            <button type="button" className="btn" disabled={saving} onClick={() => void update(false)}>Сохранить черновик</button>
            <button type="button" className="btn btn-primary" disabled={saving} onClick={() => void update(true)}>Опубликовать {locale.toUpperCase()}</button>
          </div>
        </>
      )}
    </main>
  );
}
