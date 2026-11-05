"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import SharedBookingForm from "../shared-auth-preview/SharedBookingForm";

type Identity = {
  id: string; role: string; property_id: string; tenant_id: string;
  property_code: string; module_permissions: string[]; display_name: string;
};
type Room = { id: string; code: string; name: string };

function hotelDate(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  const p = (n: number) => String(n).padStart(2, "0");
  return d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate());
}

/** Agent books only with a server-confirmed ACTIVE bookingAgentId in their hotel. */
export default function SharedAgentBookingPage() {
  const [mode, setMode] = useState<"checking"|"ready"|"blocked">("checking");
  const [tenant, setTenant] = useState("");
  const [hotel, setHotel] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [identity, setIdentity] = useState<Identity | null>(null);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [busy, setBusy] = useState(false);
  const [loadingRooms, setLoadingRooms] = useState(false);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    void (async () => {
      try {
        const response = await fetch("/core/api/v1/auth/mode", {
          cache: "no-store", signal: controller.signal,
        });
        const data = await response.json();
        if (!response.ok || data.mode !== "shared_auth_preview") {
          if (!controller.signal.aborted) setMode("blocked");
          return;
        }
        if (controller.signal.aborted) return;
        setMode("ready");
        const me = await fetch("/core/api/v1/auth/me", {
          cache: "no-store", signal: controller.signal,
        });
        if (!me.ok) return;
        const current = await me.json() as Identity;
        if (!controller.signal.aborted && current.role === "AGENT" &&
            current.property_id && current.tenant_id &&
            current.module_permissions?.includes("PMS")) setIdentity(current);
      } catch {
        if (!controller.signal.aborted) setMode("blocked");
      }
    })();
    return () => controller.abort();
  }, []);

  useEffect(() => {
    setRooms([]);
    if (!identity) return;
    const controller = new AbortController();
    setLoadingRooms(true); setNotice("");
    void (async () => {
      try {
        const response = await fetch(
          "/core/api/v1/pms/grid?start=" + hotelDate(0) + "&end=" + hotelDate(16),
          { cache: "no-store", signal: controller.signal },
        );
        if (response.status === 401) {
          if (!controller.signal.aborted) setIdentity(null);
          return;
        }
        if (response.status === 403) {
          if (!controller.signal.aborted) setNotice(
            "Агент не привязан к действующей организации гостиницы либо доступ PMS отозван."
          );
          return;
        }
        if (!response.ok) throw new Error("grid not available");
        const body = await response.json();
        if (body.property !== identity.property_code || !Array.isArray(body.rooms)) {
          throw new Error("server hotel context mismatch");
        }
        if (!controller.signal.aborted) setRooms(body.rooms as Room[]);
      } catch {
        if (!controller.signal.aborted) setNotice(
          "Список номеров своей гостиницы не подтверждён сервером. Бронирование закрыто."
        );
      } finally {
        if (!controller.signal.aborted) setLoadingRooms(false);
      }
    })();
    return () => controller.abort();
  }, [identity]);

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || mode !== "ready") return;
    setBusy(true); setRooms([]); setIdentity(null); setNotice("");
    try {
      const response = await fetch("/core/api/v1/auth/login", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tenant_code: tenant.trim(), property_code: hotel.trim(),
          username: username.trim(), password,
        }),
      });
      if (!response.ok) throw new Error("login rejected");
      const me = await fetch("/core/api/v1/auth/me", { cache: "no-store" });
      if (!me.ok) throw new Error("session not verified");
      const current = await me.json() as Identity;
      if (current.role !== "AGENT" || !current.tenant_id ||
          !current.property_id || current.property_code !== hotel.trim() ||
          !current.module_permissions?.includes("PMS")) {
        await fetch("/core/api/v1/auth/logout", { method: "POST" });
        throw new Error("not authorized agent");
      }
      setIdentity(current);
    } catch {
      setNotice("Не удалось подтвердить вход агента и его роль в выбранной гостинице.");
    } finally {
      setPassword(""); setBusy(false);
    }
  }

  async function logout() {
    setRooms([]); setIdentity(null); setBusy(true); setNotice("");
    try {
      const response = await fetch("/core/api/v1/auth/logout", { method: "POST" });
      if (!response.ok) setNotice("Выход не подтверждён сервером.");
    } catch {
      setNotice("Выход не подтверждён сервером.");
    } finally { setBusy(false); }
  }

  return <main className="login-screen">
    <section className="login-card" style={{ width: "100%", maxWidth: 880 }}>
      <p className="eyebrow">MARINA SMART · общая тестовая платформа</p>
      <h1>Агент · бронирование гостиницы</h1>
      <p>Доступ только для агента, привязанного к действующей организации
        выбранного отеля. Цена рассчитывается сервером. Скидки, HOLD и ручная цена запрещены.</p>
      <p><Link href="/shared-auth-preview">← Рабочий кабинет</Link></p>
      {mode === "checking" && <p role="status">Проверяю режим платформы…</p>}
      {mode === "blocked" && <p role="alert">Общий режим бронирования недоступен.</p>}
      {mode === "ready" && !identity && <form onSubmit={login} aria-label="Вход агента">
        <label>Код организации<input required minLength={3} maxLength={80}
          value={tenant} onChange={e => setTenant(e.target.value)}/></label>
        <label>Код отеля<input required minLength={3} maxLength={80}
          value={hotel} onChange={e => setHotel(e.target.value)}/></label>
        <label>Логин<input required minLength={2} maxLength={80} autoComplete="username"
          value={username} onChange={e => setUsername(e.target.value)}/></label>
        <label>Пароль<input required type="password" minLength={8} maxLength={256}
          autoComplete="current-password" value={password}
          onChange={e => setPassword(e.target.value)}/></label>
        <button className="btn primary" type="submit" disabled={busy}>Войти как агент</button>
      </form>}
      {mode === "ready" && identity && <>
        <p role="status">Гостиница: <strong>{identity.property_code}</strong> · {identity.display_name}</p>
        {loadingRooms && <p role="status">Проверяю привязку и номера…</p>}
        {!loadingRooms && rooms.length > 0 && !notice &&
          <SharedBookingForm key={identity.property_id} coreRateOnly rooms={rooms}
            onExpired={() => { setRooms([]); setIdentity(null); setNotice("Сеанс истёк."); }}/>}
        {!loadingRooms && !notice && !rooms.length &&
          <p>Нет подтверждённых номеров для бронирования.</p>}
        <button className="btn" type="button" disabled={busy} onClick={() => void logout()}>Выйти</button>
      </>}
      {notice && <p role="alert">{notice}</p>}
    </section>
  </main>;
}
