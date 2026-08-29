"use client";

import { useCallback, useEffect, useState } from "react";
import OwnerControlV2 from "./OwnerControlV2";
import OwnerExecutivePack from "./OwnerExecutivePack";

type StayItem = {
  id: string;
  booking_number: string;
  guest_name?: string | null;
  phone?: string | null;
  room_code?: string | null;
  check_in: string;
  check_out: string;
};

type AttentionTask = {
  id: string;
  type: string;
  status: string;
  priority: string;
  title: string;
  room_code?: string | null;
  assigned_to?: string | null;
  created_at: string;
};

type Dashboard = {
  property: { name: string; code: string; timezone: string; currency: string; local_date: string };
  rooms: { total: number; clean: number; dirty: number; in_inspection: number; tech_block: number; unknown: number };
  stays: { arrivals_today: number; departures_today: number; in_house: number; guaranteed: number; occupied_rooms: number; occupancy_percent: number };
  requests: { new: number; quoted: number; awaiting_prepayment: number; active: number };
  tasks: { housekeeping_active: number; maintenance_active: number; guest_requests_active: number; urgent_active: number };
  communications: { active: number; needs_reply: number; oldest_waiting_seconds: number; sla_rule: null };
  finance: { confirmed_payments_today_kgs: number; active_reservations_total_kgs: number; active_reservations_paid_kgs: number; active_reservations_remaining_kgs: number; scope_note: string };
  today: { arrivals: StayItem[]; departures: StayItem[] };
  attention_tasks: AttentionTask[];
};

type DashboardDestination = "PMS" | "REQUESTS" | "RESERVATIONS" | "FINANCE" | "OPS" | "INBOX";

const money = (value: number) => `${new Intl.NumberFormat("ru-RU").format(value)} сом`;
const taskType: Record<string, string> = { HOUSEKEEPING: "Уборка", MAINTENANCE: "Ремонт", GUEST_REQUEST: "Запрос гостя" };
const priority: Record<string, string> = { URGENT: "Срочно", HIGH: "Высокий", NORMAL: "Обычный", LOW: "Низкий" };

function waitingLabel(seconds: number) {
  if (seconds <= 0) return "—";
  if (seconds < 60) return `${seconds} сек`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)} мин`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} ч ${Math.floor((seconds % 3600) / 60)} мин`;
  return `${Math.floor(seconds / 86400)} д ${Math.floor((seconds % 86400) / 3600)} ч`;
}

function Drill({ children, to, onNavigate }: { children: React.ReactNode; to: DashboardDestination; onNavigate?: (tab: DashboardDestination) => void }) {
  if (!onNavigate) return <>{children}</>;
  return <button className="command-drill" onClick={() => onNavigate(to)}>{children}<span aria-hidden="true">→</span></button>;
}

export default function DashboardBoard({ onNavigate }: { onNavigate?: (tab: DashboardDestination) => void }) {
  const [data, setData] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/core/api/v1/admin/dashboard", { cache: "no-store" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Не удалось загрузить Command Center");
      setData(body as Dashboard);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка загрузки");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  if (loading) return <main className="work-shell"><div className="loading">Загрузка Command Center…</div></main>;
  if (error) return <main className="work-shell"><div className="error-box">{error}</div><button className="btn" onClick={load}>Повторить</button></main>;
  if (!data) return null;

  const roomReady = data.rooms.clean;
  const roomNeedsWork = data.rooms.dirty + data.rooms.in_inspection + data.rooms.tech_block;

  return (
    <main className="work-shell dashboard-shell">
      <div className="work-head">
        <div>
          <p className="eyebrow">Три Короны · управление</p>
          <h1>Command Center</h1>
          <p className="subtitle">{data.property.local_date} · данные Resort Core · {data.property.timezone}</p>
        </div>
        <button className="btn" onClick={load}>Обновить</button>
      </div>

      <OwnerExecutivePack />
      <OwnerControlV2 />

      <section className="command-kpis">
        <article><span>Загрузка сейчас</span><strong>{data.stays.occupancy_percent}%</strong><small>{data.stays.occupied_rooms} из {data.rooms.total} номеров</small></article>
        <article><span>Заезды сегодня</span><strong>{data.stays.arrivals_today}</strong><small>гарантированные брони</small></article>
        <article><span>Выезды сегодня</span><strong>{data.stays.departures_today}</strong><small>проживающие гости</small></article>
        <article><span>Активные заявки</span><strong>{data.requests.active}</strong><small>{data.requests.awaiting_prepayment} ждут решения менеджера</small></article>
        <article><span>Сообщения ждут</span><strong>{data.communications.needs_reply}</strong><small>самое долгое: {waitingLabel(data.communications.oldest_waiting_seconds)}</small></article>
        <article><span>Платежи сегодня</span><strong>{money(data.finance.confirmed_payments_today_kgs)}</strong><small>только записанные менеджером</small></article>
        <article><span>Номера требуют внимания</span><strong>{roomNeedsWork}</strong><small>уборка / проверка / ремонт</small></article>
      </section>

      <section className="command-grid">
        <article className="command-panel">
          <div className="command-panel-head"><div><p className="eyebrow">Номерной фонд</p><h2>{data.rooms.total} номеров · состояние</h2></div><Drill to="PMS" onNavigate={onNavigate}>Открыть шахматку</Drill></div>
          <div className="room-state-grid">
            <div className="state-clean"><strong>{data.rooms.clean}</strong><span>Готовы</span></div>
            <div className="state-dirty"><strong>{data.rooms.dirty}</strong><span>Нужна уборка</span></div>
            <div className="state-inspection"><strong>{data.rooms.in_inspection}</strong><span>На проверке</span></div>
            <div className="state-tech"><strong>{data.rooms.tech_block}</strong><span>TECH_BLOCK</span></div>
            <div><strong>{data.rooms.unknown}</strong><span>Не указан статус</span></div>
          </div>
          <p className="command-note">Готовы сейчас: {roomReady}. Физическое состояние номера не подменяет коммерческую занятость.</p>
        </article>

        <article className="command-panel">
          <div className="command-panel-head"><div><p className="eyebrow">Бронирование</p><h2>Заявки и проживания</h2></div><Drill to="REQUESTS" onNavigate={onNavigate}>Открыть заявки</Drill></div>
          <div className="command-list compact">
            <div><span>Новые заявки</span><strong>{data.requests.new}</strong></div>
            <div><span>Рассчитаны</span><strong>{data.requests.quoted}</strong></div>
            <div><span>Ждут решения/предоплаты менеджера</span><strong>{data.requests.awaiting_prepayment}</strong></div>
            <div><span>Гарантированные будущие</span><strong>{data.stays.guaranteed}</strong></div>
            <div><span>Сейчас проживают</span><strong>{data.stays.in_house}</strong></div>
          </div>
        </article>

        <article className="command-panel">
          <div className="command-panel-head"><div><p className="eyebrow">Коммуникации</p><h2>Аудит входящих</h2></div><Drill to="INBOX" onNavigate={onNavigate}>Открыть аудит</Drill></div>
          <div className="command-list compact">
            <div><span>Активные диалоги</span><strong>{data.communications.active}</strong></div>
            <div><span>Нужен ответ</span><strong>{data.communications.needs_reply}</strong></div>
            <div><span>Самое долгое ожидание</span><strong>{waitingLabel(data.communications.oldest_waiting_seconds)}</strong></div>
          </div>
          <p className="command-note">Клиентские каналы V1 ведёт n8n. Resort OS хранит только доступные факты/аудит; SLA-порог не выдумывается.</p>
        </article>

        <article className="command-panel">
          <div className="command-panel-head"><div><p className="eyebrow">Внутренний контроль</p><h2>Активные брони</h2></div><Drill to="FINANCE" onNavigate={onNavigate}>Открыть финансы</Drill></div>
          <div className="command-money">
            <div><span>Стоимость</span><strong>{money(data.finance.active_reservations_total_kgs)}</strong></div>
            <div><span>Записано оплат</span><strong>{money(data.finance.active_reservations_paid_kgs)}</strong></div>
            <div><span>Остаток</span><strong>{money(data.finance.active_reservations_remaining_kgs)}</strong></div>
          </div>
          <p className="command-note">Только внутренние manager-confirmed факты. Это не бухгалтерская прибыль, налоговый или revenue-recognition отчёт.</p>
        </article>

        <article className="command-panel">
          <div className="command-panel-head"><div><p className="eyebrow">Операции</p><h2>Активная работа</h2></div><Drill to="OPS" onNavigate={onNavigate}>Открыть задачи</Drill></div>
          <div className="command-list compact">
            <div><span>Уборка</span><strong>{data.tasks.housekeeping_active}</strong></div>
            <div><span>Ремонт</span><strong>{data.tasks.maintenance_active}</strong></div>
            <div><span>Запросы гостей</span><strong>{data.tasks.guest_requests_active}</strong></div>
          </div>
          {data.tasks.urgent_active > 0 && <p className="command-note danger-text">Срочных активных задач: {data.tasks.urgent_active}</p>}
        </article>
      </section>

      <section className="command-grid two">
        <article className="command-panel">
          <div className="command-panel-head"><div><p className="eyebrow">Сегодня</p><h2>Заезды</h2></div><Drill to="RESERVATIONS" onNavigate={onNavigate}>Ресепшен · {data.today.arrivals.length}</Drill></div>
          <StayList items={data.today.arrivals} empty="Заездов по текущим данным нет." />
        </article>
        <article className="command-panel">
          <div className="command-panel-head"><div><p className="eyebrow">Сегодня</p><h2>Выезды</h2></div><Drill to="RESERVATIONS" onNavigate={onNavigate}>Ресепшен · {data.today.departures.length}</Drill></div>
          <StayList items={data.today.departures} empty="Выездов по текущим данным нет." />
        </article>
      </section>

      <section className="command-panel attention-panel">
        <div className="command-panel-head"><div><p className="eyebrow">Контроль</p><h2>Задачи, требующие внимания</h2></div><Drill to="OPS" onNavigate={onNavigate}>Все задачи · {data.attention_tasks.length}</Drill></div>
        {data.attention_tasks.length === 0 ? <div className="empty small">Активных задач нет.</div> : <div className="attention-table">
          {data.attention_tasks.map((task) => <div className="attention-row" key={task.id}>
            <span className={`priority-pill p-${task.priority}`}>{priority[task.priority] || task.priority}</span>
            <div><strong>{task.title}</strong><small>{taskType[task.type] || task.type}{task.room_code ? ` · номер ${task.room_code}` : ""}</small></div>
            <span>{task.assigned_to || "Не назначено"}</span>
            <span>{task.status}</span>
          </div>)}
        </div>}
      </section>
    </main>
  );
}

function StayList({ items, empty }: { items: StayItem[]; empty: string }) {
  if (items.length === 0) return <div className="empty small">{empty}</div>;
  return <div className="stay-list">{items.map((item) => <div className="stay-row" key={item.id}>
    <div><strong>{item.room_code ? `№ ${item.room_code}` : "Номер не назначен"}</strong><span>{item.booking_number}</span></div>
    <div><b>{item.guest_name || "Гость"}</b>{item.phone && <a href={`tel:${item.phone}`}>{item.phone}</a>}</div>
  </div>)}</div>;
}
