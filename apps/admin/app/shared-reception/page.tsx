"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import SharedReceptionCash from "./SharedReceptionCash";
import SharedBookingForm from "../shared-auth-preview/SharedBookingForm";

type Identity = {
  id: string; role: string; tenant_id: string; property_id: string;
  property_code: string; module_permissions: string[];
  display_name: string;
};
type Room = { id: string; code: string; name: string };

function isoDateAfter(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() + days);
  const part = (n: number) => String(n).padStart(2, "0");
  return date.getFullYear() + "-" + part(date.getMonth() + 1) + "-" + part(date.getDate());
}

/** P0 shared-only reception booking. The canonical API owns pricing and permission checks. */
export default function SharedReceptionBookingPage() {
  const [mode, setMode] = useState<"loading"|"ready"|"blocked">("loading");
  const [tenant, setTenant] = useState("");
  const [hotel, setHotel] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [user, setUser] = useState<Identity|null>(null);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [loadingRooms, setLoadingRooms] = useState(false);
  const [bookingRefresh, setBookingRefresh] = useState(0);
  const expire = useCallback(() => {
    setRooms([]); setUser(null); setNotice("Сеанс истёк.");
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void (async () => {
      try {
        const response = await fetch("/core/api/v1/auth/mode", {
          cache: "no-store", signal: controller.signal,
        });
        const body = await response.json();
        if (!response.ok || body.mode !== "shared_auth_preview") {
          if (!controller.signal.aborted) setMode("blocked");
          return;
        }
        if (controller.signal.aborted) return;
        setMode("ready");
        const me = await fetch("/core/api/v1/auth/me", {
          cache: "no-store", signal: controller.signal,
        });
        if (me.ok) {
          const identity = await me.json() as Identity;
          if (!controller.signal.aborted && identity.role === "RECEPTION" &&
              identity.tenant_id && identity.property_id &&
              identity.module_permissions?.includes("PMS")) setUser(identity);
        }
      } catch {
        if (!controller.signal.aborted) setMode("blocked");
      }
    })();
    return () => controller.abort();
  }, []);

  useEffect(() => {
    setRooms([]);
    if (!user) return;
    const controller = new AbortController();
    setLoadingRooms(true);
    setNotice("");
    void (async () => {
      try {
        const response = await fetch(
          "/core/api/v1/pms/grid?start=" + isoDateAfter(0) + "&end=" + isoDateAfter(14),
          { cache: "no-store", signal: controller.signal },
        );
        if (response.status === 401) {
          if (!controller.signal.aborted) setUser(null);
          return;
        }
        if (!response.ok) throw new Error("grid unavailable");
        const body = await response.json();
        if (body.property !== user.property_code || !Array.isArray(body.rooms)) {
          throw new Error("hotel scope mismatch");
        }
        if (!controller.signal.aborted) setRooms(body.rooms as Room[]);
      } catch {
        if (!controller.signal.aborted) setNotice("Номера своей гостиницы не подтверждены сервером.");
      } finally {
        if (!controller.signal.aborted) setLoadingRooms(false);
      }
    })();
    return () => controller.abort();
  }, [user]);

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (mode !== "ready" || busy) return;
    setBusy(true); setNotice(""); setRooms([]);
    try {
      const response = await fetch("/core/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tenant_code: tenant.trim(), property_code: hotel.trim(),
          username: username.trim(), password,
        }),
      });
      if (!response.ok) throw new Error("login");
      const me = await fetch("/core/api/v1/auth/me", { cache: "no-store" });
      if (!me.ok) throw new Error("session");
      const identity = await me.json() as Identity;
      if (identity.role !== "RECEPTION" || !identity.tenant_id || !identity.property_id ||
          identity.property_code !== hotel.trim() ||
          !identity.module_permissions?.includes("PMS")) {
        await fetch("/core/api/v1/auth/logout", { method: "POST" });
        throw new Error("role");
      }
      setUser(identity);
    } catch {
      setNotice("Не удалось подтвердить вход ресепшен и разрешение PMS. Проверьте коды и доступ.");
    } finally {
      setPassword(""); setBusy(false);
    }
  }

  async function logout() {
    setRooms([]); setUser(null); setBusy(true); setNotice("");
    try {
      const response = await fetch("/core/api/v1/auth/logout", { method: "POST" });
      if (!response.ok) setNotice("Не удалось подтвердить выход на сервере.");
    } catch {
      setNotice("Нет подтверждения выхода на сервере.");
    } finally { setBusy(false); }
  }

  return <main className="login-screen">
    <section className="login-card" style={{ width: "100%", maxWidth: 880 }}>
      <p className="eyebrow">MARINA SMART · общая тестовая платформа</p>
      <h1>Ресепшен · новая бронь</h1>
      <p>Бронь создаётся по обычному тарифу гостиницы. Скидки, изменение цены и HOLD недоступны.
        Отдельно можно записать только уже полученные наличные — не банковскую операцию.</p>
      <p><Link href="/shared-auth-preview">← Вернуться в рабочий кабинет</Link></p>
      {mode === "loading" && <p role="status">Проверяю режим платформы…</p>}
      {mode === "blocked" && <p role="alert">Общий режим гостиниц недоступен. Бронирование закрыто.</p>}
      {mode === "ready" && !user && <form onSubmit={login} aria-label="Вход ресепшен">
        <label>Код организации<input required minLength={3} maxLength={80}
          value={tenant} onChange={e => setTenant(e.target.value)} /></label>
        <label>Код отеля<input required minLength={3} maxLength={80}
          value={hotel} onChange={e => setHotel(e.target.value)} /></label>
        <label>Логин<input required minLength={2} maxLength={80}
          value={username} onChange={e => setUsername(e.target.value)} autoComplete="username" /></label>
        <label>Пароль<input required type="password" minLength={8} maxLength={256}
          value={password} onChange={e => setPassword(e.target.value)} autoComplete="current-password" /></label>
        <button className="btn primary" disabled={busy} type="submit">Войти как ресепшен</button>
      </form>}
      {mode === "ready" && user && <>
        <p role="status">Подтверждённый отель: <strong>{user.property_code}</strong> · {user.display_name}</p>
        {loadingRooms && <p role="status">Загружаю номера гостиницы…</p>}
        {!loadingRooms && !notice && rooms.length > 0 &&
          <SharedBookingForm key={user.property_id} coreRateOnly rooms={rooms}
            onExpired={expire} onCreated={() => setBookingRefresh(value => value + 1)} />}
        {!loadingRooms && !notice && rooms.length === 0 && <p>Нет доступного списка номеров.</p>}
        <SharedReceptionCash user={user} onExpired={expire} refreshToken={bookingRefresh}/>
        <button className="btn" type="button" disabled={busy} onClick={() => void logout()}>Выйти</button>
      </>}
      {notice && <p role="alert">{notice}</p>}
    </section>
  </main>;
}
