"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import styles from "./ReservationFolioPanel.module.css";

type Charge = { id: string; source_type: string; code: string; description: string; amount_kgs: number; status: string; service_date?: string | null; created_at: string };
type Payment = { id: string; amount_kgs: number; method: string; status: string; provider?: string | null; external_ref?: string | null; paid_at?: string | null; recorded_at: string; metadata?: Record<string, unknown> | null };
type Folio = {
  totals: { accommodation_kgs: number; extras_kgs: number; grand_total_kgs: number; paid_kgs: number; remaining_kgs: number; overpaid_kgs: number };
  charges: Charge[];
  payments: Payment[];
};

type AuthMe = { role?: string | null };

const METHODS = [
  ["CASH", "Наличные"],
  ["CARD_POS", "Карта / POS"],
  ["QR_CASHLESS", "QR / безнал"],
  ["BANK_TRANSFER", "Банковский перевод"],
  ["OTHER", "Другое"],
] as const;

const money = (value: number) => `${new Intl.NumberFormat("ru-RU").format(value)} сом`;

function nowLocalInput() {
  const value = new Date();
  const shifted = new Date(value.getTime() - value.getTimezoneOffset() * 60000);
  return shifted.toISOString().slice(0, 16);
}

async function api(path: string, init?: RequestInit) {
  const response = await fetch(path, { cache: "no-store", ...init });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(typeof body?.detail === "string" ? body.detail : body?.detail?.message || body?.detail?.code || "Ошибка Resort Core");
  return body;
}

export default function ReservationFolioPanel({ reservationId, onChanged }: { reservationId: string; onChanged?: () => void | Promise<void> }) {
  const [folio, setFolio] = useState<Folio | null>(null);
  const [viewerRole, setViewerRole] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState("CASH");
  const [paidAt, setPaidAt] = useState(nowLocalInput());
  const [externalRef, setExternalRef] = useState("");
  const [note, setNote] = useState("");

  const [chargeCode, setChargeCode] = useState("EXTRA_SERVICE");
  const [chargeDescription, setChargeDescription] = useState("");
  const [chargeAmount, setChargeAmount] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const body = await api(`/core/api/v1/admin/folio/reservations/${reservationId}`);
      setFolio(body as Folio);
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось загрузить folio гостя");
    } finally {
      setLoading(false);
    }
  }, [reservationId]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    let active = true;
    fetch("/core/api/v1/auth/me", { cache: "no-store" })
      .then(async (response) => response.ok ? await response.json() as AuthMe : null)
      .then((payload) => { if (active) setViewerRole(payload?.role || null); })
      .catch(() => { if (active) setViewerRole(null); });
    return () => { active = false; };
  }, []);

  const openCharges = useMemo(() => folio?.charges.filter((item) => item.status === "OPEN") ?? [], [folio]);
  const canManagePayments = viewerRole === "OWNER" || viewerRole === "MANAGER";
  const canCloseCharges = canManagePayments;

  async function recordPayment(event: FormEvent) {
    event.preventDefault();
    if (!canManagePayments) return;
    const amountKgs = Number(amount);
    if (!Number.isFinite(amountKgs) || amountKgs <= 0) return;
    setBusy("payment"); setError(null); setNotice(null);
    try {
      await api(`/core/api/v1/admin/booking/reservations/${reservationId}/payments`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          amount_kgs: Math.round(amountKgs),
          method,
          paid_at: paidAt ? new Date(paidAt).toISOString() : null,
          external_ref: externalRef.trim() || null,
          note: note.trim() || null,
          idempotency_key: `pms-${reservationId}-${crypto.randomUUID()}`,
        }),
      });
      setNotice("Оплата принята и записана. Фактическое время и время внесения сохранены отдельно.");
      setAmount(""); setExternalRef(""); setNote(""); setPaidAt(nowLocalInput());
      await load();
      await onChanged?.();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось записать оплату");
    } finally { setBusy(null); }
  }

  async function createCharge(event: FormEvent) {
    event.preventDefault();
    const amountKgs = Number(chargeAmount);
    if (!chargeDescription.trim() || !Number.isFinite(amountKgs) || amountKgs <= 0) return;
    setBusy("charge"); setError(null); setNotice(null);
    try {
      await api(`/core/api/v1/admin/folio/reservations/${reservationId}/charges`, {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ code: chargeCode, description: chargeDescription.trim(), amount_kgs: Math.round(amountKgs), notes: null }),
      });
      setChargeDescription(""); setChargeAmount("");
      setNotice("Начисление добавлено в folio. Это задолженность, а не подтверждение получения денег.");
      await load();
      await onChanged?.();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Не удалось добавить начисление"); }
    finally { setBusy(null); }
  }

  async function closeCharge(charge: Charge, status: "WAIVED" | "VOID") {
    if (!canCloseCharges) return;
    const reason = window.prompt(status === "WAIVED" ? "Причина списания/комплимента:" : "Причина аннулирования начисления:");
    if (!reason?.trim()) return;
    setBusy(charge.id); setError(null); setNotice(null);
    try {
      await api(`/core/api/v1/admin/folio/charges/${charge.id}`, {
        method: "PATCH", headers: { "content-type": "application/json" }, body: JSON.stringify({ status, reason: reason.trim() }),
      });
      setNotice(status === "WAIVED" ? "Начисление списано решением менеджера." : "Начисление аннулировано.");
      await load();
      await onChanged?.();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Не удалось изменить начисление"); }
    finally { setBusy(null); }
  }

  return <section className={styles.shell}>
    <div className={styles.head}><div><small>Guest folio · Resort Core</small><h3>Финансы гостя</h3><p>Проживание + дополнительные услуги = общий счёт. Payment появляется только когда деньги реально приняты.</p></div><button onClick={() => void load()} disabled={loading}>↻ Обновить</button></div>
    {error && <div className={styles.error}>{error}</div>}{notice && <div className={styles.notice}>{notice}</div>}

    <div className={styles.totals}>
      <div><span>Проживание</span><strong>{loading || !folio ? "…" : money(folio.totals.accommodation_kgs)}</strong></div>
      <div><span>Доп. услуги</span><strong>{loading || !folio ? "…" : money(folio.totals.extras_kgs)}</strong></div>
      <div><span>Общий счёт</span><strong>{loading || !folio ? "…" : money(folio.totals.grand_total_kgs)}</strong></div>
      <div><span>Оплачено</span><strong>{loading || !folio ? "…" : money(folio.totals.paid_kgs)}</strong></div>
      <div className={folio?.totals.remaining_kgs ? styles.due : styles.ok}><span>Остаток</span><strong>{loading || !folio ? "…" : money(folio.totals.remaining_kgs)}</strong>{Boolean(folio?.totals.overpaid_kgs) && <small>Переплата {money(folio!.totals.overpaid_kgs)}</small>}</div>
    </div>

    <div className={styles.grid}>
      {canManagePayments ? <form className={styles.card} onSubmit={recordPayment}>
        <div className={styles.cardHead}><div><small>Касса / менеджер</small><h4>Принять оплату</h4></div></div>
        <div className={styles.two}><label>Сумма, сом<input type="number" min="1" step="1" value={amount} onChange={(e) => setAmount(e.target.value)} required /></label><label>Способ<select value={method} onChange={(e) => setMethod(e.target.value)}>{METHODS.map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label></div>
        <label>Фактическое время оплаты<input type="datetime-local" value={paidAt} onChange={(e) => setPaidAt(e.target.value)} required /></label>
        <div className={styles.two}><label>Чек / транзакция<input value={externalRef} maxLength={180} onChange={(e) => setExternalRef(e.target.value)} placeholder="необязательно" /></label><label>Комментарий<input value={note} maxLength={500} onChange={(e) => setNote(e.target.value)} placeholder="необязательно" /></label></div>
        <button className={styles.primary} disabled={busy === "payment"}>{busy === "payment" ? "Записываю…" : "Принять оплату"}</button>
      </form> : <div className={styles.card}>
        <div className={styles.cardHead}><div><small>Финансовые права</small><h4>Оплаты — только просмотр</h4></div></div>
        <p className={styles.hint}>Ресепшен видит историю и остаток. Запись факта получения денег и списание начислений доступны OWNER / MANAGER.</p>
      </div>}

      <form className={styles.card} onSubmit={createCharge}>
        <div className={styles.cardHead}><div><small>Дополнительные услуги</small><h4>Добавить начисление</h4></div></div>
        <div className={styles.two}><label>Код<select value={chargeCode} onChange={(e) => setChargeCode(e.target.value)}><option value="EXTRA_SERVICE">Доп. услуга</option><option value="DINING">Питание</option><option value="TRANSFER">Трансфер</option><option value="HOUSEKEEPING">Уборка</option><option value="LINEN">Бельё</option><option value="OTHER">Другое</option></select></label><label>Сумма, сом<input type="number" min="1" step="1" value={chargeAmount} onChange={(e) => setChargeAmount(e.target.value)} required /></label></div>
        <label>Описание<input value={chargeDescription} maxLength={500} onChange={(e) => setChargeDescription(e.target.value)} placeholder="Например: дополнительная уборка" required /></label>
        <button disabled={busy === "charge"}>{busy === "charge" ? "Добавляю…" : "Добавить в folio"}</button>
        <p className={styles.hint}>Начисление увеличивает долг гостя, но не считается оплатой.</p>
      </form>
    </div>

    <div className={styles.history}>
      <section><h4>Начисления · {folio?.charges.length ?? 0}</h4>{!folio?.charges.length ? <p>Дополнительных начислений нет.</p> : folio.charges.map((charge) => <div key={charge.id} data-status={charge.status}><span><strong>{charge.description}</strong><small>{charge.code} · {charge.source_type} · {charge.service_date || charge.created_at}</small></span><b>{money(charge.amount_kgs)}</b><em>{charge.status}</em>{charge.status === "OPEN" && canCloseCharges && <span className={styles.rowActions}><button disabled={busy === charge.id} onClick={() => void closeCharge(charge, "WAIVED")}>Списать</button><button disabled={busy === charge.id} onClick={() => void closeCharge(charge, "VOID")}>Аннулировать</button></span>}</div>)}</section>
      <section><h4>История оплат · {folio?.payments.length ?? 0}</h4>{!folio?.payments.length ? <p>Оплат пока нет.</p> : [...folio.payments].reverse().map((payment) => <div key={payment.id}><span><strong>{METHODS.find(([value]) => value === payment.method)?.[1] || payment.method}</strong><small>Оплачено: {payment.paid_at || "—"}<br />Внесено в PMS: {payment.recorded_at}</small></span><b>{money(payment.amount_kgs)}</b><em>{payment.status}</em></div>)}</section>
    </div>
  </section>;
}
