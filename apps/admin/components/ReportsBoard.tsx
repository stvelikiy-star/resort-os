"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import OwnerOccupancyMatrix from "./OwnerOccupancyMatrix";

type Report = {
  property: { name: string; local_date: string; currency: string };
  range: { from: string; to: string; days: number };
  kpi: Record<string, number>;
  rooms_now: Record<string, number>;
  crm: {
    leads: number;
    new: number;
    quoted: number;
    awaiting_prepayment: number;
    converted: number;
    lost: number;
    conversion_percent: number;
    channels: Array<{ source: string; leads: number; converted: number; conversion_percent: number }>;
  };
  payments: { received_kgs: number; received_count: number; refunded_status_amount_kgs: number; failed_count: number };
  room_types: Array<{
    code: string;
    name: string;
    room_count: number;
    reservation_count: number;
    booked_room_nights: number;
    available_room_nights: number;
    occupancy_percent: number;
    allocated_booked_value_kgs: number;
    adr_kgs: number;
    revpar_kgs: number;
  }>;
  channels: Array<{ source: string; reservations: number; allocated_booked_value_kgs: number }>;
  operations: Array<{ type: string; created_in_period: number; completed_in_period: number; active_now: number; urgent_now: number }>;
  debtors: Array<{
    reservation_id: string;
    booking_number: string;
    status: string;
    guest_name?: string | null;
    phone?: string | null;
    check_in: string;
    check_out: string;
    total_kgs: number;
    paid_kgs: number;
    outstanding_kgs: number;
  }>;
  daily: Array<{ date: string; booked_rooms: number; occupancy_percent: number; received_kgs: number; arrivals: number; departures: number }>;
  truth: Record<string, string>;
};

const money = (value: number) => `${new Intl.NumberFormat("ru-RU").format(Math.round(value || 0))} сом`;
const pct = (value: number) => `${Number(value || 0).toFixed(1)}%`;
const localIso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const parseIso = (value: string) => { const [year, month, day] = value.split("-").map(Number); return new Date(year, month - 1, day); };

function csvCell(value: unknown) {
  const text = value == null ? "" : String(value);
  return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

function downloadCsv(filename: string, rows: Array<Record<string, unknown>>) {
  if (!rows.length) return;
  const columns = Array.from(new Set(rows.flatMap((row) => Object.keys(row))));
  const text = [columns, ...rows.map((row) => columns.map((key) => row[key]))]
    .map((row) => row.map(csvCell).join(","))
    .join("\n");
  const blob = new Blob(["\ufeff", text], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function defaultDates() {
  const end = new Date();
  const start = new Date(end);
  start.setDate(start.getDate() - 29);
  return { from: localIso(start), to: localIso(end) };
}

function previousRange(from: string, to: string) {
  const start = parseIso(from);
  const end = parseIso(to);
  const days = Math.max(1, Math.round((end.getTime() - start.getTime()) / 86400000) + 1);
  const previousTo = new Date(start);
  previousTo.setDate(previousTo.getDate() - 1);
  const previousFrom = new Date(previousTo);
  previousFrom.setDate(previousFrom.getDate() - days + 1);
  return { from: localIso(previousFrom), to: localIso(previousTo) };
}

function delta(current: number, previous: number, suffix = "") {
  const difference = Number(current || 0) - Number(previous || 0);
  return { value: `${difference >= 0 ? "+" : ""}${suffix === "%" ? difference.toFixed(1) : new Intl.NumberFormat("ru-RU").format(Math.round(difference))}${suffix}`, positive: difference >= 0 };
}

const operationLabel: Record<string, string> = {
  HOUSEKEEPING: "Уборка",
  MAINTENANCE: "Ремонт",
  GUEST_REQUEST: "Запросы гостей",
};

export default function ReportsBoard() {
  const initial = useMemo(defaultDates, []);
  const [fromDate, setFromDate] = useState(initial.from);
  const [toDate, setToDate] = useState(initial.to);
  const [report, setReport] = useState<Report | null>(null);
  const [comparison, setComparison] = useState<Report | null>(null);
  const [compareEnabled, setCompareEnabled] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const comparisonRange = useMemo(() => previousRange(fromDate, toDate), [fromDate, toDate]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const query = new URLSearchParams({ from_date: fromDate, to_date: toDate });
      const requests: Promise<Response>[] = [fetch(`/core/api/v1/admin/reports/overview?${query}`, { cache: "no-store" })];
      if (compareEnabled) {
        const previous = new URLSearchParams({ from_date: comparisonRange.from, to_date: comparisonRange.to });
        requests.push(fetch(`/core/api/v1/admin/reports/overview?${previous}`, { cache: "no-store" }));
      }
      const responses = await Promise.all(requests);
      const currentBody = await responses[0].json().catch(() => ({}));
      if (!responses[0].ok) throw new Error(currentBody.detail || "Не удалось сформировать отчёт");
      setReport(currentBody as Report);
      if (compareEnabled && responses[1]) {
        const previousBody = await responses[1].json().catch(() => ({}));
        if (!responses[1].ok) throw new Error(previousBody.detail || "Не удалось сформировать сравнительный период");
        setComparison(previousBody as Report);
      } else {
        setComparison(null);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка отчёта");
    } finally {
      setLoading(false);
    }
  }, [fromDate, toDate, compareEnabled, comparisonRange.from, comparisonRange.to]);

  useEffect(() => { void load(); }, [load]);

  function preset(days: number) {
    const end = new Date();
    const start = new Date(end);
    start.setDate(end.getDate() - days + 1);
    setFromDate(localIso(start));
    setToDate(localIso(end));
  }

  function currentMonth() {
    const now = new Date();
    setFromDate(localIso(new Date(now.getFullYear(), now.getMonth(), 1)));
    setToDate(localIso(new Date(now.getFullYear(), now.getMonth() + 1, 0)));
  }

  function previousMonth() {
    const now = new Date();
    setFromDate(localIso(new Date(now.getFullYear(), now.getMonth() - 1, 1)));
    setToDate(localIso(new Date(now.getFullYear(), now.getMonth(), 0)));
  }

  function season() {
    const year = new Date().getFullYear();
    setFromDate(`${year}-06-01`);
    setToDate(`${year}-09-15`);
  }

  function year() {
    const value = new Date().getFullYear();
    setFromDate(`${value}-01-01`);
    setToDate(`${value}-12-31`);
  }

  const chartDaily = useMemo(() => {
    if (!report) return [];
    return report.daily.length > 45 ? report.daily.slice(-45) : report.daily;
  }, [report]);

  const excelHref = `/core/api/v1/admin/intelligence/export.xlsx?${new URLSearchParams({ from_date: fromDate, to_date: toDate }).toString()}`;

  return (
    <main className="reports-shell">
      <header className="reports-head">
        <div>
          <p className="eyebrow">OWNER CONTROL · RESORT CORE</p>
          <h1>Отчёты и аналитика</h1>
          <p>Загрузка, продажи, деньги, категории, каналы, задолженность, операции и история номерного фонда — из одной базы Resort Core.</p>
        </div>
        <div className="reports-actions">
          <button className="btn" onClick={() => preset(7)}>7 дней</button>
          <button className="btn" onClick={currentMonth}>Этот месяц</button>
          <button className="btn" onClick={previousMonth}>Прошлый месяц</button>
          <button className="btn" onClick={season}>Сезон</button>
          <button className="btn" onClick={year}>Год</button>
          <a className="btn" href={excelHref}>Excel</a>
          <button className="btn" onClick={() => window.print()}>Печать / PDF</button>
          <button className="btn primary" onClick={load} disabled={loading}>{loading ? "Считаю…" : "Обновить"}</button>
        </div>
      </header>

      <section className="reports-filter">
        <label><span>С</span><input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} /></label>
        <label><span>По</span><input type="date" value={toDate} onChange={(e) => setToDate(e.target.value)} /></label>
        <label className="reports-compare-toggle"><input type="checkbox" checked={compareEnabled} onChange={(e) => setCompareEnabled(e.target.checked)} /><span>Сравнить с предыдущим периодом</span></label>
        {report && <small>{report.range.days} календарных дней · данные Resort Core</small>}
      </section>

      {error && <div className="error-box">{error}</div>}
      {loading && !report && <div className="loading">Формирую управленческий отчёт…</div>}

      {report && <>
        {comparison && compareEnabled && (
          <section className="reports-comparison">
            <div className="reports-comparison-head"><div><span>Сравнение</span><strong>{fromDate} — {toDate}</strong></div><small>vs {comparisonRange.from} — {comparisonRange.to}</small></div>
            {[
              ["Загрузка", delta(report.kpi.occupancy_percent, comparison.kpi.occupancy_percent, "%")],
              ["ADR", delta(report.kpi.adr_kgs, comparison.kpi.adr_kgs, " сом")],
              ["RevPAR", delta(report.kpi.revpar_kgs, comparison.kpi.revpar_kgs, " сом")],
              ["Получено оплат", delta(report.kpi.received_payments_kgs, comparison.kpi.received_payments_kgs, " сом")],
              ["Номеро-ночи", delta(report.kpi.booked_room_nights, comparison.kpi.booked_room_nights)],
              ["CRM-конверсия", delta(report.crm.conversion_percent, comparison.crm.conversion_percent, "%")],
            ].map(([label, change]) => {
              const value = change as { value: string; positive: boolean };
              return <article key={String(label)}><span>{String(label)}</span><strong className={value.positive ? "up" : "down"}>{value.value}</strong></article>;
            })}
          </section>
        )}

        <section className="reports-kpis">
          <article><span>Загрузка</span><strong>{pct(report.kpi.occupancy_percent)}</strong><small>{report.kpi.booked_room_nights} / {report.kpi.available_room_nights} номеро-ночей</small></article>
          <article><span>ADR</span><strong>{money(report.kpi.adr_kgs)}</strong><small>управленческий</small></article>
          <article><span>RevPAR</span><strong>{money(report.kpi.revpar_kgs)}</strong><small>управленческий</small></article>
          <article><span>Стоимость броней</span><strong>{money(report.kpi.allocated_booked_value_kgs)}</strong><small>распределено по ночам периода</small></article>
          <article className="money-card"><span>Получено оплат</span><strong>{money(report.kpi.received_payments_kgs)}</strong><small>{report.kpi.received_payment_count} операций</small></article>
          <article className={report.kpi.active_outstanding_kgs > 0 ? "danger-card" : ""}><span>Дебиторка сейчас</span><strong>{money(report.kpi.active_outstanding_kgs)}</strong><small>{report.kpi.active_debtor_count} активных броней</small></article>
          <article><span>Заезды периода</span><strong>{report.kpi.arrivals}</strong><small>гарантированные / прожитые</small></article>
          <article><span>Выезды периода</span><strong>{report.kpi.departures}</strong><small>проживание</small></article>
          <article><span>Сейчас проживают</span><strong>{report.kpi.in_house_now}</strong><small>броней</small></article>
          <article><span>Ожидают заезд</span><strong>{report.kpi.guaranteed_now}</strong><small>гарантированных броней</small></article>
          <article><span>CRM-конверсия</span><strong>{pct(report.crm.conversion_percent)}</strong><small>{report.crm.converted} / {report.crm.leads}</small></article>
          <article><span>Техблок сейчас</span><strong>{report.rooms_now.tech_block || 0}</strong><small>из {report.rooms_now.total || 0} комнат</small></article>
        </section>

        <OwnerOccupancyMatrix fromDate={fromDate} toDate={toDate} />

        <section className="report-card report-chart-card">
          <div className="report-card-head"><div><span>Динамика</span><h2>Загрузка по дням</h2></div><button className="btn sm" onClick={() => downloadCsv(`three-crowns-daily-${fromDate}-${toDate}.csv`, report.daily)}>CSV по дням</button></div>
          <div className="occupancy-chart" aria-label="График загрузки">
            {chartDaily.map((day) => <div className="occupancy-column" key={day.date} title={`${day.date}: ${day.occupancy_percent}% · ${money(day.received_kgs)}`}>
              <div className="occupancy-bar-wrap"><i style={{ height: `${Math.max(2, Math.min(100, day.occupancy_percent))}%` }} /></div>
              <strong>{Math.round(day.occupancy_percent)}</strong>
              <span>{day.date.slice(5)}</span>
            </div>)}
          </div>
        </section>

        <div className="reports-two">
          <section className="report-card">
            <div className="report-card-head"><div><span>Продажи</span><h2>CRM-воронка</h2></div></div>
            <div className="funnel-grid">
              <div><span>Все лиды</span><strong>{report.crm.leads}</strong></div>
              <div><span>Новые</span><strong>{report.crm.new}</strong></div>
              <div><span>Котировка</span><strong>{report.crm.quoted}</strong></div>
              <div><span>Ждут предоплату</span><strong>{report.crm.awaiting_prepayment}</strong></div>
              <div><span>В бронь</span><strong>{report.crm.converted}</strong></div>
              <div><span>Закрыты</span><strong>{report.crm.lost}</strong></div>
            </div>
            <div className="mini-table">
              {report.crm.channels.map((row) => <div key={row.source}><b>{row.source}</b><span>{row.leads} лидов</span><strong>{pct(row.conversion_percent)}</strong></div>)}
            </div>
          </section>

          <section className="report-card">
            <div className="report-card-head"><div><span>Операции</span><h2>Уборка и ремонт</h2></div></div>
            <div className="ops-report-grid">
              {report.operations.map((row) => <article key={row.type}>
                <span>{operationLabel[row.type] || row.type}</span>
                <strong>{row.active_now}</strong>
                <small>активно сейчас</small>
                <div><em>{row.created_in_period} создано</em><em>{row.completed_in_period} завершено</em>{row.urgent_now > 0 && <em className="urgent">{row.urgent_now} срочно</em>}</div>
              </article>)}
            </div>
          </section>
        </div>

        <section className="report-card">
          <div className="report-card-head"><div><span>Номерной фонд</span><h2>Эффективность категорий</h2></div><button className="btn sm" onClick={() => downloadCsv(`three-crowns-room-types-${fromDate}-${toDate}.csv`, report.room_types)}>CSV категорий</button></div>
          <div className="report-table-wrap"><table className="report-table"><thead><tr><th>Категория</th><th>Комнат</th><th>Броней</th><th>Ночей</th><th>Загрузка</th><th>Стоимость</th><th>ADR</th><th>RevPAR</th></tr></thead><tbody>
            {report.room_types.map((row) => <tr key={row.code}><td><strong>{row.name}</strong><small>{row.code}</small></td><td>{row.room_count}</td><td>{row.reservation_count}</td><td>{row.booked_room_nights}</td><td>{pct(row.occupancy_percent)}</td><td>{money(row.allocated_booked_value_kgs)}</td><td>{money(row.adr_kgs)}</td><td>{money(row.revpar_kgs)}</td></tr>)}
          </tbody></table></div>
        </section>

        <div className="reports-two">
          <section className="report-card">
            <div className="report-card-head"><div><span>Источники</span><h2>Каналы броней</h2></div></div>
            <div className="channel-report-list">{report.channels.length ? report.channels.map((row) => <div key={row.source}><strong>{row.source}</strong><span>{row.reservations} броней</span><b>{money(row.allocated_booked_value_kgs)}</b></div>) : <p className="report-empty">За период броней по каналам нет.</p>}</div>
          </section>

          <section className="report-card">
            <div className="report-card-head"><div><span>Контроль денег</span><h2>Текущая задолженность</h2></div><button className="btn sm" disabled={!report.debtors.length} onClick={() => downloadCsv(`three-crowns-debtors-${toDate}.csv`, report.debtors)}>CSV дебиторки</button></div>
            <div className="debtor-list">{report.debtors.slice(0, 12).map((row) => <div key={row.reservation_id}><div><strong>{row.booking_number} · {row.guest_name || "Гость"}</strong><span>{row.check_in} → {row.check_out}{row.phone ? ` · ${row.phone}` : ""}</span></div><b>{money(row.outstanding_kgs)}</b></div>)}{!report.debtors.length && <p className="report-empty">По активным броням задолженности нет.</p>}</div>
          </section>
        </div>

        <section className="report-truth">
          <strong>Как читать цифры</strong>
          <p>{report.truth.allocated_booked_value}</p>
          <p>{report.truth.received_payments}</p>
          <p>{report.truth.adr_revpar}</p>
          <p>Excel-выгрузка содержит отдельные листы «Итоги», «Занятость по номерам», «Брони», «Гости» и «Платежи». Это управленческий, а не бухгалтерский отчёт.</p>
        </section>
      </>}
    </main>
  );
}
