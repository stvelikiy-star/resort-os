"use client";

import { PointerEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

import styles from "./DiningFloorPlan.module.css";

type User = { id: string; role: string };
type Table = {
  id: string;
  code: string;
  name: string;
  seats: number;
  status: string;
  zone_label: string;
  floor_x?: number | null;
  floor_y?: number | null;
  floor_shape: "ROUND" | "SQUARE" | "RECTANGLE";
  notes?: string | null;
  active_orders: number;
  ready_orders: number;
};
type Session = {
  id: string;
  table_id: string;
  stay_id: string;
  reservation_id: string;
  status: "WAITING" | "SEATED";
  meal_type?: string | null;
  party_size: number;
  adults: number;
  children: number;
  guest_name: string;
  room_code?: string | null;
  booking_number: string;
  waiter_id?: string | null;
  waiter_name?: string | null;
  seated_at?: string | null;
  created_at: string;
};
type Payload = {
  service_date: string;
  editable: boolean;
  current_user_id: string;
  tables: Table[];
  sessions: Session[];
};

const STATUS: Record<string, string> = {
  AVAILABLE: "Свободен",
  RESERVED: "Ожидает",
  OCCUPIED: "Занят",
  CLEANING: "Уборка",
  OUT_OF_SERVICE: "Закрыт",
};
const MEAL: Record<string, string> = { BREAKFAST: "Завтрак", LUNCH: "Обед", DINNER: "Ужин", OTHER: "Другое" };

async function api(path: string, init?: RequestInit) {
  const response = await fetch(path, { cache: "no-store", ...init });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(typeof body?.detail === "string" ? body.detail : body?.detail?.code || "Ошибка Dining Floor");
  return body;
}

function clamp(value: number) { return Math.max(3, Math.min(97, value)); }
function elapsed(value?: string | null) {
  if (!value) return null;
  const minutes = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 60000));
  return `${minutes} мин`;
}

export default function DiningFloorPlan({ user }: { user: User }) {
  const [payload, setPayload] = useState<Payload | null>(null);
  const [tables, setTables] = useState<Table[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [zone, setZone] = useState("ALL");
  const [editMode, setEditMode] = useState(false);
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const canvasRef = useRef<HTMLDivElement>(null);

  const load = useCallback(async () => {
    if (draggingId) return;
    try {
      const body = await api("/core/api/v1/dining/floor-layout") as Payload;
      setPayload(body);
      setTables(body.tables ?? []);
      setSessions(body.sessions ?? []);
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось загрузить схему зала");
    }
  }, [draggingId]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    const timer = window.setInterval(() => void load(), 10000);
    return () => window.clearInterval(timer);
  }, [load]);

  const zones = useMemo(() => Array.from(new Set(tables.map((table) => table.zone_label || "Основной зал"))).sort(), [tables]);
  const visible = useMemo(() => tables.filter((table) => zone === "ALL" || table.zone_label === zone), [tables, zone]);
  const sessionByTable = useMemo(() => new Map(sessions.map((session) => [session.table_id, session])), [sessions]);
  const selected = tables.find((table) => table.id === selectedId) || null;
  const selectedSession = selected ? sessionByTable.get(selected.id) || null : null;
  const canEdit = Boolean(payload?.editable && ["OWNER", "MANAGER"].includes(user.role));

  async function patchTable(table: Table, quiet = false) {
    setBusy(table.id); if (!quiet) { setError(null); setNotice(null); }
    try {
      const body = await api(`/core/api/v1/dining/floor-layout/tables/${table.id}`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          floor_x: table.floor_x ?? 50,
          floor_y: table.floor_y ?? 50,
          zone_label: table.zone_label || "Основной зал",
          floor_shape: table.floor_shape || "ROUND",
        }),
      }) as Table;
      setTables((current) => current.map((item) => item.id === table.id ? { ...item, ...body } : item));
      if (!quiet) setNotice(`Стол ${table.code}: схема сохранена.`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось сохранить позицию стола");
      await load();
    } finally { setBusy(null); }
  }

  function point(event: PointerEvent<HTMLElement>) {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return null;
    return {
      x: clamp(((event.clientX - rect.left) / rect.width) * 100),
      y: clamp(((event.clientY - rect.top) / rect.height) * 100),
    };
  }

  function dragStart(event: PointerEvent<HTMLButtonElement>, table: Table) {
    setSelectedId(table.id);
    if (!canEdit || !editMode) return;
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    setDraggingId(table.id);
  }

  function dragMove(event: PointerEvent<HTMLButtonElement>, table: Table) {
    if (draggingId !== table.id || !canEdit || !editMode) return;
    const next = point(event);
    if (!next) return;
    setTables((current) => current.map((item) => item.id === table.id ? { ...item, floor_x: next.x, floor_y: next.y } : item));
  }

  function dragEnd(event: PointerEvent<HTMLButtonElement>, table: Table) {
    if (draggingId !== table.id || !canEdit || !editMode) return;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
    setDraggingId(null);
    const current = tables.find((item) => item.id === table.id) || table;
    void patchTable(current, true);
  }

  function updateSelected(patch: Partial<Table>) {
    if (!selected) return;
    setTables((current) => current.map((item) => item.id === selected.id ? { ...item, ...patch } : item));
  }

  return <section className={styles.shell}>
    <header className={styles.head}>
      <div><small>Live Dining Floor</small><h2>Схема зала</h2><p>Посадка связана с проживанием гостя. Координаты стола — только визуальная схема и не меняют финансовые или операционные факты.</p></div>
      <div className={styles.headActions}>{canEdit && <button className={editMode ? styles.editing : ""} onClick={() => setEditMode((value) => !value)}>{editMode ? "✓ Завершить расстановку" : "Расставить столы"}</button>}<button onClick={() => void load()}>↻ Обновить</button></div>
    </header>

    {error && <div className={styles.error}>{error}</div>}{notice && <div className={styles.notice}>{notice}</div>}

    <div className={styles.metrics}>
      <article><strong>{tables.filter((item) => item.status === "AVAILABLE").length}</strong><span>свободно</span></article>
      <article><strong>{sessions.filter((item) => item.status === "SEATED").length}</strong><span>за столами</span></article>
      <article><strong>{sessions.filter((item) => item.status === "WAITING").length}</strong><span>ожидаются</span></article>
      <article data-hot={tables.some((item) => item.ready_orders > 0)}><strong>{tables.reduce((sum, item) => sum + item.ready_orders, 0)}</strong><span>готово к выдаче</span></article>
    </div>

    <div className={styles.zoneTabs}><button className={zone === "ALL" ? styles.active : ""} onClick={() => setZone("ALL")}>Весь зал</button>{zones.map((item) => <button key={item} className={zone === item ? styles.active : ""} onClick={() => setZone(item)}>{item}</button>)}</div>

    <div className={styles.workspace}>
      <div className={styles.canvas} ref={canvasRef} data-edit={editMode}>
        <div className={styles.canvasLabel}><span>{zone === "ALL" ? "Все зоны" : zone}</span><small>{payload?.service_date || "сегодня"}</small></div>
        {visible.map((table, index) => {
          const session = sessionByTable.get(table.id);
          const x = table.floor_x ?? 10 + (index % 5) * 18;
          const y = table.floor_y ?? 15 + Math.floor(index / 5) * 24;
          return <button
            type="button"
            key={table.id}
            className={`${styles.table} ${selectedId === table.id ? styles.selected : ""}`}
            data-status={table.status}
            data-shape={table.floor_shape}
            data-dragging={draggingId === table.id}
            style={{ left: `${x}%`, top: `${y}%` }}
            onPointerDown={(event) => dragStart(event, table)}
            onPointerMove={(event) => dragMove(event, table)}
            onPointerUp={(event) => dragEnd(event, table)}
            onPointerCancel={(event) => dragEnd(event, table)}
            onClick={() => setSelectedId(table.id)}
          >
            {table.ready_orders > 0 && <b className={styles.readyBadge}>{table.ready_orders}</b>}
            <strong>{table.code}</strong>
            <span>{session ? `№ ${session.room_code || "—"}` : STATUS[table.status] || table.status}</span>
            {session && <small>{session.party_size} гост.</small>}
          </button>;
        })}
        {!visible.length && <div className={styles.empty}>В этой зоне столов нет.</div>}
      </div>

      <aside className={styles.inspector}>
        {!selected ? <div className={styles.emptyInspector}><strong>Выберите стол</strong><span>Нажмите на стол, чтобы увидеть гостя, официанта и активные заказы.</span></div> : <>
          <div className={styles.tableTitle}><div><small>{selected.zone_label}</small><h3>{selected.code} · {selected.name}</h3><span>{selected.seats} мест · {STATUS[selected.status] || selected.status}</span></div><b data-status={selected.status}>{selected.ready_orders > 0 ? `${selected.ready_orders} READY` : selected.active_orders ? `${selected.active_orders} заказ.` : "—"}</b></div>

          {selectedSession ? <section className={styles.guestCard}><small>{selectedSession.status === "SEATED" ? "ГОСТЬ ЗА СТОЛОМ" : "ОЖИДАЕТ"}</small><strong>№ {selectedSession.room_code || "—"} · {selectedSession.guest_name}</strong><span>{selectedSession.adults} взр. · {selectedSession.children} дет. · {MEAL[selectedSession.meal_type || ""] || selectedSession.meal_type || "Приём не указан"}</span><span>{selectedSession.waiter_name ? `Официант: ${selectedSession.waiter_name}` : "Официант не назначен"}</span>{selectedSession.status === "SEATED" && selectedSession.seated_at && <b>{elapsed(selectedSession.seated_at)} за столом</b>}</section> : <section className={styles.freeCard}><strong>Активной посадки нет</strong><span>Гостя можно закрепить через блок «Посадка и мои столы» ниже.</span></section>}

          {canEdit && <section className={styles.editor}>
            <div><small>OWNER / MANAGER</small><strong>Визуальная расстановка</strong></div>
            <label>Зона<input value={selected.zone_label} onChange={(event) => updateSelected({ zone_label: event.target.value })} /></label>
            <label>Форма<select value={selected.floor_shape} onChange={(event) => updateSelected({ floor_shape: event.target.value as Table["floor_shape"] })}><option value="ROUND">Круглый</option><option value="SQUARE">Квадратный</option><option value="RECTANGLE">Прямоугольный</option></select></label>
            <div className={styles.coordinates}><label>X<input type="number" min="0" max="100" step="0.1" value={(selected.floor_x ?? 50).toFixed(1)} onChange={(event) => updateSelected({ floor_x: clamp(Number(event.target.value)) })} /></label><label>Y<input type="number" min="0" max="100" step="0.1" value={(selected.floor_y ?? 50).toFixed(1)} onChange={(event) => updateSelected({ floor_y: clamp(Number(event.target.value)) })} /></label></div>
            <button disabled={busy === selected.id || !selected.zone_label.trim()} onClick={() => void patchTable(selected)}>{busy === selected.id ? "Сохраняю…" : "Сохранить параметры"}</button>
            <p>{editMode ? "Перетаскивайте столы прямо по схеме. Позиция сохраняется при отпускании." : "Включите «Расставить столы», чтобы перетаскивать их мышкой или пальцем."}</p>
          </section>}
        </>}
      </aside>
    </div>

    <div className={styles.legend}><span data-status="AVAILABLE">Свободен</span><span data-status="RESERVED">Ожидает</span><span data-status="OCCUPIED">Занят</span><span data-status="CLEANING">Уборка</span><span data-status="OUT_OF_SERVICE">Закрыт</span><small>Красный счётчик = блюда READY</small></div>
  </section>;
}
