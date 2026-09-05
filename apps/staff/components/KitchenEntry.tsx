"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import KitchenAdmin from "./KitchenAdmin";
import styles from "./KitchenEntry.module.css";

type User = { id: string; username: string; display_name: string; role: string; property_code: string };
type MenuItem = { id: string; name_ru: string; category: string; price_kgs: number; is_active: boolean; is_draft: boolean };
type TableItem = { id: string; status: string; is_active: boolean };
type OrderItem = { id: string; status: string };
type ArrivalItem = { id: string; status: string };

type KitchenPulse = {
  menu: MenuItem[];
  tables: TableItem[];
  orders: OrderItem[];
  arrivals: ArrivalItem[];
};

const KITCHEN_ROLES = new Set(["OWNER", "MANAGER", "DINING_STAFF"]);

async function json(path: string, init?: RequestInit) {
  const response = await fetch(path, { cache: "no-store", ...init });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(typeof body?.detail === "string" ? body.detail : "Ошибка Resort Core");
  return body;
}

export default function KitchenEntry() {
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(true);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [pulse, setPulse] = useState<KitchenPulse | null>(null);
  const [pulseError, setPulseError] = useState<string | null>(null);

  const loadPulse = useCallback(async () => {
    try {
      const [menuBody, tablesBody, ordersBody, arrivalsBody] = await Promise.all([
        json("/core/api/v1/kitchen/menu"),
        json("/core/api/v1/kitchen/tables"),
        json("/core/api/v1/kitchen/orders?status=ACTIVE"),
        json("/core/api/v1/ops/kitchen/arrivals"),
      ]);
      setPulse({
        menu: menuBody.items ?? [],
        tables: tablesBody.items ?? [],
        orders: ordersBody.items ?? [],
        arrivals: arrivalsBody.items ?? [],
      });
      setPulseError(null);
    } catch (e) {
      setPulse(null);
      setPulseError(e instanceof Error ? e.message : "Не удалось загрузить сводку кухни");
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const me = await json("/core/api/v1/auth/me") as User;
        if (!KITCHEN_ROLES.has(me.role)) throw new Error("Эта учётная запись не имеет доступа к кухне.");
        if (!cancelled) setUser(me);
      } catch {
        if (!cancelled) setUser(null);
      } finally {
        if (!cancelled) setChecking(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!user) return;
    void loadPulse();
    const timer = window.setInterval(() => void loadPulse(), 15000);
    return () => window.clearInterval(timer);
  }, [user, loadPulse]);

  async function login(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const body = await json("/core/api/v1/auth/login", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ username, password }),
      }) as User;
      if (!KITCHEN_ROLES.has(body.role)) {
        await fetch("/core/api/v1/auth/logout", { method: "POST" }).catch(() => undefined);
        throw new Error("Для этого входа нужна роль DINING_STAFF, MANAGER или OWNER.");
      }
      setUser(body);
      setPassword("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось войти");
    } finally {
      setSubmitting(false);
    }
  }

  async function logout() {
    await fetch("/core/api/v1/auth/logout", { method: "POST" }).catch(() => undefined);
    setUser(null);
    setPulse(null);
    setPassword("");
  }

  const facts = useMemo(() => {
    const menu = pulse?.menu ?? [];
    const tables = pulse?.tables.filter((item) => item.is_active) ?? [];
    const orders = pulse?.orders ?? [];
    const published = menu.filter((item) => item.is_active && !item.is_draft);
    const drafts = menu.filter((item) => item.is_draft);
    return {
      published: published.length,
      drafts: drafts.length,
      activeOrders: orders.length,
      readyOrders: orders.filter((item) => item.status === "READY").length,
      occupiedTables: tables.filter((item) => item.status === "OCCUPIED").length,
      availableTables: tables.filter((item) => item.status === "AVAILABLE").length,
      arrivals: pulse?.arrivals.length ?? 0,
    };
  }, [pulse]);

  if (checking) return <main className={styles.loginPage}><div className={styles.loginCard}><p>Три Короны · Resort OS</p><h1>Открываю кухню…</h1><span>Проверяю рабочую сессию.</span></div></main>;

  if (!user) {
    return <main className={styles.loginPage}>
      <form className={styles.loginCard} onSubmit={login}>
        <div className={styles.mark}>III</div>
        <p>Три Короны · отдельный вход</p>
        <h1>Кухня и зал</h1>
        <span>Заказы, столы, меню для гостя и новые заезды — в одном рабочем окне.</span>
        <label>Логин<input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" required autoFocus /></label>
        <label>Пароль<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" minLength={8} required /></label>
        {error && <div className={styles.error}>{error}</div>}
        <button className={styles.primary} disabled={submitting}>{submitting ? "Входим…" : "Войти в кухню"}</button>
        <a href="/">Открыть общий вход «Моя смена»</a>
      </form>
    </main>;
  }

  return <>
    <section className={styles.pulse}>
      <div className={styles.pulseHead}>
        <div><p>Кухня · сегодня</p><h2>Рабочая сводка</h2><span>{user.display_name} · {user.role}</span></div>
        <div className={styles.pulseActions}><button onClick={() => void loadPulse()}>Обновить</button><button onClick={() => void logout()}>Выйти</button></div>
      </div>
      {pulseError && <div className={styles.error}>{pulseError}</div>}
      <div className={styles.metrics}>
        <article><strong>{facts.activeOrders}</strong><span>активных заказов</span><small>{facts.readyOrders} готовы к выдаче</small></article>
        <article><strong>{facts.occupiedTables}</strong><span>занятых столов</span><small>{facts.availableTables} свободно</small></article>
        <article><strong>{facts.published}</strong><span>блюд готовы для гостя</span><small>активно · не черновик</small></article>
        <article className={facts.drafts ? styles.attention : ""}><strong>{facts.drafts}</strong><span>черновиков меню</span><small>нужно проверить перед публикацией</small></article>
        <article><strong>{facts.arrivals}</strong><span>карточек заезда</span><small>для команды питания</small></article>
      </div>
      <div className={styles.guide}>
        <b>Логика работы:</b><span>Официант/питание создаёт заказ и привязывает его к столу → кухня ведёт NEW → ACCEPTED → COOKING → READY → SERVED → после выдачи стол освобождается. Меню гостя должно содержать только подтверждённые активные позиции.</span>
      </div>
    </section>
    <KitchenAdmin />
  </>;
}
