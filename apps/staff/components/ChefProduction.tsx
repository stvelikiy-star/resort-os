"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import styles from "./ChefProduction.module.css";

type GuestLine = {
  entitlement_id: string;
  stay_id: string;
  reservation_id: string;
  booking_number: string;
  guest_name: string;
  room_code?: string | null;
  adult_portions: number;
  child_portions: number;
  check_in: string;
  check_out: string;
  departure_day: boolean;
  notes?: string | null;
};
type Meal = { service_date: string; meal_type: "BREAKFAST" | "LUNCH" | "DINNER"; adult_portions: number; child_portions: number; total_portions: number; guests: GuestLine[] };
type Day = { service_date: string; meals: Meal[] };
type Production = { from_date: string; through_date: string; days: Day[] };

const mealLabel = { BREAKFAST: "Завтрак", LUNCH: "Обед", DINNER: "Ужин" } as const;

function localIso(offset = 0) {
  const value = new Date();
  value.setDate(value.getDate() + offset);
  const shifted = new Date(value.getTime() - value.getTimezoneOffset() * 60000);
  return shifted.toISOString().slice(0, 10);
}

async function api(path: string) {
  const response = await fetch(path, { cache: "no-store" });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(typeof body?.detail === "string" ? body.detail : body?.detail?.code || "Ошибка Resort Core");
  return body;
}

export default function ChefProduction() {
  const [fromDate, setFromDate] = useState(localIso());
  const [throughDate, setThroughDate] = useState(localIso(6));
  const [data, setData] = useState<Production | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const body = await api(`/core/api/v1/dining/production?from_date=${encodeURIComponent(fromDate)}&through_date=${encodeURIComponent(throughDate)}`);
      setData(body as Production);
    } catch (cause) {
      setData(null);
      setError(cause instanceof Error ? cause.message : "Не удалось загрузить план питания");
    } finally {
      setLoading(false);
    }
  }, [fromDate, throughDate]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    const timer = window.setInterval(() => void load(), 30000);
    return () => window.clearInterval(timer);
  }, [load]);

  const today = localIso();
  const todayDay = data?.days.find((day) => day.service_date === today);
  const todayTotal = useMemo(() => todayDay?.meals.reduce((sum, meal) => sum + meal.total_portions, 0) ?? 0, [todayDay]);
  const departures = useMemo(() => todayDay?.meals.flatMap((meal) => meal.guests.filter((guest) => guest.departure_day).map((guest) => ({ ...guest, meal_type: meal.meal_type }))) ?? [], [todayDay]);

  return <section className={styles.shell}>
    <header className={styles.head}>
      <div><p>Chef OS · план производства</p><h2>Сколько готовим</h2><span>Только подтверждённые права питания из Resort Core. Взрослые и детские порции считаются отдельно.</span></div>
      <div className={styles.controls}><label>С<input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} /></label><label>По<input type="date" value={throughDate} onChange={(e) => setThroughDate(e.target.value)} /></label><button onClick={() => void load()} disabled={loading}>↻ Обновить</button></div>
    </header>

    {error && <div className={styles.error}>{error}</div>}

    <div className={styles.kpis}>
      <article><strong>{loading ? "…" : todayTotal}</strong><span>порций сегодня</span></article>
      <article><strong>{loading ? "…" : todayDay?.meals.find((m) => m.meal_type === "BREAKFAST")?.total_portions ?? 0}</strong><span>завтрак</span></article>
      <article><strong>{loading ? "…" : todayDay?.meals.find((m) => m.meal_type === "LUNCH")?.total_portions ?? 0}</strong><span>обед</span></article>
      <article><strong>{loading ? "…" : todayDay?.meals.find((m) => m.meal_type === "DINNER")?.total_portions ?? 0}</strong><span>ужин</span></article>
      <article className={departures.length ? styles.attention : ""}><strong>{loading ? "…" : departures.length}</strong><span>выездных отметок сегодня</span></article>
    </div>

    {loading && !data ? <div className={styles.empty}>Загружаю производственный план…</div> : <div className={styles.days}>{data?.days.map((day) => <article className={styles.day} key={day.service_date}>
      <div className={styles.dayHead}><div><small>{day.service_date === today ? "СЕГОДНЯ" : "ДАТА"}</small><h3>{day.service_date}</h3></div><b>{day.meals.reduce((sum, meal) => sum + meal.total_portions, 0)} порц.</b></div>
      <div className={styles.meals}>{day.meals.map((meal) => {
        const key = `${day.service_date}:${meal.meal_type}`;
        return <section key={key} className={meal.total_portions ? styles.mealActive : styles.mealEmpty}>
          <button className={styles.mealButton} onClick={() => setExpanded(expanded === key ? null : key)}>
            <span><small>{mealLabel[meal.meal_type]}</small><strong>{meal.total_portions}</strong></span>
            <span><b>{meal.adult_portions}</b> взр. · <b>{meal.child_portions}</b> дет.</span>
            <i>{expanded === key ? "−" : "+"}</i>
          </button>
          {expanded === key && <div className={styles.lines}>{meal.guests.length === 0 ? <p>Порций нет.</p> : meal.guests.map((guest) => <div key={guest.entitlement_id} className={guest.departure_day ? styles.departure : ""}>
            <div><strong>№ {guest.room_code || "—"} · {guest.guest_name}</strong><small>{guest.booking_number}{guest.departure_day ? " · ВЫЕЗД" : ""}</small></div>
            <b>{guest.adult_portions}+{guest.child_portions}</b>
            {guest.notes && <span>{guest.notes}</span>}
          </div>)}</div>}
        </section>;
      })}</div>
    </article>)}</div>}

    <footer className={styles.foot}>Если питание гостя отсутствует здесь, кухня не должна считать его включённым автоматически — план назначается из управления/ресепшена.</footer>
  </section>;
}
