"use client";

import { useCallback, useEffect, useState } from "react";
import SharedManualPaymentPanel from "../shared-auth-preview/SharedManualPaymentPanel";

type Identity = {
  id: string; role: string; tenant_id: string; property_id: string;
  module_permissions: string[];
};
type Booking = {
  id: string; bookingNumber: string; status: string;
  totalKgs: number; paidKgs: number; remainingKgs: number;
};
type Reply = { items: Booking[] };

/** Only an internal cash fact after physical receipt; no acquiring or refund. */
export default function SharedReceptionCash({
  user, onExpired, refreshToken,
}: {
  user: Identity;
  onExpired: () => void;
  refreshToken: number;
}) {
  const [items, setItems] = useState<Booking[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async (signal?: AbortSignal) => {
    const auth = await fetch("/core/api/v1/auth/me", { cache: "no-store", signal });
    if (!auth.ok) { onExpired(); return; }
    const session = await auth.json() as Identity;
    if (session.id !== user.id || session.role !== "RECEPTION" ||
        session.tenant_id !== user.tenant_id ||
        session.property_id !== user.property_id ||
        !session.module_permissions?.includes("RESERVATIONS")) {
      onExpired(); return;
    }
    const response = await fetch("/core/api/v1/admin/reception/reservations", {
      cache: "no-store", signal,
    });
    if (response.status === 401 || response.status === 403) { onExpired(); return; }
    if (!response.ok) throw new Error("reservations unavailable");
    const body = await response.json() as Reply;
    if (!Array.isArray(body.items)) throw new Error("unverified reservations");
    const available = body.items.filter(item =>
      typeof item.id === "string" && typeof item.bookingNumber === "string" &&
      Number.isSafeInteger(item.remainingKgs) && item.remainingKgs > 0 &&
      !["CANCELLED", "NO_SHOW"].includes(item.status));
    if (signal?.aborted) return;
    setItems(available);
    setSelectedId(old => available.some(item => item.id === old)
      ? old : available[0]?.id ?? "");
    setError("");
  }, [user.id, user.tenant_id, user.property_id, user.role, onExpired]);

  useEffect(() => {
    const controller = new AbortController();
    setItems([]); setSelectedId(""); setBusy(true);
    void refresh(controller.signal)
      .catch(() => {
        if (!controller.signal.aborted) setError("Брони своей гостиницы не подтверждены сервером.");
      })
      .finally(() => { if (!controller.signal.aborted) setBusy(false); });
    return () => controller.abort();
  }, [refresh, refreshToken]);

  const selected = items.find(item => item.id === selectedId);
  return <section aria-label="Ресепшен: учёт наличных">
    <h2>Учёт полученных наличных</h2>
    <p>Вручную фиксируются только деньги, которые гостиница уже получила. 
      Возвраты, терминал, QR и банковские операции здесь недоступны.</p>
    <button type="button" className="btn" disabled={busy}
      onClick={() => { setBusy(true); void refresh().catch(() =>
        setError("Не удалось обновить бронирования."))
        .finally(() => setBusy(false)); }}>Обновить бронирования</button>
    {busy && <p role="status">Проверка бронирований…</p>}
    {error && <p role="alert">{error}</p>}
    {!busy && !error && items.length === 0 &&
      <p>Бронирований с подтверждённым неоплаченным остатком нет.</p>}
    {!busy && !error && items.length > 0 && <>
      <label>Бронь для учёта оплаты
        <select value={selectedId} onChange={event => setSelectedId(event.target.value)}>
          {items.map(item => <option key={item.id} value={item.id}>
            {item.bookingNumber} · остаток {item.remainingKgs} KGS
          </option>)}
        </select>
      </label>
      {selected && <SharedManualPaymentPanel
        key={selected.id}
        reservationId={selected.id}
        bookingNumber={selected.bookingNumber}
        onExpired={onExpired}
        onUpdated={() => refresh()}
        receptionCashOnly
      />}
    </>}
  </section>;
}
