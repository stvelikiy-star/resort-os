"use client";

import { useEffect, useMemo, useState } from "react";

type ReservationDetail = {
  local_date: string;
  reservation: {
    id: string;
    booking_number: string;
    status: string;
    check_in: string;
    check_out: string;
    adults: number;
    children: number;
    total_kgs: number;
    notes?: string | null;
  };
  guest: {
    first_name?: string | null;
    last_name?: string | null;
    phone?: string | null;
    email?: string | null;
  };
  room: {
    id: string;
    code: string;
    state: string;
    room_type_name?: string | null;
    segment_start: string;
    segment_end: string;
  } | null;
  schedule: Array<{
    inventory_block_id: string;
    room_id: string;
    room_code: string;
    room_state: string;
    room_type_name: string;
    start: string;
    end: string;
    is_working_room: boolean;
  }>;
  finance: {
    total_kgs: number;
    paid_kgs: number;
    remaining_kgs: number;
    payments: Array<{
      id: string;
      amount_kgs: number;
      method: string;
      status: string;
      provider?: string | null;
      external_ref?: string | null;
      paid_at?: string | null;
      created_at: string;
    }>;
  };
  room_tasks: Array<{
    id: string;
    room_code: string;
    type: string;
    status: string;
    priority: string;
    title: string;
    assigned_to_name?: string | null;
    created_at: string;
  }>;
  audit: Array<{
    id: string;
    action: string;
    resource: string;
    source?: string | null;
    result: string;
    created_at: string;
  }>;
};

const money = (value: number) => `${new Intl.NumberFormat("ru-RU").format(value)} сом`;
const TASK_ACTIVE = new Set(["OPEN", "IN_PROGRESS", "IN_INSPECTION"]);

export default function ReservationQuickFacts({ reservationId, refreshKey }: { reservationId: string; refreshKey?: string }) {
  const [detail, setDetail] = useState<ReservationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetch(`/core/api/v1/admin/booking/reservations/${reservationId}`, { cache: "no-store" })
      .then(async (response) => {
        const body = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(body.detail || "Не удалось загрузить данные брони");
        return body as ReservationDetail;
      })
      .then((body) => { if (!cancelled) setDetail(body); })
      .catch((cause) => { if (!cancelled) setError(cause instanceof Error ? cause.message : "Ошибка карточки брони"); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [reservationId, refreshKey]);

  const activeTasks = useMemo(() => (detail?.room_tasks || []).filter((task) => TASK_ACTIVE.has(task.status)), [detail]);
  const latestAudit = useMemo(() => (detail?.audit || []).slice(0, 8), [detail]);
  const latestPayments = useMemo(() => [...(detail?.finance.payments || [])].reverse().slice(0, 4), [detail]);

  if (loading && !detail) return <section className="chess-quick-facts"><div className="detail-muted">Загружаю гостя, платежи и задачи…</div></section>;
  if (error && !detail) return <section className="chess-quick-facts"><div className="detail-muted">{error}</div></section>;
  if (!detail) return null;

  const guestName = [detail.guest.first_name, detail.guest.last_name].filter(Boolean).join(" ") || "Гость";

  return <section className="chess-quick-facts">
    <div className="chess-quick-contact">
      <div><span>Гость</span><strong>{guestName}</strong><small>{detail.room ? `Сейчас № ${detail.room.code} · ${detail.room.room_type_name || ""}` : "Номер не определён"}</small></div>
      <div className="chess-contact-actions">
        {detail.guest.phone && <a className="btn" href={`tel:${detail.guest.phone}`}>Позвонить · {detail.guest.phone}</a>}
        {detail.guest.email && <a className="btn" href={`mailto:${detail.guest.email}`}>Email</a>}
      </div>
    </div>

    <div className="chess-finance-strip">
      <div><span>Стоимость</span><strong>{money(detail.finance.total_kgs)}</strong></div>
      <div><span>Подтверждено</span><strong>{money(detail.finance.paid_kgs)}</strong></div>
      <div><span>Остаток</span><strong>{money(detail.finance.remaining_kgs)}</strong></div>
      <div><span>Активные задачи</span><strong>{activeTasks.length}</strong></div>
    </div>

    <div className="chess-facts-columns">
      <details open={activeTasks.length > 0}>
        <summary>Задачи по проживанию · {activeTasks.length} активных</summary>
        <div className="chess-fact-list">
          {activeTasks.length === 0 ? <p>Активных задач нет.</p> : activeTasks.slice(0, 8).map((task) => <div key={task.id}>
            <strong>№ {task.room_code} · {task.title}</strong>
            <span>{task.type} · {task.priority} · {task.status}</span>
            <small>{task.assigned_to_name || "Не назначено"}</small>
          </div>)}
        </div>
      </details>

      <details>
        <summary>Внутренние платежи · {detail.finance.payments.length}</summary>
        <div className="chess-fact-list">
          {latestPayments.length === 0 ? <p>Подтверждённых записей оплаты нет.</p> : latestPayments.map((payment) => <div key={payment.id}>
            <strong>{money(payment.amount_kgs)} · {payment.status}</strong>
            <span>{payment.method}{payment.provider ? ` · ${payment.provider}` : ""}</span>
            <small>{payment.paid_at || payment.created_at}</small>
          </div>)}
        </div>
      </details>

      <details>
        <summary>Последние действия · {detail.audit.length}</summary>
        <div className="chess-fact-list">
          {latestAudit.length === 0 ? <p>Записей аудита нет.</p> : latestAudit.map((entry) => <div key={entry.id}>
            <strong>{entry.action}</strong>
            <span>{entry.resource} · {entry.source || "—"} · {entry.result}</span>
            <small>{entry.created_at}</small>
          </div>)}
        </div>
      </details>
    </div>

    {detail.reservation.notes && <div className="chess-booking-note"><span>Заметка</span><p>{detail.reservation.notes}</p></div>}
  </section>;
}
