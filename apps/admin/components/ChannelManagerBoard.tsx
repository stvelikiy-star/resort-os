"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import ChannelCsvImport from "./ChannelCsvImport";
import styles from "./ChannelManagerBoard.module.css";

type Locale = "ru" | "kg" | "kz" | "en";
type Provider = "BOOKING_COM" | "AIRBNB" | "OSTROVOK";
type Item = { provider: Provider; external_id: string; revision: number; status: string; reservation_id: string | null; room_id: string | null; guest_name: string | null; phone: string | null; check_in: string | null; check_out: string | null; total_kgs: number | null; adults: number; children: number };
type Overview = { providers: Array<{ code: Provider; name: string; connected: boolean }>; rooms: Array<{ id: string; code: string }>; items: Item[] };
const names: Record<Provider, string> = { BOOKING_COM: "Booking.com", AIRBNB: "Airbnb", OSTROVOK: "Ostrovok" };
const copy = {
  ru: { title: "Каналы продаж", intro: "Брони с площадок в общей шахматке", boundary: "Сейчас доступен ручной ввод. Автоматические подключения не настроены. Изменения здесь не отправляются на площадки.", disconnected: "Автосинхронизация не подключена", add: "Внести бронь с площадки", edit: "Изменить", cancel: "Отмена в MARINA", confirm: "Отменить бронь в MARINA и освободить даты? На площадке бронь останется без изменений. Оплаты не возвращаются автоматически.", source: "Площадка", external: "Номер брони на площадке", guest: "Имя гостя", phone: "Телефон, если предоставлен", room: "Номер отеля", choose: "Выберите номер", arrival: "Заезд", departure: "Выезд", adults: "Взрослые", children: "Дети", total: "Стоимость проживания, сом", save: "Сохранить в MARINA", reset: "Новая бронь", refresh: "Обновить", history: "Внешние брони", empty: "Внешних броней пока нет", loading: "Загрузка…", saved: "Сохранено. Проверьте бронь в шахматке. Оплата автоматически не начислялась.", cancelled: "Отменена", confirmed: "Подтверждена", error: "Не удалось выполнить действие. Проверьте данные и повторите.", conflict: "Номер недоступен на эти даты или находится на ремонте.", stale: "Данные уже изменились. Обновите список и откройте бронь заново.", review: "Эта бронь требует проверки администратора: она отменена или гость уже заселён.", capacity: "Количество гостей превышает вместимость номера.", editing: "Изменение существующей брони", currency: "На этом этапе суммы вводятся только в сомах (KGS). Бронь не означает получение оплаты." },
  en: { title: "Sales channels", intro: "External bookings on your shared room grid", boundary: "Manual entry is available. Automatic connections are not configured. Changes here are not sent to external platforms.", disconnected: "Automatic sync not connected", add: "Enter an external booking", edit: "Edit", cancel: "Cancel in MARINA", confirm: "Cancel this booking in MARINA and release its dates? The external platform will not be updated. Payments are not refunded automatically.", source: "Platform", external: "External booking number", guest: "Guest name", phone: "Phone, if provided", room: "Hotel room", choose: "Choose a room", arrival: "Check-in", departure: "Check-out", adults: "Adults", children: "Children", total: "Accommodation total, KGS", save: "Save in MARINA", reset: "New booking", refresh: "Refresh", history: "External bookings", empty: "No external bookings yet", loading: "Loading…", saved: "Saved. Check the room grid. No payment was recorded automatically.", cancelled: "Cancelled", confirmed: "Confirmed", error: "Could not complete the action. Check the details and retry.", conflict: "The room is unavailable for these dates or under maintenance.", stale: "The booking has changed. Refresh and reopen it.", review: "Administrator review is required: the booking is cancelled or the guest has checked in.", capacity: "The guest count exceeds room capacity.", editing: "Editing an existing booking", currency: "This version accepts KGS totals only. A booking is not proof of payment." },
  kg: { title: "Сатуу каналдары", intro: "Платформалардан келген брондор жалпы шахматкада", boundary: "Азыр кол менен киргизүү жеткиликтүү. Автоматтык байланыштар орнотулган эмес. Бул жердеги өзгөртүүлөр платформаларга жөнөтүлбөйт.", disconnected: "Автоматтык синхрондоштуруу туташкан эмес", add: "Платформадан брон киргизүү", edit: "Өзгөртүү", cancel: "MARINA ичинде жокко чыгаруу", confirm: "MARINA ичинде бронду жокко чыгарып, даталарды бошотосузбу? Платформадагы брон өзгөрбөйт. Төлөмдөр автоматтык түрдө кайтарылбайт.", source: "Платформа", external: "Платформадагы брондун номери", guest: "Коноктун аты", phone: "Телефон, берилген болсо", room: "Мейманкана бөлмөсү", choose: "Бөлмөнү тандаңыз", arrival: "Кирүү", departure: "Чыгуу", adults: "Чоңдор", children: "Балдар", total: "Жашоонун баасы, сом", save: "MARINA ичинде сактоо", reset: "Жаңы брон", refresh: "Жаңыртуу", history: "Тышкы брондор", empty: "Тышкы брондор азырынча жок", loading: "Жүктөлүүдө…", saved: "Сакталды. Шахматкадан текшериңиз. Төлөм автоматтык түрдө катталган жок.", cancelled: "Жокко чыгарылды", confirmed: "Ырасталды", error: "Аракет аткарылган жок. Маалыматты текшерип, кайра аракет кылыңыз.", conflict: "Бул даталарда бөлмө бош эмес же оңдоодо.", stale: "Маалымат өзгөрдү. Тизмени жаңыртып, бронду кайра ачыңыз.", review: "Администратордун текшерүүсү керек: брон жокко чыгарылган же конок кирген.", capacity: "Коноктордун саны бөлмөнүн сыйымдуулугунан ашат.", editing: "Учурдагы бронду өзгөртүү", currency: "Бул этапта сумма сом менен гана киргизилет (KGS). Брон төлөм алынганын билдирбейт." },
  kz: { title: "Сату арналары", intro: "Платформалардан келген броньдар ортақ шахматкада", boundary: "Қазір қолмен енгізу қолжетімді. Автоматты қосылымдар бапталмаған. Мұндағы өзгерістер платформаларға жіберілмейді.", disconnected: "Автоматты синхрондау қосылмаған", add: "Платформадан бронь енгізу", edit: "Өзгерту", cancel: "MARINA ішінде бас тарту", confirm: "MARINA ішінде броньды тоқтатып, күндерді босатасыз ба? Платформадағы бронь өзгермейді. Төлемдер автоматты түрде қайтарылмайды.", source: "Платформа", external: "Платформадағы бронь нөмірі", guest: "Қонақтың аты", phone: "Телефон, берілген болса", room: "Қонақүй бөлмесі", choose: "Бөлмені таңдаңыз", arrival: "Кіру", departure: "Шығу", adults: "Ересектер", children: "Балалар", total: "Тұру құны, сом", save: "MARINA ішінде сақтау", reset: "Жаңа бронь", refresh: "Жаңарту", history: "Сыртқы броньдар", empty: "Сыртқы броньдар әзірше жоқ", loading: "Жүктелуде…", saved: "Сақталды. Шахматкадан тексеріңіз. Төлем автоматты түрде тіркелген жоқ.", cancelled: "Тоқтатылды", confirmed: "Расталды", error: "Әрекет орындалмады. Деректерді тексеріп, қайталаңыз.", conflict: "Бұл күндері бөлме бос емес немесе жөндеуде.", stale: "Деректер өзгерді. Тізімді жаңартып, броньды қайта ашыңыз.", review: "Әкімші тексеруі қажет: бронь тоқтатылған немесе қонақ кірген.", capacity: "Қонақтар саны бөлме сыйымдылығынан асады.", editing: "Бар броньды өзгерту", currency: "Бұл кезеңде сомалар тек соммен енгізіледі (KGS). Бронь төлем алынғанын білдірмейді." },
};
const initial = { provider: "BOOKING_COM" as Provider, external_id: "", revision: 1, guest_name: "", phone: "", room_id: "", check_in: "", check_out: "", adults: "1", children: "0", total_kgs: "" };

export default function ChannelManagerBoard() {
  const [locale, setLocale] = useState<Locale>("ru");
  const [data, setData] = useState<Overview | null>(null);
  const [form, setForm] = useState(initial);
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [errorKey, setErrorKey] = useState<"error" | "conflict" | "stale" | "review" | "capacity" | null>(null);
  const [saved, setSaved] = useState(false);
  const t = copy[locale];

  useEffect(() => {
    const update = () => {
      const value = document.documentElement.lang;
      setLocale(value === "ky" ? "kg" : value === "kk" ? "kz" : value === "en" ? "en" : "ru");
    };
    update();
    const observer = new MutationObserver(update);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["lang"] });
    return () => observer.disconnect();
  }, []);

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    try {
      const response = await fetch("/core/api/v1/admin/channels", { cache: "no-store", signal });
      if (!response.ok) throw new Error("load");
      setData(await response.json() as Overview);
    } catch (error) {
      if (!signal?.aborted) setErrorKey("error");
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  async function send(body: Record<string, unknown>) {
    setBusy(true); setErrorKey(null); setSaved(false);
    try {
      const response = await fetch("/core/api/v1/admin/channels/reservations/import", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      const result = await response.json();
      if (!response.ok) {
        const code = result.detail?.code;
        setErrorKey(["CHANNEL_ROOM_CONFLICT", "CHANNEL_ROOM_TECH_BLOCK"].includes(code) ? "conflict" : ["CHANNEL_STALE_REVISION", "CHANNEL_REVISION_PAYLOAD_MISMATCH"].includes(code) ? "stale" : ["CHANNEL_ACTIVE_STAY_REQUIRES_REVIEW", "CHANNEL_CANCELLED_REQUIRES_REVIEW"].includes(code) ? "review" : code === "CHANNEL_ROOM_CAPACITY" ? "capacity" : "error");
        return;
      }
      setSaved(true); setForm(initial); setEditing(false);
      await load();
    } catch { setErrorKey("error"); }
    finally { setBusy(false); }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void send({ ...form, phone: form.phone.trim() || null, adults: Number(form.adults), children: Number(form.children), total_kgs: Number(form.total_kgs), status: "CONFIRMED", currency: "KGS" });
  }

  function edit(item: Item) {
    setForm({ provider: item.provider, external_id: item.external_id, revision: item.revision + 1, guest_name: item.guest_name || "", phone: item.phone || "", room_id: item.room_id || "", check_in: item.check_in || "", check_out: item.check_out || "", adults: String(item.adults), children: String(item.children), total_kgs: String(item.total_kgs ?? "") });
    setEditing(true); setSaved(false); setErrorKey(null);
  }

  return <section className={styles.shell} data-i18n-skip>
    <header className={styles.header}><div><h1>{t.title}</h1><p>{t.intro}</p></div><button type="button" disabled={busy || loading} onClick={() => { setErrorKey(null); void load(); }}>{t.refresh}</button></header>
    <p className={styles.boundary}>{t.boundary}</p>
    <div className={styles.providers}>{Object.entries(names).map(([code, name]) => <article key={code}><strong>{name}</strong><span>{t.disconnected}</span></article>)}</div>
    {errorKey && <p role="alert" className={styles.error}>{t[errorKey]}</p>}
    {saved && <p role="status" className={styles.success}>{t.saved}</p>}
    <form onSubmit={submit} className={styles.form}>
      <h2>{editing ? t.editing : t.add}</h2><p>{t.currency}</p>
      <fieldset disabled={busy || !data}>
        <label>{t.source}<select value={form.provider} disabled={editing} onChange={(e) => setForm({ ...form, provider: e.target.value as Provider })}>{Object.entries(names).map(([code, name]) => <option key={code} value={code}>{name}</option>)}</select></label>
        <label>{t.external}<input required maxLength={180} value={form.external_id} readOnly={editing} onChange={(e) => setForm({ ...form, external_id: e.target.value })} /></label>
        <label>{t.guest}<input required minLength={2} maxLength={160} value={form.guest_name} onChange={(e) => setForm({ ...form, guest_name: e.target.value })} /></label>
        <label>{t.phone}<input type="tel" maxLength={40} value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></label>
        <label>{t.room}<select required value={form.room_id} onChange={(e) => setForm({ ...form, room_id: e.target.value })}><option value="">{t.choose}</option>{data?.rooms.map((room) => <option key={room.id} value={room.id}>{room.code}</option>)}</select></label>
        <label>{t.arrival}<input type="date" required value={form.check_in} onChange={(e) => setForm({ ...form, check_in: e.target.value })} /></label>
        <label>{t.departure}<input type="date" required min={form.check_in || undefined} value={form.check_out} onChange={(e) => setForm({ ...form, check_out: e.target.value })} /></label>
        <label>{t.adults}<input type="number" required min={1} max={20} value={form.adults} onChange={(e) => setForm({ ...form, adults: e.target.value })} /></label>
        <label>{t.children}<input type="number" required min={0} max={20} value={form.children} onChange={(e) => setForm({ ...form, children: e.target.value })} /></label>
        <label>{t.total}<input type="number" required min={0} max={2147483647} step={1} value={form.total_kgs} onChange={(e) => setForm({ ...form, total_kgs: e.target.value })} /></label>
      </fieldset>
      <div className={styles.actions}><button type="submit" disabled={busy || !data}>{busy ? t.loading : t.save}</button>{editing && <button type="button" disabled={busy} onClick={() => { setEditing(false); setForm(initial); }}>{t.reset}</button>}</div>
    </form>
    <ChannelCsvImport locale={locale} rooms={data?.rooms ?? []} onImported={() => void load()} />
    <h2>{t.history}</h2>
    {loading && <p role="status">{t.loading}</p>}
    {!loading && data?.items.length === 0 && <p>{t.empty}</p>}
    <div className={styles.list}>{data?.items.map((item) => <article key={`${item.provider}:${item.external_id}`}>
      <div><strong>{names[item.provider]} · {item.external_id}</strong><p>{item.guest_name || "—"} · {item.check_in || "—"} → {item.check_out || "—"}</p><span>{item.status === "CANCELLED" ? t.cancelled : t.confirmed}{item.total_kgs !== null ? ` · ${item.total_kgs.toLocaleString()} KGS` : ""}</span></div>
      {item.status !== "CANCELLED" && <div className={styles.actions}><button type="button" disabled={busy} onClick={() => edit(item)}>{t.edit}</button><button type="button" disabled={busy} onClick={() => { if (window.confirm(t.confirm)) void send({ provider: item.provider, external_id: item.external_id, revision: item.revision + 1, status: "CANCELLED" }); }}>{t.cancel}</button></div>}
    </article>)}</div>
  </section>;
}
