"use client";

import { FormEvent, useEffect, useState } from "react";
import PMSGrid from "./PMSGrid";

type User = {
  id: string;
  username: string;
  display_name: string;
  role: string;
  property_code: string;
};

export default function AdminShell() {
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(true);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetch("/core/api/v1/auth/me", { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) return null;
        return (await response.json()) as User;
      })
      .then(setUser)
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
          <p className="login-copy">Шахматка, бронирования и операционные данные доступны только сотрудникам.</p>
          <label><span>Логин</span><input autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} minLength={2} required autoFocus /></label>
          <label><span>Пароль</span><input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} minLength={8} required /></label>
          {error && <div className="login-error">{error}</div>}
          <button className="btn primary login-button" disabled={submitting}>{submitting ? "Входим…" : "Войти"}</button>
        </form>
      </main>
    );
  }

  return (
    <>
      <div className="auth-toolbar"><span><b>{user.display_name}</b> · {user.role}</span><button onClick={logout}>Выйти</button></div>
      <PMSGrid />
    </>
  );
}
