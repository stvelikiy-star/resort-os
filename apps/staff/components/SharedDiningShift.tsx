"use client";

import { useCallback, useEffect, useState } from "react";

type User = {
  id: string; role: "COOK" | "WAITER"; property_code: string;
  property_id: string; tenant_id: string; display_name: string;
  module_permissions?: string[];
};
type Order = {
  id: string; order_number: string; status: string; source: string;
  room_code?: string | null; table_code?: string | null;
  total_kgs?: number; waiter_id?: string | null;
};
type Floor = { current_user_id: string; orders: Order[];
  tables: Array<{ id: string; code: string; name: string }>; reservations: unknown[] };
type Kitchen = { items: Order[] };

const NEXT_KITCHEN_STATUS: Record<string, string> = {
  NEW: "ACCEPTED", ACCEPTED: "COOKING", COOKING: "READY",
};

export default function SharedDiningShift({ user, onEnd }: {
  user: User; onEnd: () => void;
}) {
  const [orders, setOrders] = useState<Order[]>([]);
  const [tables, setTables] = useState<Floor["tables"]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const refresh = useCallback(async (signal?: AbortSignal) => {
    const me = await fetch("/core/api/v1/auth/me", { cache: "no-store", signal });
    if (!me.ok) { onEnd(); return; }
    const identity = await me.json() as User;
    if (identity.id !== user.id || identity.property_id !== user.property_id ||
        identity.tenant_id !== user.tenant_id || identity.role !== user.role ||
        !identity.module_permissions?.includes("DINING")) {
      onEnd(); return;
    }
    const path = user.role === "COOK" ? "/core/api/v1/kitchen/orders?status=ACTIVE"
      : "/core/api/v1/dining/floor";
    const response = await fetch(path, { cache: "no-store", signal });
    if (response.status === 401) { onEnd(); return; }
    if (!response.ok) throw new Error("Dining module not admitted");
    const data = await response.json() as Kitchen & Floor;
    const values = user.role === "COOK" ? data.items : data.orders;
    if (!Array.isArray(values) || (user.role === "WAITER" && (
        data.current_user_id !== user.id || !Array.isArray(data.tables)))) {
      throw new Error("Unverified dining response");
    }
    if (signal?.aborted) return;
    setOrders(values);
    setTables(user.role === "WAITER" ? data.tables : []);
  }, [user, onEnd]);

  useEffect(() => {
    const controller = new AbortController();
    setOrders([]); setTables([]); setLoading(true); setError("");
    void refresh(controller.signal)
      .catch(() => { if (!controller.signal.aborted) setError("Данные кухни/зала не подтверждены сервером."); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [refresh]);

  async function changeOrder(order: Order) {
    if (busy) return;
    const cook = user.role === "COOK";
    const next = cook ? NEXT_KITCHEN_STATUS[order.status] : undefined;
    if (cook && !next) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const url = cook
        ? "/core/api/v1/kitchen/orders/" + order.id + "/status"
        : "/core/api/v1/dining/orders/" + order.id + "/waiter";
      const response = await fetch(url, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(cook ? { status: next } : { waiter_id: user.id }),
      });
      if (response.status === 401) { onEnd(); return; }
      if (!response.ok) throw new Error("Mutation not confirmed");
      const result = await response.json();
      if (result.id !== order.id || (cook
          ? result.status !== next
          : result.waiter_id !== user.id)) throw new Error("Unexpected receipt");
      setNotice("Операция по заказу " + order.order_number + " подтверждена.");
      try { await refresh(); }
      catch { setError("Операция подтверждена сервером, но список не обновился."); }
    } catch {
      setError("Результат действия не подтверждён. Проверьте заказ перед повтором.");
    } finally { setBusy(false); }
  }

  async function logout() {
    // Revocation is server-side. Do not expose stale hotel rows after logout.
    setOrders([]); setTables([]);
    try { await fetch("/core/api/v1/auth/logout", { method: "POST" }); }
    finally { onEnd(); }
  }

  return <main className="shift-shell">
    <header className="shift-head">
      <div><p className="shift-eyebrow">MARINA SMART · {user.property_code}</p>
        <h1>{user.role === "COOK" ? "Кухня · заказы" : "Официант · зал"}</h1>
        <span>{user.display_name}</span>
      </div>
      <button type="button" className="shift-ghost" onClick={() => void logout()}>Выйти</button>
    </header>
    {loading && <p role="status">Загружаю данные своей гостиницы…</p>}
    {notice && <p role="status">{notice}</p>}
    {error && <p role="alert">{error}</p>}
    {!loading && !error && <>
      {user.role === "WAITER" && <p>Столов зала: {tables.length}. Заказы своей гостиницы.</p>}
      <section aria-label={user.role === "COOK" ? "Заказы кухни" : "Заказы зала"}>
        {orders.length === 0 && <p>Активных заказов пока нет.</p>}
        {orders.map(order => <article key={order.id} className="shift-card">
          <h2>{order.order_number}</h2>
          <p>{order.status} · {order.room_code || order.table_code || order.source}</p>
          {user.role === "COOK" && NEXT_KITCHEN_STATUS[order.status] &&
            <button type="button" className="shift-primary" disabled={busy}
              onClick={() => void changeOrder(order)}>
              {order.status === "NEW" ? "Принять в работу" :
                order.status === "ACCEPTED" ? "Начать приготовление" : "Заказ готов"}
            </button>}
          {user.role === "WAITER" && order.waiter_id !== user.id &&
            <button type="button" className="shift-primary" disabled={busy}
              onClick={() => void changeOrder(order)}>Назначить заказ себе</button>}
        </article>)}
      </section>
    </>}
  </main>;
}
