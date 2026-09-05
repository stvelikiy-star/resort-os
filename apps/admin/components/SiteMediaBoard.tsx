"use client";

import { ChangeEvent, useCallback, useEffect, useMemo, useState } from "react";

import styles from "./SiteMediaBoard.module.css";

type MediaAsset = {
  id: string;
  filename: string;
  mime_type: string;
  byte_size: number;
  sha256: string;
  alt_text?: string | null;
  is_active: boolean;
  url: string;
  created_at: string;
  updated_at: string;
};

type MediaRef = {
  asset_id: string;
  filename: string;
  mime_type: string;
  byte_size: number;
  alt_text?: string | null;
  url: string;
};

type MediaSlot = {
  slot: string;
  label: string;
  version: number;
  published_version: number;
  published_at?: string | null;
  dirty: boolean;
  draft?: MediaRef | null;
  published?: MediaRef | null;
  updated_at?: string | null;
};

type DraftValue = { assetId: string; altText: string };

const GROUPS = [
  { key: "PRIMARY", label: "Главные блоки", match: (slot: string) => ["HERO", "CONFERENCE"].includes(slot) },
  { key: "GALLERY", label: "Галерея", match: (slot: string) => slot.startsWith("GALLERY_") },
  { key: "ADVANTAGE", label: "Преимущества", match: (slot: string) => slot.startsWith("ADVANTAGE_") },
  { key: "ROOM", label: "Номерной фонд", match: (slot: string) => slot.startsWith("ROOM_") },
] as const;

function bytes(value: number) {
  if (value < 1024 * 1024) return `${Math.max(1, Math.round(value / 1024))} КБ`;
  return `${(value / 1024 / 1024).toFixed(1)} МБ`;
}

async function api(path: string, init?: RequestInit) {
  const response = await fetch(path, { cache: "no-store", ...init });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const message = typeof body?.detail === "string"
      ? body.detail
      : body?.detail?.message || body?.detail?.code || `CMS Media ${response.status}`;
    throw new Error(message);
  }
  return body;
}

function buildDrafts(slots: MediaSlot[]): Record<string, DraftValue> {
  const next: Record<string, DraftValue> = {};
  for (const slot of slots) {
    next[slot.slot] = {
      assetId: slot.draft?.asset_id || "",
      altText: slot.draft?.alt_text || "",
    };
  }
  return next;
}

export default function SiteMediaBoard() {
  const [assets, setAssets] = useState<MediaAsset[]>([]);
  const [slots, setSlots] = useState<MediaSlot[]>([]);
  const [drafts, setDrafts] = useState<Record<string, DraftValue>>({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploadAlt, setUploadAlt] = useState("");
  const [showLibrary, setShowLibrary] = useState(true);
  const [group, setGroup] = useState("PRIMARY");

  const load = useCallback(async () => {
    setError(null);
    try {
      const [mediaBody, slotsBody] = await Promise.all([
        api("/core/api/v1/admin/site/media"),
        api("/core/api/v1/admin/site/media/slots"),
      ]);
      const nextSlots = (slotsBody.items ?? []) as MediaSlot[];
      setAssets((mediaBody.items ?? []) as MediaAsset[]);
      setSlots(nextSlots);
      setDrafts(buildDrafts(nextSlots));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось загрузить медиатеку");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const currentGroup = GROUPS.find((item) => item.key === group) ?? GROUPS[0];
  const visibleSlots = useMemo(() => slots.filter((slot) => currentGroup.match(slot.slot)), [slots, currentGroup]);
  const dirtyCount = slots.filter((slot) => slot.dirty).length;

  async function upload(file: File | null) {
    if (!file) return;
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      setError("Разрешены JPEG, PNG и WebP.");
      return;
    }
    setBusy("upload"); setError(null); setMessage(null);
    try {
      const body = await api("/core/api/v1/admin/site/media", {
        method: "POST",
        headers: {
          "content-type": file.type,
          "x-filename": encodeURIComponent(file.name),
          "x-alt-text": encodeURIComponent(uploadAlt.trim()),
        },
        body: file,
      });
      setMessage(body.deduplicated ? "Такой файл уже был в медиатеке — использую существующий оригинал." : "Фото загружено в медиатеку. На сайте оно ещё не опубликовано.");
      setUploadAlt("");
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось загрузить фото");
    } finally { setBusy(null); }
  }

  function updateDraft(slot: string, patch: Partial<DraftValue>) {
    setDrafts((current) => ({
      ...current,
      [slot]: { assetId: current[slot]?.assetId || "", altText: current[slot]?.altText || "", ...patch },
    }));
  }

  async function saveDraft(slot: MediaSlot) {
    const value = drafts[slot.slot] || { assetId: "", altText: "" };
    setBusy(`save:${slot.slot}`); setError(null); setMessage(null);
    try {
      await api(`/core/api/v1/admin/site/media/slots/${slot.slot}/draft`, {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ asset_id: value.assetId || null, alt_text: value.altText.trim() || null }),
      });
      setMessage(`${slot.label}: черновик сохранён. Публичный сайт не изменён.`);
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось сохранить черновик фото");
    } finally { setBusy(null); }
  }

  async function publish(slot: MediaSlot) {
    const value = drafts[slot.slot] || { assetId: "", altText: "" };
    setBusy(`publish:${slot.slot}`); setError(null); setMessage(null);
    try {
      await api(`/core/api/v1/admin/site/media/slots/${slot.slot}/draft`, {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ asset_id: value.assetId || null, alt_text: value.altText.trim() || null }),
      });
      await api(`/core/api/v1/admin/site/media/slots/${slot.slot}/publish`, { method: "POST" });
      setMessage(`${slot.label}: изображение опубликовано.`);
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось опубликовать фото");
    } finally { setBusy(null); }
  }

  async function archive(asset: MediaAsset) {
    if (!window.confirm(`Архивировать «${asset.filename}»? Фото нельзя архивировать, пока оно используется в черновике или публикации.`)) return;
    setBusy(`archive:${asset.id}`); setError(null); setMessage(null);
    try {
      await api(`/core/api/v1/admin/site/media/${asset.id}/archive`, { method: "POST" });
      setMessage("Фото перенесено в архив.");
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось архивировать фото");
    } finally { setBusy(null); }
  }

  if (loading) return <section className={styles.shell}><div className={styles.state}>Загружаю медиатеку…</div></section>;

  return <section className={styles.shell}>
    <header className={styles.head}>
      <div>
        <p>CMS · Media Library</p>
        <h2>Фото публичного сайта</h2>
        <span>Загрузка не меняет сайт. Сначала сохраняется черновик конкретного места, затем он публикуется отдельно.</span>
      </div>
      <div className={styles.headStats}>
        <article><strong>{assets.length}</strong><span>фото</span></article>
        <article data-alert={dirtyCount > 0}><strong>{dirtyCount}</strong><span>не опубликовано</span></article>
      </div>
    </header>

    {error && <div className={styles.error}>{error}</div>}
    {message && <div className={styles.notice}>{message}</div>}

    <section className={styles.upload}>
      <div><strong>Добавить фото</strong><span>JPEG / PNG / WebP · до 8 МБ · оригинал хранится в Resort Core</span></div>
      <input value={uploadAlt} onChange={(event) => setUploadAlt(event.target.value)} placeholder="Описание фото для accessibility / SEO" />
      <label className={styles.uploadButton} aria-disabled={busy === "upload"}>{busy === "upload" ? "Загружаю…" : "Выбрать файл"}<input disabled={busy === "upload"} type="file" accept="image/jpeg,image/png,image/webp" onChange={(event: ChangeEvent<HTMLInputElement>) => { const file = event.target.files?.[0] || null; void upload(file); event.target.value = ""; }} /></label>
      <button type="button" onClick={() => setShowLibrary((value) => !value)}>{showLibrary ? "Скрыть медиатеку" : "Показать медиатеку"}</button>
    </section>

    {showLibrary && <div className={styles.library}>
      {assets.length === 0 && <div className={styles.state}>Медиатека пуста. Загрузите первое фото.</div>}
      {assets.map((asset) => <article key={asset.id}>
        <div className={styles.thumb}><img src={asset.url} alt={asset.alt_text || asset.filename} loading="lazy" /></div>
        <div className={styles.assetBody}><strong title={asset.filename}>{asset.filename}</strong><span>{bytes(asset.byte_size)} · {asset.mime_type.replace("image/", "").toUpperCase()}</span><small>{asset.alt_text || "Alt-текст не задан"}</small></div>
        <button type="button" disabled={busy === `archive:${asset.id}`} onClick={() => void archive(asset)}>Архив</button>
      </article>)}
    </div>}

    <div className={styles.groupTabs}>{GROUPS.map((item) => <button type="button" key={item.key} className={group === item.key ? styles.active : ""} onClick={() => setGroup(item.key)}>{item.label}<span>{slots.filter((slot) => item.match(slot.slot)).filter((slot) => slot.dirty).length || ""}</span></button>)}</div>

    <div className={styles.slots}>
      {visibleSlots.map((slot) => {
        const value = drafts[slot.slot] || { assetId: "", altText: "" };
        const draftAsset = assets.find((asset) => asset.id === value.assetId);
        return <article className={styles.slot} key={slot.slot} data-dirty={slot.dirty}>
          <div className={styles.slotHead}><div><small>{slot.slot}</small><h3>{slot.label}</h3></div><div>{slot.dirty ? <b>Есть черновик</b> : <span>Синхронизировано</span>}<small>v{slot.version} / live v{slot.published_version}</small></div></div>

          <div className={styles.previewGrid}>
            <div><span>Сейчас на сайте</span>{slot.published ? <img src={slot.published.url} alt={slot.published.alt_text || slot.label} /> : <div className={styles.noImage}>Системное фото / пусто</div>}<small>{slot.published?.filename || "Нет управляемой публикации"}</small></div>
            <div><span>Черновик</span>{draftAsset ? <img src={draftAsset.url} alt={value.altText || draftAsset.alt_text || slot.label} /> : <div className={styles.noImage}>Будет использоваться системное фото / пусто</div>}<small>{draftAsset?.filename || "Без назначенного фото"}</small></div>
          </div>

          <label className={styles.field}><span>Изображение</span><select value={value.assetId} onChange={(event) => updateDraft(slot.slot, { assetId: event.target.value })}><option value="">Системное фото / очистить слот</option>{assets.map((asset) => <option key={asset.id} value={asset.id}>{asset.filename} · {bytes(asset.byte_size)}</option>)}</select></label>
          <label className={styles.field}><span>Alt-текст этого места</span><input value={value.altText} onChange={(event) => updateDraft(slot.slot, { altText: event.target.value })} placeholder={draftAsset?.alt_text || "Описание изображения"} /></label>

          <div className={styles.actions}>
            <button type="button" disabled={busy !== null} onClick={() => void saveDraft(slot)}>{busy === `save:${slot.slot}` ? "Сохраняю…" : "Сохранить черновик"}</button>
            <button className={styles.primary} type="button" disabled={busy !== null} onClick={() => void publish(slot)}>{busy === `publish:${slot.slot}` ? "Публикую…" : "Сохранить и опубликовать"}</button>
          </div>
          {slot.published_at && <footer>Последняя публикация: {new Date(slot.published_at).toLocaleString("ru-RU")}</footer>}
        </article>;
      })}
    </div>
  </section>;
}
