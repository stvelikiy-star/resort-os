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
type SnapshotMeal = {
  service_date: string;
  meal_type: "BREAKFAST" | "LUNCH" | "DINNER";
  current_adult_portions: number;
  current_child_portions: number;
  current_total_portions: number;
  current_entitlement_count: number;
  state: "OPEN" | "FROZEN";
  cutoff_status: "UNCONFIGURED" | "BEFORE_CUTOFF" | "CUTOFF_REACHED";
  meal_start?: string | null;
  cutoff_at?: string | null;
  cutoff_minutes: number;
  captured_at?: string | null;
  captured_by_name?: string | null;
  forced: boolean;
  reason?: string | null;
  frozen_adult_portions?: number | null;
  frozen_child_portions?: number | null;
  frozen_total_portions?: number | null;
  frozen_entitlement_count?: number | null;
  delta_adult_portions?: number | null;
  delta_child_portions?: number | null;
  delta_total_portions?: number | null;
  delta_entitlement_count?: number | null;
  changed_since_snapshot: boolean;
};
type SnapshotResponse = { from_date: string; through_date: string; days: Array<{ service_date: string; meals: SnapshotMeal[] }> };

type Props = { userRole: string };

const mealLabel = { BREAKFAST: "Завтрак", LUNCH: "Обед", DINNER: "Ужин" } as const;

function localIso(offset = 0) {
  const value = new Date();
  value.setDate(value.getDate() + offset);
  const shifted = new Date(value.getTime() - value.getTimezoneOffset() * 60000);
  return shifted.toISOString().slice(0, 10);
}

async function api(path: string, init?: RequestInit) {
  const response = await fetch(path, { cache: "no-store", ...init });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(typeof body?.detail === "string" ? body.detail : body?.detail?.code || "Ошибка Resort Core");
  return body;
}

function formatClock(value?: string | null) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
}

function signed(value?: number | null) {
  const number = Number(value || 0);
  return number > 0 ? `+${number}` : String(number);
}

export default function ChefProduction({ userRole }: Props) {
  const [fromDate, setFromDate] = useState(localIso());
  const [throughDate, setThroughDate] = useState(localIso(6));
  const [data, setData] = useState<Production | null>(null);
  const [snapshots, setSnapshots] = useState<SnapshotResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [busySnapshot, setBusySnapshot] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [productionBody, snapshotBody] = await Promise.all([
        api(`/core/api/v1/dining/production?from_date=${encodeURIComponent(fromDate)}&through_date=${encodeURIComponent(throughDate)}`),
        api(`/core/api/v1/dining/production-snapshots?from_date=${encodeURIComponent(fromDate)}&through_date=${encodeURIComponent(throughDate)}`),
      ]);
      setData(productionBody as Production);
      setSnapshots(snapshotBody as SnapshotResponse);
    } catch (cause) {
      setData(null);
      setSnapshots(null);
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

  const snapshotByKey = useMemo(() => {
    const map = new Map<string, SnapshotMeal>();
    for (const day of snapshots?.days ?? []) {
      for (const meal of day.meals) map.set(`${day.service_date}:${meal.meal_type}`, meal);
    }
    return map;
  }, [snapshots]);

  const today = localIso();
  const todayDay = data?.days.find((day) => day.service_date === today);
  const todayTotal = useMemo(() => todayDay?.meals.reduce((sum, meal) => sum + meal.total_portions, 0) ?? 0, [todayDay]);
  const departures = useMemo(() => todayDay?.meals.flatMap((meal) => meal.guests.filter((guest) => guest.departure_day).map((guest) => ({ ...guest, meal_type: meal.meal_type }))) ?? [], [todayDay]);
  const isManager = userRole === "OWNER" || userRole === "MANAGER";

  async function freeze(meal: Meal, snapshot: SnapshotMeal, force: boolean) {
    const key = `${meal.service_date}:${meal.meal_type}`;
    if (force) {
      const reason = snapshot.cutoff_status === "UNCONFIGURED"
        ? "Время этого приёма пищи ещё не настроено. Зафиксировать производственный план вручную?"
        : "До штатного cutoff ещё есть время. Зафиксировать производственный план досрочно?";
      if (!window.confirm(reason)) return;
    }
    setBusySnapshot(key);
    setError(null);
    setNotice(null);
    try {
      const body = await api("/core/api/v1/dining/production-snapshots", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          service_date: meal.service_date,
          meal_type: meal.meal_type,
          force_before_cutoff: force,
          notes: force ? "Manual Chef OS production baseline" : null,
        }),
      });
      setNotice(`${mealLabel[meal.meal_type]} ${meal.service_date}: зафиксировано ${body.frozen_total_portions ?? 0} порций. Поздние изменения теперь показываются отдельно.`);
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось зафиксировать план кухни");
    } finally {
      setBusySnapshot(null);
    }
  }

  return <section className={styles.shell}>
    <header className={styles.head}>
      <div><p>Chef OS · план производства</p><h2>Сколько готовим</h2><span>Текущий план идёт из Resort Core. После cutoff кухня фиксирует базовое количество, а все поздние изменения отображаются отдельной дельтой.</span></div>
      <div className={styles.controls}><label>С<input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} /></label><label>По<input type="date" value={throughDate} onChange={(e) => setThroughDate(e.target.value)} /></label><button onClick={() => void load()} disabled={loading}>↻ Обновить</button></div>
    </header>

    {error && <div className={styles.error}>{error}</div>}
    {notice && <div className={styles.notice}>{notice}</div>}

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
        const snapshot = snapshotByKey.get(key);
        const changed = snapshot?.state === "FROZEN" && snapshot.changed_since_snapshot;
        const canNormalFreeze = snapshot?.state === "OPEN" && snapshot.cutoff_status === "CUTOFF_REACHED";
        const canForce = snapshot?.state === "OPEN" && snapshot.cutoff_status !== "CUTOFF_REACHED" && isManager;
        return <section key={key} className={meal.total_portions ? styles.mealActive : styles.mealEmpty}>
          <button className={styles.mealButton} onClick={() => setExpanded(expanded === key ? null : key)}>
            <span><small>{mealLabel[meal.meal_type]}</small><strong>{meal.total_portions}</strong></span>
            <span><b>{meal.adult_portions}</b> взр. · <b>{meal.child_portions}</b> дет.</span>
            <i>{expanded === key ? "−" : "+"}</i>
          </button>
          {snapshot && <div className={styles.snapshotBar} data-state={snapshot.state} data-changed={changed ? "true" : "false"}>
            {snapshot.state === "FROZEN" ? <>
              <span><b>Зафиксировано: {snapshot.frozen_total_portions ?? 0}</b> · {snapshot.frozen_adult_portions ?? 0} взр. + {snapshot.frozen_child_portions ?? 0} дет.</span>
              <span className={changed ? styles.deltaHot : styles.deltaOk}>{changed ? `Позднее изменение: ${signed(snapshot.delta_total_portions)} порц.` : "Изменений после фиксации нет"}</span>
              <small>{snapshot.captured_at ? `Фиксация ${new Date(snapshot.captured_at).toLocaleString("ru-RU")}` : ""}{snapshot.captured_by_name ? ` · ${snapshot.captured_by_name}` : ""}{snapshot.forced ? " · вручную" : ""}</small>
            </> : <>
              <span>{snapshot.cutoff_status === "UNCONFIGURED" ? "Время приёма пищи не настроено — автоматический cutoff недоступен." : snapshot.cutoff_status === "BEFORE_CUTOFF" ? `План открыт до ${formatClock(snapshot.cutoff_at) || "cutoff"}.` : "Cutoff достигнут — план можно зафиксировать."}</span>
              {canNormalFreeze && <button disabled={busySnapshot === key} onClick={() => void freeze(meal, snapshot, false)}>{busySnapshot === key ? "Фиксирую…" : "Зафиксировать план"}</button>}
              {canForce && <button className={styles.force} disabled={busySnapshot === key} onClick={() => void freeze(meal, snapshot, true)}>{snapshot.cutoff_status === "UNCONFIGURED" ? "Зафиксировать вручную" : "Зафиксировать досрочно"}</button>}
            </>}
          </div>}
          {expanded === key && <div className={styles.lines}>{meal.guests.length === 0 ? <p>Порций нет.</p> : meal.guests.map((guest) => <div key={guest.entitlement_id} className={guest.departure_day ? styles.departure : ""}>
            <div><strong>№ {guest.room_code || "—"} · {guest.guest_name}</strong><small>{guest.booking_number}{guest.departure_day ? " · ВЫЕЗД" : ""}</small></div>
            <b>{guest.adult_portions}+{guest.child_portions}</b>
            {guest.notes && <span>{guest.notes}</span>}
          </div>)}</div>}
        </section>;
      })}</div>
    </article>)}</div>}

    <footer className={styles.foot}>Зафиксированный план — производственная отметка кухни, а не платёж и не начисление. Если менеджер меняет питание после фиксации, базовое число сохраняется, а Chef OS показывает разницу отдельно.</footer>
  </section>;
}
