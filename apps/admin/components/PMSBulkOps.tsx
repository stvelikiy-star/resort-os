"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type Room = {
  id: string;
  code: string;
  room_type_name: string;
  building_or_zone: string | null;
  floor: string | null;
  operational_state: "UNKNOWN" | "CLEAN" | "DIRTY" | "IN_INSPECTION" | "TECH_BLOCK";
};

type GridResponse = { rooms: Room[] };

type Task = {
  id: string;
  type: "HOUSEKEEPING" | "MAINTENANCE" | "GUEST_REQUEST";
  status: "OPEN" | "IN_PROGRESS" | "IN_INSPECTION" | "DONE" | "CANCELLED";
  room_id: string | null;
  room_code: string | null;
  priority: string;
  title: string;
};

type Candidate = { room: Room; type: "HOUSEKEEPING" | "MAINTENANCE"; priority: "NORMAL" | "HIGH"; reason: string };

function localDate(value: Date) {
  const y = value.getFullYear();
  const m = String(value.getMonth() + 1).padStart(2, "0");
  const d = String(value.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function tomorrow() {
  const next = new Date();
  next.setDate(next.getDate() + 1);
  return localDate(next);
}

const ACTIVE_TASKS = new Set(["OPEN", "IN_PROGRESS", "IN_INSPECTION"]);

export default function PMSBulkOps() {
  const [rooms, setRooms] = useState<Room[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [complete, setComplete] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const query = new URLSearchParams({ start: localDate(new Date()), end: tomorrow() });
      const [gridResponse, housekeepingResponse, maintenanceResponse] = await Promise.all([
        fetch(`/core/api/v1/pms/grid?${query}`, { cache: "no-store" }),
        fetch("/core/api/v1/ops/tasks?type=HOUSEKEEPING&limit=300", { cache: "no-store" }),
        fetch("/core/api/v1/ops/tasks?type=MAINTENANCE&limit=300", { cache: "no-store" }),
      ]);
      const gridBody = await gridResponse.json().catch(() => ({}));
      const housekeepingBody = await housekeepingResponse.json().catch(() => ({}));
      const maintenanceBody = await maintenanceResponse.json().catch(() => ({}));
      if (!gridResponse.ok) throw new Error(typeof gridBody.detail === "string" ? gridBody.detail : "Не удалось получить номерной фонд");
      if (!housekeepingResponse.ok || !maintenanceResponse.ok || !Array.isArray(housekeepingBody.items) || !Array.isArray(maintenanceBody.items)) {
        throw new Error("Не удалось подтвердить полноту операционных задач");
      }
      const hk = housekeepingBody.items as Task[];
      const mt = maintenanceBody.items as Task[];
      setRooms((gridBody as GridResponse).rooms || []);
      setTasks([...hk, ...mt]);
      setComplete(hk.length < 300 && mt.length < 300);
      setSelected(new Set());
    } catch (cause) {
      setRooms([]);
      setTasks([]);
      setComplete(false);
      setError(cause instanceof Error ? cause.message : "Ошибка загрузки массовых операций");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const activeByRoom = useMemo(() => {
    const map = new Map<string, Set<string>>();
    tasks.forEach((task) => {
      if (!task.room_id || !ACTIVE_TASKS.has(task.status)) return;
      const set = map.get(task.room_id) || new Set<string>();
      set.add(task.type);
      map.set(task.room_id, set);
    });
    return map;
  }, [tasks]);

  const candidates = useMemo<Candidate[]>(() => rooms.flatMap((room) => {
    const active = activeByRoom.get(room.id) || new Set<string>();
    if (room.operational_state === "DIRTY" && !active.has("HOUSEKEEPING")) {
      return [{ room, type: "HOUSEKEEPING", priority: "NORMAL", reason: "DIRTY без активной housekeeping-задачи" }];
    }
    if (room.operational_state === "TECH_BLOCK" && !active.has("MAINTENANCE")) {
      return [{ room, type: "MAINTENANCE", priority: "HIGH", reason: "TECH_BLOCK без активного maintenance-ticket" }];
    }
    return [];
  }).sort((a, b) => a.type === b.type ? a.room.code.localeCompare(b.room.code, "ru") : a.type === "MAINTENANCE" ? -1 : 1), [rooms, activeByRoom]);

  function toggle(id: string) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  function selectAll() {
    setSelected(new Set(candidates.map((candidate) => candidate.room.id)));
  }

  async function createTasks() {
    if (!complete || selected.size === 0 || busy) return;
    const chosen = candidates.filter((candidate) => selected.has(candidate.room.id));
    const housekeeping = chosen.filter((item) => item.type === "HOUSEKEEPING").length;
    const maintenance = chosen.filter((item) => item.type === "MAINTENANCE").length;
    const confirmed = window.confirm(`Создать ${chosen.length} задач в Resort Core?\nУборка: ${housekeeping}\nРемонт: ${maintenance}\n\nКаждая задача попадёт в audit log. Существующие активные задачи не дублируются.`);
    if (!confirmed) return;

    setBusy(true);
    setError(null);
    setResult(null);
    let created = 0;
    const failures: string[] = [];
    for (const candidate of chosen) {
      try {
        const response = await fetch("/core/api/v1/ops/tasks", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            type: candidate.type,
            room_id: candidate.room.id,
            priority: candidate.priority,
            title: candidate.type === "HOUSEKEEPING" ? `Уборка номера № ${candidate.room.code}` : `Проверить технический блок № ${candidate.room.code}`,
            description: candidate.reason,
            source: "PMS_BULK_COMMAND",
          }),
        });
        const body = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : `HTTP ${response.status}`);
        created += 1;
      } catch (cause) {
        failures.push(`№ ${candidate.room.code}: ${cause instanceof Error ? cause.message : "ошибка"}`);
      }
    }
    setResult(`Создано задач: ${created}${failures.length ? ` · Ошибок: ${failures.length}` : ""}`);
    if (failures.length) setError(failures.slice(0, 5).join(" · "));
    setBusy(false);
    await load();
  }

  return <section className="v5-bulk-ops">
    <header className="v5-bulk-head">
      <div><p className="eyebrow">Operations guard · V5</p><h3>Массовые действия</h3><span>Только недостающие задачи: система сначала сверяет живой статус номера и активные tasks Resort Core.</span></div>
      <button className="btn" onClick={() => void load()} disabled={busy}>↻ Пересчитать</button>
    </header>

    {!complete && !loading && <div className="v5-guard-warning"><strong>Bulk-write заблокирован</strong><span>{error || "Task endpoint достиг лимита 300 или не подтвердил полноту. Пока список нельзя доказать полным, массовое создание отключено."}</span></div>}
    {result && <div className="v5-bulk-result">{result}</div>}
    {error && complete && <div className="v5-bulk-error">{error}</div>}

    <div className="v5-bulk-summary">
      <article><span>Найдено без задачи</span><strong>{loading ? "…" : candidates.length}</strong></article>
      <article><span>Уборка</span><strong>{loading ? "…" : candidates.filter((item) => item.type === "HOUSEKEEPING").length}</strong></article>
      <article><span>Ремонт</span><strong>{loading ? "…" : candidates.filter((item) => item.type === "MAINTENANCE").length}</strong></article>
      <article><span>Выбрано</span><strong>{selected.size}</strong></article>
    </div>

    <div className="v5-bulk-toolbar"><div><button onClick={selectAll} disabled={!complete || candidates.length === 0}>Выбрать всё</button><button onClick={() => setSelected(new Set())} disabled={selected.size === 0}>Снять выбор</button></div><button className="v5-create-tasks" onClick={() => void createTasks()} disabled={!complete || selected.size === 0 || busy}>{busy ? "Создаю…" : `Создать задачи (${selected.size})`}</button></div>

    <div className="v5-candidate-list">{loading ? <div className="loading">Сверяю номера и активные задачи…</div> : candidates.length === 0 ? <div className="v5-all-good"><strong>Очередь чистая</strong><span>Для DIRTY/TECH_BLOCK уже существуют активные операционные задачи либо таких номеров нет.</span></div> : candidates.map((candidate) => <label key={candidate.room.id} className={selected.has(candidate.room.id) ? "is-selected" : ""}><input type="checkbox" checked={selected.has(candidate.room.id)} onChange={() => toggle(candidate.room.id)} disabled={!complete || busy} /><span className={`v5-kind kind-${candidate.type.toLowerCase()}`}>{candidate.type === "HOUSEKEEPING" ? "Уборка" : "Ремонт"}</span><div><strong>№ {candidate.room.code}</strong><span>{candidate.room.room_type_name}</span><small>{[candidate.room.building_or_zone, candidate.room.floor].filter(Boolean).join(" · ") || "—"}</small></div><em>{candidate.reason}</em></label>)}</div>
  </section>;
}
