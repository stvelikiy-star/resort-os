"use client";
import { useState } from "react";
import styles from "./ChannelManagerBoard.module.css";
const labels = {
 ru: ["Массовый импорт CSV", "До 100 броней в формате MARINA. Проверка не сохраняет данные. Импорт сохраняет весь пакет или ничего. Изменения не отправляются на площадки.", "Шаблон CSV", "Содержимое CSV", "Проверить", "Импортировать", "Проверено", "Импортировано", "Ошибка", "Строка", "Номера: код → room_id"],
 en: ["Bulk CSV import", "Up to 100 bookings in MARINA format. Preview saves nothing. Import saves the entire batch or nothing. Changes are not sent to platforms.", "CSV template", "CSV content", "Preview", "Import", "Checked", "Imported", "Error", "Row", "Rooms: code → room_id"],
 kg: ["CSV топтук импорт", "MARINA форматында 100 бронго чейин. Текшерүү сактабайт. Импорт бүт пакетти сактайт же эч нерсе сактабайт. Платформага жөнөтүлбөйт.", "CSV үлгүсү", "CSV мазмуну", "Текшерүү", "Импорттоо", "Текшерилди", "Импорттолду", "Ката", "Сап", "Бөлмөлөр: код → room_id"],
 kz: ["CSV топтық импорт", "MARINA форматында 100 броньға дейін. Тексеру сақтамайды. Импорт бүкіл пакетті сақтайды немесе ештеңе сақтамайды. Платформаға жіберілмейді.", "CSV үлгісі", "CSV мазмұны", "Тексеру", "Импорттау", "Тексерілді", "Импортталды", "Қате", "Жол", "Бөлмелер: код → room_id"],
};
const header = "provider,external_id,revision,status,room_id,guest_name,phone,check_in,check_out,adults,children,total_kgs,currency\n";
type Props = { locale: keyof typeof labels; rooms: Array<{ id: string; code: string }>; onImported: () => void };
export default function ChannelCsvImport({ locale, rooms, onImported }: Props) {
 const t = labels[locale];
 const [text, setText] = useState("");
 const [checked, setChecked] = useState<string | null>(null);
 const [busy, setBusy] = useState(false);
 const [message, setMessage] = useState("");
 const [failed, setFailed] = useState(false);
 async function submit(preview: boolean) {
  setBusy(true); setMessage(""); setFailed(false); setChecked(null);
  try {
   const response = await fetch("/core/api/v1/admin/channels/reservations/csv", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ csv_text: text, preview }) });
   const result = await response.json();
   if (!response.ok) {
    setFailed(true); setMessage(`${t[8]}${result.detail?.row ? ` · ${t[9]} ${result.detail.row}` : ""} · ${result.detail?.code || response.status}${result.detail?.message ? ` · ${result.detail.message}` : ""}`); return;
   }
   setMessage(`${preview ? t[6] : t[7]}: ${result.count}`);
   if (preview) setChecked(text); else onImported();
  } catch { setFailed(true); setMessage(t[8]); }
  finally { setBusy(false); }
 }
 return <section className={styles.form} aria-label={t[0]}>
  <h3>{t[0]}</h3><p>{t[1]}</p>
  <a download="marina-reservations-template.csv" href={`data:text/csv;charset=utf-8,${encodeURIComponent(header)}`}>{t[2]}</a>
  <label>{t[3]}<textarea rows={6} value={text} maxLength={200000} disabled={busy} style={{ width: "100%", maxWidth: "100%", boxSizing: "border-box" }} onChange={event => { setText(event.target.value); setChecked(null); setMessage(""); }} /></label>
  <details><summary>{t[10]}</summary>{rooms.map(room => <p key={room.id} style={{ overflowWrap: "anywhere" }}>{room.code} → {room.id}</p>)}</details>
  <div className={styles.actions}>
   <button type="button" disabled={busy || !text.trim()} onClick={() => void submit(true)}>{t[4]}</button>
   <button type="button" disabled={busy || checked !== text} onClick={() => void submit(false)}>{t[5]}</button>
  </div>
  {message ? <p role={failed ? "alert" : "status"}>{message}</p> : null}
 </section>;
}
