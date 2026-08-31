"use client";

import { FormEvent, useEffect, useState } from "react";
import DashboardBoard from "./DashboardBoard";
import GrowthControlBoard from "./GrowthControlBoard";
import GuestHistoryBoard from "./GuestHistoryBoard";
import HotelFinanceBoard from "./HotelFinanceBoard";
import InboxBoard from "./InboxBoard";
import MyStayAdminBoard from "./MyStayAdminBoard";
import OperationsBoard from "./OperationsBoard";
import PMSGrid from "./PMSGridV9";
import ReceptionBoard from "./ReceptionBoard";
import ReportsBoard from "./ReportsBoard";
import RequestsBoard from "./RequestsBoard";
import SiteContentBoard from "./SiteContentBoard";
import StaffBoard from "./StaffBoard";

type User = {
  id: string;
  username: string;
  display_name: string;
  role: string;
  property_code: string;
};

type Tab = "DASHBOARD" | "PMS" | "REQUESTS" | "RESERVATIONS" | "GUESTS" | "GROWTH" | "FINANCE" | "REPORTS" | "CONTENT" | "INBOX" | "OPS" | "STAFF" | "MY_STAY";

const managementRoles = new Set(["OWNER", "ADMIN", "MANAGER"]);
const receptionRoles = new Set(["OWNER", "ADMIN", "MANAGER", "RECEPTION"]);
const operationsRoles = new Set(["OWNER", "ADMIN", "MANAGER", "MAID", "TECHNICIAN"]);

function startTab(role: string): Tab {
  if (managementRoles.has(role)) return "DASHBOARD";
  if (role === "RECEPTION") return "RESERVATIONS";
  return "OPS";
}

export default function AdminShell() {
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(true);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [tab, setTab] = useState<Tab>("DASHBOARD");

  useEffect(() => {
    fetch("/core/api/v1/auth/me", { cache: "no-store" })
      .then(async (response) => response.ok ? (await response.json()) as User : null)
      .then((payload) => {
        setUser(payload);
        if (payload) setTab(startTab(payload.role));
      })
      .catch(() => setUser(null))
      .finally(() => setChecking(false));
  }, []);

  async function login(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const response = await fetch("/core/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (!response.ok) {
        setError("Неверный логин или пароль.");
        return;
      }
      const payload = (await response.json()) as User;
      setUser(payload);
      setTab(startTab(payload.role));
      setPassword("");
    } catch {
      setError("Сервис входа недоступен. Проверьте Resort Core.");
    } finally {
      setSubmitting(false);
    }
  }

  async function logout() {
    try {
      await fetch("/core/api/v1/auth/logout", { method: "POST" });
    } finally {
      setUser(null);
      setPassword("");
    }
  }

  if (checking) {
    return <main className="login-screen"><div className="login-card"><p className="eyebrow">Resort OS</p><h1>Проверяю доступ…</h1></div></main>;
  }

  if (!user) {
    return (
      <main className="login-screen">
        <form className="login-card" onSubmit={login}>
          <p className="eyebrow">Три Короны · Resort OS</p>
          <h1>Вход в управление</h1>
          <p className="login-copy">Шахматка, CRM, бронирования, сайт и операционные данные доступны только сотрудникам.</p>
          <label><span>Логин</span><input autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} minLength={2} required autoFocus /></label>
          <label><span>Пароль</span><input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} minLength={8} required /></label>
          {error && <div className="login-error">{error}</div>}
          <button className="btn primary login-button" disabled={submitting}>{submitting ? "Входим…" : "Войти"}</button>
        </form>
      </main>
    );
  }

  const isManagement = managementRoles.has(user.role);
  const isReception = receptionRoles.has(user.role);
  const canOps = operationsRoles.has(user.role);

  return (
    <>
      <div className="auth-toolbar admin-nav">
        <div className="admin-identity"><strong>Три Короны · Resort OS</strong><span>{user.display_name} · {user.role}</span></div>
        <nav className="admin-tabs">
          {isManagement && <button className={tab === "DASHBOARD" ? "active" : ""} onClick={() => setTab("DASHBOARD")}>Главная</button>}
          {isManagement && <button className={tab === "PMS" ? "active" : ""} onClick={() => setTab("PMS")}>Супершахматка</button>}
          {isManagement && <button className={tab === "REQUESTS" ? "active" : ""} onClick={() => setTab("REQUESTS")}>CRM / Заявки</button>}
          {isReception && <button className={tab === "RESERVATIONS" ? "active" : ""} onClick={() => setTab("RESERVATIONS")}>Ресепшен / Брони</button>}
          {isReception && <button className={tab === "MY_STAY" ? "active" : ""} onClick={() => setTab("MY_STAY")}>MY STAY / QR</button>}
          {isManagement && <button className={tab === "GUESTS" ? "active" : ""} onClick={() => setTab("GUESTS")}>Гости / История</button>}
          {isManagement && <button className={tab === "GROWTH" ? "active" : ""} onClick={() => setTab("GROWTH")}>Рост / Отзывы</button>}
          {isManagement && <button className={tab === "FINANCE" ? "active" : ""} onClick={() => setTab("FINANCE")}>Финансы</button>}
          {isManagement && <button className={tab === "REPORTS" ? "active" : ""} onClick={() => setTab("REPORTS")}>Отчёты / Аналитика</button>}
          {user.role !== "RECEPTION" && isManagement && <button className={tab === "CONTENT" ? "active" : ""} onClick={() => setTab("CONTENT")}>Сайт / Контент</button>}
          {canOps && <button className={tab === "OPS" ? "active" : ""} onClick={() => setTab("OPS")}>Уборка / Ремонт</button>}
          {isManagement && <button className={tab === "STAFF" ? "active" : ""} onClick={() => setTab("STAFF")}>Персонал</button>}
          {isManagement && <button className={tab === "INBOX" ? "active" : ""} onClick={() => setTab("INBOX")}>Сообщения</button>}
        </nav>
        <button className="logout-button" onClick={logout}>Выйти</button>
      </div>
      {tab === "DASHBOARD" && isManagement && <DashboardBoard onNavigate={(destination) => setTab(destination as Tab)} />}
      {tab === "PMS" && isManagement && <PMSGrid />}
      {tab === "REQUESTS" && isManagement && <RequestsBoard />}
      {tab === "RESERVATIONS" && isReception && <ReceptionBoard />}
      {tab === "MY_STAY" && isReception && <MyStayAdminBoard />}
      {tab === "GUESTS" && isManagement && <GuestHistoryBoard />}
      {tab === "GROWTH" && isManagement && <GrowthControlBoard />}
      {tab === "FINANCE" && isManagement && <HotelFinanceBoard />}
      {tab === "REPORTS" && isManagement && <ReportsBoard />}
      {tab === "CONTENT" && isManagement && <SiteContentBoard />}
      {tab === "OPS" && canOps && <OperationsBoard user={user} />}
      {tab === "STAFF" && isManagement && <StaffBoard />}
      {tab === "INBOX" && isManagement && <InboxBoard />}
      {!isManagement && !isReception && !canOps && <main className="login-screen"><div className="login-card"><p className="eyebrow">Resort OS</p><h1>Для этой роли используется Staff-интерфейс.</h1></div></main>}
    </>
  );
}
