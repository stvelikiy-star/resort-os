"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import styles from "./DiningReadyRealtime.module.css";

type User = { id: string; role: string };
type ReadyOrder = {
  id: string;
  order_number: string;
  table_code?: string | null;
  table_name?: string | null;
  room_code?: string | null;
  guest_count: number;
  total_kgs: number;
  ready_at?: string | null;
};
type ReadyMessage =
  | { type: "dining.ready.snapshot"; orders: ReadyOrder[]; scope: string }
  | { type: "dining.order.ready"; order: ReadyOrder }
  | { type: "heartbeat" };

const ALLOWED = new Set(["OWNER", "MANAGER", "DINING_STAFF"]);

function websocketBase() {
  const configured = process.env.NEXT_PUBLIC_CORE_WS_URL?.replace(/\/$/, "");
  if (configured) return configured;
  if (typeof window === "undefined") return "";
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const port = window.location.port === "3002" ? "8000" : window.location.port;
  return `${protocol}//${window.location.hostname}${port ? `:${port}` : ""}`;
}

function destination(order: ReadyOrder) {
  if (order.table_code) return `${order.table_code}${order.table_name ? ` · ${order.table_name}` : ""}`;
  if (order.room_code) return `Номер ${order.room_code}`;
  return "Заказ без точки обслуживания";
}

export default function DiningReadyRealtime() {
  const [user, setUser] = useState<User | null>(null);
  const [connection, setConnection] = useState<"OFF" | "CONNECTING" | "LIVE">("OFF");
  const [readyCount, setReadyCount] = useState(0);
  const [alert, setAlert] = useState<ReadyOrder | null>(null);
  const [notificationPermission, setNotificationPermission] = useState<NotificationPermission | "unsupported">("unsupported");
  const reconnectTimer = useRef<number | null>(null);

  useEffect(() => {
    if (typeof Notification !== "undefined") setNotificationPermission(Notification.permission);
    fetch("/core/api/v1/auth/me", { cache: "no-store" })
      .then(async (response) => response.ok ? response.json() : null)
      .then((body) => setUser(body && ALLOWED.has(body.role) ? body : null))
      .catch(() => setUser(null));
  }, []);

  useEffect(() => {
    if (!user) return;
    let stopped = false;
    let socket: WebSocket | null = null;

    const connect = () => {
      if (stopped) return;
      const base = websocketBase();
      if (!base) return;
      setConnection("CONNECTING");
      socket = new WebSocket(`${base}/ws/dining/ready`);
      socket.onopen = () => setConnection("LIVE");
      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as ReadyMessage;
          if (message.type === "dining.ready.snapshot") {
            setReadyCount(message.orders.length);
            return;
          }
          if (message.type !== "dining.order.ready") return;
          const order = message.order;
          setAlert(order);
          setReadyCount((count) => count + 1);
          if (typeof navigator !== "undefined" && "vibrate" in navigator) navigator.vibrate?.([180, 80, 180]);
          if (typeof Notification !== "undefined" && Notification.permission === "granted") {
            new Notification(`Кухня: ${order.order_number} готов`, {
              body: `${destination(order)} · ${order.guest_count} гост.`,
              icon: "/icon.svg",
              tag: `dining-ready-${order.id}`,
            });
          }
        } catch {
          // Ignore malformed websocket frames; normal polling in WaiterEntry remains fallback.
        }
      };
      socket.onerror = () => setConnection("OFF");
      socket.onclose = () => {
        setConnection("OFF");
        if (!stopped) reconnectTimer.current = window.setTimeout(connect, 2000);
      };
    };

    connect();
    return () => {
      stopped = true;
      if (reconnectTimer.current !== null) window.clearTimeout(reconnectTimer.current);
      socket?.close();
    };
  }, [user?.id]);

  const statusText = useMemo(() => {
    if (connection === "LIVE") return `Realtime активен · READY: ${readyCount}`;
    if (connection === "CONNECTING") return "Подключаю realtime кухни…";
    return "Realtime недоступен · список заказов продолжает обновляться по fallback";
  }, [connection, readyCount]);

  async function enableNotifications() {
    if (typeof Notification === "undefined") return;
    const result = await Notification.requestPermission();
    setNotificationPermission(result);
  }

  if (!user) return null;

  return <>
    <section className={`${styles.bar} ${connection === "LIVE" ? styles.live : ""}`} aria-live="polite">
      <div className={styles.status}><i className={styles.dot} /><div><strong>{statusText}</strong><span>Назначенный официант получает событие сразу после перехода KitchenOrder в READY.</span></div></div>
      <div className={styles.actions}>
        {notificationPermission === "default" && <button onClick={() => void enableNotifications()}>Включить уведомления</button>}
        {notificationPermission === "granted" && <span>Уведомления включены</span>}
      </div>
    </section>
    {alert && <section className={styles.alert} role="status" aria-live="assertive">
      <strong>{alert.order_number} готов к выдаче</strong>
      <span>{destination(alert)} · {alert.guest_count} гост. · {alert.total_kgs.toLocaleString("ru-RU")} KGS</span>
      <button onClick={() => setAlert(null)}>Понятно</button>
    </section>}
  </>;
}
