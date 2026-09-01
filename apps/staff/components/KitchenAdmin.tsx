"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import styles from "./KitchenAdmin.module.css";

type User = { id: string; display_name: string; role: string };
type MenuItem = { id: string; code: string; category: string; name_ru: string; name_kg: string; name_en: string; price_kgs: number; is_active: boolean; is_draft: boolean; sort_order: number };
type TableItem = { id: string; code: string; name: string; seats: number; status: string; is_active: boolean; notes?: string | null };
type OrderItem = { id: string; name_ru: string; quantity: number; line_total_kgs: number; status: string };
type Order = { id: string; order_number: string; status: string; source: string; guest_count: number; total_kgs: number; table_code?: string | null; table_name?: string | null; room_code?: string | null; opened_at: string; items: OrderItem[] };
type Arrival = { id: string; status: string; title: string; description?: string | null; room_code?: string | null; booking_number?: string | null; created_at: string };
type Tab = "orders" | "tables" | "menu" | "arrivals";

const STATUS_NEXT: Record<string, { label: string; value: string } | null> = {
  NEW: { label: "Принять", value: "ACCEPTED" },
  ACCEPTED: { label: "Готовить", value: "COOKING" },
  COOKING: { label: "Готово", value: "READY" },
  READY: { label: "Выдано", value: "SERVED" },
  SERVED: null,
  CANCELLED: null,
};
const STATUS_LABEL: Record<string, string> = {
  NEW: "Новый",
  ACCEPTED: "Принят",
  COOKING: "Готовится",
  READY: "Готов",
  SERVED: "Выдан",
  CANCELLED: "Отменён",
};
const TABLE_STATUS: Record<string, string> = {
  AVAILABLE: "Свободен",
  RESERVED: "Бронь",
  OCCUPIED: "Занят",
  CLEANING: "Уборка",
  OUT_OF_SERVICE: "Не используется",
};
const CATEGORIES: Record<string, string> = {
  BREAKFAST: "Завтрак", SOUP: "Супы", SALAD: "Салаты", MAIN: "Основное", SIDE: "Гарниры", DESSERT: "Десерты", DRINK: "Напитки",
};

async function api(path: string, init?: RequestInit) {
  const response = await fetch(path, { cache: "no-store", ...init });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(typeof body?.detail === "string" ? body.detail : "Ошибка Resort Core");
  return body;
}

export default function KitchenAdmin() {
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(true);
  const [tab, setTab] = useState<Tab>("orders");
  const [menu, setMenu] = useState<MenuItem[]>([]);
  const [tables, setTables] = useState<TableItem[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [arrivals, setArrivals] = useState<Arrival[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [tableCode, setTableCode] = useState("");
  const [tableName, setTableName] = useState("");
  const [tableSeats, setTableSeats] = useState(4);
  const [selectedTable, setSelectedTable] = useState("");
  const [qty, setQty] = useState<Record<string, number>>({});
  const [orderNote, setOrderNote] = useState("");

  const loadAll = useCallback(async () => {
    try {
      const [menuBody, tableBody, orderBody, arrivalBody] = await Promise.all([
        api("/core/api/v1/kitchen/menu"),
        api("/core/api/v1/kitchen/tables"),
        api("/core/api/v1/kitchen/orders?status=ACTIVE"),
        api("/core/api/v1/ops/kitchen/arrivals"),
      ]);
      setMenu(menuBody.items ?? []);
      setTables(tableBody.items ?? []);
      setOrders(orderBody.items ?? []);
      setArrivals(arrivalBody.items ?? []);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка связи");
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const me = await api("/core/api/v1/auth/me") as User;
        if (!["OWNER", "MANAGER", "DINING_STAFF"].includes(me.role)) throw new Error("Нет доступа к кухне");
        if (!cancelled) setUser(me);
        await api("/core/api/v1/ops/kitchen/sync-arrivals", { method: "POST" }).catch(() => null);
        if (!cancelled) await loadAll();
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Нет доступа");
      } finally {
        if (!cancelled) setChecking(false);
      }
    })();
    const timer = window.setInterval(async () => {
      await api("/core/api/v1/ops/kitchen/sync-arrivals", { method: "POST" }).catch(() => null);
      await loadAll();
    }, 10000);
    return () => { cancelled = true; window.clearInterval(timer); };
  }, [loadAll]);

  const activeMenu = useMemo(() => menu.filter((item) => item.is_active), [menu]);
  const activeTables = useMemo(() => tables.filter((item) => item.is_active), [tables]);
  const selectedItems = useMemo(() => activeMenu.filter((item) => (qty[item.id] ?? 0) > 0), [activeMenu, qty]);
  const draftTotal = selectedItems.reduce((sum, item) => sum + item.price_kgs * (qty[item.id] ?? 0), 0);

  async function bootstrapMenu() {
    setBusy("bootstrap");
    try { await api("/core/api/v1/kitchen/menu/bootstrap-draft", { method: "POST" }); await loadAll(); }
    catch (e) { setError(e instanceof Error ? e.message : "Ошибка"); }
    finally { setBusy(null); }
  }

  async function createTable(event: FormEvent) {
    event.preventDefault(); setBusy("table");
    try {
      await api("/core/api/v1/kitchen/tables", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ code: tableCode, name: tableName, seats: tableSeats }) });
      setTableCode(""); setTableName(""); setTableSeats(4); await loadAll();
    } catch (e) { setError(e instanceof Error ? e.message : "Ошибка"); }
    finally { setBusy(null); }
  }

  async function patchTable(id: string, patch: Record<string, unknown>) {
    setBusy(id);
    try { await api(`/core/api/v1/kitchen/tables/${id}`, { method: "PATCH", headers: { "content-type": "application/json" }, body: JSON.stringify(patch) }); await loadAll(); }
    catch (e) { setError(e instanceof Error ? e.message : "Ошибка"); }
    finally { setBusy(null); }
  }

  async function patchMenu(item: MenuItem, patch: Record<string, unknown>) {
    setBusy(item.id);
    try { await api(`/core/api/v1/kitchen/menu/${item.id}`, { method: "PATCH", headers: { "content-type": "application/json" }, body: JSON.stringify(patch) }); await loadAll(); }
    catch (e) { setError(e instanceof Error ? e.message : "Ошибка"); }
    finally { setBusy(null); }
  }

  async function createOrder(event: FormEvent) {
    event.preventDefault();
    if (!selectedItems.length) { setError("Добавьте хотя бы одно блюдо"); return; }
    setBusy("order");
    try {
      await api("/core/api/v1/kitchen/orders", {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ source: "TABLE", table_id: selectedTable || null, guest_count: 1, notes: orderNote || null, items: selectedItems.map((item) => ({ menu_item_id: item.id, quantity: qty[item.id] })) }),
      });
      setQty({}); setOrderNote(""); await loadAll(); setTab("orders");
    } catch (e) { setError(e instanceof Error ? e.message : "Ошибка"); }
    finally { setBusy(null); }
  }

  async function orderAction(order: Order, value: string) {
    setBusy(order.id);
    try { await api(`/core/api/v1/kitchen/orders/${order.id}/status`, { method: "PATCH", headers: { "content-type": "application/json" }, body: JSON.stringify({ status: value }) }); await loadAll(); }
    catch (e) { setError(e instanceof Error ? e.message : "Ошибка"); }
    finally { setBusy(null); }
  }

  async function ackArrival(id: string) {
    setBusy(id);
    try { await api(`/core/api/v1/ops/kitchen/arrivals/${id}/ack`, { method: "POST" }); await loadAll(); }
    catch (e) { setError(e instanceof Error ? e.message : "Ошибка"); }
    finally { setBusy(null); }
  }

  if (checking) return <main className={styles.center}>Подключаю кухню…</main>;
  if (!user) return <main className={styles.center}><div><h1>Кухня недоступна</h1><p>{error}</p><a href="/">Вернуться в «Мою смену»</a></div></main>;

  return <main className={styles.shell}>
    <header className={styles.header}>
      <div><p>Три Короны · Resort OS</p><h1>Kitchen Admin</h1><span>{user.display_name} · {user.role}</span></div>
      <a href="/">Моя смена</a>
    </header>

    <section className={styles.stats}>
      <div><strong>{orders.length}</strong><span>активных заказов</span></div>
      <div><strong>{activeTables.filter((t) => t.status === "OCCUPIED").length}</strong><span>занятых столов</span></div>
      <div><strong>{arrivals.length}</strong><span>новых заездов</span></div>
      <div><strong>{activeMenu.length}</strong><span>блюд в меню</span></div>
    </section>

    <nav className={styles.tabs}>
      {(["orders", "tables", "menu", "arrivals"] as Tab[]).map((item) => <button key={item} className={tab === item ? styles.active : ""} onClick={() => setTab(item)}>{item === "orders" ? "Заказы" : item === "tables" ? "Столы" : item === "menu" ? "Меню" : `Заезды${arrivals.length ? ` · ${arrivals.length}` : ""}`}</button>)}
    </nav>
    {error && <div className={styles.error}>{error}</div>}

    {tab === "orders" && <section className={styles.grid}>
      <div className={styles.panel}>
        <div className={styles.panelHead}><div><small>Kitchen Display</small><h2>Очередь кухни</h2></div><button onClick={() => void loadAll()}>Обновить</button></div>
        {!orders.length ? <p className={styles.empty}>Активных заказов нет.</p> : <div className={styles.orderList}>{orders.map((order) => {
          const next = STATUS_NEXT[order.status];
          return <article className={styles.order} key={order.id} data-status={order.status}>
            <div className={styles.orderTop}><strong>{order.order_number}</strong><span>{STATUS_LABEL[order.status] ?? order.status}</span></div>
            <p>{order.table_code ? `${order.table_name || "Стол"} · ${order.table_code}` : order.room_code ? `Номер ${order.room_code}` : order.source}</p>
            <div className={styles.items}>{order.items.map((item) => <div key={item.id}><span>{item.quantity}× {item.name_ru}</span><b>{item.line_total_kgs.toLocaleString()} KGS</b></div>)}</div>
            <div className={styles.orderBottom}><strong>{order.total_kgs.toLocaleString()} KGS</strong><div>{next && <button disabled={busy === order.id} onClick={() => void orderAction(order, next.value)}>{next.label}</button>}{!(["SERVED", "CANCELLED"].includes(order.status)) && <button className={styles.danger} disabled={busy === order.id} onClick={() => void orderAction(order, "CANCELLED")}>Отмена</button>}</div></div>
          </article>;
        })}</div>}
      </div>
      <form className={styles.panel} onSubmit={createOrder}>
        <div className={styles.panelHead}><div><small>Новый заказ</small><h2>Стол / зал</h2></div></div>
        <label>Стол<select value={selectedTable} onChange={(e) => setSelectedTable(e.target.value)}><option value="">Без стола</option>{activeTables.map((table) => <option key={table.id} value={table.id}>{table.code} · {table.name} · {TABLE_STATUS[table.status] ?? table.status}</option>)}</select></label>
        {!activeMenu.length ? <button type="button" onClick={() => void bootstrapMenu()} disabled={busy === "bootstrap"}>Загрузить тестовое меню</button> : <div className={styles.menuPicker}>{activeMenu.map((item) => <label key={item.id}><span><b>{item.name_ru}</b><small>{CATEGORIES[item.category] ?? item.category} · {item.price_kgs} KGS</small></span><input type="number" min="0" max="20" value={qty[item.id] ?? 0} onChange={(e) => setQty((current) => ({ ...current, [item.id]: Number(e.target.value) }))} /></label>)}</div>}
        <label>Комментарий<input value={orderNote} onChange={(e) => setOrderNote(e.target.value)} placeholder="Например: без лука" /></label>
        <div className={styles.total}><span>Сумма заказа</span><strong>{draftTotal.toLocaleString()} KGS</strong></div>
        <button className={styles.primary} disabled={busy === "order" || !selectedItems.length}>Создать заказ</button>
        <small className={styles.financeNote}>Заказ кухни не создаёт Hotel Payment автоматически.</small>
      </form>
    </section>}

    {tab === "tables" && <section className={styles.grid}>
      <div className={styles.panel}><div className={styles.panelHead}><div><small>Зал</small><h2>Столы</h2></div></div>{!tables.length ? <p className={styles.empty}>Столы ещё не заведены.</p> : <div className={styles.tableGrid}>{tables.map((table) => <article key={table.id}><div><strong>{table.code}</strong><span>{TABLE_STATUS[table.status] ?? table.status}</span></div><h3>{table.name}</h3><p>{table.seats} мест</p><select value={table.status} disabled={busy === table.id} onChange={(e) => void patchTable(table.id, { status: e.target.value })}>{Object.keys(TABLE_STATUS).map((status) => <option key={status} value={status}>{TABLE_STATUS[status]}</option>)}</select></article>)}</div>}</div>
      <form className={styles.panel} onSubmit={createTable}><div className={styles.panelHead}><div><small>Настройка</small><h2>Добавить стол</h2></div></div><label>Код<input value={tableCode} onChange={(e) => setTableCode(e.target.value)} placeholder="T01" required /></label><label>Название<input value={tableName} onChange={(e) => setTableName(e.target.value)} placeholder="Стол у окна" required /></label><label>Количество мест<input type="number" min="1" max="30" value={tableSeats} onChange={(e) => setTableSeats(Number(e.target.value))} /></label><button className={styles.primary} disabled={busy === "table"}>Добавить</button></form>
    </section>}

    {tab === "menu" && <section className={styles.panel}>
      <div className={styles.panelHead}><div><small>Каталог</small><h2>Меню кухни</h2></div>{!menu.length && <button onClick={() => void bootstrapMenu()} disabled={busy === "bootstrap"}>Загрузить тестовое меню</button>}</div>
      {!menu.length ? <p className={styles.empty}>Меню пустое. Можно загрузить безопасный тестовый набор блюд.</p> : <div className={styles.menuAdmin}>{menu.map((item) => <article key={item.id}><div className={styles.menuTitle}><div><span>{CATEGORIES[item.category] ?? item.category}</span><strong>{item.name_ru}</strong><small>{item.code}{item.is_draft ? " · черновик" : ""}</small></div><button className={item.is_active ? "" : styles.mutedButton} disabled={busy === item.id} onClick={() => void patchMenu(item, { is_active: !item.is_active })}>{item.is_active ? "В меню" : "Скрыто"}</button></div><div className={styles.menuEdit}><input defaultValue={item.name_ru} onBlur={(e) => { if (e.target.value !== item.name_ru) void patchMenu(item, { name_ru: e.target.value }); }} /><label><input type="number" defaultValue={item.price_kgs} min="0" onBlur={(e) => { const value = Number(e.target.value); if (value !== item.price_kgs) void patchMenu(item, { price_kgs: value }); }} /><span>KGS</span></label>{item.is_draft && <button onClick={() => void patchMenu(item, { is_draft: false })}>Утвердить</button>}</div></article>)}</div>}
    </section>}

    {tab === "arrivals" && <section className={styles.panel}><div className={styles.panelHead}><div><small>Check-in → кухня</small><h2>Новые заезды</h2></div><button onClick={async () => { await api("/core/api/v1/ops/kitchen/sync-arrivals", { method: "POST" }); await loadAll(); }}>Синхронизировать</button></div>{!arrivals.length ? <p className={styles.empty}>Непросмотренных заездов нет.</p> : <div className={styles.arrivals}>{arrivals.map((arrival) => <article key={arrival.id}><div><strong>{arrival.title}</strong><span>{arrival.booking_number}</span></div><p>{arrival.description}</p><button disabled={busy === arrival.id} onClick={() => void ackArrival(arrival.id)}>Ознакомился</button></article>)}</div>}</section>}
  </main>;
}
