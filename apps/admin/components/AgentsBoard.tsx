"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type Agent = {
  id: string;
  name: string;
  contact_name?: string | null;
  phone?: string | null;
  whatsapp?: string | null;
  email?: string | null;
  notes?: string | null;
  status: "ACTIVE" | "INACTIVE";
  reservations: number;
  booked_kgs: number;
  received_kgs: number;
  room_nights: number;
  last_check_in?: string | null;
};

type AgentReport = {
  agent: Agent;
  summary: {
    reservations: number;
    effective_reservations: number;
    booked_kgs: number;
    received_kgs: number;
    room_nights: number;
    average_booking_kgs: number;
    cancelled_or_no_show: number;
  };
  reservations: Array<{
    id: string;
    booking_number: string;
    status: string;
    check_in: string;
    check_out: string;
    total_kgs: number;
    received_kgs: number;
    guest_name?: string | null;
    guest_phone?: string | null;
    rooms?: string | null;
    discount_percent: number;
    extra_bed_count: number;
  }>;
  interactions: Array<{ id: string; kind: string; note: string; next_contact_at?: string | null; created_at: string }>;
};

const money = (value: number) => `${new Intl.NumberFormat("ru-RU").format(value)} сом`;
const todayIso = () => new Date().toISOString().slice(0, 10);
const monthStartIso = () => `${todayIso().slice(0, 8)}01`;

export default function AgentsBoard() {
  const [items, setItems] = useState<Agent[]>([]);
  const [search, setSearch] = useState("");
  const [fromDate, setFromDate] = useState(monthStartIso());
  const [toDate, setToDate] = useState(todayIso());
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [report, setReport] = useState<AgentReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [contact, setContact] = useState("");
  const [phone, setPhone] = useState("");
  const [whatsapp, setWhatsapp] = useState("");
  const [email, setEmail] = useState("");
  const [notes, setNotes] = useState("");
  const [interactionKind, setInteractionKind] = useState("NOTE");
  const [interactionNote, setInteractionNote] = useState("");
  const [nextContactAt, setNextContactAt] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ search, include_inactive: "true", from_date: fromDate, to_date: toDate });
      const response = await fetch(`/core/api/v1/admin/owner-corrections/agents?${params}`, { cache: "no-store" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Не удалось загрузить агентов");
      setItems(body.items || []);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось загрузить агентов");
    } finally {
      setLoading(false);
    }
  }, [search, fromDate, toDate]);

  const loadReport = useCallback(async (agentId: string) => {
    setError(null);
    try {
      const params = new URLSearchParams({ from_date: fromDate, to_date: toDate });
      const response = await fetch(`/core/api/v1/admin/owner-corrections/agents/${agentId}/report?${params}`, { cache: "no-store" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Не удалось загрузить отчёт агента");
      setReport(body as AgentReport);
      setSelectedId(agentId);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось загрузить отчёт агента");
    }
  }, [fromDate, toDate]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 250);
    return () => window.clearTimeout(timer);
  }, [load]);
  useEffect(() => {
    if (selectedId) void loadReport(selectedId);
  }, [fromDate, toDate]); // eslint-disable-line react-hooks/exhaustive-deps

  const totals = useMemo(
    () => items.reduce(
      (acc, item) => ({
        reservations: acc.reservations + item.reservations,
        booked: acc.booked + item.booked_kgs,
        received: acc.received + item.received_kgs,
        nights: acc.nights + item.room_nights,
      }),
      { reservations: 0, booked: 0, received: 0, nights: 0 },
    ),
    [items],
  );

  async function createAgent(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const response = await fetch("/core/api/v1/admin/owner-corrections/agents", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          contact_name: contact.trim() || null,
          phone: phone.trim() || null,
          whatsapp: whatsapp.trim() || null,
          email: email.trim() || null,
          notes: notes.trim() || null,
        }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Не удалось создать агента");
      setName("");
      setContact("");
      setPhone("");
      setWhatsapp("");
      setEmail("");
      setNotes("");
      setShowCreate(false);
      await load();
      await loadReport(body.id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось создать агента");
    } finally {
      setBusy(false);
    }
  }

  async function addInteraction(event: FormEvent) {
    event.preventDefault();
    if (!selectedId || !interactionNote.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(`/core/api/v1/admin/owner-corrections/agents/${selectedId}/interactions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kind: interactionKind, note: interactionNote.trim(), next_contact_at: nextContactAt || null }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Не удалось сохранить взаимодействие");
      setInteractionNote("");
      setNextContactAt("");
      await loadReport(selectedId);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось сохранить взаимодействие");
    } finally {
      setBusy(false);
    }
  }

  return <main className="shell">
    <div className="topbar">
      <div>
        <p className="eyebrow">CRM · B2B продажи</p>
        <h1>Агенты</h1>
        <p className="subtitle">Карточки партнёров, брони, полученные оплаты, ночи и история контактов. Забронированная сумма и реально полученные деньги показываются отдельно.</p>
      </div>
      <button className="btn primary" onClick={() => setShowCreate((value) => !value)}>{showCreate ? "Закрыть" : "Новый агент"}</button>
    </div>

    <section className="controls">
      <div className="control"><label>Поиск агента</label><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Название, контакт, телефон" /></div>
      <div className="control"><label>С</label><input type="date" value={fromDate} onChange={(event) => setFromDate(event.target.value)} /></div>
      <div className="control"><label>По</label><input type="date" value={toDate} onChange={(event) => setToDate(event.target.value)} /></div>
      <div className="date-actions"><button className="btn" onClick={() => void load()}>Обновить</button></div>
    </section>

    <section className="summary">
      <div className="summary-card"><strong>{items.length}</strong><span>Агентов</span></div>
      <div className="summary-card"><strong>{totals.reservations}</strong><span>Броней за период</span></div>
      <div className="summary-card"><strong>{totals.nights}</strong><span>Ночей</span></div>
      <div className="summary-card"><strong>{money(totals.booked)}</strong><span>Забронировано</span></div>
      <div className="summary-card"><strong>{money(totals.received)}</strong><span>Получено оплат</span></div>
    </section>

    {showCreate && <form className="controls" onSubmit={createAgent}>
      <div className="control"><label>Название *</label><input required minLength={2} value={name} onChange={(e) => setName(e.target.value)} /></div>
      <div className="control"><label>Контакт</label><input value={contact} onChange={(e) => setContact(e.target.value)} /></div>
      <div className="control"><label>Телефон</label><input value={phone} onChange={(e) => setPhone(e.target.value)} /></div>
      <div className="control"><label>WhatsApp</label><input value={whatsapp} onChange={(e) => setWhatsapp(e.target.value)} /></div>
      <div className="control"><label>Email</label><input type="email" value={email} onChange={(e) => setEmail(e.target.value)} /></div>
      <div className="control"><label>Комментарий</label><input value={notes} onChange={(e) => setNotes(e.target.value)} /></div>
      <div className="date-actions"><button className="btn primary" disabled={busy}>{busy ? "Сохраняю…" : "Создать карточку"}</button></div>
    </form>}

    {error && <div className="error-box">{error}</div>}
    {loading ? <div className="loading">Загрузка агентов…</div> : <section className="pms-v2-card">
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead><tr><th>Агент</th><th>Контакт</th><th>Брони</th><th>Ночи</th><th>Забронировано</th><th>Получено</th><th>Последний заезд</th><th /></tr></thead>
          <tbody>{items.map((agent) => <tr key={agent.id} style={{ opacity: agent.status === "INACTIVE" ? .55 : 1 }}>
            <td><strong>{agent.name}</strong><br/><small>{agent.status === "ACTIVE" ? "Активен" : "Неактивен"}</small></td>
            <td>{agent.contact_name || "—"}<br/><small>{agent.phone || agent.whatsapp || ""}</small></td>
            <td>{agent.reservations}</td><td>{agent.room_nights}</td><td>{money(agent.booked_kgs)}</td><td>{money(agent.received_kgs)}</td><td>{agent.last_check_in || "—"}</td>
            <td><button className="btn" onClick={() => void loadReport(agent.id)}>Карточка / отчёт</button></td>
          </tr>)}</tbody>
        </table>
      </div>
    </section>}

    {report && <section className="pms-v2-card" style={{ marginTop: 20 }}>
      <div className="topbar">
        <div><p className="eyebrow">Карточка агента</p><h2>{report.agent.name}</h2><p>{[report.agent.contact_name, report.agent.phone, report.agent.whatsapp, report.agent.email].filter(Boolean).join(" · ")}</p></div>
        <button className="btn" onClick={() => { setReport(null); setSelectedId(null); }}>Закрыть</button>
      </div>
      <section className="summary">
        <div className="summary-card"><strong>{report.summary.effective_reservations}</strong><span>Действующих броней</span></div>
        <div className="summary-card"><strong>{report.summary.room_nights}</strong><span>Ночей</span></div>
        <div className="summary-card"><strong>{money(report.summary.booked_kgs)}</strong><span>Забронировано</span></div>
        <div className="summary-card"><strong>{money(report.summary.received_kgs)}</strong><span>Получено оплат</span></div>
        <div className="summary-card"><strong>{money(report.summary.average_booking_kgs)}</strong><span>Средняя бронь</span></div>
        <div className="summary-card"><strong>{report.summary.cancelled_or_no_show}</strong><span>Отмен / no-show</span></div>
      </section>

      <h3>Бронирования</h3>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead><tr><th>Бронь</th><th>Гость</th><th>Номер</th><th>Период</th><th>Сумма</th><th>Получено</th><th>Скидка</th><th>Допмест</th></tr></thead>
          <tbody>{report.reservations.map((item) => <tr key={item.id}>
            <td><strong>{item.booking_number}</strong><br/><small>{item.status}</small></td>
            <td>{item.guest_name || "—"}<br/><small>{item.guest_phone || ""}</small></td><td>{item.rooms || "—"}</td><td>{item.check_in} → {item.check_out}</td>
            <td>{money(item.total_kgs)}</td><td>{money(item.received_kgs)}</td><td>{item.discount_percent}%</td><td>{item.extra_bed_count}</td>
          </tr>)}</tbody>
        </table>
      </div>

      <h3 style={{ marginTop: 20 }}>Взаимодействия</h3>
      <form className="controls" onSubmit={addInteraction}>
        <div className="control"><label>Тип</label><select value={interactionKind} onChange={(e) => setInteractionKind(e.target.value)}><option value="NOTE">Заметка</option><option value="CALL">Звонок</option><option value="WHATSAPP">WhatsApp</option><option value="MESSAGE">Сообщение</option><option value="MEETING">Встреча</option><option value="TASK">Задача</option></select></div>
        <div className="control"><label>Что произошло / что сделать</label><input required value={interactionNote} onChange={(e) => setInteractionNote(e.target.value)} /></div>
        <div className="control"><label>Следующий контакт</label><input type="datetime-local" value={nextContactAt} onChange={(e) => setNextContactAt(e.target.value)} /></div>
        <div className="date-actions"><button className="btn primary" disabled={busy}>Сохранить</button></div>
      </form>
      <div>{report.interactions.map((item) => <article key={item.id} style={{ padding: "10px 0", borderBottom: "1px solid rgba(255,255,255,.08)" }}><strong>{item.kind}</strong> · <small>{new Date(item.created_at).toLocaleString("ru-RU")}</small><div>{item.note}</div>{item.next_contact_at && <small>Следующий контакт: {new Date(item.next_contact_at).toLocaleString("ru-RU")}</small>}</article>)}</div>
    </section>}
  </main>;
}