"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type Block = {
  id: string;
  type: "RESERVATION" | "MAINTENANCE" | "MANUAL";
  start: string;
  end: string;
  reason: string | null;
  reservation_id: string | null;
  booking_number: string | null;
  reservation_status: string | null;
  guest_name: string | null;
  guest_phone: string | null;
};

type Room = {
  id: string;
  code: string;
  room_type_name: string;
  building_or_zone: string | null;
  floor: string | null;
  operational_state: "UNKNOWN" | "CLEAN" | "DIRTY" | "IN_INSPECTION" | "TECH_BLOCK";
  blocks: Block[];
};

type GridResponse = { rooms: Room[] };

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
};

type Detail = {
  reservation: { id: string; booking_number: string; status: string; check_in: string; check_out: string; adults: number; children: number; total_kgs: number; notes?: string | null };
  guest: { first_name?: string | null; last_name?: string | null; phone?: string | null; email?: string | null };
  source: { channel?: string | null };
  room: { code: string; state: string; room_type_name?: string | null; area?: string | null } | null;
  finance: { total_kgs: number; paid_kgs: number; remaining_kgs: number };
};

type Conflict = { key: string; severity: "critical" | "warning"; title: string; description: string; roomCode?: string; reservationId?: string };
type FinanceState = "loading" | "ready" | "partial" | "error";

const money = (value: number) => `${new Intl.NumberFormat("ru-RU").format(value)} сом`;
const roomStateLabel: Record<string, string> = { CLEAN: "Готов", DIRTY: "Нужна уборка", IN_INSPECTION: "На проверке", TECH_BLOCK: "Ремонт", UNKNOWN: "Без статуса" };

function localDate(value: Date) {
  const y = value.getFullYear();
  const m = String(value.getMonth() + 1).padStart(2, "0");
  const d = String(value.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function addDays(value: Date, amount: number) {
  const next = new Date(value.getFullYear(), value.getMonth(), value.getDate());
  next.setDate(next.getDate() + amount);
  return next;
}

function sortBlocks<T extends Pick<Block, "start" | "end">>(blocks: T[]) {
  return [...blocks].sort((a, b) => a.start.localeCompare(b.start) || a.end.localeCompare(b.end));
}

export default function PMSReceptionCockpit() {
  const [grid, setGrid] = useState<GridResponse | null>(null);
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [financeState, setFinanceState] = useState<FinanceState>("loading");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [acknowledged, setAcknowledged] = useState<string[]>([]);

  const today = localDate(new Date());
  const tomorrow = localDate(addDays(new Date(), 1));
  const horizonEnd = localDate(addDays(new Date(), 15));

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ start: localDate(addDays(new Date(), -1)), end: horizonEnd });
      const [gridResponse, receptionResponse] = await Promise.all([
        fetch(`/core/api/v1/pms/grid?${params}`, { cache: "no-store" }),
        fetch("/core/api/v1/admin/reception/reservations?limit=500", { cache: "no-store" }),
      ]);
      const gridBody = await gridResponse.json().catch(() => ({}));
      if (!gridResponse.ok) throw new Error(typeof gridBody.detail === "string" ? gridBody.detail : `Grid HTTP ${gridResponse.status}`);
      setGrid(gridBody as GridResponse);

      const receptionBody = await receptionResponse.json().catch(() => ({}));
      if (!receptionResponse.ok || !Array.isArray(receptionBody.items)) {
        setReservations([]);
        setFinanceState("error");
      } else {
        const items = receptionBody.items as Reservation[];
        setReservations(items);
        setFinanceState(items.length >= 500 ? "partial" : "ready");
      }
    } catch (cause) {
      setGrid(null);
      setReservations([]);
      setFinanceState("error");
      setError(cause instanceof Error ? cause.message : "Не удалось загрузить Reception Cockpit");
    } finally {
      setLoading(false);
    }
  }, [horizonEnd]);

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(), 45_000);
    return () => window.clearInterval(timer);
  }, [load]);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(`resort-pms-v6-ack-${today}`);
      if (raw) setAcknowledged(JSON.parse(raw));
    } catch { /* local shift marks are optional */ }
  }, [today]);

  const reservationRoom = useMemo(() => {
    const map = new Map<string, { room: Room; block: Block }>();
    grid?.rooms.forEach((room) => room.blocks.forEach((block) => {
      if (!block.reservation_id || block.type !== "RESERVATION") return;
      const current = map.get(block.reservation_id);
      const coversToday = block.start <= today && today < block.end;
      const currentCovers = current ? current.block.start <= today && today < current.block.end : false;
      if (!current || (coversToday && !currentCovers) || (!currentCovers && block.start < current.block.start)) map.set(block.reservation_id, { room, block });
    }));
    return map;
  }, [grid, today]);

  const arrivalsToday = useMemo(() => reservations.filter((item) => item.status === "GUARANTEED" && item.checkIn === today), [reservations, today]);
  const arrivalsTomorrow = useMemo(() => reservations.filter((item) => item.status === "GUARANTEED" && item.checkIn === tomorrow), [reservations, tomorrow]);
  const departuresToday = useMemo(() => reservations.filter((item) => item.status === "CHECKED_IN" && item.checkOut === today), [reservations, today]);
  const departuresTomorrow = useMemo(() => reservations.filter((item) => item.status === "CHECKED_IN" && item.checkOut === tomorrow), [reservations, tomorrow]);
  const overdue = useMemo(() => reservations.filter((item) => item.status === "CHECKED_IN" && item.checkOut < today), [reservations, today]);

  const notReadyArrivals = useMemo(() => arrivalsToday.filter((item) => {
    const linked = reservationRoom.get(item.id);
    const state = linked?.room.operational_state || item.room_state;
    return !linked || state !== "CLEAN";
  }), [arrivalsToday, reservationRoom]);

  const debtQueue = useMemo(() => financeState === "ready" ? reservations
    .filter((item) => ["GUARANTEED", "CHECKED_IN"].includes(item.status) && item.remainingKgs > 0)
    .sort((a, b) => b.remainingKgs - a.remainingKgs) : [], [reservations, financeState]);

  const conflicts = useMemo(() => {
    const result: Conflict[] = [];
    const segments = new Map<string, Array<{ room: Room; block: Block }>>();

    grid?.rooms.forEach((room) => {
      const blocks = sortBlocks(room.blocks);
      for (let index = 1; index < blocks.length; index += 1) {
        const previous = blocks[index - 1];
        const current = blocks[index];
        if (current.start < previous.end) {
          result.push({
            key: `room-overlap-${room.id}-${previous.id}-${current.id}`,
            severity: "critical",
            title: `Пересечение блоков · № ${room.code}`,
            description: `${previous.start} → ${previous.end} пересекается с ${current.start} → ${current.end}`,
            roomCode: room.code,
            reservationId: current.reservation_id || previous.reservation_id || undefined,
          });
        }
      }
      room.blocks.forEach((block) => {
        if (!block.reservation_id || block.type !== "RESERVATION") return;
        segments.set(block.reservation_id, [...(segments.get(block.reservation_id) || []), { room, block }]);
      });
    });

    segments.forEach((items, reservationId) => {
      const ordered = [...items].sort((a, b) => a.block.start.localeCompare(b.block.start));
      for (let index = 1; index < ordered.length; index += 1) {
        const previous = ordered[index - 1];
        const current = ordered[index];
        if (current.block.start < previous.block.end) {
          result.push({
            key: `reservation-overlap-${reservationId}-${index}`,
            severity: "critical",
            title: "Перекрытие графика одной брони",
            description: `№ ${previous.room.code} и № ${current.room.code}: ${current.block.start} начинается до завершения предыдущего сегмента ${previous.block.end}.`,
            reservationId,
          });
        } else if (current.block.start > previous.block.end) {
          result.push({
            key: `reservation-gap-${reservationId}-${index}`,
            severity: "warning",
            title: "Разрыв в графике проживания",
            description: `Между № ${previous.room.code} и № ${current.room.code} есть разрыв ${previous.block.end} → ${current.block.start}.`,
            reservationId,
          });
        }
      }
    });

    arrivalsToday.forEach((item) => {
      const linked = reservationRoom.get(item.id);
      if (!linked) {
        result.push({ key: `arrival-no-room-${item.id}`, severity: "critical", title: "Заезд сегодня без рабочего номера", description: `${item.firstName || item.bookingNumber} · ${item.bookingNumber}`, reservationId: item.id });
      } else if (linked.room.operational_state !== "CLEAN") {
        result.push({ key: `arrival-not-ready-${item.id}`, severity: "critical", title: `Номер № ${linked.room.code} не готов к заезду`, description: `${item.firstName || item.bookingNumber} · ${roomStateLabel[linked.room.operational_state] || linked.room.operational_state}`, roomCode: linked.room.code, reservationId: item.id });
      }
    });

    overdue.forEach((item) => result.push({ key: `overdue-${item.id}`, severity: "warning", title: "Просроченный выезд", description: `${item.firstName || item.bookingNumber} · плановый выезд ${item.checkOut}`, reservationId: item.id }));
    return result;
  }, [grid, arrivalsToday, overdue, reservationRoom]);

  const activeConflictCount = conflicts.filter((item) => !acknowledged.includes(item.key)).length;

  function acknowledge(key: string) {
    const next = acknowledged.includes(key) ? acknowledged.filter((item) => item !== key) : [...acknowledged, key];
    setAcknowledged(next);
    try { window.localStorage.setItem(`resort-pms-v6-ack-${today}`, JSON.stringify(next)); } catch { /* optional station-local mark */ }
  }

  async function openDetail(id: string) {
    setDetailLoading(true);
    setError(null);
    try {
      const response = await fetch(`/core/api/v1/admin/booking/reservations/${id}`, { cache: "no-store" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Не удалось открыть карточку брони");
      setDetail(body as Detail);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Ошибка карточки брони");
    } finally {
      setDetailLoading(false);
    }
  }

  async function transition(item: Reservation, action: "check-in" | "check-out") {
    const label = action === "check-in" ? "заезд" : "выезд";
    if (!window.confirm(`Подтвердить ${label}: ${item.firstName || item.bookingNumber} · ${item.bookingNumber}?`)) return;
    setBusy(item.id);
    setError(null);
    try {
      const response = await fetch(`/core/api/v1/admin/stays/reservations/${item.id}/${action}`, { method: "POST" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = typeof body.detail === "string" ? body.detail : body.detail?.code || `HTTP ${response.status}`;
        throw new Error(String(detail));
      }
      setDetail(null);
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : `Не удалось оформить ${label}`);
    } finally {
      setBusy(null);
    }
  }

  const shiftQueue = useMemo(() => {
    const seen = new Set<string>();
    const items: Array<{ item: Reservation; kind: string; tone: string }> = [];
    overdue.forEach((item) => { if (!seen.has(item.id)) { seen.add(item.id); items.push({ item, kind: "Просроченный выезд", tone: "critical" }); } });
    notReadyArrivals.forEach((item) => { if (!seen.has(item.id)) { seen.add(item.id); items.push({ item, kind: "Заезд · номер не готов", tone: "critical" }); } });
    departuresToday.forEach((item) => { if (!seen.has(item.id)) { seen.add(item.id); items.push({ item, kind: "Выезд сегодня", tone: "warning" }); } });
    arrivalsToday.forEach((item) => { if (!seen.has(item.id)) { seen.add(item.id); items.push({ item, kind: "Заезд сегодня", tone: "normal" }); } });
    return items;
  }, [overdue, notReadyArrivals, departuresToday, arrivalsToday]);

  return <section className="v6-cockpit">
    <header className="v6-head">
      <div><p className="eyebrow">Reception Cockpit · V6</p><h2>Смена ресепшена</h2><span>Заезды, выезды, readiness, долги и конфликтные состояния из Resort Core.</span></div>
      <div className="v6-head-actions"><span className={error ? "v6-status error" : "v6-status live"}>{error ? "Core warning" : loading ? "Обновление…" : `Смена · ${today}`}</span><button className="btn" onClick={() => void load()}>↻ Обновить</button></div>
    </header>

    {error && <div className="v6-error">{error}</div>}

    <div className="v6-kpis">
      <article><span>Заезды сегодня</span><strong>{arrivalsToday.length}</strong><small>{notReadyArrivals.length ? `${notReadyArrivals.length} не готовы` : "готовность проверена"}</small></article>
      <article><span>Выезды сегодня</span><strong>{departuresToday.length}</strong><small>{overdue.length ? `+ ${overdue.length} просрочено` : "без просрочек"}</small></article>
      <article className={notReadyArrivals.length ? "danger" : "ok"}><span>Не готово к заезду</span><strong>{notReadyArrivals.length}</strong><small>статус номера ≠ CLEAN</small></article>
      <article className={activeConflictCount ? "danger" : "ok"}><span>Conflict Center</span><strong>{activeConflictCount}</strong><small>{conflicts.length - activeConflictCount} принято в работу</small></article>
      <article className={financeState === "ready" ? "money" : "muted"}><span>Активных с долгом</span><strong>{financeState === "ready" ? debtQueue.length : "—"}</strong><small>{financeState === "partial" ? "выборка неполная" : financeState === "error" ? "финансы недоступны" : financeState === "loading" ? "загрузка" : debtQueue.length ? money(debtQueue.reduce((sum, item) => sum + item.remainingKgs, 0)) : "остатков нет"}</small></article>
      <article><span>Следующие 24ч</span><strong>{arrivalsTomorrow.length + departuresTomorrow.length}</strong><small>{arrivalsTomorrow.length} заезд · {departuresTomorrow.length} выезд</small></article>
    </div>

    <div className="v6-workbench">
      <section className="v6-shift-card">
        <div className="v6-section-head"><div><strong>Очередь смены</strong><span>Сначала просрочки и неподготовленные заезды.</span></div><b>{shiftQueue.length}</b></div>
        <div className="v6-shift-list">{shiftQueue.length === 0 ? <p className="v6-empty">На текущую смену срочных гостевых событий нет.</p> : shiftQueue.map(({ item, kind, tone }) => {
          const linked = reservationRoom.get(item.id);
          const roomCode = linked?.room.code || item.room_code || "—";
          const roomState = linked?.room.operational_state || item.room_state || "UNKNOWN";
          return <article key={`${kind}-${item.id}`} className={`tone-${tone}`}>
            <div className="v6-event-main"><span className="v6-event-kind">{kind}</span><strong>{item.firstName || "Гость"}</strong><small>{item.bookingNumber} · № {roomCode} · {roomStateLabel[roomState] || roomState}</small></div>
            <div className="v6-event-finance">{financeState === "ready" && <><span>Остаток</span><strong className={item.remainingKgs > 0 ? "due" : "paid"}>{money(Math.max(0, item.remainingKgs))}</strong></>}</div>
            <div className="v6-event-actions"><button onClick={() => void openDetail(item.id)} disabled={detailLoading}>Карточка</button>{item.phone && <a href={`tel:${item.phone}`}>Позвонить</a>}{item.status === "GUARANTEED" && item.checkIn === today && <button className="primary" onClick={() => void transition(item, "check-in")} disabled={busy === item.id}>Заезд</button>}{item.status === "CHECKED_IN" && item.checkOut <= today && <button className="primary" onClick={() => void transition(item, "check-out")} disabled={busy === item.id}>Выезд</button>}</div>
          </article>;
        })}</div>
      </section>

      <section className="v6-conflict-card">
        <div className="v6-section-head"><div><strong>Conflict Center</strong><span>Overlap/gap, просрочки и readiness.</span></div><b>{activeConflictCount}</b></div>
        <div className="v6-conflict-list">{conflicts.length === 0 ? <p className="v6-empty">Конфликтов не обнаружено в текущем горизонте.</p> : conflicts.slice(0, 16).map((conflict) => {
          const ack = acknowledged.includes(conflict.key);
          return <article key={conflict.key} className={`${conflict.severity} ${ack ? "ack" : ""}`}><button className="v6-ack" onClick={() => acknowledge(conflict.key)} title="Локальная отметка этой рабочей станции">{ack ? "✓" : "!"}</button><div><strong>{conflict.title}</strong><span>{conflict.description}</span></div>{conflict.reservationId && <button onClick={() => void openDetail(conflict.reservationId!)}>Бронь</button>}</article>;
        })}</div>
        <p className="v6-local-note">✓ — локальная отметка «принято в работу» на этой станции; она не меняет Resort Core и не скрывает сам конфликт.</p>
      </section>

      <section className="v6-next-card">
        <div className="v6-section-head"><div><strong>Следующие 24 часа</strong><span>Подготовка следующей смены.</span></div><b>{arrivalsTomorrow.length + departuresTomorrow.length}</b></div>
        <div className="v6-next-block"><span>Заезды завтра</span>{arrivalsTomorrow.slice(0, 8).map((item) => <button key={item.id} onClick={() => void openDetail(item.id)}><strong>{item.firstName || item.bookingNumber}</strong><small>{item.bookingNumber} · № {item.room_code || "—"}</small></button>)}{arrivalsTomorrow.length === 0 && <em>Нет</em>}</div>
        <div className="v6-next-block"><span>Выезды завтра</span>{departuresTomorrow.slice(0, 8).map((item) => <button key={item.id} onClick={() => void openDetail(item.id)}><strong>{item.firstName || item.bookingNumber}</strong><small>{item.bookingNumber} · № {item.room_code || "—"}</small></button>)}{departuresTomorrow.length === 0 && <em>Нет</em>}</div>
      </section>
    </div>

    {detail && <div className="v6-detail-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setDetail(null); }}>
      <section className="v6-detail" role="dialog" aria-modal="true">
        <header><div><p className="eyebrow">Quick Guest Card</p><h3>{detail.guest.first_name || "Гость"} · {detail.reservation.booking_number}</h3></div><button className="btn" onClick={() => setDetail(null)}>Закрыть</button></header>
        <div className="v6-detail-grid"><div><span>Телефон</span><strong>{detail.guest.phone || "—"}</strong>{detail.guest.phone && <a href={`tel:${detail.guest.phone}`}>Позвонить</a>}</div><div><span>Номер</span><strong>№ {detail.room?.code || "—"}</strong><small>{detail.room?.room_type_name || ""} · {detail.room?.state ? roomStateLabel[detail.room.state] || detail.room.state : ""}</small></div><div><span>Даты</span><strong>{detail.reservation.check_in} → {detail.reservation.check_out}</strong><small>{detail.reservation.adults} взр. · {detail.reservation.children} дет.</small></div><div><span>Источник</span><strong>{detail.source.channel || "—"}</strong></div></div>
        <div className="v6-detail-finance"><div><span>Стоимость</span><strong>{money(detail.finance.total_kgs)}</strong></div><div><span>Оплачено</span><strong>{money(detail.finance.paid_kgs)}</strong></div><div><span>Остаток</span><strong className={detail.finance.remaining_kgs > 0 ? "due" : "paid"}>{money(detail.finance.remaining_kgs)}</strong></div></div>
        {detail.reservation.notes && <div className="v6-detail-notes"><span>Примечание</span><p>{detail.reservation.notes}</p></div>}
      </section>
    </div>}
  </section>;
}
