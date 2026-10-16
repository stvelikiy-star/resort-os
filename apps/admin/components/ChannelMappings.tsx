"use client";
import { FormEvent, useCallback, useEffect, useState } from "react";
import styles from "./ChannelManagerBoard.module.css";
const copy = {
 ru: ["Сопоставление номеров и тарифов", "Настройки для будущего подключения. Сохранение не включает синхронизацию. Укажите точные идентификаторы из кабинета площадки; категория не назначает конкретную комнату.", "Площадка", "ID отеля на площадке", "ID категории на площадке", "ID тарифа на площадке", "Категория MARINA", "Тариф MARINA (KGS)", "Сохранить связь", "Изменить", "Активна", "Новая связь", "Сохранено. Площадка ещё не подключена.", "Ошибка", "Связь уже изменена. Обновите список.", "Обновить", "Выберите", "Связей пока нет"],
 en: ["Room and rate mapping", "Configuration for a future connection. Saving does not enable synchronization. Enter exact platform account identifiers; category mapping does not assign a physical room.", "Platform", "External property ID", "External room type ID", "External rate plan ID", "MARINA room type", "MARINA rate plan (KGS)", "Save mapping", "Edit", "Active", "New mapping", "Saved. Platform is still disconnected.", "Error", "Mapping has changed. Refresh the list.", "Refresh", "Choose", "No mappings yet"],
 kg: ["Бөлмө жана тариф байланышы", "Кийинки туташуу үчүн жөндөөлөр. Сактоо синхрондоштурууну иштетпейт. Платформадагы так ID коддорун жазыңыз; категория конкреттүү бөлмөнү дайындабайт.", "Платформа", "Платформадагы объект ID", "Платформадагы категория ID", "Платформадагы тариф ID", "MARINA категориясы", "MARINA тарифи (KGS)", "Байланышты сактоо", "Өзгөртүү", "Активдүү", "Жаңы байланыш", "Сакталды. Платформа туташа элек.", "Ката", "Байланыш өзгөрдү. Тизмени жаңыртыңыз.", "Жаңыртуу", "Тандаңыз", "Байланыштар азырынча жок"],
 kz: ["Бөлме мен тариф сәйкестігі", "Кейінгі қосылымға арналған баптаулар. Сақтау синхрондауды қоспайды. Платформадағы нақты ID кодтарын енгізіңіз; санат нақты бөлмені тағайындамайды.", "Платформа", "Платформадағы нысан ID", "Платформадағы санат ID", "Платформадағы тариф ID", "MARINA санаты", "MARINA тарифі (KGS)", "Байланысты сақтау", "Өзгерту", "Белсенді", "Жаңа байланыс", "Сақталды. Платформа әлі қосылмаған.", "Қате", "Байланыс өзгерді. Тізімді жаңартыңыз.", "Жаңарту", "Таңдаңыз", "Байланыстар әзірше жоқ"],
};
type Mapping = { id: string; provider: string; external_property_id: string; external_room_type_id: string; external_rate_plan_id: string; room_type_id: string; rate_plan_id: string; currency: string; active: boolean; revision: number };
type Target = { id: string; code: string; name: string; currency?: string };
type Data = { items: Mapping[]; room_types: Target[]; rate_plans: Target[] };
const initial = { provider: "BOOKING_COM", external_property_id: "", external_room_type_id: "", external_rate_plan_id: "", room_type_id: "", rate_plan_id: "", active: true, expected_revision: 0 };
export default function ChannelMappings({ locale }: { locale: keyof typeof copy }) {
 const t = copy[locale];
 const [data, setData] = useState<Data | null>(null);
 const [form, setForm] = useState(initial);
 const [busy, setBusy] = useState(false);
 const [notice, setNotice] = useState<"saved" | "stale" | "error" | null>(null);
 const load = useCallback(async (signal?: AbortSignal) => {
  try {
   const response = await fetch("/core/api/v1/admin/channels/mappings", { cache: "no-store", signal });
   if (!response.ok) throw new Error("load");
   setData(await response.json() as Data);
  } catch { if (!signal?.aborted) setNotice("error"); }
 }, []);
 useEffect(() => { const controller = new AbortController(); void load(controller.signal); return () => controller.abort(); }, [load]);
 async function save(event: FormEvent) {
  event.preventDefault(); setBusy(true); setNotice(null);
  try {
   const response = await fetch("/core/api/v1/admin/channels/mappings", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...form, currency: "KGS" }) });
   const result = await response.json();
   if (!response.ok) { setNotice(result.detail?.code === "CHANNEL_MAPPING_STALE" ? "stale" : "error"); return; }
   setNotice("saved"); setForm(initial); await load();
  } catch { setNotice("error"); } finally { setBusy(false); }
 }
 return <section className={styles.form} aria-label={t[0]}>
  <h2>{t[0]}</h2><p>{t[1]}</p>
  <form onSubmit={save}>
   <fieldset disabled={busy || !data}>
    <label>{t[2]}<select aria-label={t[2]} value={form.provider} disabled={form.expected_revision > 0} onChange={e => setForm({ ...form, provider: e.target.value })}><option value="BOOKING_COM">Booking.com</option><option value="AIRBNB">Airbnb</option><option value="OSTROVOK">Ostrovok</option></select></label>
    {(["external_property_id", "external_room_type_id", "external_rate_plan_id"] as const).map((key, index) => <label key={key}>{t[3 + index]}<input required maxLength={180} value={form[key]} readOnly={form.expected_revision > 0} onChange={e => setForm({ ...form, [key]: e.target.value })} /></label>)}
    <label>{t[6]}<select aria-label={t[6]} required value={form.room_type_id} onChange={e => setForm({ ...form, room_type_id: e.target.value })}><option value="">{t[16]}</option>{data?.room_types.map(item => <option key={item.id} value={item.id}>{item.code} · {item.name}</option>)}</select></label>
    <label>{t[7]}<select aria-label={t[7]} required value={form.rate_plan_id} onChange={e => setForm({ ...form, rate_plan_id: e.target.value })}><option value="">{t[16]}</option>{data?.rate_plans.filter(item => item.currency === "KGS").map(item => <option key={item.id} value={item.id}>{item.code} · {item.name}</option>)}</select></label>
    <label>{t[10]}<input type="checkbox" checked={form.active} onChange={e => setForm({ ...form, active: e.target.checked })} /></label>
   </fieldset>
   <div className={styles.actions}><button type="submit" disabled={busy || !data}>{t[8]}</button><button type="button" disabled={busy} onClick={() => { setForm(initial); setNotice(null); }}>{t[11]}</button><button type="button" disabled={busy} onClick={() => { setNotice(null); void load(); }}>{t[15]}</button></div>
  </form>
  {notice ? <p role={notice === "saved" ? "status" : "alert"}>{notice === "saved" ? t[12] : notice === "stale" ? t[14] : t[13]}</p> : null}
  <div className={styles.list}>{data?.items.map(item => <article key={item.id}><div><strong>{item.provider === "BOOKING_COM" ? "Booking.com" : item.provider === "AIRBNB" ? "Airbnb" : "Ostrovok"}</strong><p>{item.external_property_id} / {item.external_room_type_id} / {item.external_rate_plan_id}</p><p>{data.room_types.find(target => target.id === item.room_type_id)?.name} · {data.rate_plans.find(target => target.id === item.rate_plan_id)?.name}</p><span>{t[10]}: {item.active ? "✓" : "—"} · v{item.revision}</span></div><button type="button" disabled={busy} onClick={() => { setForm({ provider: item.provider, external_property_id: item.external_property_id, external_room_type_id: item.external_room_type_id, external_rate_plan_id: item.external_rate_plan_id, room_type_id: item.room_type_id, rate_plan_id: item.rate_plan_id, active: item.active, expected_revision: item.revision }); setNotice(null); }}>{t[9]}</button></article>)}</div>
  {data && !data.items.length ? <p>{t[17]}</p> : null}
 </section>;
}
