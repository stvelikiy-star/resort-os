"use client";

import { FormEvent, useEffect, useState } from "react";

type Identity = {
  id: string; display_name: string; role: string;
  property_code: string; property_id: string; tenant_id: string;
  module_permissions: string[];
};
type Section = "dashboard" | "grid" | "staff";
type Dashboard = {
  property: { code: string; name: string };
  rooms: { total: number; clean: number; dirty: number };
  stays: { in_house: number; arrivals_today: number; departures_today: number };
  communications: { needs_reply: number };
};
type Grid = {
  property: string;
  rooms: Array<{ id: string; code: string; name: string; operational_state: string;
    blocks: Array<{ id: string; type: string; start: string; end: string }> }>;
};
type StaffOverview = {
  staff: Array<{ id: string; username: string; display_name: string;
    role: string; active: boolean; module_permissions: string[] }>;
  can_manage_access: boolean;
  managed_roles: string[];
};
const MANAGED_ROLES = ["MANAGER", "RECEPTION", "MAID", "TECHNICIAN", "COOK", "WAITER"] as const;

function availableSections(user: Identity): Section[] {
  const grants = user.module_permissions || [];
  const can = (module: string) => user.role === "OWNER" || grants.includes(module);
  const sections: Section[] = [];
  if (["OWNER", "MANAGER"].includes(user.role) && can("DASHBOARD")) sections.push("dashboard");
  if (["OWNER", "MANAGER", "RECEPTION", "AGENT"].includes(user.role) && can("PMS")) sections.push("grid");
  if (["OWNER", "MANAGER"].includes(user.role) && can("STAFF")) sections.push("staff");
  return sections;
}
function dateText(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export default function SharedAuthPreview() {
  const [mode, setMode] = useState<"loading" | "ready" | "unavailable">("loading");
  const [tenant, setTenant] = useState("");
  const [property, setProperty] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [identity, setIdentity] = useState<Identity | null>(null);
  const [section, setSection] = useState<Section | null>(null);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [grid, setGrid] = useState<Grid | null>(null);
  const [staff, setStaff] = useState<StaffOverview | null>(null);
  const [loadingSection, setLoadingSection] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [sectionError, setSectionError] = useState("");
  const [staffUsername, setStaffUsername] = useState("");
  const [staffName, setStaffName] = useState("");
  const [staffPassword, setStaffPassword] = useState("");
  const [staffRole, setStaffRole] = useState<(typeof MANAGED_ROLES)[number]>("RECEPTION");
  const today = dateText(new Date());
  const end = new Date();
  end.setDate(end.getDate() + 7);
  const until = dateText(end);
  const sections = identity ? availableSections(identity) : [];

  useEffect(() => {
    const controller = new AbortController();
    void (async () => {
      try {
        const response = await fetch("/core/api/v1/auth/mode", { cache: "no-store", signal: controller.signal });
        const body = await response.json();
        if (!response.ok || body.mode !== "shared_auth_preview") {
          setMode("unavailable");
          return;
        }
        setMode("ready");
        const me = await fetch("/core/api/v1/auth/me", { cache: "no-store", signal: controller.signal });
        if (me.ok) {
          const user = await me.json() as Identity;
          if (user.property_id && user.tenant_id) setIdentity(user);
        }
      } catch {
        if (!controller.signal.aborted) setMode("unavailable");
      }
    })();
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!identity) {
      setSection(null); setDashboard(null); setGrid(null); setStaff(null);
      return;
    }
    const allowed = availableSections(identity);
    setSection(current => current && allowed.includes(current) ? current : (allowed[0] || null));
  }, [identity]);

  useEffect(() => {
    if (!identity || !section) return;
    const controller = new AbortController();
    setLoadingSection(true);
    setSectionError("");
    const api = section === "dashboard" ? "/core/api/v1/admin/dashboard"
      : section === "grid" ? `/core/api/v1/pms/grid?start=${today}&end=${until}`
      : "/core/api/v1/admin/staff/overview";
    void (async () => {
      try {
        const response = await fetch(api, { cache: "no-store", signal: controller.signal });
        if (response.status === 401) {
          setIdentity(null);
          setSectionError("Сеанс истёк. Войдите повторно.");
          return;
        }
        if (!response.ok) throw new Error(String(response.status));
        const body = await response.json();
        if (controller.signal.aborted) return;
        // Never cache one hotel's result across a new verified login.
        if (section === "dashboard") {
          if (body.property?.code !== identity.property_code) throw new Error("scope");
          setDashboard(body as Dashboard);
        } else if (section === "grid") {
          if (body.property !== identity.property_code) throw new Error("scope");
          setGrid(body as Grid);
        } else {
          setStaff(body as StaffOverview);
        }
      } catch {
        if (!controller.signal.aborted) setSectionError("Данные раздела недоступны или не прошли проверку.");
      } finally {
        if (!controller.signal.aborted) setLoadingSection(false);
      }
    })();
    return () => controller.abort();
  }, [identity, section, today, until]);

  async function login(event: FormEvent) {
    event.preventDefault();
    if (pending || mode !== "ready") return;
    setPending(true);
    setError("");
    try {
      const response = await fetch("/core/api/v1/auth/login", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tenant_code: tenant.trim(), property_code: property.trim(), username, password }),
      });
      if (!response.ok) throw new Error("login");
      const me = await fetch("/core/api/v1/auth/me", { cache: "no-store" });
      if (!me.ok) throw new Error("session");
      const user = await me.json() as Identity;
      if (!user.property_id || !user.tenant_id || user.property_code !== property.trim()) {
        await fetch("/core/api/v1/auth/logout", { method: "POST" });
        throw new Error("scope");
      }
      setIdentity(user);
    } catch {
      setError("Вход не подтверждён. Проверьте коды организации и отеля, логин и пароль.");
    } finally {
      setPassword("");
      setPending(false);
    }
  }

  async function logout() {
    setPending(true);
    setError("");
    try {
      const response = await fetch("/core/api/v1/auth/logout", { method: "POST" });
      if (!response.ok) throw new Error("logout");
      setIdentity(null);
    } catch {
      setError("Не удалось завершить сеанс. Повторите попытку.");
    } finally { setPending(false); }
  }

  async function createStaff(event: FormEvent) {
    event.preventDefault();
    if (!identity || identity.role !== "OWNER" || pending) return;
    setPending(true);
    setSectionError("");
    try {
      const response = await fetch("/core/api/v1/admin/staff", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: staffUsername.trim(), display_name: staffName.trim(),
          password: staffPassword, role: staffRole,
        }),
      });
      if (!response.ok) throw new Error(String(response.status));
      setStaffPassword("");
      setStaffUsername("");
      setStaffName("");
      const refreshed = await fetch("/core/api/v1/admin/staff/overview", { cache: "no-store" });
      if (!refreshed.ok) throw new Error("refresh");
      setStaff(await refreshed.json() as StaffOverview);
    } catch {
      setSectionError("Не удалось добавить сотрудника. Проверьте поля, уникальность логина и права.");
    } finally {
      setStaffPassword("");
      setPending(false);
    }
  }

  async function toggleStaff(row: StaffOverview["staff"][number]) {
    if (!identity || identity.role !== "OWNER" || row.role === "OWNER" || pending) return;
    setPending(true);
    setSectionError("");
    try {
      const response = await fetch(`/core/api/v1/admin/staff/${row.id}`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ active: !row.active }),
      });
      if (!response.ok) throw new Error(String(response.status));
      const refreshed = await fetch("/core/api/v1/admin/staff/overview", { cache: "no-store" });
      if (!refreshed.ok) throw new Error("refresh");
      setStaff(await refreshed.json() as StaffOverview);
    } catch {
      setSectionError("Не удалось изменить доступ сотрудника. Данные не подтверждены.");
    } finally { setPending(false); }
  }

  return <main className="login-screen">
    <section className="login-card" aria-labelledby="shared-auth-title" style={{ maxWidth: identity ? 920 : 520, width: "100%" }}>
      <p className="eyebrow">MARINA SMART · Изолированная тестовая платформа</p>
      <h1 id="shared-auth-title">Общий вход</h1>
      {mode === "loading" && <p role="status">Проверяю доступность входа…</p>}
      {mode === "unavailable" && <p role="status">Этот вход доступен только в отдельном тестовом контуре общей платформы.</p>}
      {mode === "ready" && !identity && <form onSubmit={login}>
        <p>Используйте выданные коды организации и гостиницы.</p>
        <label>Код организации<input required minLength={3} maxLength={80} value={tenant} onChange={e => setTenant(e.target.value)} autoCapitalize="none" spellCheck={false} /></label>
        <label>Код отеля<input required minLength={3} maxLength={80} value={property} onChange={e => setProperty(e.target.value)} autoCapitalize="none" spellCheck={false} /></label>
        <label>Логин<input required minLength={2} maxLength={80} value={username} onChange={e => setUsername(e.target.value)} autoComplete="username" /></label>
        <label>Пароль<input required type="password" minLength={8} maxLength={256} value={password} onChange={e => setPassword(e.target.value)} autoComplete="current-password" /></label>
        <button className="btn primary login-button" disabled={pending}>{pending ? "Проверяю…" : "Войти"}</button>
      </form>}
      {mode === "ready" && identity && <>
        <p role="status">Подтверждённый вход: <strong>{identity.display_name}</strong> · {identity.property_code} · {identity.role}</p>
        <p>Доступны только проверенные функции. Остальные разделы и операции PMS пока закрыты.</p>
        <nav aria-label="Проверяемые разделы" style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 20 }}>
          {sections.map(item => <button className="btn" type="button" key={item} aria-current={section === item ? "page" : undefined}
            onClick={() => setSection(item)}>{item === "dashboard" ? "Дашборд" : item === "grid" ? "Шахматка" : "Персонал"}</button>)}
        </nav>
        {!sections.length && <p>Для этой роли рабочие разделы ещё не приняты. Доступ к данным других гостиниц закрыт.</p>}
        {loadingSection && <p role="status">Загружаю данные своей гостиницы…</p>}
        {sectionError && <p role="alert" className="login-error">{sectionError}</p>}
        {!loadingSection && !sectionError && section === "dashboard" && dashboard &&
          <section aria-label="Дашборд гостиницы">
            <h2>{dashboard.property.name}</h2>
            <p>Номеров: {dashboard.rooms.total} · Убрано: {dashboard.rooms.clean} · Требуют уборки: {dashboard.rooms.dirty}</p>
            <p>Проживают: {dashboard.stays.in_house} · Заезды сегодня: {dashboard.stays.arrivals_today} · Выезды: {dashboard.stays.departures_today}</p>
            <p>Диалогов без ответа: {dashboard.communications.needs_reply}</p>
          </section>}
        {!loadingSection && !sectionError && section === "grid" && grid &&
          <section aria-label="Шахматка">
            <h2>Шахматка · ближайшие 7 дней</h2>
            <p>Номеров: {grid.rooms.length}</p>
            <div style={{ overflowX: "auto" }}>
              <table><thead><tr><th>Номер</th><th>Состояние</th><th>Занятость</th></tr></thead>
                <tbody>{grid.rooms.map(room => <tr key={room.id}><td>{room.code} · {room.name}</td>
                  <td>{room.operational_state}</td><td>{room.blocks.length ? room.blocks.map(b => `${b.start}–${b.end} (${b.type})`).join("; ") : "Свободно"}</td></tr>)}</tbody>
              </table>
            </div>
          </section>}
        {!loadingSection && !sectionError && section === "staff" && staff &&
          <section aria-label="Персонал гостиницы">
            <h2>Сотрудники ({staff.staff.length})</h2>
            <div style={{ overflowX: "auto" }}>
              <table><thead><tr><th>Имя</th><th>Роль</th><th>Статус</th>{identity.role === "OWNER" && <th>Доступ</th>}</tr></thead>
                <tbody>{staff.staff.map(row => <tr key={row.id}><td>{row.display_name} ({row.username})</td>
                  <td>{row.role}</td><td>{row.active ? "Активен" : "Отключён"}</td>
                  {identity.role === "OWNER" && <td>{row.role !== "OWNER" && <button className="btn" type="button" disabled={pending}
                    onClick={() => void toggleStaff(row)}>{row.active ? "Отключить" : "Включить"}</button>}</td>}</tr>)}</tbody>
              </table>
            </div>
            {identity.role === "OWNER" && <form onSubmit={createStaff} aria-label="Создание сотрудника">
              <h3>Новый сотрудник</h3>
              <label>Логин<input required minLength={2} maxLength={80} pattern="[A-Za-z0-9._-]+" value={staffUsername} onChange={e => setStaffUsername(e.target.value)} /></label>
              <label>Имя<input required minLength={2} maxLength={160} value={staffName} onChange={e => setStaffName(e.target.value)} /></label>
              <label>Пароль<input required type="password" minLength={8} maxLength={256} autoComplete="new-password" value={staffPassword} onChange={e => setStaffPassword(e.target.value)} /></label>
              <label>Роль<select value={staffRole} onChange={e => setStaffRole(e.target.value as (typeof MANAGED_ROLES)[number])}>
                {MANAGED_ROLES.map(role => <option key={role} value={role}>{role}</option>)}</select></label>
              <button className="btn primary" disabled={pending} type="submit">Создать сотрудника</button>
            </form>}
          </section>}
        <button className="btn" onClick={() => void logout()} disabled={pending}>Выйти</button>
      </>}
      {error && <p role="alert" className="login-error">{error}</p>}
    </section>
  </main>;
}
