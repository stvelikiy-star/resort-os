"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import styles from "./DiningManagementBoard.module.css";

type StayItem = {
  stay_id: string;
  stay_status: string;
  reservation_id: string;
  reservation_status: string;
  booking_number: string;
  check_in: string;
  check_out: string;
  adults: number;
  children: number;
  guest_name: string;
  phone?: string | null;
  room_code?: string | null;
  entitlement_count: number;
};
type Entitlement = { id: string; service_date: string; meal_type: string; adult_portions: number; child_portions: number; status: string; notes?: string | null };
type ProductionMeal = { meal_type: string; adult_portions: number; child_portions: number; total_portions: number };
type ProductionDay = { service_date: string; meals: ProductionMeal[] };

const mealLabels: Record<string, string> = { BREAKFAST: "Завтрак", LUNCH: "Обед", DINNER: "Ужин" };

async function api(path: string, init?: RequestInit) {
  const response = await fetch(path, { cache: "no-store", ...init });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(typeof body?.detail === "string" ? body.detail : body?.detail?.code || "Ошибка Resort Core");
  return body;
}

function todayIso() {
  const now = new Date();
  const shifted = new Date(now.getTime() - now.getTimezoneOffset() * 60000);
  return shifted.toISOString().slice(0, 10);
}

export default function DiningManagementBoard() {
  const [stays, setStays] = useState<StayItem[]>([]);
  const [selectedStayId, setSelectedStayId] = useState("");
  const [entitlements, setEntitlements] = useState<Entitlement[]>([]);
  const [production, setProduction] = useState<ProductionDay[]>([]);
  const [query, setQuery] = useState("");
  const [fromDate, setFromDate] = useState(todayIso());
  const [throughDate, setThroughDate] = useState(todayIso());
  const [meals, setMeals] = useState<string[]>(["BREAKFAST"]);
  const [adults, setAdults] = useState(1);
  const [children, setChildren] = useState(0);
  const [replaceRange, setReplaceRange] = useState(false);
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [staysBody, productionBody] = await Promise.all([
        api("/core/api/v1/dining/stays?include_future_days=30"),
        api(`/core/api/v1/dining/production?from_date=${todayIso()}&through_date=${todayIso()}`),
      ]);
      const nextStays = (staysBody.items ?? []) as StayItem[];
      setStays(nextStays);
      setSelectedStayId((current) => current || nextStays[0]?.stay_id || "");
      setProduction(productionBody.days ?? []);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось загрузить питание");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const selected = useMemo(() => stays.find((item) => item.stay_id === selectedStayId) ?? null, [stays, selectedStayId]);
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return stays;
    return stays.filter((item) => [item.guest_name, item.phone, item.room_code, item.booking_number].some((value) => String(value || "").toLowerCase().includes(q)));
  }, [stays, query]);

  useEffect(() => {
    if (!selected) { setEntitlements([]); return; }
    setFromDate(selected.check_in);
    setThroughDate(selected.check_out);
    setAdults(selected.adults);
    setChildren(selected.children);
    api(`/core/api/v1/dining/stays/${selected.stay_id}/entitlements`)
      .then((body) => setEntitlements(body.items ?? []))
      .catch((cause) => setError(cause instanceof Error ? cause.message : "Не удалось загрузить календарь питания"));
  }, [selected]);

  function toggleMeal(meal: string) {
    setMeals((current) => current.includes(meal) ? current.filter((value) => value !== meal) : [...current, meal]);
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!selected || meals.length === 0) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const body = await api(`/core/api/v1/dining/stays/${selected.stay_id}/meal-plan`, {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          from_date: fromDate,
          through_date: throughDate,
          meals,
          adult_portions: adults,
          child_portions: children,
          notes: notes.trim() || null,
          replace_range: replaceRange,
        }),
      });
      setNotice(`Питание сохранено: ${body.updated_items} записей. Финансы проживания не изменены.`);
      const detail = await api(`/core/api/v1/dining/stays/${selected.stay_id}/entitlements`);
      setEntitlements(detail.items ?? []);
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось сохранить питание");
    } finally {
      setBusy(false);
    }
  }

  const todayMeals = production[0]?.meals ?? [];

  return <main className={styles.shell}>
    <header className={styles.head}>
      <div><p>Resort Core · Dining</p><h1>Питание / ресторан</h1><span>План питания проживающих, кухня и зал работают из одного источника данных. Включённое питание не создаёт платёж.</span></div>
      <button onClick={() => void load()} disabled={loading}>↻ Обновить</button>
    </header>

    <div className={styles.kpis}>{["BREAKFAST", "LUNCH", "DINNER"].map((meal) => {
      const row = todayMeals.find((item) => item.meal_type === meal);
      return <article key={meal}><span>{mealLabels[meal]}</span><strong>{loading ? "…" : row?.total_portions ?? 0}</strong><small>{row?.adult_portions ?? 0} взрослых · {row?.child_portions ?? 0} детских</small></article>;
    })}<article><span>Гости с питанием</span><strong>{loading ? "…" : stays.filter((item) => item.entitlement_count > 0).length}</strong><small>активные / ближайшие</small></article></div>

    {error && <div className={styles.error}>{error}</div>}
    {notice && <div className={styles.notice}>{notice}</div>}

    <div className={styles.grid}>
      <section className={styles.card}>
        <div className={styles.cardHead}><div><small>Гости</small><h2>Кому назначить питание</h2></div><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Гость / номер / телефон" /></div>
        <div className={styles.stays}>{filtered.map((item) => <button key={item.stay_id} className={selectedStayId === item.stay_id ? styles.activeStay : ""} onClick={() => setSelectedStayId(item.stay_id)}>
          <div><strong>№ {item.room_code || "—"} · {item.guest_name}</strong><small>{item.booking_number} · {item.check_in} → {item.check_out}</small></div>
          <span>{item.adults}+{item.children}</span><b>{item.entitlement_count ? `${item.entitlement_count} приёмов` : "Не задано"}</b>
        </button>)}</div>
      </section>

      <section className={styles.card}>
        <div className={styles.cardHead}><div><small>Meal plan</small><h2>{selected ? `№ ${selected.room_code || "—"} · ${selected.guest_name}` : "Выберите гостя"}</h2></div></div>
        {selected && <form className={styles.form} onSubmit={save}>
          <div className={styles.dates}><label>С<input type="date" min={selected.check_in} max={selected.check_out} value={fromDate} onChange={(e) => setFromDate(e.target.value)} /></label><label>По<input type="date" min={selected.check_in} max={selected.check_out} value={throughDate} onChange={(e) => setThroughDate(e.target.value)} /></label></div>
          <div className={styles.mealChecks}>{["BREAKFAST", "LUNCH", "DINNER"].map((meal) => <label key={meal}><input type="checkbox" checked={meals.includes(meal)} onChange={() => toggleMeal(meal)} /><span>{mealLabels[meal]}</span></label>)}</div>
          <div className={styles.dates}><label>Взрослых порций<input type="number" min="0" max="50" value={adults} onChange={(e) => setAdults(Math.max(0, Number(e.target.value) || 0))} /></label><label>Детских порций<input type="number" min="0" max="50" value={children} onChange={(e) => setChildren(Math.max(0, Number(e.target.value) || 0))} /></label></div>
          <label className={styles.notes}>Заметка<textarea value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Аллергия, детское питание, выезд после обеда…" /></label>
          <label className={styles.replace}><input type="checkbox" checked={replaceRange} onChange={(e) => setReplaceRange(e.target.checked)} /><span>Заменить существующий план в выбранном диапазоне</span></label>
          <button className={styles.primary} disabled={busy || meals.length === 0}>{busy ? "Сохраняю…" : "Сохранить питание"}</button>
        </form>}

        {selected && <div className={styles.calendar}><h3>Текущий календарь</h3>{entitlements.length === 0 ? <p>Питание пока не назначено.</p> : <div>{entitlements.map((item) => <span key={item.id} data-status={item.status}><b>{item.service_date}</b>{mealLabels[item.meal_type] || item.meal_type}<em>{item.adult_portions}+{item.child_portions}</em></span>)}</div>}</div>}
      </section>
    </div>
  </main>;
}
