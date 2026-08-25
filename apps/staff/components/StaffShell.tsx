"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type User = {
  id: string;
  username: string;
  display_name: string;
  role: "OWNER" | "MANAGER" | "MAID" | "TECHNICIAN";
  property_code: string;
};

type Task = {
  id: string;
  type: "HOUSEKEEPING" | "MAINTENANCE" | "GUEST_REQUEST";
  status: "OPEN" | "IN_PROGRESS" | "IN_INSPECTION" | "DONE" | "CANCELLED";
  priority: "LOW" | "NORMAL" | "HIGH" | "URGENT";
  title: string;
  description?: string | null;
  room_code?: string | null;
  room_state?: string | null;
  assigned_to_id?: string | null;
  assigned_to_name?: string | null;
  created_at: string;
};

declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        ready: () => void;
        expand: () => void;
        colorScheme?: string;
        initData?: string;
      };
    };
  }
}

const roleLabel: Record<string, string> = {
  MAID: "Горничная",
  TECHNICIAN: "Техник",
  OWNER: "Владелец",
  MANAGER: "Менеджер",
};
const statusLabel: Record<string, string> = {
  OPEN: "Свободная",
  IN_PROGRESS: "В работе",
  IN_INSPECTION: "На проверке",
  DONE: "Готово",
  CANCELLED: "Отменена",
};
const priorityLabel: Record<string, string> = {
  URGENT: "Срочно",
  HIGH: "Высокий",
  NORMAL: "Обычный",
  LOW: "Низкий",
};

export default function StaffShell() {
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(true);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState<string | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"ACTIVE" | "MINE" | "DONE">("ACTIVE");
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    window.Telegram?.WebApp?.ready();
    window.Telegram?.WebApp?.expand();
    if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => undefined);

    fetch("/core/api/v1/auth/me", { cache: "no-store" })
      .then(async (response) => response.ok ? (await response.json()) as User : null)
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setChecking(false));
  }, []);

  const loadTasks = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/core/api/v1/ops/tasks?limit=250", { cache: "no-store" });
      if (response.status === 401) {
        setUser(null);
        return;
      }
      if (!response.ok) throw new Error("Не удалось загрузить задачи");
      const data = await response.json();
      setTasks(data.items || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка связи");
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => { if (user) loadTasks(); }, [user, loadTasks]);

  const visible = useMemo(() => tasks.filter((task) => {
    if (filter === "DONE") return task.status === "DONE";
    if (filter === "MINE") return task.assigned_to_id === user?.id && !["DONE", "CANCELLED"].includes(task.status);
    return !["DONE", "CANCELLED"].includes(task.status);
  }), [tasks, filter, user?.id]);

  async function login(event: FormEvent) {
    event.preventDefault();
    setLoginError(null);
    try {
      const response = await fetch("/core/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (!response.ok) {
        setLoginError("Неверный логин или пароль");
        return;
      }
      const payload = (await response.json()) as User;
      if (!["MAID", "TECHNICIAN", "OWNER", "MANAGER"].includes(payload.role)) {
        setLoginError("Эта роль не имеет доступа к интерфейсу персонала");
        return;
      }
      setUser(payload);
      setPassword("");
    } catch {
      setLoginError("Resort Core недоступен");
    }
  }

  async function logout() {
    await fetch("/core/api/v1/auth/logout", { method: "POST" }).catch(() => undefined);
    setUser(null);
    setTasks([]);
  }

  async function claim(task: Task) {
    setBusy(task.id);
    setError(null);
    try {
      const response = await fetch(`/core/api/v1/ops/tasks/${task.id}/claim`, { method: "POST" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Не удалось взять задачу");
      await loadTasks();
      setFilter("MINE");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка операции");
    } finally {
      setBusy(null);
    }
  }

  async function changeStatus(task: Task, status: string) {
    setBusy(task.id);
    setError(null);
    try {
      const response = await fetch(`/core/api/v1/ops/tasks/${task.id}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Не удалось обновить задачу");
      await loadTasks();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка операции");
    } finally {
      setBusy(null);
    }
  }

  if (checking) return <main className="center-screen"><div className="login-panel"><span className="brand-mark">III</span><h1>Подключаю Resort OS…</h1></div></main>;

  if (!user) return (
    <main className="center-screen">
      <form className="login-panel" onSubmit={login}>
        <span className="brand-mark">III</span>
        <p className="eyebrow">Три Короны · Персонал</p>
        <h1>Моя смена</h1>
        <p className="muted">Войдите под учётной записью сотрудника. Telegram Mini App позже будет выполнять этот вход автоматически.</p>
        <label><span>Логин</span><input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required /></label>
        <label><span>Пароль</span><input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" minLength={8} required /></label>
        {loginError && <div className="error">{loginError}</div>}
        <button className="primary">Войти</button>
      </form>
    </main>
  );

  const isLineStaff = ["MAID", "TECHNICIAN"].includes(user.role);

  return (
    <main className="staff-shell">
      <header className="staff-head">
        <div><p className="eyebrow">Три Короны · Resort OS</p><h1>{user.display_name}</h1><span>{roleLabel[user.role] || user.role}</span></div>
        <button className="ghost" onClick={logout}>Выйти</button>
      </header>

      <section className="quick-stats">
        <div><strong>{tasks.filter((x) => x.status === "OPEN").length}</strong><span>свободно</span></div>
        <div><strong>{tasks.filter((x) => x.assigned_to_id === user.id && x.status === "IN_PROGRESS").length}</strong><span>у меня</span></div>
        <div><strong>{tasks.filter((x) => x.status === "IN_INSPECTION").length}</strong><span>проверка</span></div>
      </section>

      <nav className="filters">
        <button className={filter === "ACTIVE" ? "active" : ""} onClick={() => setFilter("ACTIVE")}>Активные</button>
        <button className={filter === "MINE" ? "active" : ""} onClick={() => setFilter("MINE")}>Мои</button>
        <button className={filter === "DONE" ? "active" : ""} onClick={() => setFilter("DONE")}>Готовые</button>
        <button onClick={loadTasks}>↻</button>
      </nav>

      {error && <div className="error">{error}</div>}
      {loading ? <div className="loading">Обновляю задачи…</div> : <section className="task-stack">
        {visible.length === 0 && <div className="empty"><strong>Задач нет</strong><span>Новые задачи появятся здесь автоматически.</span></div>}
        {visible.map((task) => {
          const mine = task.assigned_to_id === user.id;
          return <article key={task.id} className={`task priority-${task.priority}`}>
            <div className="task-top"><span className="priority">{priorityLabel[task.priority]}</span><span className="status">{statusLabel[task.status]}</span></div>
            <h2>{task.room_code ? `№ ${task.room_code}` : "Общая задача"}</h2>
            <h3>{task.title}</h3>
            {task.description && <p>{task.description}</p>}
            {task.assigned_to_name && <small>Исполнитель: {task.assigned_to_name}</small>}
            <div className="actions">
              {isLineStaff && task.status === "OPEN" && !task.assigned_to_id && <button className="primary" disabled={busy === task.id} onClick={() => claim(task)}>Взять задачу</button>}
              {isLineStaff && mine && task.status === "IN_PROGRESS" && task.type === "HOUSEKEEPING" && <button className="primary" disabled={busy === task.id} onClick={() => changeStatus(task, "IN_INSPECTION")}>Уборка закончена</button>}
              {isLineStaff && mine && task.status === "IN_PROGRESS" && task.type === "MAINTENANCE" && <button className="primary" disabled={busy === task.id} onClick={() => changeStatus(task, "DONE")}>Ремонт завершён</button>}
              {!isLineStaff && task.status === "IN_INSPECTION" && task.type === "HOUSEKEEPING" && <button className="primary" disabled={busy === task.id} onClick={() => changeStatus(task, "DONE")}>Принять номер</button>}
            </div>
          </article>;
        })}
      </section>}
    </main>
  );
}
