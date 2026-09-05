"use client";

import { FormEvent, useEffect, useState } from "react";
import DashboardBoard from "./DashboardBoard";
import DiningManagementBoard from "./DiningManagementBoard";
import GroupBookingBoard from "./GroupBookingBoard";
import GrowthControlBoard from "./GrowthControlBoard";
import GuestHistoryBoard from "./GuestHistoryBoard";
import GuestOffersBoard from "./GuestOffersBoard";
import GuestServicesCenter from "./GuestServicesCenter";
import GuestServiceSettingsBoard from "./GuestServiceSettingsBoard";
import HotelFinanceBoard from "./HotelFinanceBoard";
import InboxBoard from "./InboxBoard";
import OperationsBoard from "./OperationsBoard";
import PMSGrid from "./PMSGridV9";
import ReceptionWorkspace from "./ReceptionWorkspace";
import ReportsBoard from "./ReportsBoard";
import RequestsBoard from "./RequestsBoard";
import RoomQrBoard from "./RoomQrBoard";
import ServicePointsBoard from "./ServicePointsBoard";
import SiteContentBoard from "./SiteContentBoard";
import StaffBoard from "./StaffBoard";

type User = {
  id: string;
  username: string;
  display_name: string;
  role: string;
  property_code: string;
};

type Tab = "DASHBOARD" | "PMS" | "GROUPS" | "REQUESTS" | "RESERVATIONS" | "SERVICES" | "DINING" | "SERVICE_SETTINGS" | "GUESTS" | "OFFERS" | "GROWTH" | "FINANCE" | "REPORTS" | "CONTENT" | "ROOM_QR" | "POINT_QR" | "INBOX" | "OPS" | "STAFF";

const ADMIN_ROLES = new Set(["OWNER", "MANAGER", "RECEPTION", "MAID", "TECHNICIAN"]);
const HOUSEKEEPING_SYNC_ROLES = new Set(["OWNER", "MANAGER", "RECEPTION", "MAID"]);

function canEnterAdmin(role?: string | null): boolean {
  return Boolean(role && ADMIN_ROLES.has(role));
}

function initialTab(role?: string | null): Tab {
  if (["OWNER", "MANAGER"].includes(role || "")) return "DASHBOARD";
  if (role === "RECEPTION") return "RESERVATIONS";
  if (["MAID", "TECHNICIAN"].includes(role || "")) return "OPS";
  return "DASHBOARD";
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
      .then(async (response) => {
        if (!response.ok) return null;
        return (await response.json()) as User;
      })
      .then((payload) => {
        if (payload && !canEnterAdmin(payload.role)) {
          void fetch("/core/api/v1/auth/logout", { method: "POST" }).catch(() => undefined);
          setUser(null);
          return;
        }
        setUser(payload);
        setTab(initialTab(payload?.role));
      })
      .catch(() => setUser(null))
      .finally(() => setChecking(false));
  }, []);

  useEffect(() => {
    if (!user || !HOUSEKEEPING_SYNC_ROLES.has(user.role)) return;
    void fetch("/core/api/v1/ops/housekeeping/schedule/ensure", { method: "POST" }).catch(() => undefined);
  }, [user?.id, user?.role]);

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
      if (!canEnterAdmin(payload.role)) {
        await fetch("/core/api/v1/auth/logout", { method: "POST" }).catch(() => undefined);
        setUser(null);
        setError("Эта роль работает в интерфейсе «Моя смена», а не в Admin/PMS.");
        return;
      }
      setUser(payload);
      setTab(initialTab(payload.role));
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

  const isManager = ["OWNER", "MANAGER"].includes(user.role);
  const isReception = user.role === "RECEPTION";
  const canUseReception = isManager || isReception;
  const canManageRoomQr = ["OWNER", "MANAGER", "RECEPTION"].includes(user.role);
  const canUseOps = isManager || ["MAID", "TECHNICIAN"].includes(user.role);

  return (
    <>
      <div className="auth-toolbar admin-nav">
        <div className="admin-identity"><strong>Три Короны · Resort OS</strong><span>{user.display_name} · {user.role}</span></div>
        <nav className="admin-tabs">
          {isManager && <button className={tab === "DASHBOARD" ? "active" : ""} onClick={() => setTab("DASHBOARD")}>Главная</button>}
          {isManager && <button className={tab === "PMS" ? "active" : ""} onClick={() => setTab("PMS")}>Супершахматка</button>}
          {canUseReception && <button className={tab === "GROUPS" ? "active" : ""} onClick={() => setTab("GROUPS")}>Групповая бронь</button>}
          {isManager && <button className={tab === "REQUESTS" ? "active" : ""} onClick={() => setTab("REQUESTS")}>CRM / Заявки</button>}
          {canUseReception && <button className={tab === "RESERVATIONS" ? "active" : ""} onClick={() => setTab("RESERVATIONS")}>Ресепшен / Брони</button>}
          {canUseReception && <button className={tab === "SERVICES" ? "active" : ""} onClick={() => setTab("SERVICES")}>Сервис гостя</button>}
          {canUseReception && <button className={tab === "DINING" ? "active" : ""} onClick={() => setTab("DINING")}>Питание / Ресторан</button>}
          {isManager && <button className={tab === "SERVICE_SETTINGS" ? "active" : ""} onClick={() => setTab("SERVICE_SETTINGS")}>Настройки услуг</button>}
          {isManager && <button className={tab === "GUESTS" ? "active" : ""} onClick={() => setTab("GUESTS")}>Гости / История</button>}
          {isManager && <button className={tab === "OFFERS" ? "active" : ""} onClick={() => setTab("OFFERS")}>Офферы гостю</button>}
          {canManageRoomQr && <button className={tab === "ROOM_QR" ? "active" : ""} onClick={() => setTab("ROOM_QR")}>QR номеров</button>}
          {isManager && <button className={tab === "POINT_QR" ? "active" : ""} onClick={() => setTab("POINT_QR")}>QR зон</button>}
          {isManager && <button className={tab === "GROWTH" ? "active" : ""} onClick={() => setTab("GROWTH")}>Рост / Отзывы</button>}
          {isManager && <button className={tab === "FINANCE" ? "active" : ""} onClick={() => setTab("FINANCE")}>Финансы</button>}
          {isManager && <button className={tab === "REPORTS" ? "active" : ""} onClick={() => setTab("REPORTS")}>Отчёты / Аналитика</button>}
          {isManager && <button className={tab === "CONTENT" ? "active" : ""} onClick={() => setTab("CONTENT")}>Сайт / Контент</button>}
          {canUseOps && <button className={tab === "OPS" ? "active" : ""} onClick={() => setTab("OPS")}>Уборка / Ремонт</button>}
          {isManager && <button className={tab === "STAFF" ? "active" : ""} onClick={() => setTab("STAFF")}>Персонал</button>}
          {isManager && <button className={tab === "INBOX" ? "active" : ""} onClick={() => setTab("INBOX")}>Сообщения</button>}
        </nav>
        <button className="logout-button" onClick={logout}>Выйти</button>
      </div>
      {tab === "DASHBOARD" && isManager && <DashboardBoard onNavigate={(destination) => setTab(destination as Tab)} />}
      {tab === "PMS" && isManager && <PMSGrid />}
      {tab === "GROUPS" && canUseReception && <GroupBookingBoard />}
      {tab === "REQUESTS" && isManager && <RequestsBoard />}
      {tab === "RESERVATIONS" && canUseReception && <ReceptionWorkspace userRole={user.role} onNavigate={(destination) => setTab(destination as Tab)} />}
      {tab === "SERVICES" && canUseReception && <GuestServicesCenter user={{ id: user.id, role: user.role }} />}
      {tab === "DINING" && canUseReception && <DiningManagementBoard />}
      {tab === "SERVICE_SETTINGS" && isManager && <GuestServiceSettingsBoard />}
      {tab === "GUESTS" && isManager && <GuestHistoryBoard />}
      {tab === "OFFERS" && isManager && <GuestOffersBoard />}
      {tab === "ROOM_QR" && canManageRoomQr && <RoomQrBoard />}
      {tab === "POINT_QR" && isManager && <ServicePointsBoard />}
      {tab === "GROWTH" && isManager && <GrowthControlBoard />}
      {tab === "FINANCE" && isManager && <HotelFinanceBoard />}
      {tab === "REPORTS" && isManager && <ReportsBoard />}
      {tab === "CONTENT" && isManager && <SiteContentBoard />}
      {tab === "OPS" && canUseOps && <OperationsBoard user={user} />}
      {tab === "STAFF" && isManager && <StaffBoard />}
      {tab === "INBOX" && isManager && <InboxBoard />}
    </>
  );
}
