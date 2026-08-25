"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import ChessboardReservationModal, { ChessboardMode } from "./ChessboardReservationModal";
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

type GridResponse = {
  property: string;
  start: string;
  end: string;
  rooms: Room[];
};

type RealtimeMessage = {
  type: "pms.grid.snapshot" | "heartbeat";
  version?: string;
  data?: GridResponse;
};

type ReservationOpen = {
  id: string;
  initialMode?: ChessboardMode;
  targetRoomId?: string;
};

const STATE_LABELS: Record<Room["operational_state"], string> = {
  UNKNOWN: "Не указан",
  CLEAN: "Готов",
  DIRTY: "Уборка",
  IN_INSPECTION: "Проверка",
  TECH_BLOCK: "Ремонт",
};

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

function dateRange(start: Date, count: number) {
  return Array.from({ length: count }, (_, index) => addDays(start, index));
}

function dayOrdinal(value: string) {
  const [y, m, d] = value.split("-").map(Number);
  return Math.floor(Date.UTC(y, m - 1, d) / 86400000);
}

function daysBetween(left: string, right: string) {
  return dayOrdinal(right) - dayOrdinal(left);
}

function blockTitle(block: Block) {
  if (block.type === "RESERVATION") return block.guest_name || block.booking_number || "Бронь";
  return block.reason || (block.type === "MAINTENANCE" ? "Ремонт" : "Блок");
}

function websocketBase() {
  const configured = process.env.NEXT_PUBLIC_CORE_WS_URL?.replace(/\/$/, "");
  if (configured) return configured;
  if (typeof window === "undefined") return "";
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.hostname;
  const port = window.location.port === "3001" ? "8000" : window.location.port;
  return `${protocol}//${host}${port ? `:${port}` : ""}`;
}

export default function PMSGridV2() {
  const [start, setStart] = useState(() => {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), now.getDate());
  });
  const [windowDays, setWindowDays] = useState(14);
  const [data, setData] = useState<GridResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [realtime, setRealtime] = useState<"connecting" | "live" | "offline">("connecting");
  const [search, setSearch] = useState("");
  const [roomType, setRoomType] = useState("ALL");
  const [state, setState] = useState("ALL");
  const [refreshToken, setRefreshToken] = useState(0);
  const [selectedRoomId, setSelectedRoomId] = useState<string | null>(null);
  const [selectedReservation, setSelectedReservation] = useState<ReservationOpen | null>(null);
  const [draggingReservationId, setDraggingReservationId] = useState<string | null>(null);
  const [dropRoomId, setDropRoomId] = useState<string | null>(null);

  const days = useMemo(() => dateRange(start, windowDays), [start, windowDays]);
  const end = useMemo(() => addDays(start, windowDays), [start, windowDays]);
  const startIso = localDateString(start);
  const endIso = localDateString(end);
  const today = localDateString(new Date());

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ start: localDateString(start), end: localDateString(end) });
      const response = await fetch(`/core/api/v1/pms/grid?${params}`, { cache: "no-store" });
      if (!response.ok) throw new Error(`Core API: HTTP ${response.status}`);
      setData((await response.json()) as GridResponse);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось загрузить шахматку");
    } finally {
      setLoading(false);
    }
  }, [start, end, refreshToken]);

  useEffect(() => { void load(); }, [load]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    let socket: WebSocket | null = null;
    let stopped = false;
    let reconnectTimer: number | undefined;
    const params = new URLSearchParams({ start: startIso, end: endIso });
    const base = websocketBase();
    if (!base) return;

    function connect() {
      if (stopped) return;
      setRealtime("connecting");
      socket = new WebSocket(`${base}/ws/pms/grid?${params.toString()}`);
      socket.onopen = () => setRealtime("live");
      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as RealtimeMessage;
          if (message.type === "pms.grid.snapshot" && message.data) {
            setData(message.data);
            setError(null);
            setLoading(false);
          }
        } catch {
          // HTTP remains fallback.
        }
      };
      socket.onerror = () => socket?.close();
      socket.onclose = () => {
        if (stopped) return;
        setRealtime("offline");
        reconnectTimer = window.setTimeout(connect, 3000);
      };
    }

    connect();
    return () => {
      stopped = true;
      if (reconnectTimer) window.clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, [startIso, endIso]);

  const roomTypes = useMemo(() => {
    if (!data) return [];
    const map = new Map<string, string>();
    data.rooms.forEach((room) => map.set(room.room_type_code, room.room_type_name));
    return Array.from(map.entries()).sort((a, b) => a[1].localeCompare(b[1], "ru"));
  }, [data]);

  const rooms = useMemo(() => {
    if (!data) return [];
    const query = search.trim().toLocaleLowerCase("ru");
    return data.rooms.filter((room) => {
      const text = [room.code, room.room_type_name, room.building_or_zone || "", room.floor || ""].join(" ").toLocaleLowerCase("ru");
      return (!query || text.includes(query)) && (roomType === "ALL" || room.room_type_code === roomType) && (state === "ALL" || room.operational_state === state);
    });
  }, [data, roomType, search, state]);

  const counts = useMemo(() => {
    const result: Record<Room["operational_state"] | "TOTAL", number> = { TOTAL: rooms.length, UNKNOWN: 0, CLEAN: 0, DIRTY: 0, IN_INSPECTION: 0, TECH_BLOCK: 0 };
    rooms.forEach((room) => result[room.operational_state]++);
    return result;
  }, [rooms]);

  const gridTemplateColumns = `190px 118px repeat(${windowDays}, 72px)`;

  function blockPlacement(block: Block) {
    const from = Math.max(0, daysBetween(startIso, block.start));
    const to = Math.min(windowDays, daysBetween(startIso, block.end));
    if (to <= 0 || from >= windowDays || to <= from) return null;
    return { from, to, column: `${3 + from} / ${3 + to}` };
  }

  function onDrop(room: Room, event: React.DragEvent) {
    event.preventDefault();
    const reservationId = event.dataTransfer.getData("application/x-resort-reservation") || draggingReservationId;
    setDropRoomId(null);
    setDraggingReservationId(null);
    if (!reservationId || room.operational_state === "TECH_BLOCK") return;
    setSelectedReservation({ id: reservationId, initialMode: "MOVE", targetRoomId: room.id });
  }

  return <main className="shell pms-v2-shell">
    <div className="topbar">
      <div>
        <p className="eyebrow">Resort OS · Three Crowns</p>
        <h1>Шахматка</h1>
        <p className="subtitle">Бронь — единая полоса по датам. Будущую бронь можно перетащить на другой номер; Core сначала покажет preview и только потом позволит подтвердить.</p>
      </div>
      <div className={`connection ${error ? "error" : "ok"}`}>{error ? "Core недоступен" : realtime === "live" ? "Realtime" : realtime === "connecting" ? "Подключение…" : "HTTP режим"}</div>
    </div>

    <section className="controls" aria-label="Фильтры шахматки">
      <div className="control"><label>Номер / категория</label><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="312, люкс, коттедж…" /></div>
      <div className="control"><label>Категория</label><select value={roomType} onChange={(e) => setRoomType(e.target.value)}><option value="ALL">Все категории</option>{roomTypes.map(([code, name]) => <option key={code} value={code}>{name}</option>)}</select></div>
      <div className="control"><label>Состояние</label><select value={state} onChange={(e) => setState(e.target.value)}><option value="ALL">Все состояния</option>{Object.entries(STATE_LABELS).map(([code, label]) => <option key={code} value={code}>{label}</option>)}</select></div>
      <div className="control"><label>Период</label><select value={windowDays} onChange={(e) => setWindowDays(Number(e.target.value))}><option value={7}>7 дней</option><option value={14}>14 дней</option><option value={31}>31 день</option></select></div>
      <div className="date-actions"><button className="btn" onClick={() => setStart(addDays(start, -7))}>←</button><button className="btn" onClick={() => setStart(parseDateOnly(today))}>Сегодня</button><button className="btn" onClick={() => setStart(addDays(start, 7))}>→</button><button className="btn primary" onClick={() => setRefreshToken((x) => x + 1)}>Обновить</button></div>
    </section>

    <section className="summary">
      <div className="summary-card"><strong>{counts.TOTAL}</strong><span>Показано</span></div>
      <div className="summary-card"><strong>{counts.CLEAN}</strong><span>Готовы</span></div>
      <div className="summary-card"><strong>{counts.DIRTY}</strong><span>Уборка</span></div>
      <div className="summary-card"><strong>{counts.IN_INSPECTION}</strong><span>Проверка</span></div>
      <div className="summary-card"><strong>{counts.TECH_BLOCK}</strong><span>Ремонт</span></div>
      <div className="summary-card"><strong>{counts.UNKNOWN}</strong><span>Без статуса</span></div>
    </section>

    <section className="pms-v2-card">
      <div className="pms-v2-toolbar"><div><strong>{startIso}</strong> — <strong>{localDateString(addDays(end, -1))}</strong></div><div className="pms-v2-help"><span>Перетащить = перенос</span><span>Край полосы = изменить даты</span><span>Клик = карточка / переселение / заезд</span></div></div>
      {error && <div className="error-box">{error}</div>}
      {loading && !data ? <div className="loading">Загрузка шахматки…</div> : rooms.length === 0 ? <div className="empty">Нет номеров по фильтрам.</div> : <div className="pms-v2-scroll">
        <div className="pms-v2-board" style={{ minWidth: `${308 + windowDays * 72}px` }}>
          <div className="pms-v2-header" style={{ gridTemplateColumns }}>
            <div className="v2-room-head">Номер</div><div className="v2-state-head">Статус</div>
            {days.map((day) => { const key = localDateString(day); const weekday = new Intl.DateTimeFormat("ru-RU", { weekday: "short" }).format(day); return <div key={key} className={`v2-date-head ${key === today ? "today" : ""}`}><strong>{day.getDate()}</strong><span>{weekday}</span></div>; })}
          </div>

          {rooms.map((room) => <div key={room.id} className={`pms-v2-row ${dropRoomId === room.id ? "drop-target" : ""} ${room.operational_state === "TECH_BLOCK" ? "tech-row" : ""}`} style={{ gridTemplateColumns }} onDragOver={(event) => { if (draggingReservationId && room.operational_state !== "TECH_BLOCK") { event.preventDefault(); setDropRoomId(room.id); } }} onDragLeave={() => { if (dropRoomId === room.id) setDropRoomId(null); }} onDrop={(event) => onDrop(room, event)}>
            <button className="v2-room-cell" onClick={() => setSelectedRoomId(room.id)}><strong>{room.code}</strong><span>{room.room_type_name}</span></button>
            <div className="v2-state-cell"><span className={`badge ${room.operational_state}`}>{STATE_LABELS[room.operational_state]}</span></div>
            {days.map((day, index) => { const key = localDateString(day); const weekend = day.getDay() === 0 || day.getDay() === 6; return <div key={key} className={`v2-day-bg ${weekend ? "weekend" : ""} ${key === today ? "today" : ""}`} style={{ gridColumn: `${3 + index} / ${4 + index}` }} />; })}
            {room.blocks.map((block) => {
              const place = blockPlacement(block);
              if (!place) return null;
              const interactive = block.type === "RESERVATION" && Boolean(block.reservation_id);
              const draggable = interactive && block.reservation_status === "GUARANTEED";
              return <div key={block.id} className={`v2-booking-bar ${block.type} ${interactive ? "interactive" : ""} ${draggable ? "draggable" : ""}`} style={{ gridColumn: place.column }} draggable={draggable} onDragStart={(event) => {
                if (!draggable || !block.reservation_id) return;
                setDraggingReservationId(block.reservation_id);
                event.dataTransfer.effectAllowed = "move";
                event.dataTransfer.setData("application/x-resort-reservation", block.reservation_id);
              }} onDragEnd={() => { setDraggingReservationId(null); setDropRoomId(null); }}>
                {interactive && block.reservation_id && <button className="v2-resize-handle left" title="Изменить даты" onClick={(event) => { event.stopPropagation(); setSelectedReservation({ id: block.reservation_id!, initialMode: "DATES" }); }}>‹</button>}
                <button className="v2-bar-main" disabled={!interactive} onClick={() => interactive && block.reservation_id && setSelectedReservation({ id: block.reservation_id })} title={`${blockTitle(block)} · ${block.start} → ${block.end}${draggable ? " · можно перетащить" : ""}`}>
                  <strong>{blockTitle(block)}</strong><span>{block.booking_number || block.reason || ""}</span>
                </button>
                {interactive && block.reservation_id && <button className="v2-resize-handle right" title="Изменить даты" onClick={(event) => { event.stopPropagation(); setSelectedReservation({ id: block.reservation_id!, initialMode: "DATES" }); }}>›</button>}
              </div>;
            })}
          </div>)}
        </div>
      </div>}
    </section>

    {selectedRoomId && <RoomDetailModal roomId={selectedRoomId} onClose={() => setSelectedRoomId(null)} />}
    {selectedReservation && <ChessboardReservationModal reservationId={selectedReservation.id} rooms={data?.rooms || []} initialMode={selectedReservation.initialMode} initialTargetRoomId={selectedReservation.targetRoomId} onClose={() => setSelectedReservation(null)} onUpdated={() => setRefreshToken((x) => x + 1)} />}
  </main>;
}
