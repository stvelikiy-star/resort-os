"use client";

/**
 * OWNER Command Center — Future Luxury 2.0 reference composition (Admin).
 * Hierarchy: 1) state now (KPI)  2) outlook + what needs attention  3) today's movements + shortcuts
 *            4) fund / money / work detail  5) existing extended Owner analytics (unchanged, passed as children).
 * Data: ONLY the existing /admin/dashboard payload (props) and the existing /admin/intelligence/owner-brief
 * (forward on-books occupancy). Nothing is estimated; missing data shows an honest state.
 */
import { useCallback, useEffect, useState, type ReactNode } from "react";
import { ArrowRight, Banknote, BedDouble, Bot, CalendarCheck, ClipboardCheck, ConciergeBell, Inbox, LayoutGrid, LogOut, MessagesSquare, RefreshCw, Wrench } from "lucide-react";
import type { Dashboard, DashboardDestination } from "../DashboardBoard";
import { AreaChart, Badge, Card, ErrorBox, Kpi, Meter, Ring, Skeleton, StackedBar } from "./Fl2";

const money = (value: number) => `${new Intl.NumberFormat("ru-RU").format(value)} сом`;
const taskType: Record<string, string> = { HOUSEKEEPING: "Уборка", MAINTENANCE: "Ремонт", GUEST_REQUEST: "Запрос гостя" };
const priorityLabel: Record<string, string> = { URGENT: "Срочно", HIGH: "Высокий", NORMAL: "Обычный", LOW: "Низкий" };
const priorityTone = (p: string) => (p === "URGENT" ? "danger" : p === "HIGH" ? "warning" : "neutral") as "danger" | "warning" | "neutral";
const shortDate = (iso: string) => { const [, m, d] = iso.split("-"); return `${d}.${m}`; };

function waitingLabel(seconds: number) {
  if (seconds <= 0) return "—";
  if (seconds < 60) return `${seconds} сек`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)} мин`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} ч ${Math.floor((seconds % 3600) / 60)} мин`;
  return `${Math.floor(seconds / 86400)} д ${Math.floor((seconds % 86400) / 3600)} ч`;
}

type Forward = { daily: Array<{ date: string; occupancy_on_books_percent: number }> };
type ForwardState = { status: "loading" } | { status: "error"; message: string } | { status: "ready"; daily: Forward["daily"] };

/** Reads the existing owner-brief endpoint (same one Owner Control V2 uses). */
function useForwardOccupancy(): [ForwardState, () => void] {
  const [state, setState] = useState<ForwardState>({ status: "loading" });
  const load = useCallback(async () => {
    setState({ status: "loading" });
    try {
      const response = await fetch("/core/api/v1/admin/intelligence/owner-brief?horizon_days=30", { cache: "no-store" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Не удалось загрузить загрузку на 30 дней");
      const daily = (body as { forward?: Forward }).forward?.daily;
      setState({ status: "ready", daily: Array.isArray(daily) ? daily : [] });
    } catch (e) {
      setState({ status: "error", message: e instanceof Error ? e.message : "Ошибка загрузки" });
    }
  }, []);
  useEffect(() => { void load(); }, [load]);
  return [state, load];
}

function Drill({ to, onNavigate, children }: { to: DashboardDestination; onNavigate?: (tab: DashboardDestination) => void; children: ReactNode }) {
  if (!onNavigate) return null;
  return <button className="mx-link" onClick={() => onNavigate(to)}>{children}<ArrowRight size={16} aria-hidden="true" /></button>;
}

function Stays({ items, empty }: { items: Dashboard["today"]["arrivals"]; empty: string }) {
  if (items.length === 0) return <div className="mx-empty">{empty}</div>;
  return <ul className="mx-rows">{items.map((s) => <li className="mx-row" key={s.id}>
    <div><strong>{s.room_code ? `№ ${s.room_code}` : "Номер не назначен"}</strong><small>{s.booking_number}</small></div>
    <div style={{ textAlign: "right" }}><strong>{s.guest_name || "Гость"}</strong>{s.phone && <a className="mx-sub" href={`tel:${s.phone}`}>{s.phone}</a>}</div>
  </li>)}</ul>;
}

export function OwnerCommandCenterSkeleton() {
  return <main className="work-shell dashboard-shell"><div className="mx-page"><Skeleton /></div></main>;
}
export function OwnerCommandCenterError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return <main className="work-shell dashboard-shell"><div className="mx-page"><ErrorBox message={message} onRetry={onRetry} /></div></main>;
}

export default function OwnerCommandCenter({ data, onNavigate, onRefresh, children }: {
  data: Dashboard; onNavigate?: (tab: DashboardDestination) => void; onRefresh: () => void; children?: ReactNode;
}) {
  const [forward, reloadForward] = useForwardOccupancy();
  const occupancy = Number.isFinite(data.stays.occupancy_percent) ? Math.max(0, Math.min(100, data.stays.occupancy_percent)) : 0;
  const attention = data.rooms.dirty + data.rooms.in_inspection + data.rooms.tech_block;
  const total = data.finance.active_reservations_total_kgs;
  const paidShare = total > 0 ? (data.finance.active_reservations_paid_kgs / total) * 100 : 0;
  const rooms = [
    { name: "Готовы", value: data.rooms.clean, color: "var(--mx-success)" },
    { name: "Нужна уборка", value: data.rooms.dirty, color: "var(--mx-warning)" },
    { name: "На проверке", value: data.rooms.in_inspection, color: "var(--mx-info)" },
    { name: "Тех. блокировка", value: data.rooms.tech_block, color: "var(--mx-danger)" },
    { name: "Статус не указан", value: data.rooms.unknown, color: "var(--mx-muted)" },
  ];
  const quick: Array<{ to: DashboardDestination; label: string; icon: typeof LayoutGrid }> = [
    { to: "PMS", label: "Шахматка", icon: LayoutGrid },
    { to: "RESERVATIONS", label: "Ресепшен", icon: ConciergeBell },
    { to: "REQUESTS", label: "Заявки", icon: ClipboardCheck },
    { to: "FINANCE", label: "Финансы", icon: Banknote },
    { to: "OPS", label: "Задачи", icon: Wrench },
    { to: "INBOX", label: "Входящие", icon: Inbox },
    { to: "WHATSAPP", label: "WhatsApp / AI", icon: Bot },
  ];

  return (
    <main className="work-shell dashboard-shell" data-fl2-owner="true">
      <div className="mx-page">
        <header className="mx-hero mx-reveal">
          <div>
            <p className="mx-eyebrow">{data.property.name} · управление</p>
            <h1>Command Center</h1>
            <p>{data.property.local_date} · {data.property.timezone} · данные из Core в момент обновления</p>
          </div>
          <button className="mx-btn mx-btn--primary" onClick={onRefresh}><RefreshCw size={18} aria-hidden="true" />Обновить</button>
        </header>

        <div className="mx-grid" role="region" aria-label="Ключевые показатели">
          <Kpi icon={BedDouble} label="Загрузка сейчас" value={`${data.stays.occupancy_percent}%`} hint={`${data.stays.occupied_rooms} из ${data.rooms.total} номеров`} span={6} i={1}>
            <div style={{ marginTop: 14 }}><Meter percent={occupancy} label="Загрузка сейчас" /></div>
          </Kpi>
          <Kpi icon={CalendarCheck} label="Заезды сегодня" value={data.stays.arrivals_today} hint="гарантированные брони" span={3} i={2} />
          <Kpi icon={LogOut} label="Выезды сегодня" value={data.stays.departures_today} hint="проживающие гости" span={3} i={3} />
          <Kpi icon={Banknote} label="Платежи сегодня" value={money(data.finance.confirmed_payments_today_kgs)} hint="только записанные менеджером" span={4} i={4} full />
          <Kpi icon={MessagesSquare} label="Сообщения ждут" value={data.communications.needs_reply} hint={`самое долгое: ${waitingLabel(data.communications.oldest_waiting_seconds)}`} tone={data.communications.needs_reply > 0 ? "warning" : undefined} span={4} i={5} />
          <Kpi icon={Wrench} label="Номера требуют внимания" value={attention} hint="уборка / проверка / ремонт" tone={attention > 0 ? "warning" : undefined} span={4} i={6} />
        </div>

        <div className="mx-grid">
          <Card span={8} i={7} eyebrow="Брони на книгах" title="Загрузка на 30 дней вперёд" action={<Drill to="PMS" onNavigate={onNavigate}>Шахматка</Drill>}>
            {forward.status === "loading" && <div className="mx-skel" aria-busy="true" style={{ minHeight: 200 }} />}
            {forward.status === "error" && <ErrorBox message={forward.message} onRetry={reloadForward} />}
            {forward.status === "ready" && (forward.daily.length === 0
              ? <div className="mx-empty">Данных on-books по датам нет.</div>
              : <AreaChart ariaLabel={`Загрузка по броням на ${forward.daily.length} дней вперёд, от ${Math.min(...forward.daily.map((d) => d.occupancy_on_books_percent)).toFixed(1)}% до ${Math.max(...forward.daily.map((d) => d.occupancy_on_books_percent)).toFixed(1)}%`}
                  points={forward.daily.map((d) => ({ label: shortDate(d.date), y: d.occupancy_on_books_percent }))} />)}
            <p className="mx-note">Текущие брони и доступность, не прогноз спроса.</p>
          </Card>

          <Card span={4} i={8} eyebrow="Контроль" title="Требует внимания" action={<Drill to="OPS" onNavigate={onNavigate}>Все · {data.attention_tasks.length}</Drill>}>
            {data.attention_tasks.length === 0
              ? <div className="mx-empty">Активных задач нет.</div>
              : <ul className="mx-rows">{data.attention_tasks.map((t) => <li className="mx-row" key={t.id}>
                <div><strong>{t.title}</strong><small>{taskType[t.type] || t.type}{t.room_code ? ` · номер ${t.room_code}` : ""} · {t.assigned_to || "Не назначено"}</small></div>
                <Badge tone={priorityTone(t.priority)}>{priorityLabel[t.priority] || t.priority}</Badge>
              </li>)}</ul>}
            {data.tasks.urgent_active > 0 && <p className="mx-note" style={{ color: "var(--mx-danger)" }}>Срочных активных задач: {data.tasks.urgent_active}</p>}
          </Card>
        </div>

        <div className="mx-grid">
          <Card span={4} i={9} eyebrow="Сегодня" title="Заезды" action={<Drill to="RESERVATIONS" onNavigate={onNavigate}>Ресепшен · {data.today.arrivals.length}</Drill>}>
            <Stays items={data.today.arrivals} empty="Заездов по текущим данным нет." />
          </Card>
          <Card span={4} i={10} eyebrow="Сегодня" title="Выезды" action={<Drill to="RESERVATIONS" onNavigate={onNavigate}>Ресепшен · {data.today.departures.length}</Drill>}>
            <Stays items={data.today.departures} empty="Выездов по текущим данным нет." />
          </Card>
          <Card span={4} i={11} eyebrow="Навигация" title="Быстрые переходы">
            <div className="mx-quick">
              {quick.map(({ to, label, icon: Icon }) => <button key={to} className="mx-tile" onClick={() => onNavigate?.(to)} disabled={!onNavigate}><Icon size={20} aria-hidden="true" />{label}</button>)}
            </div>
          </Card>
        </div>

        <div className="mx-grid">
          <Card span={4} i={12} eyebrow="Номерной фонд" title={`${data.rooms.total} номеров · состояние`} action={<Drill to="PMS" onNavigate={onNavigate}>Шахматка</Drill>}>
            <div style={{ display: "flex", alignItems: "center", gap: 18, flexWrap: "wrap" }}>
              <Ring percent={occupancy} caption="Загрузка" />
              <ul className="mx-legend" style={{ flex: "1 1 150px" }}>
                {rooms.map((r) => <li key={r.name}><span><i className="mx-dot" style={{ "--c": r.color } as React.CSSProperties} />{r.name}</span><b>{r.value}</b></li>)}
              </ul>
            </div>
            <div style={{ marginTop: 16 }}><StackedBar label="Состояние номерного фонда" segments={rooms} /></div>
            <p className="mx-note">Физическое состояние номера не подменяет коммерческую занятость.</p>
          </Card>

          <Card span={4} i={13} eyebrow="Внутренний контроль" title="Активные брони · деньги" action={<Drill to="FINANCE" onNavigate={onNavigate}>Финансы</Drill>}>
            <ul className="mx-rows">
              <li className="mx-row"><div><small>Стоимость</small></div><b>{money(total)}</b></li>
              <li className="mx-row"><div><small>Записано оплат</small></div><b style={{ color: "var(--mx-success)" }}>{money(data.finance.active_reservations_paid_kgs)}</b></li>
              <li className="mx-row"><div><small>Остаток</small></div><b style={{ color: data.finance.active_reservations_remaining_kgs > 0 ? "var(--mx-warning)" : undefined }}>{money(data.finance.active_reservations_remaining_kgs)}</b></li>
            </ul>
            {total > 0 && <div style={{ marginTop: 14 }}><Meter percent={paidShare} label="Доля записанных оплат от стоимости активных броней" /></div>}
            <p className="mx-note">Только внутренние manager-confirmed факты. Это не бухгалтерская прибыль и не revenue-recognition отчёт.</p>
          </Card>

          <Card span={4} i={14} eyebrow="Бронирование и работа" title="Заявки · диалоги · задачи" action={<Drill to="REQUESTS" onNavigate={onNavigate}>Заявки · {data.requests.active}</Drill>}>
            <ul className="mx-rows">
              <li className="mx-row"><div><small>Новые заявки</small></div><b>{data.requests.new}</b></li>
              <li className="mx-row"><div><small>Рассчитаны</small></div><b>{data.requests.quoted}</b></li>
              <li className="mx-row"><div><small>Ждут решения/предоплаты менеджера</small></div><b>{data.requests.awaiting_prepayment}</b></li>
              <li className="mx-row"><div><small>Гарантированные будущие · проживают</small></div><b>{data.stays.guaranteed} · {data.stays.in_house}</b></li>
              <li className="mx-row"><div><small>Диалоги активные · нужен ответ</small></div><b>{data.communications.active} · {data.communications.needs_reply}</b></li>
              <li className="mx-row"><div><small>Уборка · ремонт · запросы гостей</small></div><b>{data.tasks.housekeeping_active} · {data.tasks.maintenance_active} · {data.tasks.guest_requests_active}</b></li>
            </ul>
            <p className="mx-note">Клиентские каналы V1 ведёт n8n; SLA-порог не выдумывается.</p>
          </Card>
        </div>

        {children}
      </div>
    </main>
  );
}
