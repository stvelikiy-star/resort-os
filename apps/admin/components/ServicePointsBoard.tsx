"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

type Point = {
  id: string;
  code: string;
  name: string;
  category: string;
  zone_label?: string | null;
  is_active: boolean;
  active_qr_id?: string | null;
  qr_issued_at?: string | null;
  request_options: Array<{ code: string; label: string; task_type: string; priority: string; is_active: boolean }>;
};

type QrResult = {
  qr_id: string;
  service_point_id: string;
  service_point_code: string;
  token: string;
  public_url: string;
  qr_svg: string;
  display_once: boolean;
};

const categoryLabels: Record<string, string> = {
  POOL: "Бассейн",
  BEACH: "Пляж",
  RESTROOM: "Санузел",
  CORRIDOR: "Коридор / общая зона",
  DINING: "Питание / ресторан",
  SAUNA: "Сауна",
  OTHER: "Другая зона",
};

async function jsonFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { cache: "no-store", ...init });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = body?.detail;
    const code = typeof detail === "object" && detail ? detail.code : null;
    throw new Error(code || (typeof detail === "string" ? detail : "Ошибка Service Point QR"));
  }
  return body as T;
}

export default function ServicePointsBoard() {
  const [items, setItems] = useState<Point[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [qr, setQr] = useState<QrResult | null>(null);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [category, setCategory] = useState("OTHER");
  const [zone, setZone] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const body = await jsonFetch<{ items: Point[] }>("/core/api/v1/admin/service-points");
      setItems(body.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось загрузить точки");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function create(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await jsonFetch("/core/api/v1/admin/service-points", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          code,
          name,
          category,
          zone_label: zone.trim() || null,
          request_options: [
            { code: "CLEANLINESS", label: "Нужна уборка", task_type: "HOUSEKEEPING", priority: "NORMAL" },
            { code: "TECHNICAL", label: "Техническая проблема", task_type: "MAINTENANCE", priority: "NORMAL" },
            { code: "OTHER", label: "Другое обращение", task_type: "GUEST_REQUEST", priority: "NORMAL" },
          ],
        }),
      });
      setCode(""); setName(""); setZone(""); setCategory("OTHER");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось создать точку");
    } finally {
      setSubmitting(false);
    }
  }

  async function qrAction(point: Point, action: "issue" | "rotate" | "revoke") {
    if (action === "rotate" && !window.confirm(`Старый QR «${point.name}» сразу перестанет работать. Выпустить новый?`)) return;
    if (action === "revoke" && !window.confirm(`Отключить QR «${point.name}»?`)) return;
    setError(null);
    try {
      if (action === "revoke") {
        await jsonFetch(`/core/api/v1/admin/service-points/${point.id}/qr/revoke`, { method: "POST" });
      } else {
        const result = await jsonFetch<QrResult>(`/core/api/v1/admin/service-points/${point.id}/qr/${action}`, { method: "POST" });
        setQr(result);
      }
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось изменить QR");
    }
  }

  return <main className="board service-points-board">
    <section className="board-head">
      <div><p className="eyebrow">PROPERTY OPERATIONS · BLOCK 11</p><h1>QR общественных зон</h1><p>Отдельный от QR номеров и NFC контур: сканирование создаёт анонимную операционную заявку.</p></div>
      <button className="btn" onClick={() => void load()}>Обновить</button>
    </section>

    {error && <div className="error-box">{error}</div>}

    <form className="service-point-create" onSubmit={create}>
      <h2>Новая точка</h2>
      <input placeholder="Код: POOL_MAIN" value={code} onChange={(e) => setCode(e.target.value)} minLength={2} required />
      <input placeholder="Название: Бассейн" value={name} onChange={(e) => setName(e.target.value)} minLength={2} required />
      <select value={category} onChange={(e) => setCategory(e.target.value)}>{Object.entries(categoryLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select>
      <input placeholder="Зона / ориентир (необязательно)" value={zone} onChange={(e) => setZone(e.target.value)} />
      <button className="btn primary" disabled={submitting}>{submitting ? "Создаём…" : "Создать точку"}</button>
      <small>По умолчанию создаются три нейтральных маршрута: уборка → HOUSEKEEPING, техническая проблема → MAINTENANCE, другое → GUEST_REQUEST. Приоритет NORMAL; QR сам срочность не придумывает.</small>
    </form>

    {loading ? <p>Загрузка…</p> : <section className="service-point-grid">
      {items.map((point) => <article key={point.id} className="service-point-card">
        <div><span className="eyebrow">{categoryLabels[point.category] || point.category}</span><h2>{point.name}</h2><p>{point.code}{point.zone_label ? ` · ${point.zone_label}` : ""}</p></div>
        <div className="service-point-options">{point.request_options.filter((option) => option.is_active).map((option) => <span key={option.code}>{option.label} → {option.task_type}</span>)}</div>
        <div className="service-point-qr-state"><strong>{point.active_qr_id ? "QR активен" : "QR не выпущен"}</strong>{point.qr_issued_at && <small>{new Date(point.qr_issued_at).toLocaleString("ru-RU")}</small>}</div>
        <div className="service-point-actions">
          {!point.active_qr_id && <button className="btn primary" onClick={() => void qrAction(point, "issue")}>Выпустить QR</button>}
          {point.active_qr_id && <button className="btn" onClick={() => void qrAction(point, "rotate")}>Сменить QR</button>}
          {point.active_qr_id && <button className="btn" onClick={() => void qrAction(point, "revoke")}>Отключить</button>}
        </div>
      </article>)}
      {!items.length && <p>Service Point QR пока не создано.</p>}
    </section>}

    {qr && <div className="service-point-modal" role="dialog" aria-modal="true">
      <div className="service-point-modal-card">
        <p className="eyebrow">ПОКАЗЫВАЕТСЯ ОДИН РАЗ</p>
        <h2>QR готов · {qr.service_point_code}</h2>
        <div className="service-point-svg" dangerouslySetInnerHTML={{ __html: qr.qr_svg }} />
        <label>Ссылка<input readOnly value={qr.public_url} onFocus={(e) => e.currentTarget.select()} /></label>
        <p>В базе хранится только SHA-256 hash токена. После закрытия окна исходный токен из админки повторно не читается.</p>
        <button className="btn primary" onClick={() => setQr(null)}>Закрыть</button>
      </div>
    </div>}
  </main>;
}
