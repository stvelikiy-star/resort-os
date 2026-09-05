"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

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

type AccessProfile = {
  service_point_id: string;
  code: string;
  name: string;
  mode: "FREE_REQUEST" | "PAID_LOCK";
  is_active: boolean;
  amount_kgs: number | null;
  currency: "KGS";
  provider_code: string | null;
  lock_provider_code: string | null;
  lock_external_id: string | null;
  runtime: { ready: boolean; code: string };
};

type PaymentIntent = {
  id: string;
  reference: string;
  provider_code: string;
  amount_kgs: number;
  status: string;
  paid_at?: string | null;
  unlocked_at?: string | null;
  failure_code?: string | null;
  service_point_code: string;
  service_point_name: string;
};

type PointConfig = {
  mode: "FREE_REQUEST" | "PAID_LOCK";
  amount: string;
  provider: string;
  lockId: string;
  active: boolean;
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

const runtimeLabels: Record<string, string> = {
  READY: "Готово: банк → подтверждение → TTLock",
  PAID_ACCESS_NOT_ENABLED: "Платный доступ выключен",
  PAYMENT_BRIDGE_NOT_CONFIGURED: "Нужен платёжный bridge / банковская интеграция",
  TTLOCK_NOT_CONFIGURED: "Нужны TTLock credentials + gateway",
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

function configFromProfile(profile?: AccessProfile): PointConfig {
  return {
    mode: profile?.mode || "FREE_REQUEST",
    amount: profile?.amount_kgs ? String(profile.amount_kgs) : "",
    provider: profile?.provider_code || "MBANK",
    lockId: profile?.lock_external_id || "",
    active: profile?.is_active ?? true,
  };
}

export default function ServicePointsBoard() {
  const [items, setItems] = useState<Point[]>([]);
  const [profiles, setProfiles] = useState<Record<string, AccessProfile>>({});
  const [configs, setConfigs] = useState<Record<string, PointConfig>>({});
  const [intents, setIntents] = useState<PaymentIntent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [savingPoint, setSavingPoint] = useState<string | null>(null);
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
      const [pointsBody, profilesBody, intentsBody] = await Promise.all([
        jsonFetch<{ items: Point[] }>("/core/api/v1/admin/service-points"),
        jsonFetch<{ items: AccessProfile[] }>("/core/api/v1/admin/service-point-payments/profiles"),
        jsonFetch<{ items: PaymentIntent[] }>("/core/api/v1/admin/service-point-payments/intents?limit=40"),
      ]);
      const nextProfiles = Object.fromEntries(profilesBody.items.map((item) => [item.service_point_id, item]));
      setItems(pointsBody.items);
      setProfiles(nextProfiles);
      setConfigs((current) => {
        const next = { ...current };
        for (const point of pointsBody.items) {
          if (!next[point.id]) next[point.id] = configFromProfile(nextProfiles[point.id]);
        }
        return next;
      });
      setIntents(intentsBody.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось загрузить точки");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const paidCount = useMemo(() => Object.values(profiles).filter((item) => item.mode === "PAID_LOCK" && item.is_active).length, [profiles]);
  const readyCount = useMemo(() => Object.values(profiles).filter((item) => item.runtime.ready).length, [profiles]);

  async function create(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setNotice(null);
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
      setNotice("Точка создана. Теперь можно выпустить QR и при необходимости включить платный доступ.");
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
    setNotice(null);
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

  function patchConfig(pointId: string, patch: Partial<PointConfig>) {
    setConfigs((current) => ({ ...current, [pointId]: { ...(current[pointId] || configFromProfile(profiles[pointId])), ...patch } }));
  }

  async function saveAccess(point: Point) {
    const config = configs[point.id] || configFromProfile(profiles[point.id]);
    setSavingPoint(point.id);
    setError(null);
    setNotice(null);
    try {
      const paid = config.mode === "PAID_LOCK";
      const amount = paid ? Number(config.amount) : null;
      if (paid && (!Number.isInteger(amount) || !amount || amount <= 0)) throw new Error("Укажите цену в сомах целым положительным числом");
      if (paid && !config.lockId.trim()) throw new Error("Укажите TTLock lockId для этой точки");
      await jsonFetch(`/core/api/v1/admin/service-point-payments/service-points/${point.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mode: config.mode,
          amount_kgs: amount,
          provider_code: paid ? config.provider.trim().toUpperCase() : null,
          lock_provider_code: paid ? "TTLOCK" : null,
          lock_external_id: paid ? config.lockId.trim() : null,
          is_active: config.active,
        }),
      });
      setNotice(`Доступ «${point.name}» сохранён.`);
      setConfigs((current) => {
        const next = { ...current };
        delete next[point.id];
        return next;
      });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось сохранить платный доступ");
    } finally {
      setSavingPoint(null);
    }
  }

  async function retryUnlock(intent: PaymentIntent) {
    if (!window.confirm(`Оплата ${intent.reference} уже должна быть подтверждена. Повторить только команду открытия замка?`)) return;
    setError(null);
    setNotice(null);
    try {
      const result = await jsonFetch<{ status: string; failure_code?: string }>(`/core/api/v1/admin/service-point-payments/intents/${intent.id}/retry-unlock`, { method: "POST" });
      setNotice(result.status === "UNLOCKED" ? "Замок подтвердил открытие." : `Замок не открылся: ${result.failure_code || result.status}`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось повторить открытие");
    }
  }

  return <main className="board service-points-board">
    <section className="board-head">
      <div><p className="eyebrow">PROPERTY OPERATIONS · QR ACCESS</p><h1>QR-точки · оплата · замки</h1><p>Один QR-контур для общественных зон. Бесплатные точки создают заявки; платные точки получают подтверждение банка и только затем отправляют команду TTLock.</p></div>
      <button className="btn" onClick={() => void load()}>Обновить</button>
    </section>

    <section className="service-point-kpis">
      <div><span>Всего точек</span><strong>{items.length}</strong></div>
      <div><span>Платный доступ</span><strong>{paidCount}</strong></div>
      <div><span>Полностью готово</span><strong>{readyCount}</strong></div>
      <div><span>Последние оплаты</span><strong>{intents.length}</strong></div>
    </section>

    {error && <div className="error-box">{error}</div>}
    {notice && <div className="service-point-notice">{notice}</div>}

    <form className="service-point-create" onSubmit={create}>
      <h2>Новая точка</h2>
      <input placeholder="Код: WC_OUTSIDE" value={code} onChange={(e) => setCode(e.target.value)} minLength={2} required />
      <input placeholder="Название: Наружный туалет" value={name} onChange={(e) => setName(e.target.value)} minLength={2} required />
      <select value={category} onChange={(e) => setCategory(e.target.value)}>{Object.entries(categoryLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select>
      <input placeholder="Зона / ориентир" value={zone} onChange={(e) => setZone(e.target.value)} />
      <button className="btn primary" disabled={submitting}>{submitting ? "Создаём…" : "Создать точку"}</button>
      <small>Физически печатается QR нашей точки. Для платной точки банковский QR создаётся после сканирования — это позволяет связать конкретную оплату с конкретным замком.</small>
    </form>

    {loading ? <p>Загрузка…</p> : <section className="service-point-grid">
      {items.map((point) => {
        const profile = profiles[point.id];
        const config = configs[point.id] || configFromProfile(profile);
        const isPaid = config.mode === "PAID_LOCK";
        return <article key={point.id} className="service-point-card">
          <div><span className="eyebrow">{categoryLabels[point.category] || point.category}</span><h2>{point.name}</h2><p>{point.code}{point.zone_label ? ` · ${point.zone_label}` : ""}</p></div>
          <div className="service-point-options">{point.request_options.filter((option) => option.is_active).map((option) => <span key={option.code}>{option.label} → {option.task_type}</span>)}</div>

          <div className="service-point-qr-state"><strong>{point.active_qr_id ? "QR точки активен" : "QR точки не выпущен"}</strong>{point.qr_issued_at && <small>{new Date(point.qr_issued_at).toLocaleString("ru-RU")}</small>}</div>
          <div className="service-point-actions">
            {!point.active_qr_id && <button className="btn primary" onClick={() => void qrAction(point, "issue")}>Выпустить QR</button>}
            {point.active_qr_id && <button className="btn" onClick={() => void qrAction(point, "rotate")}>Сменить QR</button>}
            {point.active_qr_id && <button className="btn" onClick={() => void qrAction(point, "revoke")}>Отключить QR</button>}
          </div>

          <section className="service-point-access-config">
            <div className="service-point-access-title"><strong>Доступ</strong>{profile && <span className={profile.runtime.ready ? "ready" : "pending"}>{runtimeLabels[profile.runtime.code] || profile.runtime.code}</span>}</div>
            <label>Режим<select value={config.mode} onChange={(e) => patchConfig(point.id, { mode: e.target.value as PointConfig["mode"] })}><option value="FREE_REQUEST">Бесплатная точка / заявки</option><option value="PAID_LOCK">Оплата → открыть замок</option></select></label>
            {isPaid && <div className="service-point-paid-fields">
              <label>Цена, сом<input inputMode="numeric" value={config.amount} onChange={(e) => patchConfig(point.id, { amount: e.target.value.replace(/\D/g, "") })} placeholder="50" /></label>
              <label>Банк / bridge<input value={config.provider} onChange={(e) => patchConfig(point.id, { provider: e.target.value })} placeholder="MBANK" /></label>
              <label>TTLock lockId<input inputMode="numeric" value={config.lockId} onChange={(e) => patchConfig(point.id, { lockId: e.target.value.replace(/\D/g, "") })} placeholder="1234567" /></label>
            </div>}
            <label className="service-point-check"><input type="checkbox" checked={config.active} onChange={(e) => patchConfig(point.id, { active: e.target.checked })} /> Контур активен</label>
            <button className="btn primary" disabled={savingPoint === point.id} onClick={() => void saveAccess(point)}>{savingPoint === point.id ? "Сохраняем…" : "Сохранить доступ"}</button>
            {isPaid && <small>Автооткрытие не включится, пока одновременно не готовы платёжный bridge, банковское подтверждение и TTLock credentials/gateway.</small>}
          </section>
        </article>;
      })}
      {!items.length && <p>Service Point QR пока не создано.</p>}
    </section>}

    <section className="service-point-payment-log">
      <div className="service-point-log-head"><div><p className="eyebrow">PAID ACCESS LEDGER</p><h2>Последние операции точек</h2></div><small>Не смешиваются с оплатой проживания</small></div>
      {!intents.length ? <p>Платёжных операций пока нет.</p> : <div className="service-point-payment-table">
        {intents.map((intent) => <div className="service-point-payment-row" key={intent.id}>
          <div><strong>{intent.service_point_name}</strong><small>{intent.reference}</small></div>
          <span>{intent.amount_kgs} сом · {intent.provider_code}</span>
          <strong>{intent.status}</strong>
          <small>{intent.failure_code || (intent.unlocked_at ? "Открыто" : intent.paid_at ? "Оплачено" : "Ожидание")}</small>
          {intent.status === "UNLOCK_FAILED" ? <button className="btn" onClick={() => void retryUnlock(intent)}>Повторить открытие</button> : <span />}
        </div>)}
      </div>}
    </section>

    {qr && <div className="service-point-modal" role="dialog" aria-modal="true">
      <div className="service-point-modal-card">
        <p className="eyebrow">ПОКАЗЫВАЕТСЯ ОДИН РАЗ</p>
        <h2>QR точки готов · {qr.service_point_code}</h2>
        <div className="service-point-svg" dangerouslySetInnerHTML={{ __html: qr.qr_svg }} />
        <label>Ссылка<input readOnly value={qr.public_url} onFocus={(e) => e.currentTarget.select()} /></label>
        <p>Это QR нашей сервисной точки, а не статический банковский QR. При платном доступе банк создаёт платёж уже после сканирования.</p>
        <button className="btn primary" onClick={() => setQr(null)}>Закрыть</button>
      </div>
    </div>}
  </main>;
}
