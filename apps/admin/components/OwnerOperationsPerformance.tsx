"use client";

import { useCallback, useEffect, useState } from "react";

type TaskSummary = {
  created_in_period: number;
  completed_in_period: number;
  active_now: number;
  urgent_now: number;
  avg_completion_minutes: number | null;
  max_completion_minutes: number | null;
};

type OwnerOperations = {
  property: { local_date: string; timezone: string };
  range: { from: string; to: string; days: number };
  guest_services: TaskSummary & {
    past_due_date_active: number;
    by_service: Array<{
      service_code: string;
      created_in_period: number;
      completed_in_period: number;
      active_now: number;
      avg_completion_minutes: number | null;
    }>;
  };
  guest_service_sla: {
    status: string;
    configured: boolean;
    target_minutes: number | null;
    breach_count: number | null;
    observed_avg_completion_minutes: number | null;
    due_date_overdue_active: number;
  };
  housekeeping: TaskSummary;
  maintenance: TaskSummary;
  problem_rooms: Array<{
    room_id: string;
    room_code: string;
    room_name?: string | null;
    operational_state: string;
    maintenance_created_in_period: number;
    completed_from_period: number;
    active_from_period: number;
  }>;
  recurring_faults: Array<{
    room_id: string;
    room_code: string;
    title: string;
    occurrences: number;
  }>;
  staff_performance: Array<{
    staff_id: string;
    display_name: string;
    role: string;
    task_type: string;
    completed_in_period: number;
    active_now: number;
    avg_completion_minutes: number | null;
  }>;
};

function monthStart(localDate: string) {
  const [year, month] = localDate.split("-");
  return `${year}-${month}-01`;
}

function minutes(value: number | null) {
  if (value == null) return "—";
  if (value < 60) return `${Math.round(value)} мин`;
  const hours = Math.floor(value / 60);
  const remainder = Math.round(value % 60);
  return remainder ? `${hours} ч ${remainder} мин` : `${hours} ч`;
}

async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url, { cache: "no-store" });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Не удалось загрузить операционную аналитику");
  return body as T;
}

export default function OwnerOperationsPerformance() {
  const [data, setData] = useState<OwnerOperations | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const dashboard = await getJson<{ property: { local_date: string } }>("/core/api/v1/admin/dashboard");
      const params = new URLSearchParams({
        from_date: monthStart(dashboard.property.local_date),
        to_date: dashboard.property.local_date,
      });
      setData(await getJson<OwnerOperations>(`/core/api/v1/admin/intelligence/operations-performance?${params}`));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка операционной аналитики");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  if (loading && !data) return <section className="owner-executive loading">Формирую операционную аналитику…</section>;
  if (!data) return <section className="owner-executive"><div className="error-box">{error || "Операционная аналитика недоступна"}</div><button className="btn" onClick={load}>Повторить</button></section>;

  return (
    <section className="owner-executive">
      <div className="owner-executive-head">
        <div>
          <p className="eyebrow">OWNER OPERATIONS · MTD</p>
          <h2>Сервис, уборка и ремонты</h2>
          <p>{data.range.from} → {data.range.to} · {data.property.timezone} · только факты Resort Core</p>
        </div>
        <button className="btn" onClick={load} disabled={loading}>{loading ? "Обновляю…" : "Обновить"}</button>
      </div>

      {error && <div className="error-box">{error}</div>}

      <div className="owner-executive-grid">
        <article><span>Guest Services · создано</span><strong>{data.guest_services.created_in_period}</strong><small>{data.guest_services.completed_in_period} завершено за период</small></article>
        <article className={data.guest_services.active_now > 0 ? "executive-attention" : ""}><span>Guest Services · активные</span><strong>{data.guest_services.active_now}</strong><small>{data.guest_services.past_due_date_active} просрочено по дате</small></article>
        <article><span>Среднее закрытие Guest Services</span><strong>{minutes(data.guest_services.avg_completion_minutes)}</strong><small>наблюдаемое время, не SLA</small></article>
        <article><span>SLA Guest Services</span><strong>{data.guest_service_sla.status}</strong><small>{data.guest_service_sla.configured ? `${data.guest_service_sla.target_minutes} мин` : "порог в Core не задан"}</small></article>
        <article><span>Housekeeping · завершено</span><strong>{data.housekeeping.completed_in_period}</strong><small>{data.housekeeping.active_now} активно · среднее {minutes(data.housekeeping.avg_completion_minutes)}</small></article>
        <article className={data.housekeeping.urgent_now > 0 ? "executive-attention" : ""}><span>Housekeeping · срочно</span><strong>{data.housekeeping.urgent_now}</strong><small>{data.housekeeping.created_in_period} создано за период</small></article>
        <article><span>Maintenance · завершено</span><strong>{data.maintenance.completed_in_period}</strong><small>{data.maintenance.active_now} активно · среднее {minutes(data.maintenance.avg_completion_minutes)}</small></article>
        <article className={data.problem_rooms.length > 0 ? "executive-attention" : ""}><span>Проблемные номера</span><strong>{data.problem_rooms.length}</strong><small>2+ ремонтных задач за выбранный период</small></article>
        <article className={data.recurring_faults.length > 0 ? "executive-attention" : ""}><span>Повторяющиеся поломки</span><strong>{data.recurring_faults.length}</strong><small>точное повторение названия в одном номере</small></article>
      </div>

      <div className="owner-executive-bottom">
        <article className="owner-executive-actions-panel">
          <div><p className="eyebrow">PROBLEM ROOMS</p><h3>Номера с повторными ремонтами</h3></div>
          {data.problem_rooms.length === 0 ? <p className="executive-muted">За выбранный период повторных ремонтов по номерам нет.</p> : (
            <div className="executive-action-list">{data.problem_rooms.slice(0, 8).map((room) => <div key={room.room_id}>
              <span className="exec-severity e-HIGH">№ {room.room_code}</span>
              <strong>{room.maintenance_created_in_period} ремонтных задач · {room.operational_state}</strong>
              <b>{room.active_from_period} актив.</b>
            </div>)}</div>
          )}
        </article>

        <article className="owner-executive-actions-panel">
          <div><p className="eyebrow">RECURRING FAULTS</p><h3>Точные повторения поломок</h3></div>
          {data.recurring_faults.length === 0 ? <p className="executive-muted">Точных повторений названия поломки в одном номере нет.</p> : (
            <div className="executive-action-list">{data.recurring_faults.slice(0, 8).map((fault) => <div key={`${fault.room_id}-${fault.title}`}>
              <span className="exec-severity e-CRITICAL">№ {fault.room_code}</span>
              <strong>{fault.title}</strong>
              <b>×{fault.occurrences}</b>
            </div>)}</div>
          )}
        </article>
      </div>

      <div className="owner-executive-bottom">
        <article className="owner-executive-actions-panel">
          <div><p className="eyebrow">TEAM FACTS</p><h3>Исполнение по сотрудникам</h3></div>
          {data.staff_performance.length === 0 ? <p className="executive-muted">Нет завершённых или активных задач по MAID / TECHNICIAN.</p> : (
            <div className="executive-action-list">{data.staff_performance.slice(0, 10).map((staff) => <div key={`${staff.staff_id}-${staff.task_type}`}>
              <span className="exec-severity e-NORMAL">{staff.role}</span>
              <strong>{staff.display_name} · {staff.task_type}</strong>
              <b>{staff.completed_in_period} done · {staff.active_now} active · {minutes(staff.avg_completion_minutes)}</b>
            </div>)}</div>
          )}
        </article>

        <article className="owner-executive-truth">
          <p className="eyebrow">TRUTH BOUNDARY</p>
          <h3>Как читать показатели</h3>
          <p>Время закрытия считается от фактического OperationalTask.createdAt до completedAt только для DONE.</p>
          <p>SLA breach не считается, пока в Resort Core нет утверждённого SLA-порога. Просрочка по дате — отдельный факт.</p>
          <p>«Проблемный номер» означает минимум две MAINTENANCE-задачи в периоде.</p>
          <p>«Повторяющаяся поломка» — одинаковый нормализованный текст title в том же физическом номере. Семантическое сходство ИИ не применяется.</p>
        </article>
      </div>
    </section>
  );
}
