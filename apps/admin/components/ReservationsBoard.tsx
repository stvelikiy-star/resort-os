"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type Reservation = {
  id: string;
  bookingNumber: string;
  status: string;
  checkIn: string;
  checkOut: string;
  adults: number;
  children: number;
  totalKgs: number;
  firstName?: string | null;
  phone?: string | null;
  room_code?: string | null;
  room_type_name?: string | null;
};

type NfcWalletSummary = {
  wallet_id: string;
  reservation_id: string;
  guest_id: string;
  booking_number: string;
  reservation_status: string;
  guest_name?: string | null;
  balance_kgs: number;
  wallet_status: string;
  bracelet_id?: string | null;
  bracelet_status?: string | null;
  bracelet_label?: string | null;
  issued_at?: string | null;
};

type NfcIssueResult = {
  idempotent_replay: boolean;
  wallet_id: string;
  bracelet_id: string;
  booking_number: string;
  balance_kgs: number;
  wallet_status: string;
  bracelet_status: string;
  label?: string | null;
};

type NdefReader = {
  scan: () => Promise<void>;
  addEventListener: (
    type: "reading",
    listener: (event: { serialNumber?: string }) => void,
    options?: { once?: boolean },
  ) => void;
};

type NdefReaderConstructor = new () => NdefReader;

const fmt = (value: number) => new Intl.NumberFormat("ru-RU").format(value) + " сом";
const statusLabels: Record<string, string> = {
  GUARANTEED: "Гарантирована",
  CHECKED_IN: "Проживает",
  CHECKED_OUT: "Выехал",
  CANCELLED: "Отменена",
  NO_SHOW: "Не заехал",
};

export default function ReservationsBoard() {
  const [items, setItems] = useState<Reservation[]>([]);
  const [wallets, setWallets] = useState<Record<string, NfcWalletSummary>>({});
  const [filter, setFilter] = useState("ACTIVE");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [issueTarget, setIssueTarget] = useState<Reservation | null>(null);
  const [braceletUid, setBraceletUid] = useState("");
  const [initialBalance, setInitialBalance] = useState("0");
  const [issueBusy, setIssueBusy] = useState(false);
  const [issueError, setIssueError] = useState<string | null>(null);
  const [scanNotice, setScanNotice] = useState<string | null>(null);
  const [issueResult, setIssueResult] = useState<NfcIssueResult | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [reservationResponse, walletResponse] = await Promise.all([
        fetch("/core/api/v1/admin/booking/reservations?limit=250", { cache: "no-store" }),
        fetch("/core/api/v1/admin/nfc/wallets", { cache: "no-store" }),
      ]);
      if (!reservationResponse.ok) throw new Error("Не удалось загрузить брони");
      if (!walletResponse.ok) throw new Error("Не удалось загрузить NFC-кошельки");
      const reservationData = await reservationResponse.json();
      const walletData = await walletResponse.json();
      setItems(reservationData.items || []);
      const nextWallets: Record<string, NfcWalletSummary> = {};
      for (const wallet of (walletData.items || []) as NfcWalletSummary[]) {
        nextWallets[wallet.reservation_id] = wallet;
      }
      setWallets(nextWallets);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка загрузки");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const visible = useMemo(() => items.filter((item) => {
    if (filter === "ALL") return true;
    if (filter === "ACTIVE") return ["GUARANTEED", "CHECKED_IN"].includes(item.status);
    return item.status === filter;
  }), [items, filter]);

  async function transition(item: Reservation, action: "check-in" | "check-out") {
    setBusy(item.id);
    setError(null);
    try {
      const response = await fetch(`/core/api/v1/admin/stays/reservations/${item.id}/${action}`, { method: "POST" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Не удалось изменить статус проживания");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка операции");
    } finally {
      setBusy(null);
    }
  }

  function openNfcIssue(item: Reservation) {
    setIssueTarget(item);
    setBraceletUid("");
    setInitialBalance("0");
    setIssueError(null);
    setScanNotice(null);
    setIssueResult(null);
  }

  function closeNfcIssue() {
    if (issueBusy) return;
    setIssueTarget(null);
    setIssueResult(null);
    setIssueError(null);
    setScanNotice(null);
  }

  async function scanNfc() {
    setIssueError(null);
    setScanNotice(null);
    const NDEFReaderCtor = (window as unknown as { NDEFReader?: NdefReaderConstructor }).NDEFReader;
    if (!NDEFReaderCtor) {
      setScanNotice("Web NFC на этом устройстве недоступен. Введите UID вручную или используйте считыватель как клавиатуру.");
      return;
    }
    try {
      const reader = new NDEFReaderCtor();
      await reader.scan();
      setScanNotice("Поднесите браслет к телефону…");
      reader.addEventListener("reading", (event) => {
        const serial = (event.serialNumber || "").trim();
        if (!serial) {
          setScanNotice("Браслет считан, но устройство не передало UID. Используйте ручной ввод.");
          return;
        }
        setBraceletUid(serial);
        setScanNotice("Браслет считан. Проверьте UID и подтвердите выдачу.");
      }, { once: true });
    } catch (e) {
      setScanNotice(e instanceof Error ? `NFC недоступен: ${e.message}` : "Не удалось запустить NFC-считывание");
    }
  }

  async function issueBracelet(event: FormEvent) {
    event.preventDefault();
    if (!issueTarget) return;
    setIssueError(null);
    setIssueResult(null);
    const normalizedUid = braceletUid.trim();
    const balance = Number(initialBalance);
    if (normalizedUid.length < 4) {
      setIssueError("UID браслета должен содержать минимум 4 символа");
      return;
    }
    if (!Number.isInteger(balance) || balance < 0 || balance > 10_000_000) {
      setIssueError("Стартовый баланс должен быть целым числом от 0 до 10 000 000 сом");
      return;
    }

    setIssueBusy(true);
    try {
      const label = `${issueTarget.room_code ? `№${issueTarget.room_code}` : issueTarget.bookingNumber} · ${issueTarget.firstName || "Гость"}`.slice(0, 80);
      const response = await fetch("/core/api/v1/admin/nfc/wallets", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          reservation_id: issueTarget.id,
          bracelet_uid: normalizedUid,
          initial_balance_kgs: balance,
          label,
        }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Не удалось выдать NFC-браслет");
      setIssueResult(body as NfcIssueResult);
      setScanNotice(body.idempotent_replay ? "Этот браслет уже был выдан этой брони. Повторного начисления не произошло." : "Браслет выдан и NFC-кошелёк активирован.");
      await load();
    } catch (e) {
      setIssueError(e instanceof Error ? e.message : "Ошибка выдачи NFC-браслета");
    } finally {
      setIssueBusy(false);
    }
  }

  return (
    <main className="work-shell">
      <div className="work-head">
        <div><p className="eyebrow">PMS · проживание</p><h1>Брони и заезды</h1><p className="subtitle">Гарантированные брони, проживающие гости, выезды и NFC-браслеты.</p></div>
        <div className="work-actions"><select value={filter} onChange={(e) => setFilter(e.target.value)}><option value="ACTIVE">Активные</option><option value="GUARANTEED">Ожидают заезд</option><option value="CHECKED_IN">Проживают</option><option value="CHECKED_OUT">Выехали</option><option value="ALL">Все</option></select><button className="btn" onClick={load}>Обновить</button></div>
      </div>
      {error && <div className="error-box">{error}</div>}
      {loading ? <div className="loading">Загрузка броней…</div> : <div className="reservation-list">
        {visible.length === 0 && <div className="empty">Броней в этом фильтре нет.</div>}
        {visible.map((item) => {
          const wallet = wallets[item.id];
          return <article className="reservation-card" key={item.id}>
            <div className="reservation-id"><span>{statusLabels[item.status] || item.status}</span><strong>{item.bookingNumber}</strong></div>
            <div><span className="field-label">Гость</span><b>{item.firstName || "Без имени"}</b>{item.phone && <a href={`tel:${item.phone}`}>{item.phone}</a>}</div>
            <div><span className="field-label">Номер</span><b>{item.room_code || "—"}</b><small>{item.room_type_name || ""}</small></div>
            <div><span className="field-label">Даты</span><b>{item.checkIn} → {item.checkOut}</b><small>{item.adults} взр. · {item.children} дет.</small></div>
            <div><span className="field-label">Стоимость</span><b>{fmt(item.totalKgs)}</b></div>
            <div className="reservation-nfc">
              <span className="field-label">NFC</span>
              {wallet ? <><b className={`nfc-status ${wallet.wallet_status === "ACTIVE" ? "active" : ""}`}>{wallet.wallet_status === "ACTIVE" ? "Кошелёк активен" : wallet.wallet_status}</b><small>{fmt(wallet.balance_kgs)}{wallet.bracelet_label ? ` · ${wallet.bracelet_label}` : ""}</small></> : <><b className="nfc-status">Не выдан</b>{item.status === "CHECKED_IN" && <small>Можно выдать после оформленного заезда</small>}</>}
            </div>
            <div className="reservation-actions">
              {item.status === "GUARANTEED" && <button className="btn primary" disabled={busy === item.id} onClick={() => transition(item, "check-in")}>Оформить заезд</button>}
              {item.status === "CHECKED_IN" && !wallet && <button className="btn nfc" disabled={busy === item.id} onClick={() => openNfcIssue(item)}>Выдать NFC-браслет</button>}
              {item.status === "CHECKED_IN" && <button className="btn primary" disabled={busy === item.id} onClick={() => transition(item, "check-out")}>Оформить выезд</button>}
            </div>
          </article>;
        })}
      </div>}

      {issueTarget && <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) closeNfcIssue(); }}>
        <section className="nfc-modal" role="dialog" aria-modal="true" aria-labelledby="nfc-modal-title">
          <div className="nfc-modal-head">
            <div><p className="eyebrow">Ресепшен · NFC</p><h2 id="nfc-modal-title">Выдача браслета</h2><p>{issueTarget.bookingNumber} · {issueTarget.firstName || "Гость"} · номер {issueTarget.room_code || "—"}</p></div>
            <button className="btn" type="button" disabled={issueBusy} onClick={closeNfcIssue}>Закрыть</button>
          </div>

          {issueResult ? <div className="nfc-success">
            <strong>Браслет активен</strong>
            <span>Баланс: {fmt(issueResult.balance_kgs)}</span>
            <small>{issueResult.idempotent_replay ? "Повтор распознан безопасно — баланс не начислялся второй раз." : "Кошелёк создан, стартовый баланс записан в ledger."}</small>
            <button className="btn primary" type="button" onClick={closeNfcIssue}>Готово</button>
          </div> : <form className="nfc-issue-form" onSubmit={issueBracelet}>
            <label><span>UID браслета</span><div className="nfc-input-row"><input value={braceletUid} onChange={(e) => setBraceletUid(e.target.value)} placeholder="Например 04:A1:B2:C3" autoFocus required minLength={4} maxLength={160} /><button className="btn" type="button" onClick={scanNfc}>Считать NFC</button></div></label>
            <label><span>Стартовый баланс, сом</span><input type="number" min="0" max="10000000" step="1" inputMode="numeric" value={initialBalance} onChange={(e) => setInitialBalance(e.target.value)} required /></label>
            <div className="nfc-warning"><strong>Контроль выдачи</strong><span>Браслет можно привязать только к брони со статусом CHECKED_IN. Сырой UID на сервере не хранится.</span></div>
            {scanNotice && <div className="notice-box">{scanNotice}</div>}
            {issueError && <div className="error-box compact">{issueError}</div>}
            <button className="btn primary nfc-submit" disabled={issueBusy}>{issueBusy ? "Выдаю…" : "Выдать браслет"}</button>
          </form>}
        </section>
      </div>}
    </main>
  );
}
