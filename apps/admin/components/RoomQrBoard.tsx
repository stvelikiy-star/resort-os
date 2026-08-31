"use client";

import { useEffect, useMemo, useState } from "react";

type RoomQrItem = {
  room_id: string;
  room_code: string;
  beds_raw: string | null;
  qr_id: string | null;
  status: "ACTIVE" | null;
  label: string | null;
  issued_at: string | null;
  raw_token_recoverable: false;
  reprint_requires_rotation: boolean;
};

type IssuedQr = {
  qr_id: string;
  room_id: string;
  room_code: string;
  token: string;
  public_url: string;
  qr_svg: string;
  token_display_once: true;
  reprint_requires_rotation: true;
};

type Registry = { property: string; items: RoomQrItem[] };

export default function RoomQrBoard() {
  const [registry, setRegistry] = useState<Registry | null>(null);
  const [issued, setIssued] = useState<IssuedQr[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/core/api/v1/admin/guest-os/room-qrs", { cache: "no-store" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body?.detail || `HTTP ${response.status}`);
      setRegistry(body as Registry);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось загрузить реестр QR");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (registry?.items || []).filter((item) => !q || [item.room_code, item.beds_raw, item.label].some((value) => value?.toLowerCase().includes(q)));
  }, [registry, query]);

  const active = registry?.items.filter((item) => item.qr_id).length || 0;
  const missing = (registry?.items.length || 0) - active;

  async function issueOne(roomId: string) {
    setBusy(roomId);
    setError(null);
    try {
      const response = await fetch(`/core/api/v1/admin/guest-os/room-qrs/${roomId}/issue`, { method: "POST" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body?.detail?.code || body?.detail || `HTTP ${response.status}`);
      setIssued((current) => [body as IssuedQr, ...current]);
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось выпустить QR");
    } finally {
      setBusy(null);
    }
  }

  async function rotateOne(item: RoomQrItem) {
    if (!window.confirm(`Заменить QR номера ${item.room_code}? Старый QR перестанет работать сразу.`)) return;
    setBusy(item.room_id);
    setError(null);
    try {
      const response = await fetch(`/core/api/v1/admin/guest-os/room-qrs/${item.room_id}/rotate`, { method: "POST" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body?.detail?.code || body?.detail || `HTTP ${response.status}`);
      setIssued((current) => [body as IssuedQr, ...current]);
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось заменить QR");
    } finally {
      setBusy(null);
    }
  }

  async function issueMissing() {
    if (!missing) return;
    if (!window.confirm(`Выпустить ${missing} недостающих QR? Сразу после выпуска откроется печатный пакет. Исходные токены потом восстановить нельзя.`)) return;
    setBusy("BATCH");
    setError(null);
    try {
      const response = await fetch("/core/api/v1/admin/guest-os/room-qrs/issue-missing", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ include_existing: false }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body?.detail || `HTTP ${response.status}`);
      const batch = Array.isArray(body.issued) ? body.issued as IssuedQr[] : [];
      setIssued(batch);
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось выпустить пакет QR");
    } finally {
      setBusy(null);
    }
  }

  return (
    <main className="room-qr-board">
      <section className="room-qr-hero">
        <div>
          <p className="eyebrow">Guest OS · постоянные QR комнат</p>
          <h1>QR номеров</h1>
          <p>QR привязан к физическому номеру, а не к конкретному гостю. Личные данные появляются только после проверки PIN активного проживания.</p>
        </div>
        <div className="room-qr-stats">
          <div><strong>{registry?.items.length || 0}</strong><span>номеров</span></div>
          <div><strong>{active}</strong><span>QR активны</span></div>
          <div className={missing ? "warn" : "ok"}><strong>{missing}</strong><span>не выпущены</span></div>
        </div>
      </section>

      <section className="room-qr-security">
        <strong>Security by design</strong>
        <p>В базе хранится только SHA-256 хэш. Исходный QR-токен показывается один раз при выпуске. Для повторной печати потерянного QR нужно выполнить ротацию — старый код сразу отзывается.</p>
      </section>

      <section className="room-qr-actions">
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Номер или конфигурация кроватей…" />
        <button className="btn" onClick={() => void load()} disabled={loading}>↻ Обновить</button>
        <button className="btn primary" onClick={() => void issueMissing()} disabled={!missing || busy !== null}>{busy === "BATCH" ? "Выпускаю…" : `Выпустить недостающие (${missing})`}</button>
      </section>

      {error && <div className="room-qr-error">{error}</div>}

      {issued.length > 0 && (
        <section className="room-qr-print-pack">
          <div className="room-qr-print-head">
            <div><p className="eyebrow">Только что выпущены</p><h2>Сохраните или распечатайте сейчас</h2><p>После закрытия страницы исходные токены не восстанавливаются.</p></div>
            <button className="btn primary" onClick={() => window.print()}>Печать QR</button>
          </div>
          <div className="room-qr-print-grid">
            {issued.map((item) => (
              <article key={item.qr_id} className="room-qr-print-card">
                <img src={`data:image/svg+xml;charset=utf-8,${encodeURIComponent(item.qr_svg)}`} alt={`QR номера ${item.room_code}`} />
                <strong>Номер {item.room_code}</strong>
                <span>Три Короны · Guest OS</span>
                <small>{item.public_url}</small>
              </article>
            ))}
          </div>
        </section>
      )}

      <section className="room-qr-table-wrap">
        <div className="room-qr-table-head"><span>Номер</span><span>Спальные места</span><span>Статус QR</span><span>Выпущен</span><span>Действие</span></div>
        {loading && !registry ? <div className="room-qr-loading">Загрузка 84 номеров…</div> : rows.map((item) => (
          <div className="room-qr-row" key={item.room_id}>
            <strong>№ {item.room_code}</strong>
            <span>{item.beds_raw || "—"}</span>
            <span className={item.qr_id ? "qr-active" : "qr-missing"}>{item.qr_id ? "ACTIVE" : "НЕ ВЫПУЩЕН"}</span>
            <span>{item.issued_at ? new Date(item.issued_at).toLocaleString("ru-RU") : "—"}</span>
            <div>
              {item.qr_id ? <button className="btn danger-lite" disabled={busy !== null} onClick={() => void rotateOne(item)}>{busy === item.room_id ? "…" : "Ротация"}</button> : <button className="btn" disabled={busy !== null} onClick={() => void issueOne(item.room_id)}>{busy === item.room_id ? "…" : "Выпустить"}</button>}
            </div>
          </div>
        ))}
      </section>
    </main>
  );
}
