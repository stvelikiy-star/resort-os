"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type UserContext = { id: string; role: string };

type Reservation = {
  id: string;
  bookingNumber: string;
  status: string;
  checkIn: string;
  checkOut: string;
  firstName?: string | null;
  phone?: string | null;
  room_code?: string | null;
  room_type_name?: string | null;
};

type ServiceItem = {
  id: string;
  reservation_id?: string | null;
  stay_id?: string | null;
  booking_number?: string | null;
  reservation_status?: string | null;
  guest_name?: string | null;
  guest_phone?: string | null;
  service_code: ServiceCode;
  service_label: string;
  service_date?: string | null;
  service_time?: string | null;
  status: "OPEN" | "IN_PROGRESS" | "DONE" | "CANCELLED";
  priority: "LOW" | "NORMAL" | "HIGH" | "URGENT";
  description?: string | null;
  room_code?: string | null;
  room_type_name?: string | null;
  assigned_to_id?: string | null;
  assigned_to_name?: string | null;
  source?: string | null;
};

type ServiceCode =
  | "HOUSEKEEPING"
  | "TOWELS"
  | "LINEN"
  | "MAINTENANCE"
  | "TRANSFER"
  | "MEALS"
  | "PARKING"
  | "SAUNA"
  | "BILLIARDS"
  | "EXCURSIONS"
  | "ADMIN";

const SERVICE_LABELS: Record<ServiceCode, string> = {
  HOUSEKEEPING: "🧹 Уборка в проживании",
  TOWELS: "🧺 Полотенца",
  LINEN: "🛏 Бельё",
  MAINTENANCE: "🛠 Ремонт / неисправность",
  TRANSFER: "🚐 Трансфер",
  MEALS: "🍽 Питание",
  PARKING: "🚗 Парковка",
  SAUNA: "🔥 Сауна",
  BILLIARDS: "🎱 Бильярд",
  EXCURSIONS: "🗺 Экскурсии",
  ADMIN: "🛎 Администратор",
};

const ROUTE_LABELS: Record<ServiceCode, string> = {
  HOUSEKEEPING: "Горничные",
  TOWELS: "Горничные",
  LINEN: "Горничные",
  MAINTENANCE: "Техник",
  TRANSFER: "Ресепшен",
  MEALS: "Питание",
  PARKING: "Ресепшен",
  SAUNA: "Ресепшен",
  BILLIARDS: "Ресепшен",
  EXCURSIONS: "Ресепшен",
  ADMIN: "Ресепшен",
};

const RECEPTION_CODES = new Set<ServiceCode>(["TRANSFER", "PARKING", "SAUNA", "BILLIARDS", "EXCURSIONS", "ADMIN"]);
const SERVICE_CODES = Object.keys(SERVICE_LABELS) as ServiceCode[];

function localDate() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

function serviceError(body: any, fallback: string) {
  if (typeof body?.detail === "string") return body.detail;
  const code = body?.detail?.code;
  if (code === "GUEST_SERVICE_DUPLICATE_ACTIVE") return "Такой активный запрос уже существует для этой брони, даты и времени.";
  if (code === "GUEST_SERVICE_RESERVATION_NOT_ACTIVE") return "Запрос можно создать только для GUARANTEED / CHECKED_IN брони.";
  if (code === "GUEST_REQUEST_NOT_CLAIMABLE") return "Запрос уже нельзя взять в работу.";
  if (code === "GUEST_REQUEST_NOT_IN_PROGRESS") return "Сначала запрос должен быть взят в работу.";
  if (code === "GUEST_REQUEST_NOT_CANCELLABLE") return "Запрос уже нельзя отменить.";
  return fallback;
}

export default function GuestServicesCenter({ user }: { user: UserContext }) {
  const [items, setItems] = useState<ServiceItem[]>([]);
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [statusFilter, setStatusFilter] = useState("ACTIVE");
  const [serviceFilter, setServiceFilter] = useState("ALL");
  const [priorityFilter, setPriorityFilter] = useState("ALL");
  const [guestFilter, setGuestFilter] = useState("");
  const [roomFilter, setRoomFilter] = useState("");
  const [assigneeFilter, setAssigneeFilter] = useState("");

  const [reservationId, setReservationId] = useState("");
  const [serviceCode, setServiceCode] = useState<ServiceCode>("TOWELS");
  const [serviceDate, setServiceDate] = useState("");
  const [serviceTime, setServiceTime] = useState("");
  const [priority, setPriority] = useState("NORMAL");
  const [description, setDescription] = useState("");

  const isManager = ["OWNER", "MANAGER"].includes(user.role);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const query = new URLSearchParams({ status: statusFilter, limit: "500" });
      if (serviceFilter !== "ALL") query.set("service_code", serviceFilter);
      if (priorityFilter !== "ALL") query.set("priority", priorityFilter);
      if (guestFilter.trim()) query.set("guest", guestFilter.trim());
      if (roomFilter.trim()) query.set("room", roomFilter.trim());
      if (assigneeFilter.trim()) query.set("assignee", assigneeFilter.trim());

      const [serviceResponse, reservationsResponse] = await Promise.all([
        fetch(`/core/api/v1/admin/guest-services?${query}`, { cache: "no-store" }),
        fetch("/core/api/v1/admin/reception/reservations?limit=500", { cache: "no-store" }),
      ]);
      const serviceBody = await serviceResponse.json().catch(() => ({}));
      const reservationsBody = await reservationsResponse.json().catch(() => ({}));
      if (!serviceResponse.ok) throw new Error(serviceError(serviceBody, "Не удалось загрузить Guest Services Center"));
      if (!reservationsResponse.ok) throw new Error("Не удалось загрузить активные брони");

      setItems(Array.isArray(serviceBody.items) ? serviceBody.items : []);
      const active = (Array.isArray(reservationsBody.items) ? reservationsBody.items : []).filter((item: Reservation) =>
        ["GUARANTEED", "CHECKED_IN"].includes(item.status),
      );
      setReservations(active);
      setReservationId((current) => current || active[0]?.id || "");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Ошибка загрузки Guest Services Center");
    } finally {
      setLoading(false);
    }
  }, [assigneeFilter, guestFilter, priorityFilter, roomFilter, serviceFilter, statusFilter]);

  useEffect(() => { void load(); }, [load]);

  const selectedReservation = useMemo(() => reservations.find((item) => item.id === reservationId), [reservations, reservationId]);
  const today = localDate();
  const todayQueue = useMemo(() => items.filter((item) => item.service_date === today), [items, today]);
  const urgentQueue = useMemo(() => items.filter((item) => item.priority === "URGENT" && ["OPEN", "IN_PROGRESS"].includes(item.status)), [items]);
  const unassigned = useMemo(() => items.filter((item) => item.status === "OPEN" && !item.assigned_to_id), [items]);
  const activeCount = useMemo(() => items.filter((item) => ["OPEN", "IN_PROGRESS"].includes(item.status)).length, [items]);

  function canOperate(item: ServiceItem) {
    if (isManager) return true;
    return user.role === "RECEPTION" && RECEPTION_CODES.has(item.service_code);
  }

  function canFinish(item: ServiceItem) {
    if (isManager) return true;
    return canOperate(item) && item.assigned_to_id === user.id;
  }

  function chooseReservation(value: string) {
    setReservationId(value);
    const reservation = reservations.find((item) => item.id === value);
    if (reservation && !serviceDate) setServiceDate(reservation.checkIn);
  }

  async function createService(event: FormEvent) {
    event.preventDefault();
    if (!reservationId) return;
    setBusy("create");
    setError(null);
    setNotice(null);
    try {
      const response = await fetch("/core/api/v1/admin/guest-services", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          reservation_id: reservationId,
          service_code: serviceCode,
          service_date: serviceDate || null,
          service_time: serviceTime || null,
          priority,
          description: description.trim() || null,
        }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(serviceError(body, "Не удалось создать запрос гостя"));
      setDescription("");
      setServiceTime("");
      setNotice(`${SERVICE_LABELS[serviceCode]} · создано в единой очереди. Маршрут: ${ROUTE_LABELS[serviceCode]}. Стоимость проживания и платежи не изменены.`);
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Ошибка создания запроса");
    } finally {
      setBusy(null);
    }
  }

  async function lifecycle(item: ServiceItem, action: "claim" | "complete" | "cancel") {
    setBusy(item.id);
    setError(null);
    setNotice(null);
    try {
      const response = await fetch(`/core/api/v1/ops/guest-requests/${item.id}/${action}`, { method: "POST" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(serviceError(body, "Не удалось изменить статус запроса"));
      setNotice(`${SERVICE_LABELS[item.service_code]} · ${action === "claim" ? "в работе" : action === "complete" ? "выполнено" : "отменено"}.`);
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Ошибка статуса запроса");
    } finally {
      setBusy(null);
    }
  }

  return <section className="v9-cockpit" id="guest-services-center">
    <header className="v9-head">
      <div>
        <p className="eyebrow">Resort Core · Guest Services Center</p>
        <h2>Единый центр сервиса гостя</h2>
        <span>Одна очередь для Guest OS, PMS и ресепшена. Исполнитель определяется типом услуги. Запрос не меняет цену проживания, Payment или физический статус номера автоматически.</span>
      </div>
      <div className="v9-actions">
        <button className="btn" onClick={() => void load()} disabled={loading}>↻ Обновить</button>
      </div>
    </header>

    {error && <div className="v9-error">{error}</div>}
    {notice && <div className="v9-source ok">{notice}</div>}

    <div className="v9-kpis">
      <article><span>Активные</span><strong>{loading ? "…" : activeCount}</strong><small>OPEN + IN_PROGRESS</small></article>
      <article className={urgentQueue.length ? "danger" : "ok"}><span>Срочно</span><strong>{loading ? "…" : urgentQueue.length}</strong><small>URGENT в активной очереди</small></article>
      <article><span>Сегодня</span><strong>{loading ? "…" : todayQueue.length}</strong><small>{today}</small></article>
      <article className={unassigned.length ? "danger" : "ok"}><span>Без исполнителя</span><strong>{loading ? "…" : unassigned.length}</strong><small>новые запросы</small></article>
    </div>

    <section className="v9-card">
      <div className="v9-section-head"><div><strong>Фильтр очереди</strong><span>По фактическим данным Resort Core.</span></div></div>
      <div className="work-actions">
        <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
          <option value="ACTIVE">Активные</option><option value="OPEN">Новые</option><option value="IN_PROGRESS">В работе</option>
          <option value="DONE">Выполнены</option><option value="CANCELLED">Отменены</option><option value="ALL">Все</option>
        </select>
        <select value={serviceFilter} onChange={(event) => setServiceFilter(event.target.value)}>
          <option value="ALL">Все типы</option>{SERVICE_CODES.map((code) => <option key={code} value={code}>{SERVICE_LABELS[code]}</option>)}
        </select>
        <select value={priorityFilter} onChange={(event) => setPriorityFilter(event.target.value)}>
          <option value="ALL">Любой приоритет</option><option value="URGENT">Срочно</option><option value="HIGH">Высокий</option><option value="NORMAL">Обычный</option><option value="LOW">Низкий</option>
        </select>
        <input value={guestFilter} onChange={(event) => setGuestFilter(event.target.value)} placeholder="Гость / телефон / бронь" />
        <input value={roomFilter} onChange={(event) => setRoomFilter(event.target.value)} placeholder="Номер" />
        <input value={assigneeFilter} onChange={(event) => setAssigneeFilter(event.target.value)} placeholder="Исполнитель" />
      </div>
    </section>

    <div className="v9-grid">
      <section className="v9-card">
        <div className="v9-section-head"><div><strong>Новый запрос</strong><span>Ресепшен может принять любую просьбу и отправить её нужной роли.</span></div></div>
        <form className="work-actions" onSubmit={createService}>
          <select value={reservationId} onChange={(event) => chooseReservation(event.target.value)} required>
            <option value="">Выберите бронь</option>
            {reservations.map((item) => <option key={item.id} value={item.id}>{item.firstName || "Гость"} · {item.bookingNumber} · № {item.room_code || "—"} · {item.status}</option>)}
          </select>
          <select value={serviceCode} onChange={(event) => setServiceCode(event.target.value as ServiceCode)}>
            {SERVICE_CODES.map((code) => <option key={code} value={code}>{SERVICE_LABELS[code]} → {ROUTE_LABELS[code]}</option>)}
          </select>
          <input type="date" value={serviceDate} onChange={(event) => setServiceDate(event.target.value)} />
          <input type="time" value={serviceTime} onChange={(event) => setServiceTime(event.target.value)} />
          <select value={priority} onChange={(event) => setPriority(event.target.value)}>
            <option value="LOW">Низкий</option><option value="NORMAL">Обычный</option><option value="HIGH">Высокий</option><option value="URGENT">Срочно</option>
          </select>
          <input value={description} onChange={(event) => setDescription(event.target.value)} maxLength={2000} placeholder="Что нужно гостю / детали / маршрут / неисправность…" />
          <button className="btn primary" type="submit" disabled={busy === "create" || !reservationId}>{busy === "create" ? "Создаю…" : "Создать запрос"}</button>
        </form>
        {selectedReservation && <p className="v9-empty">{selectedReservation.firstName || "Гость"} · {selectedReservation.bookingNumber} · {selectedReservation.status}. Финансовый эффект: NONE_AUTOMATIC.</p>}
      </section>

      <section className="v9-card">
        <div className="v9-section-head"><div><strong>Операционная очередь</strong><span>Канал создания не влияет на маршрутизацию.</span></div><b>{items.length}</b></div>
        <div className="v9-events">
          {items.map((item) => {
            const operable = canOperate(item);
            const finishable = canFinish(item);
            return <article className={item.priority === "URGENT" ? "critical" : "arrival"} key={item.id}>
              <div>
                <em>{SERVICE_LABELS[item.service_code] || item.service_label} · {item.status} · {item.priority}</em>
                <strong>{item.guest_name || "Гость"}{item.booking_number ? ` · ${item.booking_number}` : ""}{item.room_code ? ` · № ${item.room_code}` : ""}</strong>
                <span>{[item.service_date, item.service_time, item.description].filter(Boolean).join(" · ") || "Без комментария"}</span>
                <small>Маршрут: {ROUTE_LABELS[item.service_code] || "Менеджер"} · Источник: {item.source || "CORE"} · Исполнитель: {item.assigned_to_name || "не назначен"}</small>
              </div>
              <div className="v9-row-actions">
                {item.status === "OPEN" && operable && !item.assigned_to_id && <button disabled={busy === item.id} onClick={() => void lifecycle(item, "claim")}>В работу</button>}
                {item.status === "IN_PROGRESS" && finishable && <button disabled={busy === item.id} onClick={() => void lifecycle(item, "complete")}>Выполнено</button>}
                {["OPEN", "IN_PROGRESS"].includes(item.status) && (isManager || finishable || (!item.assigned_to_id && operable)) && <button disabled={busy === item.id} onClick={() => void lifecycle(item, "cancel")}>Отменить</button>}
                {!operable && ["OPEN", "IN_PROGRESS"].includes(item.status) && <span>Исполняет: {ROUTE_LABELS[item.service_code]}</span>}
              </div>
            </article>;
          })}
          {!loading && items.length === 0 && <p className="v9-empty">Запросов по текущему фильтру нет.</p>}
        </div>
      </section>
    </div>
  </section>;
}
