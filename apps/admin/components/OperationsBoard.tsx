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
  assigned_to_id?: string | null;
  assigned_to_name?: string | null;
  created_at: string;
};
type Room = { id: string; code: string; room_type_name: string; operational_state: string };
type StaffAssignee = { id: string; display_name: string; role: string; active: boolean };
type HistoryItem = {
  id: string;
  actor_type: string;
  actor_name?: string | null;
  actor_role?: string | null;
  action: string;
  source?: string | null;
  result: string;
  after?: Record<string, unknown> | null;
  created_at: string;
};

const typeLabel: Record<string, string> = { HOUSEKEEPING: "Уборка", MAINTENANCE: "Ремонт", GUEST_REQUEST: "Запрос гостя" };
const statusLabel: Record<string, string> = { OPEN: "Открыта", IN_PROGRESS: "В работе", IN_INSPECTION: "Проверка", DONE: "Готово", CANCELLED: "Отменена" };
const actionLabel: Record<string, string> = { CREATE: "Создана", CLAIM: "Взята в работу", ASSIGN: "Назначен сотрудник", UNASSIGN: "Снято назначение", STATUS_CHANGE: "Изменён статус", VOICE_MAINTENANCE_INTAKE: "Создана голосом" };

function dateTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }).format(date);
}

export default function OperationsBoard({ user }: { user: User }) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [staff, setStaff] = useState<StaffAssignee[]>([]);
  const [filter, setFilter] = useState("ACTIVE");
  const [typeFilter, setTypeFilter] = useState("ALL");
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [assigningTaskId, setAssigningTaskId] = useState<string | null>(null);
  const [taskType, setTaskType] = useState(user.role === "TECHNICIAN" ? "MAINTENANCE" : "HOUSEKEEPING");
  const [roomId, setRoomId] = useState("");
  const [title, setTitle] = useState("");
  const [priority, setPriority] = useState("NORMAL");
  const [historyTaskId, setHistoryTaskId] = useState<string | null>(null);
  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const isManager = ["OWNER", "MANAGER"].includes(user.role);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const taskResponse = await fetch("/core/api/v1/ops/tasks?limit=250", { cache: "no-store" });
      if (!taskResponse.ok) throw new Error("Не удалось загрузить задачи");
      const taskData = await taskResponse.json();
      setTasks(taskData.items || []);

      if (isManager) {
        const today = new Date();
        const tomorrow = new Date(today); tomorrow.setDate(today.getDate() + 1);
        const iso = (d: Date) => d.toISOString().slice(0, 10);
        const [gridResponse, staffResponse] = await Promise.all([
          fetch(`/core/api/v1/pms/grid?start=${iso(today)}&end=${iso(tomorrow)}`, { cache: "no-store" }),
          fetch("/core/api/v1/admin/staff/overview", { cache: "no-store" }),
        ]);
        if (gridResponse.ok) {
          const grid = await gridResponse.json();
          setRooms((grid.rooms || []).map((r: any) => ({ id: r.id, code: r.code, room_type_name: r.room_type_name, operational_state: r.operational_state })));
        }
        if (staffResponse.ok) {
          const staffData = await staffResponse.json();
          setStaff((staffData.staff || []).filter((item: StaffAssignee) => item.active));
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка загрузки");
    } finally {
      setLoading(false);
    }
  }, [isManager]);

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

  function eligibleStaff(task: Task) {
    const expected = task.type === "HOUSEKEEPING" ? "MAID" : task.type === "MAINTENANCE" ? "TECHNICIAN" : null;
    return expected ? staff.filter((item) => item.role === expected) : [];
  }

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
      if (historyTaskId === task.id) await loadHistory(task.id, true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка обновления");
    }
  }

  async function assignTask(task: Task, assignedToId: string) {
    if (!isManager || !["HOUSEKEEPING", "MAINTENANCE"].includes(task.type)) return;
    setAssigningTaskId(task.id);
    setError(null);
    try {
      const response = await fetch(`/core/api/v1/ops/tasks/${task.id}/assignee`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ assigned_to_id: assignedToId || null }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Не удалось назначить сотрудника");
      await load();
      if (historyTaskId === task.id) await loadHistory(task.id, true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка назначения");
    } finally {
      setAssigningTaskId(null);
    }
  }

  async function loadHistory(taskId: string, force = false) {
    if (!force && historyTaskId === taskId) {
      setHistoryTaskId(null);
      setHistoryItems([]);
      return;
    }
    setHistoryTaskId(taskId);
    setHistoryLoading(true);
    setError(null);
    try {
      const response = await fetch(`/core/api/v1/ops/tasks/${taskId}/history`, { cache: "no-store" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Не удалось загрузить историю задачи");
      setHistoryItems(body.history || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка истории задачи");
      setHistoryItems([]);
    } finally {
      setHistoryLoading(false);
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
  const canSeeHistory = isManager;

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
          {isManager && <option value="GUEST_REQUEST">Запрос гостя</option>}
        </select>
        {isManager ? <select value={roomId} onChange={(e) => setRoomId(e.target.value)}><option value="">Без номера</option>{rooms.map((room) => <option key={room.id} value={room.id}>{room.code} · {room.room_type_name} · {room.operational_state}</option>)}</select> : <input value={roomId} onChange={(e) => setRoomId(e.target.value)} placeholder="ID номера (из Telegram/PWA)" />}
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

          {isManager && ["HOUSEKEEPING", "MAINTENANCE"].includes(task.type) && !["DONE", "CANCELLED"].includes(task.status) && <label className="task-assignee-control">
            <span>Ответственный</span>
            <select value={task.assigned_to_id || ""} disabled={assigningTaskId === task.id} onChange={(e) => assignTask(task, e.target.value)}>
              <option value="">Не назначен</option>
              {eligibleStaff(task).map((employee) => <option value={employee.id} key={employee.id}>{employee.display_name}</option>)}
            </select>
          </label>}

          <div className="task-actions">
            {task.status === "OPEN" && <button className="btn" onClick={() => updateStatus(task, "IN_PROGRESS")}>Взять в работу</button>}
            {task.type === "HOUSEKEEPING" && task.status === "IN_PROGRESS" && <button className="btn primary" onClick={() => updateStatus(task, "IN_INSPECTION")}>Уборка закончена → проверка</button>}
            {task.type === "HOUSEKEEPING" && task.status === "IN_INSPECTION" && isManager && <button className="btn primary" onClick={() => updateStatus(task, "DONE")}>Принять номер → CLEAN</button>}
            {task.type === "MAINTENANCE" && task.status === "IN_PROGRESS" && <button className="btn primary" onClick={() => updateStatus(task, "DONE")}>Ремонт завершён</button>}
            {task.type === "GUEST_REQUEST" && task.status === "IN_PROGRESS" && isManager && <button className="btn primary" onClick={() => updateStatus(task, "DONE")}>Выполнено</button>}
            {canSeeHistory && <button className="btn" type="button" onClick={() => loadHistory(task.id)}>{historyTaskId === task.id ? "Скрыть историю" : "История"}</button>}
          </div>
          {canSeeHistory && historyTaskId === task.id && <div className="task-history">
            <strong>История действий</strong>
            {historyLoading ? <span>Загрузка…</span> : historyItems.length === 0 ? <span>Записей пока нет.</span> : historyItems.map((item) => <div className="task-history-row" key={item.id}>
              <time>{dateTime(item.created_at)}</time>
              <div><b>{actionLabel[item.action] || item.action}</b><span>{item.actor_name || item.actor_type}{item.actor_role ? ` · ${item.actor_role}` : ""}{item.source ? ` · ${item.source}` : ""}</span></div>
              {typeof item.after?.status === "string" && <em>{statusLabel[item.after.status] || item.after.status}</em>}
            </div>)}
          </div>}
        </article>)}
      </div>}
    </main>
  );
}
