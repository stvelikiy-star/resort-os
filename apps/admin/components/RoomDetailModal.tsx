"use client";

import { useEffect, useMemo, useState } from "react";

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

function dateTime(value?: string | null) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" }).format(date);
}

export default function RoomDetailModal({ roomId, onClose }: { roomId: string; onClose: () => void; onUpdated?: () => void }) {
  const [data, setData] = useState<RoomDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [section, setSection] = useState<"TASKS" | "BLOCKS">("TASKS");

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(null);
    fetch(`/core/api/v1/admin/rooms/${roomId}`, { cache: "no-store" })
      .then(async (response) => {
        const body = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(body.detail || "Не удалось открыть номер");
        return body as RoomDetail;
      })
      .then((body) => { if (alive) setData(body); })
      .catch((e) => { if (alive) setError(e instanceof Error ? e.message : "Ошибка карточки номера"); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [roomId]);

  const activeTasks = useMemo(() => data?.tasks.filter((task) => !["DONE", "CANCELLED"].includes(task.status)) || [], [data]);
  const activeBlocks = useMemo(() => data?.blocks.filter((block) => block.active) || [], [data]);

  return <div className="room-detail-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <section className="room-detail-modal" role="dialog" aria-modal="true">
      {loading ? <div className="loading">Загрузка номера…</div> : error ? <div className="error-box">{error}</div> : data && <>
        <header className="room-detail-head">
          <div><p className="eyebrow">Карточка номера</p><h2>№ {data.room.code}</h2><p>{data.room.room_type_name}</p></div>
          <button className="btn" onClick={onClose}>Закрыть</button>
        </header>

        <div className="room-detail-status">
          <span className={`badge ${data.room.operational_state}`}>{stateLabel[data.room.operational_state] || data.room.operational_state}</span>
          <span>Активных задач: <b>{activeTasks.length}</b></span>
          <span>Активных блоков: <b>{activeBlocks.length}</b></span>
        </div>

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
