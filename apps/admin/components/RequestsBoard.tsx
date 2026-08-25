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
  reservation?: { id: string; booking_number: string; status: string } | null;
};

type AvailabilityOption = {
  room_type_code: string;
  room_type_name: string;
  available_count: number;
  pricing: { sellable: boolean; total_kgs: number | null; reason?: string | null };
};

const fmt = (value?: number | null) => value == null ? "—" : new Intl.NumberFormat("ru-RU").format(value) + " сом";

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
      if (!response.ok) throw new Error(body.detail || "Не удалось рассчитать заявку");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка расчёта");
    } finally {
      setBusy(null);
    }
  }

  async function confirmPayment(item: RequestItem) {
    const amountText = window.prompt("Сумма, которую менеджер фактически получил, сом", "");
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
          amount_kgs: amount,
          method: "MANAGER_MANUAL_CONFIRMATION",
          provider: "MANAGER_MANUAL",
          external_ref: externalRef,
          idempotency_key: `pms-${item.id}-${Date.now()}`,
        }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Не удалось зафиксировать оплату и создать бронь");
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
                <div><span className={`status-pill s-${item.status}`}>{item.status}</span><h3>{item.guest_name}</h3><a href={`tel:${item.phone}`}>{item.phone}</a></div>
                <div className="request-dates"><b>{item.check_in} → {item.check_out}</b><span>{item.adults} взр. · {item.children} дет.</span></div>
              </div>
              <div className="request-money">
                <div><span>Категория</span><b>{item.room_type_name || "не выбрана"}</b></div>
                <div><span>Стоимость проживания</span><b>{fmt(item.quoted_total_kgs)}</b></div>
                <div><span>Предоплата</span><b>{item.required_prepayment_kgs ? fmt(item.required_prepayment_kgs) : "решает менеджер"}</b></div>
                {item.reservation && <div><span>Бронь</span><b>{item.reservation.booking_number}</b></div>}
              </div>
              {!item.reservation && <div className="request-actions">
                <button className="btn" disabled={busy === item.id} onClick={() => findOptions(item)}>Проверить варианты</button>
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
