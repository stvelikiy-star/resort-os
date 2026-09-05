"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import styles from "./DiningDayPlanner.module.css";

type User = { id: string; display_name: string; role: string };
type MenuItem = { id: string; code: string; category: string; name_ru: string; price_kgs: number; is_active: boolean; is_draft: boolean };
type DayItem = {
  availability_id: string;
  menu_item_id: string;
  meal_type: string;
  code: string;
  category: string;
  name_ru: string;
  price_kgs: number;
  is_active: boolean;
  is_draft: boolean;
  is_available: boolean;
  sold_out: boolean;
  notes?: string | null;
};

type Meal = "BREAKFAST" | "LUNCH" | "DINNER" | "OTHER";

const mealLabel: Record<Meal, string> = {
  BREAKFAST: "Завтрак",
  LUNCH: "Обед",
  DINNER: "Ужин",
  OTHER: "Весь день / другое",
};

const categoryLabel: Record<string, string> = {
  BREAKFAST: "Завтрак",
  SOUP: "Супы",
  SALAD: "Салаты",
  MAIN: "Основное",
  SIDE: "Гарниры",
  DESSERT: "Десерты",
  DRINK: "Напитки",
};

function todayIso() {
  const now = new Date();
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
}

async function api(path: string, init?: RequestInit) {
  const response = await fetch(path, { cache: "no-store", ...init });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(typeof body?.detail === "string" ? body.detail : body?.detail?.code || "Ошибка Resort Core");
  return body;
}

export default function DiningDayPlanner() {
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(true);
  const [date, setDate] = useState(todayIso());
  const [meal, setMeal] = useState<Meal>("BREAKFAST");
  const [menu, setMenu] = useState<MenuItem[]>([]);
  const [dayItems, setDayItems] = useState<DayItem[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    api("/core/api/v1/auth/me")
      .then((body) => {
        if (!["OWNER", "MANAGER", "DINING_STAFF"].includes(body.role)) throw new Error("Нет доступа к меню кухни");
        setUser(body);
      })
      .catch(() => setUser(null))
      .finally(() => setChecking(false));
  }, []);

  const load = useCallback(async () => {
    if (!user) return;
    setError(null);
    try {
      const [menuBody, dayBody] = await Promise.all([
        api("/core/api/v1/kitchen/menu"),
        api(`/core/api/v1/dining/menu-day?service_date=${encodeURIComponent(date)}&meal_type=${meal}`),
      ]);
      const menuItems = (menuBody.items ?? []) as MenuItem[];
      const serviceItems = (dayBody.items ?? []) as DayItem[];
      setMenu(menuItems);
      setDayItems(serviceItems);
      setSelected(new Set(serviceItems.filter((item) => item.is_available).map((item) => item.menu_item_id)));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось загрузить меню");
    }
  }, [date, meal, user]);

  useEffect(() => { void load(); }, [load]);

  const approved = useMemo(() => menu.filter((item) => item.is_active && !item.is_draft), [menu]);
  const drafts = useMemo(() => menu.filter((item) => item.is_draft), [menu]);

  function toggle(id: string) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  async function publish() {
    if (!selected.size) {
      setError("Выберите хотя бы одно подтверждённое блюдо для публикации.");
      return;
    }
    setBusy("publish");
    setError(null);
    setNotice(null);
    try {
      const body = await api("/core/api/v1/dining/menu-day/publish", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ service_date: date, meal_type: meal, menu_item_ids: Array.from(selected) }),
      });
      setNotice(`${mealLabel[meal]} · ${date}: опубликовано ${body.published_items} позиций.`);
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось опубликовать меню");
    } finally {
      setBusy(null);
    }
  }

  async function patch(item: DayItem, patchBody: Record<string, unknown>) {
    setBusy(item.availability_id);
    setError(null);
    try {
      await api(`/core/api/v1/dining/menu-day/${item.availability_id}`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(patchBody),
      });
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось изменить доступность");
    } finally {
      setBusy(null);
    }
  }

  if (checking) return <main className={styles.center}>Проверяю доступ…</main>;
  if (!user) return <main className={styles.center}><div><h1>Нужен вход кухни</h1><p>Сначала войдите рабочей учётной записью.</p><a href="/kitchen">Открыть вход кухни</a></div></main>;

  return <main className={styles.shell}>
    <header className={styles.header}>
      <div><p>Три Короны · Dining Control</p><h1>Меню на сегодня</h1><span>{user.display_name} · меню гостя публикуется только после явного подтверждения.</span></div>
      <nav><a href="/kitchen">Кухня</a><a href="/waiter">Официант / зал</a></nav>
    </header>

    <section className={styles.controls}>
      <label>Дата<input type="date" value={date} onChange={(event) => setDate(event.target.value)} /></label>
      <label>Приём пищи<select value={meal} onChange={(event) => setMeal(event.target.value as Meal)}>{Object.entries(mealLabel).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
      <button type="button" onClick={() => setSelected(new Set(approved.map((item) => item.id)))}>Выбрать все подтверждённые</button>
      <button type="button" onClick={() => setSelected(new Set())}>Снять выбор</button>
      <button className={styles.primary} type="button" disabled={busy === "publish" || !selected.size} onClick={() => void publish()}>{busy === "publish" ? "Публикую…" : `Опубликовать: ${selected.size}`}</button>
    </section>

    {error && <div className={styles.error}>{error}</div>}
    {notice && <div className={styles.notice}>{notice}</div>}

    <section className={styles.grid}>
      <div className={styles.panel}>
        <div className={styles.panelHead}><div><small>Каталог кухни</small><h2>Что включить в {mealLabel[meal].toLowerCase()}</h2></div><span>{approved.length} подтверждено · {drafts.length} черновиков</span></div>
        {!approved.length ? <p className={styles.empty}>Нет активных подтверждённых блюд. Сначала утвердите меню в Kitchen Admin.</p> : <div className={styles.catalog}>{approved.map((item) => <label key={item.id} className={selected.has(item.id) ? styles.selected : ""}><input type="checkbox" checked={selected.has(item.id)} onChange={() => toggle(item.id)} /><span><small>{categoryLabel[item.category] ?? item.category}</small><strong>{item.name_ru}</strong><b>{item.price_kgs.toLocaleString("ru-RU")} KGS</b></span></label>)}</div>}
      </div>

      <div className={styles.panel}>
        <div className={styles.panelHead}><div><small>Опубликовано гостю</small><h2>{mealLabel[meal]} · {date}</h2></div><span>{dayItems.filter((item) => item.is_available && !item.sold_out).length} доступно</span></div>
        {!dayItems.length ? <p className={styles.empty}>Этот приём пищи ещё не опубликован. Гость не увидит неподтверждённое меню.</p> : <div className={styles.liveList}>{dayItems.map((item) => <article key={item.availability_id} className={!item.is_available || item.sold_out ? styles.disabled : ""}><div><small>{categoryLabel[item.category] ?? item.category}</small><strong>{item.name_ru}</strong><span>{item.price_kgs.toLocaleString("ru-RU")} KGS</span></div><button disabled={busy === item.availability_id} onClick={() => void patch(item, { sold_out: !item.sold_out })}>{item.sold_out ? "Вернуть в продажу" : "Стоп-лист"}</button><button disabled={busy === item.availability_id} onClick={() => void patch(item, { is_available: !item.is_available })}>{item.is_available ? "Скрыть" : "Показать"}</button></article>)}</div>}
      </div>
    </section>
  </main>;
}
