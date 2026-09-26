"use client";

import { FormEvent, useEffect, useState } from "react";
import AgentsBoard from "./AgentsBoard";
import DashboardBoard from "./DashboardBoard";
import DiningManagementBoard from "./DiningManagementBoard";
import GroupBookingBoard from "./GroupBookingBoard";
import GrowthControlBoard from "./GrowthControlBoard";
import GuestHistoryBoard from "./GuestHistoryBoard";
import GuestOffersBoard from "./GuestOffersBoard";
import GuestServicesCenter from "./GuestServicesCenter";
import GuestServiceSettingsBoard from "./GuestServiceSettingsBoard";
import HotelFinanceBoard from "./HotelFinanceBoard";
import HotelSetupBoard from "./HotelSetupBoard";
import InboxBoard from "./InboxBoard";
import MarketingBoard from "./MarketingBoard";
import OperationsBoard from "./OperationsBoard";
import PMSGrid from "./PMSGridV9";
import RateManagementBoard from "./RateManagementBoard";
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

type Tab = "DASHBOARD" | "PMS" | "RATES" | "GROUPS" | "REQUESTS" | "AGENTS" | "RESERVATIONS" | "SERVICES" | "DINING" | "SERVICE_SETTINGS" | "GUESTS" | "OFFERS" | "MARKETING" | "GROWTH" | "FINANCE" | "REPORTS" | "CONTENT" | "ROOM_QR" | "POINT_QR" | "INBOX" | "OPS" | "STAFF" | "SETTINGS";

const ADMIN_ROLES = new Set(["OWNER", "MANAGER", "RECEPTION", "MAID", "TECHNICIAN"]);
const HOUSEKEEPING_SYNC_ROLES = new Set(["OWNER", "MANAGER", "RECEPTION", "MAID"]);
const SESSION_CHECK_INTERVAL_MS = 30_000;
const DEFAULT_ENABLED_MODULES = ["GROUPS", "AGENTS", "DINING", "ROOM_QR"];

function canEnterAdmin(role?: string | null): boolean {
  return Boolean(role && ADMIN_ROLES.has(role));
}

function initialTab(role?: string | null): Tab {
  if (["OWNER", "MANAGER"].includes(role || "")) return "DASHBOARD";
  if (role === "RECEPTION") return "RESERVATIONS";
  if (["MAID", "TECHNICIAN"].includes(role || "")) return "OPS";
  return "DASHBOARD";
}

function coreApiRequest(input: RequestInfo | URL): boolean {
  const raw = typeof input === "string" ? input : input instanceof Request ? input.url : input.toString();
  try {
    const url = new URL(raw, window.location.origin);
    return url.origin === window.location.origin && url.pathname.startsWith("/core/api/v1/");
  } catch {
    return false;
  }
}

export default function AdminShell() {
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(true);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [tab, setTab] = useState<Tab>("DASHBOARD");
  const [enabledModules, setEnabledModules] = useState<string[]>(DEFAULT_ENABLED_MODULES);

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
    if (!user) return;

    const nativeFetch = window.fetch.bind(window);
    const authAwareFetch: typeof window.fetch = async (...args) => {
      const response = await nativeFetch(...args);
      const input = args[0];
      if ((response.status === 401 || response.status === 403) && coreApiRequest(input)) {
        setUser(null);
      }
      return response;
    };

    window.fetch = authAwareFetch;
    return () => {
      if (window.fetch === authAwareFetch) window.fetch = nativeFetch;
    };
  }, [user?.id]);

  useEffect(() => {
    if (!user) return;

    let disposed = false;
    const validateSession = async () => {
      try {
        const response = await fetch("/core/api/v1/auth/me", { cache: "no-store" });
        if (disposed) return;
        if (response.status === 401 || response.status === 403) {
          setUser(null);
          return;
        }
        if (!response.ok) return;
        const payload = (await response.json()) as User;
        if (!canEnterAdmin(payload.role)) {
          setUser(null);
          return;
        }
        if (payload.id !== user.id || payload.role !== user.role || payload.display_name !== user.display_name) {
          setUser(payload);
        }
      } catch {
        // A transient network failure is not proof that the session expired.
      }
    };

    const timer = window.setInterval(() => void validateSession(), SESSION_CHECK_INTERVAL_MS);
    const onFocus = () => void validateSession();
    const onVisibilityChange = () => {
      if (document.visibilityState === "visible") void validateSession();
    };

    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", onVisibilityChange);
    return () => {
      disposed = true;
      window.clearInterval(timer);
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [user?.id, user?.role, user?.display_name]);

  useEffect(() => {
    if (!user || !HOUSEKEEPING_SYNC_ROLES.has(user.role)) return;
    void fetch("/core/api/v1/ops/housekeeping/schedule/ensure", { method: "POST" }).catch(() => undefined);
  }, [user?.id, user?.role]);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    fetch("/core/api/v1/admin/hotel-setup/modules", { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) return null;
        return await response.json() as { enabled_modules?: string[] };
      })
      .then((body) => {
        if (!cancelled && body?.enabled_modules) setEnabledModules(body.enabled_modules);
      })
      .catch(() => undefined);
    return () => { cancelled = true; };
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
    return <main className="login-screen"><div className="login-card"><img className="marina-brand-logo" src="/marina-smart-logo.webp" alt="MARINA SMART" /><p className="eyebrow">MARINA SMART · Hotel OS</p><h1>Проверяю доступ…</h1></div></main>;
  }

  if (!user) {
    return (
      <main className="login-screen">
        <form className="login-card" onSubmit={login}>
          <p className="eyebrow">MARINA SMART · Hotel OS</p>
          <h1>Вход в управление</h1>
          <p className="login-copy">Шахматка, CRM, бронирования и операционные данные доступны только сотрудникам.</p>
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
  const moduleEnabled = (module: string) => enabledModules.includes(module);

  return (
    <>
      <div className="auth-toolbar admin-nav">
        <div className="admin-identity"><img className="marina-brand-logo-small" src="/marina-smart-logo.webp" alt="" /><div><strong>MARINA SMART · Hotel OS</strong><span>{user.display_name} · {user.role}</span></div></div>
        <nav className="admin-tabs">
          {isManager && <button className={tab === "DASHBOARD" ? "active" : ""} onClick={() => setTab("DASHBOARD")}>Главная</button>}
          {isManager && <button className={tab === "PMS" ? "active" : ""} onClick={() => setTab("PMS")}>Супершахматка</button>}
          {canUseReception && <button className={tab === "RESERVATIONS" ? "active" : ""} onClick={() => setTab("RESERVATIONS")}>Брони / Ресепшен</button>}
          {isManager && <button className={tab === "REQUESTS" ? "active" : ""} onClick={() => setTab("REQUESTS")}>CRM / Заявки</button>}
          {isManager && <button className={tab === "FINANCE" ? "active" : ""} onClick={() => setTab("FINANCE")}>Финансы</button>}
          {canUseReception && <button className={tab === "SERVICES" ? "active" : ""} onClick={() => setTab("SERVICES")}>Сервис</button>}
          {canUseOps && <button className={tab === "OPS" ? "active" : ""} onClick={() => setTab("OPS")}>Операции</button>}
          {isManager && <button className={tab === "REPORTS" ? "active" : ""} onClick={() => setTab("REPORTS")}>Отчёты</button>}
          {isManager && <button className={`admin-settings-button ${tab === "SETTINGS" ? "active" : ""}`} onClick={() => setTab("SETTINGS")}>Настройки</button>}
          <details className="admin-more-menu">
            <summary>Ещё</summary>
            <div className="admin-more-panel">
              {isManager && <button className={tab === "RATES" ? "active" : ""} onClick={() => setTab("RATES")}>Цены / Сезоны</button>}
              {canUseReception && moduleEnabled("GROUPS") && <button className={tab === "GROUPS" ? "active" : ""} onClick={() => setTab("GROUPS")}>Групповая бронь</button>}
              {isManager && moduleEnabled("AGENTS") && <button className={tab === "AGENTS" ? "active" : ""} onClick={() => setTab("AGENTS")}>Агенты</button>}
              {isManager && moduleEnabled("MARKETING") && <button className={tab === "MARKETING" ? "active" : ""} onClick={() => setTab("MARKETING")}>Маркетинг</button>}
              {canUseReception && moduleEnabled("DINING") && <button className={tab === "DINING" ? "active" : ""} onClick={() => setTab("DINING")}>Питание / Ресторан</button>}
              {isManager && <button className={tab === "SERVICE_SETTINGS" ? "active" : ""} onClick={() => setTab("SERVICE_SETTINGS")}>Настройки услуг</button>}
              {isManager && <button className={tab === "GUESTS" ? "active" : ""} onClick={() => setTab("GUESTS")}>Гости / История</button>}
              {isManager && moduleEnabled("OFFERS") && <button className={tab === "OFFERS" ? "active" : ""} onClick={() => setTab("OFFERS")}>Офферы гостю</button>}
              {canManageRoomQr && moduleEnabled("ROOM_QR") && <button className={tab === "ROOM_QR" ? "active" : ""} onClick={() => setTab("ROOM_QR")}>QR номеров</button>}
              {isManager && moduleEnabled("POINT_QR") && <button className={tab === "POINT_QR" ? "active" : ""} onClick={() => setTab("POINT_QR")}>QR зон</button>}
              {isManager && moduleEnabled("GROWTH") && <button className={tab === "GROWTH" ? "active" : ""} onClick={() => setTab("GROWTH")}>Рост / Отзывы</button>}
              {isManager && moduleEnabled("CONTENT") && <button className={tab === "CONTENT" ? "active" : ""} onClick={() => setTab("CONTENT")}>Сайт / Контент</button>}
              {isManager && <button className={tab === "STAFF" ? "active" : ""} onClick={() => setTab("STAFF")}>Персонал</button>}
              {isManager && moduleEnabled("INBOX") && <button className={tab === "INBOX" ? "active" : ""} onClick={() => setTab("INBOX")}>Сообщения</button>}
            </div>
          </details>
        </nav>
        <button className="logout-button" onClick={logout}>Выйти</button>
      </div>
      {tab === "DASHBOARD" && isManager && <DashboardBoard onNavigate={(destination) => setTab(destination as Tab)} />}
      {tab === "PMS" && isManager && <PMSGrid />}
      {tab === "RATES" && isManager && <RateManagementBoard />}
      {tab === "GROUPS" && canUseReception && moduleEnabled("GROUPS") && <GroupBookingBoard userRole={user.role} />}
      {tab === "REQUESTS" && isManager && <RequestsBoard />}
      {tab === "AGENTS" && isManager && moduleEnabled("AGENTS") && <AgentsBoard />}
      {tab === "MARKETING" && isManager && moduleEnabled("MARKETING") && <MarketingBoard />}
      {tab === "RESERVATIONS" && canUseReception && <ReceptionWorkspace userRole={user.role} onNavigate={(destination) => setTab(destination as Tab)} />}
      {tab === "SERVICES" && canUseReception && <GuestServicesCenter user={{ id: user.id, role: user.role }} />}
      {tab === "DINING" && canUseReception && moduleEnabled("DINING") && <DiningManagementBoard />}
      {tab === "SERVICE_SETTINGS" && isManager && <GuestServiceSettingsBoard />}
      {tab === "GUESTS" && isManager && <GuestHistoryBoard />}
      {tab === "OFFERS" && isManager && moduleEnabled("OFFERS") && <GuestOffersBoard />}
      {tab === "ROOM_QR" && canManageRoomQr && moduleEnabled("ROOM_QR") && <RoomQrBoard />}
      {tab === "POINT_QR" && isManager && moduleEnabled("POINT_QR") && <ServicePointsBoard />}
      {tab === "GROWTH" && isManager && moduleEnabled("GROWTH") && <GrowthControlBoard />}
      {tab === "FINANCE" && isManager && <HotelFinanceBoard />}
      {tab === "REPORTS" && isManager && <ReportsBoard />}
      {tab === "CONTENT" && isManager && moduleEnabled("CONTENT") && <SiteContentBoard />}
      {tab === "OPS" && canUseOps && <OperationsBoard user={user} />}
      {tab === "STAFF" && isManager && <StaffBoard userRole={user.role} />}
      {tab === "INBOX" && isManager && moduleEnabled("INBOX") && <InboxBoard />}
      {tab === "SETTINGS" && isManager && <HotelSetupBoard onModulesChanged={setEnabledModules} />}
    </>
  );
}