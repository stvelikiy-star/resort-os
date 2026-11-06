"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import type { MarinaGuestLocale } from "../lib/marinaGuestLocale";
import styles from "./GuestAiAssistant.module.css";

type Message = { role: "user" | "assistant"; content: string };
type HumanHandoff = {
  available: boolean;
  status: "NOT_REQUESTED";
  request_code: "ADMIN";
  requires_explicit_guest_action: true;
  action: "CREATE_GUEST_REQUEST";
  endpoint_suffix: "/requests";
  http_method: "POST";
  task_created: false;
};

function acceptsHandoff(value: unknown): value is HumanHandoff {
  if (!value || typeof value !== "object") return false;
  const item = value as Partial<HumanHandoff>;
  return item.available === true && item.status === "NOT_REQUESTED"
    && item.request_code === "ADMIN" && item.requires_explicit_guest_action === true
    && item.action === "CREATE_GUEST_REQUEST" && item.endpoint_suffix === "/requests"
    && item.http_method === "POST" && item.task_created === false;
}
const HUMAN_HANDOFF_UI_ENABLED = process.env.NEXT_PUBLIC_MARINA_GUEST_HANDOFF_ENABLED === "true";
const COPY = {
  ru: { title: "Помощник MARINA AI", note: "Правила отеля, ваше проживание и заявки. Помощник отвечает на вопросы; действия выполняйте в кабинете.", question: "Ваш вопрос", send: "Спросить", wait: "Отвечаю…", unavailable: "Помощник временно недоступен. Свяжитесь с ресепшеном.", expired: "Доступ к проживанию завершён. Войдите снова или обратитесь на ресепшен.", handoff: "Позвать администратора", handoffNote: "По вашему подтверждению вопрос будет отправлен сотруднику гостиницы отдельной заявкой.", confirm: "Подтвердить заявку", cancel: "Отмена", sending: "Отправка заявки…", sent: "Заявка администратору создана. Статус появится в ваших заявках.", duplicate: "У вас уже есть активная заявка администратору. Проверьте её статус.", handoffError: "Не удалось подтвердить создание заявки. Проверьте список заявок, прежде чем повторять." },
  kg: { title: "MARINA AI жардамчысы", note: "Мейманкананын эрежелери, жашооңуз жана өтүнмөлөрүңүз. Жардамчы суроолорго жооп берет; аракеттерди жеке кабинетте аткарыңыз.", question: "Сурооңуз", send: "Суроо берүү", wait: "Жооп даярдалууда…", unavailable: "Жардамчы убактылуу жеткиликсиз. Кабыл алуу бөлүмүнө кайрылыңыз.", expired: "Жашоого кирүү мүмкүнчүлүгү аяктады. Кайра кириңиз же кабыл алуу бөлүмүнө кайрылыңыз.", handoff: "Администраторду чакыруу", handoffNote: "Ырастагандан кийин сурооңуз мейманкананын кызматкерине өзүнчө өтүнмө катары жөнөтүлөт.", confirm: "Өтүнмөнү ырастоо", cancel: "Жокко чыгаруу", sending: "Өтүнмө жөнөтүлүүдө…", sent: "Администраторго өтүнмө түзүлдү. Анын абалы өтүнмөлөр тизмесинде көрсөтүлөт.", duplicate: "Администраторго активдүү өтүнмөңүз бар. Анын абалын текшериңиз.", handoffError: "Өтүнмө түзүлгөнүн ырастоо мүмкүн болгон жок. Кайра жөнөтүүдөн мурун өтүнмөлөр тизмесин текшериңиз." },
  kz: { title: "MARINA AI көмекшісі", note: "Қонақүй ережелері, тұруыңыз және өтінімдеріңіз. Көмекші сұрақтарға жауап береді; әрекеттерді жеке кабинетте орындаңыз.", question: "Сұрағыңыз", send: "Сұрау", wait: "Жауап дайындалуда…", unavailable: "Көмекші уақытша қолжетімсіз. Қабылдау бөліміне хабарласыңыз.", expired: "Тұруға кіру мүмкіндігі аяқталды. Қайта кіріңіз немесе қабылдау бөліміне хабарласыңыз.", handoff: "Әкімшіні шақыру", handoffNote: "Растағаннан кейін сұрағыңыз қонақүй қызметкеріне жеке өтінім ретінде жіберіледі.", confirm: "Өтінімді растау", cancel: "Бас тарту", sending: "Өтінім жіберілуде…", sent: "Әкімшіге өтінім құрылды. Күйі өтінімдер тізімінде көрсетіледі.", duplicate: "Әкімшіге белсенді өтініміңіз бар. Күйін тексеріңіз.", handoffError: "Өтінімнің құрылғанын растау мүмкін болмады. Қайталаудан бұрын өтінімдер тізімін тексеріңіз." },
  en: { title: "MARINA AI assistant", note: "Hotel rules, your stay and requests. The assistant answers questions; use your guest area to perform actions.", question: "Your question", send: "Ask", wait: "Answering…", unavailable: "The assistant is temporarily unavailable. Please contact reception.", expired: "Your stay access has ended. Sign in again or contact reception.", handoff: "Ask reception for help", handoffNote: "With your confirmation, your question will be sent to hotel staff as a separate service request.", confirm: "Confirm request", cancel: "Cancel", sending: "Sending request…", sent: "A reception request has been created. You can track it in your requests.", duplicate: "You already have an active reception request. Check its status.", handoffError: "The request could not be confirmed. Check your requests before trying again." },
};

export default function GuestAiAssistant({ token, locale, onSessionExpired, onHandoffRequested }: {
  token: string;
  locale: MarinaGuestLocale;
  onSessionExpired: () => void;
  onHandoffRequested?: () => void;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [handoffAvailable, setHandoffAvailable] = useState(false);
  const [handoffQuestion, setHandoffQuestion] = useState("");
  const [handoffConfirm, setHandoffConfirm] = useState(false);
  const [handoffBusy, setHandoffBusy] = useState(false);
  const [handoffStatus, setHandoffStatus] = useState("");
  const handoffPending = useRef(false);
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
    setHandoffAvailable(false); setHandoffConfirm(false); setHandoffStatus("");
    try {
      const response = await fetch(`/core/api/v1/guest-os/rooms/${encodeURIComponent(token)}/assistant/chat`, {
        method: "POST", credentials: "include", signal: controller.signal,
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ messages: history, locale }),
      });
      if (response.status === 401 || response.status === 404) {
        setMessages([]); setError(copy.expired); onSessionExpired(); return;
      }
      // A provider outage happens AFTER the guest's stay session is checked by
      // the guest-assistant endpoint. Keep AI truthfully unavailable, but allow
      // an explicit request to real reception through the existing guest API.
      // No help task is created here; the guest must confirm it separately.
      if (response.status === 503) {
        setError(copy.unavailable);
        setHandoffQuestion(question.trim().slice(0, 1200));
        setHandoffAvailable(HUMAN_HANDOFF_UI_ENABLED);
        return;
      }
      const body = await response.json();
      if (!response.ok || typeof body.answer !== "string") throw new Error();
      setMessages([...history, { role: "assistant", content: body.answer }]);
      const option = acceptsHandoff(body.human_handoff);
      setHandoffAvailable(HUMAN_HANDOFF_UI_ENABLED && option);
      setHandoffQuestion(question.trim().slice(0, 1200));
      setQuestion("");
    } catch {
      if (!controller.signal.aborted) setError(copy.unavailable);
    } finally { if (!controller.signal.aborted) setBusy(false); }
  }

  async function requestHumanHelp() {
    if (!handoffAvailable || !handoffConfirm || handoffBusy || handoffPending.current) return;
    handoffPending.current = true;
    setHandoffBusy(true);
    setHandoffStatus("");
    try {
      // Fixed canonical route, not a server-provided arbitrary URL.
      const response = await fetch(`/core/api/v1/guest-os/rooms/${encodeURIComponent(token)}/requests`, {
        method: "POST",
        credentials: "include",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ request_code: "ADMIN", description: handoffQuestion || null }),
      });
      const body = await response.json().catch(() => ({}));
      if (response.status === 401 || response.status === 404) {
        setHandoffAvailable(false);
        setMessages([]);
        setHandoffStatus(copy.expired);
        onSessionExpired();
        return;
      }
      if (response.status === 409 && body?.detail?.code === "GUEST_REQUEST_DUPLICATE_ACTIVE") {
        setHandoffStatus(copy.duplicate);
        setHandoffAvailable(false);
        onHandoffRequested?.();
        return;
      }
      if (response.status !== 201 || typeof body?.id !== "string") {
        setHandoffStatus(copy.handoffError);
        setHandoffAvailable(false);
        onHandoffRequested?.();
        return;
      }
      setHandoffAvailable(false);
      setHandoffConfirm(false);
      setHandoffStatus(copy.sent);
      onHandoffRequested?.();
    } catch {
      // Network timeout may happen AFTER successful creation: no auto retry.
      setHandoffStatus(copy.handoffError);
      setHandoffAvailable(false);
      onHandoffRequested?.();
    } finally {
      handoffPending.current = false;
      setHandoffBusy(false);
    }
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
      {handoffAvailable && (
        <div className={styles.handoff}>
          <p>{copy.handoffNote}</p>
          {!handoffConfirm ? (
            <button type="button" disabled={busy} onClick={() => setHandoffConfirm(true)}>{copy.handoff}</button>
          ) : (
            <div className={styles.handoffConfirm}>
              <p className={styles.questionPreview}>{handoffQuestion}</p>
              <button type="button" disabled={handoffBusy} onClick={() => void requestHumanHelp()}>
                {handoffBusy ? copy.sending : copy.confirm}
              </button>
              <button type="button" disabled={handoffBusy} className={styles.secondary} onClick={() => setHandoffConfirm(false)}>{copy.cancel}</button>
            </div>
          )}
        </div>
      )}
      {handoffStatus && <p role="status">{handoffStatus}</p>}
    </details>
  </section>;
}
