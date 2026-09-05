"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type StaffItem = {
  id: string;
  username: string;
  display_name: string;
  role: string;
  active: boolean;
  telegram_linked: boolean;
  telegram_username?: string | null;
  telegram_linked_at?: string | null;
  active_tasks: number;
  completed_today: number;
  housekeeping_active: number;
  maintenance_active: number;
  last_session_seen_at?: string | null;
};

type Overview = {
  local_date: string;
  timezone: string;
  staff: StaffItem[];
  unassigned_active_tasks: {
    housekeeping: number;
    maintenance: number;
    guest_requests: number;
    total: number;
  };
  truth: string;
};

const roleLabel: Record<string, string> = {
  OWNER: "Владелец",
  MANAGER: "Менеджер",
  RECEPTION: "Ресепшен",
  MAID: "Горничная",
  TECHNICIAN: "Техник",
  BEACH_PARTNER: "Пляжный партнёр",
};

function dateTime(value?: string | null) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }).format(date);
}

export default function StaffBoard() {
  const [data, setData] = useState<Overview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [role, setRole] = useState("ALL");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/core/api/v1/admin/staff/overview", { cache: "no-store" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Не удалось загрузить персонал");
      setData(body as Overview);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка загрузки персонала");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const visible = useMemo(() => {
    if (!data) return [];
    const q = query.trim().toLowerCase();
    return data.staff.filter((item) => {
      const roleMatches = role === "ALL" || item.role === role;
      const queryMatches = !q || [item.display_name, item.username, item.telegram_username, roleLabel[item.role]]
        .some((value) => value?.toLowerCase().includes(q));
      return roleMatches && queryMatches;
    });
  }, [data, query, role]);

  if (loading) return <main className="work-shell staff-shell"><div className="loading">Загрузка персонала…</div></main>;
  if (error) return <main className="work-shell staff-shell"><div className="error-box">{error}</div><button className="btn" onClick={load}>Повторить</button></main>;
  if (!data) return null;

  const activeStaff = data.staff.filter((item) => item.active).length;
  const linked = data.staff.filter((item) => item.telegram_linked).length;
  const assignedActive = data.staff.reduce((sum, item) => sum + item.active_tasks, 0);
  const completedToday = data.staff.reduce((sum, item) => sum + item.completed_today, 0);

  return <main className="work-shell staff-shell">
    <div className="work-head">
      <div><p className="eyebrow">Отель · персонал</p><h1>Контроль персонала</h1><p className="subtitle">Фактические задачи и доступ к системе · {data.local_date} · {data.timezone}</p></div>
      <button className="btn" onClick={load}>Обновить</button>
    </div>

    <section className="staff-kpis">
      <article><strong>{activeStaff}</strong><span>активных учётных записей</span></article>
      <article><strong>{linked}</strong><span>привязан Telegram</span></article>
      <article><strong>{assignedActive}</strong><span>активных назначенных задач</span></article>
      <article><strong>{data.unassigned_active_tasks.total}</strong><span>активных без ответственного</span></article>
      <article><strong>{completedToday}</strong><span>задач завершено сегодня</span></article>
    </section>

    <section className="staff-unassigned">
      <div><span>Без ответственного · уборка</span><strong>{data.unassigned_active_tasks.housekeeping}</strong></div>
      <div><span>Без ответственного · ремонт</span><strong>{data.unassigned_active_tasks.maintenance}</strong></div>
      <div><span>Без ответственного · запросы гостей</span><strong>{data.unassigned_active_tasks.guest_requests}</strong></div>
    </section>

    <div className="staff-controls">
      <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Имя, логин, Telegram…" />
      <select value={role} onChange={(e) => setRole(e.target.value)}>
        <option value="ALL">Все роли</option>
        <option value="OWNER">Владелец</option>
        <option value="MANAGER">Менеджеры</option>
        <option value="RECEPTION">Ресепшен</option>
        <option value="MAID">Горничные</option>
        <option value="TECHNICIAN">Техники</option>
        <option value="BEACH_PARTNER">Пляжные партнёры</option>
      </select>
    </div>

    <section className="staff-table">
      <div className="staff-row header"><span>Сотрудник</span><span>Роль / доступ</span><span>Задачи сейчас</span><span>Сегодня</span><span>Последняя сессия</span></div>
      {visible.length === 0 && <div className="empty">Сотрудников по фильтру нет.</div>}
      {visible.map((item) => <article className="staff-row" key={item.id}>
        <div><strong>{item.display_name}</strong><small>@{item.username}</small></div>
        <div><b>{roleLabel[item.role] || item.role}</b><small>{item.active ? "Активен" : "Отключён"} · Telegram: {item.telegram_linked ? item.telegram_username ? `@${item.telegram_username}` : "привязан" : "не привязан"}</small></div>
        <div><strong>{item.active_tasks}</strong><small>{item.housekeeping_active ? `уборка ${item.housekeeping_active}` : ""}{item.housekeeping_active && item.maintenance_active ? " · " : ""}{item.maintenance_active ? `ремонт ${item.maintenance_active}` : ""}</small></div>
        <div><strong>{item.completed_today}</strong><small>завершено задач</small></div>
        <div><strong>{dateTime(item.last_session_seen_at)}</strong><small>внутренняя сессия</small></div>
      </article>)}
    </section>

    <p className="staff-truth">Это контроль задач и использования Resort OS. Он не является табелем рабочего времени, расчётом зарплаты или рейтингом эффективности.</p>
  </main>;
}
