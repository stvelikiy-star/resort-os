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

type Campaign = {
  id: string;
  code: string;
  title_ru: string;
  action_type: "GUEST_REQUEST" | "EXTERNAL_URL" | "AI_PROMPT";
  active_from?: string | null;
  active_to?: string | null;
  is_active: boolean;
  analytics?: {
    clicks?: number;
    requests?: number;
    external_opens?: number;
    ai_prompts?: number;
  };
};

type RecoveryItem = Lead & {
  priority: number;
  reason: string;
  age_hours: number;
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
    SITE: "Сайт",
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

function ageHours(value?: string | null) {
  if (!value) return 0;
  const time = new Date(value).getTime();
  if (!Number.isFinite(time)) return 0;
  return Math.max(Math.floor((Date.now() - time) / 3600000), 0);
}

function contactPriority(item: Lead): RecoveryItem | null {
  const age = ageHours(item.updated_at || item.created_at);
  if (item.status === "AWAITING_PREPAYMENT") {
    return { ...item, priority: 100 + Math.min(age, 72), reason: "Предоплата не подтверждена", age_hours: age };
  }
  if (item.status === "QUOTED" && age >= 12) {
    return { ...item, priority: 80 + Math.min(age, 72), reason: "Расчёт отправлен, нужен follow-up", age_hours: age };
  }
  if (item.status === "NEW") {
    return { ...item, priority: 70 + Math.min(age, 48), reason: "Новая заявка — нужен первый контакт", age_hours: age };
  }
  if (LOST.has(item.status) && age <= 24 * 30) {
    return { ...item, priority: 30, reason: "Потерянный лид — возможен ручной возврат", age_hours: age };
  }
  return null;
}

function phoneHref(phone: string) {
  const cleaned = phone.replace(/[^\d+]/g, "");
  return cleaned ? `tel:${cleaned}` : undefined;
}

function whatsappHref(phone: string) {
  const digits = phone.replace(/\D/g, "");
  return digits ? `https://wa.me/${digits}` : undefined;
}

function campaignActionLabel(value: Campaign["action_type"]) {
  if (value === "GUEST_REQUEST") return "Заявка гостя";
  if (value === "EXTERNAL_URL") return "Внешняя ссылка";
  return "AI-сценарий";
}

export default function MarketingBoard() {
  const [days, setDays] = useState(30);
  const [report, setReport] = useState<Report | null>(null);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
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
      const [reportResponse, leadsResponse, campaignResponse] = await Promise.all([
        fetch(`/core/api/v1/admin/reports/overview?${params.toString()}`, { cache: "no-store" }),
        fetch("/core/api/v1/admin/booking/requests?limit=200", { cache: "no-store" }),
        fetch("/core/api/v1/admin/guest-offers", { cache: "no-store" }),
      ]);
      if (!reportResponse.ok) throw new Error("Не удалось загрузить маркетинговую аналитику");
      if (!leadsResponse.ok) throw new Error("Не удалось загрузить базу лидов");
      if (!campaignResponse.ok) throw new Error("Не удалось загрузить действующие офферы");
      const reportBody = await reportResponse.json();
      const leadsBody = await leadsResponse.json();
      const campaignBody = await campaignResponse.json();
      setReport(reportBody as Report);
      setLeads((leadsBody.items || []) as Lead[]);
      setCampaigns((campaignBody.items || []) as Campaign[]);
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

  const recoveryQueue = useMemo(() => leads
    .map(contactPriority)
    .filter((item): item is RecoveryItem => Boolean(item))
    .sort((a, b) => b.priority - a.priority)
    .slice(0, 20), [leads]);

  const visible = (segments as Record<string, Lead[]>)[segment] || [];
  const quotedPipeline = visible.reduce((sum, item) => sum + Number(item.quoted_total_kgs || 0), 0);
  const activeCampaigns = campaigns.filter((item) => item.is_active);
  const campaignClicks = campaigns.reduce((sum, item) => sum + Number(item.analytics?.clicks || 0), 0);
  const campaignRequests = campaigns.reduce((sum, item) => sum + Number(item.analytics?.requests || 0), 0);

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

        <section className="marketing-panel marketing-recovery">
          <div className="marketing-panel-head">
            <div><p className="eyebrow">Sales recovery</p><h2>Очередь контактов</h2><p>Приоритет формируется из статуса и давности заявки. Это ручная очередь менеджера — автоматическая массовая отправка не выполняется.</p></div>
            <span className="marketing-count-badge">{recoveryQueue.length} к контакту</span>
          </div>
          <div className="marketing-recovery-list">
            {recoveryQueue.length === 0 && <div className="empty small">Срочных контактов сейчас нет.</div>}
            {recoveryQueue.map((item) => {
              const call = phoneHref(item.phone);
              const whatsapp = whatsappHref(item.phone);
              return <div className="marketing-recovery-row" key={item.id}>
                <div className="marketing-recovery-main"><b>{item.guest_name}</b><small>{item.reason} · {item.age_hours} ч. без изменения</small></div>
                <span>{sourceLabel(item.source)}</span>
                <span>{money(item.quoted_total_kgs)}</span>
                <div className="marketing-contact-actions">
                  {call && <a href={call}>Позвонить</a>}
                  {whatsapp && <a href={whatsapp} target="_blank" rel="noreferrer">WhatsApp</a>}
                  {item.email && <a href={`mailto:${item.email}`}>Email</a>}
                </div>
              </div>;
            })}
          </div>
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

        <section className="marketing-panel marketing-campaigns">
          <div className="marketing-panel-head">
            <div><p className="eyebrow">Existing campaign engine</p><h2>Офферы Guest OS</h2><p>Marketing использует уже существующий движок офферов Три Короны, а не создаёт второй независимый контур кампаний.</p></div>
            <div className="marketing-campaign-stats"><span>Всего <b>{campaigns.length}</b></span><span>Активно <b>{activeCampaigns.length}</b></span><span>Клики <b>{campaignClicks}</b></span><span>Заявки <b>{campaignRequests}</b></span></div>
          </div>
          <div className="marketing-campaign-list">
            {campaigns.length === 0 && <div className="empty small">Офферы ещё не созданы.</div>}
            {campaigns.slice(0, 20).map((campaign) => (
              <div className="marketing-campaign-row" key={campaign.id}>
                <div><b>{campaign.title_ru}</b><small>{campaign.code} · {campaignActionLabel(campaign.action_type)}</small></div>
                <span className={campaign.is_active ? "marketing-state active" : "marketing-state"}>{campaign.is_active ? "Активна" : "Выключена"}</span>
                <span>{campaign.analytics?.clicks ?? 0} кликов</span>
                <strong>{campaign.analytics?.requests ?? 0} заявок</strong>
              </div>
            ))}
          </div>
        </section>

        <section className="marketing-panel">
          <div className="marketing-panel-head"><div><p className="eyebrow">Campaigns</p><h2>Контур автоматизации</h2></div></div>
          <div className="marketing-roadmap">
            <div><b>Этап 1 · готов</b><p>Аудитории, воронка, источники, конверсия, экспорт и очередь ручного возврата внутри PMS.</p></div>
            <div><b>Этап 2 · в работе</b><p>Согласия на маркетинг, история касаний, UTM/source tracking и безопасные правила запуска кампаний.</p></div>
            <div><b>Этап 3 · после каналов</b><p>n8n + WhatsApp/Meta: неоплата, брошенная заявка, отзыв после выезда и возврат прошлогодних гостей.</p></div>
          </div>
          <div className="marketing-consent-note"><b>Защита базы:</b> массовые внешние сообщения остаются заблокированными до появления явного marketing consent и журнала отправок. Текущие кнопки связи запускают только индивидуальное действие менеджера.</div>
        </section>
      </>}
    </main>
  );
}
