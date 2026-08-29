"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type ActionItem = { code: string; severity: "CRITICAL" | "HIGH" | "NORMAL"; count: number; label: string };
type ArrivalRisk = {
  reservation_id: string;
  booking_number: string;
  guest_name: string;
  phone?: string | null;
  check_in: string;
  room_code?: string | null;
  room_state?: string | null;
  outstanding_kgs: number;
};
type Period = {
  days: number;
  booked_room_nights: number;
  available_room_nights: number;
  occupancy_on_books_percent: number;
  allocated_booked_value_kgs: number;
  arrivals: number;
  departures: number;
};
type Brief = {
  property: { name: string; local_date: string; timezone: string };
  forward: {
    next_7_days: Period;
    next_30_days: Period;
    daily: Array<{
      date: string;
      available_rooms: number;
      booked_rooms: number;
      occupancy_on_books_percent: number;
      allocated_booked_value_kgs: number;
      arrivals: number;
      departures: number;
    }>;
  };
  actions: ActionItem[];
  details: {
    not_ready_arrivals_today: ArrivalRisk[];
    unassigned_arrivals_72h: ArrivalRisk[];
    debt_arrivals_72h: ArrivalRisk[];
  };
  guest_segments: {
    repeat_profiles: number;
    upcoming_repeat_arrivals_30d: number;
    completed_without_future: number;
    profiles_without_reservations: number;
  };
  pickup_readiness: { prior_snapshot_available: boolean; latest_prior_snapshot_date?: string | null; status: string };
  truth: Record<string, string>;
};

type Pickup = {
  status: "READY" | "INSUFFICIENT_HISTORY" | "INSUFFICIENT_COVERAGE";
  local_date: string;
  snapshot_count: number;
  baseline?: { snapshot_id: string; snapshot_date: string; age_days: number };
  summary?: {
    current_booked_room_nights: number;
    baseline_booked_room_nights: number;
    room_night_pickup: number;
    current_allocated_booked_value_kgs: number;
    baseline_allocated_booked_value_kgs: number;
    booked_value_pickup_kgs: number;
  };
  days: Array<{
    date: string;
    current_booked_rooms: number;
    baseline_booked_rooms: number;
    room_pickup: number;
    current_occupancy_percent: number;
    baseline_occupancy_percent: number;
    occupancy_pickup_points: number;
    current_allocated_value_kgs: number;
    baseline_allocated_value_kgs: number;
    booked_value_pickup_kgs: number;
  }>;
  truth: string;
};

const money = (value: number) => `${new Intl.NumberFormat("ru-RU").format(Math.round(value || 0))} сом`;
const pct = (value: number) => `${Number(value || 0).toFixed(1)}%`;

function addDaysIso(value: string, days: number) {
  const [year, month, day] = value.split("-").map(Number);
  const result = new Date(year, month - 1, day);
  result.setDate(result.getDate() + days);
  return `${result.getFullYear()}-${String(result.getMonth() + 1).padStart(2, "0")}-${String(result.getDate()).padStart(2, "0")}`;
}

function signed(value: number, moneyValue = false) {
  const prefix = value > 0 ? "+" : "";
  return moneyValue ? `${prefix}${money(value)}` : `${prefix}${new Intl.NumberFormat("ru-RU").format(value)}`;
}

export default function OwnerControlV2() {
  const [brief, setBrief] = useState<Brief | null>(null);
  const [pickup, setPickup] = useState<Pickup | null>(null);
  const [loading, setLoading] = useState(true);
  const [capturing, setCapturing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/core/api/v1/admin/intelligence/owner-brief?horizon_days=30", { cache: "no-store" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Не удалось загрузить Owner Control");
      const loaded = body as Brief;
      setBrief(loaded);

      const params = new URLSearchParams({
        from_date: loaded.property.local_date,
        to_date: addDaysIso(loaded.property.local_date, 29),
      });
      const pickupResponse = await fetch(`/core/api/v1/admin/intelligence/pickup?${params}`, { cache: "no-store" });
      const pickupBody = await pickupResponse.json().catch(() => ({}));
      if (!pickupResponse.ok) throw new Error(pickupBody.detail || "Не удалось рассчитать booking pickup");
      setPickup(pickupBody as Pickup);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка Owner Control");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function capture() {
    setCapturing(true);
    setError(null);
    try {
      const response = await fetch("/core/api/v1/admin/intelligence/snapshots/capture?horizon_days=180", { method: "POST" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Не удалось сохранить снимок");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка контрольного снимка");
    } finally {
      setCapturing(false);
    }
  }

  const activeActions = useMemo(() => brief?.actions.filter((item) => item.count > 0) || [], [brief]);

  if (loading && !brief) return <section className="owner-v2 owner-v2-loading">Формирую Owner Control V2…</section>;
  if (!brief) return <section className="owner-v2"><div className="error-box">{error || "Owner Control недоступен"}</div><button className="btn" onClick={load}>Повторить</button></section>;

  return (
    <section className="owner-v2">
      <div className="owner-v2-head">
        <div>
          <p className="eyebrow">OWNER CONTROL V2 · FORWARD VIEW</p>
          <h2>Что впереди и что требует решения</h2>
          <p>{brief.property.local_date} · подтверждённые данные Resort Core · без выдуманного прогноза спроса</p>
        </div>
        <div className="owner-v2-actions">
          <button className="btn" onClick={capture} disabled={capturing}>{capturing ? "Сохраняю…" : "Контрольный снимок"}</button>
          <button className="btn primary" onClick={load} disabled={loading}>{loading ? "Обновляю…" : "Обновить"}</button>
        </div>
      </div>

      {error && <div className="error-box">{error}</div>}

      <div className="owner-forward-kpis">
        <article><span>7 дней вперёд</span><strong>{pct(brief.forward.next_7_days.occupancy_on_books_percent)}</strong><small>{brief.forward.next_7_days.booked_room_nights} номеро-ночей уже в книге</small></article>
        <article><span>30 дней вперёд</span><strong>{pct(brief.forward.next_30_days.occupancy_on_books_percent)}</strong><small>{brief.forward.next_30_days.booked_room_nights} номеро-ночей</small></article>
        <article><span>On-books value · 30 дней</span><strong>{money(brief.forward.next_30_days.allocated_booked_value_kgs)}</strong><small>управленческое распределение по ночам</small></article>
        <article><span>Заезды · 30 дней</span><strong>{brief.forward.next_30_days.arrivals}</strong><small>текущие гарантированные / проживающие</small></article>
        <article><span>Повторные гости</span><strong>{brief.guest_segments.repeat_profiles}</strong><small>профилей с 2+ бронями</small></article>
        <article><span>Повторные заезды · 30 дней</span><strong>{brief.guest_segments.upcoming_repeat_arrivals_30d}</strong><small>фактическая история, без propensity score</small></article>
      </div>

      <div className="owner-v2-grid">
        <article className="owner-v2-panel owner-action-panel">
          <div className="owner-panel-title"><div><span>Action Center</span><h3>Контрольные риски</h3></div><strong>{activeActions.reduce((sum, item) => sum + item.count, 0)}</strong></div>
          {activeActions.length === 0 ? <p className="owner-empty">По текущим правилам критических/контрольных сигналов нет.</p> : (
            <div className="owner-action-list">{activeActions.map((item) => (
              <div key={item.code} className={`owner-action-row severity-${item.severity.toLowerCase()}`}>
                <i>{item.count}</i><div><strong>{item.label}</strong><small>{item.code}</small></div><span>{item.severity}</span>
              </div>
            ))}</div>
          )}
        </article>

        <article className="owner-v2-panel owner-pickup-panel">
          <div className="owner-panel-title"><div><span>Booking Pickup</span><h3>Изменение будущей книги</h3></div><b className={`pickup-status ${pickup?.status === "READY" ? "ready" : "waiting"}`}>{pickup?.status || "—"}</b></div>
          {pickup?.status === "READY" && pickup.summary ? <>
            <div className="pickup-kpis">
              <div><span>Pickup номеро-ночей</span><strong className={pickup.summary.room_night_pickup >= 0 ? "positive" : "negative"}>{signed(pickup.summary.room_night_pickup)}</strong></div>
              <div><span>Pickup booked value</span><strong className={pickup.summary.booked_value_pickup_kgs >= 0 ? "positive" : "negative"}>{signed(pickup.summary.booked_value_pickup_kgs, true)}</strong></div>
            </div>
            <p className="owner-note">База сравнения: {pickup.baseline?.snapshot_date} · {pickup.baseline?.age_days} дн. назад. Pickup включает новые брони и отмены.</p>
          </> : <>
            <div className="pickup-waiting"><strong>Нужна история снимков</strong><p>Сегодняшний снимок создаёт базовую точку. Реальный pickup появится после следующего hotel-local дня; система не подставляет фиктивные прошлые значения.</p></div>
          </>}
        </article>
      </div>

      <article className="owner-v2-panel owner-forward-chart-panel">
        <div className="owner-panel-title"><div><span>30 дней</span><h3>Загрузка на книге по дням</h3></div><small>on-books occupancy</small></div>
        <div className="owner-forward-chart">
          {brief.forward.daily.slice(0, 30).map((day) => (
            <div className="owner-forward-day" key={day.date} title={`${day.date}: ${day.occupancy_on_books_percent}% · ${day.booked_rooms}/${day.available_rooms} · ${money(day.allocated_booked_value_kgs)}`}>
              <div className="owner-forward-bar"><i style={{ height: `${Math.max(2, Math.min(100, day.occupancy_on_books_percent))}%` }} /></div>
              <strong>{Math.round(day.occupancy_on_books_percent)}</strong>
              <span>{day.date.slice(5)}</span>
              {(day.arrivals > 0 || day.departures > 0) && <small>+{day.arrivals}/−{day.departures}</small>}
            </div>
          ))}
        </div>
      </article>

      <div className="owner-v2-grid owner-risk-grid">
        <RiskList title="Неготовые заезды сегодня" items={brief.details.not_ready_arrivals_today} mode="room" />
        <RiskList title="Без номера · 72 часа" items={brief.details.unassigned_arrivals_72h} mode="room" />
        <RiskList title="Остаток оплаты · 72 часа" items={brief.details.debt_arrivals_72h} mode="debt" />
      </div>

      <div className="owner-segment-strip">
        <div><span>Завершили проживание, будущей брони нет</span><strong>{brief.guest_segments.completed_without_future}</strong></div>
        <div><span>Профили без Reservation</span><strong>{brief.guest_segments.profiles_without_reservations}</strong></div>
        <p>Это фактические сегменты CRM для дальнейшей работы менеджера. Система не присваивает скрытый VIP/«вероятность покупки» без доказательной модели.</p>
      </div>
    </section>
  );
}

function RiskList({ title, items, mode }: { title: string; items: ArrivalRisk[]; mode: "room" | "debt" }) {
  return <article className="owner-v2-panel risk-list-panel">
    <div className="owner-panel-title"><div><span>72H CONTROL</span><h3>{title}</h3></div><strong>{items.length}</strong></div>
    {items.length === 0 ? <p className="owner-empty">Нет.</p> : <div className="owner-risk-list">{items.slice(0, 8).map((item) => <div key={`${item.reservation_id}-${title}`}>
      <div><strong>{item.booking_number} · {item.guest_name}</strong><span>{item.check_in}{item.phone ? ` · ${item.phone}` : ""}</span></div>
      <b>{mode === "debt" ? money(item.outstanding_kgs) : (item.room_code ? `№ ${item.room_code} · ${item.room_state || "—"}` : "Номер не назначен")}</b>
    </div>)}</div>}
  </article>;
}
