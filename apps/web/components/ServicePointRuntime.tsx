"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

type PointPayload = {
  qr_valid: boolean;
  point: { code: string; name: string; category: string; zone_label?: string | null };
  request_options: Array<{ code: string; label: string }>;
  privacy: string;
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
};

async function jsonFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { cache: "no-store", ...init });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = body?.detail;
    const code = typeof detail === "object" && detail ? detail.code : null;
    throw new Error(
      (code && errorLabels[code]) ||
      (typeof detail === "string" ? detail : "Не удалось выполнить запрос"),
    );
  }
  return body as T;
}

export default function ServicePointRuntime({ token }: { token: string }) {
  const [point, setPoint] = useState<PointPayload | null>(null);
  const [requestCode, setRequestCode] = useState("");
  const [description, setDescription] = useState("");
  const [created, setCreated] = useState<Created | null>(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestIdRef = useRef<string | null>(null);

  useEffect(() => {
    let active = true;
    jsonFetch<PointPayload>(`/core/api/v1/service-points/${encodeURIComponent(token)}`)
      .then((body) => {
        if (!active) return;
        setPoint(body);
        setRequestCode(body.request_options[0]?.code || "");
      })
      .catch((e) => active && setError(e instanceof Error ? e.message : "QR недоступен"))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [token]);

  const selectedLabel = useMemo(
    () => point?.request_options.find((item) => item.code === requestCode)?.label || "",
    [point, requestCode],
  );

  function editRequest(next: () => void) {
    requestIdRef.current = null;
    setError(null);
    next();
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
  if (!point) return <main className="spqr-shell"><section className="spqr-card"><h1>QR-код недоступен</h1><p>Обратитесь к администратору.</p>{error && <small>{error}</small>}</section></main>;

  return <main className="spqr-shell">
    <section className="spqr-card">
      <p className="spqr-eyebrow">ТРИ КОРОНЫ · ПОМОЩЬ НА ТЕРРИТОРИИ</p>
      <h1>{point.point.name}</h1>
      {point.point.zone_label && <p className="spqr-zone">{point.point.zone_label}</p>}
      <p className="spqr-copy">Сообщите, что нужно исправить или сделать в этой зоне. Имя, номер комнаты и данные бронирования не требуются.</p>

      {created ? <div className="spqr-success">
        <strong>Заявка принята</strong>
        <p>{created.title}</p>
        <small>Статус: {created.status} · № {created.task_id.slice(0, 8)}</small>
        <button type="button" onClick={() => setCreated(null)}>Сообщить ещё</button>
      </div> : point.request_options.length ? <form onSubmit={submit} className="spqr-form">
        <label>
          Что требуется
          <select
            value={requestCode}
            onChange={(event) => editRequest(() => setRequestCode(event.target.value))}
            required
          >
            {point.request_options.map((item) => <option key={item.code} value={item.code}>{item.label}</option>)}
          </select>
        </label>
        <label>
          Комментарий <span>необязательно</span>
          <textarea
            value={description}
            onChange={(event) => editRequest(() => setDescription(event.target.value))}
            maxLength={1200}
            rows={4}
            placeholder={selectedLabel ? `Уточните: ${selectedLabel.toLowerCase()}` : "Опишите проблему"}
          />
        </label>
        {error && <div className="spqr-error">{error}</div>}
        <button type="submit" disabled={sending}>{sending ? "Отправляем…" : "Отправить заявку"}</button>
      </form> : <div className="spqr-error">Для этой зоны сейчас нет доступных типов обращений. Обратитесь к администратору.</div>}

      <p className="spqr-privacy">Анонимный QR общественной зоны. Он не открывает данные гостей и не выполняет оплату.</p>
    </section>
  </main>;
}
