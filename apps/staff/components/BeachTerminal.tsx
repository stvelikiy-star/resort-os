"use client";

import { FormEvent, useCallback, useMemo, useRef, useState } from "react";

type BalanceResult = {
  wallet_id: string;
  bracelet_id: string;
  booking_number: string;
  balance_kgs: number;
  wallet_status: string;
  bracelet_status: string;
  label?: string | null;
};

type ChargeResult = {
  transaction_id: string;
  wallet_id: string;
  balance_before_kgs: number;
  balance_after_kgs: number;
  amount_kgs: number;
  hotel_commission_kgs: number;
  partner_net_kgs: number;
  commission_bps: number;
  idempotent_replay: boolean;
};

type NdefReadingEvent = Event & { serialNumber?: string };

type NdefReaderInstance = EventTarget & {
  scan: (options?: { signal?: AbortSignal }) => Promise<void>;
  onreading: ((event: NdefReadingEvent) => void) | null;
  onreadingerror: (() => void) | null;
};

type NdefReaderConstructor = new () => NdefReaderInstance;

declare global {
  interface Window {
    NDEFReader?: NdefReaderConstructor;
  }
}

function money(value: number) {
  return new Intl.NumberFormat("ru-RU").format(value);
}

function normalizeUid(value: string) {
  return value.trim();
}

function apiError(body: unknown, fallback: string) {
  if (body && typeof body === "object" && "detail" in body && typeof body.detail === "string") return body.detail;
  return fallback;
}

export default function BeachTerminal() {
  const [braceletUid, setBraceletUid] = useState("");
  const [balance, setBalance] = useState<BalanceResult | null>(null);
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("");
  const [lastCharge, setLastCharge] = useState<ChargeResult | null>(null);
  const [busy, setBusy] = useState<"scan" | "balance" | "charge" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [networkUncertain, setNetworkUncertain] = useState(false);
  const chargeKeyRef = useRef<string | null>(null);
  const scanControllerRef = useRef<AbortController | null>(null);

  const nfcSupported = typeof window !== "undefined" && typeof window.NDEFReader === "function";
  const amountNumber = Number(amount);
  const canCharge = Boolean(balance && amountNumber > 0 && amountNumber <= balance.balance_kgs && !busy);

  const commissionPreview = useMemo(() => {
    if (!Number.isFinite(amountNumber) || amountNumber <= 0) return null;
    const bps = lastCharge?.commission_bps ?? 500;
    const hotel = Math.round((amountNumber * bps) / 10000);
    return { bps, hotel, partner: amountNumber - hotel };
  }, [amountNumber, lastCharge?.commission_bps]);

  const lookupBalance = useCallback(async (uidOverride?: string) => {
    const uid = normalizeUid(uidOverride ?? braceletUid);
    if (!uid) {
      setError("Приложите браслет или введите его UID.");
      return;
    }
    setBusy("balance");
    setError(null);
    setLastCharge(null);
    setNetworkUncertain(false);
    chargeKeyRef.current = null;
    try {
      const response = await fetch("/core/api/v1/beach/balance", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ bracelet_uid: uid }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(apiError(body, "Не удалось прочитать баланс"));
      setBraceletUid(uid);
      setBalance(body as BalanceResult);
    } catch (cause) {
      setBalance(null);
      setError(cause instanceof Error ? cause.message : "Ошибка чтения браслета");
    } finally {
      setBusy(null);
    }
  }, [braceletUid]);

  async function scanBracelet() {
    if (!window.NDEFReader) {
      setError("NFC API недоступен в этом браузере. Введите UID браслета вручную или используйте поддерживаемое устройство.");
      return;
    }
    scanControllerRef.current?.abort();
    const controller = new AbortController();
    scanControllerRef.current = controller;
    setBusy("scan");
    setError(null);
    try {
      const reader = new window.NDEFReader();
      reader.onreading = (event) => {
        const serial = normalizeUid(event.serialNumber || "");
        controller.abort();
        scanControllerRef.current = null;
        setBusy(null);
        if (!serial) {
          setError("Телефон прочитал NFC-метку, но не передал серийный номер. Используйте ручной ввод UID.");
          return;
        }
        setBraceletUid(serial);
        void lookupBalance(serial);
      };
      reader.onreadingerror = () => {
        controller.abort();
        scanControllerRef.current = null;
        setBusy(null);
        setError("Не удалось прочитать браслет. Приложите его повторно.");
      };
      await reader.scan({ signal: controller.signal });
    } catch (cause) {
      scanControllerRef.current = null;
      setBusy(null);
      if (cause instanceof DOMException && cause.name === "AbortError") return;
      setError(cause instanceof Error ? cause.message : "NFC-сканирование недоступно");
    }
  }

  async function charge(event: FormEvent) {
    event.preventDefault();
    const uid = normalizeUid(braceletUid);
    const parsedAmount = Number(amount);
    if (!balance || !uid || !Number.isInteger(parsedAmount) || parsedAmount <= 0) {
      setError("Укажите целую сумму в сомах и сначала прочитайте баланс браслета.");
      return;
    }
    if (parsedAmount > balance.balance_kgs) {
      setError("На браслете недостаточно средств.");
      return;
    }

    const idempotencyKey = chargeKeyRef.current ?? `beach-${crypto.randomUUID()}`;
    chargeKeyRef.current = idempotencyKey;
    setBusy("charge");
    setError(null);
    setNetworkUncertain(false);
    try {
      const response = await fetch("/core/api/v1/beach/charge", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          bracelet_uid: uid,
          amount_kgs: parsedAmount,
          idempotency_key: idempotencyKey,
          description: description.trim() || null,
        }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        chargeKeyRef.current = null;
        throw new Error(apiError(body, "Списание отклонено"));
      }
      const result = body as ChargeResult;
      setLastCharge(result);
      setBalance((current) => current ? { ...current, balance_kgs: result.balance_after_kgs } : current);
      setAmount("");
      setDescription("");
      chargeKeyRef.current = null;
    } catch (cause) {
      if (cause instanceof TypeError) {
        setNetworkUncertain(true);
        setError("Связь прервалась до подтверждения результата. Нажмите «Повторить безопасно» — тот же ключ не позволит списать дважды.");
      } else {
        setError(cause instanceof Error ? cause.message : "Ошибка списания");
      }
    } finally {
      setBusy(null);
    }
  }

  function resetBracelet() {
    scanControllerRef.current?.abort();
    scanControllerRef.current = null;
    chargeKeyRef.current = null;
    setBraceletUid("");
    setBalance(null);
    setAmount("");
    setDescription("");
    setLastCharge(null);
    setNetworkUncertain(false);
    setError(null);
  }

  return (
    <section className="beach-terminal">
      <div className="terminal-hero">
        <div>
          <p className="eyebrow">Пляж · NFC-терминал</p>
          <h2>Списание с браслета</h2>
          <p>Каждое списание атомарно. Повтор одного запроса не списывает деньги второй раз.</p>
        </div>
        <span className={`nfc-indicator ${nfcSupported ? "supported" : "fallback"}`}>{nfcSupported ? "NFC готов" : "Ручной UID"}</span>
      </div>

      <div className="terminal-card scan-card">
        <div className="terminal-step"><span>1</span><div><strong>Браслет гостя</strong><small>UID используется только для запроса и не хранится в открытом виде.</small></div></div>
        <div className="scan-actions">
          <button className="primary scan-button" type="button" onClick={scanBracelet} disabled={Boolean(busy)}>{busy === "scan" ? "Жду браслет…" : "Приложить NFC"}</button>
          <span className="or">или</span>
          <div className="uid-row">
            <input value={braceletUid} onChange={(event) => { setBraceletUid(event.target.value); setBalance(null); setLastCharge(null); chargeKeyRef.current = null; }} placeholder="UID браслета" autoCapitalize="off" autoCorrect="off" spellCheck={false} />
            <button className="ghost" type="button" onClick={() => lookupBalance()} disabled={Boolean(busy) || !braceletUid.trim()}>{busy === "balance" ? "…" : "Баланс"}</button>
          </div>
        </div>
      </div>

      {balance && <div className="wallet-card">
        <div><span>Доступно</span><strong>{money(balance.balance_kgs)} <small>KGS</small></strong></div>
        <div className="wallet-meta"><span>{balance.booking_number}</span>{balance.label && <span>{balance.label}</span>}<span>{balance.bracelet_status}</span></div>
        <button className="link-button" type="button" onClick={resetBracelet}>Другой браслет</button>
      </div>}

      {balance && <form className="terminal-card charge-card" onSubmit={charge}>
        <div className="terminal-step"><span>2</span><div><strong>Сумма услуги</strong><small>Целое количество сомов.</small></div></div>
        <div className="amount-wrap"><input inputMode="numeric" pattern="[0-9]*" value={amount} onChange={(event) => setAmount(event.target.value.replace(/\D/g, ""))} placeholder="0" aria-label="Сумма в KGS" /><b>KGS</b></div>
        <input className="description-input" value={description} onChange={(event) => setDescription(event.target.value)} maxLength={500} placeholder="Услуга, например: гидроцикл 10 мин" />
        {commissionPreview && <div className="commission-preview"><div><span>Комиссия отеля</span><strong>{money(commissionPreview.hotel)} KGS</strong></div><div><span>Партнёру</span><strong>{money(commissionPreview.partner)} KGS</strong></div></div>}
        <button className="primary charge-button" disabled={!canCharge}>{busy === "charge" ? "Провожу…" : networkUncertain ? "Повторить безопасно" : amountNumber > 0 ? `Списать ${money(amountNumber)} KGS` : "Введите сумму"}</button>
      </form>}

      {error && <div className={`terminal-message ${networkUncertain ? "warning" : "error"}`}>{error}</div>}

      {lastCharge && <div className="receipt-card">
        <div className="receipt-check">✓</div>
        <p className="eyebrow">Операция проведена</p>
        <h2>{money(lastCharge.amount_kgs)} KGS</h2>
        <div className="receipt-grid">
          <span>Баланс</span><strong>{money(lastCharge.balance_before_kgs)} → {money(lastCharge.balance_after_kgs)} KGS</strong>
          <span>Отелю {lastCharge.commission_bps / 100}%</span><strong>{money(lastCharge.hotel_commission_kgs)} KGS</strong>
          <span>Партнёру</span><strong>{money(lastCharge.partner_net_kgs)} KGS</strong>
        </div>
        {lastCharge.idempotent_replay && <div className="replay-badge">Безопасный повтор · повторного списания не было</div>}
        <small className="transaction-id">ID {lastCharge.transaction_id}</small>
      </div>}
    </section>
  );
}
