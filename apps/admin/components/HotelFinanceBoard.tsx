"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type FinanceResponse = {
  scope: {
    internal_only: boolean;
    payment_collection: string;
    manager_decides_prepayment: boolean;
    automated_acquiring_required: boolean;
    accounting_report: boolean;
  };
  range: { from: string; to: string; timezone: string; currency: string };
  period_payments: {
    received_kgs: number;
    received_count: number;
    pending_created_kgs: number;
    pending_created_count: number;
    failed_count: number;
    cancelled_count: number;
  };
  received_by_method: Array<{ method: string; amount_kgs: number; payment_count: number }>;
  received_by_day: Array<{ local_date: string; amount_kgs: number; payment_count: number }>;
  active_reservations_snapshot: {
    reservation_count: number;
    booked_total_kgs: number;
    received_kgs: number;
    outstanding_kgs: number;
  };
  awaiting_prepayment_snapshot: {
    request_count: number;
    required_kgs: number;
    received_kgs: number;
    remaining_kgs: number;
  };
  refunded_snapshot_all_time: { amount_kgs: number; payment_count: number };
  recent_payments: Array<{
    id: string;
    amount_kgs: number;
    method: string;
    status: string;
    provider?: string | null;
    external_ref?: string | null;
    paid_at?: string | null;
    created_at: string;
    request_id?: string | null;
    reservation_id?: string | null;
    booking_number?: string | null;
    guest_name?: string | null;
  }>;
};

function dateOnly(value: Date) {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function monthStart(value: Date) {
  return new Date(value.getFullYear(), value.getMonth(), 1);
}

const money = (value: number) => `${new Intl.NumberFormat("ru-RU").format(Number(value || 0))} сом`;

export default function HotelFinanceBoard() {
  const now = useMemo(() => new Date(), []);
  const [fromDate, setFromDate] = useState(() => dateOnly(monthStart(now)));
  const [toDate, setToDate] = useState(() => dateOnly(now));
  const [data, setData] = useState<FinanceResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ from_date: fromDate, to_date: toDate });
      const response = await fetch(`/core/api/v1/admin/finance/summary?${params}`, { cache: "no-store" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Не удалось загрузить внутренние финансы");
      setData(body as FinanceResponse);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Ошибка загрузки внутренних финансов");
    } finally {
      setLoading(false);
    }
  }, [fromDate, toDate]);

  useEffect(() => { void load(); }, [load]);

  return <main className="work-shell hotel-finance-shell">
    <div className="work-head">
      <div>
        <p className="eyebrow">PMS · внутренний контроль</p>
        <h1>Финансы отеля</h1>
        <p className="subtitle">Только факты, которые менеджер уже записал в Resort OS. Это не бухгалтерский отчёт и не автоматический эквайринг.</p>
      </div>
      <button className="btn" onClick={load} disabled={loading}>{loading ? "Обновляю…" : "Обновить"}</button>
    </div>

    <section className="finance-notice">
      <strong>Предоплата остаётся решением менеджера.</strong>
      <span>Система показывает полученные и сохранённые факты, но не назначает сумму, способ оплаты и не принимает деньги сама.</span>
    </section>

    <section className="finance-filters" aria-label="Период внутреннего отчёта">
      <label><span>С</span><input type="date" value={fromDate} onChange={(event) => setFromDate(event.target.value)} /></label>
      <label><span>По</span><input type="date" value={toDate} onChange={(event) => setToDate(event.target.value)} /></label>
      <button className="btn primary" onClick={load} disabled={loading}>Показать период</button>
      {data && <small>Часовой пояс: {data.range.timezone}</small>}
    </section>

    {error && <div className="error-box">{error}</div>}
    {loading && !data ? <div className="loading">Загрузка финансов…</div> : data && <>
      <section className="finance-kpis">
        <article><span>Получено за период</span><strong>{money(data.period_payments.received_kgs)}</strong><small>{data.period_payments.received_count} записей</small></article>
        <article><span>Активные брони</span><strong>{money(data.active_reservations_snapshot.booked_total_kgs)}</strong><small>{data.active_reservations_snapshot.reservation_count} броней</small></article>
        <article><span>Подтверждено по активным</span><strong>{money(data.active_reservations_snapshot.received_kgs)}</strong><small>Только Payment.status = RECEIVED</small></article>
        <article><span>Остаток по активным</span><strong>{money(data.active_reservations_snapshot.outstanding_kgs)}</strong><small>Стоимость минус подтверждённые оплаты</small></article>
      </section>

      <section className="finance-split-grid">
        <article className="finance-section">
          <div className="section-head"><h2>Способы оплаты</h2><span>{fromDate} → {toDate}</span></div>
          <div className="finance-method-list">
            {data.received_by_method.length === 0 ? <p className="finance-empty">За период подтверждённых оплат нет.</p> : data.received_by_method.map((item) => <div key={item.method}><strong>{item.method}</strong><span>{item.payment_count} операций</span><b>{money(item.amount_kgs)}</b></div>)}
          </div>
        </article>

        <article className="finance-section">
          <div className="section-head"><h2>Состояние записей</h2><span>Внутренний снимок</span></div>
          <div className="finance-state-grid">
            <div><span>Получено</span><strong>{data.period_payments.received_count}</strong></div>
            <div><span>Pending</span><strong>{data.period_payments.pending_created_count}</strong></div>
            <div><span>Failed</span><strong>{data.period_payments.failed_count}</strong></div>
            <div><span>Cancelled</span><strong>{data.period_payments.cancelled_count}</strong></div>
          </div>
          <div className="finance-footnote">Refunded: {money(data.refunded_snapshot_all_time.amount_kgs)} · {data.refunded_snapshot_all_time.payment_count} записей за всё время. По текущей модели дата возврата отдельно не нормализована.</div>
        </article>
      </section>

      <section className="finance-section">
        <div className="section-head"><h2>Получено по дням</h2><span>{data.received_by_day.length} дней с оплатами</span></div>
        <div className="finance-day-list">
          {data.received_by_day.length === 0 ? <p className="finance-empty">За выбранный период данных нет.</p> : data.received_by_day.map((item) => <div key={item.local_date}><span>{item.local_date}</span><b>{money(item.amount_kgs)}</b><small>{item.payment_count} операций</small></div>)}
        </div>
      </section>

      <section className="finance-section">
        <div className="section-head"><h2>Последние записи оплат</h2><span>До 100 последних записей Core</span></div>
        <div className="transaction-table-wrap">
          <table className="transaction-table">
            <thead><tr><th>Дата</th><th>Гость / бронь</th><th>Сумма</th><th>Способ</th><th>Статус</th><th>Ссылка / комментарий</th></tr></thead>
            <tbody>
              {data.recent_payments.length === 0 ? <tr><td colSpan={6}>Записей оплаты пока нет.</td></tr> : data.recent_payments.map((item) => <tr key={item.id}>
                <td>{item.paid_at || item.created_at}</td>
                <td><strong>{item.guest_name || "—"}</strong><small>{item.booking_number || (item.request_id ? `Request ${item.request_id.slice(0, 8)}…` : "—")}</small></td>
                <td><strong>{money(item.amount_kgs)}</strong></td>
                <td>{item.method || "—"}<small>{item.provider || ""}</small></td>
                <td><span className={`tx-status ${item.status}`}>{item.status}</span></td>
                <td>{item.external_ref || "—"}</td>
              </tr>)}
            </tbody>
          </table>
        </div>
      </section>
    </>}
  </main>;
}
