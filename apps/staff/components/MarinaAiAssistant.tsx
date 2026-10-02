"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import styles from "./MarinaAiAssistant.module.css";

type ChatMessage = { role: "user" | "assistant"; content: string };
type Locale = "ru" | "kg" | "kz" | "en";
type Locale = "ru" | "kg" | "kz" | "en";

type Props = {
  screen: string;
  role?: string;
};

const QUICK = [
  "Объясни этот экран",
  "Что мне делать дальше?",
  "Я новичок. Обучи меня",
  "Не получается — помоги",
];

function currentLocale(): Locale {
  const raw = window.localStorage.getItem("marina-smart-staff-locale");
  return raw === "kg" || raw === "kz" || raw === "en" ? raw : "ru";
}

function currentLocale(): Locale {
  const raw = window.localStorage.getItem("marina-smart-staff-locale");
  return raw === "kg" || raw === "kz" || raw === "en" ? raw : "ru";
}

export default function MarinaAiAssistant({ screen, role }: Props) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: "assistant", content: "Я MARINA AI. Подскажу, куда зайти, что нажать и что проверить в MARINA SMART." },
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (open) endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, open]);

  async function ask(raw: string) {
    const question = raw.trim();
    if (!question || sending) return;

    const userMessage: ChatMessage = { role: "user", content: question };
    const history = [...messages, userMessage].slice(-10);
    setMessages(history);
    setInput("");
    setSending(true);

    try {
      const response = await fetch("/core/api/v1/assistant/chat", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          messages: history.map(({ role: messageRole, content }) => ({ role: messageRole, content })),
          current_screen: screen,
          locale: currentLocale(),
        }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        const message =
          response.status === 503
            ? "MARINA AI временно недоступен. Повторите запрос немного позже."
            : response.status === 401 || response.status === 403
              ? "Сессия завершена или для этой роли нет доступа."
              : "Не удалось получить ответ. Повторите запрос чуть позже.";
        setMessages((current) => [...current, { role: "assistant", content: message }]);
        return;
      }
      setMessages((current) => [
        ...current,
        { role: "assistant", content: String(body.answer || "Нет ответа.") },
      ]);
    } catch {
      setMessages((current) => [
        ...current,
        { role: "assistant", content: "MARINA AI сейчас недоступен. Проверьте соединение и повторите запрос." },
      ]);
    } finally {
      setSending(false);
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    void ask(input);
  }

  return (
    <>
      <button
        type="button"
        className={styles.launcher}
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-label="Открыть MARINA AI"
      >
        <span className={styles.spark}>AI</span>
        <span>Помощник</span>
      </button>

      {open && (
        <section className={styles.panel} aria-label="MARINA AI">
          <header className={styles.header}>
            <div>
              <strong>MARINA AI</strong>
              <small>{role ? `${role} · ` : ""}{screen}</small>
            </div>
            <button type="button" onClick={() => setOpen(false)} aria-label="Закрыть">×</button>
          </header>

          <div className={styles.quick}>
            {QUICK.map((label) => (
              <button key={label} type="button" onClick={() => void ask(label)} disabled={sending}>
                {label}
              </button>
            ))}
          </div>

          <div className={styles.messages}>
            {messages.map((message, index) => (
              <div key={index} className={message.role === "user" ? styles.user : styles.assistant}>
                <span>{message.role === "user" ? "Вы" : "MARINA AI"}</span>
                <p>{message.content}</p>
              </div>
            ))}
            {sending && <div className={styles.thinking}>MARINA AI думает…</div>}
            <div ref={endRef} />
          </div>

          <form className={styles.form} onSubmit={submit}>
            <textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Напишите вопрос по MARINA SMART…"
              maxLength={3000}
              rows={2}
            />
            <button type="submit" disabled={sending || !input.trim()}>Отправить</button>
          </form>

          <footer className={styles.footer}>Read-only · ничего не меняет в системе без вашего действия</footer>
        </section>
      )}
    </>
  );
}
