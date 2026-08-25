"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type Conversation = {
  id: string;
  channel_code: string;
  channel_kind: string;
  channel_name: string;
  status: string;
  contact_name?: string | null;
  contact_phone?: string | null;
  contact_username?: string | null;
  assigned_to_id?: string | null;
  assigned_to_name?: string | null;
  reservation_request_id?: string | null;
  reservation_request_status?: string | null;
  last_inbound_at?: string | null;
  last_outbound_at?: string | null;
  first_response_at?: string | null;
  needs_reply: boolean;
  waiting_seconds?: number | null;
  last_message_text?: string | null;
  last_message_direction?: string | null;
  last_message_at?: string | null;
};

type Message = {
  id: string;
  direction: "INBOUND" | "OUTBOUND" | "INTERNAL";
  sender_type: string;
  text?: string | null;
  content_type: string;
  delivery_status: string;
  sent_at?: string | null;
  created_at: string;
};

type Detail = { conversation: Conversation; messages: Message[] };

type RequestItem = {
  id: string;
  status: string;
  guest_name: string;
  phone: string;
  check_in: string;
  check_out: string;
  reservation?: { booking_number: string; status: string } | null;
};

type OutboundCapabilities = {
  telegram: {
    channel_code: string;
    inbound_configured: boolean;
    outbound_configured: boolean;
    max_text_length: number;
  };
  whatsapp: { configured: boolean };
  instagram: { configured: boolean };
  truth: string;
};

type AiCapabilities = {
  draft_configured: boolean;
  auto_send_enabled: boolean;
  model_configured: boolean;
  truth: string;
};

const statusLabels: Record<string, string> = {
  OPEN: "Открыт",
  WAITING_GUEST: "Ждём гостя",
  WAITING_STAFF: "Ждёт сотрудника",
  RESOLVED: "Решён",
  ARCHIVED: "Архив",
};

const channelLabels: Record<string, string> = {
  WEBSITE: "Сайт",
  TELEGRAM: "Telegram",
  WHATSAPP: "WhatsApp",
  INSTAGRAM: "Instagram",
  OTHER: "Другой",
};

function waitingLabel(seconds?: number | null) {
  if (seconds == null || seconds < 0) return "—";
  if (seconds < 60) return `${Math.floor(seconds)} сек`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)} мин`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} ч ${Math.floor((seconds % 3600) / 60)} мин`;
  return `${Math.floor(seconds / 86400)} д ${Math.floor((seconds % 86400) / 3600)} ч`;
}

function dateTime(value?: string | null) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }).format(date);
}

function messageAuthor(message: Message) {
  if (message.direction === "INBOUND") return "Гость";
  if (message.direction === "OUTBOUND") return "Исходящее";
  if (message.sender_type === "AI_DRAFT") return "AI-черновик · не отправлен";
  return "Внутренняя заметка";
}

export default function InboxBoard() {
  const [items, setItems] = useState<Conversation[]>([]);
  const [filter, setFilter] = useState("NEEDS_REPLY");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [detailBusy, setDetailBusy] = useState(false);
  const [note, setNote] = useState("");
  const [noteBusy, setNoteBusy] = useState(false);
  const [requests, setRequests] = useState<RequestItem[]>([]);
  const [linkRequestId, setLinkRequestId] = useState("");
  const [capabilities, setCapabilities] = useState<OutboundCapabilities | null>(null);
  const [aiCapabilities, setAiCapabilities] = useState<AiCapabilities | null>(null);
  const [reply, setReply] = useState("");
  const [sendBusy, setSendBusy] = useState(false);
  const [aiBusy, setAiBusy] = useState(false);
  const [sendInfo, setSendInfo] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ limit: "250" });
      if (filter === "NEEDS_REPLY") params.set("needs_reply", "true");
      else if (filter !== "ALL") params.set("status", filter);
      const response = await fetch(`/core/api/v1/admin/inbox/conversations?${params.toString()}`, { cache: "no-store" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Не удалось загрузить сообщения");
      setItems(body.items || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка загрузки Inbox");
    } finally {
      setLoading(false);
    }
  }, [filter]);

  const loadCapabilities = useCallback(async () => {
    try {
      const [outboundResponse, aiResponse] = await Promise.all([
        fetch("/core/api/v1/admin/inbox/outbound-capabilities", { cache: "no-store" }),
        fetch("/core/api/v1/admin/inbox/ai-capabilities", { cache: "no-store" }),
      ]);
      if (outboundResponse.ok) setCapabilities(await outboundResponse.json());
      if (aiResponse.ok) setAiCapabilities(await aiResponse.json());
    } catch {
      // Missing capabilities keep optional actions safely disabled.
    }
  }, []);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { loadCapabilities(); }, [loadCapabilities]);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter((item) => [
      item.contact_name,
      item.contact_phone,
      item.contact_username,
      item.channel_name,
      item.last_message_text,
      item.reservation_request_id,
    ].some((value) => value?.toLowerCase().includes(q)));
  }, [items, query]);

  const telegramReplyEnabled = Boolean(
    detail
    && detail.conversation.channel_kind === "TELEGRAM"
    && capabilities?.telegram.outbound_configured
    && detail.conversation.channel_code === capabilities.telegram.channel_code
  );
  const aiDraftEnabled = Boolean(detail && aiCapabilities?.draft_configured);

  async function openConversation(id: string) {
    setDetailBusy(true);
    setError(null);
    setSendInfo(null);
    try {
      const [detailResponse, requestResponse] = await Promise.all([
        fetch(`/core/api/v1/admin/inbox/conversations/${id}`, { cache: "no-store" }),
        fetch("/core/api/v1/admin/booking/requests?limit=200", { cache: "no-store" }),
      ]);
      const body = await detailResponse.json().catch(() => ({}));
      if (!detailResponse.ok) throw new Error(body.detail || "Не удалось открыть диалог");
      setDetail(body as Detail);
      setLinkRequestId(body.conversation.reservation_request_id || "");
      if (requestResponse.ok) {
        const requestBody = await requestResponse.json();
        setRequests(requestBody.items || []);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка диалога");
    } finally {
      setDetailBusy(false);
    }
  }

  async function claim() {
    if (!detail) return;
    setDetailBusy(true);
    try {
      const response = await fetch(`/core/api/v1/admin/inbox/conversations/${detail.conversation.id}/claim`, { method: "POST" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Не удалось взять диалог");
      await openConversation(detail.conversation.id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка назначения");
    } finally {
      setDetailBusy(false);
    }
  }

  async function changeStatus(status: string) {
    if (!detail) return;
    setDetailBusy(true);
    try {
      const response = await fetch(`/core/api/v1/admin/inbox/conversations/${detail.conversation.id}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Не удалось изменить статус");
      await openConversation(detail.conversation.id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка статуса");
    } finally {
      setDetailBusy(false);
    }
  }

  async function linkRequest() {
    if (!detail) return;
    setDetailBusy(true);
    try {
      const response = await fetch(`/core/api/v1/admin/inbox/conversations/${detail.conversation.id}/reservation-request`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reservation_request_id: linkRequestId || null }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Не удалось связать заявку");
      await openConversation(detail.conversation.id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка связи с заявкой");
    } finally {
      setDetailBusy(false);
    }
  }

  async function addNote(event: FormEvent) {
    event.preventDefault();
    if (!detail || !note.trim()) return;
    setNoteBusy(true);
    try {
      const response = await fetch(`/core/api/v1/admin/inbox/conversations/${detail.conversation.id}/notes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: note.trim() }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Не удалось добавить заметку");
      setNote("");
      await openConversation(detail.conversation.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка заметки");
    } finally {
      setNoteBusy(false);
    }
  }

  async function generateAiDraft() {
    if (!detail || !aiDraftEnabled) return;
    setAiBusy(true);
    setError(null);
    setSendInfo(null);
    try {
      const response = await fetch(`/core/api/v1/admin/inbox/conversations/${detail.conversation.id}/ai-draft`, { method: "POST" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Не удалось создать AI-черновик");
      const maxLength = capabilities?.telegram.max_text_length || 4096;
      setReply(String(body.text || "").slice(0, maxLength));
      setSendInfo("AI создал черновик. Проверьте и отредактируйте его перед отправкой.");
      await openConversation(detail.conversation.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка AI-черновика");
    } finally {
      setAiBusy(false);
    }
  }

  async function sendReply(event: FormEvent) {
    event.preventDefault();
    if (!detail || !telegramReplyEnabled || !reply.trim()) return;
    setSendBusy(true);
    setError(null);
    setSendInfo(null);
    const key = `pms-${crypto.randomUUID()}`;
    try {
      const response = await fetch(`/core/api/v1/admin/inbox/conversations/${detail.conversation.id}/send-text`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Idempotency-Key": key },
        body: JSON.stringify({ text: reply.trim() }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        const statusText = body.delivery_status ? `Статус доставки: ${body.delivery_status}. ` : "";
        throw new Error(`${statusText}${body.provider_description || body.detail || "Telegram не подтвердил отправку"}`);
      }
      setReply("");
      setSendInfo(body.delivery_status === "SENT" ? "Telegram подтвердил отправку." : `Статус: ${body.delivery_status}`);
      await openConversation(detail.conversation.id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка отправки");
      await openConversation(detail.conversation.id);
      await load();
    } finally {
      setSendBusy(false);
    }
  }

  return <main className="work-shell inbox-shell">
    <div className="work-head">
      <div><p className="eyebrow">Коммуникации</p><h1>Единый Inbox</h1><p className="subtitle">Входящие, фактическое время ожидания, AI-черновики и реальные статусы доставки. AI сам сообщения не отправляет.</p></div>
      <button className="btn" onClick={() => { load(); loadCapabilities(); }}>Обновить</button>
    </div>

    <div className="inbox-controls">
      <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Имя, телефон, канал, текст…" />
      <select value={filter} onChange={(e) => setFilter(e.target.value)}>
        <option value="NEEDS_REPLY">Нужен ответ</option><option value="OPEN">Открытые</option><option value="WAITING_STAFF">Ждут сотрудника</option><option value="WAITING_GUEST">Ждём гостя</option><option value="RESOLVED">Решённые</option><option value="ALL">Все</option>
      </select>
    </div>

    {error && <div className="error-box">{error}</div>}
    {loading ? <div className="loading">Загрузка диалогов…</div> : <section className="inbox-list">
      {visible.length === 0 && <div className="empty">Диалогов по этому фильтру пока нет.</div>}
      {visible.map((item) => <button className={`inbox-row ${item.needs_reply ? "needs-reply" : ""}`} key={item.id} onClick={() => openConversation(item.id)} disabled={detailBusy}>
        <div className="inbox-contact"><strong>{item.contact_name || item.contact_phone || item.contact_username || "Без имени"}</strong><span>{channelLabels[item.channel_kind] || item.channel_name}</span></div>
        <div className="inbox-preview"><strong>{item.last_message_direction === "INBOUND" ? "Гость" : item.last_message_direction === "INTERNAL" ? "Внутреннее" : "Ответ"}</strong><span>{item.last_message_text || "Сообщение без текста"}</span></div>
        <div><span className={`inbox-reply-pill ${item.needs_reply ? "waiting" : ""}`}>{item.needs_reply ? "Нужен ответ" : statusLabels[item.status] || item.status}</span><small>{item.needs_reply ? `ожидает ${waitingLabel(item.waiting_seconds)}` : dateTime(item.last_message_at)}</small></div>
        <div><span className="field-label">Ответственный</span><b>{item.assigned_to_name || "Не назначен"}</b>{item.reservation_request_id && <small>Есть заявка · {item.reservation_request_status || ""}</small>}</div>
      </button>)}
    </section>}

    {detail && <div className="detail-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setDetail(null); }}>
      <section className="inbox-detail" role="dialog" aria-modal="true">
        <header>
          <div><p className="eyebrow">{channelLabels[detail.conversation.channel_kind] || detail.conversation.channel_name}</p><h2>{detail.conversation.contact_name || detail.conversation.contact_phone || detail.conversation.contact_username || "Диалог"}</h2><div className="inbox-header-meta"><span>{statusLabels[detail.conversation.status] || detail.conversation.status}</span>{detail.conversation.needs_reply && <b>Нужен ответ · {waitingLabel(detail.conversation.waiting_seconds)}</b>}</div></div>
          <button className="btn" onClick={() => setDetail(null)}>Закрыть</button>
        </header>

        <div className="inbox-management">
          <div><span className="field-label">Ответственный</span><strong>{detail.conversation.assigned_to_name || "Не назначен"}</strong>{!detail.conversation.assigned_to_id && <button className="btn" onClick={claim} disabled={detailBusy}>Взять диалог</button>}</div>
          <div><span className="field-label">Статус</span><select value={detail.conversation.status} onChange={(e) => changeStatus(e.target.value)} disabled={detailBusy}><option value="OPEN">Открыт</option><option value="WAITING_STAFF">Ждёт сотрудника</option><option value="WAITING_GUEST">Ждём гостя</option><option value="RESOLVED">Решён</option><option value="ARCHIVED">Архив</option></select></div>
          <div className="inbox-link-request"><span className="field-label">Заявка на бронь</span><div><select value={linkRequestId} onChange={(e) => setLinkRequestId(e.target.value)} disabled={detailBusy}><option value="">Не связана</option>{requests.map((request) => <option key={request.id} value={request.id}>{request.guest_name} · {request.phone} · {request.check_in} → {request.check_out} · {request.status}</option>)}</select><button className="btn" onClick={linkRequest} disabled={detailBusy}>Сохранить</button></div></div>
        </div>

        <div className="message-stream">
          {detail.messages.length === 0 && <div className="empty small">Сообщений нет.</div>}
          {detail.messages.map((message) => <article className={`message-bubble ${message.direction.toLowerCase()} ${message.sender_type === "AI_DRAFT" ? "ai-draft" : ""}`} key={message.id}>
            <div><strong>{messageAuthor(message)}</strong><time>{dateTime(message.sent_at || message.created_at)}</time></div>
            <p>{message.text || `[${message.content_type}]`}</p>
            {message.direction === "OUTBOUND" && <small>Доставка: {message.delivery_status}</small>}
          </article>)}
        </div>

        {(aiDraftEnabled || telegramReplyEnabled) ? <form className="outbound-reply-form" onSubmit={sendReply}>
          <label><span>Черновик ответа менеджера</span><textarea value={reply} onChange={(e) => setReply(e.target.value)} rows={4} maxLength={capabilities?.telegram.max_text_length || 4096} placeholder="Напишите ответ или создайте AI-черновик…" /></label>
          <div className="reply-actions">
            {aiDraftEnabled && <button type="button" className="btn" onClick={generateAiDraft} disabled={aiBusy || sendBusy}>{aiBusy ? "Готовлю…" : "AI-черновик"}</button>}
            {telegramReplyEnabled ? <button className="btn primary" disabled={sendBusy || aiBusy || !reply.trim()}>{sendBusy ? "Отправляю…" : "Отправить в Telegram"}</button> : <small>Отправка наружу выключена, пока реальный адаптер канала не настроен.</small>}
          </div>
          {sendInfo && <p className="send-info">{sendInfo}</p>}
          <p className="reply-truth">AI только предлагает текст. Наличие, цена, оплата и статус брони берутся только из Core и требуют фактических данных.</p>
        </form> : <div className="inbox-send-disabled"><strong>AI и исходящая отправка не активированы</strong><span>Они включаются только после задания реальных ключей/модели и provider-адаптера. Система не имитирует отправку.</span></div>}

        <form className="internal-note-form" onSubmit={addNote}>
          <label><span>Внутренняя заметка — клиент её не получает</span><textarea value={note} onChange={(e) => setNote(e.target.value)} rows={3} maxLength={12000} placeholder="Например: уточнить даты у гостя после звонка" /></label>
          <button className="btn" disabled={noteBusy || !note.trim()}>{noteBusy ? "Сохраняю…" : "Добавить заметку"}</button>
        </form>
      </section>
    </div>}
  </main>;
}