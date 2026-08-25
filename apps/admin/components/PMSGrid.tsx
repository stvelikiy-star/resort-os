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

function addDays(value: Date, amount: number) {
  const next = new Date(value.getFullYear(), value.getMonth(), value.getDate());
  next.setDate(next.getDate() + amount);
  return next;
}

function dateRange(start: Date, count: number) {
  return Array.from({ length: count }, (_, index) => addDays(start, index));
}

function blockAt(room: Room, day: string) {
  return room.blocks.find((block) => block.start <= day && day < block.end);
}

function blockTitle(block: Block) {
  if (block.type === "RESERVATION") {
    return block.guest_name || block.booking_number || "Бронь";
  }
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

export default function PMSGrid() {
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

  const days = useMemo(() => dateRange(start, windowDays), [start, windowDays]);
  const end = useMemo(() => addDays(start, windowDays), [start, windowDays]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        start: localDateString(start),
        end: localDateString(end),
      });
      const response = await fetch(`/core/api/v1/pms/grid?${params}`, { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`Core API: HTTP ${response.status}`);
      }
      const payload = (await response.json()) as GridResponse;
      setData(payload);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось загрузить шахматку");
    } finally {
      setLoading(false);
    }
  }, [start, end, refreshToken]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    let socket: WebSocket | null = null;
    let stopped = false;
    let reconnectTimer: number | undefined;

    const params = new URLSearchParams({
      start: localDateString(start),
      end: localDateString(end),
    });
    const base = websocketBase();
    if (!base) return;
    const url = `${base}/ws/pms/grid?${params.toString()}`;

    function connect() {
      if (stopped) return;
      setRealtime("connecting");
      socket = new WebSocket(url);
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
          // Ignore malformed realtime frames; the HTTP snapshot remains the fallback source.
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
  }, [start, end]);

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
      const matchesSearch =
        !query ||
        room.code.toLocaleLowerCase("ru").includes(query) ||
        room.room_type_name.toLocaleLowerCase("ru").includes(query) ||
        (room.building_or_zone || "").toLocaleLowerCase("ru").includes(query);
      const matchesType = roomType === "ALL" || room.room_type_code === roomType;
      const matchesState = state === "ALL" || room.operational_state === state;
      return matchesSearch && matchesType && matchesState;
    });
  }, [data, roomType, search, state]);

  const counts = useMemo(() => {
    const result: Record<Room["operational_state"] | "TOTAL", number> = {
      TOTAL: rooms.length,
      UNKNOWN: 0,
      CLEAN: 0,
      DIRTY: 0,
      IN_INSPECTION: 0,
      TECH_BLOCK: 0,
    };
    rooms.forEach((room) => result[room.operational_state]++);
    return result;
  }, [rooms]);

  const today = localDateString(new Date());

  return (
    <main className="shell">
      <div className="topbar">
        <div>
          <p className="eyebrow">Resort OS · Three Crowns</p>
          <h1>Шахматка номеров</h1>
          <p className="subtitle">84 номера · реальные категории · данные из Resort Core</p>
        </div>
        <div className={`connection ${error ? "error" : "ok"}`}>
          {error ? "Core недоступен" : realtime === "live" ? "Realtime подключён" : loading ? "Обновление…" : realtime === "connecting" ? "Realtime подключается…" : "HTTP подключён"}
        </div>
      </div>

      <section className="controls" aria-label="Фильтры шахматки">
        <div className="control">
          <label htmlFor="search">Номер / категория</label>
          <input
            id="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Например 312 или Люкс"
          />
        </div>

        <div className="control">
          <label htmlFor="roomType">Категория</label>
          <select id="roomType" value={roomType} onChange={(event) => setRoomType(event.target.value)}>
            <option value="ALL">Все категории</option>
            {roomTypes.map(([code, name]) => (
              <option key={code} value={code}>{name}</option>
            ))}
          </select>
        </div>

        <div className="control">
          <label htmlFor="state">Состояние</label>
          <select id="state" value={state} onChange={(event) => setState(event.target.value)}>
            <option value="ALL">Все состояния</option>
            {Object.entries(STATE_LABELS).map(([code, label]) => (
              <option key={code} value={code}>{label}</option>
            ))}
          </select>
        </div>

        <div className="control">
          <label htmlFor="period">Период</label>
          <select id="period" value={windowDays} onChange={(event) => setWindowDays(Number(event.target.value))}>
            <option value={7}>7 дней</option>
            <option value={14}>14 дней</option>
            <option value={31}>31 день</option>
          </select>
        </div>

        <div className="date-actions">
          <button className="btn" onClick={() => setStart(addDays(start, -7))} aria-label="Назад 7 дней">←</button>
          <button className="btn" onClick={() => {
            const now = new Date();
            setStart(new Date(now.getFullYear(), now.getMonth(), now.getDate()));
          }}>Сегодня</button>
          <button className="btn" onClick={() => setStart(addDays(start, 7))} aria-label="Вперёд 7 дней">→</button>
          <button className="btn primary" onClick={() => setRefreshToken((value) => value + 1)}>Обновить</button>
        </div>
      </section>

      <section className="summary" aria-label="Сводка по номерам">
        <div className="summary-card"><strong>{counts.TOTAL}</strong><span>Показано номеров</span></div>
        <div className="summary-card"><strong>{counts.CLEAN}</strong><span>Готовы</span></div>
        <div className="summary-card"><strong>{counts.DIRTY}</strong><span>Требуют уборки</span></div>
        <div className="summary-card"><strong>{counts.IN_INSPECTION}</strong><span>На проверке</span></div>
        <div className="summary-card"><strong>{counts.TECH_BLOCK}</strong><span>Тех. блок</span></div>
        <div className="summary-card"><strong>{counts.UNKNOWN}</strong><span>Статус не задан</span></div>
      </section>

      <section className="grid-card">
        <div className="grid-toolbar">
          <div>
            <strong>{localDateString(start)}</strong> — <strong>{localDateString(addDays(end, -1))}</strong>
          </div>
          <div className="legend" aria-label="Легенда блоков">
            <span className="legend-item" style={{ "--legend": "var(--reservation)" } as React.CSSProperties}>Бронь</span>
            <span className="legend-item" style={{ "--legend": "var(--maintenance)" } as React.CSSProperties}>Ремонт</span>
            <span className="legend-item" style={{ "--legend": "var(--manual)" } as React.CSSProperties}>Ручной блок</span>
          </div>
        </div>

        {error && <div className="error-box">{error}. Проверьте Resort Core и повторите.</div>}
        {loading && !data ? (
          <div className="loading">Загружаю номера…</div>
        ) : rooms.length === 0 ? (
          <div className="empty">По выбранным фильтрам номеров нет.</div>
        ) : (
          <div className="grid-scroll">
            <table className="pms-table">
              <thead>
                <tr>
                  <th className="room-head">Номер</th>
                  <th className="state-head">Состояние</th>
                  {days.map((day) => {
                    const key = localDateString(day);
                    const weekday = new Intl.DateTimeFormat("ru-RU", { weekday: "short" }).format(day);
                    return (
                      <th key={key} className={`date-head ${key === today ? "today" : ""}`}>
                        <strong>{day.getDate()}</strong>
                        {weekday}
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody>
                {rooms.map((room) => (
                  <tr key={room.id}>
                    <td className="room-cell" title={`${room.room_type_name}${room.beds_raw ? ` · ${room.beds_raw}` : ""}`}>
                      <div className="room-code">{room.code}</div>
                      <div className="room-type">{room.room_type_name}</div>
                    </td>
                    <td className="state-cell">
                      <span className={`badge ${room.operational_state}`}>{STATE_LABELS[room.operational_state]}</span>
                    </td>
                    {days.map((day, index) => {
                      const key = localDateString(day);
                      const block = blockAt(room, key);
                      const weekend = day.getDay() === 0 || day.getDay() === 6;
                      const showBlockLabel = block && (block.start === key || index === 0);
                      return (
                        <td key={key} className={`day-cell ${weekend ? "weekend" : ""} ${key === today ? "today" : ""}`}>
                          {block && (
                            <div
                              className={`block ${block.type}`}
                              title={`${blockTitle(block)} · ${block.start} — ${block.end}`}
                            >
                              {showBlockLabel ? blockTitle(block) : ""}
                              {showBlockLabel && block.booking_number && (
                                <span className="muted">{block.booking_number}</span>
                              )}
                            </div>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}
