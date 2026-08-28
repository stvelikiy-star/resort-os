"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

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
  reservation_id: string;
  booking_number: string;
  reservation_status: string;
  guest_name?: string | null;
  guest_phone?: string | null;
  service_code: string;
  service_label: string;
  service_date?: string | null;
  service_time?: string | null;
  status: "OPEN" | "IN_PROGRESS" | "DONE" | "CANCELLED";
  priority: "LOW" | "NORMAL" | "HIGH" | "URGENT";
  description?: string | null;
  room_code?: string | null;
  room_type_name?: string | null;
  assigned_to_name?: string | null;
};

type ServiceCode = "TRANSFER" | "MEALS" | "PARKING" | "SAUNA" | "BILLIARDS" | "EXCURSIONS";

const SERVICE_LABELS: Record<ServiceCode, string> = {
  TRANSFER: "🚐 Трансфер",
  MEALS: "🍽 Питание",
  PARKING: "🚗 Парковка",
  SAUNA: "🔥 Сауна",
  BILLIARDS: "🎱 Бильярд",
  EXCURSIONS: "🗺 Экскурсии",
};

const SERVICE_CODES = Object.keys(SERVICE_LABELS) as ServiceCode[];

function localDate() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

function serviceError(body: any, fallback: string) {
  if (typeof body?.detail === "string") return body.detail;
  if (body?.detail?.code === "GUEST_SERVICE_DUPLICATE_ACTIVE") return "Такой активный запрос уже существует для этой брони, даты и времени.";
  if (body?.detail?.code === "GUEST_SERVICE_RESERVATION_NOT_ACTIVE") return "Дополнительную услугу можно создать только для активной гарантированной брони или проживающего гостя.";
  return fallback;
}

export default function PMSGuestServicesV9() {
  const [items, setItems] = useState<ServiceItem[]>([]);
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("ACTIVE");
  const [serviceFilter, setServiceFilter] = useState("ALL");
  const [reservationId, setReservationId] = useState("");
  const [serviceCode, setServiceCode] = useState<ServiceCode>("TRANSFER");
  const [serviceDate, setServiceDate] = useState("");
  const [serviceTime, setServiceTime] = useState("");
  const [priority, setPriority] = useState("NORMAL");
  const [description, setDescription] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const query = new URLSearchParams({ status: statusFilter, limit: "300" });
      if (serviceFilter !== "ALL") query.set("service_code", serviceFilter);
      const [serviceResponse, reservationsResponse] = await Promise.all([
        fetch(`/core/api/v1/admin/guest-services?${query}`, { cache: "no-store" }),
        fetch("/core/api/v1/admin/reception/reservations?limit=500", { cache: "no-store" }),
      ]);
      const serviceBody = await serviceResponse.json().catch(() => ({}));
      const reservationsBody = await reservationsResponse.json().catch(() => ({}));
      if (!serviceResponse.ok) throw new Error(serviceError(serviceBody, "Не удалось загрузить дополнительные услуги"));
      if (!reservationsResponse.ok) throw new Error("Не удалось загрузить активные брони");
      setItems(Array.isArray(serviceBody.items) ? serviceBody.items : []);
      const active = (Array.isArray(reservationsBody.items) ? reservationsBody.items : []).filter((item: Reservation) => ["GUARANTEED", "CHECKED_IN"].includes(item.status));
      setReservations(active);
      if (!reservationId && active.length) setReservationId(active[0].id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Ошибка загрузки сервиса");
    } finally {
      setLoading(false);
    }
  }, [reservationId, serviceFilter, statusFilter]);

  useEffect(() => { void load(); }, [load]);

  const selectedReservation = useMemo(() => reservations.find((item) => item.id === reservationId), [reservations, reservationId]);
  const today = localDate();
  const todayQueue = useMemo(() => items.filter((item) => item.service_date === today), [items, today]);
  const transferQueue = useMemo(() => items.filter((item) => item.service_code === "TRANSFER"), [items]);
  const unstarted = useMemo(() => items.filter((item) => item.status === "OPEN"), [items]);

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
      setNotice(`${SERVICE_LABELS[serviceCode]} · запрос создан без автоматического изменения стоимости проживания.`);
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Ошибка создания запроса");
    } finally {
      setBusy(null);
    }
  }

  async function changeStatus(item: ServiceItem, next: "IN_PROGRESS" | "DONE" | "CANCELLED") {
    setBusy(item.id);
    setError(null);
    setNotice(null);
    try {
      const response = await fetch(`/core/api/v1/ops/tasks/${item.id}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: next }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(serviceError(body, "Не удалось изменить статус услуги"));
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Ошибка статуса услуги");
    } finally {
      setBusy(null);
    }
  }

  return <section className="v9-cockpit" id="guest-services">
    <header className="v9-head">
      <div>
        <p className="eyebrow">PMS V9 · Guest Services</p>
        <h2>Дополнительные услуги по брони</h2>
        <span>Трансфер, питание, парковка, сауна, бильярд и экскурсии привязаны к Reservation. Запрос услуги не меняет цену проживания и не создаёт платёж автоматически.</span>
      </div>
      <div className="v9-actions">
        <select value={serviceFilter} onChange={(event) => setServiceFilter(event.target.value)}>
          <option value="ALL">Все услуги</option>
          {SERVICE_CODES.map((code) => <option key={code} value={code}>{SERVICE_LABELS[code]}</option>)}
        </select>
        <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
          <option value="ACTIVE">Активные</option>
          <option value="OPEN">Новые</option>
          <option value="IN_PROGRESS">В работе</option>
          <option value="DONE">Выполнены</option>
          <option value="CANCELLED">Отменены</option>
          <option value="ALL">Все</option>
        </select>
        <button className="btn" onClick={() => void load()} disabled={loading}>↻ Обновить</button>
      </div>
    </header>

    {error && <div className="v9-error">{error}</div>}
    {notice && <div className="v9-source ok">{notice}</div>}

    <div className="v9-kpis">
      <article><span>Активные услуги</span><strong>{loading ? "…" : items.length}</strong><small>по текущему фильтру</small></article>
      <article><span>Сегодня</span><strong>{loading ? "…" : todayQueue.length}</strong><small>с датой {today}</small></article>
      <article><span>Трансферы</span><strong>{loading ? "…" : transferQueue.length}</strong><small>в текущей очереди</small></article>
      <article className={unstarted.length ? "danger" : "ok"}><span>Не начаты</span><strong>{loading ? "…" : unstarted.length}</strong><small>статус OPEN</small></article>
    </div>

    <div className="v9-grid">
      <section className="v9-card">
        <div className="v9-section-head"><div><strong>Новый запрос гостя</strong><span>Только для GUARANTEED / CHECKED_IN Reservation.</span></div></div>
        <form className="work-actions" onSubmit={createService}>
          <select value={reservationId} onChange={(event) => chooseReservation(event.target.value)} required>
            <option value="">Выберите бронь</option>
            {reservations.map((item) => <option key={item.id} value={item.id}>{item.firstName || "Гость"} · {item.bookingNumber} · № {item.room_code || "—"} · {item.checkIn}→{item.checkOut}</option>)}
          </select>
          <select value={serviceCode} onChange={(event) => setServiceCode(event.target.value as ServiceCode)}>
            {SERVICE_CODES.map((code) => <option key={code} value={code}>{SERVICE_LABELS[code]}</option>)}
          </select>
          <input type="date" value={serviceDate} onChange={(event) => setServiceDate(event.target.value)} />
          <input type="time" value={serviceTime} onChange={(event) => setServiceTime(event.target.value)} />
          <select value={priority} onChange={(event) => setPriority(event.target.value)}>
            <option value="LOW">Низкий</option><option value="NORMAL">Обычный</option><option value="HIGH">Высокий</option><option value="URGENT">Срочно</option>
          </select>
          <input value={description} onChange={(event) => setDescription(event.target.value)} maxLength={2000} placeholder={serviceCode === "TRANSFER" ? "Маршрут, рейс, тип авто, количество гостей…" : "Комментарий / пожелания гостя"} />
          <button className="btn primary" type="submit" disabled={busy === "create" || !reservationId}>{busy === "create" ? "Создаю…" : "Добавить услугу"}</button>
        </form>
        {selectedReservation && <p className="v9-empty">Выбрано: {selectedReservation.firstName || "Гость"} · {selectedReservation.bookingNumber} · {selectedReservation.status}. Цена номера и платежи этим действием не изменяются.</p>}
      </section>

      <section className="v9-card">
        <div className="v9-section-head"><div><strong>Очередь услуг</strong><span>Комната разрешается из актуального сегмента Reservation, поэтому перенос номера не теряет запрос.</span></div><b>{items.length}</b></div>
        <div className="v9-events">
          {items.map((item) => <article className={item.priority === "URGENT" ? "critical" : "arrival"} key={item.id}>
            <div>
              <em>{SERVICE_LABELS[item.service_code as ServiceCode] || item.service_label} · {item.status}</em>
              <strong>{item.guest_name || "Гость"} · {item.booking_number}{item.room_code ? ` · № ${item.room_code}` : ""}</strong>
              <span>{[item.service_date, item.service_time, item.description].filter(Boolean).join(" · ") || "Без дополнительного комментария"}</span>
            </div>
            <div className="v9-row-actions">
              {item.status === "OPEN" && <button disabled={busy === item.id} onClick={() => void changeStatus(item, "IN_PROGRESS")}>В работу</button>}
              {item.status === "IN_PROGRESS" && <button disabled={busy === item.id} onClick={() => void changeStatus(item, "DONE")}>Выполнено</button>}
              {["OPEN", "IN_PROGRESS"].includes(item.status) && <button disabled={busy === item.id} onClick={() => void changeStatus(item, "CANCELLED")}>Отменить</button>}
            </div>
          </article>)}
          {!loading && items.length === 0 && <p className="v9-empty">Запросов по текущему фильтру нет.</p>}
        </div>
      </section>
    </div>
  </section>;
}
