"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type RequestItem = {
  id: string;
  status: string;
  source?: string | null;
  guest_name: string;
  phone: string;
  email?: string | null;
  check_in: string;
  check_out: string;
  adults: number;
  children: number;
  room_type_code?: string | null;
  room_type_name?: string | null;
  quoted_total_kgs?: number | null;
  required_prepayment_kgs?: number | null;
  notes?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  reservation?: { id: string; booking_number: string; status: string } | null;
};

type AvailabilityOption = {
  room_type_code: string;
  room_type_name: string;
  available_count: number;
  pricing: { sellable: boolean; total_kgs: number | null; reason?: string | null };
};

const fmt = (value?: number | null) => value == null ? "—" : new Intl.NumberFormat("ru-RU").format(value) + " сом";
const requestStatusLabel: Record<string, string> = {
  NEW: "Новая",
  QUOTED: "Рассчитана",
  AWAITING_PREPAYMENT: "На согласовании оплаты",
  CONVERTED: "Забронирована",
  CANCELLED: "Отменена",
  REJECTED: "Отклонена",
  EXPIRED: "Истекла",
};

function makePaymentKey(requestId: string) {
  const random = typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return `pms-request-payment-${requestId}-${random}`;
}

function paymentErrorMessage(body: any) {
  if (typeof body?.detail === "string") return body.detail;
  if (body?.detail?.code === "PAYMENT_EXTERNAL_REF_CONFLICT") {
    const amount = typeof body.detail.amount_kgs === "number" ? ` · ${fmt(body.detail.amount_kgs)}` : "";
    return `Этот номер операции уже записан${amount}. Проверьте существующий платёж перед созданием брони.`;
  }
  if (body?.detail?.code === "IDEMPOTENCY_CONFLICT") return "Запрос подтверждения уже использован для другой заявки. Обновите список и повторите.";
  if (body?.detail?.code === "IDEMPOTENCY_PAYLOAD_MISMATCH") return "Этот ключ операции уже был использован с другими реквизитами платежа.";
  return "Не удалось зафиксировать оплату и создать бронь";
}

function paymentRequirementError(body: any) {
  if (typeof body?.detail === "string") return body.detail;
  if (body?.detail?.code === "PAYMENT_REQUIREMENT_EXCEEDS_QUOTE") {
    return `Требуемая сумма не может превышать стоимость проживания ${fmt(body.detail.quoted_total_kgs)}.`;
  }
  if (body?.detail?.code === "PAYMENT_REQUIREMENT_REQUEST_NOT_QUOTED" || body?.detail?.code === "PAYMENT_REQUIREMENT_QUOTE_REQUIRED") {
    return "Сначала рассчитайте заявку и зафиксируйте стоимость проживания.";
  }
  return "Не удалось сохранить требуемую сумму предоплаты.";
}

function csvCell(value: unknown) {
  const text = value == null ? "" : String(value);
  return `"${text.replace(/"/g, '""')}"`;
}

function requestNights(item: RequestItem) {
  const start = new Date(`${item.check_in}T00:00:00Z`).getTime();
  const end = new Date(`${item.check_out}T00:00:00Z`).getTime();
  return Number.isFinite(start) && Number.isFinite(end) ? Math.max(Math.round((end - start) / 86400000), 0) : "";
}

export default function RequestsBoard() {
  const [items, setItems] = useState<RequestItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [options, setOptions] = useState<Record<string, AvailabilityOption[]>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [filter, setFilter] = useState("ACTIVE");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/core/api/v1/admin/booking/requests?limit=200", { cache: "no-store" });
      if (!response.ok) throw new Error("Не удалось загрузить заявки");
      const data = await response.json();
      setItems(data.items || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка загрузки");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const visible = useMemo(() => items.filter((item) => {
    if (filter === "ALL") return true;
    if (filter === "ACTIVE") return !["CONVERTED", "CANCELLED", "REJECTED", "EXPIRED"].includes(item.status);
    return item.status === filter;
  }), [items, filter]);

  function downloadCrmCsv() {
    const headers = [
      "Lead ID", "Дата/время", "Канал", "Имя", "Телефон", "Контакт/ник", "Город/страна",
      "Заезд", "Выезд", "Ночей", "Гостей", "Дети", "Тип номера", "Бюджет KGS", "Статус",
      "Ответственный", "Последний контакт", "Следующий контакт", "Источник/кампания", "Комментарий",
      "Ссылка на чат", "Booking ID",
    ];
    const rows = visible.map((item) => [
      item.id,
      item.created_at || "",
      item.source || "",
      item.guest_name,
      item.phone,
      item.email || "",
      "",
      item.check_in,
      item.check_out,
      requestNights(item),
      item.adults + item.children,
      item.children,
      item.room_type_name || item.room_type_code || "",
      item.quoted_total_kgs ?? "",
      requestStatusLabel[item.status] || item.status,
      "",
      item.updated_at || "",
      "",
      item.source || "",
      item.notes || "",
      "",
      item.reservation?.id || "",
    ]);
    const csv = "\uFEFF" + [headers, ...rows].map((row) => row.map(csvCell).join(";")).join("\r\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `three-crowns-crm-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }

  async function findOptions(item: RequestItem) {
    setBusy(item.id);
    setError(null);
    try {
      const q = new URLSearchParams({
        check_in: item.check_in,
        check_out: item.check_out,
        adults: String(item.adults),
        children: String(item.children),
      });
      const response = await fetch(`/core/api/v1/booking/check-availability?${q.toString()}`, { cache: "no-store" });
      if (!response.ok) throw new Error("Не удалось проверить наличие");
      const data = await response.json();
      setOptions((prev) => ({ ...prev, [item.id]: (data.results || []).filter((x: AvailabilityOption) => x.pricing.sellable) }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка проверки наличия");
    } finally {
      setBusy(null);
    }
  }

  async function quote(item: RequestItem, roomTypeCode: string) {
    setBusy(item.id);
    setError(null);
    try {
      const response = await fetch(`/core/api/v1/admin/booking/requests/${item.id}/quote`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ room_type_code: roomTypeCode }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Не удалось рассчитать заявку");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка расчёта");
    } finally {
      setBusy(null);
    }
  }

  async function setPaymentRequirement(item: RequestItem) {
    if (!item.quoted_total_kgs) {
      setError("Сначала рассчитайте стоимость проживания.");
      return;
    }
    const current = item.required_prepayment_kgs ? String(item.required_prepayment_kgs) : "";
    const amountText = window.prompt(
      `Какую сумму предоплаты требует менеджер? Максимум ${fmt(item.quoted_total_kgs)}. Процент автоматически не применяется.`,
      current,
    );
    if (amountText === null) return;
    const amount = Number(amountText.replace(/\s/g, ""));
    if (!Number.isFinite(amount) || amount <= 0 || amount > item.quoted_total_kgs) {
      setError(`Укажите положительную сумму не больше ${fmt(item.quoted_total_kgs)}.`);
      return;
    }
    setBusy(item.id);
    setError(null);
    try {
      const response = await fetch(`/core/api/v1/admin/finance/requests/${item.id}/payment-requirement`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ amount_kgs: Math.trunc(amount) }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(paymentRequirementError(body));
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка сохранения требуемой предоплаты");
    } finally {
      setBusy(null);
    }
  }

  async function confirmPayment(item: RequestItem) {
    const hint = item.required_prepayment_kgs ? String(item.required_prepayment_kgs) : "";
    const amountText = window.prompt("Сумма, которую менеджер фактически получил, сом", hint);
    if (!amountText) return;
    const amount = Number(amountText.replace(/\s/g, ""));
    if (!Number.isFinite(amount) || amount <= 0) {
      setError("Укажите фактически полученную положительную сумму.");
      return;
    }
    const externalRefText = window.prompt("Номер операции / внутренний комментарий (можно оставить пустым)", "");
    if (externalRefText === null) return;
    const externalRef = externalRefText.trim() || null;
    setBusy(item.id);
    setError(null);
    try {
      const response = await fetch(`/core/api/v1/admin/booking/requests/${item.id}/confirm-payment`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          amount_kgs: Math.trunc(amount),
          method: "MANAGER_MANUAL_CONFIRMATION",
          external_ref: externalRef,
          idempotency_key: makePaymentKey(item.id),
        }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(paymentErrorMessage(body));
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка фиксации оплаты");
    } finally {
      setBusy(null);
    }
  }

  return (
    <main className="work-shell">
      <div className="work-head">
        <div>
          <p className="eyebrow">Продажи · бронирование</p>
          <h1>Заявки гостей</h1>
          <p className="subtitle">n8n/сайт доводят клиента до заявки. Размер, условия и способ предоплаты определяет менеджер вручную.</p>
        </div>
        <div className="work-actions">
          <select value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="ACTIVE">Активные</option>
            <option value="NEW">Новые</option>
            <option value="QUOTED">Рассчитанные</option>
            <option value="AWAITING_PREPAYMENT">На согласовании оплаты</option>
            <option value="CONVERTED">Забронированы</option>
            <option value="ALL">Все</option>
          </select>
          <button className="btn" onClick={downloadCrmCsv} disabled={visible.length === 0}>CSV для CRM</button>
          <button className="btn" onClick={load}>Обновить</button>
        </div>
      </div>
      {error && <div className="error-box">{error}</div>}
      {loading ? <div className="loading">Загрузка заявок…</div> : (
        <div className="request-list">
          {visible.length === 0 && <div className="empty">Заявок в этом фильтре нет.</div>}
          {visible.map((item) => (
            <article className="request-card" key={item.id}>
              <div className="request-main">
                <div><span className={`status-pill s-${item.status}`}>{requestStatusLabel[item.status] || item.status}</span><h3>{item.guest_name}</h3><a href={`tel:${item.phone}`}>{item.phone}</a></div>
                <div className="request-dates"><b>{item.check_in} → {item.check_out}</b><span>{item.adults} взр. · {item.children} дет.</span></div>
              </div>
              <div className="request-money">
                <div><span>Категория</span><b>{item.room_type_name || "не выбрана"}</b></div>
                <div><span>Стоимость проживания</span><b>{fmt(item.quoted_total_kgs)}</b></div>
                <div><span>Требуемая предоплата</span><b>{item.required_prepayment_kgs ? fmt(item.required_prepayment_kgs) : "решает менеджер"}</b></div>
                {item.reservation && <div><span>Бронь</span><b>{item.reservation.booking_number}</b></div>}
              </div>
              {!item.reservation && <div className="request-actions">
                <button className="btn" disabled={busy === item.id} onClick={() => findOptions(item)}>Проверить варианты</button>
                {["QUOTED", "AWAITING_PREPAYMENT"].includes(item.status) && <button className="btn" disabled={busy === item.id} onClick={() => setPaymentRequirement(item)}>{item.required_prepayment_kgs ? "Изменить требуемую предоплату" : "Задать требуемую предоплату"}</button>}
                {["QUOTED", "AWAITING_PREPAYMENT"].includes(item.status) && <button className="btn primary" disabled={busy === item.id} onClick={() => confirmPayment(item)}>Оплата получена менеджером → создать бронь</button>}
              </div>}
              {options[item.id] && <div className="option-row">
                {options[item.id].length === 0 ? <span>Нет продаваемых вариантов.</span> : options[item.id].map((option) => <button key={option.room_type_code} onClick={() => quote(item, option.room_type_code)} disabled={busy === item.id}><b>{option.room_type_name}</b><span>{option.available_count} своб. · {fmt(option.pricing.total_kgs)}</span></button>)}
              </div>}
            </article>
          ))}
        </div>
      )}
    </main>
  );
}
