"use client";

import { useEffect, useRef, useState } from "react";
import styles from "./WhatsAppWorkspace.module.css";

type Connection = { configured: boolean; state: string; account_authorized: boolean; messaging_verified?: boolean; ai_auto_send?: boolean };
const LABELS: Record<string, string> = {
  disabled: "Подключение GreenAPI не настроено",
  notAuthorized: "Номер ожидает сканирования QR",
  authorized: "Номер авторизован в GreenAPI",
  blocked: "GreenAPI сообщает о блокировке номера",
  sleepMode: "Номер находится в спящем режиме",
  starting: "GreenAPI запускает подключение",
  qrWaiting: "Ожидаем QR-код от GREEN-API",
  passkeyRequired: "Подтвердите привязку устройства в WhatsApp на телефоне, затем запросите QR снова",
  yellowCard: "GreenAPI сообщает об ограничении номера",
  suspended: "На номере действуют временные ограничения GreenAPI. Проверьте состояние у провайдера.",
};

export default function WhatsAppConnection() {
  const [connection, setConnection] = useState<Connection | null>(null);
  const [qr, setQr] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [pairing, setPairing] = useState(false);
  const pairingDeadline = useRef(0);
  const pending = useRef<AbortController | null>(null);

  useEffect(() => {
    // Opening the owner cabinet also supports the first pairing done directly
    // in GREEN-API. Never create a QR or disconnect a phone automatically.
    void check();
    function hidePairing() {
      if (document.visibilityState === "hidden") {
        pending.current?.abort(); pending.current = null;
        setPairing(false); setQr(""); setBusy(false);
      } else if (document.visibilityState === "visible") {
        void check();
      }
    }
    document.addEventListener("visibilitychange", hidePairing);
    return () => {
      document.removeEventListener("visibilitychange", hidePairing);
      pending.current?.abort(); pending.current = null;
    };
    // The initial check is read-only; subsequent checks are explicit.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => {
    if (!qr) return;
    const timer = window.setTimeout(() => setQr(""), 20_000);
    return () => window.clearTimeout(timer);
  }, [qr]);

  useEffect(() => {
    if (!pairing || busy) return;
    const timer = window.setTimeout(() => {
      if (Date.now() >= pairingDeadline.current) {
        setPairing(false); setQr("");
        setError("Время подключения истекло. Нажмите «Получить QR-код», чтобы повторить.");
      } else if (document.visibilityState === "hidden") {
        setPairing(false); setQr("");
      } else {
        void check(true, true);
      }
    }, 5_000);
    return () => window.clearTimeout(timer);
  }, [pairing, busy]);

  function stopPairing() {
    setPairing(false); setQr(""); setError(""); setBusy(false);
    pending.current?.abort(); pending.current = null;
  }

  async function check(getQr = false, automatic = false) {
    if (pending.current) return;
    const controller = new AbortController();
    pending.current = controller;
    if (!automatic) {
      setQr(""); setPairing(getQr);
      if (getQr) pairingDeadline.current = Date.now() + 90_000;
    }
    if (getQr) setQr(""); // Never display a prior QR during a new provider request.
    setBusy(true); setError("");
    try {
      const response = await fetch(`/core/api/v1/admin/whatsapp/connection${getQr ? "/qr" : ""}`, {
        method: getQr ? "POST" : "GET", cache: "no-store", signal: controller.signal,
      });
      const body = await response.json().catch(() => ({}));
      if (controller.signal.aborted) return;
      if (!response.ok) {
        setPairing(false); setQr(""); setConnection(null);
        setError(response.status === 401 || response.status === 403
          ? "Войдите под учётной записью собственника."
          : response.status === 429 ? "Подождите минуту перед повторной проверкой."
          : response.status === 503 ? "Подключение GreenAPI для этой гостиницы ещё не настроено."
          : "Не удалось проверить GreenAPI. Повторите проверку позже.");
        return;
      }
      if (getQr) {
        if (body.state === "authorized") {
          setPairing(false); setQr("");
          setConnection({ configured: true, state: "authorized", account_authorized: true });
        } else if (typeof body.qr_data_url === "string" && body.qr_data_url.startsWith("data:image/png;base64,")) {
          setConnection({ configured: true, state: "notAuthorized", account_authorized: false });
          setQr(body.qr_data_url);
        } else if (body.state === "qrWaiting" || body.state === "passkeyRequired") {
          setQr("");
          setConnection({ configured: true, state: body.state, account_authorized: false });
          if (body.state === "passkeyRequired") setPairing(false);
        } else {
          setPairing(false); setQr(""); setConnection(null);
          setError("GreenAPI не вернул действительный QR-код. Повторите проверку.");
        }
      } else {
        if (typeof body.configured !== "boolean" || typeof body.state !== "string" || typeof body.account_authorized !== "boolean") {
          setConnection(null);
          setError("Сервер вернул неизвестное состояние подключения.");
          return;
        }
        setConnection(body as Connection);
      }
    } catch {
      if (!controller.signal.aborted) {
        setPairing(false); setQr(""); setConnection(null);
        setError("Не удалось связаться с сервером MARINA SMART.");
      }
    } finally {
      if (pending.current === controller) pending.current = null;
      if (!controller.signal.aborted) setBusy(false);
    }
  }

  return <section aria-label="Авторизация GreenAPI" className={styles.connection}>
    <p role="status">{busy ? "Проверяю GreenAPI…" : connection
      ? LABELS[connection.state] || "Состояние подключения неизвестно"
      : "Состояние номера ещё не проверено"}</p>
    <div className={styles.actions}>
      <button type="button" className="btn" disabled={busy} onClick={() => void check()}>Проверить подключение</button>
      <button type="button" className="btn primary" disabled={busy || pairing || !connection?.configured || connection.account_authorized || !["notAuthorized", "qrWaiting", "passkeyRequired"].includes(connection.state)}
        onClick={() => void check(true)}>Получить QR-код</button>
      {pairing && <button type="button" className="btn" onClick={stopPairing}>Остановить подключение</button>}
    </div>
    {pairing && <p role="status">QR обновляется автоматически. Отсканируйте его в WhatsApp Business → Связанные устройства → Привязать устройство.</p>}
    {connection && <div className={styles.tiles} aria-label="Готовность WhatsApp">
      <article><strong>Номер</strong><span>{connection.account_authorized ? "Авторизован" : "Не авторизован"}</span></article>
      <article><strong>Переписка</strong><span>{connection.messaging_verified === true ? "Проверена" : "Приём и доставка ещё не подтверждены"}</span></article>
      <article><strong>MARINA AI</strong><span>{connection.ai_auto_send === true ? "Автоответы включены" : "Автоответы выключены"}</span></article>
    </div>}
    {error && <p role="alert">{error}</p>}
    {qr && <figure className={styles.qr}>
      {/* A short-lived PNG returned by our authenticated server; no provider URL or key. */}
      <img src={qr} width={260} height={260} alt="QR-код подключения WhatsApp гостиницы" />
      <figcaption>WhatsApp → Связанные устройства → Привязать устройство. QR скрывается через 20 секунд. Подключение проверяется автоматически; ожидание — до 90 секунд.</figcaption>
    </figure>}
    <p className={styles.small}>Если номер уже привязан в GREEN-API, достаточно проверить подключение. Повторное сканирование нужно только при потере авторизации. Авторизация номера не подтверждает приём и доставку сообщений. Автоответы ИИ включаются отдельно после проверки переписки.</p>
  </section>;
}
