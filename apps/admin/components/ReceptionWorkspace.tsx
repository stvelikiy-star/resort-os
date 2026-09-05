"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import ReceptionBoard from "./ReceptionBoard";

type Arrival = {
  id: string;
  bookingNumber: string;
  status: string;
  checkIn: string;
  firstName?: string | null;
  room_code?: string | null;
  room_state?: string | null;
};

type ApiResponse = { local_date?: string; items?: Arrival[] };

type HandoffResult = {
  status: string;
  room_code?: string;
  room_state?: string;
  task_id?: string | null;
  task_status?: string;
};

const stateLabel: Record<string, string> = {
  CLEAN: "Готов",
  DIRTY: "Нужна уборка",
  IN_INSPECTION: "На проверке",
  TECH_BLOCK: "Ремонт",
  UNKNOWN: "Статус не указан",
};

function addDays(iso: string, days: number) {
  const [year, month, day] = iso.split("-").map(Number);
  const value = new Date(year, month - 1, day + days);
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
}

export default function ReceptionWorkspace({ userRole, onNavigate }: { userRole: string; onNavigate: (tab: string) => void }) {
  const [items, setItems] = useState<Arrival[]>([]);
  const [localDate, setLocalDate] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, HandoffResult>>({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch("/core/api/v1/admin/reception/reservations?limit=500", { cache: "no-store" });
      const body = await response.json().catch(() => ({})) as ApiResponse & { detail?: unknown };
      if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Не удалось проверить готовность заездов");
      setItems(body.items ?? []);
      setLocalDate(body.local_date ?? "");
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось проверить готовность заездов");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const attention = useMemo(() => {
    if (!localDate) return [];
    const horizon = addDays(localDate, 2);
    return items
      .filter((item) => item.status === "GUARANTEED" && item.checkIn >= localDate && item.checkIn <= horizon && item.room_state !== "CLEAN")
      .sort((left, right) => left.checkIn.localeCompare(right.checkIn) || (left.room_code || "").localeCompare(right.room_code || ""));
  }, [items, localDate]);

  async function sendHousekeeping(item: Arrival) {
    if (busy) return;
    setBusy(item.id);
    setError(null);
    try {
      const response = await fetch(`/core/api/v1/admin/reception/reservations/${item.id}/housekeeping-request`, { method: "POST" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = body?.detail;
        const message = typeof detail === "string" ? detail : detail?.message || "Не удалось передать номер на подготовку";
        throw new Error(message);
      }
      setResults((current) => ({ ...current, [item.id]: body as HandoffResult }));
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось передать номер на подготовку");
    } finally {
      setBusy(null);
    }
  }

  const isManager = userRole === "OWNER" || userRole === "MANAGER";

  return <>
    <section className="reception-readiness" aria-label="Готовность ближайших заездов">
      <div className="reception-readiness-head">
        <div><p className="eyebrow">До заселения · контроль готовности</p><h2>Ближайшие заезды без статуса «Готов»</h2><span>Показываем сегодня + 2 дня. Core по-прежнему не разрешит заезд, пока номер не CLEAN.</span></div>
        <div className="reception-readiness-actions"><strong>{loading ? "…" : attention.length}</strong>{isManager && <button className="btn" onClick={() => onNavigate("OPS")}>Уборка / ремонт</button>}<button className="btn" onClick={() => void load()}>Обновить</button></div>
      </div>
      {error && <div className="error-box compact">{error}</div>}
      {!loading && attention.length === 0 && <div className="reception-readiness-ok"><b>Готовность без критичных сигналов</b><span>На ближайшие два дня нет гарантированных заездов с неподготовленным назначенным номером.</span></div>}
      {attention.length > 0 && <div className="reception-readiness-list">{attention.map((item) => {
        const state = item.room_state || "UNKNOWN";
        const result = results[item.id];
        const canSend = Boolean(item.room_code) && (state === "DIRTY" || state === "UNKNOWN");
        return <article key={item.id} data-state={state}>
          <div><small>{item.checkIn === localDate ? "ЗАЕЗД СЕГОДНЯ" : `ЗАЕЗД ${item.checkIn}`}</small><strong>{item.firstName || "Гость"} · {item.bookingNumber}</strong></div>
          <div><span>Номер</span><b>{item.room_code || "Не назначен"}</b></div>
          <div><span>Готовность</span><b>{stateLabel[state] || state}</b></div>
          <div className="reception-readiness-cta">
            {canSend && <button disabled={busy === item.id || result?.status === "CREATED" || result?.status === "EXISTING_TASK"} onClick={() => void sendHousekeeping(item)}>{busy === item.id ? "Передаю…" : result ? "Передано в уборку" : "Передать в уборку"}</button>}
            {state === "IN_INSPECTION" && <span>Горничная закончила · ждём проверку</span>}
            {state === "TECH_BLOCK" && (isManager ? <button onClick={() => onNavigate("OPS")}>Открыть ремонт</button> : <span>Нужен менеджер: номер в ремонте</span>)}
            {!item.room_code && <span>Сначала назначьте номер в шахматке</span>}
          </div>
        </article>;
      })}</div>}
    </section>
    <ReceptionBoard />
  </>;
}
