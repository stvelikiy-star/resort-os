"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import styles from "./GuestRequestShiftPanel.module.css";

type Role = "OWNER" | "MANAGER" | "MAID" | "TECHNICIAN" | "RECEPTION" | "DINING_STAFF" | string;
type User = { id: string; display_name: string; role: Role };
type Item = {
  id: string;
  request_code: string;
  status: "OPEN" | "IN_PROGRESS" | "DONE" | "CANCELLED";
  title: string;
  description?: string | null;
  room_code?: string | null;
  guest_first_name?: string | null;
  booking_number?: string | null;
  service_date?: string | null;
  service_time?: string | null;
  assigned_to_id?: string | null;
  assigned_to_name?: string | null;
};

const LABELS: Record<string, string> = {
  HOUSEKEEPING: "Уборка по просьбе гостя",
  TOWELS: "Полотенца",
  LINEN: "Замена белья",
  MAINTENANCE: "Поломка / ремонт",
  TRANSFER: "Трансфер",
  MEALS: "Питание",
  SAUNA: "Сауна",
  BILLIARDS: "Бильярд",
  EXCURSIONS: "Экскурсии",
  ADMIN: "Администратор",
};

const STATUS: Record<string, string> = { OPEN: "Новая", IN_PROGRESS: "В работе", DONE: "Готово", CANCELLED: "Отменена" };
const SUPPORTED = new Set(["OWNER", "MANAGER", "MAID", "TECHNICIAN", "RECEPTION", "DINING_STAFF"]);

export default function GuestRequestShiftPanel() {
  const [user, setUser] = useState<User | null>(null);
  const [items, setItems] = useState<Item[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const me = await fetch("/core/api/v1/auth/me", { cache: "no-store" });
      if (!me.ok) {
        setUser(null);
        setItems([]);
        return;
      }
      const who = await me.json() as User;
      if (!SUPPORTED.has(who.role)) {
        setUser(null);
        setItems([]);
        return;
      }
      setUser(who);
      const response = await fetch("/core/api/v1/ops/guest-requests?status=ACTIVE&limit=200", { cache: "no-store" });
      if (response.status === 403) {
        setItems([]);
        return;
      }
      if (!response.ok) throw new Error("Не удалось загрузить гостевые заявки");
      const body = await response.json() as { items?: Item[] };
      setItems(body.items ?? []);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка связи");
    }
  }, []);

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(), 5000);
    return () => window.clearInterval(timer);
  }, [load]);

  async function mutate(item: Item, action: "claim" | "complete") {
    setBusy(item.id);
    setError(null);
    try {
      const response = await fetch(`/core/api/v1/ops/guest-requests/${item.id}/${action}`, { method: "POST" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Не удалось выполнить действие");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка операции");
    } finally {
      setBusy(null);
    }
  }

  const active = useMemo(() => items.filter((item) => item.status === "OPEN" || item.status === "IN_PROGRESS"), [items]);
  if (!user) return null;

  return <section className={styles.wrap} aria-label="Заявки гостей">
    <div className={styles.card}>
      <div className={styles.head}>
        <div><p className={styles.eyebrow}>Guest OS → персонал</p><h2>Заявки гостей · {active.length}</h2></div>
        <button className={styles.refresh} onClick={() => void load()}>Обновить</button>
      </div>
      {error && <div className={styles.empty}>{error}</div>}
      {!active.length ? <div className={styles.empty}>Новых заявок для вашей роли сейчас нет.</div> : <div className={styles.stack}>
        {active.map((item) => {
          const mine = item.assigned_to_id === user.id;
          return <article key={item.id} className={styles.item}>
            <div className={styles.meta}><span>{item.room_code ? `№ ${item.room_code}` : "Без номера"} · {LABELS[item.request_code] || item.request_code}</span><span>{STATUS[item.status] || item.status}</span></div>
            <h3>{item.title}</h3>
            {item.description && <p>{item.description}</p>}
            <small>{item.guest_first_name ? `Гость: ${item.guest_first_name}` : ""}{item.booking_number ? ` · ${item.booking_number}` : ""}{item.service_date ? ` · ${item.service_date}` : ""}{item.service_time ? ` · ${item.service_time}` : ""}</small>
            {item.assigned_to_name && <small>Исполнитель: {item.assigned_to_name}</small>}
            <div className={styles.actions}>
              {item.status === "OPEN" && !item.assigned_to_id && <button className={styles.action} disabled={busy === item.id} onClick={() => void mutate(item, "claim")}>Взять</button>}
              {item.status === "IN_PROGRESS" && (mine || user.role === "OWNER" || user.role === "MANAGER") && <button className={`${styles.action} ${styles.done}`} disabled={busy === item.id} onClick={() => void mutate(item, "complete")}>Выполнено</button>}
            </div>
          </article>;
        })}
      </div>}
    </div>
  </section>;
}
