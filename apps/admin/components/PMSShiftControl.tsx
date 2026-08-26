"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type Task = {
  id: string;
  type: "HOUSEKEEPING" | "MAINTENANCE" | "GUEST_REQUEST";
  status: string;
  priority: string;
  title: string;
  room_code?: string | null;
  assigned_to_name?: string | null;
  created_at: string;
};

type Reservation = {
  id: string;
  bookingNumber: string;
  status: string;
  checkIn: string;
  checkOut: string;
  totalKgs: number;
  paidKgs: number;
  remainingKgs: number;
  firstName?: string | null;
  room_code?: string | null;
  room_state?: string | null;
};

type Room = {
  id: string;
  code: string;
  operational_state: "UNKNOWN" | "CLEAN" | "DIRTY" | "IN_INSPECTION" | "TECH_BLOCK";
};

type User = { id: string; display_name: string; role: string };
type Thresholds = { HOUSEKEEPING: number; MAINTENANCE: number; GUEST_REQUEST: number };
type Snapshot = {
  id: string;
  createdAt: string;
  user: string;
  note: string;
  activeTaskIds: string[];
  metrics: {
    arrivals: number;
    departures: number;
    activeTasks: number;
    escalations: number;
    dirty: number;
    inspection: number;
    tech: number;
    debtKgs: number | null;
  };
};

const DEFAULT_THRESHOLDS: Thresholds = { HOUSEKEEPING: 45, MAINTENANCE: 120, GUEST_REQUEST: 30 };
const TYPE_LABEL: Record<Task["type"], string> = { HOUSEKEEPING: "Уборка", MAINTENANCE: "Ремонт", GUEST_REQUEST: "Запрос гостя" };
const PRIORITY_WEIGHT: Record<string, number> = { URGENT: 4, HIGH: 3, NORMAL: 2, LOW: 1 };
const ACTIVE_STATUSES = new Set(["OPEN", "IN_PROGRESS", "IN_INSPECTION"]);

function localDate(value = new Date()) {
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

function ageMinutes(value: string) {
  const created = new Date(value).getTime();
  if (!Number.isFinite(created)) return 0;
  return Math.max(0, Math.round((Date.now() - created) / 60000));
}

function ageLabel(minutes: number) {
  if (minutes < 60) return `${minutes} мин`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest ? `${hours} ч ${rest} мин` : `${hours} ч`;
}

function money(value: number) {
  return new Intl.NumberFormat("ru-RU").format(value);
}

function safeFileName(value: string) {
  return value.replace(/[^a-zA-Z0-9а-яА-ЯёЁ_-]+/g, "-").replace(/-+/g, "-");
}

export default function PMSShiftControl() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tasksComplete, setTasksComplete] = useState(true);
  const [financeComplete, setFinanceComplete] = useState(true);
  const [thresholds, setThresholds] = useState<Thresholds>(DEFAULT_THRESHOLDS);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [handoverNote, setHandoverNote] = useState("");
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [acceptedAt, setAcceptedAt] = useState<string | null>(null);

  const today = localDate();
  const tomorrow = localDate(addDays(new Date(), 1));

  useEffect(() => {
    try {
      const rawThresholds = window.localStorage.getItem("resort-pms-v7-thresholds");
      if (rawThresholds) setThresholds({ ...DEFAULT_THRESHOLDS, ...JSON.parse(rawThresholds) });
      const rawNote = window.localStorage.getItem(`resort-pms-v7-note-${today}`);
      if (rawNote) setHandoverNote(rawNote);
      const rawSnapshots = window.localStorage.getItem("resort-pms-v7-snapshots");
      if (rawSnapshots) setSnapshots(JSON.parse(rawSnapshots));
      const rawAccepted = window.localStorage.getItem(`resort-pms-v7-accepted-${today}`);
      if (rawAccepted) setAcceptedAt(rawAccepted);
    } catch { /* station-local convenience only */ }
  }, [today]);

  useEffect(() => {
    try { window.localStorage.setItem(`resort-pms-v7-note-${today}`, handoverNote); } catch { /* optional */ }
  }, [handoverNote, today]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const gridParams = new URLSearchParams({ start: today, end: tomorrow });
      const [taskResponse, receptionResponse, gridResponse, meResponse] = await Promise.all([
        fetch("/core/api/v1/ops/tasks?limit=250", { cache: "no-store" }),
        fetch("/core/api/v1/admin/reception/reservations?limit=500", { cache: "no-store" }),
        fetch(`/core/api/v1/pms/grid?${gridParams}`, { cache: "no-store" }),
        fetch("/core/api/v1/auth/me", { cache: "no-store" }),
      ]);

      const taskBody = await taskResponse.json().catch(() => ({}));
      if (!taskResponse.ok || !Array.isArray(taskBody.items)) throw new Error("Не удалось получить задачи Resort Core");
      const taskItems = taskBody.items as Task[];
      setTasks(taskItems);
      setTasksComplete(taskItems.length < 250);

      const receptionBody = await receptionResponse.json().catch(() => ({}));
      if (receptionResponse.ok && Array.isArray(receptionBody.items)) {
        const items = receptionBody.items as Reservation[];
        setReservations(items);
        setFinanceComplete(items.length < 500);
      } else {
        setReservations([]);
        setFinanceComplete(false);
      }

      const gridBody = await gridResponse.json().catch(() => ({}));
      if (!gridResponse.ok || !Array.isArray(gridBody.rooms)) throw new Error("Не удалось получить статус номерного фонда");
      setRooms((gridBody.rooms as Room[]).map((room) => ({ id: room.id, code: room.code, operational_state: room.operational_state })));

      if (meResponse.ok) setUser(await meResponse.json() as User);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось загрузить Control Tower");
    } finally {
      setLoading(false);
    }
  }, [today, tomorrow]);

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(), 60_000);
    return () => window.clearInterval(timer);
  }, [load]);

  const activeTasks = useMemo(() => tasks.filter((task) => ACTIVE_STATUSES.has(task.status)), [tasks]);

  const agedTasks = useMemo(() => activeTasks.map((task) => {
    const age = ageMinutes(task.created_at);
    const threshold = Math.max(5, thresholds[task.type] || 60);
    const overdue = age >= threshold;
    const ratio = age / threshold;
    const priorityWeight = PRIORITY_WEIGHT[task.priority] || 2;
    const risk = ratio * 10 + priorityWeight * 3 + (!task.assigned_to_name ? 4 : 0);
    return { task, age, threshold, overdue, risk };
  }).sort((a, b) => b.risk - a.risk), [activeTasks, thresholds]);

  const escalations = useMemo(() => agedTasks.filter(({ task, overdue }) => overdue || (!task.assigned_to_name && ["URGENT", "HIGH"].includes(task.priority))), [agedTasks]);
  const unassigned = useMemo(() => activeTasks.filter((task) => !task.assigned_to_name), [activeTasks]);
  const arrivals = useMemo(() => reservations.filter((item) => item.status === "GUARANTEED" && item.checkIn === today), [reservations, today]);
  const departures = useMemo(() => reservations.filter((item) => item.status === "CHECKED_IN" && item.checkOut === today), [reservations, today]);
  const activeDebt = useMemo(() => financeComplete ? reservations.filter((item) => ["GUARANTEED", "CHECKED_IN"].includes(item.status)).reduce((sum, item) => sum + Math.max(0, item.remainingKgs), 0) : null, [reservations, financeComplete]);

  const roomMetrics = useMemo(() => ({
    dirty: rooms.filter((room) => room.operational_state === "DIRTY").length,
    inspection: rooms.filter((room) => room.operational_state === "IN_INSPECTION").length,
    tech: rooms.filter((room) => room.operational_state === "TECH_BLOCK").length,
    clean: rooms.filter((room) => room.operational_state === "CLEAN").length,
  }), [rooms]);

  const previousSnapshot = snapshots[0] || null;
  const carriedTaskIds = useMemo(() => {
    if (!previousSnapshot) return new Set<string>();
    const current = new Set(activeTasks.map((task) => task.id));
    return new Set(previousSnapshot.activeTaskIds.filter((id) => current.has(id)));
  }, [previousSnapshot, activeTasks]);

  function changeThreshold(type: keyof Thresholds, value: number) {
    const next = { ...thresholds, [type]: Math.max(5, Math.min(1440, value || 5)) };
    setThresholds(next);
    try { window.localStorage.setItem("resort-pms-v7-thresholds", JSON.stringify(next)); } catch { /* optional */ }
  }

  function buildSnapshot(): Snapshot {
    return {
      id: `${Date.now()}`,
      createdAt: new Date().toISOString(),
      user: user?.display_name || "Менеджер",
      note: handoverNote.trim(),
      activeTaskIds: activeTasks.map((task) => task.id),
      metrics: {
        arrivals: arrivals.length,
        departures: departures.length,
        activeTasks: activeTasks.length,
        escalations: escalations.length,
        dirty: roomMetrics.dirty,
        inspection: roomMetrics.inspection,
        tech: roomMetrics.tech,
        debtKgs: activeDebt,
      },
    };
  }

  function saveSnapshot() {
    const snapshot = buildSnapshot();
    const next = [snapshot, ...snapshots].slice(0, 10);
    setSnapshots(next);
    try { window.localStorage.setItem("resort-pms-v7-snapshots", JSON.stringify(next)); } catch { /* optional */ }
  }

  function acceptShift() {
    const value = new Date().toISOString();
    setAcceptedAt(value);
    try { window.localStorage.setItem(`resort-pms-v7-accepted-${today}`, value); } catch { /* optional */ }
  }

  function exportSnapshot() {
    const snapshot = buildSnapshot();
    const payload = {
      kind: "three-crowns-shift-handover",
      version: 1,
      stationLocal: true,
      snapshot,
      thresholds,
      tasksComplete,
      financeComplete,
      escalations: escalations.map(({ task, age, threshold }) => ({ id: task.id, type: task.type, room: task.room_code, title: task.title, priority: task.priority, status: task.status, assignee: task.assigned_to_name, ageMinutes: age, controlThresholdMinutes: threshold })),
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = safeFileName(`three-crowns-handover-${today}.json`);
    anchor.click();
    URL.revokeObjectURL(url);
  }

  function printShift() {
    const snapshot = buildSnapshot();
    const popup = window.open("", "_blank", "width=980,height=760");
    if (!popup) return;
    const escalationRows = escalations.slice(0, 30).map(({ task, age, threshold }) => `<tr><td>${task.room_code || "—"}</td><td>${TYPE_LABEL[task.type]}</td><td>${task.title}</td><td>${task.assigned_to_name || "Не назначен"}</td><td>${ageLabel(age)} / ${threshold} мин</td></tr>`).join("");
    popup.document.write(`<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>Передача смены · ${today}</title><style>body{font-family:Arial,sans-serif;color:#17263a;padding:30px}h1{margin:0 0 6px}p{color:#657489}section{margin-top:24px}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}.card{border:1px solid #dbe2ea;border-radius:8px;padding:12px}.card span{display:block;font-size:10px;color:#718094;text-transform:uppercase}.card strong{display:block;margin-top:6px;font-size:20px}table{width:100%;border-collapse:collapse;font-size:12px}th,td{border-bottom:1px solid #e3e8ed;padding:8px;text-align:left}th{font-size:10px;text-transform:uppercase;color:#718094}.note{white-space:pre-wrap;border:1px solid #dbe2ea;padding:14px;border-radius:8px}@media print{button{display:none}}</style></head><body><h1>Три Короны · Передача смены</h1><p>${new Date(snapshot.createdAt).toLocaleString("ru-RU")} · ${snapshot.user}</p><section class="grid"><div class="card"><span>Заезды</span><strong>${snapshot.metrics.arrivals}</strong></div><div class="card"><span>Выезды</span><strong>${snapshot.metrics.departures}</strong></div><div class="card"><span>Активные задачи</span><strong>${snapshot.metrics.activeTasks}</strong></div><div class="card"><span>Контроль</span><strong>${snapshot.metrics.escalations}</strong></div><div class="card"><span>DIRTY</span><strong>${snapshot.metrics.dirty}</strong></div><div class="card"><span>Inspection</span><strong>${snapshot.metrics.inspection}</strong></div><div class="card"><span>TECH_BLOCK</span><strong>${snapshot.metrics.tech}</strong></div><div class="card"><span>Остатки</span><strong>${snapshot.metrics.debtKgs == null ? "—" : `${money(snapshot.metrics.debtKgs)} сом`}</strong></div></section><section><h2>Требует контроля</h2><table><thead><tr><th>Номер</th><th>Тип</th><th>Задача</th><th>Ответственный</th><th>Возраст / порог</th></tr></thead><tbody>${escalationRows || "<tr><td colspan='5'>Нет элементов</td></tr>"}</tbody></table></section><section><h2>Комментарий смены</h2><div class="note">${snapshot.note.replace(/[&<>]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[char] || char)) || "—"}</div></section><section><p>Пороги V7 — настраиваемый интерфейсный контроль, не backend SLA. Источники: Resort Core PMS grid, reception read model и operations tasks.</p></section><script>window.onload=()=>window.print()</script></body></html>`);
    popup.document.close();
  }

  return <section className="v7-control-tower">
    <header className="v7-head">
      <div><p className="eyebrow">Control Tower · V7</p><h2>Передача смены и контроль SLA</h2><span>Live задачи, возраст, назначение, номерной фонд и handover-снимок в одном месте.</span></div>
      <div className="v7-actions"><span className={error ? "v7-health bad" : loading ? "v7-health wait" : "v7-health live"}>{error ? "Core warning" : loading ? "Обновление…" : "Live source"}</span><button className="btn" onClick={() => void load()}>↻</button><button className="btn" onClick={() => setSettingsOpen((value) => !value)}>Пороги</button><button className="btn" onClick={printShift}>Печать</button><button className="btn" onClick={exportSnapshot}>JSON</button></div>
    </header>

    {error && <div className="v7-warning"><strong>Часть Control Tower недоступна</strong><span>{error}</span></div>}
    {!tasksComplete && <div className="v7-warning"><strong>Список задач потенциально неполный</strong><span>Endpoint вернул 250 элементов. V7 не трактует отсутствие задачи за пределами лимита как факт.</span></div>}
    {!financeComplete && <div className="v7-warning"><strong>Финансы неполные или недоступны</strong><span>Сумма остатков показывается как неизвестная, а не как ноль.</span></div>}

    {settingsOpen && <div className="v7-thresholds"><div><strong>Пороги операционного контроля V7</strong><span>Настройка рабочей станции; это не backend SLA и не меняет Resort Core.</span></div><label>Уборка <input type="number" min={5} max={1440} value={thresholds.HOUSEKEEPING} onChange={(event) => changeThreshold("HOUSEKEEPING", Number(event.target.value))} /> мин</label><label>Ремонт <input type="number" min={5} max={1440} value={thresholds.MAINTENANCE} onChange={(event) => changeThreshold("MAINTENANCE", Number(event.target.value))} /> мин</label><label>Запрос гостя <input type="number" min={5} max={1440} value={thresholds.GUEST_REQUEST} onChange={(event) => changeThreshold("GUEST_REQUEST", Number(event.target.value))} /> мин</label></div>}

    <div className="v7-kpis">
      <article><span>Активные задачи</span><strong>{activeTasks.length}</strong><small>{unassigned.length} без ответственного</small></article>
      <article className={escalations.length ? "danger" : "ok"}><span>Требуют контроля</span><strong>{escalations.length}</strong><small>по возрасту / приоритету</small></article>
      <article><span>Перешли из снимка</span><strong>{carriedTaskIds.size}</strong><small>{previousSnapshot ? new Date(previousSnapshot.createdAt).toLocaleString("ru-RU", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }) : "нет прошлого снимка"}</small></article>
      <article><span>Номерной фонд</span><strong>{roomMetrics.clean}<small> CLEAN</small></strong><small>{roomMetrics.dirty} dirty · {roomMetrics.inspection} inspection · {roomMetrics.tech} tech</small></article>
      <article><span>Гостевые события</span><strong>{arrivals.length}<small> / {departures.length}</small></strong><small>заезды / выезды сегодня</small></article>
      <article className={activeDebt == null ? "muted" : activeDebt > 0 ? "money" : "ok"}><span>Остаток активных</span><strong>{activeDebt == null ? "—" : money(activeDebt)}<small>{activeDebt == null ? "" : " сом"}</small></strong><small>{financeComplete ? "confirmed reception read model" : "финансы не подтверждены"}</small></article>
    </div>

    <div className="v7-grid">
      <section className="v7-escalation-card">
        <div className="v7-section-head"><div><strong>Контроль активных задач</strong><span>Сортировка по возрасту, приоритету и отсутствию назначения.</span></div><b>{escalations.length}</b></div>
        <div className="v7-task-list">{escalations.length === 0 ? <p className="v7-empty">Нет задач за настроенными порогами контроля.</p> : escalations.slice(0, 20).map(({ task, age, threshold }) => <article key={task.id} className={carriedTaskIds.has(task.id) ? "carried" : ""}><div className={`v7-task-type type-${task.type.toLowerCase()}`}>{TYPE_LABEL[task.type]}</div><div><strong>{task.room_code ? `№ ${task.room_code} · ` : ""}{task.title}</strong><span>{task.assigned_to_name || "Без ответственного"} · {task.status} · {task.priority}</span></div><div className="v7-age"><strong>{ageLabel(age)}</strong><span>порог {threshold} мин</span></div>{carriedTaskIds.has(task.id) && <em>с прошлой смены</em>}</article>)}</div>
      </section>

      <section className="v7-handover-card">
        <div className="v7-section-head"><div><strong>Handover</strong><span>Комментарий и воспроизводимый снимок текущей смены.</span></div><b>{snapshots.length}</b></div>
        <textarea value={handoverNote} onChange={(event) => setHandoverNote(event.target.value)} placeholder="Что должна знать следующая смена: гости, номера, ремонт, оплаты, обещания…" maxLength={4000} />
        <div className="v7-handover-actions"><button className="primary" onClick={saveSnapshot}>Сохранить снимок смены</button><button onClick={acceptShift}>{acceptedAt ? "Обновить принятие" : "Принять смену"}</button></div>
        <p className="v7-local-disclaimer">Handover-снимки и отметка «принял смену» сейчас хранятся локально на рабочей станции. Они не подменяют Resort Core и явно экспортируются/печатаются для передачи.</p>
        {acceptedAt && <div className="v7-accepted"><strong>Смена принята</strong><span>{new Date(acceptedAt).toLocaleString("ru-RU")} · {user?.display_name || "Менеджер"}</span></div>}
        <div className="v7-snapshots">{snapshots.slice(0, 5).map((snapshot) => <article key={snapshot.id}><div><strong>{new Date(snapshot.createdAt).toLocaleString("ru-RU")}</strong><span>{snapshot.user}</span></div><b>{snapshot.metrics.escalations} контроль</b><small>{snapshot.metrics.activeTasks} задач</small></article>)}{snapshots.length === 0 && <p className="v7-empty">Снимков смены ещё нет.</p>}</div>
      </section>
    </div>
  </section>;
}
