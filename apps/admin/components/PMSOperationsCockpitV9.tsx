"use client";

import { useMemo, useState } from "react";
import { ControlReservationV9, ControlTaskV9, usePMSControlSnapshotV9 } from "./PMSControlSnapshotV9";

function money(value: number) {
  return new Intl.NumberFormat("ru-RU").format(value);
}

function taskLabel(type: ControlTaskV9["type"]) {
  if (type === "HOUSEKEEPING") return "Уборка";
  if (type === "MAINTENANCE") return "Ремонт";
  return "Запрос гостя";
}

function errorText(body: any, fallback: string) {
  if (typeof body?.detail === "string") return body.detail;
  const code = body?.detail?.code;
  if (code === "CHECK_IN_ROOM_NOT_READY") return `Номер ${body.detail.room_code || ""} не готов к заселению.`.trim();
  if (code === "CHECK_IN_DATE_OUTSIDE_SCHEDULE") return "Сегодня не входит в график проживания. Сначала исправьте бронь в шахматке.";
  if (code === "CHECK_OUT_AFTER_SCHEDULE") return "Фактическая дата позже запланированного выезда. Сначала продлите график в шахматке.";
  return fallback;
}

export default function PMSOperationsCockpitV9() {
  const { snapshot, loading, refreshing, error: snapshotError, refresh } = usePMSControlSnapshotV9();
  const [busyId, setBusyId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const localToday = snapshot?.local_date || "";
  const arrivals = useMemo(() => (snapshot?.reservations || []).filter((item) => item.status === "GUARANTEED" && item.checkIn === localToday), [snapshot, localToday]);
  const departures = useMemo(() => (snapshot?.reservations || []).filter((item) => item.status === "CHECKED_IN" && item.checkOut === localToday), [snapshot, localToday]);
  const overdue = useMemo(() => (snapshot?.reservations || []).filter((item) => item.status === "CHECKED_IN" && item.checkOut < localToday), [snapshot, localToday]);
  const notReady = useMemo(() => arrivals.filter((item) => !item.room_id || item.room_state !== "CLEAN"), [arrivals]);
  const debtQueue = useMemo(() => (snapshot?.reservations || []).filter((item) => item.remainingKgs > 0).sort((a, b) => b.remainingKgs - a.remainingKgs).slice(0, 8), [snapshot]);
  const urgentTasks = useMemo(() => (snapshot?.tasks || []).slice(0, 8), [snapshot]);

  async function stayAction(item: ControlReservationV9, action: "check-in" | "check-out") {
    const verb = action === "check-in" ? "заселение" : "выезд";
    if (!window.confirm(`Подтвердить ${verb}: ${item.firstName || item.bookingNumber}${item.room_code ? ` · № ${item.room_code}` : ""}?`)) return;
    setBusyId(item.id);
    setActionError(null);
    try {
      const response = await fetch(`/core/api/v1/admin/stays/reservations/${item.id}/${action}`, { method: "POST" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(errorText(body, `Не удалось выполнить ${verb}`));
      await refresh();
    } catch (cause) {
      setActionError(cause instanceof Error ? cause.message : `Ошибка: ${verb}`);
    } finally {
      setBusyId(null);
    }
  }

  function jumpToTape() {
    document.querySelector(".v8-board")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  const roomStates = snapshot?.room_states || {};
  const error = actionError || snapshotError;

  return <section className="v9-cockpit">
    <header className="v9-head">
      <div><p className="eyebrow">PMS Integration · V9</p><h2>Один Core · одна смена · одна шахматка</h2><span>Reception, оплаты, room-state и активные задачи используют один общий live snapshot. Изменения размещения выполняются в Universal Tape Chart через Core preview/commit.</span></div>
      <div className="v9-actions"><span className={`v9-source ${snapshot ? "ok" : "bad"}`}>{snapshot ? `Core complete · ${snapshot.local_date}` : "Snapshot offline"}</span><button className="btn" onClick={() => void refresh()} disabled={refreshing}>↻ {refreshing ? "Обновляю" : "Обновить"}</button><button className="btn primary" onClick={jumpToTape}>К шахматке ↓</button></div>
    </header>

    {error && <div className="v9-error">{error}</div>}

    <div className="v9-kpis">
      <article><span>Заезды сегодня</span><strong>{loading ? "…" : arrivals.length}</strong><small>{notReady.length ? `${notReady.length} требуют подготовки` : "готовность проверена"}</small></article>
      <article><span>Выезды сегодня</span><strong>{loading ? "…" : departures.length}</strong><small>{overdue.length ? `+ ${overdue.length} просрочено` : "без просрочек"}</small></article>
      <article className={notReady.length ? "danger" : "ok"}><span>Не готовы к заезду</span><strong>{loading ? "…" : notReady.length}</strong><small>только GUARANTEED сегодня</small></article>
      <article><span>Проживают</span><strong>{loading ? "…" : (snapshot?.reservations || []).filter((item) => item.status === "CHECKED_IN").length}</strong><small>включая просроченные</small></article>
      <article className="money"><span>Остаток активных</span><strong>{snapshot ? `${money(snapshot.summary.debt_total_kgs)} сом` : "—"}</strong><small>{debtQueue.length} крупнейших в очереди</small></article>
      <article><span>Активные задачи</span><strong>{snapshot?.summary.active_tasks ?? "—"}</strong><small>{urgentTasks.filter((task) => !task.assigned_to_name).length} без ответственного среди первых</small></article>
    </div>

    <div className="v9-grid">
      <section className="v9-card">
        <div className="v9-section-head"><div><strong>Смена ресепшена</strong><span>Заезды, выезды и исключения сегодня.</span></div><b>{arrivals.length + departures.length + overdue.length}</b></div>
        <div className="v9-events">
          {overdue.map((item) => <article className="critical" key={`over-${item.id}`}><div><em>Просроченный выезд · сначала график</em><strong>{item.firstName || "Гость"} · {item.bookingNumber}</strong><span>№ {item.room_code || "—"} · план {item.checkOut}. Core не позволит оформить выезд позже графика без его явного продления.</span></div><div className="v9-row-actions">{item.remainingKgs > 0 && <b>{money(item.remainingKgs)} сом</b>}<button onClick={jumpToTape}>Исправить график</button></div></article>)}
          {arrivals.map((item) => <article className={!item.room_id || item.room_state !== "CLEAN" ? "critical" : "arrival"} key={`arr-${item.id}`}><div><em>{!item.room_id ? "Заезд · номер не назначен" : item.room_state !== "CLEAN" ? "Заезд · номер не готов" : "Заезд сегодня"}</em><strong>{item.firstName || "Гость"} · {item.bookingNumber}</strong><span>№ {item.room_code || "—"} · {item.room_type_name || "категория"}{item.has_room_move ? " · split stay" : ""}</span></div><div className="v9-row-actions">{item.remainingKgs > 0 && <b>{money(item.remainingKgs)} сом</b>}<button disabled={busyId === item.id || !item.room_id || item.room_state !== "CLEAN"} onClick={() => void stayAction(item, "check-in")}>Заезд</button></div></article>)}
          {departures.map((item) => <article className="departure" key={`dep-${item.id}`}><div><em>Выезд сегодня</em><strong>{item.firstName || "Гость"} · {item.bookingNumber}</strong><span>№ {item.room_code || "—"}</span></div><div className="v9-row-actions">{item.remainingKgs > 0 && <b>{money(item.remainingKgs)} сом</b>}<button disabled={busyId === item.id} onClick={() => void stayAction(item, "check-out")}>Выезд</button></div></article>)}
          {!loading && arrivals.length + departures.length + overdue.length === 0 && <p className="v9-empty">На сегодня нет событий проживания.</p>}
        </div>
      </section>

      <section className="v9-card">
        <div className="v9-section-head"><div><strong>Операционная очередь</strong><span>Все активные задачи приходят из общего Core snapshot.</span></div><b>{snapshot?.tasks.length ?? "—"}</b></div>
        <div className="v9-tasks">{urgentTasks.map((task) => <article key={task.id}><div className={`v9-task-type type-${task.type.toLowerCase()}`}>{taskLabel(task.type)}</div><div><strong>{task.room_code ? `№ ${task.room_code} · ` : ""}{task.title}</strong><span>{task.status} · {task.priority} · {task.assigned_to_name || "без ответственного"}</span></div></article>)}{!loading && urgentTasks.length === 0 && <p className="v9-empty">Активных задач нет.</p>}</div>
      </section>

      <section className="v9-card">
        <div className="v9-section-head"><div><strong>Финансовая очередь</strong><span>Только manager-recorded RECEIVED payments.</span></div><b>{debtQueue.length}</b></div>
        <div className="v9-debts">{debtQueue.map((item) => <article key={item.id}><div><strong>{item.firstName || "Гость"} · {item.bookingNumber}</strong><span>№ {item.room_code || "—"} · {item.status}</span></div><b>{money(item.remainingKgs)} сом</b></article>)}{!loading && debtQueue.length === 0 && <p className="v9-empty">Активных остатков нет.</p>}</div>
        <div className="v9-room-states"><span>CLEAN <b>{roomStates.CLEAN || 0}</b></span><span>DIRTY <b>{roomStates.DIRTY || 0}</b></span><span>INSPECTION <b>{roomStates.IN_INSPECTION || 0}</b></span><span>TECH <b>{roomStates.TECH_BLOCK || 0}</b></span></div>
      </section>
    </div>
  </section>;
}
