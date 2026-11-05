"use client";

import { useEffect, useState } from "react";
import WhatsAppWorkspace from "../../components/WhatsAppWorkspace";

type VerifiedIdentity = {
  id: string;
  role: string;
  property_code: string;
  property_id: string | null;
  tenant_id: string | null;
};

type State = "loading" | "ready" | "login" | "forbidden" | "unavailable";

const ADMITTED_ROLES = new Set(["OWNER", "MANAGER", "RECEPTION"]);

export default function SharedWhatsAppPage() {
  const [identity, setIdentity] = useState<VerifiedIdentity | null>(null);
  const [state, setState] = useState<State>("loading");

  useEffect(() => {
    let mounted = true;
    let checkNumber = 0;

    async function verifyCurrentHotel() {
      const number = ++checkNumber;
      try {
        const modeResponse = await fetch("/core/api/v1/auth/mode", {
          credentials: "same-origin", cache: "no-store",
        });
        if (!modeResponse.ok) throw new Error("Mode unavailable");
        const mode = await modeResponse.json() as { mode?: string };
        if (mode.mode !== "shared_auth_preview") {
          if (mounted && number === checkNumber) {
            setIdentity(null);
            setState("unavailable");
          }
          return;
        }
        const response = await fetch("/core/api/v1/auth/me", {
          credentials: "same-origin", cache: "no-store",
        });
        if (mounted && number === checkNumber && response.status === 401) {
          setIdentity(null);
          setState("login");
          return;
        }
        if (!response.ok) throw new Error("Identity unavailable");
        const user = await response.json() as VerifiedIdentity;
        if (!user.property_id || !user.tenant_id || !user.property_code) {
          throw new Error("Unbound hotel");
        }
        if (mounted && number === checkNumber) {
          if (!ADMITTED_ROLES.has(user.role)) {
            setIdentity(null);
            setState("forbidden");
          } else {
            // The per-property React key below unmounts ALL previous hotel's
            // contact names, message previews, notes and AI draft state.
            setIdentity(user);
            setState("ready");
          }
        }
      } catch {
        if (mounted && number === checkNumber) {
          setIdentity(null);
          setState("unavailable");
        }
      }
    }

    void verifyCurrentHotel();
    window.addEventListener("focus", verifyCurrentHotel);
    const interval = window.setInterval(() => void verifyCurrentHotel(), 10_000);
    const visibility = () => {
      if (document.visibilityState === "visible") void verifyCurrentHotel();
    };
    document.addEventListener("visibilitychange", visibility);
    return () => {
      mounted = false;
      checkNumber++;
      window.clearInterval(interval);
      window.removeEventListener("focus", verifyCurrentHotel);
      document.removeEventListener("visibilitychange", visibility);
    };
  }, []);

  return <div style={{ maxWidth: 1500, margin: "0 auto", padding: "16px" }}>
    <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 20, flexWrap: "wrap", marginBottom: 22 }}>
      <div>
        <strong style={{ letterSpacing: "0.08em" }}>MARINA SMART</strong>
        <p style={{ margin: "6px 0 0", opacity: 0.75 }}>Общий рабочий кабинет WhatsApp</p>
      </div>
      <a href="/shared-auth-preview" style={{ textDecoration: "underline" }}>Общая платформа PMS</a>
    </header>
    {state === "loading" && <p role="status">Проверяем гостиницу и права доступа…</p>}
    {state === "login" && <section role="status">
      <h1>Нужен вход в гостиницу</h1>
      <p>Авторизуйтесь с выбором организации и гостиницы в общей MARINA SMART.</p>
      <a href="/shared-auth-preview">Перейти к входу</a>
    </section>}
    {state === "forbidden" && <section role="alert">
      <h1>Недостаточно прав</h1>
      <p>WhatsApp доступен только собственнику, менеджеру и ресепшену своей гостиницы.</p>
    </section>}
    {state === "unavailable" && <section role="alert">
      <h1>Общая платформа недоступна</h1>
      <p>Без подтверждённого серверного гостиничного сеанса переписки не отображаются.</p>
      <a href="/shared-auth-preview">Открыть общий вход</a>
    </section>}
    {state === "ready" && identity && <section aria-label="WhatsApp своей гостиницы">
      <p role="status" style={{ margin: "0 0 16px", fontWeight: 600 }}>
        Гостиница: {identity.property_code} · Роль: {identity.role}
      </p>
      <WhatsAppWorkspace
        key={identity.tenant_id + ":" + identity.property_id + ":" + identity.role}
        role={identity.role}
        onNavigate={() => window.location.assign("/shared-auth-preview")}
      />
    </section>}
  </div>;
}
