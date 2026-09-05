"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

type PointPayload = {
  qr_valid: boolean;
  point: { code: string; name: string; category: string; zone_label?: string | null };
  request_options: Array<{ code: string; label: string }>;
  privacy: string;
};

type AccessProfile = {
  service_point_code: string;
  mode: "FREE_REQUEST" | "PAID_LOCK";
  is_active: boolean;
  amount_kgs: number | null;
  currency: "KGS";
  provider_code: string | null;
  lock_provider_code: string | null;
  runtime: { ready: boolean; code: string };
};

type PaymentIntent = {
  id: string;
  reference: string;
  provider_code: string;
  provider_payment_id?: string | null;
  amount_kgs: number;
  currency: "KGS";
  status: "CREATED" | "AWAITING_PAYMENT" | "PAID" | "UNLOCK_PENDING" | "UNLOCKED" | "UNLOCK_FAILED" | "PAYMENT_FAILED" | "EXPIRED" | "CANCELLED";
  checkout_url?: string | null;
  payment_qr_svg?: string | null;
  paid_at?: string | null;
  expires_at: string;
  unlocked_at?: string | null;
  failure_code?: string | null;
};

type Created = {
  task_id: string;
  status: string;
  title: string;
  idempotent_replay: boolean;
};

const errorLabels: Record<string, string> = {
  SERVICE_POINT_QR_NOT_FOUND: "Этот QR-код больше не действует. Обратитесь к администратору.",
  SERVICE_POINT_REQUEST_NOT_ALLOWED: "Выбранный тип обращения больше недоступен. Обновите страницу.",
  SERVICE_POINT_IDEMPOTENCY_PAYLOAD_MISMATCH: "Содержание обращения изменилось. Повторите отправку ещё раз.",
  SERVICE_POINT_RATE_LIMITED: "С этой точки уже поступило много обращений. Попробуйте немного позже.",
  PAID_ACCESS_NOT_ENABLED: "Платный доступ для этой точки не включён.",
  PAYMENT_BRIDGE_NOT_CONFIGURED: "Приём оплаты ещё не подключён. Обратитесь к администратору.",
  TTLOCK_NOT_CONFIGURED: "Замок ещё не подключён к системе. Оплата временно недоступна.",
  PAYMENT_PROVIDER_NOT_CONFIGURED: "Банковский провайдер ещё не подключён.",
};

async function jsonFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { cache: "no-store", ...init });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = body?.detail;
    const code = typeof detail === "object" && detail ? detail.code : null;
    throw new Error(
      (code && errorLabels[code]) ||
      (typeof detail === "string" ? detail : code || "Не удалось выполнить запрос"),
    );
  }
  return body as T;
}

export default function ServicePointRuntime({ token }: { token: string }) {
  const [point, setPoint] = useState<PointPayload | null>(null);
  const [access, setAccess] = useState<AccessProfile | null>(null);
  const [intent, setIntent] = useState<PaymentIntent | null>(null);
  const [requestCode, setRequestCode] = useState("");
  const [description, setDescription] = useState("");
  const [created, setCreated] = useState<Created | null>(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [paying, setPaying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestIdRef = useRef<string | null>(null);
  const paymentRequestIdRef = useRef<string | null>(null);

  useEffect(() => {
    let active = true;
    Promise.all([
      jsonFetch<PointPayload>(`/core/api/v1/service-points/${encodeURIComponent(token)}`),
      jsonFetch<AccessProfile>(`/core/api/v1/service-point-payments/points/${encodeURIComponent(token)}/profile`),
    ])
      .then(([pointBody, accessBody]) => {
        if (!active) return;
        setPoint(pointBody);
        setAccess(accessBody);
        setRequestCode(pointBody.request_options[0]?.code || "");
      })
      .catch((e) => active && setError(e instanceof Error ? e.message : "QR недоступен"))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [token]);

  useEffect(() => {
    if (!intent || !["AWAITING_PAYMENT", "PAID", "UNLOCK_PENDING"].includes(intent.status)) return;
    let cancelled = false;
    const timer = window.setInterval(async () => {
      try {
        const fresh = await jsonFetch<PaymentIntent>(`/core/api/v1/service-point-payments/points/${encodeURIComponent(token)}/intents/${intent.id}`);
        if (!cancelled) setIntent(fresh);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Не удалось проверить оплату");
      }
    }, 2000);
    return () => { cancelled = true; window.clearInterval(timer); };
  }, [intent?.id, intent?.status, token]);

  const selectedLabel = useMemo(
    () => point?.request_options.find((item) => item.code === requestCode)?.label || "",
    [point, requestCode],
  );

  function editRequest(next: () => void) {
    requestIdRef.current = null;
    setError(null);
    next();
  }

  async function startPayment() {
    if (paying) return;
    setPaying(true);
    setError(null);
    const clientRequestId = paymentRequestIdRef.current || crypto.randomUUID();
    paymentRequestIdRef.current = clientRequestId;
    try {
      const body = await jsonFetch<PaymentIntent>(`/core/api/v1/service-point-payments/points/${encodeURIComponent(token)}/intents`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ client_request_id: clientRequestId }),
      });
      setIntent(body);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось открыть оплату");
    } finally {
      setPaying(false);
    }
  }

  function retryPayment() {
    paymentRequestIdRef.current = null;
    setIntent(null);
    setError(null);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!requestCode || sending) return;
    setSending(true);
    setError(null);
    const clientRequestId = requestIdRef.current || crypto.randomUUID();
    requestIdRef.current = clientRequestId;
    try {
      const body = await jsonFetch<Created>(`/core/api/v1/service-points/${encodeURIComponent(token)}/requests`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          client_request_id: clientRequestId,
          request_code: requestCode,
          description: description.trim() || null,
        }),
      });
      requestIdRef.current = null;
      setCreated(body);
      setDescription("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось отправить заявку");
    } finally {
      setSending(false);
    }
  }

  if (loading) return <main className="spqr-shell"><section className="spqr-card"><p>Проверяем QR-код…</p></section></main>;
  if (!point || !access) return <main className="spqr-shell"><section className="spqr-card"><h1>QR-код недоступен</h1><p>Обратитесь к администратору.</p>{error && <small>{error}</small>}</section></main>;

  const paidLock = access.mode === "PAID_LOCK" && access.is_active;
  const terminalFailure = intent && ["PAYMENT_FAILED", "EXPIRED", "CANCELLED"].includes(intent.status);

  return <main className="spqr-shell">
    <section className="spqr-card">
      <p className="spqr-eyebrow">ТРИ КОРОНЫ · СЕРВИСНАЯ ТОЧКА</p>
      <h1>{point.point.name}</h1>
      {point.point.zone_label && <p className="spqr-zone">{point.point.zone_label}</p>}

      {paidLock && <section className="spqr-pay-card">
        <div className="spqr-pay-head">
          <div><span>Доступ по оплате</span><strong>{access.amount_kgs} сом</strong></div>
          <small>{access.provider_code || "BANK QR"} → {access.lock_provider_code || "LOCK"}</small>
        </div>

        {!access.runtime.ready && <div className="spqr-error">Оплата временно недоступна: {errorLabels[access.runtime.code] || access.runtime.code}</div>}

        {access.runtime.ready && !intent && <>
          <p className="spqr-copy">Нажмите «Оплатить». Система создаст отдельную банковскую операцию. Замок откроется только после подтверждения оплаты банком.</p>
          <button className="spqr-pay-button" type="button" disabled={paying} onClick={() => void startPayment()}>{paying ? "Создаём оплату…" : `Оплатить ${access.amount_kgs} сом`}</button>
        </>}

        {intent && <div className="spqr-payment-state">
          <div className="spqr-state-line"><span>Статус</span><strong>{intent.status}</strong></div>
          {intent.payment_qr_svg && ["CREATED", "AWAITING_PAYMENT"].includes(intent.status) && <div className="spqr-bank-qr" dangerouslySetInnerHTML={{ __html: intent.payment_qr_svg }} />}
          {intent.checkout_url && ["CREATED", "AWAITING_PAYMENT"].includes(intent.status) && <a className="spqr-checkout-link" href={intent.checkout_url} target="_blank" rel="noreferrer">Открыть оплату в банке</a>}
          {["CREATED", "AWAITING_PAYMENT"].includes(intent.status) && <p>После оплаты ничего нажимать не нужно — подтверждение придёт от банка автоматически.</p>}
          {intent.status === "PAID" && <p>Оплата подтверждена. Готовим открытие замка…</p>}
          {intent.status === "UNLOCK_PENDING" && <p>Оплата подтверждена. Команда на замок отправляется…</p>}
          {intent.status === "UNLOCKED" && <div className="spqr-unlocked"><strong>Дверь открыта</strong><span>Можно входить.</span></div>}
          {intent.status === "UNLOCK_FAILED" && <div className="spqr-error"><strong>Оплата получена.</strong><br />Замок не подтвердил открытие. Не оплачивайте повторно — обратитесь к администратору и назовите код {intent.reference}.</div>}
          {terminalFailure && <><div className="spqr-error">Оплата не завершена. Деньги не считаются подтверждёнными этой системой.</div><button className="spqr-pay-button" type="button" onClick={retryPayment}>Создать новую оплату</button></>}
          <small>Операция: {intent.reference}</small>
        </div>}
      </section>}

      <p className="spqr-copy">Если в этой зоне нужна уборка, ремонт или помощь, отправьте анонимную заявку ниже. Имя, номер комнаты и данные бронирования не требуются.</p>

      {created ? <div className="spqr-success">
        <strong>Заявка принята</strong>
        <p>{created.title}</p>
        <small>Статус: {created.status} · № {created.task_id.slice(0, 8)}</small>
        <button type="button" onClick={() => setCreated(null)}>Сообщить ещё</button>
      </div> : point.request_options.length ? <form onSubmit={submit} className="spqr-form">
        <label>
          Что требуется
          <select value={requestCode} onChange={(event) => editRequest(() => setRequestCode(event.target.value))} required>
            {point.request_options.map((item) => <option key={item.code} value={item.code}>{item.label}</option>)}
          </select>
        </label>
        <label>
          Комментарий <span>необязательно</span>
          <textarea value={description} onChange={(event) => editRequest(() => setDescription(event.target.value))} maxLength={1200} rows={4} placeholder={selectedLabel ? `Уточните: ${selectedLabel.toLowerCase()}` : "Опишите проблему"} />
        </label>
        {error && <div className="spqr-error">{error}</div>}
        <button type="submit" disabled={sending}>{sending ? "Отправляем…" : "Отправить заявку"}</button>
      </form> : <div className="spqr-error">Для этой зоны сейчас нет доступных типов обращений. Обратитесь к администратору.</div>}

      <p className="spqr-privacy">QR этой точки не раскрывает данные гостей. Платный доступ отделён от оплаты проживания: дверь открывается только после подтверждённого банковского события.</p>
    </section>
  </main>;
}
