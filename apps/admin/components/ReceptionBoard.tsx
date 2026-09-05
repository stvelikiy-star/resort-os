"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import ReservationFolioPanel from "./ReservationFolioPanel";

type Reservation = {
  id: string;
  bookingNumber: string;
  status: string;
  checkIn: string;
  checkOut: string;
  adults: number;
  children: number;
  totalKgs: number;
  paidKgs: number;
  remainingKgs: number;
  firstName?: string | null;
  phone?: string | null;
  room_code?: string | null;
  room_type_name?: string | null;
  room_state?: string | null;
  schedule_segments: number;
  has_room_move: boolean;
};

type ScheduleSegment = {
  inventory_block_id: string;
  room_id: string;
  room_code: string;
  room_state: string;
  room_type_code: string;
  room_type_name: string;
  area?: string | null;
  start: string;
  end: string;
  is_working_room: boolean;
};

type Detail = {
  local_date: string;
  reservation: { id: string; booking_number: string; status: string; check_in: string; check_out: string; adults: number; children: number; total_kgs: number; notes?: string | null; created_at: string };
  guest: { first_name?: string | null; last_name?: string | null; phone?: string | null; email?: string | null };
  source: { channel?: string | null; request_id?: string | null };
  room: { id: string; code: string; state: string; room_type_code?: string | null; room_type_name?: string | null; area?: string | null; segment_start: string; segment_end: string } | null;
  schedule: ScheduleSegment[];
  finance: { total_kgs: number; paid_kgs: number; remaining_kgs: number; payments: Array<{ id: string; amount_kgs: number; method: string; status: string; provider?: string | null; external_ref?: string | null; paid_at?: string | null; created_at: string }> };
  room_tasks: Array<{ id: string; room_code: string; type: string; status: string; priority: string; title: string; assigned_to_name?: string | null; created_at: string }>;
  audit: Array<{ id: string; action: string; resource: string; source?: string | null; result: string; created_at: string }>;
};

type Filter = "ACTIVE" | "ARRIVALS_TODAY" | "DEPARTURES_TODAY" | "GUARANTEED" | "CHECKED_IN" | "CHECKED_OUT" | "ALL";

const money = (value: number) => `${new Intl.NumberFormat("ru-RU").format(value)} сом`;
const statusLabel: Record<string, string> = { GUARANTEED: "Гарантирована", CHECKED_IN: "Проживает", CHECKED_OUT: "Выехал", CANCELLED: "Отменена", NO_SHOW: "Не заехал" };
const roomStateLabel: Record<string, string> = { CLEAN: "Готов", DIRTY: "Нужна уборка", IN_INSPECTION: "На проверке", TECH_BLOCK: "Ремонт", UNKNOWN: "Не указан" };

function actionError(body: any, fallback: string) {
  if (typeof body?.detail === "string") return body.detail;
  if (body?.detail?.code === "CHECK_IN_ROOM_NOT_READY") {
    return `Номер ${body.detail.room_code || ""} не готов к заселению (${roomStateLabel[body.detail.room_state] || body.detail.room_state || "неизвестный статус"}).`.trim();
  }
  if (body?.detail?.code === "CHECK_IN_DATE_OUTSIDE_SCHEDULE") {
    return `Сегодня не входит в даты брони. Сначала измените даты в шахматке (${body.detail.planned_check_in} → ${body.detail.planned_check_out}).`;
  }
  if (body?.detail?.code === "CHECK_OUT_AFTER_SCHEDULE") {
    return `Дата выезда уже позже графика брони. Сначала продлите проживание в шахматке до ${body.detail.actual_local_date}.`;
  }
  if (body?.detail?.code === "CHECK_OUT_WOULD_CREATE_ZERO_NIGHT_STAY") {
    return "Нельзя оформить выезд в дату заезда в текущей модели проживания. Проверьте даты брони.";
  }
  return fallback;
}

export default function ReceptionBoard() {
  const [items, setItems] = useState<Reservation[]>([]);
  const [localDate, setLocalDate] = useState<string>("");
  const [filter, setFilter] = useState<Filter>("ACTIVE");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/core/api/v1/admin/reception/reservations?limit=500", { cache: "no-store" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Не удалось загрузить брони");
      setItems(body.items || []);
      setLocalDate(body.local_date || "");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка загрузки");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return items.filter((item) => {
      let statusMatch = true;
      if (filter === "ACTIVE") statusMatch = ["GUARANTEED", "CHECKED_IN"].includes(item.status);
      else if (filter === "ARRIVALS_TODAY") statusMatch = item.status === "GUARANTEED" && Boolean(localDate) && item.checkIn === localDate;
      else if (filter === "DEPARTURES_TODAY") statusMatch = item.status === "CHECKED_IN" && Boolean(localDate) && item.checkOut === localDate;
      else if (filter !== "ALL") statusMatch = item.status === filter;
      if (!statusMatch) return false;
      if (!q) return true;
      return [item.bookingNumber, item.firstName, item.phone, item.room_code, item.room_type_name].some((value) => value?.toLowerCase().includes(q));
    });
  }, [items, filter, query, localDate]);

  async function transition(item: Reservation, action: "check-in" | "check-out") {
    const prompt = action === "check-in"
      ? `Подтвердить заезд ${item.firstName || "гостя"} в номер ${item.room_code || "—"}?`
      : `Подтвердить выезд ${item.firstName || "гостя"} из номера ${item.room_code || "—"}? Номер станет «Нужна уборка».`;
    if (!window.confirm(prompt)) return;

    setBusy(item.id);
    setError(null);
    try {
      const response = await fetch(`/core/api/v1/admin/stays/reservations/${item.id}/${action}`, { method: "POST" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(actionError(body, "Не удалось выполнить операцию"));
      await load();
      if (detail?.reservation.id === item.id) await openDetail(item.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка операции");
    } finally {
      setBusy(null);
    }
  }

  async function openDetail(id: string) {
    setDetailLoading(true);
    setError(null);
    try {
      const response = await fetch(`/core/api/v1/admin/booking/reservations/${id}`, { cache: "no-store" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Не удалось загрузить карточку брони");
      setDetail(body as Detail);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка карточки брони");
    } finally {
      setDetailLoading(false);
    }
  }

  return <main className="work-shell reception-shell">
    <div className="work-head">
      <div><p className="eyebrow">PMS · ресепшен</p><h1>Брони и проживание</h1><p className="subtitle">Одна бронь — одна строка, даже после переселения. Текущий номер, оплаты, folio и история размещения берутся из Resort Core.</p></div>
      <button className="btn" onClick={load}>Обновить</button>
    </div>

    <div className="reception-controls">
      <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Гость, телефон, номер, бронь…" />
      <select value={filter} onChange={(e) => setFilter(e.target.value as Filter)}>
        <option value="ACTIVE">Активные</option>
        <option value="ARRIVALS_TODAY">Заезды сегодня</option>
        <option value="DEPARTURES_TODAY">Выезды сегодня</option>
        <option value="GUARANTEED">Ожидают заезд</option>
        <option value="CHECKED_IN">Проживают</option>
        <option value="CHECKED_OUT">Выехали</option>
        <option value="ALL">Все</option>
      </select>
      <span>{localDate ? `Дата отеля: ${localDate}` : ""}</span>
    </div>

    {error && <div className="error-box">{error}</div>}
    {loading ? <div className="loading">Загрузка броней…</div> : <div className="reception-list">
      {visible.length === 0 && <div className="empty">По выбранному фильтру броней нет.</div>}
      {visible.map((item) => <article className="reception-card" key={item.id}>
        <div><span className={`status-pill s-${item.status}`}>{statusLabel[item.status] || item.status}</span><strong className="reception-booking">{item.bookingNumber}</strong>{item.has_room_move && <small className="room-move-note">Переселение · {item.schedule_segments} сегм.</small>}</div>
        <div><span className="field-label">Гость</span><b>{item.firstName || "Без имени"}</b>{item.phone && <a href={`tel:${item.phone}`}>{item.phone}</a>}</div>
        <div><span className="field-label">{item.status === "GUARANTEED" ? "Номер на заезд" : item.status === "CHECKED_IN" ? "Текущий номер" : "Последний номер"}</span><b>{item.room_code || "—"}</b><small>{item.room_type_name || ""}</small>{item.room_state && <small>{roomStateLabel[item.room_state] || item.room_state}</small>}</div>
        <div><span className="field-label">Даты</span><b>{item.checkIn} → {item.checkOut}</b><small>{item.adults} взр. · {item.children} дет.</small></div>
        <div className="reception-finance"><span className="field-label">Оплата проживания</span><b>{money(item.paidKgs)} / {money(item.totalKgs)}</b><small className={item.remainingKgs > 0 ? "balance-due" : "balance-ok"}>{item.remainingKgs > 0 ? `Без доп. услуг: остаток ${money(item.remainingKgs)}` : "Проживание оплачено"}</small></div>
        <div className="reception-actions">
          <button className="btn" onClick={() => openDetail(item.id)} disabled={detailLoading}>Карточка</button>
          {item.status === "GUARANTEED" && <button className="btn primary" onClick={() => transition(item, "check-in")} disabled={busy === item.id}>Заезд</button>}
          {item.status === "CHECKED_IN" && <button className="btn primary" onClick={() => transition(item, "check-out")} disabled={busy === item.id}>Выезд</button>}
        </div>
      </article>)}
    </div>}

    {detail && <div className="detail-backdrop" onMouseDown={(e) => { if (e.target === e.currentTarget) setDetail(null); }}>
      <section className="reservation-detail" role="dialog" aria-modal="true">
        <header><div><p className="eyebrow">Карточка брони</p><h2>{detail.reservation.booking_number}</h2><span className={`status-pill s-${detail.reservation.status}`}>{statusLabel[detail.reservation.status] || detail.reservation.status}</span></div><button className="btn" onClick={() => setDetail(null)}>Закрыть</button></header>

        <div className="detail-summary">
          <div><span>Гость</span><strong>{[detail.guest.first_name, detail.guest.last_name].filter(Boolean).join(" ") || "Без имени"}</strong>{detail.guest.phone && <a href={`tel:${detail.guest.phone}`}>{detail.guest.phone}</a>}{detail.guest.email && <small>{detail.guest.email}</small>}</div>
          <div><span>Текущий/рабочий номер</span><strong>{detail.room?.code || "—"}</strong><small>{detail.room?.room_type_name || ""}{detail.room?.area ? ` · ${detail.room.area}` : ""}</small><small>{detail.room?.state ? roomStateLabel[detail.room.state] || detail.room.state : "Назначение не найдено"}</small></div>
          <div><span>Проживание</span><strong>{detail.reservation.check_in} → {detail.reservation.check_out}</strong><small>{detail.reservation.adults} взр. · {detail.reservation.children} дет.</small></div>
          <div><span>Источник</span><strong>{detail.source.channel || "—"}</strong><small>{detail.source.request_id ? `Request ${detail.source.request_id.slice(0, 8)}…` : ""}</small></div>
        </div>

        <section className="detail-section"><h3>График проживания</h3>{detail.schedule.length === 0 ? <p className="detail-muted">У брони нет активного графика размещения.</p> : <div className="stay-schedule-list">{detail.schedule.map((segment) => <div key={segment.inventory_block_id} className={segment.is_working_room ? "working-room-segment" : ""}><strong>№ {segment.room_code}{segment.is_working_room ? " · сейчас" : ""}</strong><span>{segment.start} → {segment.end}</span><small>{segment.room_type_name}{segment.room_state ? ` · ${roomStateLabel[segment.room_state] || segment.room_state}` : ""}</small></div>)}</div>}</section>

        <section className="detail-section"><ReservationFolioPanel reservationId={detail.reservation.id} onChanged={async () => { await load(); await openDetail(detail.reservation.id); }} /></section>

        <section className="detail-section"><h3>Задачи по номерам проживания</h3>{detail.room_tasks.length === 0 ? <p className="detail-muted">Задач по номерам этой брони нет.</p> : <div className="detail-rows">{detail.room_tasks.map((task) => <div key={task.id}><strong>№ {task.room_code} · {task.title}</strong><span>{task.type} · {task.priority}</span><span>{task.status}</span><small>{task.assigned_to_name || "Не назначено"}</small></div>)}</div>}</section>

        <section className="detail-section"><h3>Журнал действий</h3>{detail.audit.length === 0 ? <p className="detail-muted">Записей аудита по брони/заявке нет.</p> : <div className="audit-list">{detail.audit.map((entry) => <div key={entry.id}><strong>{entry.action}</strong><span>{entry.resource} · {entry.source || "—"} · {entry.result}</span><time>{entry.created_at}</time></div>)}</div>}</section>

        {detail.reservation.notes && <section className="detail-section"><h3>Заметка</h3><p className="detail-muted">{detail.reservation.notes}</p></section>}
      </section>
    </div>}
  </main>;
}
