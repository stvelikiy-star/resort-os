"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import styles from "./MarinaAiAssistant.module.css";

type ChatMessage = { role: "user" | "assistant"; content: string };
type Navigation = { screen: string; label: string };

type Props = {
  screen: string;
  role?: string;
  onNavigate?: (screen: string) => void;
};

const TRANSLATIONS = {
  ru: { greeting: "Я MARINA AI. Помогу разобраться с платформой.", quick: ["Объясни этот экран", "Что мне делать дальше?", "Обучи меня работе", "Помоги решить проблему"], launcher: "Помощник", open: "Открыть MARINA AI", close: "Закрыть", you: "Вы", thinking: "{copy.thinking}", placeholder: "Напишите вопрос по MARINA SMART…", send: "Отправить", readOnly: "Только чтение · помощник не изменяет данные", unavailable: "MARINA AI временно недоступен. Повторите запрос позже.", denied: "Сессия завершена или у вашей роли нет доступа.", failed: "Не удалось получить ответ. Повторите запрос.", network: "Проверьте соединение и повторите запрос.", empty: "Ответ отсутствует.", navigate: "Открыть" },
  kg: { greeting: "Мен MARINA AI жардамчысымын. Платформаны колдонууга жардам берем.", quick: ["Бул экранды түшүндүр", "Эми эмне кылышым керек?", "Мага иштөөнү үйрөт", "Маселени чечүүгө жардам бер"], launcher: "Жардамчы", open: "MARINA AI ачуу", close: "Жабуу", you: "Сиз", thinking: "MARINA AI жооп даярдоодо…", placeholder: "MARINA SMART боюнча суроо жазыңыз…", send: "Жөнөтүү", readOnly: "Окуу режими · маалыматтарды өзгөртпөйт", unavailable: "MARINA AI убактылуу жеткиликсиз. Кийин кайталаңыз.", denied: "Сеанс аяктады же бул ролго уруксат жок.", failed: "Жооп алуу мүмкүн болгон жок. Кайталаңыз.", network: "Байланышты текшерип, кайра аракет кылыңыз.", empty: "Жооп жок.", navigate: "Ачуу" },
  en: { greeting: "I'm MARINA AI. I can help you use the platform.", quick: ["Explain this screen", "What should I do next?", "Teach me how to use this", "Help me solve a problem"], launcher: "Assistant", open: "Open MARINA AI", close: "Close", you: "You", thinking: "MARINA AI is thinking…", placeholder: "Ask about MARINA SMART…", send: "Send", readOnly: "Read-only · the assistant cannot change data", unavailable: "MARINA AI is temporarily unavailable. Try again later.", denied: "Your session has ended or this role has no access.", failed: "Could not get a response. Try again.", network: "Check your connection and try again.", empty: "No response.", navigate: "Open" },
  kz: { greeting: "Мен MARINA AI көмекшісімін. Платформаны пайдалануға көмектесемін.", quick: ["Бұл экранды түсіндір", "Әрі қарай не істеуім керек?", "Жұмыс істеуді үйрет", "Мәселені шешуге көмектес"], launcher: "Көмекші", open: "MARINA AI ашу", close: "Жабу", you: "Сіз", thinking: "MARINA AI жауап дайындауда…", placeholder: "MARINA SMART туралы сұрақ жазыңыз…", send: "Жіберу", readOnly: "Тек оқу · деректерді өзгертпейді", unavailable: "MARINA AI уақытша қолжетімсіз. Кейін қайталаңыз.", denied: "Сеанс аяқталды немесе бұл рөлге рұқсат жоқ.", failed: "Жауап алу мүмкін болмады. Қайталаңыз.", network: "Байланысты тексеріп, қайта көріңіз.", empty: "Жауап жоқ.", navigate: "Ашу" },
} as const;

function currentLocale(): "ru" | "kg" | "en" | "kz" {
  if (typeof document === "undefined") return "ru";
  const raw = (document.documentElement.lang || navigator.language || "ru").toLowerCase();
  if (raw.startsWith("ky") || raw.startsWith("kg")) return "kg";
  if (raw.startsWith("kk") || raw.startsWith("kz")) return "kz";
  if (raw.startsWith("en")) return "en";
  return "ru";
}

export default function MarinaAiAssistant({ screen, role, onNavigate }: Props) {
  const [open, setOpen] = useState(false);
  const [locale, setLocale] = useState<"ru" | "kg" | "en" | "kz">("ru");
  const copy = TRANSLATIONS[locale];
  useEffect(() => {
    const update = () => setLocale(currentLocale());
    update();
    const observer = new MutationObserver(update);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["lang"] });
    return () => observer.disconnect();
  }, []);
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: "assistant", content: "" },
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [navigation, setNavigation] = useState<Navigation | null>(null);
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
    setNavigation(null);

    try {
      const response = await fetch("/core/api/v1/assistant/chat", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          messages: history.map(({ role: messageRole, content }) => ({ role: messageRole, content })),
          current_screen: screen,
          locale,
        }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        const message =
          response.status === 503
            ? copy.unavailable
            : response.status === 401 || response.status === 403
              ? copy.denied
              : copy.failed;
        setMessages((current) => [...current, { role: "assistant", content: message }]);
        return;
      }
      setMessages((current) => [
        ...current,
        { role: "assistant", content: String(body.answer || copy.empty) },
      ]);
      if (body.navigation && typeof body.navigation.screen === "string" && typeof body.navigation.label === "string") {
        setNavigation(body.navigation as Navigation);
      }
    } catch {
      setMessages((current) => [
        ...current,
        { role: "assistant", content: copy.network },
      ]);
    } finally {
      setSending(false);
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    void ask(input);
  }

  if (!role || !["OWNER", "MANAGER", "RECEPTION"].includes(role)) return null;

  return (
    <>
      <button
        type="button"
        className={styles.launcher}
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-label={copy.open}
      >
        <span className={styles.spark}>AI</span>
        <span>{copy.launcher}</span>
      </button>

      {open && (
        <section className={styles.panel} aria-label="MARINA AI">
          <header className={styles.header}>
            <div>
              <strong>MARINA AI</strong>
              <small>{role ? `${role} · ` : ""}{screen}</small>
            </div>
            <button type="button" onClick={() => setOpen(false)} aria-label={copy.close}>×</button>
          </header>

          <div className={styles.quick}>
            {copy.quick.map((label) => (
              <button key={label} type="button" onClick={() => void ask(label)} disabled={sending}>
                {label}
              </button>
            ))}
          </div>

          <div className={styles.messages}>
            <div className={styles.assistant}><p>{copy.greeting}</p></div>
            {messages.map((message, index) => (
              <div key={index} className={message.role === "user" ? styles.user : styles.assistant}>
                <span>{message.role === "user" ? copy.you : "MARINA AI"}</span>
                <p>{message.content}</p>
              </div>
            ))}
            {sending && <div className={styles.thinking}>{copy.thinking}</div>}
            <div ref={endRef} />
          </div>

          {navigation && onNavigate && (
            <div className={styles.quick}>
              <button type="button" onClick={() => { onNavigate(navigation.screen); setOpen(false); }}>
                {copy.navigate}: {navigation.label}
              </button>
            </div>
          )}

          <form className={styles.form} onSubmit={submit}>
            <textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder={copy.placeholder}
              maxLength={3000}
              rows={2}
            />
            <button type="submit" disabled={sending || !input.trim()}>{copy.send}</button>
          </form>

          <footer className={styles.footer}>{copy.readOnly}</footer>
        </section>
      )}
    </>
  );
}
