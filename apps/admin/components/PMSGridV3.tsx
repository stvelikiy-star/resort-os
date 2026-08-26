"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import ChessboardReservationModal from "./ChessboardReservationModal";
import RoomDetailModal from "./RoomDetailModal";

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
  name: string;
  room_type_code: string;
  room_type_name: string;
  building_or_zone: string | null;
  floor: string | null;
  beds_raw: string | null;
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

type FinanceMode = "ALL" | "PAID" | "PARTIAL" | "UNPAID" | "DEBT";
type FinanceState = "loading" | "ready" | "partial" | "error";
type OccupancyMode = "ALL" | "FREE" | "OCCUPIED" | "BLOCKED";
type DailyMode = "ALL" | "ARRIVALS" | "DEPARTURES" | "IN_HOUSE" | "FREE_TODAY" | "DEBT" | "ATTENTION";
type Density = "COMPACT" | "COMFORTABLE";
type BlockMode = "ALL" | "RESERVATION" | "MAINTENANCE" | "MANUAL";

type Filters = {
  search: string;
  roomType: string;
  building: string;
  floor: string;
  state: string;
  reservationStatus: string;
  finance: FinanceMode;
  occupancy: OccupancyMode;
  blockType: BlockMode;
  daily: DailyMode;
};

type SavedView = { id: string; name: string; filters: Filters; windowDays: number; density: Density };

type ReservationOpen = { id: string; targetRoomId?: string; initialCheckIn?: string; initialCheckOut?: string };

type RealtimeMessage = { type: "pms.grid.snapshot" | "heartbeat"; data?: GridResponse };

const ROOM_STATE_LABELS: Record<Room["operational_state"], string> = {
  UNKNOWN: "Без статуса",
  CLEAN: "Готов",
  DIRTY: "Уборка",
  IN_INSPECTION: "Проверка",
  TECH_BLOCK: "Ремонт",
};

const RESERVATION_STATUS_LABELS: Record<string, string> = {
  GUARANTEED: "Ожидает заезд",
  CHECKED_IN: "Проживает",
  CHECKED_OUT: "Выехал",
  CANCELLED: "Отменена",
  NO_SHOW: "Не заехал",
};

const QUICK_VIEWS: Array<{ key: DailyMode; label: string; hint: string }> = [
  { key: "ALL", label: "Все", hint: "Весь фонд" },
  { key: "ARRIVALS", label: "Заезды", hint: "Сегодня" },
  { key: "DEPARTURES", label: "Выезды", hint: "Сегодня" },
  { key: "IN_HOUSE", label: "Проживают", hint: "Сейчас" },
  { key: "FREE_TODAY", label: "Свободные", hint: "Сегодня" },
  { key: "DEBT", label: "С долгом", hint: "Оплата" },
  { key: "ATTENTION", label: "Внимание", hint: "Уборка / ремонт" },
];

const DEFAULT_FILTERS: Filters = {
  search: "",
  roomType: "ALL",
  building: "ALL",
  floor: "ALL",
  state: "ALL",
  reservationStatus: "ALL",
  finance: "ALL",
  occupancy: "ALL",
  blockType: "ALL",
  daily: "ALL",
};

const money = (value: number) => new Intl.NumberFormat("ru-RU").format(value);

function localDateString(value: Date) {
  const y = value.getFullYear();
  const m = String(value.getMonth() + 1).padStart(2, "0");
  const d = String(value.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function parseDateOnly(value: string) {
  const [y, m, d] = value.split("-").map(Number);
  return new Date(y, m - 1, d);
}

function addDays(value: Date, amount: number) {
  const next = new Date(value.getFullYear(), value.getMonth(), value.getDate());
  next.setDate(next.getDate() + amount);
  return next;
}

function shiftDate(value: string, amount: number) {
  const [y, m, d] = value.split("-").map(Number);
  const next = new Date(Date.UTC(y, m - 1, d + amount));
  return next.toISOString().slice(0, 10);
}

function dayOrdinal(value: string) {
  const [y, m, d] = value.split("-").map(Number);
  return Math.floor(Date.UTC(y, m - 1, d) / 86400000);
}

function daysBetween(left: string, right: string) { return dayOrdinal(right) - dayOrdinal(left); }

function dateRange(start: Date, count: number) { return Array.from({ length: count }, (_, index) => addDays(start, index)); }

function websocketBase() {
  const configured = process.env.NEXT_PUBLIC_CORE_WS_URL?.replace(/\/$/, "");
  if (configured) return configured;
  if (typeof window === "undefined") return "";
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.hostname;
  const port = window.location.port === "3001" ? "8000" : window.location.port;
  return `${protocol}//${host}${port ? `:${port}` : ""}`;
}

function financeClass(item?: ReceptionItem) {
  if (!item) return "unknown";
  if (item.remainingKgs <= 0) return "paid";
  if (item.paidKgs > 0) return "partial";
  return "unpaid";
}

function financeMatches(mode: FinanceMode, item?: ReceptionItem) {
  if (mode === "ALL") return true;
  if (!item) return false;
  if (mode === "PAID") return item.remainingKgs <= 0;
  if (mode === "PARTIAL") return item.paidKgs > 0 && item.remainingKgs > 0;
  if (mode === "UNPAID") return item.paidKgs <= 0 && item.remainingKgs > 0;
  return item.remainingKgs > 0;
}

export default function PMSGridV3() {
  const [start, setStart] = useState(() => { const now = new Date(); return new Date(now.getFullYear(), now.getMonth(), now.getDate()); });
  const [windowDays, setWindowDays] = useState(14);
  const [density, setDensity] = useState<Density>("COMFORTABLE");
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [advancedOpen, setAdvancedOpen] = useState(true);
  const [data, setData] = useState<GridResponse | null>(null);
  const [financeItems, setFinanceItems] = useState<ReceptionItem[]>([]);
  const [financeState, setFinanceState] = useState<FinanceState>("loading");
  const [financeError, setFinanceError] = useState<string | null>(null);
  const [financeUpdatedAt, setFinanceUpdatedAt] = useState<Date | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [realtime, setRealtime] = useState<"connecting" | "live" | "offline">("connecting");
  const [refreshToken, setRefreshToken] = useState(0);
  const [selectedRoomId, setSelectedRoomId] = useState<string | null>(null);
  const [selectedReservation, setSelectedReservation] = useState<ReservationOpen | null>(null);
  const [draggingReservationId, setDraggingReservationId] = useState<string | null>(null);
  const [dropRoomId, setDropRoomId] = useState<string | null>(null);
  const [dropDate, setDropDate] = useState<string | null>(null);
  const [savedViews, setSavedViews] = useState<SavedView[]>([]);

  const today = localDateString(new Date());
  const days = useMemo(() => dateRange(start, windowDays), [start, windowDays]);
  const end = useMemo(() => addDays(start, windowDays), [start, windowDays]);
  const startIso = localDateString(start);
  const endIso = localDateString(end);
  const dayWidth = density === "COMPACT" ? 60 : 76;
  const roomWidth = density === "COMPACT" ? 188 : 214;
  const stateWidth = density === "COMPACT" ? 104 : 122;
  const fixedWidth = roomWidth + stateWidth;
  const gridTemplateColumns = `${roomWidth}px ${stateWidth}px repeat(${windowDays}, ${dayWidth}px)`;
  const financeComplete = financeState === "ready";

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem("resort-pms-v3-views");
      if (raw) setSavedViews(JSON.parse(raw));
    } catch { /* ignore damaged local state */ }
  }, []);

  const loadFinance = useCallback(async () => {
    try {
      const response = await fetch("/core/api/v1/admin/reception/reservations?limit=500", { cache: "no-store" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        setFinanceItems([]);
        setFinanceState("error");
        setFinanceError(typeof body.detail === "string" ? body.detail : `Finance HTTP ${response.status}`);
        return;
      }
      if (!Array.isArray(body.items)) {
        setFinanceItems([]);
        setFinanceState("error");
        setFinanceError("Resort Core вернул некорректный финансовый список");
        return;
      }
      const items = body.items as ReceptionItem[];
      setFinanceItems(items);
      setFinanceUpdatedAt(new Date());
      if (items.length >= 500) {
        setFinanceState("partial");
        setFinanceError("Получено 500 броней — достигнут лимит endpoint. Общие KPI и фильтры долга отключены как потенциально неполные.");
      } else {
        setFinanceState("ready");
        setFinanceError(null);
      }
    } catch {
      setFinanceItems([]);
      setFinanceState("error");
      setFinanceError("Не удалось получить финансовые данные из Resort Core");
    }
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ start: localDateString(start), end: localDateString(end) });
      const gridResponse = await fetch(`/core/api/v1/pms/grid?${params}`, { cache: "no-store" });
      const gridBody = await gridResponse.json().catch(() => ({}));
      if (!gridResponse.ok) throw new Error(gridBody.detail || `Grid HTTP ${gridResponse.status}`);
      setData(gridBody as GridResponse);
    } catch (cause) {
      setData(null);
      setError(cause instanceof Error ? cause.message : "Не удалось загрузить шахматку");
    } finally {
      setLoading(false);
    }
  }, [start, end, refreshToken]);

  useEffect(() => { void load(); }, [load]);

  useEffect(() => {
    void loadFinance();
    const timer = window.setInterval(() => { void loadFinance(); }, 60_000);
    return () => window.clearInterval(timer);
  }, [loadFinance]);

  useEffect(() => {
    if (financeState !== "error" && financeState !== "partial") return;
    setFilters((current) => {
      const daily = current.daily === "DEBT" ? "ALL" : current.daily;
      if (current.finance === "ALL" && daily === current.daily) return current;
      return { ...current, finance: "ALL", daily };
    });
  }, [financeState]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    let socket: WebSocket | null = null;
    let stopped = false;
    let reconnectTimer: number | undefined;
    const base = websocketBase();
    if (!base) return;
    const params = new URLSearchParams({ start: startIso, end: endIso });
    function connect() {
      if (stopped) return;
      setRealtime("connecting");
      socket = new WebSocket(`${base}/ws/pms/grid?${params}`);
      socket.onopen = () => setRealtime("live");
      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as RealtimeMessage;
          if (message.type === "pms.grid.snapshot" && message.data) {
            setData(message.data);
            setError(null);
            setLoading(false);
          }
        } catch { /* HTTP remains fallback */ }
      };
      socket.onerror = () => socket?.close();
      socket.onclose = () => {
        if (stopped) return;
        setRealtime("offline");
        reconnectTimer = window.setTimeout(connect, 3000);
      };
    }
    connect();
    return () => { stopped = true; if (reconnectTimer) window.clearTimeout(reconnectTimer); socket?.close(); };
  }, [startIso, endIso]);

  const financeByReservation = useMemo(() => new Map(financeItems.map((item) => [item.id, item])), [financeItems]);

  const reservationBounds = useMemo(() => {
    const map = new Map<string, { start: string; end: string; segments: number }>();
    data?.rooms.forEach((room) => room.blocks.forEach((block) => {
      if (!block.reservation_id || block.type !== "RESERVATION") return;
      const current = map.get(block.reservation_id);
      if (!current) map.set(block.reservation_id, { start: block.start, end: block.end, segments: 1 });
      else {
        if (block.start < current.start) current.start = block.start;
        if (block.end > current.end) current.end = block.end;
        current.segments += 1;
      }
    }));
    return map;
  }, [data]);

  const roomTypes = useMemo(() => {
    const map = new Map<string, string>();
    data?.rooms.forEach((room) => map.set(room.room_type_code, room.room_type_name));
    return Array.from(map.entries()).sort((a, b) => a[1].localeCompare(b[1], "ru"));
  }, [data]);
  const buildings = useMemo(() => Array.from(new Set(data?.rooms.map((room) => room.building_or_zone).filter(Boolean) as string[])).sort(), [data]);
  const floors = useMemo(() => Array.from(new Set(data?.rooms.map((room) => room.floor).filter(Boolean) as string[])).sort(), [data]);

  function hasBlockToday(room: Room) { return room.blocks.some((block) => block.start <= today && today < block.end); }
  function hasReservationToday(room: Room) { return room.blocks.some((block) => block.type === "RESERVATION" && block.start <= today && today < block.end); }
  function reservationForRoom(room: Room) { return room.blocks.filter((block) => block.reservation_id).map((block) => financeByReservation.get(block.reservation_id!)).filter(Boolean) as ReceptionItem[]; }

  function roomMatchesQuickView(room: Room, mode: DailyMode) {
    if (mode === "ALL") return true;
    if (mode === "FREE_TODAY") return room.operational_state !== "TECH_BLOCK" && !hasBlockToday(room);
    if (mode === "ATTENTION") return ["DIRTY", "IN_INSPECTION", "TECH_BLOCK"].includes(room.operational_state);
    if (mode === "DEBT") return financeComplete && reservationForRoom(room).some((item) => item.remainingKgs > 0 && ["GUARANTEED", "CHECKED_IN"].includes(item.status));
    return room.blocks.some((block) => {
      if (!block.reservation_id || block.type !== "RESERVATION") return false;
      const bounds = reservationBounds.get(block.reservation_id);
      if (!bounds) return false;
      if (mode === "ARRIVALS") return block.reservation_status === "GUARANTEED" && bounds.start === today;
      if (mode === "DEPARTURES") return block.reservation_status === "CHECKED_IN" && bounds.end === today;
      if (mode === "IN_HOUSE") return block.reservation_status === "CHECKED_IN" && block.start <= today && today < block.end;
      return true;
    });
  }

  const rooms = useMemo(() => {
    if (!data) return [];
    const q = filters.search.trim().toLocaleLowerCase("ru");
    return data.rooms.filter((room) => {
      const blockText = room.blocks.flatMap((block) => [block.guest_name, block.guest_phone, block.booking_number, block.reason, block.reservation_status]).filter(Boolean).join(" ");
      const text = [room.code, room.name, room.room_type_name, room.building_or_zone, room.floor, room.beds_raw, blockText].filter(Boolean).join(" ").toLocaleLowerCase("ru");
      if (q && !text.includes(q)) return false;
      if (filters.roomType !== "ALL" && room.room_type_code !== filters.roomType) return false;
      if (filters.building !== "ALL" && room.building_or_zone !== filters.building) return false;
      if (filters.floor !== "ALL" && room.floor !== filters.floor) return false;
      if (filters.state !== "ALL" && room.operational_state !== filters.state) return false;
      if (filters.blockType !== "ALL" && !room.blocks.some((block) => block.type === filters.blockType)) return false;
      if (filters.reservationStatus !== "ALL" && !room.blocks.some((block) => block.reservation_status === filters.reservationStatus)) return false;
      if (financeComplete && filters.finance !== "ALL" && !reservationForRoom(room).some((item) => financeMatches(filters.finance, item))) return false;
      if (filters.occupancy === "FREE" && (hasBlockToday(room) || room.operational_state === "TECH_BLOCK")) return false;
      if (filters.occupancy === "OCCUPIED" && !hasReservationToday(room)) return false;
      if (filters.occupancy === "BLOCKED" && !(room.operational_state === "TECH_BLOCK" || room.blocks.some((block) => block.type !== "RESERVATION" && block.start <= today && today < block.end))) return false;
      return roomMatchesQuickView(room, filters.daily);
    });
  }, [data, filters, financeByReservation, financeComplete, reservationBounds, today]);

  const metrics = useMemo(() => {
    const source = data?.rooms || [];
    const arrivals = new Set<string>();
    const departures = new Set<string>();
    const inHouse = new Set<string>();
    source.forEach((room) => room.blocks.forEach((block) => {
      if (!block.reservation_id || block.type !== "RESERVATION") return;
      const bounds = reservationBounds.get(block.reservation_id);
      if (!bounds) return;
      if (block.reservation_status === "GUARANTEED" && bounds.start === today) arrivals.add(block.reservation_id);
      if (block.reservation_status === "CHECKED_IN" && bounds.end === today) departures.add(block.reservation_id);
      if (block.reservation_status === "CHECKED_IN" && block.start <= today && today < block.end) inHouse.add(block.reservation_id);
    }));
    const activeReservations = financeComplete ? financeItems.filter((item) => ["GUARANTEED", "CHECKED_IN"].includes(item.status)) : [];
    return {
      total: source.length,
      shown: rooms.length,
      arrivals: arrivals.size,
      departures: departures.size,
      inHouse: inHouse.size,
      free: source.filter((room) => room.operational_state !== "TECH_BLOCK" && !hasBlockToday(room)).length,
      dirty: source.filter((room) => room.operational_state === "DIRTY").length,
      inspection: source.filter((room) => room.operational_state === "IN_INSPECTION").length,
      tech: source.filter((room) => room.operational_state === "TECH_BLOCK").length,
      debtCount: financeComplete ? activeReservations.filter((item) => item.remainingKgs > 0).length : null,
      debtKgs: financeComplete ? activeReservations.reduce((sum, item) => sum + Math.max(0, item.remainingKgs), 0) : null,
    };
  }, [data, financeItems, financeComplete, reservationBounds, rooms, today]);

  const quickCounts = useMemo(() => {
    const result = new Map<DailyMode, number | null>();
    QUICK_VIEWS.forEach((view) => {
      if (view.key === "DEBT" && !financeComplete) result.set(view.key, null);
      else result.set(view.key, data?.rooms.filter((room) => roomMatchesQuickView(room, view.key)).length || 0);
    });
    return result;
  }, [data, financeItems, financeByReservation, financeComplete, reservationBounds, today]);

  const activeFilters = useMemo(() => {
    const chips: Array<{ key: keyof Filters; label: string }> = [];
    if (filters.search) chips.push({ key: "search", label: `Поиск: ${filters.search}` });
    if (filters.roomType !== "ALL") chips.push({ key: "roomType", label: roomTypes.find(([code]) => code === filters.roomType)?.[1] || filters.roomType });
    if (filters.building !== "ALL") chips.push({ key: "building", label: `Корпус: ${filters.building}` });
    if (filters.floor !== "ALL") chips.push({ key: "floor", label: `Этаж: ${filters.floor}` });
    if (filters.state !== "ALL") chips.push({ key: "state", label: ROOM_STATE_LABELS[filters.state as Room["operational_state"]] || filters.state });
    if (filters.reservationStatus !== "ALL") chips.push({ key: "reservationStatus", label: RESERVATION_STATUS_LABELS[filters.reservationStatus] || filters.reservationStatus });
    if (filters.finance !== "ALL") chips.push({ key: "finance", label: `Оплата: ${filters.finance}` });
    if (filters.occupancy !== "ALL") chips.push({ key: "occupancy", label: `Занятость: ${filters.occupancy}` });
    if (filters.blockType !== "ALL") chips.push({ key: "blockType", label: `Блок: ${filters.blockType}` });
    return chips;
  }, [filters, roomTypes]);

  function clearFilter(key: keyof Filters) { setFilters((current) => ({ ...current, [key]: DEFAULT_FILTERS[key] })); }
  function resetFilters() { setFilters(DEFAULT_FILTERS); }

  function saveView() {
    const name = window.prompt("Название представления", `Мой вид ${savedViews.length + 1}`)?.trim();
    if (!name) return;
    const view: SavedView = { id: `${Date.now()}`, name, filters, windowDays, density };
    const next = [...savedViews, view].slice(-8);
    setSavedViews(next);
    window.localStorage.setItem("resort-pms-v3-views", JSON.stringify(next));
  }

  function applyView(view: SavedView) {
    const safeFilters = financeComplete ? view.filters : { ...view.filters, finance: "ALL" as FinanceMode, daily: view.filters.daily === "DEBT" ? "ALL" as DailyMode : view.filters.daily };
    setFilters(safeFilters);
    setWindowDays(view.windowDays);
    setDensity(view.density);
  }
  function deleteView(id: string) {
    const next = savedViews.filter((view) => view.id !== id);
    setSavedViews(next);
    window.localStorage.setItem("resort-pms-v3-views", JSON.stringify(next));
  }

  function blockPlacement(block: Pick<Block, "start" | "end">) {
    const from = Math.max(0, daysBetween(startIso, block.start));
    const to = Math.min(windowDays, daysBetween(startIso, block.end));
    if (to <= 0 || from >= windowDays || to <= from) return null;
    return { from, to, column: `${3 + from} / ${3 + to}` };
  }

  function dateFromDragEvent(event: React.DragEvent<HTMLDivElement>) {
    const target = event.target as HTMLElement;
    if (target.closest(".mega-room-cell,.mega-state-cell")) return null;
    const rect = event.currentTarget.getBoundingClientRect();
    const relativeX = event.clientX - rect.left - fixedWidth;
    const index = Math.floor(relativeX / dayWidth);
    if (index < 0 || index >= windowDays) return null;
    return shiftDate(startIso, index);
  }

  function onDrop(room: Room, event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    const reservationId = event.dataTransfer.getData("application/x-resort-reservation") || draggingReservationId;
    const targetDate = dateFromDragEvent(event);
    setDropRoomId(null); setDropDate(null); setDraggingReservationId(null);
    if (!reservationId || !targetDate || room.operational_state === "TECH_BLOCK") return;
    const bounds = reservationBounds.get(reservationId);
    const nights = bounds ? Math.max(1, daysBetween(bounds.start, bounds.end)) : 1;
    setSelectedReservation({ id: reservationId, targetRoomId: room.id, initialCheckIn: targetDate, initialCheckOut: shiftDate(targetDate, nights) });
  }

  const financeBadge = financeState === "ready"
    ? `Финансы Core${financeUpdatedAt ? ` · ${financeUpdatedAt.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}` : ""}`
    : financeState === "partial" ? "Финансы неполные" : financeState === "error" ? "Финансы недоступны" : "Финансы загружаются";

  return <main className={`mega-pms-shell density-${density.toLowerCase()}`}>
    <header className="mega-pms-head">
      <div>
        <p className="eyebrow">Resort OS · Three Crowns</p>
        <h1>Мега-шахматка <span>V3</span></h1>
        <p>84 номера, live inventory, финансы и операционные статусы в одном командном экране.</p>
      </div>
      <div className="mega-head-actions">
        <span className={`mega-connection ${error ? "is-error" : realtime === "live" ? "is-live" : ""}`}><i />{error ? "Core недоступен" : realtime === "live" ? "Realtime live" : realtime === "connecting" ? "Подключение" : "HTTP fallback"}</span>
        <span className={`mega-connection ${financeState === "ready" ? "is-live" : financeState === "partial" ? "is-warning" : financeState === "error" ? "is-error" : ""}`}><i />{financeBadge}</span>
        <button className="btn" onClick={() => { setRefreshToken((value) => value + 1); void loadFinance(); }}>↻ Обновить</button>
      </div>
    </header>

    <section className="mega-command-bar" aria-label="Командная панель шахматки">
      <div className="mega-search"><span>⌕</span><input value={filters.search} onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))} placeholder="Гость, телефон, бронь, № комнаты, категория, корпус…" />{filters.search && <button onClick={() => clearFilter("search")}>×</button>}</div>
      <div className="mega-date-nav"><button onClick={() => setStart(addDays(start, -7))}>← 7</button><button className="today" onClick={() => setStart(parseDateOnly(today))}>Сегодня</button><button onClick={() => setStart(addDays(start, 7))}>7 →</button></div>
      <select value={windowDays} onChange={(event) => setWindowDays(Number(event.target.value))} aria-label="Период"><option value={7}>7 дней</option><option value={14}>14 дней</option><option value={21}>21 день</option><option value={31}>31 день</option></select>
      <div className="mega-density"><button className={density === "COMPACT" ? "active" : ""} onClick={() => setDensity("COMPACT")}>Плотно</button><button className={density === "COMFORTABLE" ? "active" : ""} onClick={() => setDensity("COMFORTABLE")}>Комфорт</button></div>
      <button className={`mega-filter-toggle ${activeFilters.length ? "has-filters" : ""}`} onClick={() => setAdvancedOpen((value) => !value)}>Фильтры {activeFilters.length > 0 && <b>{activeFilters.length}</b>} {advancedOpen ? "↑" : "↓"}</button>
    </section>

    {financeState !== "ready" && <div className={`mega-finance-warning state-${financeState}`} role="status"><strong>Финансовая истина не подтверждена</strong><span>{financeError || "Финансовые данные ещё загружаются из Resort Core."} KPI и фильтры долга не показывают нулевые значения вместо неизвестных.</span></div>}

    <section className="mega-quick-grid" aria-label="Операционные режимы">
      {QUICK_VIEWS.map((view) => {
        const disabled = view.key === "DEBT" && !financeComplete;
        const count = quickCounts.get(view.key);
        return <button key={view.key} disabled={disabled} className={filters.daily === view.key ? "active" : ""} onClick={() => !disabled && setFilters((current) => ({ ...current, daily: view.key }))} title={disabled ? "Фильтр долга доступен только при полной финансовой выборке Resort Core" : undefined}><span>{view.label}<small>{view.hint}</small></span><strong>{count == null ? "—" : count}</strong></button>;
      })}
    </section>

    {advancedOpen && <section className="mega-filter-panel">
      <div className="mega-filter-head"><div><strong>Супер-фильтр</strong><span>Комбинируйте условия одновременно</span></div><div><button onClick={saveView}>＋ Сохранить вид</button><button onClick={resetFilters}>Сбросить всё</button></div></div>
      <div className="mega-filter-grid">
        <label><span>Категория номера</span><select value={filters.roomType} onChange={(event) => setFilters((current) => ({ ...current, roomType: event.target.value }))}><option value="ALL">Все категории</option>{roomTypes.map(([code, name]) => <option key={code} value={code}>{name}</option>)}</select></label>
        <label><span>Корпус / зона</span><select value={filters.building} onChange={(event) => setFilters((current) => ({ ...current, building: event.target.value }))}><option value="ALL">Все корпуса</option>{buildings.map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
        <label><span>Этаж</span><select value={filters.floor} onChange={(event) => setFilters((current) => ({ ...current, floor: event.target.value }))}><option value="ALL">Все этажи</option>{floors.map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
        <label><span>Статус номера</span><select value={filters.state} onChange={(event) => setFilters((current) => ({ ...current, state: event.target.value }))}><option value="ALL">Любой</option>{Object.entries(ROOM_STATE_LABELS).map(([code, label]) => <option key={code} value={code}>{label}</option>)}</select></label>
        <label><span>Статус брони</span><select value={filters.reservationStatus} onChange={(event) => setFilters((current) => ({ ...current, reservationStatus: event.target.value }))}><option value="ALL">Любой</option><option value="GUARANTEED">Ожидает заезд</option><option value="CHECKED_IN">Проживает</option><option value="CHECKED_OUT">Выехал</option><option value="CANCELLED">Отменена</option><option value="NO_SHOW">Не заехал</option></select></label>
        <label><span>Оплата</span><select disabled={!financeComplete} value={filters.finance} onChange={(event) => setFilters((current) => ({ ...current, finance: event.target.value as FinanceMode }))} title={!financeComplete ? "Фильтр оплаты отключён, пока финансовая выборка Resort Core не подтверждена полностью" : undefined}><option value="ALL">{financeComplete ? "Любая" : "Финансы недоступны"}</option><option value="PAID">Оплачено полностью</option><option value="PARTIAL">Частичная оплата</option><option value="UNPAID">Без оплаты</option><option value="DEBT">Есть остаток</option></select></label>
        <label><span>Занятость сегодня</span><select value={filters.occupancy} onChange={(event) => setFilters((current) => ({ ...current, occupancy: event.target.value as OccupancyMode }))}><option value="ALL">Любая</option><option value="FREE">Свободные</option><option value="OCCUPIED">Заняты гостями</option><option value="BLOCKED">Заблокированы</option></select></label>
        <label><span>Тип блока</span><select value={filters.blockType} onChange={(event) => setFilters((current) => ({ ...current, blockType: event.target.value as BlockMode }))}><option value="ALL">Любой</option><option value="RESERVATION">Бронь</option><option value="MAINTENANCE">Ремонт</option><option value="MANUAL">Служебный</option></select></label>
      </div>
      {activeFilters.length > 0 && <div className="mega-filter-chips">{activeFilters.map((chip) => <button key={chip.key} onClick={() => clearFilter(chip.key)}>{chip.label}<span>×</span></button>)}</div>}
      {savedViews.length > 0 && <div className="mega-saved-views"><span>Мои виды</span>{savedViews.map((view) => <div key={view.id}><button onClick={() => applyView(view)}>{view.name}</button><button className="delete" onClick={() => deleteView(view.id)} aria-label={`Удалить ${view.name}`}>×</button></div>)}</div>}
    </section>}

    <section className="mega-kpis">
      <article><span>Показано</span><strong>{metrics.shown}<small>/ {metrics.total}</small></strong></article>
      <article className="kpi-blue"><span>Проживают</span><strong>{metrics.inHouse}</strong></article>
      <article className="kpi-green"><span>Свободно сегодня</span><strong>{metrics.free}</strong></article>
      <article className="kpi-cyan"><span>Заезды / выезды</span><strong>{metrics.arrivals}<small> / {metrics.departures}</small></strong></article>
      <article className="kpi-red"><span>Долг по активным</span><strong>{metrics.debtKgs == null ? "—" : money(metrics.debtKgs)}<small>{metrics.debtCount == null ? " данные не подтверждены" : ` сом · ${metrics.debtCount}`}</small></strong></article>
      <article className="kpi-amber"><span>Уборка / проверка</span><strong>{metrics.dirty}<small> / {metrics.inspection}</small></strong></article>
      <article className="kpi-gray"><span>Техблок</span><strong>{metrics.tech}</strong></article>
    </section>

    <section className="mega-board-card">
      <div className="mega-board-toolbar">
        <div><strong>{startIso}</strong><span>→</span><strong>{localDateString(addDays(end, -1))}</strong><em>{windowDays} дней</em></div>
        <div className="mega-legend"><span><i className="lg guaranteed" />Ожидает</span><span><i className="lg inhouse" />Проживает</span><span><i className="lg paid" />Оплачено</span><span><i className="lg debt" />Есть остаток</span><span><i className="lg maintenance" />Ремонт</span></div>
      </div>
      {error && <div className="error-box">{error}</div>}
      {loading && !data ? <div className="loading">Загрузка мега-шахматки…</div> : rooms.length === 0 ? <div className="mega-empty"><strong>0 номеров</strong><p>Ничего не совпало с текущей комбинацией фильтров.</p><button className="btn" onClick={resetFilters}>Сбросить фильтры</button></div> : <div className="mega-board-scroll">
        <div className="mega-board" style={{ minWidth: `${fixedWidth + windowDays * dayWidth}px` }}>
          <div className="mega-grid-head" style={{ gridTemplateColumns }}>
            <div className="mega-room-head">Номер <small>{rooms.length}</small></div><div className="mega-state-head">Статус</div>
            {days.map((day) => { const key = localDateString(day); const weekday = new Intl.DateTimeFormat("ru-RU", { weekday: "short" }).format(day); const weekend = day.getDay() === 0 || day.getDay() === 6; return <div key={key} className={`mega-date-head ${key === today ? "today" : ""} ${weekend ? "weekend" : ""}`}><strong>{day.getDate()}</strong><span>{weekday}</span></div>; })}
          </div>

          {rooms.map((room) => <div key={room.id} className={`mega-grid-row state-${room.operational_state.toLowerCase()} ${dropRoomId === room.id ? "drop-target" : ""}`} style={{ gridTemplateColumns }} onDragOver={(event) => { if (!draggingReservationId || room.operational_state === "TECH_BLOCK") return; event.preventDefault(); setDropRoomId(room.id); setDropDate(dateFromDragEvent(event)); }} onDragLeave={(event) => { if (event.currentTarget.contains(event.relatedTarget as Node | null)) return; if (dropRoomId === room.id) { setDropRoomId(null); setDropDate(null); } }} onDrop={(event) => onDrop(room, event)}>
            <button className="mega-room-cell" onClick={() => setSelectedRoomId(room.id)}><strong>№ {room.code}</strong><span>{room.room_type_name}</span><small>{[room.building_or_zone, room.floor].filter(Boolean).join(" · ") || "—"}</small></button>
            <div className="mega-state-cell"><span className={`mega-state-pill ${room.operational_state}`}>{ROOM_STATE_LABELS[room.operational_state]}</span></div>
            {days.map((day, index) => { const key = localDateString(day); const weekend = day.getDay() === 0 || day.getDay() === 6; const targeted = dropRoomId === room.id && dropDate === key; return <div key={key} className={`mega-day-bg ${weekend ? "weekend" : ""} ${key === today ? "today" : ""} ${targeted ? "targeted" : ""}`} style={{ gridColumn: `${3 + index} / ${4 + index}` }} />; })}
            {room.blocks.map((block) => {
              const place = blockPlacement(block); if (!place) return null;
              const finance = block.reservation_id ? financeByReservation.get(block.reservation_id) : undefined;
              const payment = financeClass(finance);
              const interactive = block.type === "RESERVATION" && Boolean(block.reservation_id);
              const title = block.type === "RESERVATION" ? block.guest_name || block.booking_number || "Бронь" : block.reason || (block.type === "MAINTENANCE" ? "Ремонт" : "Блок");
              return <button key={block.id} draggable={interactive} className={`mega-block type-${block.type.toLowerCase()} status-${(block.reservation_status || "none").toLowerCase()} payment-${payment}`} style={{ gridColumn: place.column }} onDragStart={(event) => { if (!interactive || !block.reservation_id) { event.preventDefault(); return; } setDraggingReservationId(block.reservation_id); event.dataTransfer.effectAllowed = "move"; event.dataTransfer.setData("application/x-resort-reservation", block.reservation_id); }} onDragEnd={() => { setDraggingReservationId(null); setDropRoomId(null); setDropDate(null); }} onClick={() => { if (block.reservation_id) setSelectedReservation({ id: block.reservation_id }); }} title={[title, block.booking_number, finance ? `Оплачено ${money(finance.paidKgs)} / ${money(finance.totalKgs)} сом` : "Финансы не загружены для этой брони"].filter(Boolean).join(" · ")}>
                <span className="mega-block-title">{title}</span>
                <span className="mega-block-meta">{block.booking_number || (block.type === "MAINTENANCE" ? "TECH" : "BLOCK")}{finance && <b className={`money-${payment}`}>{finance.remainingKgs <= 0 ? "✓" : `${money(finance.remainingKgs)} сом`}</b>}</span>
              </button>;
            })}
          </div>)}
        </div>
      </div>}
      <footer className="mega-board-footer"><span>Перетащите бронь: выберите номер и дату, затем подтвердите server preview</span><span>Клик по брони: карточка / даты / переселение / заезд</span><span>Клик по номеру: задачи, блоки и статус комнаты</span></footer>
    </section>

    {selectedRoomId && <RoomDetailModal roomId={selectedRoomId} onClose={() => setSelectedRoomId(null)} />}
    {selectedReservation && data && <ChessboardReservationModal reservationId={selectedReservation.id} rooms={data.rooms.map((room) => ({ id: room.id, code: room.code, room_type_code: room.room_type_code, room_type_name: room.room_type_name, operational_state: room.operational_state }))} onClose={() => setSelectedReservation(null)} onUpdated={() => { setSelectedReservation(null); setRefreshToken((value) => value + 1); void loadFinance(); }} initialMode="MOVE" initialTargetRoomId={selectedReservation.targetRoomId} initialCheckIn={selectedReservation.initialCheckIn} initialCheckOut={selectedReservation.initialCheckOut} />}
  </main>;
}