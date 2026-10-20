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
};
type State = { property_name: string; version: number; rules: Rules; updated_at: string | null };
const labels: { key: keyof Rules; label: string; hint: string }[] = [
  { key: "late_cancellation_penalty", label: "Штраф за позднюю отмену", hint: "Например: удерживается стоимость первых суток" },
  { key: "no_show_policy", label: "Если гость не приехал", hint: "Укажите условия незаезда и возврата" },
  { key: "children_policy", label: "Проживание детей", hint: "Возраст, бесплатное размещение, ограничения" },
  { key: "extra_bed_policy", label: "Дополнительные места", hint: "Наличие, стоимость, порядок предоставления" },
  { key: "pets_policy", label: "Проживание с животными", hint: "Разрешено ли, ограничения и доплаты" },
  { key: "smoking_policy", label: "Курение", hint: "Где разрешено и где запрещено" },
  { key: "early_checkin_policy", label: "Ранний заезд", hint: "Возможность и доплата" },
  { key: "late_checkout_policy", label: "Поздний выезд", hint: "Возможность и доплата" },
  { key: "included_services", label: "Что включено в стоимость", hint: "Завтрак, парковка, бассейн, Wi-Fi и т.д." },
  { key: "additional_information", label: "Другая полезная информация для гостей и MARINA AI", hint: "Только проверенные сведения об отеле" },
];

export default function HotelRulesBoard() {
  const [state, setState] = useState<State | null>(null);
  const [rules, setRules] = useState<Rules | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  async function load() {
    setError("");
    const response = await fetch("/core/api/v1/admin/hotel-rules", { cache: "no-store" });
    if (!response.ok) { setError("Не удалось загрузить правила"); return; }
    const data: State = await response.json();
    setState(data);
    setRules(data.rules);
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
      setState(updated); setRules(updated.rules);
      setNotice("Сохранено. MARINA AI будет использовать обновлённые правила в следующих ответах.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Ошибка сохранения");
    } finally { setBusy(false); }
  }
  if (!state || !rules) return <main className="work-shell management-shell"><h1>Правила отеля</h1><p>{error || "Загружаем правила…"}</p><button className="btn" onClick={() => void load()}>Обновить</button></main>;
  return <main className="work-shell management-shell">
    <div className="work-header"><div><p className="eyebrow">MARINA SMART · Настройки</p><h1>Правила отеля</h1>
      <p className="subtitle">Все условия принадлежат отелю «{state.property_name}». После сохранения MARINA AI читает их из базы этого отеля. Платежи и действующие брони автоматически не изменяются.</p></div></div>
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
      {labels.map(item => <label key={item.key} className="management-form-wide"><span>{item.label}</span><textarea rows={2} value={String(rules[item.key] ?? "")} onChange={e => change(item.key, e.target.value)} placeholder={item.hint} /></label>)}
      <p className="subtitle">Важно: эти сведения используются для информирования и ответов MARINA AI. Автоматическое удержание денег, возврат или изменение старых броней здесь не включаются.</p>
      <div className="management-modal-actions"><button type="button" className="btn" onClick={() => void load()} disabled={busy}>Отменить изменения</button><button className="btn primary" type="submit" disabled={busy}>{busy ? "Сохраняем…" : "Сохранить правила"}</button></div>
    </form>
  </main>;
}
