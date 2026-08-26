"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import PMSGridV3 from "./PMSGridV3";

type Block = {
  id: string;
  type: "RESERVATION" | "MAINTENANCE" | "MANUAL";
  start: string;
  end: string;
  reservation_id: string | null;
  reservation_status: string | null;
  guest_name: string | null;
  guest_phone: string | null;
  booking_number: string | null;
  reason: string | null;
};

type Room = {
  id: string;
  code: string;
  room_type_code: string;
  room_type_name: string;
  building_or_zone: string | null;
  floor: string | null;
  operational_state: "UNKNOWN" | "CLEAN" | "DIRTY" | "IN_INSPECTION" | "TECH_BLOCK";
  blocks: Block[];
};

type GridResponse = { property: string; start: string; end: string; rooms: Room[] };

type ReceptionItem = {
  id: string;
  bookingNumber: string;
  status: string;
  checkIn: string;
  checkOut: string;
  totalKgs: number;
  paidKgs: number;
  remainingKgs: number;
  firstName?: string | null;
  phone?: string | null;
  room_code?: string | null;
  room_type_name?: string | null;
};

type GroupMode = "BUILDING" | "FLOOR" | "CATEGORY";
type SortMode = "LOAD" | "FREE" | "ATTENTION" | "NAME";
type FinanceState = "loading" | "ready" | "partial" | "error";

const money = (value: number) => new Intl.NumberFormat("ru-RU").format(value);

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

function shortDate(value: string) {
  const [y, m, d] = value.split("-").map(Number);
  const date = new Date(y, m - 1, d);
  return new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "short", weekday: "short" }).format(date);
}

function blockCovers(block: Block, day: string) {
  return block.start <= day && day < block.end;
}

function attentionWeight(state: Room["operational_state"]) {
  if (state === "TECH_BLOCK") return 4;
  if (state === "DIRTY") return 3;
  if (state === "IN_INSPECTION") return 2;
  if (state === "UNKNOWN") return 1;
  return 0;
}

function stateLabel(state: Room["operational_state"]) {
  return { CLEAN: "Готов", DIRTY: "Нужна уборка", IN_INSPECTION: "На проверке", TECH_BLOCK: "Техблок", UNKNOWN: "Без статуса" }[state];
}

export default function PMSGridV4() {
  const [grid, setGrid] = useState<GridResponse | null>(null);
  const [finance, setFinance] = useState<ReceptionItem[]>([]);
  const [financeState, setFinanceState] = useState<FinanceState>("loading");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [groupMode, setGroupMode] = useState<GroupMode>("BUILDING");
  const [sortMode, setSortMode] = useState<SortMode>("LOAD");
  const [deckOpen, setDeckOpen] = useState(true);

  const today = localDate(new Date());
  const horizon = useMemo(() => Array.from({ length: 14 }, (_, index) => localDate(addDays(new Date(), index))), []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const end = localDate(addDays(new Date(), 14));
    try {
      const [gridResponse, financeResponse] = await Promise.all([
        fetch(`/core/api/v1/pms/grid?${new URLSearchParams({ start: today, end })}`, { cache: "no-store" }),
        fetch("/core/api/v1/admin/reception/reservations?limit=500", { cache: "no-store" }),
      ]);
      const gridBody = await gridResponse.json().catch(() => ({}));
      if (!gridResponse.ok) throw new Error(typeof gridBody.detail === "string" ? gridBody.detail : `Grid HTTP ${gridResponse.status}`);
      setGrid(gridBody as GridResponse);

      const financeBody = await financeResponse.json().catch(() => ({}));
      if (!financeResponse.ok || !Array.isArray(financeBody.items)) {
        setFinance([]);
        setFinanceState("error");
      } else if (financeBody.items.length >= 500) {
        setFinance(financeBody.items as ReceptionItem[]);
        setFinanceState("partial");
      } else {
        setFinance(financeBody.items as ReceptionItem[]);
        setFinanceState("ready");
      }
    } catch (cause) {
      setGrid(null);
      setFinance([]);
      setFinanceState("error");
      setError(cause instanceof Error ? cause.message : "Не удалось загрузить Command Deck");
    } finally {
      setLoading(false);
    }
  }, [today]);

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => { void load(); }, 60_000);
    return () => window.clearInterval(timer);
  }, [load]);

  const heatmap = useMemo(() => horizon.map((day) => {
    const rooms = grid?.rooms || [];
    const reservationRooms = rooms.filter((room) => room.blocks.some((block) => block.type === "RESERVATION" && blockCovers(block, day))).length;
    const serviceRooms = rooms.filter((room) => room.operational_state === "TECH_BLOCK" || room.blocks.some((block) => block.type !== "RESERVATION" && blockCovers(block, day))).length;
    const unavailable = rooms.filter((room) => room.operational_state === "TECH_BLOCK" || room.blocks.some((block) => blockCovers(block, day))).length;
    const free = Math.max(0, rooms.length - unavailable);
    const loadPct = rooms.length ? Math.round((unavailable / rooms.length) * 100) : 0;
    return { day, reservationRooms, serviceRooms, free, loadPct };
  }), [grid, horizon]);

  const groups = useMemo(() => {
    const rooms = grid?.rooms || [];
    const map = new Map<string, Room[]>();
    rooms.forEach((room) => {
      const key = groupMode === "BUILDING" ? room.building_or_zone || "Без корпуса" : groupMode === "FLOOR" ? room.floor ? `${room.floor} этаж` : "Этаж не указан" : room.room_type_name;
      map.set(key, [...(map.get(key) || []), room]);
    });
    const items = Array.from(map.entries()).map(([name, groupRooms]) => {
      const occupied = groupRooms.filter((room) => room.blocks.some((block) => block.type === "RESERVATION" && blockCovers(block, today))).length;
      const unavailable = groupRooms.filter((room) => room.operational_state === "TECH_BLOCK" || room.blocks.some((block) => blockCovers(block, today))).length;
      const attention = groupRooms.filter((room) => attentionWeight(room.operational_state) > 0).length;
      const free = Math.max(0, groupRooms.length - unavailable);
      return { name, total: groupRooms.length, occupied, free, attention, load: groupRooms.length ? Math.round((unavailable / groupRooms.length) * 100) : 0 };
    });
    items.sort((a, b) => sortMode === "LOAD" ? b.load - a.load : sortMode === "FREE" ? b.free - a.free : sortMode === "ATTENTION" ? b.attention - a.attention : a.name.localeCompare(b.name, "ru"));
    return items;
  }, [grid, groupMode, sortMode, today]);

  const attention = useMemo(() => (grid?.rooms || [])
    .filter((room) => attentionWeight(room.operational_state) > 0)
    .sort((a, b) => attentionWeight(b.operational_state) - attentionWeight(a.operational_state) || a.code.localeCompare(b.code, "ru"))
    .slice(0, 12), [grid]);

  const debtQueue = useMemo(() => financeState === "ready" ? finance
    .filter((item) => ["GUARANTEED", "CHECKED_IN"].includes(item.status) && item.remainingKgs > 0)
    .sort((a, b) => b.remainingKgs - a.remainingKgs)
    .slice(0, 10) : [], [finance, financeState]);

  const readiness = useMemo(() => {
    const rooms = grid?.rooms || [];
    const ready = rooms.filter((room) => room.operational_state === "CLEAN").length;
    return rooms.length ? Math.round((ready / rooms.length) * 100) : 0;
  }, [grid]);

  const peak = useMemo(() => heatmap.reduce((best, item) => item.loadPct > best.loadPct ? item : best, heatmap[0] || { day: today, loadPct: 0, free: 0, reservationRooms: 0, serviceRooms: 0 }), [heatmap, today]);

  function jumpToBoard() {
    document.getElementById("mega-grid-v3")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return <>
    <section className={`v4-command-deck ${deckOpen ? "is-open" : "is-collapsed"}`}>
      <header className="v4-deck-head">
        <div><p className="eyebrow">PMS Intelligence · V4</p><h2>Command Deck</h2><span>Сводка поверх мега-шахматки: загрузка, готовность фонда, группы, долги и операционные исключения.</span></div>
        <div className="v4-deck-actions"><button className="btn" onClick={() => void load()}>↻ Обновить</button><button className="btn" onClick={jumpToBoard}>К шахматке ↓</button><button className="v4-collapse" onClick={() => setDeckOpen((value) => !value)}>{deckOpen ? "Свернуть" : "Развернуть"}</button></div>
      </header>

      {deckOpen && <>
        {error && <div className="v4-error">{error}</div>}
        <section className="v4-pulse-grid">
          <article><span>Фонд</span><strong>{grid?.rooms.length ?? "—"}</strong><small>номеров в Core</small></article>
          <article className="is-green"><span>Готовность фонда</span><strong>{loading ? "…" : `${readiness}%`}</strong><small>CLEAN сейчас</small></article>
          <article className="is-blue"><span>Пик 14 дней</span><strong>{loading ? "…" : `${peak.loadPct}%`}</strong><small>{shortDate(peak.day)}</small></article>
          <article className="is-red"><span>Требуют внимания</span><strong>{loading ? "…" : attention.length}</strong><small>первые 12 исключений</small></article>
          <article className={financeState === "ready" ? "is-amber" : "is-muted"}><span>Финансовая очередь</span><strong>{financeState === "ready" ? debtQueue.length : "—"}</strong><small>{financeState === "ready" ? "крупнейшие остатки" : financeState === "partial" ? "выборка неполная" : "финансы недоступны"}</small></article>
        </section>

        <section className="v4-heatmap-card">
          <div className="v4-section-head"><div><strong>Occupancy heatmap · 14 дней</strong><span>Недоступность = активная бронь/блок или текущий TECH_BLOCK.</span></div><div className="v4-heat-legend"><i className="l1" />низкая <i className="l2" />средняя <i className="l3" />высокая</div></div>
          <div className="v4-heatmap">{heatmap.map((item) => <article key={item.day} className={item.loadPct >= 80 ? "heat-3" : item.loadPct >= 55 ? "heat-2" : "heat-1"} title={`${item.day}: занято/заблокировано ${item.loadPct}%, свободно ${item.free}`}><span>{shortDate(item.day)}</span><strong>{item.loadPct}%</strong><small>{item.free} свободно</small><em>{item.reservationRooms} бронь · {item.serviceRooms} блок</em></article>)}</div>
        </section>

        <section className="v4-workbench">
          <div className="v4-groups-card">
            <div className="v4-section-head"><div><strong>Группировка фонда</strong><span>Смотрите нагрузку по структуре отеля.</span></div><div className="v4-segmented"><button className={groupMode === "BUILDING" ? "active" : ""} onClick={() => setGroupMode("BUILDING")}>Корпус</button><button className={groupMode === "FLOOR" ? "active" : ""} onClick={() => setGroupMode("FLOOR")}>Этаж</button><button className={groupMode === "CATEGORY" ? "active" : ""} onClick={() => setGroupMode("CATEGORY")}>Категория</button></div></div>
            <div className="v4-sort-row"><span>Сортировка</span><select value={sortMode} onChange={(event) => setSortMode(event.target.value as SortMode)}><option value="LOAD">По загрузке</option><option value="FREE">По свободным</option><option value="ATTENTION">По проблемам</option><option value="NAME">По названию</option></select></div>
            <div className="v4-group-list">{groups.map((group) => <article key={group.name}><div><strong>{group.name}</strong><span>{group.total} номеров · {group.free} свободно · {group.attention} внимание</span></div><div className="v4-load"><i style={{ width: `${group.load}%` }} /><b>{group.load}%</b></div></article>)}</div>
          </div>

          <div className="v4-attention-card">
            <div className="v4-section-head"><div><strong>Операционная очередь</strong><span>Самые срочные номера по состоянию фонда.</span></div><b>{attention.length}</b></div>
            <div className="v4-attention-list">{attention.length === 0 ? <p>Операционных исключений нет.</p> : attention.map((room) => <article key={room.id}><div className={`v4-state state-${room.operational_state.toLowerCase()}`}>{stateLabel(room.operational_state)}</div><div><strong>№ {room.code}</strong><span>{room.room_type_name}</span><small>{[room.building_or_zone, room.floor].filter(Boolean).join(" · ") || "—"}</small></div></article>)}</div>
          </div>

          <div className="v4-money-card">
            <div className="v4-section-head"><div><strong>Финансовая очередь</strong><span>Только подтверждённые данные reception endpoint.</span></div><b>{financeState === "ready" ? debtQueue.length : "—"}</b></div>
            {financeState !== "ready" ? <div className="v4-finance-unknown"><strong>Не показываю ложный рейтинг долгов</strong><span>{financeState === "partial" ? "Endpoint вернул 500 записей: глобальная выборка потенциально неполная." : "Финансовая выборка сейчас недоступна."}</span></div> : <div className="v4-money-list">{debtQueue.length === 0 ? <p>Активных броней с остатком нет.</p> : debtQueue.map((item) => <article key={item.id}><div><strong>{item.firstName || item.bookingNumber}</strong><span>{item.bookingNumber} · № {item.room_code || "—"}</span></div><b>{money(item.remainingKgs)} сом</b><small>{money(item.paidKgs)} / {money(item.totalKgs)}</small></article>)}</div>}
          </div>
        </section>
      </>}
    </section>

    <div id="mega-grid-v3"><PMSGridV3 /></div>
  </>;
}
