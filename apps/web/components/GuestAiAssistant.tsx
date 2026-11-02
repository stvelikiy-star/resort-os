"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import type { MarinaGuestLocale } from "../lib/marinaGuestLocale";
import styles from "./GuestAiAssistant.module.css";

type Message = { role: "user" | "assistant"; content: string };
const COPY = {
  ru: { title: "Помощник MARINA AI", note: "Правила отеля, ваше проживание и заявки. Помощник отвечает на вопросы; действия выполняйте в кабинете.", question: "Ваш вопрос", send: "Спросить", wait: "Отвечаю…", unavailable: "Помощник временно недоступен. Свяжитесь с ресепшеном.", expired: "Доступ к проживанию завершён. Войдите снова или обратитесь на ресепшен." },
  kg: { title: "MARINA AI жардамчысы", note: "Мейманкананын эрежелери, жашооңуз жана өтүнмөлөрүңүз. Жардамчы суроолорго жооп берет; аракеттерди жеке кабинетте аткарыңыз.", question: "Сурооңуз", send: "Суроо берүү", wait: "Жооп даярдалууда…", unavailable: "Жардамчы убактылуу жеткиликсиз. Кабыл алуу бөлүмүнө кайрылыңыз.", expired: "Жашоого кирүү мүмкүнчүлүгү аяктады. Кайра кириңиз же кабыл алуу бөлүмүнө кайрылыңыз." },
  kz: { title: "MARINA AI көмекшісі", note: "Қонақүй ережелері, тұруыңыз және өтінімдеріңіз. Көмекші сұрақтарға жауап береді; әрекеттерді жеке кабинетте орындаңыз.", question: "Сұрағыңыз", send: "Сұрау", wait: "Жауап дайындалуда…", unavailable: "Көмекші уақытша қолжетімсіз. Қабылдау бөліміне хабарласыңыз.", expired: "Тұруға кіру мүмкіндігі аяқталды. Қайта кіріңіз немесе қабылдау бөліміне хабарласыңыз." },
  en: { title: "MARINA AI assistant", note: "Hotel rules, your stay and requests. The assistant answers questions; use your guest area to perform actions.", question: "Your question", send: "Ask", wait: "Answering…", unavailable: "The assistant is temporarily unavailable. Please contact reception.", expired: "Your stay access has ended. Sign in again or contact reception." },
};

export default function GuestAiAssistant({ token, locale, onSessionExpired }: {
  token: string; locale: MarinaGuestLocale; onSessionExpired: () => void;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const pending = useRef<AbortController | null>(null);
  const copy = COPY[locale];

  useEffect(() => () => pending.current?.abort(), [token]);

  async function ask(event: FormEvent) {
    event.preventDefault();
    if (!question.trim() || busy) return;
    const history = [...messages, { role: "user" as const, content: question.trim() }].slice(-10);
    const controller = new AbortController();
    pending.current = controller;
    setBusy(true); setError("");
    try {
      const response = await fetch(`/core/api/v1/guest-os/rooms/${encodeURIComponent(token)}/assistant/chat`, {
        method: "POST", credentials: "include", signal: controller.signal,
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ messages: history, locale }),
      });
      if (response.status === 401 || response.status === 404) {
        setMessages([]); setError(copy.expired); onSessionExpired(); return;
      }
      const body = await response.json();
      if (!response.ok || typeof body.answer !== "string") throw new Error();
      setMessages([...history, { role: "assistant", content: body.answer }]);
      setQuestion("");
    } catch {
      if (!controller.signal.aborted) setError(copy.unavailable);
    } finally { if (!controller.signal.aborted) setBusy(false); }
  }

  return <section className={`concierge-section ${styles.card}`} aria-label={copy.title}>
    <details>
      <summary><strong>{copy.title}</strong></summary>
      <p>{copy.note}</p>
      <div role="log" aria-live="polite" className={styles.log}>
        {messages.map((message, i) => <p key={i}><strong>{message.role === "assistant" ? "MARINA AI: " : ""}</strong>{message.content}</p>)}
      </div>
      <form onSubmit={ask}>
        <label>{copy.question}<textarea value={question} onChange={e => setQuestion(e.target.value)} maxLength={1600} required disabled={busy} /></label>
        {error && <p role="alert">{error}</p>}
        <button disabled={busy || !question.trim()}>{busy ? copy.wait : copy.send}</button>
      </form>
    </details>
  </section>;
}
