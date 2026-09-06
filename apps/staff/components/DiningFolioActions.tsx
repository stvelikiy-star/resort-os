"use client";

import { useCallback, useEffect, useState } from "react";

import styles from "./DiningFolioActions.module.css";

type Order = {
  id: string;
  order_number: string;
  status: string;
  table_code?: string | null;
  room_code?: string | null;
  waiter_name?: string | null;
  guest_name?: string | null;
  total_kgs: number;
  folio_charge_id?: string | null;
  eligible_to_post: boolean;
  stay_status?: string | null;
  financial_truth: string;
};

type ResponseBody = { items: Order[]; truth: string };

async function api(path: string, init?: RequestInit) {
  const response = await fetch(path, { cache: "no-store", ...init });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(typeof body?.detail === "string" ? body.detail : body?.detail?.code || "Ошибка Resort Core");
  return body;
}

export default function DiningFolioActions() {
  const [data, setData] = useState<ResponseBody | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const body = await api("/core/api/v1/dining/folio-orders") as ResponseBody;
      setData(body);
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось загрузить начисления ресторана");
    }
  }, []);

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(), 10000);
    return () => window.clearInterval(timer);
  }, [load]);

  async function post(order: Order) {
    if (!window.confirm(`Начислить ${order.total_kgs.toLocaleString("ru-RU")} KGS на счёт номера? Это создаст долг в Folio, но НЕ отметит оплату.`)) return;
    setBusy(order.id);
    setError(null);
    setNotice(null);
    try {
      const result = await api(`/core/api/v1/dining/orders/${order.id}/folio`, { method: "POST" });
      setNotice(`${order.order_number}: начисление создано в Folio. Payment не создавался.`);
      if (!result.payment_created) await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось начислить заказ на номер");
    } finally {
      setBusy(null);
    }
  }

  const items = data?.items ?? [];
  if (!items.length && !error) return null;

  return <section className={styles.shell}>
    <div className={styles.panel}>
      <header className={styles.head}>
        <div><small>RESTAURANT → FOLIO</small><h3>Начисление на номер</h3><p>Только явное действие сотрудника. Начисление увеличивает долг гостя и никогда не считается фактом оплаты.</p></div>
        <button onClick={() => void load()}>Обновить</button>
      </header>
      {notice && <div className={styles.notice}>{notice}</div>}
      {error && <div className={styles.error}>{error}</div>}
      {items.length === 0 ? <div className={styles.empty}>Нет ресторанных заказов, связанных с проживающими гостями.</div> : <div className={styles.list}>
        {items.map((order) => <article className={styles.item} key={order.id}>
          <div><strong>{order.order_number} · {order.guest_name || "Гость"}</strong><span>{order.table_code ? `Стол ${order.table_code}` : order.room_code ? `Номер ${order.room_code}` : "Ресторан"} · {order.status}{order.waiter_name ? ` · ${order.waiter_name}` : ""}</span></div>
          <div className={styles.amount}>{order.total_kgs.toLocaleString("ru-RU")} KGS</div>
          {order.folio_charge_id ? <div className={styles.posted}>На счёте номера</div> : order.eligible_to_post ? <button disabled={busy === order.id} onClick={() => void post(order)}>{busy === order.id ? "Начисляю…" : "Начислить на номер"}</button> : <div className={styles.blocked}>Недоступно · Stay {order.stay_status || "—"}</div>}
        </article>)}
      </div>}
    </div>
  </section>;
}
