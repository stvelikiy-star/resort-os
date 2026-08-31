"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import PMSNewReservationModal from "./PMSNewReservationModal";
import ReservationScheduleBuilder, { ScheduleIntent } from "./ReservationScheduleBuilder";
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
  beds_raw?: string | null;
  operational_state: "UNKNOWN" | "CLEAN" | "DIRTY" | "IN_INSPECTION" | "TECH_BLOCK";
  blocks: Block[];
};

type GridResponse = { property: string; start: string; end: string; rooms: Room[] };
type BuilderOpen = { reservationId: string; intent: ScheduleIntent };
type Selection = { roomId: string; anchor: string; focus: string };
type CreateOpen = { roomId: string; roomCode: string; bedsRaw?: string | null; checkIn: string; checkOut: string };

type RealtimeMessage = { type: "pms.grid.snapshot" | "heartbeat"; data?: GridResponse };

type ReceptionItem = {
  id: string;
  totalKgs: number;
  paidKgs: number;
  remainingKgs: number;
};

const OWNER_GROUP: Record<string, string> = {
  "Одноместный, цоколь": "1м цоколь",
  "Двухместный стандарт, цоколь": "2м цоколь",
  "Одноместный, улучшенный": "Одноместный улучшенный",
  "Двухместный стандарт в коттеджном доме": "2х стандарт в коттедже",
  "Двухместный улучшенный": "2х улучшенный",
  "Полулюкс без балкона": "Полулюкс без балкона",
  "Люкс двухместный": "Люкс",
  "Люкс трехместный": "Люкс (3 местный)",
  "Двухкомнатный стандарт": "Двухкомнатный 4-х местный стандарт",
  "Двухкомнатный полулюкс": "Двухкомнатный 4-х местный полулюкс",
  "Апартаменты": "4-х местный люкс (апартаменты)",
  "Квартиры / апартаменты с кухней": "Новый корпус квартиры апартаменты",
};

const ROOM_STATE: Record<Room["operational_state"], string> = {
  UNKNOWN: "—",
  CLEAN: "Готов",
  DIRTY: "Уборка",
  IN_INSPECTION: "Проверка",
  TECH_BLOCK: "Ремонт",
};

function iso(value = new Date()) {
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

function shiftDate(value: string, amount: number) {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day + amount)).toISOString().slice(0, 10);
}

function ordinal(value: string) {
  const [year, month, day] = value.split("-").map(Number);
  return Math.floor(Date.UTC(year, month - 1, day) / 86400000);
}

function covers(block: Block, day: string) {
  return block.start <= day && day < block.end;
}

function range(selection: Selection) {
  const left = ordinal(selection.anchor) <= ordinal(selection.focus) ? selection.anchor : selection.focus;
  const right = left === selection.anchor ? selection.focus : selection.anchor;
  return { checkIn: left, checkOut: shiftDate(right, 1), nights: ordinal(right) - ordinal(left) + 1 };
}

function websocketBase() {
  const configured = process.env.NEXT_PUBLIC_CORE_WS_URL?.replace(/\/$/, "");
  if (configured) return configured;
  if (typeof window === "undefined") return "";
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const port = window.location.port === "3001" ? "8000" : window.location.port;
  return `${protocol}//${window.location.hostname}${port ? `:${port}` : ""}`;
}

function naturalRoomCode(left: Room, right: Room) {
  return left.code.localeCompare(right.code, "ru", { numeric: true, sensitivity: "base" });
}

export default function PMSOwnerGrid() {
  const [start, setStart] = useState(() => {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), now.getDate());
  });
  const [windowDays, setWindowDays] = useState(31);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("ALL");
  const [data, setData] = useState<GridResponse | null>(null);
  const [finance, setFinance] = useState<ReceptionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [realtime, setRealtime] = useState<"connecting" | "live" | "offline">("connecting");
  const [selection, setSelection] = useState<Selection | null>(null);
  const selectionRef = useRef<Selection | null>(null);
  const selectingRef = useRef(false);
  const [createOpen, setCreateOpen] = useState<CreateOpen | null>(null);
  const [builder, setBuilder] = useState<BuilderOpen | null>(null);
  const [roomId, setRoomId] = useState<string | null>(null);

  const days = useMemo(() => Array.from({ length: windowDays }, (_, index) => addDays(start, index)), [start, windowDays]);
  const startIso = iso(start);
  const endIso = iso(addDays(start, windowDays));
  const today = iso();

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ start: startIso, end: endIso });
      const [gridResponse, financeResponse] = await Promise.all([
        fetch(`/core/api/v1/pms/grid?${params}`, { cache: "no-store" }),
        fetch("/core/api/v1/admin/reception/reservations?limit=500", { cache: "no-store" }),
      ]);
      const gridBody = await gridResponse.json().catch(() => ({}));
      if (!gridResponse.ok) throw new Error(typeof gridBody.detail === "string" ? gridBody.detail : `Grid HTTP ${gridResponse.status}`);
      setData(gridBody as GridResponse);
      const financeBody = await financeResponse.json().catch(() => ({}));
      setFinance(financeResponse.ok && Array.isArray(financeBody.items) ? financeBody.items : []);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось загрузить шахматку");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [startIso, endIso]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    const timer = window.setInterval(() => void load(), 60000);
    return () => window.clearInterval(timer);
  }, [load]);

  useEffect(() => {
    const base = websocketBase();
    if (!base) return;
    let stopped = false;
    let socket: WebSocket | null = null;
    let timer: number | undefined;
    const connect = () => {
      if (stopped) return;
      setRealtime("connecting");
      socket = new WebSocket(`${base}/ws/pms/grid?${new URLSearchParams({ start: startIso, end: endIso })}`);
      socket.onopen = () => setRealtime("live");
      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as RealtimeMessage;
          if (message.type === "pms.grid.snapshot" && message.data) {
            setData(message.data);
            setRealtime("live");
          }
        } catch {
          // HTTP refresh remains the fallback.
        }
      };
      socket.onerror = () => socket?.close();
      socket.onclose = () => {
        if (stopped) return;
        setRealtime("offline");
        timer = window.setTimeout(connect, 3000);
      };
    };
    connect();
    return () => {
      stopped = true;
      if (timer) window.clearTimeout(timer);
      socket?.close();
    };
  }, [startIso, endIso]);

  const financeById = useMemo(() => new Map(finance.map((item) => [item.id, item])), [finance]);
  const categories = useMemo(() => Array.from(new Set((data?.rooms || []).map((room) => room.room_type_name))), [data]);

  const grouped = useMemo(() => {
    const q = query.trim().toLowerCase();
    const rooms = (data?.rooms || []).filter((room) => {
      if (category !== "ALL" && room.room_type_name !== category) return false;
      if (!q) return true;
      return [room.code, room.beds_raw, room.room_type_name, room.building_or_zone, room.floor].some((value) => value?.toLowerCase().includes(q));
    });
    const map = new Map<string, Room[]>();
    rooms.forEach((room) => {
      const label = OWNER_GROUP[room.room_type_name] || room.room_type_name;
      const current = map.get(label) || [];
      current.push(room);
      map.set(label, current);
    });
    return Array.from(map.entries()).map(([label, items]) => ({ label, rooms: items.sort(naturalRoomCode) }));
  }, [data, query, category]);

  const allRooms = useMemo(() => data?.rooms || [], [data]);
  const roomById = useMemo(() => new Map(allRooms.map((room) => [room.id, room])), [allRooms]);

  function isFree(room: Room, day: string) {
    return room.operational_state !== "TECH_BLOCK" && !room.blocks.some((block) => covers(block, day));
  }

  function isSelected(roomIdValue: string, day: string) {
    if (!selection || selection.roomId !== roomIdValue) return false;
    const selectedRange = range(selection);
    return selectedRange.checkIn <= day && day < selectedRange.checkOut;
  }

  function beginSelection(room: Room, day: string, event: React.PointerEvent<HTMLButtonElement>) {
    if (!isFree(room, day)) return;
    event.preventDefault();
    event.currentTarget.setPointerCapture?.(event.pointerId);
    const next = { roomId: room.id, anchor: day, focus: day };
    selectingRef.current = true;
    selectionRef.current = next;
    setSelection(next);
    setNotice(null);
  }

  function extendSelection(room: Room, day: string) {
    if (!selectingRef.current || selectionRef.current?.roomId !== room.id) return;
    const next = { ...selectionRef.current, focus: day } as Selection;
    selectionRef.current = next;
    setSelection(next);
  }

  const finishSelection = useCallback(() => {
    if (!selectingRef.current || !selectionRef.current) return;
    selectingRef.current = false;
    const selected = selectionRef.current;
    const room = roomById.get(selected.roomId);
    if (!room) {
      selectionRef.current = null;
      setSelection(null);
      return;
    }
    const selectedRange = range(selected);
    const invalidNight = Array.from({ length: selectedRange.nights }, (_, index) => shiftDate(selectedRange.checkIn, index)).find((day) => !isFree(room, day));
    if (invalidNight) {
      setNotice(`Диапазон пересекает занятую/закрытую ночь ${invalidNight}. Выберите только свободные клетки.`);
      selectionRef.current = null;
      setSelection(null);
      return;
    }
    setCreateOpen({ roomId: room.id, roomCode: room.code, bedsRaw: room.beds_raw, checkIn: selectedRange.checkIn, checkOut: selectedRange.checkOut });
  }, [roomById]);

  useEffect(() => {
    const finish = () => finishSelection();
    window.addEventListener("pointerup", finish);
    window.addEventListener("pointercancel", finish);
    return () => {
      window.removeEventListener("pointerup", finish);
      window.removeEventListener("pointercancel", finish);
    };
  }, [finishSelection]);

  function openReservation(block: Block) {
    if (!block.reservation_id) return;
    setBuilder({ reservationId: block.reservation_id, intent: { kind: "OPEN", segmentBlockId: block.id } });
  }

  const dayWidth = windowDays >= 31 ? 36 : 42;
  const template = `220px 66px repeat(${windowDays}, ${dayWidth}px)`;

  return (
    <section className="owner-grid-shell">
      <header className="owner-grid-title">
        <div>
          <p className="eyebrow">PMS · рабочая шахматка</p>
          <h1>Номер × ночь</h1>
          <p>Выделите от одной до нужного количества свободных клеток. Цена и конфликты проверяются Resort Core до создания брони.</p>
        </div>
        <div className={`owner-live ${realtime}`}><i />{realtime === "live" ? "LIVE" : realtime === "connecting" ? "CONNECT" : "HTTP"}</div>
      </header>

      <div className="owner-grid-toolbar">
        <label className="owner-grid-search"><span>⌕</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Номер, кровати, категория…" /></label>
        <select value={category} onChange={(event) => setCategory(event.target.value)}>
          <option value="ALL">Все категории</option>
          {categories.map((item) => <option key={item} value={item}>{OWNER_GROUP[item] || item}</option>)}
        </select>
        <div className="owner-date-nav">
          <button onClick={() => setStart(addDays(start, -windowDays))}>‹</button>
          <button onClick={() => setStart(new Date())}>Сегодня</button>
          <button onClick={() => setStart(addDays(start, windowDays))}>›</button>
        </div>
        <div className="owner-window-switch">
          {[14, 31].map((value) => <button key={value} className={windowDays === value ? "active" : ""} onClick={() => setWindowDays(value)}>{value} дн.</button>)}
        </div>
        <button className="owner-refresh" onClick={() => void load()}>↻</button>
      </div>

      <div className="owner-selection-help">
        <strong>Новая бронь:</strong> зажмите первую свободную клетку и проведите до последней ночи. Один клик = 1 ночь. День выезда — правая граница и не занимает клетку.
      </div>
      {notice && <div className="owner-grid-notice" onClick={() => setNotice(null)}>{notice}</div>}
      {error && <div className="owner-grid-error">{error}</div>}

      <div className="owner-grid-scroll">
        <div className="owner-grid-head" style={{ gridTemplateColumns: template }}>
          <div className="owner-room-head">Номер / спальные места</div>
          <div className="owner-state-head">Статус</div>
          {days.map((day) => {
            const key = iso(day);
            return <div key={key} className={`owner-day-head ${key === today ? "today" : ""} ${[0, 6].includes(day.getDay()) ? "weekend" : ""}`}><strong>{day.getDate()}</strong><span>{day.toLocaleDateString("ru-RU", { weekday: "short" }).slice(0, 2)}</span></div>;
          })}
        </div>

        {loading ? <div className="owner-grid-loading">Загрузка…</div> : grouped.map((group) => (
          <div key={group.label} className="owner-grid-group">
            <div className="owner-group-label"><strong>{group.label}</strong><span>{group.rooms.length}</span></div>
            {group.rooms.map((room) => (
              <div key={room.id} className={`owner-room-row state-${room.operational_state}`} style={{ gridTemplateColumns: template }}>
                <button className="owner-room-label" onClick={() => setRoomId(room.id)} title={room.room_type_name}>
                  <strong>{room.code}</strong>
                  <span>{room.beds_raw || room.room_type_name}</span>
                </button>
                <div className={`owner-room-state ${room.operational_state}`}>{ROOM_STATE[room.operational_state]}</div>

                {days.map((day, index) => {
                  const key = iso(day);
                  const free = isFree(room, key);
                  return (
                    <button
                      key={key}
                      type="button"
                      aria-label={`Номер ${room.code}, ночь ${key}${free ? ", свободно" : ", занято"}`}
                      data-room-code={room.code}
                      data-night={key}
                      data-free={free ? "true" : "false"}
                      className={`owner-night-cell ${key === today ? "today" : ""} ${[0, 6].includes(day.getDay()) ? "weekend" : ""} ${free ? "free" : "occupied"} ${isSelected(room.id, key) ? "selected" : ""}`}
                      style={{ gridColumn: `${3 + index} / ${4 + index}`, gridRow: 1 }}
                      onPointerDown={(event) => beginSelection(room, key, event)}
                      onPointerEnter={() => extendSelection(room, key)}
                    />
                  );
                })}

                {room.blocks.map((block) => {
                  const visibleStart = block.start < startIso ? startIso : block.start;
                  const visibleEnd = block.end > endIso ? endIso : block.end;
                  const startIndex = ordinal(visibleStart) - ordinal(startIso);
                  const endIndex = ordinal(visibleEnd) - ordinal(startIso);
                  if (endIndex <= 0 || startIndex >= windowDays || endIndex <= startIndex) return null;
                  const financeItem = block.reservation_id ? financeById.get(block.reservation_id) : undefined;
                  const payment = financeItem ? financeItem.remainingKgs <= 0 ? "paid" : financeItem.paidKgs > 0 ? "partial" : "unpaid" : "unknown";
                  return (
                    <button
                      key={block.id}
                      type="button"
                      className={`owner-booking-bar type-${block.type.toLowerCase()} status-${(block.reservation_status || "").toLowerCase()} payment-${payment}`}
                      style={{ gridColumn: `${3 + startIndex} / ${3 + endIndex}`, gridRow: 1 }}
                      onPointerDown={(event) => event.stopPropagation()}
                      onClick={(event) => { event.stopPropagation(); openReservation(block); }}
                      title={`${block.guest_name || block.reason || block.type} · ${block.start} → ${block.end}`}
                    >
                      <strong>{block.guest_name || block.booking_number || block.reason || block.type}</strong>
                      {financeItem && <span>{financeItem.remainingKgs <= 0 ? "Оплачено" : `Ост. ${new Intl.NumberFormat("ru-RU").format(financeItem.remainingKgs)}`}</span>}
                    </button>
                  );
                })}
              </div>
            ))}
          </div>
        ))}
      </div>

      <footer className="owner-grid-legend">
        <span><i className="free" /> свободная ночь</span>
        <span><i className="selected" /> выбранный диапазон</span>
        <span><i className="guaranteed" /> бронь</span>
        <span><i className="checked" /> проживает</span>
        <span><i className="maintenance" /> ремонт / блок</span>
      </footer>

      {createOpen && <PMSNewReservationModal {...createOpen} onClose={() => { setCreateOpen(null); setSelection(null); selectionRef.current = null; }} onCreated={() => { setSelection(null); selectionRef.current = null; void load(); }} />}
      {builder && <ReservationScheduleBuilder reservationId={builder.reservationId} rooms={allRooms.map((room) => ({ id: room.id, code: room.code, room_type_code: room.room_type_code, room_type_name: room.room_type_name, operational_state: room.operational_state, building_or_zone: room.building_or_zone, floor: room.floor }))} intent={builder.intent} onClose={() => setBuilder(null)} onUpdated={() => void load()} />}
      {roomId && <RoomDetailModal roomId={roomId} onClose={() => setRoomId(null)} onUpdated={() => void load()} />}
    </section>
  );
}
