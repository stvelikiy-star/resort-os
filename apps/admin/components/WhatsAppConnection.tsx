"use client";

import { useEffect, useRef, useState } from "react";
import styles from "./WhatsAppWorkspace.module.css";

type Connection = { configured: boolean; state: string; account_authorized: boolean };
const LABELS: Record<string, string> = {
  disabled: "Подключение GreenAPI не настроено",
  notAuthorized: "Номер ожидает сканирования QR",
  authorized: "Номер авторизован в GreenAPI",
  blocked: "GreenAPI сообщает о блокировке номера",
  sleepMode: "Номер находится в спящем режиме",
  starting: "GreenAPI запускает подключение",
  yellowCard: "GreenAPI сообщает об ограничении номера",
};

export default function WhatsAppConnection() {
  const [connection, setConnection] = useState<Connection | null>(null);
  const [qr, setQr] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const pending = useRef<AbortController | null>(null);

  useEffect(() => () => pending.current?.abort(), []);
  useEffect(() => {
    if (!qr) return;
    const timer = window.setTimeout(() => setQr(""), 20_000);
    return () => window.clearTimeout(timer);
  }, [qr]);

  async function check(getQr = false) {
    if (pending.current) return;
    const controller = new AbortController();
    pending.current = controller;
    setBusy(true); setError(""); setQr("");
    try {
      const response = await fetch(`/core/api/v1/admin/whatsapp/connection${getQr ? "/qr" : ""}`, {
        method: getQr ? "POST" : "GET", cache: "no-store", signal: controller.signal,
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        setConnection(null);
        setError(response.status === 401 || response.status === 403
          ? "Войдите под учётной записью собственника."
          : response.status === 429 ? "Подождите минуту перед повторной проверкой."
          : response.status === 503 ? "Подключение GreenAPI для этой гостиницы ещё не настроено."
          : "Не удалось проверить GreenAPI. Повторите проверку позже.");
        return;
      }
      if (getQr) {
        if (body.state === "authorized") {
          setConnection({ configured: true, state: "authorized", account_authorized: true });
        } else if (typeof body.qr_data_url === "string" && body.qr_data_url.startsWith("data:image/png;base64,")) {
          setConnection({ configured: true, state: "notAuthorized", account_authorized: false });
          setQr(body.qr_data_url);
        } else {
          setConnection(null);
          setError("GreenAPI не вернул действительный QR-код. Повторите проверку.");
        }
      } else {
        setConnection(body as Connection);
      }
    } catch {
      if (!controller.signal.aborted) {
        setConnection(null);
        setError("Не удалось связаться с сервером MARINA SMART.");
      }
    } finally {
      pending.current = null;
      if (!controller.signal.aborted) setBusy(false);
    }
  }

  return <section aria-label="Авторизация GreenAPI" className={styles.connection}>
    <p role="status">{busy ? "Проверяю GreenAPI…" : connection
      ? LABELS[connection.state] || "Состояние подключения неизвестно"
      : "Состояние номера ещё не проверено"}</p>
    <div className={styles.actions}>
      <button type="button" className="btn" disabled={busy} onClick={() => void check()}>Проверить подключение</button>
      <button type="button" className="btn primary" disabled={busy || connection?.account_authorized === true}
        onClick={() => void check(true)}>Получить QR-код</button>
    </div>
    {error && <p role="alert">{error}</p>}
    {qr && <figure className={styles.qr}>
      {/* A short-lived PNG returned by our authenticated server; no provider URL or key. */}
      <img src={qr} width={260} height={260} alt="QR-код подключения WhatsApp гостиницы" />
      <figcaption>WhatsApp → Связанные устройства → Привязать устройство. QR скрывается через 20 секунд. После сканирования нажмите «Проверить подключение».</figcaption>
    </figure>}
    <p className={styles.small}>Авторизация номера не подтверждает приём и доставку сообщений. Автоответы ИИ включаются отдельно после проверки переписки.</p>
  </section>;
}
