"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type User = { id: string; role: string; display_name: string };
type Task = {
  id: string;
  type: "HOUSEKEEPING" | "MAINTENANCE" | "GUEST_REQUEST";
  status: string;
  priority: string;
  title: string;
  description?: string | null;
  room_id?: string | null;
  room_code?: string | null;
  room_state?: string | null;
  assigned_to_name?: string | null;
  created_at: string;
};
type Room = { id: string; code: string; room_type_name: string; operational_state: string };

const typeLabel: Record<string, string> = { HOUSEKEEPING: "Уборка", MAINTENANCE: "Ремонт", GUEST_REQUEST: "Запрос гостя" };
const statusLabel: Record<string, string> = { OPEN: "Открыта", IN_PROGRESS: "В работе", IN_INSPECTION: "Проверка", DONE: "Готово", CANCELLED: "Отменена" };

function dateTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }).format(date);
}

export default function OperationsBoard({ user }: { user: User }) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [filter, setFilter] = useState("ACTIVE");
  const [typeFilter, setTypeFilter] = useState("ALL");
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [taskType, setTaskType] = useState(user.role === "TECHNICIAN" ? "MAINTENANCE" : "HOUSEKEEPING");
  const [roomId, setRoomId] = useState("");
  const [title, setTitle] = useState("");
  const [priority, setPriority] = useState("NORMAL");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const taskResponse = await fetch("/core/api/v1/ops/tasks?limit=250", { cache: "no-store" });
      if (!taskResponse.ok) throw new Error("Не удалось загрузить задачи");
      const taskData = await taskResponse.json();
      setTasks(taskData.items || []);

      if (["OWNER", "MANAGER"].includes(user.role)) {
        const today = new Date();
        const tomorrow = new Date(today); tomorrow.setDate(today.getDate() + 1);
        const iso = (d: Date) => d.toISOString().slice(0, 10);
        const gridResponse = await fetch(`/core/api/v1/pms/grid?start=${iso(today)}&end=${iso(tomorrow)}`, { cache: "no-store" });
        if (gridResponse.ok) {
          const grid = await gridResponse.json();
          setRooms((grid.rooms || []).map((r: any) => ({ id: r.id, code: r.code, room_type_name: r.room_type_name, operational_state: r.operational_state })));
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка загрузки");
    } finally {
      setLoading(false);
    }
  }, [user.role]);

  useEffect(() => { load(); }, [load]);

  const activeTasks = useMemo(() => tasks.filter((task) => !["DONE", "CANCELLED"].includes(task.status)), [tasks]);
  const metrics = useMemo(() => ({
    active: activeTasks.length,
    unassigned: activeTasks.filter((task) => !task.assigned_to_name).length,
    housekeeping: activeTasks.filter((task) => task.type === "HOUSEKEEPING").length,
    maintenance: activeTasks.filter((task) => task.type === "MAINTENANCE").length,
    inspection: activeTasks.filter((task) => task.status === "IN_INSPECTION").length,
  }), [activeTasks]);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return tasks.filter((task) => {
      const statusMatches = filter === "ALL" ? true : filter === "ACTIVE" ? !["DONE", "CANCELLED"].includes(task.status) : task.status === filter;
      const typeMatches = typeFilter === "ALL" || task.type === typeFilter;
      const queryMatches = !q || [task.title, task.description, task.room_code, task.assigned_to_name, typeLabel[task.type], statusLabel[task.status]]
        .some((value) => value?.toLowerCase().includes(q));
      return statusMatches && typeMatches && queryMatches;
    });
  }, [tasks, filter, typeFilter, query]);

  async function updateStatus(task: Task, status: string) {
    setError(null);
    try {
      const response = await fetch(`/core/api/v1/ops/tasks/${task.id}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Не удалось изменить статус");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка обновления");
    }
  }

  async function createTask(event: FormEvent) {
    event.preventDefault();
    if (!title.trim()) return;
    setCreating(true);
    setError(null);
    try {
      const response = await fetch("/core/api/v1/ops/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type: taskType, room_id: roomId || null, priority, title: title.trim(), source: "PMS" }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Не удалось создать задачу");
      setTitle("");
      setRoomId("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка создания");
    } finally {
      setCreating(false);
    }
  }

  const canCreate = ["OWNER", "MANAGER", "MAID", "TECHNICIAN"].includes(user.role);

  return (
    <main className="work-shell">
      <div className="work-head">
        <div><p className="eyebrow">Операции · персонал</p><h1>Задачи пансионата</h1><p className="subtitle">Уборка, ремонт и запросы гостей с синхронизацией статуса номера.</p></div>
        <button className="btn" onClick={load}>Обновить</button>
      </div>

      <div className="summary">
        <div className="summary-card"><strong>{metrics.active}</strong><span>активных задач</span></div>
        <div className="summary-card"><strong>{metrics.unassigned}</strong><span>без ответственного</span></div>
        <div className="summary-card"><strong>{metrics.housekeeping}</strong><span>уборка</span></div>
        <div className="summary-card"><strong>{metrics.maintenance}</strong><span>ремонт</span></div>
        <div className="summary-card"><strong>{metrics.inspection}</strong><span>на проверке</span></div>
      </div>

      <div className="controls">
        <div className="control"><label>Поиск</label><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Номер, задача, сотрудник…" /></div>
        <div className="control"><label>Статус</label><select value={filter} onChange={(e) => setFilter(e.target.value)}><option value="ACTIVE">Активные</option><option value="OPEN">Открытые</option><option value="IN_PROGRESS">В работе</option><option value="IN_INSPECTION">На проверке</option><option value="DONE">Готовые</option><option value="CANCELLED">Отменённые</option><option value="ALL">Все</option></select></div>
        <div className="control"><label>Тип</label><select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}><option value="ALL">Все типы</option><option value="HOUSEKEEPING">Уборка</option><option value="MAINTENANCE">Ремонт</option><option value="GUEST_REQUEST">Запрос гостя</option></select></div>
      </div>

      {error && <div className="error-box">{error}</div>}
      {canCreate && <form className="task-create" onSubmit={createTask}>
        <select value={taskType} onChange={(e) => setTaskType(e.target.value)} disabled={user.role === "MAID" || user.role === "TECHNICIAN"}>
          {user.role !== "TECHNICIAN" && <option value="HOUSEKEEPING">Уборка</option>}
          {user.role !== "MAID" && <option value="MAINTENANCE">Ремонт</option>}
          {["OWNER", "MANAGER"].includes(user.role) && <option value="GUEST_REQUEST">Запрос гостя</option>}
        </select>
        {["OWNER", "MANAGER"].includes(user.role) ? <select value={roomId} onChange={(e) => setRoomId(e.target.value)}><option value="">Без номера</option>{rooms.map((room) => <option key={room.id} value={room.id}>{room.code} · {room.room_type_name} · {room.operational_state}</option>)}</select> : <input value={roomId} onChange={(e) => setRoomId(e.target.value)} placeholder="ID номера (из Telegram/PWA)" />}
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Что нужно сделать" required minLength={2} />
        <select value={priority} onChange={(e) => setPriority(e.target.value)}><option value="NORMAL">Обычный</option><option value="HIGH">Высокий</option><option value="URGENT">Срочно</option><option value="LOW">Низкий</option></select>
        <button className="btn primary" disabled={creating}>{creating ? "Создаю…" : "Создать задачу"}</button>
      </form>}
      {loading ? <div className="loading">Загрузка задач…</div> : <div className="task-grid">
        {visible.length === 0 && <div className="empty">Задач по выбранным условиям нет.</div>}
        {visible.map((task) => <article className={`task-card p-${task.priority}`} key={task.id}>
          <div className="task-meta"><span>{typeLabel[task.type] || task.type}</span><b>{statusLabel[task.status] || task.status}</b></div>
          <h3>{task.title}</h3>
          <p>{task.room_code ? `Номер ${task.room_code}` : "Без привязки к номеру"}{task.room_state ? ` · ${task.room_state}` : ""}</p>
          <p>{task.assigned_to_name ? `Ответственный: ${task.assigned_to_name}` : "Ответственный не назначен"} · создана {dateTime(task.created_at)}</p>
          {task.description && <p>{task.description}</p>}
          <div className="task-actions">
            {task.status === "OPEN" && <button className="btn" onClick={() => updateStatus(task, "IN_PROGRESS")}>Взять в работу</button>}
            {task.type === "HOUSEKEEPING" && task.status === "IN_PROGRESS" && <button className="btn primary" onClick={() => updateStatus(task, "IN_INSPECTION")}>Уборка закончена → проверка</button>}
            {task.type === "HOUSEKEEPING" && task.status === "IN_INSPECTION" && ["OWNER", "MANAGER"].includes(user.role) && <button className="btn primary" onClick={() => updateStatus(task, "DONE")}>Принять номер → CLEAN</button>}
            {task.type === "MAINTENANCE" && task.status === "IN_PROGRESS" && <button className="btn primary" onClick={() => updateStatus(task, "DONE")}>Ремонт завершён</button>}
            {task.type === "GUEST_REQUEST" && task.status === "IN_PROGRESS" && ["OWNER", "MANAGER"].includes(user.role) && <button className="btn primary" onClick={() => updateStatus(task, "DONE")}>Выполнено</button>}
          </div>
        </article>)}
      </div>}
    </main>
  );
}
