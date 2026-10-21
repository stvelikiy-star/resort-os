"use client";

import { FormEvent, useEffect, useState } from "react";

type Rules = {
  prepayment_type: "NOT_SET" | "FIRST_NIGHT" | "PERCENT" | "FIXED" | "NONE";
  prepayment_value: number;
  prepayment_deadline_hours: number | null;
  free_cancellation_days: number | null;
  late_cancellation_penalty: string;
  no_show_policy: string;
  children_policy: string;
  extra_bed_policy: string;
  pets_policy: string;
  smoking_policy: string;
  early_checkin_policy: string;
  late_checkout_policy: string;
  included_services: string;
  additional_information: string;
  hotel_short_description: string;
  location_address: string;
  location_directions: string;
  official_website: string;
  official_contact: string;
  reception_hours: string;
  checkin_instructions: string;
  checkout_instructions: string;
  meal_policy: string;
  restaurant_info: string;
  parking_policy: string;
  wifi_info: string;
  pool_spa_policy: string;
  transfer_transport: string;
  nearby_attractions: string;
  accessibility_policy: string;
  payment_methods_info: string;
  quiet_hours_policy: string;
  booking_contact_policy: string;
  ai_faq: string;
  ai_escalation_policy: string;
};
type State = { property_name: string; version: number; rules: Rules; updated_at: string | null };
type Topic = { title: string; explanation: string; fields: { key: keyof Rules; label: string; hint: string; rows?: number }[] };
const topics: Topic[] = [
  { title: "01 · О гостинице и контактах", explanation: "Только достоверные сведения, которые MARINA AI сможет сообщить гостю.", fields: [
    { key: "hotel_short_description", label: "Как представить гостиницу гостю", hint: "Что это за отель, главные преимущества, для кого подходит" },
    { key: "location_address", label: "Полный адрес", hint: "Кыргызстан, город, улица, дом" },
    { key: "location_directions", label: "Как добраться", hint: "Ориентиры, подъезд, вход, схема маршрута", rows: 3 },
    { key: "official_website", label: "Официальный сайт", hint: "https://..." },
    { key: "official_contact", label: "Телефон / WhatsApp для гостей", hint: "Публикуемый контакт гостиницы" },
    { key: "reception_hours", label: "Время работы ресепшена", hint: "Круглосуточно или конкретный график" },
    { key: "nearby_attractions", label: "Что рядом с гостиницей", hint: "Пляж, транспорт, достопримечательности", rows: 3 },
  ] },
  { title: "02 · Заезд и правила проживания", explanation: "Условия, которые сотрудник и MARINA AI объясняют перед заселением.", fields: [
    { key: "checkin_instructions", label: "Порядок заселения", hint: "Куда подойти, какие условия выполнить (без персональных документов гостя)" },
    { key: "checkout_instructions", label: "Порядок выезда", hint: "Ключи, осмотр, возврат депозита при наличии правил" },
    { key: "children_policy", label: "Дети", hint: "Возраст, проживание, ограничения" },
    { key: "extra_bed_policy", label: "Дополнительное место", hint: "Наличие, тариф, порядок согласования" },
    { key: "pets_policy", label: "Животные", hint: "Разрешены ли, условия" },
    { key: "smoking_policy", label: "Курение", hint: "Где разрешено и запрещено" },
    { key: "quiet_hours_policy", label: "Тихие часы", hint: "Например, с 23:00 до 08:00" },
    { key: "early_checkin_policy", label: "Ранний заезд", hint: "Условия и возможные доплаты" },
    { key: "late_checkout_policy", label: "Поздний выезд", hint: "Условия и возможные доплаты" },
    { key: "accessibility_policy", label: "Доступность и особые условия", hint: "Лифт, пандусы, ограничения без неподтверждённых обещаний" },
  ] },
  { title: "03 · Питание и услуги", explanation: "Что включено, что оплачивается отдельно и что требует уточнения.", fields: [
    { key: "included_services", label: "Услуги в стоимости", hint: "Только действительно включённые услуги", rows: 3 },
    { key: "meal_policy", label: "Условия питания", hint: "Завтрак, тип питания, расписание, доплаты" },
    { key: "restaurant_info", label: "Ресторан / столовая", hint: "Меню, режим работы, доступность" },
    { key: "parking_policy", label: "Парковка", hint: "Наличие, стоимость, ограничения" },
    { key: "wifi_info", label: "Интернет и Wi-Fi", hint: "Есть ли Wi-Fi и где работает; НЕ указывайте пароль" },
    { key: "pool_spa_policy", label: "Бассейн / SPA / источники", hint: "Режим, условия доступа, ограничения" },
    { key: "transfer_transport", label: "Трансфер / транспорт", hint: "Как заказать и сколько стоит, если подтверждено" },
  ] },
  { title: "04 · Оплата, отмена и бронирование", explanation: "Настройки предоплаты — выше; здесь дополнительные подтверждённые условия для ответов AI.", fields: [
    { key: "late_cancellation_penalty", label: "Поздняя отмена", hint: "Штраф или порядок расчёта" },
    { key: "no_show_policy", label: "Незаезд гостя", hint: "Что происходит при незаезде" },
    { key: "payment_methods_info", label: "Доступные способы оплаты", hint: "Только способы, реально принимаемые гостиницей; никаких реквизитов или секретов" },
    { key: "booking_contact_policy", label: "Как оформлять заявки", hint: "Какие сведения уточнять, когда передавать менеджеру, как подтверждать" },
  ] },
  { title: "05 · Знания MARINA AI и передача человеку", explanation: "Факты для ответов; не записывайте здесь команды, пароли, реквизиты карт или данные гостей.", fields: [
    { key: "ai_faq", label: "Частые вопросы и точные ответы", hint: "Вопрос: ...\nОтвет: ...\n\nВопрос: ...\nОтвет: ...", rows: 8 },
    { key: "ai_escalation_policy", label: "Когда передать обращение человеку", hint: "Например: спор по оплате, претензия, нестандартное размещение", rows: 4 },
    { key: "additional_information", label: "Дополнительные сведения", hint: "Подтверждённые факты, не вошедшие в другие поля", rows: 4 },
  ] },
];
const important: (keyof Rules)[] = ["hotel_short_description", "location_address", "official_contact", "reception_hours", "checkin_instructions", "meal_policy", "included_services", "booking_contact_policy", "ai_faq", "ai_escalation_policy"];

export default function HotelRulesBoard() {
  const [state, setState] = useState<State | null>(null);
  const [rules, setRules] = useState<Rules | null>(null);
  const [busy, setBusy] = useState(false);
  const [activeTopic, setActiveTopic] = useState(0);
  const [savedSnapshot, setSavedSnapshot] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  async function load() {
    setError("");
    const response = await fetch("/core/api/v1/admin/hotel-rules", { cache: "no-store" });
    if (!response.ok) { setError("Не удалось загрузить правила"); return; }
    const data: State = await response.json();
    setState(data);
    setRules(data.rules);
    setSavedSnapshot(JSON.stringify(data.rules));
  }
  useEffect(() => { void load(); }, []);
  function change<K extends keyof Rules>(key: K, value: Rules[K]) {
    setRules(old => old ? { ...old, [key]: value } : old);
    setNotice("");
  }
  async function save(event: FormEvent) {
    event.preventDefault();
    if (!state || !rules || busy) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const response = await fetch("/core/api/v1/admin/hotel-rules", {
        method: "PUT", headers: { "content-type": "application/json" },
        body: JSON.stringify({ expected_version: state.version, rules }),
      });
      if (response.status === 409) {
        setError("Правила уже изменены в другой вкладке. Обновите страницу и проверьте изменения.");
        return;
      }
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(typeof body.detail === "string" ? body.detail : "Не удалось сохранить правила");
      }
      const updated: State = await response.json();
      setState(updated); setRules(updated.rules); setSavedSnapshot(JSON.stringify(updated.rules));
      setNotice("Сохранено. MARINA AI будет использовать обновлённые правила в следующих ответах.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Ошибка сохранения");
    } finally { setBusy(false); }
  }
  const filled = rules ? important.filter(key => Boolean(String(rules[key] ?? "").trim())).length : 0;
  const changed = rules ? JSON.stringify(rules) !== savedSnapshot : false;
  if (!state || !rules) return <main className="work-shell management-shell"><h1>Правила и знания отеля для MARINA AI</h1><p>{error || "Загружаем правила…"}</p><button className="btn" onClick={() => void load()}>Обновить</button></main>;
  return <main className="work-shell management-shell">
    <div className="work-header"><div><p className="eyebrow">MARINA SMART · Настройки</p><h1>Правила и знания отеля для MARINA AI</h1>
      <p className="subtitle">База знаний гостиницы «{state.property_name}». MARINA AI читает сохранённые проверенные правила именно этого объекта. Оплаты и действующие брони не изменяются.</p></div></div>
    <div className="hotel-knowledge-status"><strong>Основные сведения: {filled} из {important.length}</strong><span>{changed ? "Есть несохранённые изменения" : "Изменения сохранены"} · версия {state.version}</span><progress max={important.length} value={filled} aria-label="Заполненность основных сведений" /><small>Это подсказка по заполнению, не гарантия правильности ответов AI.</small></div>
    {error && <div className="error-box" role="alert">{error}</div>}
    {notice && <p role="status">{notice}</p>}
    <form onSubmit={save} className="management-form">
      <h2>Предоплата</h2>
      <label><span>Как берём предоплату?</span><select value={rules.prepayment_type} onChange={e => { const val=e.target.value as Rules["prepayment_type"]; change("prepayment_type", val); if(val!=="PERCENT" && val!=="FIXED") change("prepayment_value", 0); }}>
        <option value="NOT_SET">Пока не указано</option><option value="NONE">Без предоплаты</option><option value="FIRST_NIGHT">За первые сутки</option><option value="PERCENT">Процент от стоимости</option><option value="FIXED">Фиксированная сумма</option>
      </select></label>
      {(rules.prepayment_type==="PERCENT" || rules.prepayment_type==="FIXED") && <label><span>{rules.prepayment_type==="PERCENT" ? "Размер предоплаты, %" : "Сумма предоплаты, сом"}</span><input type="number" min="1" max={rules.prepayment_type==="PERCENT"?100:10000000} value={rules.prepayment_value} onChange={e => change("prepayment_value", Number(e.target.value))} required /></label>}
      <label><span>В течение скольких часов внести предоплату?</span><input type="number" min="1" max="720" placeholder="Не установлено" value={rules.prepayment_deadline_hours ?? ""} onChange={e => change("prepayment_deadline_hours", e.target.value===""?null:Number(e.target.value))} /></label>
      <h2>Отмена бронирования</h2>
      <label><span>Бесплатная отмена за сколько дней до заезда?</span><input type="number" min="0" max="365" placeholder="Не установлено" value={rules.free_cancellation_days ?? ""} onChange={e => change("free_cancellation_days", e.target.value===""?null:Number(e.target.value))} /></label>
      <div className="hotel-knowledge-tabs" role="group" aria-label="Темы базы знаний">
        {topics.map((topic,index) => <button type="button" key={topic.title} aria-pressed={activeTopic===index} className={activeTopic===index?"selected":""} onClick={() => setActiveTopic(index)}>{topic.title}</button>)}
      </div>
      <section className="hotel-knowledge-topic" aria-label={topics[activeTopic].title}>
        <h2>{topics[activeTopic].title}</h2>
        <p>{topics[activeTopic].explanation}</p>
        {topics[activeTopic].fields.map(item => <label key={item.key} className="management-form-wide"><span>{item.label}</span><textarea maxLength={item.key==="ai_faq"?3000:undefined} rows={item.rows || 2} value={String(rules[item.key] ?? "")} onChange={e => change(item.key, e.target.value)} placeholder={item.hint} /><small>{String(rules[item.key] ?? "").length} символов</small></label>)}
      </section>
      <p className="subtitle">Важно: эти сведения используются для информирования и ответов MARINA AI. Автоматическое удержание денег, возврат или изменение старых броней здесь не включаются.</p>
      <div className="management-modal-actions"><button type="button" className="btn" onClick={() => void load()} disabled={busy}>Отменить изменения</button><button className="btn primary" type="submit" disabled={busy || !changed}>{busy ? "Сохраняем…" : "Сохранить знания и правила"}</button></div>
    </form>
  </main>;
}
