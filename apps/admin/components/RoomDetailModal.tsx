"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type RoomDetail = {
  room: {
    id: string;
    code: string;
    name: string;
    room_type_code: string;
    room_type_name: string;
    capacity_adults: number;
    capacity_children?: number | null;
    building_or_zone?: string | null;
    floor?: string | null;
    beds_raw?: string | null;
    area?: string | null;
    operational_state: string;
    notes?: string | null;
    updated_at: string;
  };
  blocks: Array<{
    id: string;
    type: string;
    start: string;
    end: string;
    active: boolean;
    reason?: string | null;
    reservation?: {
      id: string;
      booking_number: string;
      status: string;
      guest_name?: string | null;
    } | null;
  }>;
  tasks: Array<{
    id: string;
    type: string;
    status: string;
    priority: string;
    title: string;
    description?: string | null;
    assigned_to?: string | null;
    source?: string | null;
    created_at: string;
    updated_at: string;
    completed_at?: string | null;
  }>;
  truth: string;
};

type RoomState = "CLEAN" | "DIRTY" | "IN_INSPECTION" | "TECH_BLOCK";

const stateLabel: Record<string, string> = {
  UNKNOWN: "Не указан",
  CLEAN: "Готов",
  DIRTY: "Нужна уборка",
  IN_INSPECTION: "На проверке",
  TECH_BLOCK: "Технический блок",
};
const taskType: Record<string, string> = { HOUSEKEEPING: "Уборка", MAINTENANCE: "Ремонт", GUEST_REQUEST: "Запрос гостя" };
const taskStatus: Record<string, string> = { OPEN: "Открыта", IN_PROGRESS: "В работе", IN_INSPECTION: "Проверка", DONE: "Готово", CANCELLED: "Отменена" };
const blockType: Record<string, string> = { RESERVATION: "Бронь", MAINTENANCE: "Ремонт", MANUAL: "Ручной блок" };
const readinessActions: Array<{ state: RoomState; label: string; note: string }> = [
  { state: "CLEAN", label: "✓ Номер готов", note: "Можно заселять" },
  { state: "DIRTY", label: "Уборка", note: "Нужна подготовка" },
  { state: "IN_INSPECTION", label: "На проверку", note: "Ждёт контроля" },
  { state: "TECH_BLOCK", label: "Ремонт / блок", note: "Не заселять" },
];

function dateTime(value?: string | null) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" }).format(date);
}

export default function RoomDetailModal({ roomId, onClose, onUpdated }: { roomId: string; onClose: () => void; onUpdated?: () => void }) {
  const [data, setData] = useState<RoomDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busyState, setBusyState] = useState<RoomState | null>(null);
  const [section, setSection] = useState<"TASKS" | "BLOCKS">("TASKS");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/core/api/v1/admin/rooms/${roomId}`, { cache: "no-store" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Не удалось открыть номер");
      setData(body as RoomDetail);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Ошибка карточки номера");
    } finally {
      setLoading(false);
    }
  }, [roomId]);

  useEffect(() => { void load(); }, [load]);

  const activeTasks = useMemo(() => data?.tasks.filter((task) => !["DONE", "CANCELLED"].includes(task.status)) || [], [data]);
  const activeBlocks = useMemo(() => data?.blocks.filter((block) => block.active) || [], [data]);

  async function setReadiness(nextState: RoomState) {
    if (!data || busyState) return;
    if (nextState === "TECH_BLOCK" && !window.confirm(`Поставить номер ${data.room.code} в технический блок? Заселение должно быть остановлено до снятия блока.`)) return;

    setBusyState(nextState);
    setError(null);
    setNotice(null);
    try {
      // Normal housekeeping acceptance must close the inspection task as well as
      // set the room CLEAN. This prevents a green room with an orphaned inspection.
      const inspection = data.tasks.find((task) => task.type === "HOUSEKEEPING" && task.status === "IN_INSPECTION");
      const response = nextState === "CLEAN" && inspection
        ? await fetch(`/core/api/v1/ops/tasks/${inspection.id}/status`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status: "DONE" }),
          })
        : await fetch(`/core/api/v1/ops/rooms/${roomId}/state`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ state: nextState }),
          });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = typeof body?.detail === "string" ? body.detail : body?.detail?.code || `HTTP ${response.status}`;
        throw new Error(detail);
      }
      setNotice(nextState === "CLEAN" ? "Номер подтверждён как готовый." : `Статус: ${stateLabel[nextState]}.`);
      await load();
      onUpdated?.();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось изменить готовность номера");
    } finally {
      setBusyState(null);
    }
  }

  return <div className="room-detail-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <section className="room-detail-modal" role="dialog" aria-modal="true">
      {loading && !data ? <div className="loading">Загрузка номера…</div> : error && !data ? <div className="error-box">{error}</div> : data && <>
        <header className="room-detail-head">
          <div><p className="eyebrow">Карточка номера</p><h2>№ {data.room.code}</h2><p>{data.room.room_type_name}</p></div>
          <button className="btn" onClick={onClose}>Закрыть</button>
        </header>

        <div className="room-detail-status">
          <span className={`badge ${data.room.operational_state}`}>{stateLabel[data.room.operational_state] || data.room.operational_state}</span>
          <span>Активных задач: <b>{activeTasks.length}</b></span>
          <span>Активных блоков: <b>{activeBlocks.length}</b></span>
        </div>

        <section className="room-readiness-control" aria-label="Готовность номера">
          <div className="room-readiness-head"><div><small>Быстрый статус</small><strong>Готовность номера</strong></div><span>Изменение сразу сохраняется в Resort Core</span></div>
          <div className="room-readiness-actions">
            {readinessActions.map((action) => <button key={action.state} type="button" className={`room-readiness-button ${action.state} ${data.room.operational_state === action.state ? "active" : ""}`} disabled={busyState !== null} onClick={() => void setReadiness(action.state)}><strong>{busyState === action.state ? "Сохраняю…" : action.label}</strong><small>{action.note}</small></button>)}
          </div>
          {notice && <div className="content-message success">{notice}</div>}
          {error && <div className="error-box">{error}</div>}
        </section>

        <section className="room-detail-facts">
          <div><small>Категория</small><strong>{data.room.room_type_name}</strong></div>
          <div><small>Основных мест</small><strong>{data.room.capacity_adults}</strong></div>
          <div><small>Зона / корпус</small><strong>{data.room.building_or_zone || "Не указано"}</strong></div>
          <div><small>Этаж</small><strong>{data.room.floor || "Не указан"}</strong></div>
          <div><small>Кровати · исходные данные</small><strong>{data.room.beds_raw || "Не указано"}</strong></div>
          <div><small>Площадь</small><strong>{data.room.area ? `${data.room.area} м²` : "Не указана"}</strong></div>
        </section>

        {data.room.notes && <div className="room-detail-note"><small>Примечание</small><p>{data.room.notes}</p></div>}

        <nav className="room-detail-tabs">
          <button className={section === "TASKS" ? "active" : ""} onClick={() => setSection("TASKS")}>Уборка и ремонт · {data.tasks.length}</button>
          <button className={section === "BLOCKS" ? "active" : ""} onClick={() => setSection("BLOCKS")}>Брони и блоки · {data.blocks.length}</button>
        </nav>

        {section === "TASKS" && <div className="room-detail-list">
          {data.tasks.length === 0 && <div className="empty small">Для номера задач ещё нет.</div>}
          {data.tasks.map((task) => <article key={task.id} className="room-detail-item">
            <div><span>{taskType[task.type] || task.type}</span><b>{taskStatus[task.status] || task.status}</b></div>
            <h3>{task.title}</h3>
            <p>{task.assigned_to ? `Ответственный: ${task.assigned_to}` : "Ответственный не назначен"}</p>
            {task.description && <p>{task.description}</p>}
            <small>Создана: {dateTime(task.created_at)}{task.completed_at ? ` · завершена: ${dateTime(task.completed_at)}` : ""}{task.source ? ` · ${task.source}` : ""}</small>
          </article>)}
        </div>}

        {section === "BLOCKS" && <div className="room-detail-list">
          {data.blocks.length === 0 && <div className="empty small">Блоков по номеру ещё нет.</div>}
          {data.blocks.map((block) => <article key={block.id} className="room-detail-item">
            <div><span>{blockType[block.type] || block.type}</span><b>{block.active ? "Активен" : "Не активен"}</b></div>
            <h3>{block.reservation?.booking_number || block.reason || blockType[block.type] || block.type}</h3>
            <p>{block.start} → {block.end}</p>
            {block.reservation && <p>{block.reservation.guest_name || "Гость"} · {block.reservation.status}</p>}
          </article>)}
        </div>}

        <p className="room-detail-truth">Карточка показывает только сохранённые данные Resort Core. Пустые корпус, этаж, площадь или конфигурация не заполняются предположениями.</p>
      </>}
    </section>
  </div>;
}
