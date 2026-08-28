"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type DashboardResponse = {
  stays?: {
    arrivals_today?: number;
    departures_today?: number;
    in_house?: number;
    guaranteed?: number;
    occupancy_percent?: number;
  };
  requests?: { active?: number; awaiting_prepayment?: number };
  tasks?: { guest_requests_active?: number; urgent_active?: number };
  communications?: { needs_reply?: number };
  finance?: { confirmed_payments_today_kgs?: number; active_reservations_remaining_kgs?: number };
  rooms?: { total?: number; clean?: number; dirty?: number; in_inspection?: number; tech_block?: number };
};

type GuestService = {
  id: string;
  status: string;
  priority: string;
  service_code: string;
};

type Reservation = {
  id: string;
  status: string;
  remainingKgs?: number;
};

type LoadState = "loading" | "ready" | "partial" | "error";

function money(value: number) {
  return new Intl.NumberFormat("ru-RU").format(value || 0);
}

function scrollToSelector(selector: string) {
  if (typeof document === "undefined") return;
  document.querySelector(selector)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

export default function PMSIntegrationRailV10() {
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [services, setServices] = useState<GuestService[]>([]);
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [servicesComplete, setServicesComplete] = useState(false);
  const [reservationsComplete, setReservationsComplete] = useState(false);
  const [state, setState] = useState<LoadState>("loading");
  const [updatedAt, setUpdatedAt] = useState<string>("");

  const load = useCallback(async () => {
    setState("loading");
    try {
      const [dashboardResponse, servicesResponse, reservationsResponse] = await Promise.all([
        fetch("/core/api/v1/admin/dashboard", { cache: "no-store" }),
        fetch("/core/api/v1/admin/guest-services?status=ACTIVE&limit=300", { cache: "no-store" }),
        fetch("/core/api/v1/admin/reception/reservations?limit=500", { cache: "no-store" }),
      ]);

      const dashboardBody = await dashboardResponse.json().catch(() => ({}));
      const servicesBody = await servicesResponse.json().catch(() => ({}));
      const reservationsBody = await reservationsResponse.json().catch(() => ({}));

      if (!dashboardResponse.ok) throw new Error("dashboard");

      const serviceItems = servicesResponse.ok && Array.isArray(servicesBody.items) ? servicesBody.items : [];
      const reservationItems = reservationsResponse.ok && Array.isArray(reservationsBody.items) ? reservationsBody.items : [];
      const servicesOk = servicesResponse.ok && serviceItems.length < 300;
      const reservationsOk = reservationsResponse.ok && reservationItems.length < 500;

      setDashboard(dashboardBody as DashboardResponse);
      setServices(serviceItems);
      setReservations(reservationItems);
      setServicesComplete(servicesOk);
      setReservationsComplete(reservationsOk);
      setState(servicesOk && reservationsOk ? "ready" : "partial");
      setUpdatedAt(new Date().toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" }));
    } catch {
      setState("error");
      setDashboard(null);
      setServices([]);
      setReservations([]);
      setServicesComplete(false);
      setReservationsComplete(false);
    }
  }, []);

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(), 60000);
    return () => window.clearInterval(timer);
  }, [load]);

  const activeReservations = useMemo(
    () => reservations.filter((item) => ["GUARANTEED", "CHECKED_IN"].includes(item.status)).length,
    [reservations],
  );
  const debtReservations = useMemo(
    () =>
      reservations.filter(
        (item) => ["GUARANTEED", "CHECKED_IN"].includes(item.status) && Number(item.remainingKgs || 0) > 0,
      ).length,
    [reservations],
  );
  const urgentServices = useMemo(
    () => services.filter((item) => item.priority === "URGENT" && ["OPEN", "IN_PROGRESS"].includes(item.status)).length,
    [services],
  );
  const roomAttention =
    Number(dashboard?.rooms?.dirty || 0) +
    Number(dashboard?.rooms?.in_inspection || 0) +
    Number(dashboard?.rooms?.tech_block || 0);

  return (
    <section className="v9-cockpit" id="pms-v10-control">
      <header className="v9-head">
        <div>
          <p className="eyebrow">PMS V10 · Unified Control</p>
          <h2>Сайт → Core → бронь → проживание → услуги → финансы</h2>
          <span>
            Единая рабочая цепочка Resort OS. Сайт создаёт ReservationRequest, подтверждение брони остаётся за менеджером,
            а шахматка и операционные модули читают фактическое состояние из Resort Core/PostgreSQL.
          </span>
        </div>
        <div className="v9-actions">
          <span className={`v9-source ${state === "ready" ? "ok" : state === "error" ? "bad" : ""}`}>
            {state === "loading" ? "Обновление…" : state === "ready" ? `Core complete · ${updatedAt}` : state === "partial" ? "Core partial · часть счётчиков скрыта" : "Core unavailable"}
          </span>
          <button className="btn" onClick={() => void load()} disabled={state === "loading"}>↻ Обновить всё</button>
        </div>
      </header>

      <div className="v9-kpis">
        <article><span>Заявки</span><strong>{state === "loading" ? "…" : dashboard?.requests?.active ?? "—"}</strong><small>ReservationRequest · ещё не бронь</small></article>
        <article><span>Активные брони</span><strong>{state === "loading" ? "…" : reservationsComplete ? activeReservations : "—"}</strong><small>{reservationsComplete ? "GUARANTEED + CHECKED_IN" : "неполная выборка — fail closed"}</small></article>
        <article><span>Услуги гостей</span><strong>{state === "loading" ? "…" : servicesComplete ? services.length : "—"}</strong><small>{servicesComplete ? (urgentServices ? `срочных: ${urgentServices}` : "без срочных") : "неполная выборка — fail closed"}</small></article>
        <article className={reservationsComplete && debtReservations ? "danger" : reservationsComplete ? "ok" : ""}><span>С остатком</span><strong>{state === "loading" ? "…" : reservationsComplete ? debtReservations : "—"}</strong><small>{reservationsComplete ? "активные брони с долгом" : "финансовый счётчик скрыт"}</small></article>
      </div>

      <div className="v9-actions" style={{ marginTop: 12, flexWrap: "wrap" }}>
        <button className="btn" onClick={() => scrollToSelector("#pms-v10-control + .v9-cockpit")}>Ресепшен / сегодня</button>
        <button className="btn" onClick={() => scrollToSelector("#guest-services")}>Услуги гостей</button>
        <button className="btn" onClick={() => scrollToSelector(".v9-bulk")}>Массовые операции</button>
        <button className="btn primary" onClick={() => scrollToSelector(".v8-board")}>Открыть шахматку</button>
      </div>

      <p className="v9-empty" style={{ marginTop: 12 }}>
        Платежи сегодня: {money(Number(dashboard?.finance?.confirmed_payments_today_kgs || 0))} KGS · Заезды: {dashboard?.stays?.arrivals_today ?? "—"} · Выезды: {dashboard?.stays?.departures_today ?? "—"} · Сообщения без ответа: {dashboard?.communications?.needs_reply ?? "—"} · Номера требуют внимания: {roomAttention}.
      </p>
    </section>
  );
}
