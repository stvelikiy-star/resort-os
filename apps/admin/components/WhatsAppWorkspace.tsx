"use client";

import { useState } from "react";
import InboxBoard from "./InboxBoard";
import styles from "./WhatsAppWorkspace.module.css";

type Section = "INBOX" | "LEADS" | "AI" | "CONNECT";
type Props = {
  role: string;
  onNavigate: (tab: "REQUESTS" | "RESERVATIONS" | "HOTEL_RULES" | "PMS") => void;
};

const steps: { id: Section; number: string; title: string; subtitle: string }[] = [
  { id: "INBOX", number: "01", title: "Входящие", subtitle: "Обращения гостей" },
  { id: "LEADS", number: "02", title: "Заявки и брони", subtitle: "Передача в шахматку" },
  { id: "AI", number: "03", title: "MARINA AI", subtitle: "Ответы по правилам отеля" },
  { id: "CONNECT", number: "04", title: "Подключение", subtitle: "Номер и права доступа" },
];

export default function WhatsAppWorkspace({ role, onNavigate }: Props) {
  const [section, setSection] = useState<Section>("INBOX");
  const isManager = role === "OWNER" || role === "MANAGER";
  return <main className={styles.root}>
    <header className={styles.header}>
      <div>
        <p className="eyebrow">MARINA SMART · Коммуникации</p>
        <h1>WhatsApp гостиницы</h1>
        <p className="subtitle">Диалоги гостей, предварительные заявки и MARINA AI — в одном рабочем месте.</p>
      </div>
      <div className={styles.offline} role="status">WhatsApp не подключён · тестовая подготовка</div>
    </header>

    <nav aria-label="Этапы работы с WhatsApp" className={styles.steps}>
      {steps.map((step) => <button
        key={step.id}
        type="button"
        onClick={() => setSection(step.id)}
        className={section === step.id ? styles.selected : ""}
        aria-current={section === step.id ? "step" : undefined}
      >
        <span className={styles.number}>{step.number}</span>
        <span><strong>{step.title}</strong><small>{step.subtitle}</small></span>
      </button>)}
    </nav>

    {section === "INBOX" && <section aria-label="Входящие сообщения">
      <div className={styles.notice}>
        <strong>Рабочий порядок:</strong> откройте диалог → уточните даты и гостей → проверьте наличие в шахматке → сохраните заявку → передайте гостю подтверждение только после проверки администратором.
        <p>В этом разделе видны только сообщения WhatsApp, уже сохранённые в CRM. Пока провайдер не подключён, новые сообщения с телефона сюда не поступают и отправить ответ в WhatsApp нельзя.</p>
      </div>
      <InboxBoard channelKind="WHATSAPP" role={role} />
    </section>}

    {section === "LEADS" && <section className={styles.section}>
      <h2>Заявка → проверка → бронирование</h2>
      <p>Переписка и бронь — разные записи. Сообщение гостя не занимает номер автоматически. Администратор проверяет доступность, тариф, правила и условия предоплаты перед подтверждением.</p>
      <div className={styles.sequence}>
        <span>Обращение</span><span>Заявка</span><span>Проверка цены и номера</span><span>Подтверждение</span>
      </div>
      <div className={styles.actions}>
        {isManager && <button className="btn primary" onClick={() => onNavigate("REQUESTS")}>Открыть CRM / Заявки</button>}
        <button className="btn" onClick={() => onNavigate("PMS")}>Проверить шахматку</button>
        <button className="btn" onClick={() => onNavigate("RESERVATIONS")}>Рабочее место ресепшена</button>
      </div>
      <p className={styles.small}>Автоматическое создание заявки из WhatsApp пока не активировано. Подтверждённая бронь появляется только через действующий процесс PMS.</p>
    </section>}

    {section === "AI" && <section className={styles.section}>
      <h2>MARINA AI — правила общения</h2>
      <p>AI должен брать название отеля, услуги и правила из его настроек, а цены и доступность — только из живых данных MARINA SMART. Он не вправе объявлять оплату полученной или бронь подтверждённой без данных PMS.</p>
      <div className={styles.tiles}>
        <article><strong>Консультация</strong><span>Услуги, расположение, условия проживания.</span></article>
        <article><strong>Наличие и цена</strong><span>Проверка в PMS для указанных дат и гостей.</span></article>
        <article><strong>Предварительная заявка</strong><span>Передача контактов и дат администратору.</span></article>
        <article><strong>Передача человеку</strong><span>Сложные вопросы — ответственному сотруднику.</span></article>
      </div>
      <div className={styles.actions}>
        {isManager && <button className="btn primary" onClick={() => onNavigate("HOTEL_RULES")}>Открыть правила гостиницы</button>}
      </div>
      <p className={styles.small}>Автоответы WhatsApp выключены. Текущий раздел объясняет рабочие правила и не имитирует отправку сообщений.</p>
    </section>}

    {section === "CONNECT" && <section className={styles.section}>
      <h2>Подключение WhatsApp</h2>
      <p>У каждой гостиницы будет собственный номер и собственные переписки. Техническая интеграция Green-API сознательно отложена, поэтому сейчас нельзя выдавать QR-код или показывать ложный статус «Подключено».</p>
      <div className={styles.tiles}>
        <article><strong>1. Номер гостиницы</strong><span>Закрепляем номер только за одним объектом MARINA SMART.</span></article>
        <article><strong>2. Подключение по QR</strong><span>Будет доступно после включения безопасного провайдера.</span></article>
        <article><strong>3. Проверка сообщений</strong><span>Тестируем приём и отправку с отдельного телефона.</span></article>
        <article><strong>4. Включение MARINA AI</strong><span>Только после проверки правил, ролей и предварительных заявок.</span></article>
      </div>
      <p className={styles.small}>QR, отправка, массовые сообщения и автоматический приём броней пока недоступны. Никакие реальные номера не изменены.</p>
    </section>}
  </main>;
}
