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
  initialCheckIn?: string;
  initialCheckOut?: string;
};

type ReservationBounds = {
  start: string;
  end: string;
  segments: number;
};

type ResizeDraft = {
  blockId: string;
  reservationId: string;
  edge: "LEFT" | "RIGHT";
  checkIn: string;
  checkOut: string;
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

function shiftDate(value: string, amount: number) {
  const [y, m, d] = value.split("-").map(Number);
  const next = new Date(Date.UTC(y, m - 1, d + amount));
  return next.toISOString().slice(0, 10);
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
  const [dropDate, setDropDate] = useState<string | null>(null);
  const [resizeDraft, setResizeDraft] = useState<ResizeDraft | null>(null);

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

  const reservationBounds = useMemo(() => {
    const result = new Map<string, ReservationBounds>();
    if (!data) return result;
    for (const room of data.rooms) {
      for (const block of room.blocks) {
        if (block.type !== "RESERVATION" || !block.reservation_id) continue;
        const current = result.get(block.reservation_id);
        if (!current) {
          result.set(block.reservation_id, { start: block.start, end: block.end, segments: 1 });
          continue;
        }
        if (block.start < current.start) current.start = block.start;
        if (block.end > current.end) current.end = block.end;
        current.segments += 1;
      }
    }
    return result;
  }, [data]);

  const counts = useMemo(() => {
    const result: Record<Room["operational_state"] | "TOTAL", number> = { TOTAL: rooms.length, UNKNOWN: 0, CLEAN: 0, DIRTY: 0, IN_INSPECTION: 0, TECH_BLOCK: 0 };
    rooms.forEach((room) => result[room.operational_state]++);
    return result;
  }, [rooms]);

  const gridTemplateColumns = `190px 118px repeat(${windowDays}, 72px)`;

  function blockPlacement(block: Pick<Block, "start" | "end">) {
    const from = Math.max(0, daysBetween(startIso, block.start));
    const to = Math.min(windowDays, daysBetween(startIso, block.end));
    if (to <= 0 || from >= windowDays || to <= from) return null;
    return { from, to, column: `${3 + from} / ${3 + to}` };
  }

  function dateFromDragEvent(event: React.DragEvent<HTMLDivElement>) {
    const target = event.target as HTMLElement;
    if (target.closest(".v2-room-cell,.v2-state-cell")) return null;
    const rect = event.currentTarget.getBoundingClientRect();
    const relativeX = event.clientX - rect.left - 308;
    const index = Math.floor(relativeX / 72);
    if (index < 0 || index >= windowDays) return null;
    return shiftDate(startIso, index);
  }

  function onDrop(room: Room, event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    const reservationId = event.dataTransfer.getData("application/x-resort-reservation") || draggingReservationId;
    const targetDate = dateFromDragEvent(event);
    setDropRoomId(null);
    setDropDate(null);
    setDraggingReservationId(null);
    if (!reservationId || room.operational_state === "TECH_BLOCK") return;

    const bounds = reservationBounds.get(reservationId);
    if (!bounds || bounds.segments !== 1 || !targetDate) {
      setSelectedReservation({ id: reservationId, initialMode: "MOVE", targetRoomId: room.id });
      return;
    }

    const nights = daysBetween(bounds.start, bounds.end);
    setSelectedReservation({
      id: reservationId,
      initialMode: "MOVE",
      targetRoomId: room.id,
      initialCheckIn: targetDate,
      initialCheckOut: shiftDate(targetDate, nights),
    });
  }

  function beginResize(event: React.PointerEvent<HTMLButtonElement>, block: Block, edge: "LEFT" | "RIGHT") {
    if (!block.reservation_id) return;
    const bounds = reservationBounds.get(block.reservation_id);
    if (!bounds) return;
    if (edge === "LEFT" && block.reservation_status !== "GUARANTEED") return;
    if (edge === "RIGHT" && !["GUARANTEED", "CHECKED_IN"].includes(block.reservation_status || "")) return;

    event.preventDefault();
    event.stopPropagation();

    const reservationId = block.reservation_id;
    const originalCheckIn = bounds.start;
    const originalCheckOut = bounds.end;
    const startClientX = event.clientX;
    let nextCheckIn = originalCheckIn;
    let nextCheckOut = originalCheckOut;
    let moved = false;

    setResizeDraft({ blockId: block.id, reservationId, edge, checkIn: nextCheckIn, checkOut: nextCheckOut });
    document.body.classList.add("pms-resizing");

    const onPointerMove = (pointerEvent: PointerEvent) => {
      const deltaPixels = pointerEvent.clientX - startClientX;
      if (Math.abs(deltaPixels) >= 4) moved = true;
      const deltaDays = Math.round(deltaPixels / 72);

      if (edge === "LEFT") {
        let candidate = shiftDate(originalCheckIn, deltaDays);
        if (candidate >= originalCheckOut) candidate = shiftDate(originalCheckOut, -1);
        nextCheckIn = candidate;
      } else {
        let candidate = shiftDate(originalCheckOut, deltaDays);
        if (candidate <= originalCheckIn) candidate = shiftDate(originalCheckIn, 1);
        nextCheckOut = candidate;
      }

      setResizeDraft({ blockId: block.id, reservationId, edge, checkIn: nextCheckIn, checkOut: nextCheckOut });
    };

    const cleanup = () => {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
      window.removeEventListener("pointercancel", onPointerCancel);
      document.body.classList.remove("pms-resizing");
      setResizeDraft(null);
    };

    const onPointerUp = () => {
      cleanup();
      setSelectedReservation({
        id: reservationId,
        initialMode: "DATES",
        initialCheckIn: moved ? nextCheckIn : undefined,
        initialCheckOut: moved ? nextCheckOut : undefined,
      });
    };

    const onPointerCancel = () => cleanup();

    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp, { once: true });
    window.addEventListener("pointercancel", onPointerCancel, { once: true });
  }

  return <main className="shell pms-v2-shell">
    <div className="topbar">
      <div>
        <p className="eyebrow">Resort OS · Three Crowns</p>
        <h1>Шахматка</h1>
        <p className="subtitle">Перетащите будущую бронь на другой номер или дату; потяните внешний край для сокращения/продления. Resort Core всегда проверяет изменение до сохранения.</p>
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
      <div className="pms-v2-toolbar"><div><strong>{startIso}</strong> — <strong>{localDateString(addDays(end, -1))}</strong></div><div className="pms-v2-help"><span>Перетащить = номер + дата</span><span>Потянуть внешний край = даты</span><span>Клик = карточка / переселение / заезд</span></div></div>
      {error && <div className="error-box">{error}</div>}
      {loading && !data ? <div className="loading">Загрузка шахматки…</div> : rooms.length === 0 ? <div className="empty">Нет номеров по фильтрам.</div> : <div className="pms-v2-scroll">
        <div className="pms-v2-board" style={{ minWidth: `${308 + windowDays * 72}px` }}>
          <div className="pms-v2-header" style={{ gridTemplateColumns }}>
            <div className="v2-room-head">Номер</div><div className="v2-state-head">Статус</div>
            {days.map((day) => { const key = localDateString(day); const weekday = new Intl.DateTimeFormat("ru-RU", { weekday: "short" }).format(day); return <div key={key} className={`v2-date-head ${key === today ? "today" : ""}`}><strong>{day.getDate()}</strong><span>{weekday}</span></div>; })}
          </div>

          {rooms.map((room) => <div key={room.id} className={`pms-v2-row ${dropRoomId === room.id ? "drop-target" : ""} ${room.operational_state === "TECH_BLOCK" ? "tech-row" : ""}`} style={{ gridTemplateColumns }} onDragOver={(event) => {
            if (!draggingReservationId || room.operational_state === "TECH_BLOCK") return;
            event.preventDefault();
            setDropRoomId(room.id);
            setDropDate(dateFromDragEvent(event));
          }} onDragLeave={(event) => {
            if (event.currentTarget.contains(event.relatedTarget as Node | null)) return;
            if (dropRoomId === room.id) {
              setDropRoomId(null);
              setDropDate(null);
            }
          }} onDrop={(event) => onDrop(room, event)}>
            <button className="v2-room-cell" onClick={() => setSelectedRoomId(room.id)}><strong>{room.code}</strong><span>{room.room_type_name}</span></button>
            <div className="v2-state-cell"><span className={`badge ${room.operational_state}`}>{STATE_LABELS[room.operational_state]}</span></div>
            {days.map((day, index) => { const key = localDateString(day); const weekend = day.getDay() === 0 || day.getDay() === 6; const targeted = dropRoomId === room.id && dropDate === key; return <div key={key} className={`v2-day-bg ${weekend ? "weekend" : ""} ${key === today ? "today" : ""} ${targeted ? "drop-date-target" : ""}`} style={{ gridColumn: `${3 + index} / ${4 + index}` }} />; })}
            {room.blocks.map((block) => {
              const interactive = block.type === "RESERVATION" && Boolean(block.reservation_id);
              const bounds = block.reservation_id ? reservationBounds.get(block.reservation_id) : undefined;
              const canResizeLeft = interactive && block.reservation_status === "GUARANTEED" && bounds?.start === block.start;
              const canResizeRight = interactive && ["GUARANTEED", "CHECKED_IN"].includes(block.reservation_status || "") && bounds?.end === block.end;
              const resizing = resizeDraft?.blockId === block.id;
              const visualBlock = resizing ? {
                start: resizeDraft.edge === "LEFT" ? resizeDraft.checkIn : block.start,
                end: resizeDraft.edge === "RIGHT" ? resizeDraft.checkOut : block.end,
              } : block;
              const place = blockPlacement(visualBlock);
              if (!place) return null;
              const draggable = interactive && block.reservation_status === "GUARANTEED" && bounds?.segments === 1 && !resizing;

              return <div key={block.id} className={`v2-booking-bar ${block.type} ${interactive ? "interactive" : ""} ${draggable ? "draggable" : ""} ${resizing ? "resizing" : ""}`} style={{ gridColumn: place.column }} draggable={draggable} onDragStart={(event) => {
                if (!draggable || !block.reservation_id) return;
                setDraggingReservationId(block.reservation_id);
                event.dataTransfer.effectAllowed = "move";
                event.dataTransfer.setData("application/x-resort-reservation", block.reservation_id);
              }} onDragEnd={() => { setDraggingReservationId(null); setDropRoomId(null); setDropDate(null); }}>
                {canResizeLeft && block.reservation_id ? <button className="v2-resize-handle left" title="Потянуть дату заезда" aria-label="Изменить дату заезда" onPointerDown={(event) => beginResize(event, block, "LEFT")} onKeyDown={(event) => { if (["Enter", " "].includes(event.key)) { event.preventDefault(); setSelectedReservation({ id: block.reservation_id!, initialMode: "DATES" }); } }}>‹</button> : <span className="v2-resize-spacer" />}
                <button className="v2-bar-main" disabled={!interactive} onClick={() => interactive && block.reservation_id && setSelectedReservation({ id: block.reservation_id })} title={`${blockTitle(block)} · ${block.start} → ${block.end}${draggable ? " · можно перетащить по номеру и дате" : bounds && bounds.segments > 1 ? " · составное размещение: перенос через карточку" : ""}`}>
                  <strong>{blockTitle(block)}</strong><span>{block.booking_number || block.reason || ""}</span>
                </button>
                {canResizeRight && block.reservation_id ? <button className="v2-resize-handle right" title="Потянуть дату выезда" aria-label="Изменить дату выезда" onPointerDown={(event) => beginResize(event, block, "RIGHT")} onKeyDown={(event) => { if (["Enter", " "].includes(event.key)) { event.preventDefault(); setSelectedReservation({ id: block.reservation_id!, initialMode: "DATES" }); } }}>›</button> : <span className="v2-resize-spacer" />}
                {resizing && <span className="v2-resize-live">{resizeDraft.checkIn} → {resizeDraft.checkOut}</span>}
              </div>;
            })}
          </div>)}
        </div>
      </div>}
    </section>

    {selectedRoomId && <RoomDetailModal roomId={selectedRoomId} onClose={() => setSelectedRoomId(null)} />}
    {selectedReservation && <ChessboardReservationModal reservationId={selectedReservation.id} rooms={data?.rooms || []} initialMode={selectedReservation.initialMode} initialTargetRoomId={selectedReservation.targetRoomId} initialCheckIn={selectedReservation.initialCheckIn} initialCheckOut={selectedReservation.initialCheckOut} onClose={() => setSelectedReservation(null)} onUpdated={() => setRefreshToken((x) => x + 1)} />}
  </main>;
}
