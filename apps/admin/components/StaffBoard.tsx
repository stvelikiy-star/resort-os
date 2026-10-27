"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type StaffItem = {
  id: string;
  username: string;
  display_name: string;
  role: string;
  module_permissions: string[];
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
  can_manage_access: boolean;
  managed_roles: string[];
  staff_password_policy: { min_length: number; max_length: number };
  truth: string;
};

type StaffDraft = {
  username: string;
  display_name: string;
  role: string;
  password: string;
};

type EditDraft = {
  display_name: string;
  role: string;
  password: string;
  module_permissions: string[];
};

const MODULE_GROUPS = [
  { title: "Работа с бронированиями", items: [["PMS", "Шахматка"], ["RESERVATIONS", "Ресепшен и бронирования"], ["REQUESTS", "Заявки"], ["GROUPS", "Групповые брони"], ["RATES", "Цены и сезоны"], ["CHANNELS", "Каналы продаж"], ["AGENTS", "Агентства"]] },
  { title: "Гости и связь", items: [["WHATSAPP", "WhatsApp / AI"], ["INBOX", "Все сообщения"], ["GUESTS", "Гости и история"], ["SERVICES", "Сервис гостя"], ["OFFERS", "Предложения гостям"]] },
  { title: "Работа отеля", items: [["OPS", "Уборка и ремонт"], ["DINING", "Питание и ресторан"], ["ROOM_QR", "QR номеров"], ["POINT_QR", "QR зон"], ["SERVICE_SETTINGS", "Настройки услуг"]] },
  { title: "Управление", items: [["DASHBOARD", "Главная"], ["FINANCE", "Финансы"], ["REPORTS", "Отчёты и аналитика"], ["GROWTH", "Отзывы и рост"], ["MARKETING", "Маркетинг"], ["CONTENT", "Контент отеля"], ["HOTEL_RULES", "Знания отеля / MARINA AI"], ["SETTINGS", "Настройки гостиницы"], ["STAFF", "Просмотр персонала"]] },
] as const;

const emptyStaffDraft: StaffDraft = {
  username: "",
  display_name: "",
  role: "RECEPTION",
  password: "",
};

const roleLabel: Record<string, string> = {
  OWNER: "Владелец",
  MANAGER: "Менеджер",
  RECEPTION: "Ресепшен",
  AGENT: "Агентство / туроператор",
  MAID: "Горничная",
  TECHNICIAN: "Техник",
  STORE_STAFF: "Магазин · модуль не подключён",
  // Runtime compatibility marker: DINING_STAFF: "Столовая / ресторан" (legacy enum only; no access granted).\n  DINING_STAFF: "Устаревшая роль · питание",
  COOK: "Повар",
  WAITER: "Официант",
  CONTENT_MANAGER: "Устаревшая роль · контент",
  BEACH_PARTNER: "Пляжный партнёр (legacy)",
};

function dateTime(value?: string | null) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }).format(date);
}

export default function StaffBoard({ userRole, propertyCode }: { userRole: string; propertyCode: string }) {
  // The API determines the password policy from the running environment.
  const [data, setData] = useState<Overview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [role, setRole] = useState("ALL");
  const [showCreate, setShowCreate] = useState(false);
  const [createDraft, setCreateDraft] = useState<StaffDraft>(emptyStaffDraft);
  const [editing, setEditing] = useState<StaffItem | null>(null);
  const [editDraft, setEditDraft] = useState<EditDraft>({ display_name: "", role: "RECEPTION", password: "", module_permissions: [] });
  const [saving, setSaving] = useState(false);
  const passwordMin = data?.staff_password_policy?.min_length ?? 8;
  const passwordMax = data?.staff_password_policy?.max_length ?? 256;
  const demo = passwordMin === 3 && passwordMax === 10;

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

  useEffect(() => { void load(); }, [load]);

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

  async function createStaff(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const response = await fetch("/core/api/v1/admin/staff", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(createDraft),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Не удалось создать сотрудника");
      setCreateDraft(emptyStaffDraft);
      setShowCreate(false);
      setNotice(`Сотрудник ${body.display_name} создан. Передайте пароль только лично сотруднику.`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка создания сотрудника");
    } finally {
      setSaving(false);
    }
  }

  function beginEdit(item: StaffItem) {
    if (item.role === "OWNER" || item.role === "AGENT") return;
    setEditing(item);
    setEditDraft({ display_name: item.display_name, role: item.role, password: "", module_permissions: item.module_permissions || [] });
    setError(null);
    setNotice(null);
  }

  async function saveEdit(event: FormEvent) {
    event.preventDefault();
    if (!editing) return;
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const payload: Record<string, unknown> = {
        display_name: editDraft.display_name,
        role: editDraft.role,
        module_permissions: editDraft.module_permissions,
      };
      if (editDraft.password.trim()) payload.password = editDraft.password;
      const response = await fetch(`/core/api/v1/admin/staff/${editing.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Не удалось изменить доступ");
      setEditing(null);
      setNotice("Доступ обновлён. Сотруднику нужно войти заново.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка изменения доступа");
    } finally {
      setSaving(false);
    }
  }

  async function toggleAccess(item: StaffItem) {
    if (!data?.can_manage_access || item.role === "OWNER" || item.role === "AGENT") return;
    const verb = item.active ? "отключить" : "включить";
    if (!window.confirm(`Точно ${verb} доступ для ${item.display_name}?`)) return;
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const response = await fetch(`/core/api/v1/admin/staff/${item.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ active: !item.active }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Не удалось изменить доступ");
      setNotice(`${body.display_name}: доступ ${body.active ? "включён" : "отключён"}. Активные сессии отозваны.`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка изменения доступа");
    } finally {
      setSaving(false);
    }
  }

  if (loading && !data) return <main className="work-shell staff-shell"><div className="loading">Загрузка персонала…</div></main>;
  if (error && !data) return <main className="work-shell staff-shell"><div className="error-box">{error}</div><button className="btn" onClick={load}>Повторить</button></main>;
  if (!data) return null;

  const activeStaff = data.staff.filter((item) => item.active).length;
  const linked = data.staff.filter((item) => item.telegram_linked).length;
  const assignedActive = data.staff.reduce((sum, item) => sum + item.active_tasks, 0);
  const completedToday = data.staff.reduce((sum, item) => sum + item.completed_today, 0);
  const canManage = data.can_manage_access && userRole === "OWNER";

  return <main className="work-shell staff-shell management-shell">
    <div className="work-head">
      <div><p className="eyebrow">Отель · персонал</p><h1>Персонал и доступы</h1><p className="subtitle">Фактические задачи и учётные записи Hotel OS · {data.local_date} · {data.timezone}</p></div>
      <div className="management-head-actions">
        {canManage && <button className="btn primary" onClick={() => setShowCreate((value) => !value)}>{showCreate ? "Закрыть форму" : "+ Создать сотрудника"}</button>}
        <button className="btn" onClick={load} disabled={loading}>{loading ? "Обновляю…" : "Обновить"}</button>
      </div>
    </div>

    {!canManage && <div className="management-truth"><strong>Доступ только для просмотра.</strong> Создание сотрудников, роли, пароли и отключение учётных записей доступны владельцу (OWNER).</div>}
    {notice && <div className="management-notice">{notice}</div>}
    {error && <div className="error-box">{error}</div>}

    {showCreate && canManage && <form className="management-inline-form" onSubmit={createStaff}>
      <div><p className="eyebrow">Новая учётная запись</p><h2>Создать сотрудника</h2></div>
      <label><span>Имя сотрудника</span><input required minLength={2} value={createDraft.display_name} onChange={(e) => setCreateDraft({ ...createDraft, display_name: e.target.value })} /></label>
      <label><span>Логин</span><input required minLength={2} pattern="[A-Za-z0-9._-]+" autoComplete="off" value={createDraft.username} onChange={(e) => setCreateDraft({ ...createDraft, username: e.target.value })} /></label>
      <label><span>Роль</span><select value={createDraft.role} onChange={(e) => setCreateDraft({ ...createDraft, role: e.target.value })}>{data.managed_roles.map((value) => <option key={value} value={value}>{roleLabel[value] || value}</option>)}</select></label>
      <label><span>Пароль ({demo ? "3–10" : "от 8"} символов)</span><input required type="password" minLength={passwordMin} maxLength={passwordMax} autoComplete="new-password" value={createDraft.password} onChange={(e) => setCreateDraft({ ...createDraft, password: e.target.value })} /></label>
      <div className="management-inline-actions"><button className="btn primary" disabled={saving}>{saving ? "Создаю…" : "Создать"}</button></div>
    </form>}

    <section className="staff-kpis management-kpis">
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
        {data.managed_roles.map((value) => <option key={value} value={value}>{roleLabel[value] || value}</option>)}
        {data.staff.some((item) => item.role === "AGENT") && <option value="AGENT">Агентство / туроператор</option>}
        {data.staff.some((item) => item.role === "BEACH_PARTNER") && <option value="BEACH_PARTNER">Пляжный партнёр (legacy)</option>}
      </select>
    </div>

    <section className="staff-table staff-table-access">
      <div className="staff-row header"><span>Сотрудник</span><span>Роль / доступ</span><span>Задачи сейчас</span><span>Сегодня</span><span>Последняя сессия</span>{canManage && <span>Управление</span>}</div>
      {visible.length === 0 && <div className="empty">Сотрудников по фильтру нет.</div>}
      {visible.map((item) => <article className={`staff-row ${!item.active ? "staff-disabled" : ""}`} key={item.id}>
        <div><strong>{item.display_name}</strong><small>@{item.username}</small></div>
        <div><b>{roleLabel[item.role] || item.role}</b><small>{["DINING_STAFF", "CONTENT_MANAGER", "BEACH_PARTNER"].includes(item.role) ? "Устаревшая роль · вход в кабинеты не поддерживается" : item.role === "STORE_STAFF" ? "Ограниченная роль · операции магазина не подключены" : item.active ? "Активен" : "Доступ отключён"} · Telegram: {item.telegram_linked ? item.telegram_username ? `@${item.telegram_username}` : "привязан" : "не привязан"}</small></div>
        <div><strong>{item.active_tasks}</strong><small>{item.housekeeping_active ? `уборка ${item.housekeeping_active}` : ""}{item.housekeeping_active && item.maintenance_active ? " · " : ""}{item.maintenance_active ? `ремонт ${item.maintenance_active}` : ""}</small></div>
        <div><strong>{item.completed_today}</strong><small>завершено задач</small></div>
        <div><strong>{dateTime(item.last_session_seen_at)}</strong><small>внутренняя сессия</small></div>
        {canManage && <div className="staff-access-actions">
          {item.role === "OWNER" ? <small>Защищённая учётная запись</small> : item.role === "AGENT" ? <small>Доступ управляется в разделе «Агенты»</small> : <>
            <button className="btn mini" onClick={() => beginEdit(item)}>Роль / пароль</button>
            <button className={`btn mini ${item.active ? "danger-ghost" : ""}`} disabled={saving} onClick={() => void toggleAccess(item)}>{item.active ? "Отключить" : "Включить"}</button>
          </>}
        </div>}
      </article>)}
    </section>

    <p className="staff-truth">Это контроль задач и использования Hotel OS. Он не является табелем рабочего времени, расчётом зарплаты или рейтингом эффективности.</p>

    {editing && canManage && <div className="management-modal-backdrop" role="presentation" onMouseDown={(e) => { if (e.target === e.currentTarget) setEditing(null); }}>
      <form className="management-modal" onSubmit={saveEdit}>
        <div className="management-modal-head"><div><p className="eyebrow">Учётная запись</p><h2>{editing.display_name}</h2><p>@{editing.username}</p></div><button type="button" className="btn mini" onClick={() => setEditing(null)}>Закрыть</button></div>
        <div className="management-form-grid">
          <label><span>Имя сотрудника</span><input required minLength={2} value={editDraft.display_name} onChange={(e) => setEditDraft({ ...editDraft, display_name: e.target.value })} /></label>
          <label><span>Роль</span><select value={editDraft.role} onChange={(e) => setEditDraft({ ...editDraft, role: e.target.value })}>{!data.managed_roles.includes(editing.role) && <option value={editing.role} disabled>{roleLabel[editing.role] || editing.role} · устаревшая</option>}{data.managed_roles.map((value) => <option key={value} value={value}>{roleLabel[value] || value}</option>)}</select></label>
          <label className="management-form-wide"><span>Новый пароль (оставьте пустым, если не меняете)</span><input type="password" minLength={passwordMin} maxLength={passwordMax} autoComplete="new-password" value={editDraft.password} onChange={(e) => setEditDraft({ ...editDraft, password: e.target.value })} placeholder={demo ? "От 3 до 10 символов" : "Не менее 8 символов"} /></label>
        </div>
        <fieldset className="staff-module-access">
          <legend>Доступ к разделам</legend>
          <p>Отметьте разделы, которые будут доступны этому сотруднику. Этот список заменяет стандартный набор доступа по его роли.</p>
          {MODULE_GROUPS.map((group) => <div className="staff-module-group" key={group.title}>
            <strong>{group.title}</strong>
            <div>{group.items.map(([key, title]) => <label key={key}>
              <input type="checkbox" checked={editDraft.module_permissions.includes(key)} onChange={(event) => setEditDraft((draft) => ({ ...draft, module_permissions: event.target.checked ? [...new Set([...draft.module_permissions, key])] : draft.module_permissions.filter((module) => module !== key) }))} />
              <span>{title}</span>
            </label>)}</div>
          </div>)}
        </fieldset>
        <div className="management-truth compact">После сохранения прежние сессии сотрудника отзываются. Новые разделы появятся после повторного входа.</div>
        <div className="management-modal-actions"><button type="button" className="btn" onClick={() => setEditing(null)}>Отмена</button><button className="btn primary" disabled={saving}>{saving ? "Сохраняю…" : "Сохранить"}</button></div>
      </form>
    </div>}
  </main>;
}
