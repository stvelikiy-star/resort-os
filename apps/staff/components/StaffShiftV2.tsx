"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type Role = "OWNER" | "MANAGER" | "MAID" | "TECHNICIAN";
type User = { id: string; username: string; display_name: string; role: Role; property_code: string };
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

type Filter = "MINE" | "AVAILABLE" | "DONE";

declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        ready: () => void;
        expand: () => void;
        initData?: string;
      };
    };
  }
}

const ACTIVE_ROLES = new Set<Role>(["MAID", "TECHNICIAN", "OWNER", "MANAGER"]);
const roleLabel: Record<Role, string> = { MAID: "Горничная", TECHNICIAN: "Техник", OWNER: "Владелец", MANAGER: "Менеджер" };
const priorityLabel: Record<string, string> = { URGENT: "Срочно", HIGH: "Высокий", NORMAL: "Обычный", LOW: "Низкий" };
const statusLabel: Record<string, string> = { OPEN: "Свободная", IN_PROGRESS: "В работе", IN_INSPECTION: "На проверке", DONE: "Готово", CANCELLED: "Отменена" };
const roomStateLabel: Record<string, string> = { CLEAN: "Готов", DIRTY: "Нужна уборка", IN_INSPECTION: "На проверке", TECH_BLOCK: "Техблок", UNKNOWN: "Не указан" };

const housekeepingChecklist = [
  ["BED_LINEN", "Кровать и бельё"],
  ["BATHROOM", "Санузел"],
  ["SURFACES", "Пол и поверхности"],
  ["AMENITIES", "Комплектация номера"],
  ["FINAL_CHECK", "Финальная проверка"],
] as const;

function isStaffUser(value: any): value is User {
  return Boolean(value && ACTIVE_ROLES.has(value.role));
}

function typeForRole(role: Role) {
  if (role === "MAID") return "HOUSEKEEPING";
  if (role === "TECHNICIAN") return "MAINTENANCE";
  return null;
}

export default function StaffShiftV2() {
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(true);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState<string | null>(null);
  const [telegramDetected, setTelegramDetected] = useState(false);
  const [telegramInitData, setTelegramInitData] = useState("");
  const [telegramNotice, setTelegramNotice] = useState<string | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [filter, setFilter] = useState<Filter>("MINE");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [reportTask, setReportTask] = useState<Task | null>(null);
  const [summary, setSummary] = useState("");
  const [evidenceUrl, setEvidenceUrl] = useState("");
  const [checks, setChecks] = useState<Record<string, boolean>>({});

  useEffect(() => {
    window.Telegram?.WebApp?.ready();
    window.Telegram?.WebApp?.expand();
    if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => undefined);

    let cancelled = false;
    async function clearSession() {
      await fetch("/core/api/v1/auth/logout", { method: "POST" }).catch(() => undefined);
    }
    async function bootstrap() {
      const initData = window.Telegram?.WebApp?.initData || "";
      if (initData) {
        setTelegramDetected(true);
        setTelegramInitData(initData);
        try {
          const response = await fetch("/core/api/v1/auth/telegram/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ init_data: initData }),
          });
          if (response.ok) {
            const payload = await response.json();
            if (isStaffUser(payload)) {
              if (!cancelled) setUser(payload);
              if (!cancelled) setTelegramNotice("Telegram подтверждён");
              if (!cancelled) setChecking(false);
              return;
            }
            await clearSession();
          }
        } catch {
          if (!cancelled) setTelegramNotice("Telegram-вход временно недоступен");
        }
      }
      try {
        const response = await fetch("/core/api/v1/auth/me", { cache: "no-store" });
        const payload = response.ok ? await response.json() : null;
        if (payload && !isStaffUser(payload)) {
          await clearSession();
          if (!cancelled) setUser(null);
        } else if (!cancelled) setUser(payload);
      } catch {
        if (!cancelled) setUser(null);
      } finally {
        if (!cancelled) setChecking(false);
      }
    }
    void bootstrap();
    return () => { cancelled = true; };
  }, []);

  const load = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    setError(null);
    try {
      const wantedType = typeForRole(user.role);
      const suffix = wantedType ? `&type=${wantedType}` : "";
      const response = await fetch(`/core/api/v1/ops/tasks?limit=250${suffix}`, { cache: "no-store" });
      if (response.status === 401) {
        setUser(null);
        return;
      }
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Не удалось загрузить смену");
      setTasks(body.items || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка связи");
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => { if (user) void load(); }, [user, load]);

  const visible = useMemo(() => {
    if (!user) return [];
    if (filter === "DONE") return tasks.filter((task) => task.status === "DONE" && task.assigned_to_id === user.id);
    if (filter === "AVAILABLE") return tasks.filter((task) => task.status === "OPEN" && !task.assigned_to_id);
    return tasks.filter((task) => task.assigned_to_id === user.id && !["DONE", "CANCELLED"].includes(task.status));
  }, [tasks, filter, user]);

  async function login(event: FormEvent) {
    event.preventDefault();
    setLoginError(null);
    try {
      const response = await fetch("/core/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok || !isStaffUser(body)) {
        setLoginError("Неверный логин, пароль или роль");
        return;
      }
      setUser(body);
      setPassword("");
      if (telegramInitData) {
        const link = await fetch("/core/api/v1/auth/telegram/link", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ init_data: telegramInitData }),
        }).catch(() => null);
        if (link?.ok) setTelegramNotice("Telegram привязан. Следующий вход — автоматически.");
      }
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
      if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Задачу уже забрал другой сотрудник");
      setFilter("MINE");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка операции");
    } finally {
      setBusy(null);
    }
  }

  function openReport(task: Task) {
    setReportTask(task);
    setSummary(task.type === "HOUSEKEEPING" ? "Уборка выполнена, номер готов к проверке." : "Ремонт выполнен.");
    setEvidenceUrl("");
    setChecks(Object.fromEntries(housekeepingChecklist.map(([code]) => [code, false])));
  }

  async function submitReport(event: FormEvent) {
    event.preventDefault();
    if (!reportTask) return;
    setBusy(reportTask.id);
    setError(null);
    try {
      const checklist = reportTask.type === "HOUSEKEEPING"
        ? housekeepingChecklist.map(([code, label]) => ({ code, label, done: Boolean(checks[code]) }))
        : [];
      const response = await fetch(`/core/api/v1/ops/tasks/${reportTask.id}/complete-report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          summary: summary.trim(),
          checklist,
          evidence_urls: evidenceUrl.trim() ? [evidenceUrl.trim()] : [],
        }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        if (body.detail?.code === "CHECKLIST_INCOMPLETE") throw new Error("Отметьте все пункты чек-листа перед сдачей номера.");
        throw new Error(typeof body.detail === "string" ? body.detail : "Не удалось сдать работу");
      }
      setReportTask(null);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка сдачи работы");
    } finally {
      setBusy(null);
    }
  }

  if (checking) return <main className="shift-center"><div className="shift-login"><div className="shift-crown">III</div><h1>Подключаю смену…</h1><p>Проверяю Telegram и рабочую сессию.</p></div></main>;

  if (!user) return <main className="shift-center"><form className="shift-login" onSubmit={login}>
    <div className="shift-crown">III</div>
    <p className="shift-eyebrow">Три Короны · Resort OS</p>
    <h1>Моя смена</h1>
    <p>{telegramDetected ? "Первый вход: рабочий логин и пароль. После привязки Telegram вход будет автоматическим." : "Войдите под рабочей учётной записью."}</p>
    {telegramNotice && <div className="shift-notice">{telegramNotice}</div>}
    <label><span>Логин</span><input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required /></label>
    <label><span>Пароль</span><input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" minLength={8} required /></label>
    {loginError && <div className="shift-error">{loginError}</div>}
    <button className="shift-primary">Войти</button>
  </form></main>;

  const lineStaff = user.role === "MAID" || user.role === "TECHNICIAN";
  const myActive = tasks.filter((task) => task.assigned_to_id === user.id && !["DONE", "CANCELLED"].includes(task.status)).length;
  const available = tasks.filter((task) => task.status === "OPEN" && !task.assigned_to_id).length;
  const done = tasks.filter((task) => task.status === "DONE" && task.assigned_to_id === user.id).length;

  return <main className="shift-shell">
    <header className="shift-head">
      <div><p className="shift-eyebrow">Три Короны · Моя смена</p><h1>{user.display_name}</h1><span>{roleLabel[user.role]}{telegramDetected ? " · Telegram" : ""}</span></div>
      <button className="shift-ghost" onClick={logout}>Выйти</button>
    </header>

    {telegramNotice && <div className="shift-notice">{telegramNotice}</div>}
    {error && <div className="shift-error">{error}</div>}

    <section className="shift-kpis">
      <button onClick={() => setFilter("MINE")} className={filter === "MINE" ? "active" : ""}><strong>{myActive}</strong><span>мои сейчас</span></button>
      <button onClick={() => setFilter("AVAILABLE")} className={filter === "AVAILABLE" ? "active" : ""}><strong>{available}</strong><span>можно взять</span></button>
      <button onClick={() => setFilter("DONE")} className={filter === "DONE" ? "active" : ""}><strong>{done}</strong><span>завершено</span></button>
    </section>

    <div className="shift-toolbar"><strong>{filter === "MINE" ? "Мои задачи" : filter === "AVAILABLE" ? "Свободные задачи" : "Завершённые"}</strong><button className="shift-ghost" onClick={load}>Обновить</button></div>

    {loading ? <div className="shift-empty">Обновляю смену…</div> : <section className="shift-stack">
      {visible.length === 0 && <div className="shift-empty"><strong>Здесь пока пусто</strong><span>{filter === "AVAILABLE" ? "Новые задачи появятся автоматически." : "Переключитесь на другой раздел."}</span></div>}
      {visible.map((task) => {
        const mine = task.assigned_to_id === user.id;
        return <article key={task.id} className={`shift-task priority-${task.priority}`}>
          <div className="shift-task-meta"><span>{priorityLabel[task.priority]}</span><b>{statusLabel[task.status]}</b></div>
          <div className="shift-room"><strong>{task.room_code ? `№ ${task.room_code}` : "Общая задача"}</strong>{task.room_state && <span>{roomStateLabel[task.room_state] || task.room_state}</span>}</div>
          <h2>{task.title}</h2>
          {task.description && <p>{task.description}</p>}
          {task.assigned_to_name && <small>Исполнитель: {task.assigned_to_name}</small>}
          <div className="shift-actions">
            {lineStaff && task.status === "OPEN" && !task.assigned_to_id && <button className="shift-primary" disabled={busy === task.id} onClick={() => claim(task)}>Взять в работу</button>}
            {lineStaff && mine && task.status === "IN_PROGRESS" && <button className="shift-primary" onClick={() => openReport(task)}>{task.type === "HOUSEKEEPING" ? "Сдать уборку" : "Сдать ремонт"}</button>}
            {!lineStaff && <span className="shift-supervisor-note">Управление задачей — в основной PMS.</span>}
          </div>
        </article>;
      })}
    </section>}

    {reportTask && <div className="shift-modal-backdrop" onMouseDown={(e) => { if (e.target === e.currentTarget && busy !== reportTask.id) setReportTask(null); }}>
      <form className="shift-modal" onSubmit={submitReport}>
        <div className="shift-modal-head"><div><p className="shift-eyebrow">Отчёт о работе</p><h2>{reportTask.room_code ? `Номер ${reportTask.room_code}` : reportTask.title}</h2></div><button type="button" className="shift-ghost" onClick={() => setReportTask(null)}>×</button></div>
        {reportTask.type === "HOUSEKEEPING" && <section className="shift-checklist"><h3>Чек-лист уборки</h3>{housekeepingChecklist.map(([code, label]) => <label key={code}><input type="checkbox" checked={Boolean(checks[code])} onChange={(e) => setChecks((current) => ({ ...current, [code]: e.target.checked }))} /><span>{label}</span></label>)}</section>}
        <label className="shift-field"><span>Что сделано</span><textarea value={summary} onChange={(e) => setSummary(e.target.value)} minLength={2} maxLength={2000} required /></label>
        <label className="shift-field"><span>Фото / ссылка на подтверждение</span><input type="url" value={evidenceUrl} onChange={(e) => setEvidenceUrl(e.target.value)} placeholder="https://…" /><small>На staging подключим прямую загрузку фото в защищённое хранилище; сейчас Core уже умеет сохранять ссылку в audit trail.</small></label>
        <button className="shift-primary shift-submit" disabled={busy === reportTask.id}>{busy === reportTask.id ? "Сохраняю…" : reportTask.type === "HOUSEKEEPING" ? "Отправить на проверку" : "Завершить ремонт"}</button>
      </form>
    </div>}
  </main>;
}
