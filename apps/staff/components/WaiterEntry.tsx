"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import DiningFloorPlan from "./DiningFloorPlan";
import styles from "./WaiterEntry.module.css";

type User = { id: string; username: string; display_name: string; role: string };
type TableItem = { id: string; code: string; name: string; seats: number; status: string; notes?: string | null };
type Reservation = { id: string; table_id: string; table_code: string; table_name: string; guest_name: string; phone?: string | null; party_size: number; starts_at: string; ends_at: string; status: string; notes?: string | null };
type Order = { id: string; order_number: string; status: string; source: string; table_id?: string | null; table_code?: string | null; table_name?: string | null; room_code?: string | null; guest_count: number; total_kgs: number; waiter_id?: string | null; waiter_name?: string | null; opened_at: string };
type MenuItem = { id: string; name_ru: string; category: string; price_kgs: number; is_active: boolean; is_draft: boolean };
type Floor = { service_date: string; current_user_id: string; tables: TableItem[]; reservations: Reservation[]; orders: Order[] };

const ALLOWED = new Set(["OWNER", "MANAGER", "DINING_STAFF"]);
const TABLE_LABEL: Record<string, string> = { AVAILABLE: "Свободен", RESERVED: "Бронь", OCCUPIED: "Занят", CLEANING: "Уборка", OUT_OF_SERVICE: "Закрыт" };
const ORDER_LABEL: Record<string, string> = { NEW: "Новый", ACCEPTED: "Принят", COOKING: "Готовится", READY: "Готов к выдаче", SERVED: "Выдан", CANCELLED: "Отменён" };
const RESERVATION_LABEL: Record<string, string> = { BOOKED: "Забронирован", SEATED: "Гости за столом", COMPLETED: "Завершён", CANCELLED: "Отменён", NO_SHOW: "Не пришли" };

async function api(path: string, init?: RequestInit) {
  const response = await fetch(path, { cache: "no-store", ...init });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(typeof body?.detail === "string" ? body.detail : body?.detail?.code || "Ошибка Resort Core");
  return body;
}

function localInput(hoursAhead = 0) {
  const value = new Date(Date.now() + hoursAhead * 3600_000);
  const shifted = new Date(value.getTime() - value.getTimezoneOffset() * 60000);
  return shifted.toISOString().slice(0, 16);
}

export default function WaiterEntry() {
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(true);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [floor, setFloor] = useState<Floor | null>(null);
  const [menu, setMenu] = useState<MenuItem[]>([]);
  const [busy, setBusy] = useState<string | null>(null);

  const [reservationTable, setReservationTable] = useState("");
  const [reservationGuest, setReservationGuest] = useState("");
  const [reservationPhone, setReservationPhone] = useState("");
  const [reservationParty, setReservationParty] = useState(2);
  const [reservationStart, setReservationStart] = useState(localInput(1));
  const [reservationEnd, setReservationEnd] = useState(localInput(3));

  const [orderTable, setOrderTable] = useState("");
  const [qty, setQty] = useState<Record<string, number>>({});
  const [orderNote, setOrderNote] = useState("");

  const load = useCallback(async () => {
    if (!user) return;
    try {
      const [floorBody, menuBody] = await Promise.all([
        api("/core/api/v1/dining/floor"),
        api("/core/api/v1/kitchen/menu"),
      ]);
      setFloor(floorBody);
      setMenu(menuBody.items ?? []);
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось загрузить зал");
    }
  }, [user]);

  useEffect(() => {
    api("/core/api/v1/auth/me")
      .then((body) => {
        if (!ALLOWED.has(body.role)) throw new Error("Нет доступа");
        setUser(body);
      })
      .catch(() => setUser(null))
      .finally(() => setChecking(false));
  }, []);

  useEffect(() => {
    if (!user) return;
    void load();
    const timer = window.setInterval(() => void load(), 10000);
    return () => window.clearInterval(timer);
  }, [user, load]);

  const approvedMenu = useMemo(() => menu.filter((item) => item.is_active && !item.is_draft), [menu]);
  const selectedItems = useMemo(() => approvedMenu.filter((item) => (qty[item.id] ?? 0) > 0), [approvedMenu, qty]);
  const draftTotal = useMemo(() => selectedItems.reduce((sum, item) => sum + item.price_kgs * (qty[item.id] ?? 0), 0), [selectedItems, qty]);
  const ready = floor?.orders.filter((order) => order.status === "READY") ?? [];
  const mine = floor?.orders.filter((order) => order.waiter_id === user?.id) ?? [];
  const unassigned = floor?.orders.filter((order) => !order.waiter_id) ?? [];

  async function login(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const body = await api("/core/api/v1/auth/login", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ username, password }),
      }) as User;
      if (!ALLOWED.has(body.role)) {
        await fetch("/core/api/v1/auth/logout", { method: "POST" }).catch(() => undefined);
        throw new Error("Для входа в зал нужна роль DINING_STAFF, MANAGER или OWNER.");
      }
      setUser(body);
      setPassword("");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось войти");
    } finally {
      setSubmitting(false);
    }
  }

  async function logout() {
    await fetch("/core/api/v1/auth/logout", { method: "POST" }).catch(() => undefined);
    setUser(null);
    setFloor(null);
  }

  async function tableStatus(table: TableItem, status: string) {
    setBusy(table.id);
    try {
      await api(`/core/api/v1/kitchen/tables/${table.id}`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ status }),
      });
      await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Ошибка стола"); }
    finally { setBusy(null); }
  }

  async function claim(order: Order) {
    if (!user) return;
    setBusy(order.id);
    try {
      await api(`/core/api/v1/dining/orders/${order.id}/waiter`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ waiter_id: user.id }),
      });
      await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Не удалось взять заказ"); }
    finally { setBusy(null); }
  }

  async function serve(order: Order) {
    setBusy(order.id);
    try {
      await api(`/core/api/v1/kitchen/orders/${order.id}/status`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ status: "SERVED" }),
      });
      await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Не удалось закрыть выдачу"); }
    finally { setBusy(null); }
  }

  async function reservationStatus(item: Reservation, status: string) {
    setBusy(item.id);
    try {
      await api(`/core/api/v1/dining/table-reservations/${item.id}`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ status }),
      });
      await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Не удалось изменить бронь стола"); }
    finally { setBusy(null); }
  }

  async function createReservation(event: FormEvent) {
    event.preventDefault();
    if (!reservationTable) return;
    setBusy("reservation");
    try {
      await api("/core/api/v1/dining/table-reservations", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          table_id: reservationTable,
          guest_name: reservationGuest,
          phone: reservationPhone || null,
          party_size: reservationParty,
          starts_at: new Date(reservationStart).toISOString(),
          ends_at: new Date(reservationEnd).toISOString(),
        }),
      });
      setReservationGuest("");
      setReservationPhone("");
      await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Не удалось забронировать стол"); }
    finally { setBusy(null); }
  }

  async function createOrder(event: FormEvent) {
    event.preventDefault();
    if (!user || !orderTable || !selectedItems.length) return;
    setBusy("order");
    try {
      const body = await api("/core/api/v1/kitchen/orders", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          source: "TABLE",
          table_id: orderTable,
          guest_count: 1,
          notes: orderNote || null,
          items: selectedItems.map((item) => ({ menu_item_id: item.id, quantity: qty[item.id] })),
        }),
      });
      await api(`/core/api/v1/dining/orders/${body.id}/waiter`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ waiter_id: user.id }),
      });
      setQty({});
      setOrderNote("");
      await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Не удалось создать заказ"); }
    finally { setBusy(null); }
  }

  if (checking) return <main className={styles.center}>Открываю зал…</main>;
  if (!user) return <main className={styles.login}><form onSubmit={login}><div className={styles.crown}>III</div><p>Три Короны · отдельный вход</p><h1>Официант / зал</h1><span>Столы, брони, заказы и выдача кухни в одном окне.</span><label>Логин<input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required autoFocus /></label><label>Пароль<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" minLength={8} required /></label>{error && <div className={styles.error}>{error}</div>}<button disabled={submitting}>{submitting ? "Входим…" : "Войти в зал"}</button><a href="/kitchen">Вход кухни</a></form></main>;

  return <main className={styles.shell}>
    <header className={styles.header}><div><p>Три Короны · Dining Floor</p><h1>Официант / зал</h1><span>{user.display_name} · {floor?.service_date || "сегодня"}</span></div><nav><a href="/kitchen">Кухня</a><a href="/kitchen/today">Меню сегодня</a><button onClick={() => void logout()}>Выйти</button></nav></header>
    {error && <div className={styles.error}>{error}</div>}

    <section className={styles.metrics}>
      <article className={ready.length ? styles.hot : ""}><strong>{ready.length}</strong><span>готово к выдаче</span></article>
      <article><strong>{mine.length}</strong><span>моих активных заказов</span></article>
      <article><strong>{unassigned.length}</strong><span>без официанта</span></article>
      <article><strong>{floor?.tables.filter((table) => table.status === "OCCUPIED").length ?? 0}</strong><span>занятых столов</span></article>
      <article><strong>{floor?.reservations.filter((item) => item.status === "BOOKED").length ?? 0}</strong><span>броней столов</span></article>
    </section>

    <DiningFloorPlan user={{ id: user.id, role: user.role }} />

    <section className={styles.section}><div className={styles.sectionHead}><div><small>Быстрые статусы</small><h2>Управление столами</h2></div><button onClick={() => void load()}>Обновить</button></div><div className={styles.tables}>{floor?.tables.map((table) => <article key={table.id} data-status={table.status}><div><strong>{table.code}</strong><span>{TABLE_LABEL[table.status] ?? table.status}</span></div><h3>{table.name}</h3><p>{table.seats} мест</p><div><button disabled={busy === table.id} onClick={() => void tableStatus(table, "OCCUPIED")}>Занят</button><button disabled={busy === table.id} onClick={() => void tableStatus(table, "CLEANING")}>Уборка</button><button disabled={busy === table.id} onClick={() => void tableStatus(table, "AVAILABLE")}>Свободен</button></div></article>)}</div></section>

    <section className={styles.two}>
      <div className={styles.section}><div className={styles.sectionHead}><div><small>Kitchen → waiter</small><h2>Активные заказы</h2></div></div><div className={styles.orders}>{floor?.orders.map((order) => <article key={order.id} className={order.status === "READY" ? styles.ready : ""}><div><strong>{order.order_number}</strong><span>{ORDER_LABEL[order.status] ?? order.status}</span></div><p>{order.table_code ? `${order.table_code} · ${order.table_name || "стол"}` : order.room_code ? `Номер ${order.room_code}` : order.source}</p><small>{order.waiter_name ? `Официант: ${order.waiter_name}` : "Официант не назначен"}</small><b>{order.total_kgs.toLocaleString("ru-RU")} KGS</b><div>{!order.waiter_id && <button disabled={busy === order.id} onClick={() => void claim(order)}>Взять заказ</button>}{order.status === "READY" && (order.waiter_id === user.id || user.role !== "DINING_STAFF") && <button className={styles.primary} disabled={busy === order.id} onClick={() => void serve(order)}>Выдано гостю</button>}</div></article>)}</div></div>

      <form className={styles.section} onSubmit={createOrder}><div className={styles.sectionHead}><div><small>Новый заказ</small><h2>Заказ со стола</h2></div></div><label>Стол<select value={orderTable} onChange={(e) => setOrderTable(e.target.value)} required><option value="">Выберите стол</option>{floor?.tables.filter((table) => table.status !== "OUT_OF_SERVICE").map((table) => <option key={table.id} value={table.id}>{table.code} · {table.name} · {TABLE_LABEL[table.status] ?? table.status}</option>)}</select></label><div className={styles.menuPicker}>{approvedMenu.map((item) => <label key={item.id}><span><strong>{item.name_ru}</strong><small>{item.price_kgs.toLocaleString("ru-RU")} KGS</small></span><input type="number" min="0" max="20" value={qty[item.id] ?? 0} onChange={(e) => setQty((current) => ({ ...current, [item.id]: Number(e.target.value) || 0 }))} /></label>)}</div><label>Комментарий<input value={orderNote} onChange={(e) => setOrderNote(e.target.value)} placeholder="Например: без лука" /></label><div className={styles.total}><span>Сумма</span><strong>{draftTotal.toLocaleString("ru-RU")} KGS</strong></div><button className={styles.primary} disabled={busy === "order" || !orderTable || !selectedItems.length}>Создать заказ</button></form>
    </section>

    <section className={styles.two}>
      <div className={styles.section}><div className={styles.sectionHead}><div><small>Reservations</small><h2>Брони столов сегодня</h2></div></div><div className={styles.reservations}>{floor?.reservations.length ? floor.reservations.map((item) => <article key={item.id}><div><strong>{item.table_code} · {item.guest_name}</strong><span>{RESERVATION_LABEL[item.status] ?? item.status}</span></div><p>{item.party_size} гостей · {new Date(item.starts_at).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}–{new Date(item.ends_at).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}</p>{item.phone && <a href={`tel:${item.phone}`}>{item.phone}</a>}<div>{item.status === "BOOKED" && <button onClick={() => void reservationStatus(item, "SEATED")}>Посадить</button>}{item.status === "SEATED" && <button onClick={() => void reservationStatus(item, "COMPLETED")}>Завершить</button>}{item.status === "BOOKED" && <button onClick={() => void reservationStatus(item, "NO_SHOW")}>Не пришли</button>}{!["COMPLETED", "CANCELLED", "NO_SHOW"].includes(item.status) && <button onClick={() => void reservationStatus(item, "CANCELLED")}>Отмена</button>}</div></article>) : <p className={styles.empty}>Броней столов на сегодня нет.</p>}</div></div>

      <form className={styles.section} onSubmit={createReservation}><div className={styles.sectionHead}><div><small>Новая бронь</small><h2>Забронировать стол</h2></div></div><label>Стол<select value={reservationTable} onChange={(e) => setReservationTable(e.target.value)} required><option value="">Выберите стол</option>{floor?.tables.filter((table) => table.status !== "OUT_OF_SERVICE").map((table) => <option key={table.id} value={table.id}>{table.code} · {table.name} · {table.seats} мест</option>)}</select></label><label>Имя гостя<input value={reservationGuest} onChange={(e) => setReservationGuest(e.target.value)} minLength={2} required /></label><label>Телефон<input value={reservationPhone} onChange={(e) => setReservationPhone(e.target.value)} /></label><label>Гостей<input type="number" min="1" max="30" value={reservationParty} onChange={(e) => setReservationParty(Number(e.target.value) || 1)} /></label><div className={styles.timeGrid}><label>Начало<input type="datetime-local" value={reservationStart} onChange={(e) => setReservationStart(e.target.value)} required /></label><label>До<input type="datetime-local" value={reservationEnd} onChange={(e) => setReservationEnd(e.target.value)} required /></label></div><button className={styles.primary} disabled={busy === "reservation"}>Создать бронь стола</button></form>
    </section>
  </main>;
}
