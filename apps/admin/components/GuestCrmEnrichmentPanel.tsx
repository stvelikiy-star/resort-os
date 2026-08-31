"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type Assignment = {
  id: string;
  room_id: string;
  room_code: string;
  room_name: string;
  room_type_name: string;
  started_at: string;
  ended_at?: string | null;
  source?: string | null;
};

type StayRequest = {
  id: string;
  request_code?: string | null;
  status: string;
  priority: string;
  title: string;
  description?: string | null;
  created_at: string;
  completed_at?: string | null;
};

type ActualStay = {
  id: string;
  status: string;
  booking_number: string;
  planned_check_in: string;
  planned_check_out: string;
  actual_check_in_at?: string | null;
  actual_check_out_at?: string | null;
  assignments: Assignment[];
  requests: StayRequest[];
};

type Preference = {
  id: string;
  key: string;
  label: string;
  value?: string | null;
  source?: string | null;
  active: boolean;
};

type EventItem = {
  id: string;
  stay_id?: string | null;
  event_type: string;
  source?: string | null;
  payload?: Record<string, unknown> | null;
  occurred_at: string;
};

type CrmResponse = {
  stays: ActualStay[];
  preferences: Preference[];
  events: EventItem[];
  preference_keys: Array<{ key: string; label: string }>;
  truth: string;
};

const requestLabels: Record<string, string> = {
  HOUSEKEEPING: "Уборка по просьбе гостя",
  TOWELS: "Полотенца",
  LINEN: "Замена белья",
  MAINTENANCE: "Ремонт",
  TRANSFER: "Трансфер",
  MEALS: "Питание",
  SAUNA: "Сауна",
  BILLIARDS: "Бильярд",
  EXCURSIONS: "Экскурсии",
  ADMIN: "Администратор",
};

const eventLabels: Record<string, string> = {
  CHECK_IN: "Заселение",
  CHECK_OUT: "Выезд",
  ROOM_RELOCATION: "Переселение",
  GUEST_REQUEST_CREATED: "Создана заявка гостя",
  GUEST_REQUEST_COMPLETED: "Заявка выполнена",
  GUEST_REQUEST_CANCELLED: "Заявка отменена",
};

function dateTime(value?: string | null) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("ru-RU", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function dateOnly(value?: string | null) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("ru-RU").format(new Date(`${value.slice(0, 10)}T00:00:00`));
}

function eventSummary(event: EventItem) {
  const payload = event.payload || {};
  if (event.event_type === "ROOM_RELOCATION") return "Фактическое назначение номера изменено";
  if (event.event_type.startsWith("GUEST_REQUEST")) {
    const code = typeof payload.request_code === "string" ? payload.request_code : "";
    return requestLabels[code] || code || "Заявка гостя";
  }
  return event.source || "Resort Core";
}

export default function GuestCrmEnrichmentPanel({ guestId }: { guestId: string }) {
  const [data, setData] = useState<CrmResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [preferenceKey, setPreferenceKey] = useState("HOUSEKEEPING_TIME");
  const [preferenceValue, setPreferenceValue] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/core/api/v1/admin/guest-crm/${guestId}`, { cache: "no-store" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Не удалось загрузить фактическую историю гостя");
      setData(body as CrmResponse);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка фактической истории");
    } finally {
      setLoading(false);
    }
  }, [guestId]);

  useEffect(() => { void load(); }, [load]);

  const activePreferences = useMemo(() => data?.preferences.filter((item) => item.active) || [], [data]);

  async function savePreference(event: FormEvent) {
    event.preventDefault();
    if (!preferenceValue.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const response = await fetch(`/core/api/v1/admin/guest-crm/${guestId}/preferences/${preferenceKey}`, {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ value: preferenceValue.trim() }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Не удалось сохранить предпочтение");
      setPreferenceValue("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка сохранения");
    } finally {
      setSaving(false);
    }
  }

  async function deactivate(key: string) {
    setSaving(true);
    setError(null);
    try {
      const response = await fetch(`/core/api/v1/admin/guest-crm/${guestId}/preferences/${key}`, { method: "DELETE" });
      if (!response.ok) throw new Error("Не удалось отключить предпочтение");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка сохранения");
    } finally {
      setSaving(false);
    }
  }

  return <section className="guest-crm-actual">
    <div className="guest-section-title guest-crm-title">
      <div><span>RESORT CORE · FACT</span><h3>Фактическое проживание</h3></div>
      <b>{data?.stays.length ?? 0}</b>
    </div>
    <p className="guest-crm-explain">Ниже — факт заселения и реальных переселений. Плановые сегменты брони остаются отдельно в блоке «Брони и комнаты».</p>
    {error && <div className="error-box guest-error">{error}</div>}
    {loading && !data && <div className="guest-profile-loading">Загружаю Stay и RoomAssignment…</div>}

    {data && <>
      <div className="guest-crm-stays">
        {data.stays.map((stay) => <article key={stay.id} className="guest-crm-stay">
          <header>
            <div><strong>{stay.booking_number}</strong><span>{stay.status}</span></div>
            <small>План: {dateOnly(stay.planned_check_in)} → {dateOnly(stay.planned_check_out)}</small>
          </header>
          <div className="guest-crm-actual-dates">
            <span>Факт заезда <b>{dateTime(stay.actual_check_in_at)}</b></span>
            <span>Факт выезда <b>{dateTime(stay.actual_check_out_at)}</b></span>
          </div>
          <div className="guest-crm-assignments">
            {stay.assignments.map((assignment, index) => <div key={assignment.id}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <strong>№ {assignment.room_code}</strong>
              <p>{assignment.room_type_name}</p>
              <em>{dateTime(assignment.started_at)} → {assignment.ended_at ? dateTime(assignment.ended_at) : "сейчас"}</em>
              <small>{assignment.source || "Core"}</small>
            </div>)}
            {!stay.assignments.length && <p className="guest-muted">Фактических назначений номера нет.</p>}
          </div>
          {stay.requests.length > 0 && <details className="guest-crm-requests">
            <summary>Заявки во время проживания · {stay.requests.length}</summary>
            {stay.requests.map((item) => <div key={item.id}>
              <strong>{requestLabels[item.request_code || ""] || item.request_code || item.title}</strong>
              <span>{item.status}</span>
              <p>{item.description || item.title}</p>
            </div>)}
          </details>}
        </article>)}
        {!data.stays.length && <p className="guest-empty">Фактических Stay пока нет: профиль мог существовать только как заявка или бронь без заселения.</p>}
      </div>

      <div className="guest-crm-preferences">
        <div className="guest-section-title"><div><span>Только явные настройки</span><h3>Предпочтения гостя</h3></div><b>{activePreferences.length}</b></div>
        <p className="guest-crm-explain">Сохраняются только разрешённые сервисные предпочтения, которые менеджер подтвердил явно. Автоматического профилирования нет.</p>
        <form onSubmit={savePreference}>
          <select value={preferenceKey} onChange={(event) => setPreferenceKey(event.target.value)}>
            {data.preference_keys.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}
          </select>
          <input value={preferenceValue} onChange={(event) => setPreferenceValue(event.target.value)} maxLength={240} placeholder="Например: после 16:00" />
          <button className="btn primary" disabled={saving || !preferenceValue.trim()}>{saving ? "Сохраняю…" : "Сохранить"}</button>
        </form>
        <div className="guest-crm-preference-list">
          {activePreferences.map((item) => <div key={item.id}><div><strong>{item.label}</strong><span>{item.value || "—"}</span></div><button disabled={saving} onClick={() => void deactivate(item.key)}>Отключить</button></div>)}
          {!activePreferences.length && <p className="guest-empty">Подтверждённых предпочтений пока нет.</p>}
        </div>
      </div>

      <details className="guest-crm-events">
        <summary>События истории · {data.events.length}</summary>
        <div>
          {data.events.slice(0, 100).map((event) => <article key={event.id}>
            <time>{dateTime(event.occurred_at)}</time>
            <strong>{eventLabels[event.event_type] || event.event_type}</strong>
            <span>{eventSummary(event)}</span>
          </article>)}
        </div>
      </details>
      <div className="guest-truth-note">{data.truth}</div>
    </>}
  </section>;
}
