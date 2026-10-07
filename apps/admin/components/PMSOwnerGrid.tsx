"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import PMSNewReservationModal from "./PMSNewReservationModal";
import { pmsOwnerRoomDisplayLabel, pmsRoomDisplayNumber, pmsStaffBuildingLabel } from "./PMSRoomDisplayLabel";
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

const AK_BERMET_STAFF_GROUP_ORDER = [
  "Корпус №1",
  "Корпус №2",
  "Корпус №3",
  "GARDEN",
  "Кирпичные",
  "Деревянные",
  "Сруб",
];

function akBermetGroupRank(label: string) {
  const index = AK_BERMET_STAFF_GROUP_ORDER.indexOf(label);
  return index === -1 ? AK_BERMET_STAFF_GROUP_ORDER.length : index;
}

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

function compactMoney(value: number) {
  return new Intl.NumberFormat("ru-RU").format(value);
}

export default function PMSOwnerGrid({ agentMode = false, readOnlyMode = false }: { agentMode?: boolean; readOnlyMode?: boolean }) {
  const [start, setStart] = useState(() => {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), now.getDate());
  });
  const [windowDays, setWindowDays] = useState(31);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("ALL");
  const [building, setBuilding] = useState("ALL");
  const [availability, setAvailability] = useState("ALL");
  const [locale, setLocale] = useState("ru-RU");
  useEffect(() => {
    const update = () => setLocale(({ ky: "ky-KG", kk: "kk-KZ", en: "en-US" } as Record<string, string>)[document.documentElement.lang] || "ru-RU");
    update();
    const observer = new MutationObserver(update);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["lang"] });
    return () => observer.disconnect();
  }, []);
  const filterCopy: Record<string, string[]> = {
    "Корпус": ["Корпус", "Корпус", "Building"],
    "Все корпуса": ["Бардык корпустар", "Барлық корпустар", "All buildings"],
    "Доступность": ["Жеткиликтүүлүк", "Қолжетімділік", "Availability"],
    "Все номера": ["Бардык бөлмөлөр", "Барлық бөлмелер", "All rooms"],
    "Свободны весь период": ["Бүт мезгилге бош", "Бүкіл кезеңге бос", "Free for entire period"],
    "Есть занятые ночи": ["Бош эмес түндөр бар", "Бос емес түндер бар", "Has occupied nights"],
    "На ремонте": ["Оңдоодо", "Жөндеуде", "Under repair"],
    "Месяц": ["Ай", "Ай", "Month"], "Год": ["Жыл", "Жыл", "Year"],
    "Предыдущий месяц": ["Мурунку ай", "Алдыңғы ай", "Previous month"],
    "Следующий месяц": ["Кийинки ай", "Келесі ай", "Next month"],
    "Сбросить фильтры": ["Чыпкаларды тазалоо", "Сүзгілерді тазалау", "Reset filters"],
    "Номер, гость, бронь…": ["Бөлмө, конок, бронь…", "Бөлме, қонақ, бронь…", "Room, guest, booking…"],
  };
  const copy = (text: string) => locale === "ru-RU" ? text : (filterCopy[text]?.[locale === "ky-KG" ? 0 : locale === "kk-KZ" ? 1 : 2] || text);
  const years = Array.from({ length: 21 }, (_, i) => new Date().getFullYear() - 5 + i);
  if (!years.includes(start.getFullYear())) years.push(start.getFullYear());
  years.sort((a, b) => a - b);
  function jumpMonth(year: number, month: number) {
    setStart(new Date(year, month, 1));
    setSelection(null);
  }
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
      const gridResponse = await fetch(`/core/api/v1/pms/grid?${params}`, { cache: "no-store" });
      const gridBody = await gridResponse.json().catch(() => ({}));
      if (!gridResponse.ok) throw new Error(typeof gridBody.detail === "string" ? gridBody.detail : `Grid HTTP ${gridResponse.status}`);
      setData(gridBody as GridResponse);
      if (agentMode) {
        setFinance([]);
      } else {
        const financeResponse = await fetch("/core/api/v1/admin/reception/reservations?limit=500", { cache: "no-store" });
        const financeBody = await financeResponse.json().catch(() => ({}));
        setFinance(financeResponse.ok && Array.isArray(financeBody.items) ? financeBody.items : []);
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось загрузить шахматку");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [startIso, endIso, agentMode]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    const timer = window.setInterval(() => void load(), 60000);
    return () => window.clearInterval(timer);
  }, [load]);

  useEffect(() => {
    if (agentMode) {
      setRealtime("offline");
      return;
    }
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
  }, [startIso, endIso, agentMode]);

  const financeById = useMemo(() => new Map(finance.map((item) => [item.id, item])), [finance]);
  const categories = useMemo(() => Array.from(new Set((data?.rooms || []).map((room) => room.room_type_name))), [data]);
  const buildings = useMemo(() => Array.from(new Set((data?.rooms || []).map((room) => room.building_or_zone).filter((value): value is string => Boolean(value)))), [data]);
  const akBermetMode = data?.property === "AK_BERMET_TEST";

  const grouped = useMemo(() => {
    const q = query.trim().toLowerCase();
    const rooms = (data?.rooms || []).filter((room) => {
      if (category !== "ALL" && room.room_type_name !== category) return false;
      if (building !== "ALL" && room.building_or_zone !== building) return false;
      const occupied = room.blocks.some((block) => block.start < endIso && block.end > startIso);
      if (availability === "FREE" && (occupied || room.operational_state === "TECH_BLOCK")) return false;
      if (availability === "OCCUPIED" && !occupied) return false;
      if (availability === "BLOCKED" && room.operational_state !== "TECH_BLOCK") return false;
      if (!q) return true;
      return [room.code, room.beds_raw, room.room_type_name, room.building_or_zone, room.floor, ...room.blocks.flatMap((block) => [block.guest_name, block.booking_number])].some((value) => value?.toLowerCase().includes(q));
    });
    const map = new Map<string, Room[]>();
    rooms.forEach((room) => {
      const label = akBermetMode ? pmsStaffBuildingLabel(room.building_or_zone, data?.property) : (OWNER_GROUP[room.room_type_name] || room.room_type_name);
      const current = map.get(label) || [];
      current.push(room);
      map.set(label, current);
    });
    const groups = Array.from(map.entries()).map(([label, items]) => ({
      label,
      rooms: items.sort((left, right) =>
        akBermetMode
          ? pmsRoomDisplayNumber(left, data?.property).localeCompare(pmsRoomDisplayNumber(right, data?.property), "ru", { numeric: true, sensitivity: "base" })
          : naturalRoomCode(left, right),
      ),
    }));
    if (akBermetMode) {
      groups.sort((left, right) =>
        akBermetGroupRank(left.label) - akBermetGroupRank(right.label) ||
        left.label.localeCompare(right.label, "ru", { numeric: true }),
      );
    }
    return groups;
  }, [data, query, category, building, availability, startIso, endIso, akBermetMode]);

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
    if (readOnlyMode || !isFree(room, day)) return;
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

  function moveSelection(event: React.PointerEvent<HTMLButtonElement>) {
    if (!selectingRef.current || !selectionRef.current) return;
    const hit = document.elementFromPoint(event.clientX, event.clientY)?.closest<HTMLElement>(".owner-night-cell");
    const day = hit?.dataset.night;
    const roomCode = hit?.dataset.roomCode;
    const room = roomById.get(selectionRef.current.roomId);
    if (!room || !day || room.code !== roomCode) return;
    extendSelection(room, day);
  }

  const finishSelection = useCallback(() => {
    if (readOnlyMode || !selectingRef.current || !selectionRef.current) return;
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
    setCreateOpen({ roomId: room.id, roomCode: pmsRoomDisplayNumber(room, data?.property), bedsRaw: room.beds_raw, checkIn: selectedRange.checkIn, checkOut: selectedRange.checkOut });
  }, [roomById, data?.property, readOnlyMode]);

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
    if (agentMode || readOnlyMode || !block.reservation_id) return;
    setBuilder({ reservationId: block.reservation_id, intent: { kind: "OPEN", segmentBlockId: block.id } });
  }

  const dayWidth = windowDays >= 31 ? 26 : 34;
  const template = `300px 58px repeat(${windowDays}, ${dayWidth}px)`;

  return (
    <section className="owner-grid-shell">
      <header className="owner-grid-title">
        <div>
          <p className="eyebrow">PMS · рабочая шахматка</p>
          <h1>Номер × ночь</h1>
          <p>{agentMode ? "Показываются свободные/занятые ночи. Чужие гости и финансы скрыты. Новая бронь создаётся только по открытому тарифу." : readOnlyMode ? "Режим администратора: шахматка доступна для просмотра. Создание и изменение брони выполняется в разделе «Ресепшен / Брони»." : "Выделите от одной до нужного количества свободных клеток. Цена и конфликты проверяются Resort Core до создания брони."}</p>
        </div>
        <div className={`owner-live ${realtime}`}><i />{realtime === "live" ? "LIVE" : realtime === "connecting" ? "CONNECT" : "HTTP"}</div>
      </header>

      <div className="owner-grid-toolbar">
        <label className="owner-grid-search"><span>⌕</span><input value={query} onChange={(event) => setQuery(event.target.value)} data-i18n-skip placeholder={copy("Номер, гость, бронь…")} /></label>
        <select value={category} onChange={(event) => setCategory(event.target.value)}>
          <option value="ALL">Все категории</option>
          {categories.map((item) => <option key={item} value={item}>{OWNER_GROUP[item] || item}</option>)}
        </select>
        <select data-i18n-skip aria-label={copy("Корпус")} value={building} onChange={(event) => setBuilding(event.target.value)}>
          <option value="ALL">{copy("Все корпуса")}</option>
          {buildings.map((item) => <option key={item} value={item}>{pmsStaffBuildingLabel(item, data?.property)}</option>)}
        </select>
        <select data-i18n-skip aria-label={copy("Доступность")} value={availability} onChange={(event) => setAvailability(event.target.value)}>
          <option value="ALL">{copy("Все номера")}</option><option value="FREE">{copy("Свободны весь период")}</option><option value="OCCUPIED">{copy("Есть занятые ночи")}</option><option value="BLOCKED">{copy("На ремонте")}</option>
        </select>
        <div className="owner-month-picker">
          <button data-i18n-skip aria-label={copy("Предыдущий месяц")} onClick={() => jumpMonth(start.getFullYear(), start.getMonth() - 1)}>‹</button>
          <select data-i18n-skip aria-label={copy("Месяц")} value={start.getMonth()} onChange={(event) => jumpMonth(start.getFullYear(), Number(event.target.value))}>
            {Array.from({ length: 12 }, (_, month) => <option key={month} value={month}>{new Date(2026, month, 1).toLocaleDateString(locale, { month: "long" })}</option>)}
          </select>
          <select data-i18n-skip aria-label={copy("Год")} value={start.getFullYear()} onChange={(event) => jumpMonth(Number(event.target.value), start.getMonth())}>{years.map((year) => <option key={year} value={year}>{year}</option>)}</select>
          <button data-i18n-skip aria-label={copy("Следующий месяц")} onClick={() => jumpMonth(start.getFullYear(), start.getMonth() + 1)}>›</button>
        </div>
        <div className="owner-date-nav">
          <button onClick={() => setStart(addDays(start, -windowDays))}>‹</button>
          <button onClick={() => setStart(new Date())}>Сегодня</button>
          <button onClick={() => setStart(addDays(start, windowDays))}>›</button>
        </div>
        <div className="owner-window-switch">
          {[14, 31].map((value) => <button key={value} aria-label={`Показать ${value} дней`} className={windowDays === value ? "active" : ""} onClick={() => setWindowDays(value)}>{value} дн.</button>)}
        </div>
        <button data-i18n-skip onClick={() => { setQuery(""); setCategory("ALL"); setBuilding("ALL"); setAvailability("ALL"); }}>{copy("Сбросить фильтры")}</button>
        <button className="owner-refresh" onClick={() => void load()} aria-label="Обновить шахматку">↻</button>
      </div>

      <div className="owner-selection-help">
        <strong>Новая бронь:</strong> зажмите первую свободную клетку и проведите до последней ночи. Один клик = 1 ночь. День выезда — правая граница и не занимает клетку.
      </div>
      {notice && <div className="owner-grid-notice" onClick={() => setNotice(null)}>{notice}</div>}
      {error && <div className="owner-grid-error">{error}</div>}

      <div className="owner-grid-scroll" data-window-days={windowDays}>
        <div className="owner-grid-head" style={{ gridTemplateColumns: template }}>
          <div className="owner-room-head">Номер / спальные места</div>
          <div className="owner-state-head">Статус</div>
          {days.map((day) => {
            const key = iso(day);
            return <div key={key} className={`owner-day-head ${key === today ? "today" : ""} ${[0, 6].includes(day.getDay()) ? "weekend" : ""}`}><strong>{day.getDate()}</strong><span>{day.toLocaleDateString(locale, { weekday: "short" }).slice(0, 2)}</span></div>;
          })}
        </div>

        {loading ? <div className="owner-grid-loading">Загрузка…</div> : grouped.map((group) => (
          <div key={group.label} className="owner-grid-group">
            <div className="owner-group-label"><strong>{group.label}</strong><span>{group.rooms.length}</span></div>
            {group.rooms.map((room) => (
              <div key={room.id} className={`owner-room-row state-${room.operational_state}`} style={{ gridTemplateColumns: template }}>
                <button className="owner-room-label" onClick={() => { if (!agentMode && !readOnlyMode) setRoomId(room.id); }} title={`${room.room_type_name}${room.beds_raw ? ` · ${room.beds_raw}` : ""}`}>
                  <strong>{akBermetMode ? `${pmsRoomDisplayNumber(room, data?.property)}${room.beds_raw ? ` · ${room.beds_raw}` : ""}` : pmsOwnerRoomDisplayLabel(room)}</strong>
                </button>
                <div className={`owner-room-state ${room.operational_state}`}>{ROOM_STATE[room.operational_state]}</div>

                {days.map((day, index) => {
                  const key = iso(day);
                  const free = isFree(room, key);
                  return (
                    <button
                      key={key}
                      type="button"
                      aria-label={`Номер ${pmsRoomDisplayNumber(room, data?.property)}, ночь ${key}${free ? ", свободно" : ", занято"}`}
                      data-room-code={room.code}
                      data-night={key}
                      data-free={free ? "true" : "false"}
                      className={`owner-night-cell ${key === today ? "today" : ""} ${[0, 6].includes(day.getDay()) ? "weekend" : ""} ${free ? "free" : "occupied"} ${isSelected(room.id, key) ? "selected" : ""}`}
                      style={{ gridColumn: `${3 + index} / ${4 + index}`, gridRow: 1 }}
                      onPointerDown={(event) => beginSelection(room, key, event)}
                      onPointerMove={moveSelection}
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
                  const financeTitle = financeItem
                    ? ` · Оплачено ${compactMoney(financeItem.paidKgs)} сом · Остаток ${compactMoney(financeItem.remainingKgs)} сом`
                    : "";
                  return (
                    <button
                      key={block.id}
                      type="button"
                      className={`owner-booking-bar type-${block.type.toLowerCase()} status-${(block.reservation_status || "").toLowerCase()} payment-${payment}`}
                      data-paid-kgs={financeItem?.paidKgs}
                      data-remaining-kgs={financeItem?.remainingKgs}
                      style={{ gridColumn: `${3 + startIndex} / ${3 + endIndex}`, gridRow: 1 }}
                      onPointerDown={(event) => event.stopPropagation()}
                      onClick={(event) => { event.stopPropagation(); openReservation(block); }}
                      title={`${agentMode && !block.guest_name && !block.booking_number ? "Занято" : (block.guest_name || block.reason || block.type)} · ${block.start} → ${block.end}${financeTitle}`}
                    >
                      <strong>{agentMode && !block.guest_name && !block.booking_number ? "Занято" : (block.guest_name || block.booking_number || block.reason || block.type)}</strong>
                      {!agentMode && financeItem && <span>{financeItem.paidKgs > 0 ? `Опл. ${compactMoney(financeItem.paidKgs)}` : "Без оплаты"}</span>}
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

      {!readOnlyMode && createOpen && <PMSNewReservationModal {...createOpen} agentMode={agentMode} onClose={() => { setCreateOpen(null); setSelection(null); selectionRef.current = null; }} onCreated={() => { setSelection(null); selectionRef.current = null; void load(); }} />}
      {!agentMode && !readOnlyMode && builder && <ReservationScheduleBuilder reservationId={builder.reservationId} rooms={allRooms.map((room) => ({ id: room.id, code: room.code, room_type_code: room.room_type_code, room_type_name: room.room_type_name, operational_state: room.operational_state, building_or_zone: room.building_or_zone, floor: room.floor }))} intent={builder.intent} onClose={() => setBuilder(null)} onUpdated={() => void load()} />}
      {!agentMode && !readOnlyMode && roomId && <RoomDetailModal roomId={roomId} onClose={() => setRoomId(null)} onUpdated={() => void load()} />}
    </section>
  );
}
