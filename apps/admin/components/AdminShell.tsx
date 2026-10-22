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
import HotelRulesBoard from "./HotelRulesBoard";
import InboxBoard from "./InboxBoard";
import WhatsAppWorkspace from "./WhatsAppWorkspace";
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
import MarinaAiAssistant from "./MarinaAiAssistant";
import ChannelManagerBoard from "./ChannelManagerBoard";

type User = {
  id: string;
  username: string;
  display_name: string;
  role: string;
  property_code: string;
  module_permissions: string[];
  module_permissions_custom: boolean;
};

type Tab = "DASHBOARD" | "PMS" | "RATES" | "GROUPS" | "REQUESTS" | "AGENTS" | "RESERVATIONS" | "SERVICES" | "DINING" | "SERVICE_SETTINGS" | "GUESTS" | "OFFERS" | "MARKETING" | "GROWTH" | "FINANCE" | "REPORTS" | "CONTENT" | "ROOM_QR" | "POINT_QR" | "INBOX" | "WHATSAPP" | "OPS" | "STAFF" | "SETTINGS" | "HOTEL_RULES" | "CHANNELS";

const ADMIN_ROLES = new Set(["OWNER", "MANAGER", "RECEPTION", "AGENT", "MAID", "TECHNICIAN"]);
const HOUSEKEEPING_SYNC_ROLES = new Set(["OWNER", "MANAGER", "RECEPTION", "MAID"]);
const SESSION_CHECK_INTERVAL_MS = 30_000;
const DEFAULT_ENABLED_MODULES = ["GROUPS", "AGENTS", "MARKETING", "DINING", "OFFERS", "GROWTH", "CONTENT", "ROOM_QR", "POINT_QR", "INBOX"];

function canEnterAdmin(role?: string | null, permissions?: string[] | null, customPermissions = false): boolean {
  return Boolean((role && ADMIN_ROLES.has(role)) || (customPermissions && permissions?.length));
}

const MODULE_TABS: Record<string, Tab> = {
  DASHBOARD: "DASHBOARD", PMS: "PMS", RATES: "RATES", GROUPS: "GROUPS", REQUESTS: "REQUESTS",
  AGENTS: "AGENTS", RESERVATIONS: "RESERVATIONS", SERVICES: "SERVICES", DINING: "DINING",
  SERVICE_SETTINGS: "SERVICE_SETTINGS", GUESTS: "GUESTS", OFFERS: "OFFERS", MARKETING: "MARKETING",
  GROWTH: "GROWTH", FINANCE: "FINANCE", REPORTS: "REPORTS", CONTENT: "CONTENT", ROOM_QR: "ROOM_QR",
  POINT_QR: "POINT_QR", INBOX: "INBOX", WHATSAPP: "WHATSAPP", OPS: "OPS", STAFF: "STAFF",
  SETTINGS: "SETTINGS", HOTEL_RULES: "HOTEL_RULES", CHANNELS: "CHANNELS",
};

function initialTab(role?: string | null, permissions: string[] = []): Tab {
  const preferred: Tab = ["OWNER", "MANAGER"].includes(role || "") ? "DASHBOARD" : role === "RECEPTION" ? "RESERVATIONS" : role === "AGENT" ? "PMS" : ["MAID", "TECHNICIAN"].includes(role || "") ? "OPS" : "DASHBOARD";
  return permissions.includes(preferred) ? preferred : (permissions.map((item) => MODULE_TABS[item]).find(Boolean) || preferred);
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
  const [hotelName, setHotelName] = useState<string>("");
  const [hotelLogoUrl, setHotelLogoUrl] = useState<string>("");

  useEffect(() => {
    fetch("/core/api/v1/auth/me", { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) return null;
        return (await response.json()) as User;
      })
      .then((payload) => {
        if (payload && !canEnterAdmin(payload.role, payload.module_permissions, payload.module_permissions_custom)) {
          void fetch("/core/api/v1/auth/logout", { method: "POST" }).catch(() => undefined);
          setUser(null);
          return;
        }
        setUser(payload);
        setTab(initialTab(payload?.role, payload?.module_permissions));
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
      if (response.status === 401 && coreApiRequest(input)) {
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
        if (!canEnterAdmin(payload.role, payload.module_permissions, payload.module_permissions_custom)) {
          setUser(null);
          return;
        }
        if (payload.id !== user.id || payload.role !== user.role || payload.display_name !== user.display_name || payload.module_permissions.join("|") !== user.module_permissions.join("|") || payload.module_permissions_custom !== user.module_permissions_custom) {
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
        return await response.json() as { enabled_modules?: string[]; hotel_name?: string; property_name?: string; hotel_logo_url?: string | null };
      })
      .then((body) => {
        if (cancelled || !body) return;
        if (body.enabled_modules) setEnabledModules(body.enabled_modules);
        setHotelName(body.hotel_name || body.property_name || "");
        setHotelLogoUrl(body.hotel_logo_url || "");
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
        // Cloudflare Access and reverse proxies may reject the HTTP request
        // before it reaches MARINA Core. Do not mislabel their 401 as bad credentials.
        const contentType = response.headers.get("content-type") || "";
        const serverJson = contentType.includes("application/json");
        if (!serverJson) {
          setError("Внешний шлюз не пропустил запрос входа. Проверьте Cloudflare Access или откройте локальный адрес.");
        } else if (response.status === 401) {
          setError("Неверный логин или пароль.");
        } else {
          setError(`Не удалось войти: ошибка сервера (${response.status}). Попробуйте снова или обратитесь к администратору.`);
        }
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
      setError("Сервис входа MARINA SMART недоступен. Проверьте API.");
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
          <img className="marina-brand-logo" src="/marina-smart-logo.webp" alt="MARINA SMART" />
          <p className="eyebrow">MARINA SMART · Hotel OS</p>
          <h1>Вход в управление</h1>
          <p className="login-copy">Шахматка, CRM, бронирования и операционные данные доступны только сотрудникам.</p>
          <label><span>Логин</span><input autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} minLength={2} required autoFocus /></label>
          <label><span>Пароль</span><input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} minLength={3} required /></label>
          {error && <div className="login-error">{error}</div>}
          <button className="btn primary login-button" disabled={submitting}>{submitting ? "Входим…" : "Войти"}</button>
        </form>
      </main>
    );
  }

  const canAccess = (section: string) => user.module_permissions.includes(section);
  const isReception = user.role === "RECEPTION";
  const isAgent = user.role === "AGENT";
  const canManageRoomQr = canAccess("ROOM_QR");
  const canUseOps = canAccess("OPS");
  const moduleEnabled = (module: string) => enabledModules.includes(module);

  return (
    <>
      <div className="auth-toolbar admin-nav">
        <div className="admin-identity">
          <img className="marina-brand-logo-small" src="/marina-smart-logo.webp" alt="MARINA SMART" />
          {hotelLogoUrl && <img className="hotel-brand-logo-small" src={hotelLogoUrl} alt={hotelName || "Логотип отеля"} />}
          <div><strong>MARINA SMART · Hotel OS</strong><span>{hotelName ? `${hotelName} · ` : ""}{user.display_name} · {user.role}</span></div>
        </div>
        <nav className="admin-tabs" aria-label="Разделы MARINA SMART">
          {canAccess("WHATSAPP") && <button className={tab === "WHATSAPP" ? "active" : ""} onClick={() => setTab("WHATSAPP")}>WhatsApp / AI</button>}
          {canAccess("PMS") && <button className={tab === "PMS" ? "active" : ""} onClick={() => setTab("PMS")}>{isAgent ? "Шахматка / Брони" : "Шахматка"}</button>}
          {canAccess("RESERVATIONS") && <button className={tab === "RESERVATIONS" ? "active" : ""} onClick={() => setTab("RESERVATIONS")}>Ресепшен</button>}
          {canAccess("REQUESTS") && <button className={tab === "REQUESTS" ? "active" : ""} onClick={() => setTab("REQUESTS")}>Заявки</button>}
          {canAccess("RATES") && <button className={tab === "RATES" ? "active" : ""} onClick={() => setTab("RATES")}>Цены / Сезоны</button>}
          {canAccess("SERVICES") && <button className={tab === "SERVICES" ? "active" : ""} onClick={() => setTab("SERVICES")}>Сервис гостя</button>}
          {canUseOps && <button className={tab === "OPS" ? "active" : ""} onClick={() => setTab("OPS")}>Уборка / Ремонт</button>}
          {canAccess("DASHBOARD") && <button className={tab === "DASHBOARD" ? "active" : ""} onClick={() => setTab("DASHBOARD")}>Главная</button>}
          {canAccess("FINANCE") && <button className={tab === "FINANCE" ? "active" : ""} onClick={() => setTab("FINANCE")}>Финансы</button>}
          {user.module_permissions.length > 0 && <details className="admin-more-menu">
            <summary>Все разделы</summary>
            <div className="admin-more-panel" onClick={(event) => {
              if (event.target instanceof Element && event.target.closest("button")) {
                (event.currentTarget.closest("details") as HTMLDetailsElement | null)?.removeAttribute("open");
              }
            }}>
              {canAccess("GROUPS") && <p className="admin-nav-section-label">Бронирования и продажи</p>}
              {canAccess("GROUPS") && moduleEnabled("GROUPS") && <button className={tab === "GROUPS" ? "active" : ""} onClick={() => setTab("GROUPS")}>Групповая бронь</button>}
              {canAccess("CHANNELS") && <button className={tab === "CHANNELS" ? "active" : ""} onClick={() => setTab("CHANNELS")}>Booking / Каналы продаж</button>}
              {canAccess("AGENTS") && moduleEnabled("AGENTS") && <button className={tab === "AGENTS" ? "active" : ""} onClick={() => setTab("AGENTS")}>Агентства</button>}
              {canAccess("INBOX") && moduleEnabled("INBOX") && <button className={tab === "INBOX" ? "active" : ""} onClick={() => setTab("INBOX")}>Все сообщения</button>}
              {canAccess("GUESTS") && <button className={tab === "GUESTS" ? "active" : ""} onClick={() => setTab("GUESTS")}>Гости / История</button>}
              {canAccess("MARKETING") && moduleEnabled("MARKETING") && <button className={tab === "MARKETING" ? "active" : ""} onClick={() => setTab("MARKETING")}>Маркетинг</button>}
              {canAccess("OFFERS") && moduleEnabled("OFFERS") && <button className={tab === "OFFERS" ? "active" : ""} onClick={() => setTab("OFFERS")}>Предложения гостям</button>}
              {canAccess("GROWTH") && moduleEnabled("GROWTH") && <button className={tab === "GROWTH" ? "active" : ""} onClick={() => setTab("GROWTH")}>Отзывы / Рост</button>}
              {canAccess("DINING") && <p className="admin-nav-section-label">Работа гостиницы</p>}
              {canAccess("DINING") && moduleEnabled("DINING") && <button className={tab === "DINING" ? "active" : ""} onClick={() => setTab("DINING")}>Питание / Ресторан</button>}
              {canManageRoomQr && moduleEnabled("ROOM_QR") && <button className={tab === "ROOM_QR" ? "active" : ""} onClick={() => setTab("ROOM_QR")}>QR номеров</button>}
              {canAccess("POINT_QR") && moduleEnabled("POINT_QR") && <button className={tab === "POINT_QR" ? "active" : ""} onClick={() => setTab("POINT_QR")}>QR зон</button>}
              {(canAccess("REPORTS") || canAccess("STAFF") || canAccess("HOTEL_RULES") || canAccess("SERVICE_SETTINGS") || canAccess("CONTENT") || canAccess("SETTINGS")) && <p className="admin-nav-section-label">Управление и настройки</p>}
              {canAccess("REPORTS") && <button className={tab === "REPORTS" ? "active" : ""} onClick={() => setTab("REPORTS")}>Отчёты / Аналитика</button>}
              {canAccess("STAFF") && <button className={tab === "STAFF" ? "active" : ""} onClick={() => setTab("STAFF")}>Персонал</button>}
              {canAccess("HOTEL_RULES") && <button className={tab === "HOTEL_RULES" ? "active" : ""} onClick={() => setTab("HOTEL_RULES")}>Знания отеля / MARINA AI</button>}
              {canAccess("SERVICE_SETTINGS") && <button className={tab === "SERVICE_SETTINGS" ? "active" : ""} onClick={() => setTab("SERVICE_SETTINGS")}>Настройки услуг</button>}
              {canAccess("CONTENT") && moduleEnabled("CONTENT") && <button className={tab === "CONTENT" ? "active" : ""} onClick={() => setTab("CONTENT")}>Сайт / Контент</button>}
              {canAccess("SETTINGS") && <button className={tab === "SETTINGS" ? "active" : ""} onClick={() => setTab("SETTINGS")}>Настройки гостиницы</button>}
            </div>
          </details>}
        </nav>
        <button className="logout-button" onClick={logout}>Выйти</button>
      </div>
      {user.module_permissions.length === 0 && <main className="management-shell"><section className="management-truth"><strong>Доступ к разделам отключён.</strong> Попросите собственника MARINA SMART выдать нужные разделы.</section></main>}
      {tab === "DASHBOARD" && canAccess("DASHBOARD") && <DashboardBoard isOwner={user.role === "OWNER"} onNavigate={(destination) => setTab(destination as Tab)} />}
      {tab === "PMS" && canAccess("PMS") && <PMSGrid agentMode={isAgent} readOnlyMode={isReception} />}
      {tab === "RATES" && canAccess("RATES") && <RateManagementBoard />}
      {tab === "GROUPS" && canAccess("GROUPS") && moduleEnabled("GROUPS") && <GroupBookingBoard userRole={user.role} />}
      {tab === "REQUESTS" && canAccess("REQUESTS") && <RequestsBoard />}
      {tab === "CHANNELS" && canAccess("CHANNELS") && <ChannelManagerBoard />}
      {tab === "AGENTS" && canAccess("AGENTS") && moduleEnabled("AGENTS") && <AgentsBoard userRole={user.role} />}
      {tab === "MARKETING" && canAccess("MARKETING") && moduleEnabled("MARKETING") && <MarketingBoard />}
      {tab === "RESERVATIONS" && canAccess("RESERVATIONS") && <ReceptionWorkspace userRole={user.role} onNavigate={(destination) => setTab(destination as Tab)} />}
      {tab === "SERVICES" && canAccess("SERVICES") && <GuestServicesCenter user={{ id: user.id, role: user.role }} />}
      {tab === "DINING" && canAccess("DINING") && moduleEnabled("DINING") && <DiningManagementBoard />}
      {tab === "SERVICE_SETTINGS" && canAccess("SERVICE_SETTINGS") && <GuestServiceSettingsBoard />}
      {tab === "GUESTS" && canAccess("GUESTS") && <GuestHistoryBoard />}
      {tab === "OFFERS" && canAccess("OFFERS") && moduleEnabled("OFFERS") && <GuestOffersBoard />}
      {tab === "ROOM_QR" && canAccess("ROOM_QR") && moduleEnabled("ROOM_QR") && <RoomQrBoard />}
      {tab === "POINT_QR" && canAccess("POINT_QR") && moduleEnabled("POINT_QR") && <ServicePointsBoard />}
      {tab === "GROWTH" && canAccess("GROWTH") && moduleEnabled("GROWTH") && <GrowthControlBoard />}
      {tab === "FINANCE" && canAccess("FINANCE") && <HotelFinanceBoard />}
      {tab === "REPORTS" && canAccess("REPORTS") && <ReportsBoard />}
      {tab === "CONTENT" && canAccess("CONTENT") && moduleEnabled("CONTENT") && <SiteContentBoard />}
      {tab === "OPS" && canUseOps && <OperationsBoard user={user} />}
      {tab === "STAFF" && canAccess("STAFF") && <StaffBoard userRole={user.role} propertyCode={user.property_code} />}
      {tab === "INBOX" && canAccess("INBOX") && moduleEnabled("INBOX") && <InboxBoard />}
      {tab === "WHATSAPP" && canAccess("WHATSAPP") && <WhatsAppWorkspace role={user.role} onNavigate={(destination) => setTab(destination)} />}
      {tab === "HOTEL_RULES" && canAccess("HOTEL_RULES") && <HotelRulesBoard />}
      {tab === "SETTINGS" && canAccess("SETTINGS") && <HotelSetupBoard
        onModulesChanged={setEnabledModules}
        onNavigate={(destination) => setTab(destination)}
        onIdentityChanged={(identity) => { setHotelName(identity.name); setHotelLogoUrl(identity.logo_url || ""); }}
      />}
      <MarinaAiAssistant screen={tab} role={user.role} onNavigate={(destination) => setTab(destination as Tab)} />
    </>
  );
}
