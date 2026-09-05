"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import GuestCrmEnrichmentPanel from "./GuestCrmEnrichmentPanel";

type GuestSummary = {
  id: string;
  name: string;
  phone?: string | null;
  email?: string | null;
  reservation_count: number;
  completed_stays: number;
  total_nights: number;
  booked_value_kgs: number;
  received_kgs: number;
  last_stay?: string | null;
  next_stay?: string | null;
  latest_source?: string | null;
};

type GuestListResponse = {
  items: GuestSummary[];
  total_profiles: number;
  offset: number;
  limit: number;
  truth: string;
};

type GuestReservation = {
  id: string;
  booking_number: string;
  status: string;
  check_in: string;
  check_out: string;
  adults: number;
  children: number;
  total_kgs: number;
  paid_kgs: number;
  outstanding_kgs: number;
  source?: string | null;
  notes?: string | null;
  schedule: Array<{ start: string; end: string; room_code: string; room_type_name: string }>;
  services: Array<{
    id: string;
    service_code?: string | null;
    service_date?: string | null;
    service_time?: string | null;
    status: string;
    priority: string;
    title: string;
    description?: string | null;
  }>;
  payments: Array<{
    id: string;
    amount_kgs: number;
    method: string;
    status: string;
    provider?: string | null;
    paid_at?: string | null;
  }>;
};

type GuestDetail = {
  guest: { id: string; name: string; phone?: string | null; email?: string | null; created_at: string; updated_at: string };
  lifetime: {
    reservation_count: number;
    completed_stays: number;
    total_nights: number;
    booked_value_kgs: number;
    received_kgs: number;
  };
  reservations: GuestReservation[];
  conversations: Array<{
    id: string;
    status: string;
    request_id?: string | null;
    channel_kind: string;
    channel_name: string;
    message_count: number;
    last_inbound_at?: string | null;
    last_outbound_at?: string | null;
  }>;
  truth: string;
};

type DuplicateResponse = {
  groups: Array<{
    reason: string;
    identity_key: string;
    guests: Array<{ id: string; name: string; phone?: string | null; email?: string | null }>;
  }>;
  automatic_merge: boolean;
  truth: string;
};

const money = (value: number) => `${new Intl.NumberFormat("ru-RU").format(Math.round(value || 0))} сом`;
const dateText = (value?: string | null) => value ? new Intl.DateTimeFormat("ru-RU").format(new Date(`${value.slice(0, 10)}T00:00:00`)) : "—";

const statusLabels: Record<string, string> = {
  GUARANTEED: "Ожидает заезд",
  CHECKED_IN: "Проживает",
  CHECKED_OUT: "Выезд завершён",
  CANCELLED: "Отменено",
  NO_SHOW: "Не заехал",
  OPEN: "Открыто",
  IN_PROGRESS: "В работе",
  IN_INSPECTION: "На проверке",
  DONE: "Выполнено",
};

const serviceLabels: Record<string, string> = {
  HOUSEKEEPING: "Уборка по просьбе гостя",
  TOWELS: "Полотенца",
  LINEN: "Замена белья",
  MAINTENANCE: "Ремонт",
  TRANSFER: "Трансфер",
  MEALS: "Питание",
  PARKING: "Парковка",
  SAUNA: "Сауна",
  BILLIARDS: "Бильярд",
  EXCURSIONS: "Экскурсии",
  ADMIN: "Администратор",
};

export default function GuestHistoryBoard() {
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [list, setList] = useState<GuestListResponse | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<GuestDetail | null>(null);
  const [duplicates, setDuplicates] = useState<DuplicateResponse | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadGuests = useCallback(async (needle: string) => {
    setLoadingList(true);
    setError(null);
    try {
      const params = new URLSearchParams({ limit: "300" });
      if (needle.trim()) params.set("search", needle.trim());
      const response = await fetch(`/core/api/v1/admin/intelligence/guests?${params}`, { cache: "no-store" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail?.message || body.detail || "Не удалось загрузить базу гостей");
      const payload = body as GuestListResponse;
      setList(payload);
      if (!selectedId && payload.items.length) setSelectedId(payload.items[0].id);
      if (selectedId && !payload.items.some((item) => item.id === selectedId) && payload.items.length) setSelectedId(payload.items[0].id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка загрузки гостей");
    } finally {
      setLoadingList(false);
    }
  }, [selectedId]);

  const loadDuplicates = useCallback(async () => {
    try {
      const response = await fetch("/core/api/v1/admin/intelligence/guests/duplicate-candidates", { cache: "no-store" });
      if (!response.ok) return;
      setDuplicates(await response.json() as DuplicateResponse);
    } catch {
      // Candidate review is secondary; the guest database remains usable if this read fails.
    }
  }, []);

  useEffect(() => {
    void loadGuests(search);
    void loadDuplicates();
  }, [search, loadGuests, loadDuplicates]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    setLoadingDetail(true);
    fetch(`/core/api/v1/admin/intelligence/guests/${selectedId}`, { cache: "no-store" })
      .then(async (response) => {
        const body = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(body.detail || "Не удалось открыть историю гостя");
        return body as GuestDetail;
      })
      .then((payload) => { if (!cancelled) setDetail(payload); })
      .catch((e) => { if (!cancelled) setError(e instanceof Error ? e.message : "Ошибка истории гостя"); })
      .finally(() => { if (!cancelled) setLoadingDetail(false); });
    return () => { cancelled = true; };
  }, [selectedId]);

  const loadedTotals = useMemo(() => {
    const items = list?.items || [];
    return {
      repeat: items.filter((item) => item.reservation_count > 1).length,
      nights: items.reduce((sum, item) => sum + item.total_nights, 0),
      received: items.reduce((sum, item) => sum + item.received_kgs, 0),
    };
  }, [list]);

  function submitSearch(event: React.FormEvent) {
    event.preventDefault();
    setSearch(query.trim());
  }

  return (
    <main className="guest-history-shell">
      <header className="guest-history-head">
        <div>
          <p className="eyebrow">OWNER CRM · RESORT CORE</p>
          <h1>Гости и история</h1>
          <p>Единая клиентская база: повторные визиты, план брони, фактические проживания, переселения, платежи, услуги и история коммуникаций.</p>
        </div>
        <form className="guest-search" onSubmit={submitSearch}>
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Имя, телефон или email" aria-label="Поиск гостя" />
          <button className="btn primary">Найти</button>
          {search && <button type="button" className="btn" onClick={() => { setQuery(""); setSearch(""); }}>Сбросить</button>}
        </form>
      </header>

      {error && <div className="error-box guest-error">{error}</div>}

      <section className="guest-history-kpis">
        <article><span>Профилей всего</span><strong>{list?.total_profiles ?? "—"}</strong><small>в Resort Core</small></article>
        <article><span>В выборке</span><strong>{list?.items.length ?? 0}</strong><small>{search ? `по запросу «${search}»` : "загружено для работы"}</small></article>
        <article><span>Повторные</span><strong>{loadedTotals.repeat}</strong><small>2+ броней в текущей выборке</small></article>
        <article><span>Ночей</span><strong>{loadedTotals.nights}</strong><small>по текущей выборке</small></article>
        <article><span>Получено</span><strong>{money(loadedTotals.received)}</strong><small>RECEIVED, текущая выборка</small></article>
        <article className={duplicates?.groups.length ? "guest-warning-kpi" : ""}><span>Дубли на проверку</span><strong>{duplicates?.groups.length ?? "—"}</strong><small>автослияние запрещено</small></article>
      </section>

      {duplicates && duplicates.groups.length > 0 && (
        <details className="guest-duplicate-panel">
          <summary>Найдены возможные дубли гостей · {duplicates.groups.length}</summary>
          <p>{duplicates.truth}</p>
          <div className="guest-duplicate-groups">
            {duplicates.groups.slice(0, 20).map((group) => (
              <div key={`${group.reason}-${group.identity_key}`}>
                <strong>{group.reason === "PHONE" ? "Телефон" : "Email"}: {group.identity_key}</strong>
                <span>{group.guests.map((guest) => `${guest.name} (${guest.id.slice(0, 8)})`).join(" · ")}</span>
              </div>
            ))}
          </div>
        </details>
      )}

      <div className="guest-history-layout">
        <section className="guest-directory">
          <div className="guest-directory-title"><strong>Клиентская база</strong><span>{loadingList ? "Обновляю…" : `${list?.items.length || 0} записей`}</span></div>
          <div className="guest-directory-list">
            {list?.items.map((guest) => (
              <button key={guest.id} className={selectedId === guest.id ? "active" : ""} onClick={() => setSelectedId(guest.id)}>
                <div><strong>{guest.name}</strong><span>{guest.phone || guest.email || "Контакт не указан"}</span></div>
                <div className="guest-directory-meta">
                  <b>{guest.reservation_count} брон.</b>
                  <span>{guest.total_nights} ноч.</span>
                  {guest.next_stay && <em>След. {dateText(guest.next_stay)}</em>}
                  {!guest.next_stay && guest.last_stay && <em>Был {dateText(guest.last_stay)}</em>}
                </div>
              </button>
            ))}
            {!loadingList && !list?.items.length && <p className="guest-empty">Гости по выбранному поиску не найдены.</p>}
          </div>
        </section>

        <section className="guest-profile">
          {loadingDetail && !detail && <div className="guest-profile-loading">Загружаю полную историю…</div>}
          {detail && (
            <>
              <div className="guest-profile-head">
                <div>
                  <span>Профиль гостя</span>
                  <h2>{detail.guest.name}</h2>
                  <p>{[detail.guest.phone, detail.guest.email].filter(Boolean).join(" · ") || "Контактные данные не заполнены"}</p>
                </div>
                <div className="guest-profile-id">ID {detail.guest.id.slice(0, 8)}</div>
              </div>

              <div className="guest-lifetime-grid">
                <article><span>Броней</span><strong>{detail.lifetime.reservation_count}</strong></article>
                <article><span>Завершённых визитов</span><strong>{detail.lifetime.completed_stays}</strong></article>
                <article><span>Ночей</span><strong>{detail.lifetime.total_nights}</strong></article>
                <article><span>Стоимость броней</span><strong>{money(detail.lifetime.booked_value_kgs)}</strong></article>
                <article><span>Фактически получено</span><strong>{money(detail.lifetime.received_kgs)}</strong></article>
              </div>

              <GuestCrmEnrichmentPanel guestId={detail.guest.id} />

              <div className="guest-section-title"><div><span>План / коммерческий контур</span><h3>Брони и плановые комнаты</h3></div><b>{detail.reservations.length}</b></div>
              <div className="guest-reservation-history">
                {detail.reservations.map((reservation) => (
                  <article key={reservation.id}>
                    <header>
                      <div><strong>{reservation.booking_number}</strong><span className={`guest-status status-${reservation.status.toLowerCase()}`}>{statusLabels[reservation.status] || reservation.status}</span></div>
                      <b>{money(reservation.total_kgs)}</b>
                    </header>
                    <div className="guest-reservation-facts">
                      <span>{dateText(reservation.check_in)} → {dateText(reservation.check_out)}</span>
                      <span>{reservation.adults} взр.{reservation.children ? ` · ${reservation.children} дет.` : ""}</span>
                      <span>{reservation.source || "Источник не указан"}</span>
                      <span>Оплачено {money(reservation.paid_kgs)}</span>
                      {reservation.outstanding_kgs > 0 && <span className="guest-debt">Остаток {money(reservation.outstanding_kgs)}</span>}
                    </div>
                    <div className="guest-room-timeline">
                      {reservation.schedule.map((segment, index) => (
                        <div key={`${reservation.id}-${segment.room_code}-${index}`}>
                          <b>№ {segment.room_code}</b><span>{segment.room_type_name}</span><em>{dateText(segment.start)} → {dateText(segment.end)}</em>
                        </div>
                      ))}
                      {!reservation.schedule.length && <span className="guest-muted">Плановые сегменты размещения не найдены.</span>}
                    </div>
                    {reservation.services.length > 0 && (
                      <div className="guest-service-row">
                        {reservation.services.map((service) => (
                          <span key={service.id} title={service.description || service.title}>
                            {serviceLabels[service.service_code || ""] || service.service_code || "Услуга"} · {statusLabels[service.status] || service.status}
                          </span>
                        ))}
                      </div>
                    )}
                    {reservation.payments.length > 0 && (
                      <details className="guest-payment-details">
                        <summary>Платежи · {reservation.payments.length}</summary>
                        {reservation.payments.map((payment) => <div key={payment.id}><span>{payment.method}</span><b>{money(payment.amount_kgs)}</b><em>{payment.status}</em></div>)}
                      </details>
                    )}
                    {reservation.notes && <p className="guest-notes">{reservation.notes}</p>}
                  </article>
                ))}
                {!detail.reservations.length && <p className="guest-empty">У этого профиля пока нет броней.</p>}
              </div>

              <div className="guest-section-title"><div><span>Коммуникации</span><h3>История обращений</h3></div><b>{detail.conversations.length}</b></div>
              <div className="guest-conversation-list">
                {detail.conversations.map((conversation) => (
                  <div key={conversation.id}>
                    <strong>{conversation.channel_name || conversation.channel_kind}</strong>
                    <span>{conversation.message_count} сообщений · {conversation.status}</span>
                    <em>Последний входящий: {conversation.last_inbound_at ? new Date(conversation.last_inbound_at).toLocaleString("ru-RU") : "—"}</em>
                  </div>
                ))}
                {!detail.conversations.length && <p className="guest-empty">Связанные диалоги пока не сохранены.</p>}
              </div>

              <div className="guest-truth-note">{detail.truth}</div>
            </>
          )}
        </section>
      </div>
    </main>
  );
}
