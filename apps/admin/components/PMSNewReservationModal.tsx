"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type Agent = { id: string; name: string; status: string };

type Preview = {
  room: {
    id: string;
    code: string;
    room_type_code: string;
    room_type_name: string;
    beds_raw?: string | null;
    operational_state: string;
    capacity_adults: number;
    effective_capacity_adults: number;
    extra_bed_allowed: boolean;
  };
  check_in: string;
  check_out: string;
  nights: number;
  adults: number;
  children: number;
  extra_bed_count: number;
  extra_bed_unit_kgs?: number | null;
  agent?: { id: string; name: string } | null;
  conflicts: Array<{ block_type: string; start: string; end: string; booking_number?: string | null }>;
  pricing: {
    source: "CORE_RATE" | "MANAGER_OVERRIDE";
    sellable: boolean;
    reason?: string | null;
    total_kgs?: number | null;
    base_total_kgs?: number | null;
    extra_beds_total_kgs: number;
    subtotal_kgs?: number | null;
    discount_percent: number;
    discount_kgs: number;
    returning_guest: boolean;
    previous_stays: number;
    auto_discount_percent: number;
    core_total_kgs?: number | null;
    core_sellable: boolean;
    core_reason?: string | null;
    nights: Array<{ date: string; price_kgs?: number | null; status?: string; period?: string | null }>;
  };
  can_commit: boolean;
};

const money = (value?: number | null) => value == null ? "—" : `${new Intl.NumberFormat("ru-RU").format(value)} сом`;

function errorText(body: any, fallback: string) {
  const detail = body?.detail;
  if (typeof detail === "string") return detail;
  if (detail?.code === "ROOM_CONFLICT") return "Часть выбранных ночей уже занята. Обновите шахматку и выберите свободный диапазон.";
  if (detail?.code === "ROOM_CONFLICT_RACE") return "Пока вы подтверждали, номер заняли. Бронь не создана — обновите шахматку.";
  if (detail?.code === "TARGET_ROOM_TECH_BLOCK") return "Номер находится в ремонте и недоступен для бронирования.";
  if (detail?.code === "ROOM_CAPACITY_EXCEEDED") return `Вместимость с выбранными допместами: ${detail.effective_capacity_adults ?? detail.capacity_adults}.`;
  if (detail?.code === "EXTRA_BED_NOT_ALLOWED") return `В категории «${detail.room_type_name || "этот номер"}» дополнительные места запрещены.`;
  if (detail?.code === "AGENT_NOT_FOUND") return "Карточка агента не найдена. Обновите список агентов.";
  if (detail?.code === "AGENT_INACTIVE") return `Агент «${detail.agent_name || ""}» неактивен.`;
  if (detail?.code === "PRICE_CHANGED") return `Цена изменилась в Core: ${money(detail.current_total_kgs)}. Выполните preview ещё раз.`;
  if (detail?.code === "PRICING_SOURCE_CHANGED") return "Источник цены изменился. Выполните preview ещё раз.";
  if (detail?.code === "RATE_REQUIRES_CONFIRMATION") return "На эти даты нет открытого тарифа. Введите базовую цену менеджера и подтвердите её явно.";
  if (Array.isArray(detail)) return detail.map((item) => item?.msg).filter(Boolean).join("; ") || fallback;
  return fallback;
}

export default function PMSNewReservationModal({
  roomId,
  roomCode,
  bedsRaw,
  checkIn,
  checkOut,
  onClose,
  onCreated,
}: {
  roomId: string;
  roomCode: string;
  bedsRaw?: string | null;
  checkIn: string;
  checkOut: string;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [adults, setAdults] = useState(2);
  const [children, setChildren] = useState(0);
  const [guestName, setGuestName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [notes, setNotes] = useState("");
  const [managerTotal, setManagerTotal] = useState("");
  const [extraBedCount, setExtraBedCount] = useState(0);
  const [extraBedUnit, setExtraBedUnit] = useState("");
  const [discountPercent, setDiscountPercent] = useState("");
  const [discountReason, setDiscountReason] = useState("");
  const [agents, setAgents] = useState<Agent[]>([]);
  const [agentId, setAgentId] = useState("");
  const [preview, setPreview] = useState<Preview | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<{ booking_number: string; total_kgs: number } | null>(null);

  useEffect(() => {
    fetch("/core/api/v1/admin/owner-corrections/agents?include_inactive=false", { cache: "no-store" })
      .then(async (response) => response.ok ? response.json() : { items: [] })
      .then((body) => setAgents((body.items || []).filter((item: Agent) => item.status === "ACTIVE")))
      .catch(() => setAgents([]));
  }, []);

  const normalizedDiscount = useMemo(() => {
    if (!discountPercent.trim()) return null;
    const value = Number(discountPercent);
    return Number.isInteger(value) && value >= 0 && value <= 100 ? value : null;
  }, [discountPercent]);

  const normalizedExtraUnit = useMemo(() => {
    const value = Number(extraBedUnit.replace(/\s/g, ""));
    return Number.isInteger(value) && value > 0 ? value : null;
  }, [extraBedUnit]);

  const loadPreview = useCallback(async (override?: number | null) => {
    if (extraBedCount > 0 && !normalizedExtraUnit) {
      setLoading(false);
      setPreview(null);
      setError("Укажите стоимость одного дополнительного места за ночь.");
      return;
    }
    setLoading(true);
    setError(null);
    setPreview(null);
    try {
      const response = await fetch("/core/api/v1/admin/pms/reservations/new/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          room_id: roomId,
          check_in: checkIn,
          check_out: checkOut,
          adults,
          children,
          manager_total_kgs: override || null,
          guest_phone: phone.trim() || null,
          extra_bed_count: extraBedCount,
          extra_bed_unit_kgs: extraBedCount > 0 ? normalizedExtraUnit : null,
          discount_percent: discountPercent.trim() ? normalizedDiscount : null,
          discount_reason: discountReason.trim() || null,
          agent_id: agentId || null,
        }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(errorText(body, "Не удалось проверить выбранные ночи"));
      setPreview(body as Preview);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Ошибка проверки");
    } finally {
      setLoading(false);
    }
  }, [roomId, checkIn, checkOut, adults, children, phone, extraBedCount, normalizedExtraUnit, discountPercent, normalizedDiscount, discountReason, agentId]);

  useEffect(() => {
    const timer = window.setTimeout(() => void loadPreview(null), phone.trim() ? 350 : 0);
    return () => window.clearTimeout(timer);
  }, [loadPreview]);

  async function applyManagerTotal() {
    const value = Number(managerTotal.replace(/\s/g, ""));
    if (!Number.isInteger(value) || value <= 0) {
      setError("Введите базовую стоимость проживания в сомах больше нуля.");
      return;
    }
    await loadPreview(value);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!preview?.can_commit || !preview.pricing.total_kgs) {
      setError("Сначала получите корректный preview цены и доступности.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const managerOverride = preview.pricing.source === "MANAGER_OVERRIDE" ? Number(managerTotal.replace(/\s/g, "")) : null;
      const response = await fetch("/core/api/v1/admin/pms/reservations/new/commit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          room_id: roomId,
          check_in: checkIn,
          check_out: checkOut,
          adults,
          children,
          manager_total_kgs: managerOverride,
          guest_phone: phone.trim(),
          extra_bed_count: extraBedCount,
          extra_bed_unit_kgs: extraBedCount > 0 ? normalizedExtraUnit : null,
          discount_percent: discountPercent.trim() ? normalizedDiscount : null,
          discount_reason: discountReason.trim() || null,
          agent_id: agentId || null,
          guest_name: guestName.trim(),
          phone: phone.trim(),
          email: email.trim() || null,
          notes: notes.trim() || null,
          expected_total_kgs: preview.pricing.total_kgs,
          expected_pricing_source: preview.pricing.source,
        }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(errorText(body, "Не удалось создать бронь"));
      setCreated({ booking_number: body.booking_number, total_kgs: body.total_kgs });
      onCreated();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Ошибка создания брони");
    } finally {
      setBusy(false);
    }
  }

  const deniedExtraBeds = preview?.room.extra_bed_allowed === false;

  return (
    <div className="owner-booking-backdrop" role="dialog" aria-modal="true" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className="owner-booking-modal">
        <header className="owner-booking-head">
          <div>
            <p className="eyebrow">Новая бронь · выбранные клетки</p>
            <h2>№ {roomCode}{bedsRaw ? ` · ${bedsRaw}` : ""}</h2>
            <p>{checkIn} → {checkOut}</p>
          </div>
          <button type="button" className="owner-quiet-btn" onClick={onClose}>Закрыть</button>
        </header>

        {created ? (
          <div className="owner-created">
            <strong>Бронь создана</strong>
            <b>{created.booking_number}</b>
            <span>{money(created.total_kgs)} · платеж не создавался автоматически</span>
            <button type="button" onClick={onClose}>Готово</button>
          </div>
        ) : (
          <form onSubmit={submit}>
            <div className="owner-stay-facts">
              <div><span>Заезд</span><strong>{checkIn}</strong></div>
              <div><span>Выезд</span><strong>{checkOut}</strong></div>
              <div><span>Ночей</span><strong>{preview?.nights ?? "—"}</strong></div>
              <div><span>Итого</span><strong>{money(preview?.pricing.total_kgs)}</strong></div>
            </div>

            <div className="owner-guest-grid">
              <label><span>Имя гостя</span><input required minLength={2} value={guestName} onChange={(event) => setGuestName(event.target.value)} placeholder="Как обращаться" /></label>
              <label><span>Телефон</span><input required minLength={5} value={phone} onChange={(event) => setPhone(event.target.value)} placeholder="+996 ..." /></label>
              <label><span>Взрослые</span><input type="number" min={1} max={20} value={adults} onChange={(event) => setAdults(Number(event.target.value))} /></label>
              <label><span>Дети</span><input type="number" min={0} max={20} value={children} onChange={(event) => setChildren(Number(event.target.value))} /></label>
              <label><span>Email</span><input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="необязательно" /></label>
              <label><span>Агент</span><select value={agentId} onChange={(event) => setAgentId(event.target.value)}><option value="">Прямая бронь / без агента</option>{agents.map((agent) => <option key={agent.id} value={agent.id}>{agent.name}</option>)}</select></label>
              <label className="owner-notes"><span>Комментарий</span><input value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="пожелания / условия" /></label>
            </div>

            <section className="owner-price-card ready">
              <div>
                <span>Дополнительные места</span>
                {deniedExtraBeds ? <strong>Запрещены для этой категории</strong> : <strong>Разрешены</strong>}
                {!deniedExtraBeds && <small>При добавлении места Core автоматически пересчитает весь период.</small>}
              </div>
              {!deniedExtraBeds && <div className="owner-manager-price">
                <input type="number" min={0} max={10} value={extraBedCount} onChange={(event) => setExtraBedCount(Number(event.target.value))} aria-label="Количество дополнительных мест" />
                <input inputMode="numeric" value={extraBedUnit} disabled={extraBedCount === 0} onChange={(event) => setExtraBedUnit(event.target.value)} placeholder="Цена 1 допместа / ночь" />
              </div>}
              {preview && <div className="owner-commercial-prices"><span>Допместа: {money(preview.pricing.extra_beds_total_kgs)}</span><span>Вместимость: {preview.room.effective_capacity_adults}</span></div>}
            </section>

            <section className="owner-price-card ready">
              <div>
                <span>Скидка на проживание</span>
                {preview?.pricing.returning_guest ? <strong>Постоянный гость · автоматически 10%</strong> : <strong>Новый гость / скидка по решению менеджера</strong>}
                {preview?.pricing.previous_stays ? <small>Предыдущих завершённых проживаний: {preview.pricing.previous_stays}</small> : null}
              </div>
              <div className="owner-manager-price">
                <input type="number" min={0} max={100} value={discountPercent} onChange={(event) => setDiscountPercent(event.target.value)} placeholder="% — пусто = авто" />
                <input value={discountReason} onChange={(event) => setDiscountReason(event.target.value)} placeholder="Причина другой скидки" />
              </div>
            </section>

            <section className={`owner-price-card ${preview?.pricing.sellable ? "ready" : "needs-manager"}`}>
              <div>
                <span>Расчёт Resort Core</span>
                {loading ? <strong>Проверяем…</strong> : preview?.pricing.core_sellable ? <strong>{money(preview.pricing.core_total_kgs)}</strong> : <strong>Требует подтверждения менеджера</strong>}
                {preview?.pricing.core_reason && <small>{preview.pricing.core_reason}</small>}
              </div>
              {preview?.pricing.nights?.length ? (
                <div className="owner-nightly-prices">
                  {preview.pricing.nights.map((night) => <span key={night.date}>{night.date.slice(5)} · {money(night.price_kgs)}</span>)}
                </div>
              ) : null}
              {!preview?.pricing.core_sellable && !loading && (
                <div className="owner-manager-price">
                  <input inputMode="numeric" value={managerTotal} onChange={(event) => setManagerTotal(event.target.value)} placeholder="Базовая цена проживания, сом" />
                  <button type="button" onClick={applyManagerTotal}>Подтвердить цену</button>
                </div>
              )}
              {preview?.pricing.source === "MANAGER_OVERRIDE" && <b className="owner-override-badge">Базовая цена подтверждена менеджером</b>}
              {preview && <div className="owner-commercial-prices">
                <span>База: {money(preview.pricing.base_total_kgs)}</span>
                <span>Допместа: {money(preview.pricing.extra_beds_total_kgs)}</span>
                <span>Скидка {preview.pricing.discount_percent}%: −{money(preview.pricing.discount_kgs)}</span>
                <span><b>Итого: {money(preview.pricing.total_kgs)}</b></span>
              </div>}
            </section>

            {preview?.conflicts?.length ? <div className="owner-booking-error">Выбранный период уже пересекается с активным блоком.</div> : null}
            {error && <div className="owner-booking-error">{error}</div>}

            <footer className="owner-booking-actions">
              <span>Клетки — ночи. Допместа и скидки подтверждаются Core и сохраняются в аудите.</span>
              <button type="submit" disabled={busy || loading || !preview?.can_commit || !guestName.trim() || !phone.trim()}>
                {busy ? "Создаём…" : "Подтвердить бронь"}
              </button>
            </footer>
          </form>
        )}
      </section>
    </div>
  );
}
