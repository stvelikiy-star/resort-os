"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type RoomType = {
  id: string;
  code: string;
  name: string;
  capacity_adults: number;
  capacity_children?: number | null;
  room_count: number;
};

type RatePeriod = {
  id: string;
  room_type_id: string;
  label: string;
  valid_from: string;
  valid_to: string;
  price_kgs: number;
  meal_included: string;
  sale_status: "OPEN" | "CLOSED" | "CONFIRM_REQUIRED";
  notes?: string | null;
  updated_at: string;
};

type RateOverview = {
  property_code: string;
  timezone: string;
  currency: string;
  rate_plan: { id: string; code: string; name: string };
  room_types: RoomType[];
  periods: RatePeriod[];
  rules: {
    open_requires_positive_price: boolean;
    overlap_allowed: boolean;
    existing_reservation_totals_rewritten: boolean;
    delete_supported: boolean;
  };
};

type Draft = {
  label: string;
  valid_from: string;
  valid_to: string;
  price_kgs: string;
  meal_included: string;
  sale_status: RatePeriod["sale_status"];
  notes: string;
};

const emptyDraft: Draft = {
  label: "",
  valid_from: "",
  valid_to: "",
  price_kgs: "",
  meal_included: "NONE",
  sale_status: "OPEN",
  notes: "",
};

function money(value: number, currency: string) {
  return `${new Intl.NumberFormat("ru-RU").format(value)} ${currency}`;
}

function statusLabel(value: RatePeriod["sale_status"]) {
  if (value === "OPEN") return "Открыт для продажи";
  if (value === "CLOSED") return "Закрыт";
  return "Требует подтверждения";
}

function toDraft(period: RatePeriod): Draft {
  return {
    label: period.label,
    valid_from: period.valid_from.slice(0, 10),
    valid_to: period.valid_to.slice(0, 10),
    price_kgs: String(period.price_kgs),
    meal_included: period.meal_included,
    sale_status: period.sale_status,
    notes: period.notes || "",
  };
}

export default function RateManagementBoard() {
  const [data, setData] = useState<RateOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [roomFilter, setRoomFilter] = useState("ALL");
  const [editing, setEditing] = useState<RatePeriod | null>(null);
  const [draft, setDraft] = useState<Draft>(emptyDraft);
  const [creatingFor, setCreatingFor] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/core/api/v1/admin/rates", { cache: "no-store" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Не удалось загрузить тарифы");
      setData(body as RateOverview);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка загрузки тарифов");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const grouped = useMemo(() => {
    if (!data) return [] as { roomType: RoomType; periods: RatePeriod[] }[];
    return data.room_types
      .filter((roomType) => roomFilter === "ALL" || roomType.id === roomFilter)
      .map((roomType) => ({
        roomType,
        periods: data.periods
          .filter((period) => period.room_type_id === roomType.id)
          .sort((a, b) => a.valid_from.localeCompare(b.valid_from)),
      }));
  }, [data, roomFilter]);

  function beginEdit(period: RatePeriod) {
    setCreatingFor(null);
    setEditing(period);
    setDraft(toDraft(period));
    setNotice(null);
  }

  function beginCreate(roomTypeId: string) {
    setEditing(null);
    setCreatingFor(roomTypeId);
    setDraft(emptyDraft);
    setNotice(null);
  }

  function closeEditor() {
    setEditing(null);
    setCreatingFor(null);
    setDraft(emptyDraft);
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!editing && !creatingFor) return;
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const price = Number(draft.price_kgs);
      if (!Number.isInteger(price) || price < 0) throw new Error("Цена должна быть целым числом 0 или больше");
      const payload = {
        ...(creatingFor ? { room_type_id: creatingFor } : {}),
        label: draft.label.trim(),
        valid_from: draft.valid_from,
        valid_to: draft.valid_to,
        price_kgs: price,
        meal_included: draft.meal_included.trim() || "NONE",
        sale_status: draft.sale_status,
        notes: draft.notes.trim(),
      };
      const response = await fetch(
        editing ? `/core/api/v1/admin/rates/periods/${editing.id}` : "/core/api/v1/admin/rates/periods",
        {
          method: editing ? "PATCH" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
      );
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = body.detail;
        if (detail?.code === "RATE_PERIOD_OVERLAP") {
          throw new Error(`Период пересекается с «${detail.label}» (${detail.valid_from} — ${detail.valid_to}).`);
        }
        throw new Error(typeof detail === "string" ? detail : "Не удалось сохранить тариф");
      }
      closeEditor();
      setNotice(editing ? "Тариф обновлён. Новые расчёты используют актуальные периоды." : "Новый тарифный период создан.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка сохранения тарифа");
    } finally {
      setSaving(false);
    }
  }

  if (loading && !data) return <main className="work-shell management-shell"><div className="loading">Загрузка цен и сезонов…</div></main>;
  if (error && !data) return <main className="work-shell management-shell"><div className="error-box">{error}</div><button className="btn" onClick={load}>Повторить</button></main>;
  if (!data) return null;

  const openCount = data.periods.filter((period) => period.sale_status === "OPEN").length;
  const attentionCount = data.periods.filter((period) => period.sale_status !== "OPEN").length;

  return <main className="work-shell management-shell rates-shell">
    <div className="work-head">
      <div>
        <p className="eyebrow">PMS · коммерческое управление</p>
        <h1>Цены и сезоны</h1>
        <p className="subtitle">Рабочий тариф {data.rate_plan.code} · {data.currency} · {data.timezone}</p>
      </div>
      <button className="btn" onClick={load} disabled={loading}>{loading ? "Обновляю…" : "Обновить"}</button>
    </div>

    <section className="management-kpis">
      <article><strong>{data.room_types.length}</strong><span>категорий</span></article>
      <article><strong>{data.periods.length}</strong><span>тарифных периодов</span></article>
      <article><strong>{openCount}</strong><span>открыто для продажи</span></article>
      <article><strong>{attentionCount}</strong><span>закрыто / требует внимания</span></article>
    </section>

    <div className="management-truth">
      <strong>Правило безопасности:</strong> изменение тарифа влияет на новые расчёты и изменения, где Core пересчитывает цену. Уже сохранённая сумма существующей брони автоматически не переписывается. Периоды не удаляются — их можно закрыть.
    </div>

    {notice && <div className="management-notice">{notice}</div>}
    {error && <div className="error-box">{error}</div>}

    <div className="management-controls">
      <label>
        <span>Категория</span>
        <select value={roomFilter} onChange={(e) => setRoomFilter(e.target.value)}>
          <option value="ALL">Все категории</option>
          {data.room_types.map((roomType) => <option key={roomType.id} value={roomType.id}>{roomType.name}</option>)}
        </select>
      </label>
    </div>

    <section className="rate-groups">
      {grouped.map(({ roomType, periods }) => <article className="rate-group" key={roomType.id}>
        <header>
          <div>
            <h2>{roomType.name}</h2>
            <p>{roomType.room_count} ном. · базово {roomType.capacity_adults} гост.</p>
          </div>
          <button className="btn secondary" onClick={() => beginCreate(roomType.id)}>+ Добавить период</button>
        </header>
        <div className="rate-period-table">
          <div className="rate-period-row rate-period-head"><span>Период</span><span>Даты</span><span>Цена / сутки</span><span>Продажа</span><span>Питание</span><span></span></div>
          {periods.length === 0 && <div className="empty">Для категории нет тарифных периодов. Core будет fail-closed для дат без тарифа.</div>}
          {periods.map((period) => <div className="rate-period-row" key={period.id}>
            <div><strong>{period.label}</strong>{period.notes && <small>{period.notes}</small>}</div>
            <div><strong>{period.valid_from.slice(0, 10)}</strong><small>по {period.valid_to.slice(0, 10)}</small></div>
            <div><strong>{money(period.price_kgs, data.currency)}</strong><small>за номер / ночь</small></div>
            <div><span className={`rate-status ${period.sale_status.toLowerCase()}`}>{statusLabel(period.sale_status)}</span></div>
            <div><strong>{period.meal_included || "NONE"}</strong></div>
            <div><button className="btn mini" onClick={() => beginEdit(period)}>Изменить</button></div>
          </div>)}
        </div>
      </article>)}
    </section>

    {(editing || creatingFor) && <div className="management-modal-backdrop" role="presentation" onMouseDown={(e) => { if (e.target === e.currentTarget) closeEditor(); }}>
      <form className="management-modal" onSubmit={save}>
        <div className="management-modal-head">
          <div><p className="eyebrow">{editing ? "Редактирование" : "Новый период"}</p><h2>{editing ? editing.label : data.room_types.find((item) => item.id === creatingFor)?.name}</h2></div>
          <button type="button" className="btn mini" onClick={closeEditor}>Закрыть</button>
        </div>
        <div className="management-form-grid">
          <label><span>Название периода</span><input required minLength={2} value={draft.label} onChange={(e) => setDraft({ ...draft, label: e.target.value })} placeholder="Например: Осень 2026" /></label>
          <label><span>Цена, сом / ночь</span><input required type="number" min={0} step={1} value={draft.price_kgs} onChange={(e) => setDraft({ ...draft, price_kgs: e.target.value })} /></label>
          <label><span>С</span><input required type="date" value={draft.valid_from} onChange={(e) => setDraft({ ...draft, valid_from: e.target.value })} /></label>
          <label><span>По</span><input required type="date" value={draft.valid_to} onChange={(e) => setDraft({ ...draft, valid_to: e.target.value })} /></label>
          <label><span>Статус продажи</span><select value={draft.sale_status} onChange={(e) => setDraft({ ...draft, sale_status: e.target.value as RatePeriod["sale_status"] })}><option value="OPEN">Открыт</option><option value="CONFIRM_REQUIRED">Требует подтверждения</option><option value="CLOSED">Закрыт</option></select></label>
          <label><span>Питание</span><input required value={draft.meal_included} onChange={(e) => setDraft({ ...draft, meal_included: e.target.value })} placeholder="NONE / BREAKFAST" /></label>
          <label className="management-form-wide"><span>Примечание</span><textarea rows={3} value={draft.notes} onChange={(e) => setDraft({ ...draft, notes: e.target.value })} /></label>
        </div>
        <div className="management-modal-actions"><button type="button" className="btn" onClick={closeEditor}>Отмена</button><button className="btn primary" disabled={saving}>{saving ? "Сохраняю…" : "Сохранить"}</button></div>
      </form>
    </div>}
  </main>;
}
