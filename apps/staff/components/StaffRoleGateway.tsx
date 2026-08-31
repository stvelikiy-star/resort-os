"use client";

import { FormEvent, useEffect, useState } from "react";

import GuestRequestShiftPanel from "./GuestRequestShiftPanel";
import StaffShiftV2 from "./StaffShiftV2";

type Role = "OWNER" | "MANAGER" | "RECEPTION" | "MAID" | "TECHNICIAN" | "DINING_STAFF" | "STORE_STAFF";
type User = { id: string; username: string; display_name: string; role: Role; property_code: string };

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

const OPERATIONAL_ROLES = new Set<Role>(["OWNER", "MANAGER", "RECEPTION", "MAID", "TECHNICIAN", "DINING_STAFF", "STORE_STAFF"]);
const LEGACY_SHIFT_ROLES = new Set<Role>(["OWNER", "MANAGER", "MAID", "TECHNICIAN"]);
const roleLabel: Record<Role, string> = {
  OWNER: "Владелец",
  MANAGER: "Менеджер",
  RECEPTION: "Ресепшен",
  MAID: "Горничная",
  TECHNICIAN: "Техник",
  DINING_STAFF: "Питание",
  STORE_STAFF: "Магазин",
};

function isOperationalUser(value: unknown): value is User {
  if (!value || typeof value !== "object") return false;
  const role = (value as { role?: Role }).role;
  return Boolean(role && OPERATIONAL_ROLES.has(role));
}

export default function StaffRoleGateway() {
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(true);
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

  async function login(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const response = await fetch("/core/api/v1/auth/login", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const body = await response.json().catch(() => null);
      if (!response.ok || !isOperationalUser(body)) {
        setError("Неверный логин, пароль или роль не относится к операционной смене.");
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
      setError("Resort Core недоступен");
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
      <p className="shift-eyebrow">Три Короны · Resort OS</p>
      <h1>Моя смена</h1>
      <p>{telegramInitData ? "Первый вход — рабочий логин и пароль. После привязки Telegram вход будет автоматическим." : "Войдите под рабочей учётной записью."}</p>
      {telegramNotice && <div className="shift-notice">{telegramNotice}</div>}
      <label><span>Логин</span><input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" required /></label>
      <label><span>Пароль</span><input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" minLength={8} required /></label>
      {error && <div className="shift-error">{error}</div>}
      <button className="shift-primary">Войти</button>
    </form></main>;
  }

  if (LEGACY_SHIFT_ROLES.has(user.role)) {
    return <>
      <StaffShiftV2 />
      <GuestRequestShiftPanel />
    </>;
  }

  return <>
    <main className="shift-shell">
      <header className="shift-head">
        <div>
          <p className="shift-eyebrow">Три Короны · Моя смена</p>
          <h1>{user.display_name}</h1>
          <span>{roleLabel[user.role]}{telegramNotice ? " · Telegram" : ""}</span>
        </div>
        <button className="shift-ghost" onClick={() => void logout()}>Выйти</button>
      </header>
      {telegramNotice && <div className="shift-notice">{telegramNotice}</div>}
      {user.role === "STORE_STAFF" && <div className="shift-empty"><strong>Смена магазина подключена к Resort OS.</strong><span>Финансовые операции магазина будут включены только через отдельный Core-контур, без прямых записей вне учёта.</span></div>}
      {(user.role === "RECEPTION" || user.role === "DINING_STAFF") && <div className="shift-empty"><strong>Рабочая очередь ниже обновляется автоматически.</strong><span>Берите заявку в работу и закрывайте её после фактического выполнения.</span></div>}
    </main>
    {(user.role === "RECEPTION" || user.role === "DINING_STAFF") && <GuestRequestShiftPanel />}
  </>;
}
