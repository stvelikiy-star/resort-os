"use client";

import { FormEvent, useEffect, useState } from "react";

type Identity = { display_name: string; role: string; property_code: string; property_id: string; tenant_id: string };

export default function SharedAuthPreview() {
  const [mode, setMode] = useState<"loading" | "ready" | "unavailable">("loading");
  const [tenant, setTenant] = useState("");
  const [property, setProperty] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [identity, setIdentity] = useState<Identity | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

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
          const user = await me.json();
          if (user.property_id && user.tenant_id) setIdentity(user);
        }
      } catch {
        if (!controller.signal.aborted) setMode("unavailable");
      }
    })();
    return () => controller.abort();
  }, []);

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
      const user = await me.json();
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

  return <main className="login-screen"><section className="login-card" aria-labelledby="shared-auth-title">
    <p className="eyebrow">MARINA SMART · Тестовый контур</p>
    <h1 id="shared-auth-title">Общий вход</h1>
    {mode === "loading" && <p role="status">Проверяю доступность входа…</p>}
    {mode === "unavailable" && <p role="status">Этот вход доступен только в отдельном тестовом контуре общей платформы.</p>}
    {mode === "ready" && !identity && <form onSubmit={login}>
      <p>Используйте выданные вам коды и учётную запись.</p>
      <label>Код организации<input required minLength={3} maxLength={80} value={tenant} onChange={e => setTenant(e.target.value)} autoCapitalize="none" spellCheck={false} /></label>
      <label>Код отеля<input required minLength={3} maxLength={80} value={property} onChange={e => setProperty(e.target.value)} spellCheck={false} /></label>
      <label>Логин<input required minLength={2} maxLength={80} value={username} onChange={e => setUsername(e.target.value)} autoComplete="username" /></label>
      <label>Пароль<input required type="password" minLength={8} maxLength={256} value={password} onChange={e => setPassword(e.target.value)} autoComplete="current-password" /></label>
      <button className="btn primary login-button" disabled={pending}>{pending ? "Проверяю…" : "Войти"}</button>
    </form>}
    {identity && <div>
      <p role="status">Вход подтверждён: {identity.display_name} · {identity.property_code} · {identity.role}</p>
      <p>Сейчас доступна проверка входа. Рабочие разделы подключаются после проверки изоляции отелей.</p>
      <button className="btn" onClick={() => void logout()} disabled={pending}>Выйти</button>
    </div>}
    {error && <p role="alert" className="login-error">{error}</p>}
  </section></main>;
}
