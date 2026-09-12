"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type Lead = {
  id: string;
  status: string;
  source?: string | null;
  guest_name: string;
  phone: string;
  email?: string | null;
  check_in?: string | null;
  check_out?: string | null;
  quoted_total_kgs?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
  reservation?: { id: string; booking_number: string; status: string } | null;
};

type Channel = {
  source: string;
  leads: number;
  converted: number;
  conversion_percent: number;
};

type Report = {
  crm: {
    leads: number;
    new: number;
    quoted: number;
    awaiting_prepayment: number;
    converted: number;
    lost: number;
    conversion_percent: number;
    channels: Channel[];
  };
};

const LOST = new Set(["REJECTED", "CANCELLED", "EXPIRED"]);
const ACTIVE = new Set(["NEW", "QUOTED", "AWAITING_PREPAYMENT"]);

const statusLabel: Record<string, string> = {
  NEW: "Новый",
  QUOTED: "Рассчитан",
  AWAITING_PREPAYMENT: "Ждём оплату",
  CONVERTED: "Бронь",
  CANCELLED: "Отменён",
  REJECTED: "Отклонён",
  EXPIRED: "Истёк",
};

function isoDate(value: Date) {
  return value.toISOString().slice(0, 10);
}

function sourceLabel(value?: string | null) {
  const source = (value || "UNKNOWN").trim().toUpperCase();
  const known: Record<string, string> = {
    WEBSITE: "Сайт",
    WEB: "Сайт",
    WHATSAPP: "WhatsApp",
    INSTAGRAM: "Instagram",
    TELEGRAM: "Telegram",
    PHONE: "Телефон",
    MANUAL: "Вручную",
    RECEPTION: "Ресепшен",
    UNKNOWN: "Не определён",
  };
  return known[source] || value || "Не определён";
}

function money(value?: number | null) {
  if (value == null) return "—";
  return `${new Intl.NumberFormat("ru-RU").format(value)} сом`;
}

export default function MarketingBoard() {
  const [days, setDays] = useState(30);
  const [report, setReport] = useState<Report | null>(null);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [segment, setSegment] = useState("ACTIVE");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const to = new Date();
    const from = new Date(to);
    from.setDate(from.getDate() - Math.max(days - 1, 0));
    const params = new URLSearchParams({ from_date: isoDate(from), to_date: isoDate(to) });
    try {
      const [reportResponse, leadsResponse] = await Promise.all([
        fetch(`/core/api/v1/admin/reports/overview?${params.toString()}`, { cache: "no-store" }),
        fetch("/core/api/v1/admin/booking/requests?limit=200", { cache: "no-store" }),
      ]);
      if (!reportResponse.ok) throw new Error("Не удалось загрузить маркетинговую аналитику");
      if (!leadsResponse.ok) throw new Error("Не удалось загрузить базу лидов");
      const reportBody = await reportResponse.json();
      const leadsBody = await leadsResponse.json();
      setReport(reportBody as Report);
      setLeads((leadsBody.items || []) as Lead[]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка загрузки маркетинга");
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => { void load(); }, [load]);

  const segments = useMemo(() => {
    const active = leads.filter((item) => ACTIVE.has(item.status));
    const unpaid = leads.filter((item) => item.status === "AWAITING_PREPAYMENT");
    const converted = leads.filter((item) => item.status === "CONVERTED");
    const lost = leads.filter((item) => LOST.has(item.status));
    const website = leads.filter((item) => ["WEB", "WEBSITE", "SITE"].includes((item.source || "").toUpperCase()));
    const whatsapp = leads.filter((item) => (item.source || "").toUpperCase().includes("WHATSAPP"));
    const instagram = leads.filter((item) => (item.source || "").toUpperCase().includes("INSTAGRAM"));
    return { ACTIVE: active, UNPAID: unpaid, CONVERTED: converted, LOST: lost, WEBSITE: website, WHATSAPP: whatsapp, INSTAGRAM: instagram };
  }, [leads]);

  const visible = (segments as Record<string, Lead[]>)[segment] || [];
  const quotedPipeline = visible.reduce((sum, item) => sum + Number(item.quoted_total_kgs || 0), 0);

  function exportAudience() {
    const header = ["Lead ID", "Имя", "Телефон", "Email", "Источник", "Статус", "Заезд", "Выезд", "Потенциал KGS"];
    const rows = visible.map((item) => [item.id, item.guest_name, item.phone, item.email || "", item.source || "", statusLabel[item.status] || item.status, item.check_in || "", item.check_out || "", item.quoted_total_kgs || ""]);
    const escape = (value: unknown) => `"${String(value ?? "").replace(/"/g, '""')}"`;
    const csv = "\uFEFF" + [header, ...rows].map((row) => row.map(escape).join(";")).join("\r\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `three-crowns-marketing-${segment.toLowerCase()}-${isoDate(new Date())}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  return (
    <main className="marketing-shell">
      <header className="marketing-head">
        <div>
          <p className="eyebrow">CRM · продажи · возврат гостей</p>
          <h1>Маркетинг</h1>
          <p>Единый центр лидов и каналов продаж. Источник истины — реальные заявки, бронирования и данные PMS.</p>
        </div>
        <div className="marketing-actions">
          <select value={days} onChange={(event) => setDays(Number(event.target.value))} aria-label="Период">
            <option value={30}>30 дней</option>
            <option value={90}>90 дней</option>
            <option value={365}>365 дней</option>
          </select>
          <button className="btn" onClick={load}>Обновить</button>
        </div>
      </header>

      {error && <div className="error-box">{error}</div>}
      {loading ? <div className="loading">Загрузка маркетинга…</div> : <>
        <section className="marketing-kpis">
          <article><span>Лиды</span><strong>{report?.crm.leads ?? 0}</strong><small>за выбранный период</small></article>
          <article><span>Новые</span><strong>{report?.crm.new ?? 0}</strong><small>нужен первый контакт</small></article>
          <article><span>Ждём оплату</span><strong>{report?.crm.awaiting_prepayment ?? 0}</strong><small>горячая аудитория</small></article>
          <article><span>Брони</span><strong>{report?.crm.converted ?? 0}</strong><small>конвертированные лиды</small></article>
          <article><span>Конверсия</span><strong>{(report?.crm.conversion_percent ?? 0).toFixed(1)}%</strong><small>лид → бронь</small></article>
          <article><span>Потеряны</span><strong>{report?.crm.lost ?? 0}</strong><small>отмена / отказ / истёк</small></article>
        </section>

        <section className="marketing-grid">
          <article className="marketing-panel">
            <div className="marketing-panel-head"><div><p className="eyebrow">Attribution</p><h2>Каналы продаж</h2></div></div>
            <div className="marketing-channel-list">
              {(report?.crm.channels || []).length === 0 && <div className="empty small">За период лидов нет.</div>}
              {(report?.crm.channels || []).map((channel) => (
                <div className="marketing-channel" key={channel.source}>
                  <div><b>{sourceLabel(channel.source)}</b><small>{channel.converted} броней из {channel.leads} лидов</small></div>
                  <strong>{Number(channel.conversion_percent || 0).toFixed(1)}%</strong>
                </div>
              ))}
            </div>
          </article>

          <article className="marketing-panel">
            <div className="marketing-panel-head"><div><p className="eyebrow">Automation-ready</p><h2>Следующие сценарии</h2></div></div>
            <div className="marketing-automation-list">
              <div><b>Не оплачена бронь</b><span>{segments.UNPAID.length} лидов</span><small>напоминание после согласованного срока</small></div>
              <div><b>Потерянные лиды</b><span>{segments.LOST.length} лидов</span><small>кампания возврата с новым предложением</small></div>
              <div><b>После проживания</b><span>следующий этап</span><small>отзыв + повторное бронирование</small></div>
              <div><b>Прошлый сезон</b><span>следующий этап</span><small>раннее бронирование для существующей базы</small></div>
            </div>
          </article>
        </section>

        <section className="marketing-panel marketing-audience">
          <div className="marketing-panel-head">
            <div><p className="eyebrow">Audience</p><h2>Сегменты клиентской базы</h2><p>Сегменты строятся из реальных заявок. Массовая отправка не запускается без выбранного канала и согласия клиента.</p></div>
            <button className="btn" onClick={exportAudience} disabled={visible.length === 0}>Экспорт аудитории</button>
          </div>
          <div className="marketing-segments">
            <button className={segment === "ACTIVE" ? "active" : ""} onClick={() => setSegment("ACTIVE")}>Активные · {segments.ACTIVE.length}</button>
            <button className={segment === "UNPAID" ? "active" : ""} onClick={() => setSegment("UNPAID")}>Ждут оплату · {segments.UNPAID.length}</button>
            <button className={segment === "CONVERTED" ? "active" : ""} onClick={() => setSegment("CONVERTED")}>Забронировали · {segments.CONVERTED.length}</button>
            <button className={segment === "LOST" ? "active" : ""} onClick={() => setSegment("LOST")}>Потерянные · {segments.LOST.length}</button>
            <button className={segment === "WEBSITE" ? "active" : ""} onClick={() => setSegment("WEBSITE")}>Сайт · {segments.WEBSITE.length}</button>
            <button className={segment === "WHATSAPP" ? "active" : ""} onClick={() => setSegment("WHATSAPP")}>WhatsApp · {segments.WHATSAPP.length}</button>
            <button className={segment === "INSTAGRAM" ? "active" : ""} onClick={() => setSegment("INSTAGRAM")}>Instagram · {segments.INSTAGRAM.length}</button>
          </div>
          <div className="marketing-audience-summary"><span>Контактов: <b>{visible.length}</b></span><span>Потенциал: <b>{money(quotedPipeline)}</b></span></div>
          <div className="marketing-leads">
            {visible.length === 0 && <div className="empty small">В этом сегменте пока нет контактов.</div>}
            {visible.slice(0, 50).map((item) => (
              <div className="marketing-lead" key={item.id}>
                <div><b>{item.guest_name}</b><small>{item.phone}{item.email ? ` · ${item.email}` : ""}</small></div>
                <span>{sourceLabel(item.source)}</span>
                <span>{statusLabel[item.status] || item.status}</span>
                <strong>{money(item.quoted_total_kgs)}</strong>
              </div>
            ))}
          </div>
        </section>

        <section className="marketing-panel">
          <div className="marketing-panel-head"><div><p className="eyebrow">Campaigns</p><h2>Кампании и автоматические касания</h2></div></div>
          <div className="marketing-roadmap">
            <div><b>Этап 1 · готов</b><p>Аудитории, воронка, источники, конверсия и экспорт базы внутри PMS.</p></div>
            <div><b>Этап 2 · подключение каналов</b><p>WhatsApp и Instagram/Meta: входящие лиды, единый источник и история контакта.</p></div>
            <div><b>Этап 3 · автоматизация</b><p>n8n: неоплата, брошенная заявка, отзыв после выезда, возврат прошлогодних гостей.</p></div>
          </div>
        </section>
      </>}
    </main>
  );
}
