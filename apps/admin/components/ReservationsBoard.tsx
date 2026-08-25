"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type Reservation = {
  id: string;
  bookingNumber: string;
  status: string;
  checkIn: string;
  checkOut: string;
  adults: number;
  children: number;
  totalKgs: number;
  firstName?: string | null;
  phone?: string | null;
  room_code?: string | null;
  room_type_name?: string | null;
};

const fmt = (value: number) => new Intl.NumberFormat("ru-RU").format(value) + " сом";
const statusLabels: Record<string, string> = {
  GUARANTEED: "Гарантирована",
  CHECKED_IN: "Проживает",
  CHECKED_OUT: "Выехал",
  CANCELLED: "Отменена",
  NO_SHOW: "Не заехал",
};

export default function ReservationsBoard() {
  const [items, setItems] = useState<Reservation[]>([]);
  const [filter, setFilter] = useState("ACTIVE");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/core/api/v1/admin/booking/reservations?limit=250", { cache: "no-store" });
      if (!response.ok) throw new Error("Не удалось загрузить брони");
      const data = await response.json();
      setItems(data.items || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка загрузки");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const visible = useMemo(() => items.filter((item) => {
    if (filter === "ALL") return true;
    if (filter === "ACTIVE") return ["GUARANTEED", "CHECKED_IN"].includes(item.status);
    return item.status === filter;
  }), [items, filter]);

  async function transition(item: Reservation, action: "check-in" | "check-out") {
    setBusy(item.id);
    setError(null);
    try {
      const response = await fetch(`/core/api/v1/admin/stays/reservations/${item.id}/${action}`, { method: "POST" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Не удалось изменить статус проживания");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка операции");
    } finally {
      setBusy(null);
    }
  }

  return (
    <main className="work-shell">
      <div className="work-head">
        <div><p className="eyebrow">PMS · проживание</p><h1>Брони и заезды</h1><p className="subtitle">Гарантированные брони, проживающие гости и выезды.</p></div>
        <div className="work-actions"><select value={filter} onChange={(e) => setFilter(e.target.value)}><option value="ACTIVE">Активные</option><option value="GUARANTEED">Ожидают заезд</option><option value="CHECKED_IN">Проживают</option><option value="CHECKED_OUT">Выехали</option><option value="ALL">Все</option></select><button className="btn" onClick={load}>Обновить</button></div>
      </div>
      {error && <div className="error-box">{error}</div>}
      {loading ? <div className="loading">Загрузка броней…</div> : <div className="reservation-list">
        {visible.length === 0 && <div className="empty">Броней в этом фильтре нет.</div>}
        {visible.map((item) => <article className="reservation-card" key={item.id}>
          <div className="reservation-id"><span>{statusLabels[item.status] || item.status}</span><strong>{item.bookingNumber}</strong></div>
          <div><span className="field-label">Гость</span><b>{item.firstName || "Без имени"}</b>{item.phone && <a href={`tel:${item.phone}`}>{item.phone}</a>}</div>
          <div><span className="field-label">Номер</span><b>{item.room_code || "—"}</b><small>{item.room_type_name || ""}</small></div>
          <div><span className="field-label">Даты</span><b>{item.checkIn} → {item.checkOut}</b><small>{item.adults} взр. · {item.children} дет.</small></div>
          <div><span className="field-label">Стоимость</span><b>{fmt(item.totalKgs)}</b></div>
          <div className="reservation-actions">{item.status === "GUARANTEED" && <button className="btn primary" disabled={busy === item.id} onClick={() => transition(item, "check-in")}>Оформить заезд</button>}{item.status === "CHECKED_IN" && <button className="btn primary" disabled={busy === item.id} onClick={() => transition(item, "check-out")}>Оформить выезд</button>}</div>
        </article>)}
      </div>}
    </main>
  );
}
