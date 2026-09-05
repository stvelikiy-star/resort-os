"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type ReservationLedgerItem = {
  reservation_id: string;
  booking_number: string;
  status: "GUARANTEED" | "CHECKED_IN" | "CHECKED_OUT" | "CANCELLED" | string;
  check_in: string;
  check_out: string;
  guest_name?: string | null;
  guest_phone?: string | null;
  room_code?: string | null;
  total_kgs: number;
  received_kgs: number;
  remaining_kgs: number;
  overpaid_kgs: number;
  received_payment_count: number;
  last_received_at?: string | null;
  balance_stage: "PRE_ARRIVAL" | "IN_HOUSE" | "CHECKED_OUT_BALANCE" | "CANCELLED" | string;
};

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
  receivables_snapshot: {
    debtor_count: number;
    outstanding_kgs: number;
    checked_out_count: number;
    checked_out_kgs: number;
    in_house_count: number;
    in_house_kgs: number;
    pre_arrival_count: number;
    pre_arrival_kgs: number;
  };
  debtors: ReservationLedgerItem[];
  reservation_ledger: ReservationLedgerItem[];
  finance_exceptions: {
    snapshot: {
      overpaid_count: number;
      overpaid_kgs: number;
      cancelled_with_received_count: number;
      cancelled_with_received_kgs: number;
    };
    overpaid_reservations: ReservationLedgerItem[];
    cancelled_with_received: ReservationLedgerItem[];
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
    note?: string | null;
    recorded_by_staff_id?: string | null;
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

const balanceLabel: Record<string, string> = {
  PRE_ARRIVAL: "До заезда",
  IN_HOUSE: "Проживает",
  CHECKED_OUT_BALANCE: "Выехал с долгом",
  CANCELLED: "Отменена",
};

const reservationStatusLabel: Record<string, string> = {
  GUARANTEED: "GUARANTEED",
  CHECKED_IN: "CHECKED IN",
  CHECKED_OUT: "CHECKED OUT",
  CANCELLED: "CANCELLED",
};

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
        <p className="subtitle">Платёжные факты, долги и исключения из Resort Core. Это внутренний операционный контроль, не бухгалтерский отчёт и не автоматический эквайринг.</p>
      </div>
      <button className="btn" onClick={load} disabled={loading}>{loading ? "Обновляю…" : "Обновить"}</button>
    </div>

    <section className="finance-notice">
      <strong>Предоплата и способ оплаты остаются решением OWNER / MANAGER.</strong>
      <span>Система хранит только явно записанные условия и подтверждённые факты Payment. AI/n8n не подтверждают оплату и не создают финансовые записи напрямую.</span>
    </section>

    <section className="finance-filters" aria-label="Период внутреннего отчёта">
      <label><span>С</span><input type="date" value={fromDate} onChange={(event) => setFromDate(event.target.value)} /></label>
      <label><span>По</span><input type="date" value={toDate} onChange={(event) => setToDate(event.target.value)} /></label>
      <button className="btn primary" onClick={load} disabled={loading}>Показать период</button>
      {data && <small>Границы периода считаются по часовому поясу отеля: {data.range.timezone}</small>}
    </section>

    {error && <div className="error-box">{error}</div>}
    {loading && !data ? <div className="loading">Загрузка финансов…</div> : data && <>
      <section className="finance-kpis">
        <article><span>Получено за период</span><strong>{money(data.period_payments.received_kgs)}</strong><small>{data.period_payments.received_count} записей Payment.status=RECEIVED</small></article>
        <article><span>Общий долг</span><strong>{money(data.receivables_snapshot.outstanding_kgs)}</strong><small>{data.receivables_snapshot.debtor_count} броней с остатком</small></article>
        <article><span>Долг после выезда</span><strong>{money(data.receivables_snapshot.checked_out_kgs)}</strong><small>{data.receivables_snapshot.checked_out_count} CHECKED_OUT</small></article>
        <article><span>Стоимость активных броней</span><strong>{money(data.active_reservations_snapshot.booked_total_kgs)}</strong><small>{data.active_reservations_snapshot.reservation_count} GUARANTEED / CHECKED_IN</small></article>
      </section>

      <section className="finance-split-grid">
        <article className="finance-section">
          <div className="section-head"><h2>Дебиторская задолженность</h2><span>Текущий снимок Core</span></div>
          <div className="finance-state-grid">
            <div><span>До заезда</span><strong>{money(data.receivables_snapshot.pre_arrival_kgs)}</strong><small>{data.receivables_snapshot.pre_arrival_count} броней</small></div>
            <div><span>Проживают</span><strong>{money(data.receivables_snapshot.in_house_kgs)}</strong><small>{data.receivables_snapshot.in_house_count} броней</small></div>
            <div><span>После выезда</span><strong>{money(data.receivables_snapshot.checked_out_kgs)}</strong><small>{data.receivables_snapshot.checked_out_count} броней</small></div>
            <div><span>Всего</span><strong>{money(data.receivables_snapshot.outstanding_kgs)}</strong><small>{data.receivables_snapshot.debtor_count} должников</small></div>
          </div>
        </article>

        <article className="finance-section">
          <div className="section-head"><h2>Финансовые исключения</h2><span>Требуют проверки менеджера</span></div>
          <div className="finance-state-grid">
            <div><span>Переплаты</span><strong>{data.finance_exceptions.snapshot.overpaid_count}</strong><small>{money(data.finance_exceptions.snapshot.overpaid_kgs)}</small></div>
            <div><span>Отменённые с оплатой</span><strong>{data.finance_exceptions.snapshot.cancelled_with_received_count}</strong><small>{money(data.finance_exceptions.snapshot.cancelled_with_received_kgs)}</small></div>
            <div><span>Awaiting payment</span><strong>{data.awaiting_prepayment_snapshot.request_count}</strong><small>{money(data.awaiting_prepayment_snapshot.remaining_kgs)} осталось</small></div>
            <div><span>Refunded all-time</span><strong>{data.refunded_snapshot_all_time.payment_count}</strong><small>{money(data.refunded_snapshot_all_time.amount_kgs)}</small></div>
          </div>
        </article>
      </section>

      <section className="finance-section">
        <div className="section-head"><h2>Должники</h2><span>GUARANTEED / CHECKED_IN / CHECKED_OUT · остаток &gt; 0</span></div>
        <div className="transaction-table-wrap">
          <table className="transaction-table">
            <thead><tr><th>Стадия</th><th>Гость / бронь</th><th>Номер</th><th>Проживание</th><th>Стоимость</th><th>Получено</th><th>Остаток</th></tr></thead>
            <tbody>
              {data.debtors.length === 0 ? <tr><td colSpan={7}>Должников по сохранённым фактам нет.</td></tr> : data.debtors.map((item) => <tr key={item.reservation_id}>
                <td><strong>{balanceLabel[item.balance_stage] || item.balance_stage}</strong><small>{reservationStatusLabel[item.status] || item.status}</small></td>
                <td><strong>{item.guest_name || "—"}</strong><small>{item.booking_number}{item.guest_phone ? ` · ${item.guest_phone}` : ""}</small></td>
                <td>{item.room_code || "—"}</td>
                <td>{item.check_in} → {item.check_out}</td>
                <td>{money(item.total_kgs)}</td>
                <td>{money(item.received_kgs)}</td>
                <td><strong>{money(item.remaining_kgs)}</strong></td>
              </tr>)}
            </tbody>
          </table>
        </div>
      </section>

      {(data.finance_exceptions.overpaid_reservations.length > 0 || data.finance_exceptions.cancelled_with_received.length > 0) && <section className="finance-section">
        <div className="section-head"><h2>Разбор исключений</h2><span>Не исправляется автоматически</span></div>
        <div className="transaction-table-wrap">
          <table className="transaction-table">
            <thead><tr><th>Тип</th><th>Гость / бронь</th><th>Статус</th><th>Стоимость</th><th>Получено</th><th>Разница</th></tr></thead>
            <tbody>
              {data.finance_exceptions.overpaid_reservations.map((item) => <tr key={`over-${item.reservation_id}`}>
                <td><strong>Переплата</strong></td><td>{item.guest_name || "—"}<small>{item.booking_number}</small></td><td>{item.status}</td><td>{money(item.total_kgs)}</td><td>{money(item.received_kgs)}</td><td><strong>+{money(item.overpaid_kgs)}</strong></td>
              </tr>)}
              {data.finance_exceptions.cancelled_with_received.map((item) => <tr key={`cancel-${item.reservation_id}`}>
                <td><strong>Отменена с оплатой</strong></td><td>{item.guest_name || "—"}<small>{item.booking_number}</small></td><td>{item.status}</td><td>{money(item.total_kgs)}</td><td>{money(item.received_kgs)}</td><td><strong>{money(item.received_kgs)} к сверке</strong></td>
              </tr>)}
            </tbody>
          </table>
        </div>
      </section>}

      <section className="finance-split-grid">
        <article className="finance-section">
          <div className="section-head"><h2>Способы оплаты</h2><span>{fromDate} → {toDate}</span></div>
          <div className="finance-method-list">
            {data.received_by_method.length === 0 ? <p className="finance-empty">За период подтверждённых оплат нет.</p> : data.received_by_method.map((item) => <div key={item.method}><strong>{item.method}</strong><span>{item.payment_count} операций</span><b>{money(item.amount_kgs)}</b></div>)}
          </div>
        </article>

        <article className="finance-section">
          <div className="section-head"><h2>Состояние записей</h2><span>Выбранный период</span></div>
          <div className="finance-state-grid">
            <div><span>Получено</span><strong>{data.period_payments.received_count}</strong></div>
            <div><span>Pending</span><strong>{data.period_payments.pending_created_count}</strong></div>
            <div><span>Failed</span><strong>{data.period_payments.failed_count}</strong></div>
            <div><span>Cancelled</span><strong>{data.period_payments.cancelled_count}</strong></div>
          </div>
          <div className="finance-footnote">Refunded: {money(data.refunded_snapshot_all_time.amount_kgs)} · {data.refunded_snapshot_all_time.payment_count} записей за всё время. Отдельного нормализованного refund timestamp в текущей модели нет.</div>
        </article>
      </section>

      <section className="finance-section">
        <div className="section-head"><h2>Получено по локальным дням</h2><span>{data.received_by_day.length} дней с оплатами</span></div>
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
                <td>{item.external_ref || item.note || "—"}{item.external_ref && item.note ? <small>{item.note}</small> : null}</td>
              </tr>)}
            </tbody>
          </table>
        </div>
      </section>
    </>}
  </main>;
}
