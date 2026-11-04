"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";

import GuestRequestShiftPanel from "./GuestRequestShiftPanel";
import StaffShiftV2 from "./StaffShiftV2";
import MarinaAiAssistant from "./MarinaAiAssistant";

type Role = "OWNER" | "MANAGER" | "RECEPTION" | "MAID" | "TECHNICIAN" | "DINING_STAFF" | "COOK" | "WAITER" | "STORE_STAFF";
type User = { id: string; username: string; display_name: string; role: Role; property_code: string; property_id?: string; tenant_id?: string };

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

const OPERATIONAL_ROLES = new Set<Role>(["OWNER", "MANAGER", "RECEPTION", "MAID", "TECHNICIAN", "COOK", "WAITER", "STORE_STAFF"]);
const LEGACY_SHIFT_ROLES = new Set<Role>(["OWNER", "MANAGER", "MAID", "TECHNICIAN"]);
const HOUSEKEEPING_SYNC_ROLES = new Set<Role>(["OWNER", "MANAGER", "RECEPTION", "MAID"]);
const roleLabel: Record<Role, string> = {
  OWNER: "Владелец",
  MANAGER: "Менеджер",
  RECEPTION: "Ресепшен",
  MAID: "Горничная",
  TECHNICIAN: "Техник",
  DINING_STAFF: "Устаревший доступ",
  COOK: "Повар",
  WAITER: "Официант",
  STORE_STAFF: "Магазин",
};

function isOperationalUser(value: unknown): value is User {
  if (!value || typeof value !== "object") return false;
  const role = (value as { role?: Role }).role;
  return Boolean(role && OPERATIONAL_ROLES.has(role));
}

function isSharedShiftUser(value: unknown): value is User & { role: "MAID" | "TECHNICIAN" } {
  return isOperationalUser(value) && (value.role === "MAID" || value.role === "TECHNICIAN");
}

export default function StaffRoleGateway() {
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(true);
  const [mode, setMode] = useState<"single_property" | "shared_auth_preview" | null>(null);
  const [tenantCode, setTenantCode] = useState("");
  const [propertyCode, setPropertyCode] = useState("");
  const submitting = useRef(false);
  const [busy, setBusy] = useState(false);
  const expireSharedSession = useCallback(() => setUser(null), []);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [telegramInitData, setTelegramInitData] = useState("");
  const [telegramNotice, setTelegramNotice] = useState<string | null>(null);

  useEffect(() => {
    window.Telegram?.WebApp?.ready();
    window.Telegram?.WebApp?.expand();
    let cancelled = false;

    async function bootstrap() {
      try {
        const response = await fetch("/core/api/v1/auth/mode", { cache: "no-store" });
        if (!response.ok) throw new Error("Authentication mode unavailable");
        const { mode: detected } = await response.json();
        if (detected !== "single_property" && detected !== "shared_auth_preview") {
          throw new Error("Unknown authentication mode");
        }
        if (cancelled) return;
        setMode(detected);
        if (detected === "shared_auth_preview") {
          const me = await fetch("/core/api/v1/auth/me", { cache: "no-store" });
          const identity = me.ok ? await me.json() : null;
          if (!cancelled && isSharedShiftUser(identity)) setUser(identity);
          if (!cancelled) setChecking(false);
          return;
        }
      } catch {
        if (!cancelled) {
          setError("Не удалось проверить режим входа. Обновите страницу.");
          setChecking(false);
        }
        return;
      }

      const initData = window.Telegram?.WebApp?.initData || "";
      if (initData) {
        setTelegramInitData(initData);
        try {
          const telegram = await fetch("/core/api/v1/auth/telegram/login", {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify({ init_data: initData }),
          });
          if (telegram.ok) {
            const payload = await telegram.json();
            if (isOperationalUser(payload)) {
              if (!cancelled) {
                setUser(payload);
                setTelegramNotice("Telegram подтверждён");
                setChecking(false);
              }
              return;
            }
          }
        } catch {
          if (!cancelled) setTelegramNotice("Telegram-вход временно недоступен");
        }
      }

      try {
        const response = await fetch("/core/api/v1/auth/me", { cache: "no-store" });
        const payload = response.ok ? await response.json() : null;
        if (!cancelled) setUser(isOperationalUser(payload) ? payload : null);
      } catch {
        if (!cancelled) setUser(null);
      } finally {
        if (!cancelled) setChecking(false);
      }
    }

    void bootstrap();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (mode !== "single_property" || !user || !HOUSEKEEPING_SYNC_ROLES.has(user.role)) return;
    void fetch("/core/api/v1/ops/housekeeping/schedule/ensure", { method: "POST" }).catch(() => undefined);
  }, [mode, user?.id, user?.role]);

  async function login(event: FormEvent) {
    event.preventDefault();
    if (!mode || submitting.current) return;
    submitting.current = true;
    setBusy(true);
    setError(null);
    const shared = mode === "shared_auth_preview";
    const selectors = { tenant_code: tenantCode.trim(), property_code: propertyCode.trim() };
    try {
      const response = await fetch("/core/api/v1/auth/login", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ username, password, ...(shared ? selectors : {}) }),
      });
      const body = await response.json().catch(() => null);
      if (!response.ok || (!shared && !isOperationalUser(body))) {
        setError("Неверный логин, пароль или роль не относится к операционной смене.");
        return;
      }
      if (shared) {
        try {
          const me = await fetch("/core/api/v1/auth/me", { cache: "no-store" });
          const identity = me.ok ? await me.json() : null;
          if (!isSharedShiftUser(body) || !isSharedShiftUser(identity) ||
              !identity.tenant_id || !identity.property_id ||
              identity.tenant_id !== body.tenant_id || identity.property_id !== body.property_id ||
              identity.property_code !== selectors.property_code ||
              identity.id !== body.id || identity.role !== body.role ||
              identity.property_code !== body.property_code) {
            throw new Error("Unverified shared session");
          }
          setUser(identity);
        } catch {
          await fetch("/core/api/v1/auth/logout", { method: "POST" }).catch(() => undefined);
          setError("Не удалось подтвердить отель или роль горничной либо техника.");
        }
        setPassword("");
        return;
      }
      setUser(body);
      setPassword("");
      if (telegramInitData) {
        const link = await fetch("/core/api/v1/auth/telegram/link", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ init_data: telegramInitData }),
        }).catch(() => null);
        if (link?.ok) setTelegramNotice("Telegram привязан. Следующий вход будет автоматическим.");
      }
    } catch {
      setError("MARINA SMART недоступен");
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }

  async function logout() {
    await fetch("/core/api/v1/auth/logout", { method: "POST" }).catch(() => undefined);
    setUser(null);
  }

  if (checking) {
    return <main className="shift-center"><div className="shift-login"><div className="shift-crown">III</div><h1>Подключаю смену…</h1><p>Проверяю рабочую сессию и Telegram.</p></div></main>;
  }

  if (!user) {
    return <main className="shift-center"><form className="shift-login" onSubmit={login}>
      <div className="shift-crown">III</div>
      <p className="shift-eyebrow">MARINA SMART · Hotel OS</p>
      <h1>Моя смена</h1>
      <p>{telegramInitData ? "Первый вход — рабочий логин и пароль. После привязки Telegram вход будет автоматическим." : "Войдите под рабочей учётной записью."}</p>
      {telegramNotice && <div className="shift-notice">{telegramNotice}</div>}
      {mode === "shared_auth_preview" && <>
        <label><span>Код организации</span><input value={tenantCode} onChange={(event) => setTenantCode(event.target.value)} required /></label>
        <label><span>Код отеля</span><input value={propertyCode} onChange={(event) => setPropertyCode(event.target.value)} required /></label>
      </>}
      <label><span>Логин</span><input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" required /></label>
      <label><span>Пароль</span><input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" minLength={6} required /></label>
      {error && <div className="shift-error">{error}</div>}
      <button className="shift-primary" disabled={!mode || busy}>Войти</button>
    </form></main>;
  }

  if (mode === "shared_auth_preview" && isSharedShiftUser(user)) {
    return <StaffShiftV2 key={user.id} sharedSession={{ user, onEnd: expireSharedSession }} />;
  }

  if (LEGACY_SHIFT_ROLES.has(user.role)) {
    return <>
      <StaffShiftV2 />
      <GuestRequestShiftPanel />
      <MarinaAiAssistant screen="MY_SHIFT" role={user.role} />
    </>;
  }

  return <>
    <main className="shift-shell">
      <header className="shift-head">
        <div>
          <p className="shift-eyebrow">MARINA SMART · Моя смена</p>
          <h1>{user.display_name}</h1>
          <span>{roleLabel[user.role]}{telegramNotice ? " · Telegram" : ""}</span>
        </div>
        <button className="shift-ghost" onClick={() => void logout()}>Выйти</button>
      </header>
      {telegramNotice && <div className="shift-notice">{telegramNotice}</div>}
      {user.role === "STORE_STAFF" && <div className="shift-empty"><strong>Смена магазина подключена к Hotel OS.</strong><span>Финансовые операции магазина будут включены только через отдельный Core-контур, без прямых записей вне учёта.</span></div>}
      {user.role === "COOK" && <div className="shift-empty"><strong>Kitchen Admin готов к работе.</strong><span>Меню, столы, заказы и новые заезды ведутся в отдельном кухонном интерфейсе.</span><a className="shift-primary" href="/kitchen">Открыть Kitchen Admin</a></div>}
      {user.role === "RECEPTION" && <div className="shift-empty"><strong>Рабочая очередь ниже обновляется автоматически.</strong><span>Берите заявку в работу и закрывайте её после фактического выполнения.</span></div>}
    </main>
    {(user.role === "RECEPTION" || user.role === "WAITER") && <GuestRequestShiftPanel />}
    <MarinaAiAssistant screen="MY_SHIFT" role={user.role} />
  </>;
}
