"use client";

import { FormEvent, useEffect, useState } from "react";

type Settings = {
  breakfast_start: string | null;
  lunch_start: string | null;
  dinner_start: string | null;
  meal_order_cutoff_minutes: number;
  room_delivery_enabled: boolean;
  room_delivery_fee_kgs: number;
  scheduled_housekeeping_interval_days: number;
  scheduled_linen_change_included: boolean;
  on_demand_housekeeping_price_kgs: number | null;
  on_demand_linen_price_kgs: number | null;
  meal_times_configured: boolean;
  housekeeping_prices_configured: boolean;
  updated_at?: string | null;
};

function numberOrNull(value: string): number | null {
  if (!value.trim()) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? Math.max(0, Math.round(parsed)) : null;
}

export default function GuestServiceSettingsBoard() {
  const [data, setData] = useState<Settings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function load() {
    setLoading(true); setError(null);
    try {
      const response = await fetch("/core/api/v1/admin/guest-service-settings", { cache: "no-store" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body?.detail || `HTTP ${response.status}`);
      setData(body as Settings);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось загрузить настройки услуг");
    } finally { setLoading(false); }
  }

  useEffect(() => { void load(); }, []);

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!data) return;
    setSaving(true); setError(null); setNotice(null);
    try {
      const response = await fetch("/core/api/v1/admin/guest-service-settings", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          breakfast_start: data.breakfast_start || null,
          lunch_start: data.lunch_start || null,
          dinner_start: data.dinner_start || null,
          meal_order_cutoff_minutes: data.meal_order_cutoff_minutes,
          room_delivery_enabled: data.room_delivery_enabled,
          room_delivery_fee_kgs: data.room_delivery_fee_kgs,
          scheduled_housekeeping_interval_days: data.scheduled_housekeeping_interval_days,
          scheduled_linen_change_included: data.scheduled_linen_change_included,
          on_demand_housekeeping_price_kgs: data.on_demand_housekeeping_price_kgs,
          on_demand_linen_price_kgs: data.on_demand_linen_price_kgs,
        }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof body?.detail === "string" ? body.detail : body?.detail?.code || `HTTP ${response.status}`);
      setData(body as Settings);
      setNotice("Настройки сохранены в Resort Core. Guest OS использует их сразу для новых заказов и заявок.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось сохранить настройки");
    } finally { setSaving(false); }
  }

  if (loading && !data) return <main className="service-settings"><div className="loading">Загрузка настроек…</div></main>;
  if (!data) return <main className="service-settings"><div className="error-box">{error || "Настройки недоступны"}</div></main>;

  return <main className="service-settings">
    <header className="service-settings-head">
      <div><p className="eyebrow">Resort Core · правила сервиса</p><h1>Настройки услуг гостя</h1><p>Единые операционные правила для Guest OS, кухни и housekeeping. Время и цены меняются здесь — без правки кода.</p></div>
      <button className="btn" type="button" onClick={() => void load()}>↻ Обновить</button>
    </header>

    {error && <div className="error-box">{error}</div>}
    {notice && <div className="content-message success">{notice}</div>}

    <form onSubmit={save}>
      <section className="service-settings-card">
        <div className="service-settings-title"><div><small>Питание</small><h2>Окна заказа</h2></div><span className={data.meal_times_configured ? "setting-ok" : "setting-warn"}>{data.meal_times_configured ? "Время настроено" : "Нужно задать время"}</span></div>
        <p>Заказ через клиентское меню закрывается за указанное число минут до начала завтрака, обеда или ужина. По правилу собственника сейчас — 60 минут.</p>
        <div className="service-settings-grid four">
          <label><span>Завтрак начинается</span><input type="time" value={data.breakfast_start || ""} onChange={(event) => setData({ ...data, breakfast_start: event.target.value || null })} /></label>
          <label><span>Обед начинается</span><input type="time" value={data.lunch_start || ""} onChange={(event) => setData({ ...data, lunch_start: event.target.value || null })} /></label>
          <label><span>Ужин начинается</span><input type="time" value={data.dinner_start || ""} onChange={(event) => setData({ ...data, dinner_start: event.target.value || null })} /></label>
          <label><span>Закрыть заказ за, мин.</span><input type="number" min="0" max="360" value={data.meal_order_cutoff_minutes} onChange={(event) => setData({ ...data, meal_order_cutoff_minutes: Math.max(0, Number(event.target.value) || 0) })} /></label>
        </div>
      </section>

      <section className="service-settings-card">
        <div className="service-settings-title"><div><small>Room service</small><h2>Доставка еды и напитков</h2></div><span className={data.room_delivery_enabled ? "setting-ok" : "setting-warn"}>{data.room_delivery_enabled ? "Включена" : "Выключена"}</span></div>
        <div className="service-settings-grid two">
          <label className="settings-check"><input type="checkbox" checked={data.room_delivery_enabled} onChange={(event) => setData({ ...data, room_delivery_enabled: event.target.checked })} /><span><strong>Доставка в номер доступна</strong><small>Guest OS покажет переключатель доставки.</small></span></label>
          <label><span>Стоимость доставки, сом</span><input type="number" min="0" value={data.room_delivery_fee_kgs} onChange={(event) => setData({ ...data, room_delivery_fee_kgs: Math.max(0, Number(event.target.value) || 0) })} /></label>
        </div>
        <div className="settings-rule">Текущее утверждённое значение: <strong>200 сом за заказ</strong>. Сумма хранится отдельно от стоимости еды.</div>
      </section>

      <section className="service-settings-card">
        <div className="service-settings-title"><div><small>Housekeeping</small><h2>Уборка и постельное бельё</h2></div><span className={data.housekeeping_prices_configured ? "setting-ok" : "setting-warn"}>{data.housekeeping_prices_configured ? "Платные цены настроены" : "Нужно задать платные цены"}</span></div>
        <div className="service-settings-grid two">
          <label><span>Плановая уборка каждые, дней</span><input type="number" min="1" max="30" value={data.scheduled_housekeeping_interval_days} onChange={(event) => setData({ ...data, scheduled_housekeeping_interval_days: Math.max(1, Number(event.target.value) || 1) })} /></label>
          <label className="settings-check"><input type="checkbox" checked={data.scheduled_linen_change_included} onChange={(event) => setData({ ...data, scheduled_linen_change_included: event.target.checked })} /><span><strong>Смена белья входит в плановую уборку</strong><small>По правилу собственника — каждые 3 дня вместе с уборкой.</small></span></label>
          <label><span>Дополнительная уборка, сом</span><input type="number" min="0" placeholder="Цена не задана" value={data.on_demand_housekeeping_price_kgs ?? ""} onChange={(event) => setData({ ...data, on_demand_housekeeping_price_kgs: numberOrNull(event.target.value) })} /><small>Если пусто, Guest OS не должен выдавать услугу как бесплатную.</small></label>
          <label><span>Дополнительная смена белья, сом</span><input type="number" min="0" placeholder="Цена не задана" value={data.on_demand_linen_price_kgs ?? ""} onChange={(event) => setData({ ...data, on_demand_linen_price_kgs: numberOrNull(event.target.value) })} /><small>Цена не выдумывается системой.</small></label>
        </div>
      </section>

      <footer className="service-settings-save"><div><strong>Все изменения журналируются</strong><span>{data.updated_at ? `Последнее изменение: ${new Date(data.updated_at).toLocaleString("ru-RU")}` : ""}</span></div><button className="btn primary" disabled={saving}>{saving ? "Сохраняю…" : "Сохранить настройки"}</button></footer>
    </form>
  </main>;
}
