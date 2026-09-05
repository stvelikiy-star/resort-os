"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type RoomItem = {
  id: string;
  code: string;
  name: string;
  state: "UNKNOWN" | "CLEAN" | "DIRTY" | "IN_INSPECTION" | "TECH_BLOCK";
  room_type_name: string;
  building_or_zone?: string | null;
  floor?: string | null;
};

type TaskItem = {
  id: string;
  type: "HOUSEKEEPING" | "MAINTENANCE" | "GUEST_REQUEST";
  status: string;
  room_id?: string | null;
};

type Snapshot = { complete: boolean; rooms: RoomItem[]; tasks: TaskItem[] };
type Candidate = { room: RoomItem; type: "HOUSEKEEPING" | "MAINTENANCE" };

function dateOnly(value = new Date()) {
  const y = value.getFullYear();
  const m = String(value.getMonth() + 1).padStart(2, "0");
  const d = String(value.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function addDays(value: Date, amount: number) {
  const next = new Date(value.getFullYear(), value.getMonth(), value.getDate());
  next.setDate(next.getDate() + amount);
  return next;
}

export default function PMSBulkGuardV9() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const params = new URLSearchParams({ start: dateOnly(), end: dateOnly(addDays(new Date(), 31)) });
      const response = await fetch(`/core/api/v1/admin/pms/control-snapshot?${params}`, { cache: "no-store" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok || !body.complete || !Array.isArray(body.rooms) || !Array.isArray(body.tasks)) throw new Error("Не удалось получить полный operational snapshot");
      setSnapshot(body as Snapshot);
    } catch (cause) {
      setSnapshot(null);
      setError(cause instanceof Error ? cause.message : "Operational snapshot недоступен");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const candidates = useMemo<Candidate[]>(() => {
    if (!snapshot) return [];
    const active = new Set(snapshot.tasks.filter((task) => task.room_id).map((task) => `${task.room_id}:${task.type}`));
    const out: Candidate[] = [];
    snapshot.rooms.forEach((room) => {
      if (room.state === "DIRTY" && !active.has(`${room.id}:HOUSEKEEPING`)) out.push({ room, type: "HOUSEKEEPING" });
      if (room.state === "TECH_BLOCK" && !active.has(`${room.id}:MAINTENANCE`)) out.push({ room, type: "MAINTENANCE" });
    });
    return out;
  }, [snapshot]);

  useEffect(() => {
    setSelected((current) => {
      const valid = new Set(candidates.map((item) => `${item.room.id}:${item.type}`));
      return new Set([...current].filter((key) => valid.has(key)));
    });
  }, [candidates]);

  function toggle(key: string) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key); else next.add(key);
      return next;
    });
  }

  async function createTasks() {
    const chosen = candidates.filter((item) => selected.has(`${item.room.id}:${item.type}`));
    if (!chosen.length) return;
    if (!window.confirm(`Создать ${chosen.length} недостающих задач? Resort Core повторно проверит активные задачи и заблокирует дубли.`)) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const response = await fetch("/core/api/v1/admin/pms/tasks/bulk-create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source: "PMS_V9_BULK",
          items: chosen.map((item) => ({
            room_id: item.room.id,
            type: item.type,
            priority: item.type === "MAINTENANCE" ? "HIGH" : "NORMAL",
            title: item.type === "MAINTENANCE" ? `Ремонт · № ${item.room.code}` : `Уборка · № ${item.room.code}`,
            description: "Создано из V9 после сверки room state с полным active-task snapshot.",
          })),
        }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        const message = typeof body.detail === "string" ? body.detail : body?.detail?.message || `Bulk HTTP ${response.status}`;
        throw new Error(message);
      }
      setResult(`Создано: ${body.created_count || 0}. Уже существовало: ${body.skipped_count || 0}.`);
      setSelected(new Set());
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось создать задачи");
    } finally {
      setBusy(false);
    }
  }

  const housekeeping = candidates.filter((item) => item.type === "HOUSEKEEPING").length;
  const maintenance = candidates.filter((item) => item.type === "MAINTENANCE").length;

  return <section className="v9-bulk">
    <header className="v9-bulk-head">
      <div><p className="eyebrow">Operations Guard · V9</p><h3>Недостающие задачи фонда</h3><span>Показываем только DIRTY без active HOUSEKEEPING и TECH_BLOCK без active MAINTENANCE. Перед записью Core снова блокирует комнаты и проверяет дубли.</span></div>
      <div className="v9-bulk-actions"><button className="btn" onClick={() => void load()} disabled={loading}>↻ Пересчитать</button><button className="btn primary" disabled={busy || selected.size === 0} onClick={() => void createTasks()}>{busy ? "Создаю…" : `Создать выбранные · ${selected.size}`}</button></div>
    </header>
    {error && <div className="v9-bulk-error">{error}</div>}{result && <div className="v9-bulk-result">{result}</div>}
    <div className="v9-bulk-kpis"><div><span>Без задачи</span><strong>{loading ? "…" : candidates.length}</strong></div><div><span>Уборка</span><strong>{housekeeping}</strong></div><div><span>Ремонт</span><strong>{maintenance}</strong></div><div><span>Выбрано</span><strong>{selected.size}</strong></div></div>
    <div className="v9-bulk-toolbar"><button onClick={() => setSelected(new Set(candidates.map((item) => `${item.room.id}:${item.type}`)))}>Выбрать всё</button><button onClick={() => setSelected(new Set())}>Снять выбор</button><span>DB invariant: максимум одна активная HOUSEKEEPING и одна MAINTENANCE на комнату.</span></div>
    <div className="v9-bulk-list">{candidates.slice(0, 40).map((item) => {
      const key = `${item.room.id}:${item.type}`;
      return <label key={key} className={selected.has(key) ? "selected" : ""}><input type="checkbox" checked={selected.has(key)} onChange={() => toggle(key)} /><b className={item.type === "HOUSEKEEPING" ? "hk" : "tech"}>{item.type === "HOUSEKEEPING" ? "Уборка" : "Ремонт"}</b><div><strong>№ {item.room.code}</strong><span>{item.room.room_type_name} · {[item.room.building_or_zone, item.room.floor].filter(Boolean).join(" · ") || "—"}</span></div><small>{item.type === "HOUSEKEEPING" ? "DIRTY без active task" : "TECH_BLOCK без active task"}</small></label>;
    })}{!loading && candidates.length === 0 && <p>Все DIRTY/TECH_BLOCK номера уже имеют соответствующие активные задачи.</p>}</div>
  </section>;
}
