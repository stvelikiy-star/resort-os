"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

type Preview = {
  room: {
    id: string;
    code: string;
    room_type_name: string;
    beds_raw?: string | null;
    operational_state: string;
    capacity_adults: number;
  };
  check_in: string;
  check_out: string;
  nights: number;
  adults: number;
  children: number;
  conflicts: Array<{ block_type: string; start: string; end: string; booking_number?: string | null }>;
  pricing: {
    source: "CORE_RATE" | "MANAGER_OVERRIDE";
    sellable: boolean;
    reason?: string | null;
    total_kgs?: number | null;
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
  if (detail?.code === "ROOM_CAPACITY_EXCEEDED") return `Для этого номера допустимо взрослых: ${detail.capacity_adults}.`;
  if (detail?.code === "PRICE_CHANGED") return `Цена изменилась в Core: ${money(detail.current_total_kgs)}. Выполните preview ещё раз.`;
  if (detail?.code === "PRICING_SOURCE_CHANGED") return "Источник цены изменился. Выполните preview ещё раз.";
  if (detail?.code === "RATE_REQUIRES_CONFIRMATION") return "На эти даты нет открытого тарифа. Введите итоговую цену менеджера и подтвердите её явно.";
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
  const [preview, setPreview] = useState<Preview | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<{ booking_number: string; total_kgs: number } | null>(null);

  const loadPreview = useCallback(async (override?: number | null) => {
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
  }, [roomId, checkIn, checkOut, adults, children]);

  useEffect(() => { void loadPreview(null); }, [loadPreview]);

  async function applyManagerTotal() {
    const value = Number(managerTotal.replace(/\s/g, ""));
    if (!Number.isInteger(value) || value <= 0) {
      setError("Введите итоговую стоимость в сомах больше нуля.");
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
              <div><span>Стоимость</span><strong>{money(preview?.pricing.total_kgs)}</strong></div>
            </div>

            <div className="owner-guest-grid">
              <label><span>Имя гостя</span><input required minLength={2} value={guestName} onChange={(event) => setGuestName(event.target.value)} placeholder="Как обращаться" /></label>
              <label><span>Телефон</span><input required minLength={5} value={phone} onChange={(event) => setPhone(event.target.value)} placeholder="+996 ..." /></label>
              <label><span>Взрослые</span><input type="number" min={1} max={20} value={adults} onChange={(event) => setAdults(Number(event.target.value))} /></label>
              <label><span>Дети</span><input type="number" min={0} max={20} value={children} onChange={(event) => setChildren(Number(event.target.value))} /></label>
              <label><span>Email</span><input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="необязательно" /></label>
              <label className="owner-notes"><span>Комментарий</span><input value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="пожелания / условия" /></label>
            </div>

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
                  <input inputMode="numeric" value={managerTotal} onChange={(event) => setManagerTotal(event.target.value)} placeholder="Итоговая цена, сом" />
                  <button type="button" onClick={applyManagerTotal}>Подтвердить цену</button>
                </div>
              )}
              {preview?.pricing.source === "MANAGER_OVERRIDE" && <b className="owner-override-badge">Цена подтверждена менеджером</b>}
            </section>

            {preview?.conflicts?.length ? <div className="owner-booking-error">Выбранный период уже пересекается с активным блоком.</div> : null}
            {error && <div className="owner-booking-error">{error}</div>}

            <footer className="owner-booking-actions">
              <span>Клетки — ночи. День выезда не блокируется этой бронью.</span>
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
