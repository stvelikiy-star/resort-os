"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import styles from "./DiningGuestSeatingPanel.module.css";

type User = { id: string; display_name: string; role: string };
type Stay = { stay_id: string; guest_name: string; booking_number: string; room_code?: string | null; adults: number; children: number; check_in: string; check_out: string };
type Table = { id: string; code: string; name: string; seats: number; status: string; is_active: boolean; zone_label?: string | null };
type Session = { id: string; stay_id: string; table_id: string; table_code: string; table_name: string; zone_label?: string | null; waiter_id?: string | null; waiter_name?: string | null; service_date: string; meal_type?: string | null; status: string; party_size: number; adults: number; children: number; guest_name: string; room_code?: string | null; booking_number: string; seated_at?: string | null };

const mealLabel: Record<string, string> = { BREAKFAST: "Завтрак", LUNCH: "Обед", DINNER: "Ужин", OTHER: "Другое" };

async function api(path: string, init?: RequestInit) {
  const response = await fetch(path, { cache: "no-store", ...init });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(typeof body?.detail === "string" ? body.detail : body?.detail?.code || "Ошибка Resort Core");
  return body;
}

function todayIso() {
  const now = new Date();
  const shifted = new Date(now.getTime() - now.getTimezoneOffset() * 60000);
  return shifted.toISOString().slice(0, 10);
}

function elapsed(value?: string | null) {
  if (!value) return "";
  const minutes = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 60000));
  return `${minutes} мин`;
}

export default function DiningGuestSeatingPanel() {
  const [user, setUser] = useState<User | null>(null);
  const [stays, setStays] = useState<Stay[]>([]);
  const [tables, setTables] = useState<Table[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [stayId, setStayId] = useState("");
  const [tableId, setTableId] = useState("");
  const [meal, setMeal] = useState("BREAKFAST");
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [me, staysBody, tablesBody, sessionsBody] = await Promise.all([
        api("/core/api/v1/auth/me"),
        api("/core/api/v1/dining/stays?include_future_days=3"),
        api("/core/api/v1/kitchen/tables"),
        api(`/core/api/v1/dining/sessions?service_date=${todayIso()}&status=ACTIVE`),
      ]);
      setUser(me);
      setStays(staysBody.items ?? []);
      setTables((tablesBody.items ?? []).map((item: any) => ({ ...item, zone_label: item.zone_label ?? item.zoneLabel ?? null })));
      setSessions(sessionsBody.items ?? []);
      setStayId((current) => current || staysBody.items?.[0]?.stay_id || "");
      setTableId((current) => current || tablesBody.items?.find((item: any) => item.is_active && item.status !== "OUT_OF_SERVICE")?.id || "");
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось загрузить посадку");
    }
  }, []);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    const timer = window.setInterval(() => void load(), 10000);
    return () => window.clearInterval(timer);
  }, [load]);

  const assignedStayIds = useMemo(() => new Set(sessions.map((item) => item.stay_id)), [sessions]);
  const availableStays = useMemo(() => stays.filter((item) => !assignedStayIds.has(item.stay_id)), [stays, assignedStayIds]);
  const visibleSessions = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return sessions;
    return sessions.filter((item) => [item.guest_name, item.room_code, item.table_code, item.waiter_name, item.booking_number].some((value) => String(value || "").toLowerCase().includes(q)));
  }, [sessions, query]);

  async function create(event: FormEvent) {
    event.preventDefault();
    if (!stayId || !tableId || !user) return;
    setBusy("create"); setError(null); setNotice(null);
    try {
      await api("/core/api/v1/dining/sessions", {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ stay_id: stayId, table_id: tableId, service_date: todayIso(), meal_type: meal, waiter_id: user.role === "DINING_STAFF" ? user.id : null, status: "WAITING" }),
      });
      setNotice("Гость закреплён за столом и ожидается.");
      await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Не удалось назначить стол"); }
    finally { setBusy(null); }
  }

  async function status(session: Session, next: "SEATED" | "RELEASED" | "CANCELLED") {
    setBusy(session.id); setError(null); setNotice(null);
    try {
      await api(`/core/api/v1/dining/sessions/${session.id}/status`, {
        method: "PATCH", headers: { "content-type": "application/json" }, body: JSON.stringify({ status: next }),
      });
      setNotice(next === "SEATED" ? "Гость отмечен в зале." : next === "RELEASED" ? "Стол освобождён и отправлен на уборку." : "Посадка отменена.");
      await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Не удалось изменить посадку"); }
    finally { setBusy(null); }
  }

  async function move(session: Session) {
    const candidates = tables.filter((table) => table.is_active && table.id !== session.table_id && table.status !== "OUT_OF_SERVICE" && table.seats >= session.party_size);
    if (!candidates.length) { setError("Нет подходящего стола для пересадки."); return; }
    const promptText = candidates.map((table, index) => `${index + 1}. ${table.code} · ${table.name} · ${table.seats} мест`).join("\n");
    const answer = window.prompt(`Куда пересадить ${session.guest_name}?\n${promptText}\n\nВведите номер варианта:`);
    if (!answer) return;
    const target = candidates[Number(answer) - 1];
    if (!target) { setError("Неверный номер стола."); return; }
    setBusy(session.id); setError(null); setNotice(null);
    try {
      await api(`/core/api/v1/dining/sessions/${session.id}/move`, {
        method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ target_table_id: target.id, waiter_mode: "KEEP" }),
      });
      setNotice(`Гость пересажен за стол ${target.code}. Официант сохранён.`);
      await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Не удалось пересадить гостя"); }
    finally { setBusy(null); }
  }

  return <section className={styles.shell}>
    <header className={styles.head}><div><p>Dining Floor · фиксация гостя</p><h2>Посадка и мои столы</h2><span>Гость привязывается по Stay ID. Номер комнаты используется только как подсказка.</span></div><button onClick={() => void load()}>↻</button></header>
    {error && <div className={styles.error}>{error}</div>}{notice && <div className={styles.notice}>{notice}</div>}

    <div className={styles.kpis}><article><strong>{sessions.filter((item) => item.status === "SEATED").length}</strong><span>за столами</span></article><article><strong>{sessions.filter((item) => item.status === "WAITING").length}</strong><span>ожидаются</span></article><article><strong>{sessions.filter((item) => item.waiter_id === user?.id).length}</strong><span>моих столов</span></article><article><strong>{availableStays.length}</strong><span>без стола</span></article></div>

    <form className={styles.assign} onSubmit={create}>
      <label>Гость<select value={stayId} onChange={(e) => setStayId(e.target.value)} required><option value="">Выберите гостя</option>{availableStays.map((stay) => <option key={stay.stay_id} value={stay.stay_id}>№ {stay.room_code || "—"} · {stay.guest_name} · {stay.adults}+{stay.children}</option>)}</select></label>
      <label>Стол<select value={tableId} onChange={(e) => setTableId(e.target.value)} required><option value="">Выберите стол</option>{tables.filter((table) => table.is_active && table.status !== "OUT_OF_SERVICE").map((table) => <option key={table.id} value={table.id}>{table.code} · {table.name} · {table.seats} мест · {table.status}</option>)}</select></label>
      <label>Приём<select value={meal} onChange={(e) => setMeal(e.target.value)}>{Object.entries(mealLabel).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
      <button disabled={busy === "create" || !availableStays.length}>{busy === "create" ? "Назначаю…" : "Закрепить стол"}</button>
    </form>

    <div className={styles.toolbar}><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Гость / номер / стол / официант" /><span>{visibleSessions.length} активных</span></div>
    <div className={styles.sessions}>{visibleSessions.map((session) => <article key={session.id} data-status={session.status}>
      <div className={styles.table}><small>{session.status === "SEATED" ? "ЗА СТОЛОМ" : "ОЖИДАЕТ"}</small><strong>{session.table_code}</strong><span>{session.table_name}{session.zone_label ? ` · ${session.zone_label}` : ""}</span></div>
      <div className={styles.guest}><strong>№ {session.room_code || "—"} · {session.guest_name}</strong><span>{mealLabel[session.meal_type || ""] || session.meal_type || "Без приёма"} · {session.adults}+{session.children}</span><small>{session.waiter_name ? `Официант: ${session.waiter_name}` : "Официант не назначен"}{session.status === "SEATED" && session.seated_at ? ` · ${elapsed(session.seated_at)}` : ""}</small></div>
      <div className={styles.actions}>{session.status === "WAITING" && <button disabled={busy === session.id} onClick={() => void status(session, "SEATED")}>Гость прибыл</button>}<button disabled={busy === session.id} onClick={() => void move(session)}>Пересадить</button>{session.status === "SEATED" && <button className={styles.primary} disabled={busy === session.id} onClick={() => void status(session, "RELEASED")}>Освободить</button>}</div>
    </article>)}</div>
  </section>;
}
