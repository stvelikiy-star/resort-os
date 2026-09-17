"use client";

import { FormEvent, useMemo, useState } from "react";

type Role = "user" | "assistant";
type Message = { role: Role; content: string };
type AvailabilityOption = {
  room_type_code: string | null;
  room_type_name: string | null;
  area: string | null;
  available_count: number | null;
  total_kgs: number;
  nights: number;
};
type AssistantResponse = {
  answer: string;
  availability?: {
    check_in: string;
    check_out: string;
    nights: number;
    adults: number;
    children: number;
    options: AvailabilityOption[];
  } | null;
};

function todayIso(offset = 0) {
  const now = new Date();
  const value = new Date(now.getFullYear(), now.getMonth(), now.getDate() + offset);
  const y = value.getFullYear();
  const m = String(value.getMonth() + 1).padStart(2, "0");
  const d = String(value.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export default function AiAdministratorWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", content: "Здравствуйте! Я AI-администратор «Три Короны». Помогу с номерами, датами и вопросами об отдыхе. Для точной проверки свободных номеров укажите даты и количество гостей." },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [checkIn, setCheckIn] = useState(todayIso(1));
  const [checkOut, setCheckOut] = useState(todayIso(2));
  const [adults, setAdults] = useState(2);
  const [children, setChildren] = useState(0);
  const [availability, setAvailability] = useState<AssistantResponse["availability"]>(null);

  const canSearch = useMemo(() => checkIn && checkOut && checkOut > checkIn && adults > 0, [checkIn, checkOut, adults]);

  async function callAssistant(nextMessages: Message[], search?: { check_in: string; check_out: string; adults: number; children: number }) {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/core/api/v1/public/ai-admin/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: nextMessages.slice(-12), locale: "ru", search }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail || `HTTP ${response.status}`);
      }
      const data = (await response.json()) as AssistantResponse;
      setMessages((current) => [...current, { role: "assistant", content: data.answer }]);
      if (data.availability) setAvailability(data.availability);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось получить ответ");
    } finally {
      setLoading(false);
    }
  }

  async function sendMessage(event: FormEvent) {
    event.preventDefault();
    const text = input.trim();
    if (!text || loading) return;
    const next = [...messages, { role: "user" as const, content: text }];
    setMessages(next);
    setInput("");
    await callAssistant(next);
  }

  async function checkDates() {
    if (!canSearch || loading) return;
    const question = `Проверьте свободные номера на ${checkIn} — ${checkOut}, взрослых: ${adults}, детей: ${children}.`;
    const next = [...messages, { role: "user" as const, content: question }];
    setMessages(next);
    await callAssistant(next, { check_in: checkIn, check_out: checkOut, adults, children });
  }

  return (
    <div className="ai-admin-root">
      {open && (
        <section className="ai-admin-panel" aria-label="AI-администратор Три Короны">
          <header className="ai-admin-header">
            <div><strong>AI-администратор</strong><span>Три Короны · 24/7</span></div>
            <button type="button" className="ai-admin-close" onClick={() => setOpen(false)} aria-label="Закрыть чат">×</button>
          </header>

          <div className="ai-admin-search-card">
            <div className="ai-admin-search-grid">
              <label>Заезд<input type="date" min={todayIso()} value={checkIn} onChange={(e) => setCheckIn(e.target.value)} /></label>
              <label>Выезд<input type="date" min={checkIn || todayIso()} value={checkOut} onChange={(e) => setCheckOut(e.target.value)} /></label>
              <label>Взрослые<input type="number" min={1} max={20} value={adults} onChange={(e) => setAdults(Math.max(1, Number(e.target.value) || 1))} /></label>
              <label>Дети<input type="number" min={0} max={20} value={children} onChange={(e) => setChildren(Math.max(0, Number(e.target.value) || 0))} /></label>
            </div>
            <button type="button" className="ai-admin-check" onClick={checkDates} disabled={!canSearch || loading}>Проверить даты</button>
          </div>

          <div className="ai-admin-messages" aria-live="polite">
            {messages.map((message, index) => <div key={`${message.role}-${index}`} className={`ai-admin-message ${message.role}`}>{message.content}</div>)}
            {loading && <div className="ai-admin-message assistant ai-admin-typing">Проверяю…</div>}
            {error && <div className="ai-admin-error">{error}</div>}
          </div>

          {availability && availability.options.length > 0 && (
            <>
              <div className="ai-admin-options">
                {availability.options.slice(0, 4).map((option) => (
                  <article key={option.room_type_code || option.room_type_name || String(option.total_kgs)}>
                    <strong>{option.room_type_name}</strong>
                    <span>{option.nights} ноч. · доступно {option.available_count ?? "—"}</span>
                    <b>{option.total_kgs.toLocaleString("ru-RU")} KGS</b>
                  </article>
                ))}
              </div>
              <a className="ai-admin-booking-handoff" href="/#booking" onClick={() => setOpen(false)}>Выбрать номер и оставить заявку</a>
            </>
          )}

          <form className="ai-admin-form" onSubmit={sendMessage}>
            <input value={input} maxLength={1600} onChange={(e) => setInput(e.target.value)} placeholder="Спросите о номерах, SPA, пляже…" aria-label="Сообщение AI-администратору" />
            <button type="submit" disabled={!input.trim() || loading}>Отправить</button>
          </form>
          <p className="ai-admin-note">AI проверяет цены и наличие через Resort Core. Заявка не является подтверждённой бронью; подтверждение и условия предоплаты — у менеджера.</p>
        </section>
      )}

      <button type="button" className="ai-admin-launcher" onClick={() => setOpen((value) => !value)} aria-expanded={open}>
        <span className="ai-admin-orb">AI</span><span><strong>Онлайн-администратор</strong><small>Проверить даты</small></span>
      </button>
    </div>
  );
}
