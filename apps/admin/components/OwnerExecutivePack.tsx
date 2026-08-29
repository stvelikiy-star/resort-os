"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type Report = {
  range: { from: string; to: string; days: number };
  kpi: {
    occupancy_percent: number;
    adr_kgs: number;
    revpar_kgs: number;
    allocated_booked_value_kgs: number;
    received_payments_kgs: number;
    active_outstanding_kgs: number;
    active_debtor_count: number;
  } & Record<string, number>;
  crm: { conversion_percent: number; leads: number; converted: number };
};

type Brief = {
  property: { local_date: string; name: string; timezone: string };
  forward: {
    next_30_days: {
      booked_room_nights: number;
      available_room_nights: number;
      occupancy_on_books_percent: number;
      allocated_booked_value_kgs: number;
      arrivals: number;
      departures: number;
    };
  };
  actions: Array<{ code: string; severity: "CRITICAL" | "HIGH" | "NORMAL"; count: number; label: string }>;
  pickup_readiness: { status: string; latest_prior_snapshot_date?: string | null };
};

type Growth = {
  queue: { active: number; overdue: number; feedback_open: number; return_open: number };
  feedback: {
    scored: number;
    average_score: number | null;
    promoters: number;
    passives: number;
    detractors: number;
    recovery_open: number;
    nps: number | null;
    nps_sample_size: number;
  };
  candidates: { post_stay_14d: number; reactivation: number; reactivation_min_days: number };
};

type Pickup = {
  status: string;
  baseline?: { snapshot_date: string; age_days: number };
  summary?: {
    room_night_pickup: number;
    booked_value_pickup_kgs: number;
    current_booked_room_nights: number;
  };
};

const money = (value?: number | null) => `${new Intl.NumberFormat("ru-RU").format(Math.round(value || 0))} сом`;
const pct = (value?: number | null) => `${Number(value || 0).toFixed(1)}%`;

function iso(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function fromIso(value: string) {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function monthRanges(localDate: string) {
  const now = fromIso(localDate);
  const currentFrom = new Date(now.getFullYear(), now.getMonth(), 1);
  const previousFrom = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  const previousTo = new Date(now.getFullYear(), now.getMonth(), 0);
  return {
    current: { from: iso(currentFrom), to: localDate },
    previous: { from: iso(previousFrom), to: iso(previousTo) },
  };
}

function next30Range(localDate: string) {
  const start = fromIso(localDate);
  const end = new Date(start);
  end.setDate(end.getDate() + 29);
  return { from: localDate, to: iso(end) };
}

async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url, { cache: "no-store" });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Не удалось загрузить Owner Executive Pack");
  return body as T;
}

function delta(current: number, previous: number, kind: "money" | "pct" | "number") {
  const value = Number(current || 0) - Number(previous || 0);
  const prefix = value > 0 ? "+" : "";
  if (kind === "money") return `${prefix}${money(value)}`;
  if (kind === "pct") return `${prefix}${value.toFixed(1)} п.п.`;
  return `${prefix}${new Intl.NumberFormat("ru-RU").format(Math.round(value))}`;
}

export default function OwnerExecutivePack() {
  const [brief, setBrief] = useState<Brief | null>(null);
  const [growth, setGrowth] = useState<Growth | null>(null);
  const [current, setCurrent] = useState<Report | null>(null);
  const [previous, setPrevious] = useState<Report | null>(null);
  const [pickup, setPickup] = useState<Pickup | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [ownerBrief, growthSummary] = await Promise.all([
        getJson<Brief>("/core/api/v1/admin/intelligence/owner-brief?horizon_days=30"),
        getJson<Growth>("/core/api/v1/admin/growth/summary?min_days_since_checkout=30"),
      ]);
      const ranges = monthRanges(ownerBrief.property.local_date);
      const next30 = next30Range(ownerBrief.property.local_date);
      const [currentReport, previousReport, pickupBody] = await Promise.all([
        getJson<Report>(`/core/api/v1/admin/reports/overview?${new URLSearchParams({ from_date: ranges.current.from, to_date: ranges.current.to })}`),
        getJson<Report>(`/core/api/v1/admin/reports/overview?${new URLSearchParams({ from_date: ranges.previous.from, to_date: ranges.previous.to })}`),
        getJson<Pickup>(`/core/api/v1/admin/intelligence/pickup?${new URLSearchParams({ from_date: next30.from, to_date: next30.to })}`),
      ]);
      setBrief(ownerBrief);
      setGrowth(growthSummary);
      setCurrent(currentReport);
      setPrevious(previousReport);
      setPickup(pickupBody);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка Owner Executive Pack");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const actionFacts = useMemo(() => {
    const items = brief?.actions.filter((item) => item.count > 0) || [];
    return {
      critical: items.filter((item) => item.severity === "CRITICAL").reduce((sum, item) => sum + item.count, 0),
      high: items.filter((item) => item.severity === "HIGH").reduce((sum, item) => sum + item.count, 0),
      items,
    };
  }, [brief]);

  if (loading && !brief) return <section className="owner-executive loading">Формирую Owner Executive Pack…</section>;
  if (error && !brief) return <section className="owner-executive"><div className="error-box">{error}</div><button className="btn" onClick={load}>Повторить</button></section>;
  if (!brief || !growth || !current || !previous) return null;

  const forward = brief.forward.next_30_days;
  const pickupReady = pickup?.status === "READY" && pickup.summary;

  return (
    <section className="owner-executive">
      <div className="owner-executive-head">
        <div>
          <p className="eyebrow">OWNER EXECUTIVE PACK · RESORT CORE</p>
          <h2>Сводка собственника</h2>
          <p>{brief.property.local_date} · текущий месяц + следующие 30 дней · только факты Resort Core</p>
        </div>
        <div className="owner-executive-actions"><button className="btn" onClick={() => window.print()}>Печать / PDF</button><button className="btn" onClick={load}>Обновить</button></div>
      </div>

      {error && <div className="error-box">{error}</div>}

      <div className="owner-executive-grid">
        <article><span>Загрузка · месяц</span><strong>{pct(current.kpi.occupancy_percent)}</strong><small>{delta(current.kpi.occupancy_percent, previous.kpi.occupancy_percent, "pct")} к прошлому месяцу</small></article>
        <article><span>ADR · месяц</span><strong>{money(current.kpi.adr_kgs)}</strong><small>{delta(current.kpi.adr_kgs, previous.kpi.adr_kgs, "money")} к прошлому</small></article>
        <article><span>RevPAR · месяц</span><strong>{money(current.kpi.revpar_kgs)}</strong><small>{delta(current.kpi.revpar_kgs, previous.kpi.revpar_kgs, "money")} к прошлому</small></article>
        <article><span>Получено оплат · месяц</span><strong>{money(current.kpi.received_payments_kgs)}</strong><small>{delta(current.kpi.received_payments_kgs, previous.kpi.received_payments_kgs, "money")}</small></article>
        <article><span>CRM-конверсия</span><strong>{pct(current.crm.conversion_percent)}</strong><small>{current.crm.converted} из {current.crm.leads} лидов</small></article>
        <article className={current.kpi.active_outstanding_kgs > 0 ? "executive-attention" : ""}><span>Дебиторка сейчас</span><strong>{money(current.kpi.active_outstanding_kgs)}</strong><small>{current.kpi.active_debtor_count || 0} активных броней</small></article>
        <article><span>Загрузка · 30 дней вперёд</span><strong>{pct(forward.occupancy_on_books_percent)}</strong><small>{forward.booked_room_nights} / {forward.available_room_nights} номеро-ночей</small></article>
        <article><span>Стоимость on-books · 30 дней</span><strong>{money(forward.allocated_booked_value_kgs)}</strong><small>{forward.arrivals} заездов · {forward.departures} выездов</small></article>
        <article><span>Booking pickup</span><strong>{pickupReady ? delta(pickup.summary!.room_night_pickup, 0, "number") : "—"}</strong><small>{pickupReady ? `${delta(pickup.summary!.booked_value_pickup_kgs, 0, "money")} с ${pickup.baseline?.snapshot_date}` : `статус: ${pickup?.status || brief.pickup_readiness.status}`}</small></article>
        <article><span>NPS</span><strong>{growth.feedback.nps == null ? "—" : growth.feedback.nps}</strong><small>выборка {growth.feedback.nps_sample_size} · средняя {growth.feedback.average_score == null ? "—" : growth.feedback.average_score.toFixed(2)}</small></article>
        <article className={growth.feedback.recovery_open > 0 ? "executive-attention" : ""}><span>Recovery</span><strong>{growth.feedback.recovery_open}</strong><small>{growth.feedback.detractors} detractors всего</small></article>
        <article><span>Возврат гостей</span><strong>{growth.candidates.reactivation}</strong><small>{growth.queue.return_open} уже в работе</small></article>
      </div>

      <div className="owner-executive-bottom">
        <article className="owner-executive-actions-panel">
          <div><p className="eyebrow">ACTION FACTS</p><h3>Требует решения</h3></div>
          <div className="executive-action-counts"><span><b>{actionFacts.critical}</b> critical</span><span><b>{actionFacts.high}</b> high</span><span><b>{growth.queue.overdue}</b> growth overdue</span></div>
          {actionFacts.items.length === 0 ? <p className="executive-muted">Активных Owner Control action facts нет.</p> : <div className="executive-action-list">{actionFacts.items.map((item) => <div key={item.code}><span className={`exec-severity e-${item.severity}`}>{item.severity}</span><strong>{item.label}</strong><b>{item.count}</b></div>)}</div>}
        </article>
        <article className="owner-executive-truth">
          <p className="eyebrow">TRUTH BOUNDARY</p>
          <h3>Что означают цифры</h3>
          <p>Месячные ADR/RevPAR/стоимость броней — управленческие метрики Resort Core, не бухгалтерская выручка.</p>
          <p>30 дней вперёд — текущие on-books брони и доступность, не статистический прогноз спроса.</p>
          <p>Pickup показывается только при наличии сохранённого исторического snapshot; иначе остаётся «—».</p>
          <p>NPS считается только по фактически записанным оценкам и всегда показывает размер выборки.</p>
        </article>
      </div>
    </section>
  );
}
