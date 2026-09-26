"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

type PropertyInfo = {
  id: string;
  code: string;
  name: string;
  timezone: string;
  currency: string;
};

type RoomType = {
  id: string;
  code: string;
  name: string;
  capacity_adults: number;
  capacity_children: number | null;
  area_label: string | null;
  room_count: number;
  rate_count: number;
};

type Room = {
  id: string;
  room_type_id: string;
  room_type_code: string;
  room_type_name: string;
  code: string;
  name: string;
  building_or_zone: string | null;
  floor_label: string | null;
  bed_configuration: string | null;
  area_label: string | null;
  operational_state: string;
  notes: string | null;
};

type Overview = {
  property: PropertyInfo;
  product_settings: {
    check_in_time: string;
    check_out_time: string;
    enabled_modules: string[];
    available_modules: string[];
    hotel_logo_url: string | null;
  };
  summary: { room_types: number; rooms: number; ready: number; blocked: number };
  onboarding: { ready: boolean; completed: number; total: number; rate_periods: number; active_staff: number; steps: { property: boolean; room_types: boolean; rooms: boolean; rates: boolean; staff: boolean } };
  room_types: RoomType[];
  rooms: Room[];
  rules: { demo_layout_enabled?: boolean; delete_room_only_without_history?: boolean; delete_room_type_only_when_unused?: boolean; tech_block_means_temporarily_not_sellable?: boolean; bulk_create_limit?: number };
};

type RoomDraft = {
  room_type_id: string;
  code: string;
  name: string;
  building_or_zone: string;
  floor_label: string;
  bed_configuration: string;
  area_label: string;
  operational_state: string;
  notes: string;
};

const emptyRoom: RoomDraft = {
  room_type_id: "",
  code: "",
  name: "",
  building_or_zone: "",
  floor_label: "",
  bed_configuration: "",
  area_label: "",
  operational_state: "CLEAN",
  notes: "",
};

const ROOM_STATE_LABELS: Record<string, string> = {
  CLEAN: "Готов",
  DIRTY: "Нужна уборка",
  IN_INSPECTION: "Проверка",
  TECH_BLOCK: "Ремонт / закрыт",
  UNKNOWN: "Не задан",
};

async function api(path: string, init?: RequestInit) {
  const response = await fetch(path, {
    cache: "no-store",
    ...init,
    headers: { "content-type": "application/json", ...(init?.headers || {}) },
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = body?.detail;
    if (typeof detail === "string") throw new Error(detail);
    if (detail?.code === "ROOM_HAS_HISTORY") throw new Error("Номер нельзя удалить: у него уже есть история, QR, задачи или движения.");
    if (detail?.code === "ROOM_TYPE_IN_USE") throw new Error("Категория используется номерами, тарифами или заявками.");
    if (detail?.code === "DEMO_RESET_BLOCKED_BY_ACTIVITY") throw new Error("Компактный демо-фонд нельзя создать: в базе уже есть брони, проживания, заявки, платежи или заказы.");
    if (detail?.code === "ROOM_CODES_ALREADY_EXIST") throw new Error(`Номера уже существуют: ${(detail.rooms || []).join(", ")}`);
    throw new Error(detail?.code || "Ошибка MARINA SMART");
  }
  return body;
}

const MODULE_LABELS: Record<string, { title: string; copy: string }> = {
  GROUPS: { title: "Групповые брони", copy: "Заезды групп, распределение по номерам." },
  AGENTS: { title: "Агенты / туроператоры", copy: "Отдельный агентский контур и CRM." },
  MARKETING: { title: "Маркетинг", copy: "Кампании и согласия гостей." },
  DINING: { title: "Питание / ресторан", copy: "Меню, зал, кухня и заказы." },
  OFFERS: { title: "Офферы гостю", copy: "Дополнительные предложения во время проживания." },
  GROWTH: { title: "Отзывы / рост", copy: "Контроль отзывов и возвратных гостей." },
  CONTENT: { title: "Сайт / контент", copy: "Управление контентом публичного сайта." },
  ROOM_QR: { title: "QR номеров", copy: "Постоянный QR и гостевой кабинет." },
  POINT_QR: { title: "QR зон", copy: "QR-коды общественных зон и сервисных точек." },
  INBOX: { title: "Сообщения", copy: "Единый inbox клиентских коммуникаций." },
};

const MODULE_PRESETS = [
  { key: "MINI", title: "Мини-отель", copy: "Простой PMS + гостевой QR.", modules: ["ROOM_QR"] },
  { key: "HOTEL", title: "Отель", copy: "Питание, QR и работа с агентами.", modules: ["DINING", "ROOM_QR", "AGENTS"] },
  { key: "RESORT", title: "Курорт", copy: "Группы, агенты, питание, офферы, QR зон, отзывы и сообщения.", modules: ["GROUPS", "AGENTS", "DINING", "OFFERS", "GROWTH", "ROOM_QR", "POINT_QR", "INBOX"] },
] as const;

export default function HotelSetupBoard({ onModulesChanged, onNavigate, onIdentityChanged }: { onModulesChanged?: (modules: string[]) => void; onNavigate?: (destination: "RATES" | "STAFF") => void; onIdentityChanged?: (identity: { name: string; logo_url: string | null }) => void }) {
  const [data, setData] = useState<Overview | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [propertyName, setPropertyName] = useState("");
  const [timezone, setTimezone] = useState("Asia/Bishkek");
  const [currency, setCurrency] = useState("KGS");
  const [checkInTime, setCheckInTime] = useState("14:00");
  const [checkOutTime, setCheckOutTime] = useState("12:00");
  const [hotelLogoUrl, setHotelLogoUrl] = useState("");
  const [enabledModules, setEnabledModules] = useState<string[]>([]);

  const [typeCode, setTypeCode] = useState("");
  const [typeName, setTypeName] = useState("");
  const [typeAdults, setTypeAdults] = useState(2);
  const [typeChildren, setTypeChildren] = useState(0);
  const [typeArea, setTypeArea] = useState("");
  const [editingType, setEditingType] = useState<RoomType | null>(null);

  const [roomDraft, setRoomDraft] = useState<RoomDraft>(emptyRoom);
  const [editingRoom, setEditingRoom] = useState<Room | null>(null);
  const [editRoomDraft, setEditRoomDraft] = useState<RoomDraft>(emptyRoom);

  const [bulkType, setBulkType] = useState("");
  const [bulkStart, setBulkStart] = useState(101);
  const [bulkEnd, setBulkEnd] = useState(110);
  const [bulkWidth, setBulkWidth] = useState(3);
  const [bulkPrefix, setBulkPrefix] = useState("");
  const [bulkBuilding, setBulkBuilding] = useState("");
  const [bulkFloor, setBulkFloor] = useState("");

  const [search, setSearch] = useState("");
  const [filterType, setFilterType] = useState("ALL");

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const body = (await api("/core/api/v1/admin/hotel-setup")) as Overview;
      setData(body);
      setPropertyName(body.property.name);
      setTimezone(body.property.timezone);
      setCurrency(body.property.currency);
      setCheckInTime(body.product_settings.check_in_time);
      setCheckOutTime(body.product_settings.check_out_time);
      setHotelLogoUrl(body.product_settings.hotel_logo_url || "");
      setEnabledModules(body.product_settings.enabled_modules);
      if (!roomDraft.room_type_id && body.room_types[0]) {
        setRoomDraft((current) => ({ ...current, room_type_id: body.room_types[0].id }));
      }
      if (!bulkType && body.room_types[0]) setBulkType(body.room_types[0].id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось загрузить настройки отеля");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);

  const filteredRooms = useMemo(() => {
    const q = search.trim().toLowerCase();
    return (data?.rooms || []).filter((room) => {
      if (filterType !== "ALL" && room.room_type_id !== filterType) return false;
      if (!q) return true;
      return [room.code, room.name, room.room_type_name, room.building_or_zone, room.floor_label]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(q));
    });
  }, [data?.rooms, search, filterType]);

  function done(message: string) {
    setNotice(message);
    setError(null);
    window.setTimeout(() => setNotice(null), 3500);
  }

  async function saveProperty(event: FormEvent) {
    event.preventDefault();
    setBusy("property");
    try {
      const saved = await api("/core/api/v1/admin/hotel-setup/property", {
        method: "PATCH",
        body: JSON.stringify({ name: propertyName, timezone, currency, check_in_time: checkInTime, check_out_time: checkOutTime, hotel_logo_url: hotelLogoUrl || null }),
      });
      onIdentityChanged?.({ name: saved.name, logo_url: saved.hotel_logo_url || null });
      await load();
      done("Данные объекта сохранены.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Ошибка сохранения объекта");
    } finally { setBusy(null); }
  }

  async function saveModules(next: string[]) {
    setBusy("modules");
    try {
      const result = await api("/core/api/v1/admin/hotel-setup/modules", {
        method: "PATCH",
        body: JSON.stringify({ enabled_modules: next }),
      });
      setEnabledModules(result.enabled_modules || []);
      onModulesChanged?.(result.enabled_modules || []);
      done("Набор модулей сохранён.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось сохранить модули");
    } finally { setBusy(null); }
  }

  function toggleModule(module: string) {
    const next = enabledModules.includes(module)
      ? enabledModules.filter((item) => item !== module)
      : [...enabledModules, module];
    void saveModules(next);
  }

  async function createType(event: FormEvent) {
    event.preventDefault();
    setBusy("type-create");
    try {
      await api("/core/api/v1/admin/hotel-setup/room-types", {
        method: "POST",
        body: JSON.stringify({
          code: typeCode,
          name: typeName,
          capacity_adults: typeAdults,
          capacity_children: typeChildren,
          area_label: typeArea || null,
        }),
      });
      setTypeCode(""); setTypeName(""); setTypeArea("");
      await load();
      done("Категория добавлена.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Ошибка категории");
    } finally { setBusy(null); }
  }

  async function saveType(event: FormEvent) {
    event.preventDefault();
    if (!editingType) return;
    setBusy("type-edit");
    try {
      await api(`/core/api/v1/admin/hotel-setup/room-types/${editingType.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          code: editingType.code,
          name: editingType.name,
          capacity_adults: editingType.capacity_adults,
          capacity_children: editingType.capacity_children ?? 0,
          area_label: editingType.area_label || null,
        }),
      });
      setEditingType(null);
      await load();
      done("Категория обновлена.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Ошибка категории");
    } finally { setBusy(null); }
  }

  async function removeType(item: RoomType) {
    if (!window.confirm(`Удалить категорию «${item.name}»? Это возможно только если она нигде не используется.`)) return;
    setBusy(`type-${item.id}`);
    try {
      await api(`/core/api/v1/admin/hotel-setup/room-types/${item.id}`, { method: "DELETE" });
      await load();
      done("Категория удалена.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Категорию удалить нельзя");
    } finally { setBusy(null); }
  }

  async function createRoom(event: FormEvent) {
    event.preventDefault();
    setBusy("room-create");
    try {
      await api("/core/api/v1/admin/hotel-setup/rooms", {
        method: "POST",
        body: JSON.stringify({
          ...roomDraft,
          name: roomDraft.name || null,
          building_or_zone: roomDraft.building_or_zone || null,
          floor_label: roomDraft.floor_label || null,
          bed_configuration: roomDraft.bed_configuration || null,
          area_label: roomDraft.area_label || null,
          notes: roomDraft.notes || null,
        }),
      });
      const keepType = roomDraft.room_type_id;
      setRoomDraft({ ...emptyRoom, room_type_id: keepType });
      await load();
      done("Номер добавлен и уже доступен шахматке.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Ошибка создания номера");
    } finally { setBusy(null); }
  }

  function openRoom(room: Room) {
    setEditingRoom(room);
    setEditRoomDraft({
      room_type_id: room.room_type_id,
      code: room.code,
      name: room.name || "",
      building_or_zone: room.building_or_zone || "",
      floor_label: room.floor_label || "",
      bed_configuration: room.bed_configuration || "",
      area_label: room.area_label || "",
      operational_state: room.operational_state,
      notes: room.notes || "",
    });
  }

  async function saveRoom(event: FormEvent) {
    event.preventDefault();
    if (!editingRoom) return;
    setBusy("room-edit");
    try {
      await api(`/core/api/v1/admin/hotel-setup/rooms/${editingRoom.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          ...editRoomDraft,
          building_or_zone: editRoomDraft.building_or_zone || null,
          floor_label: editRoomDraft.floor_label || null,
          bed_configuration: editRoomDraft.bed_configuration || null,
          area_label: editRoomDraft.area_label || null,
          notes: editRoomDraft.notes || null,
        }),
      });
      setEditingRoom(null);
      await load();
      done("Номер обновлён.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Ошибка изменения номера");
    } finally { setBusy(null); }
  }

  async function toggleRoom(room: Room) {
    const next = room.operational_state === "TECH_BLOCK" ? "CLEAN" : "TECH_BLOCK";
    setBusy(`room-state-${room.id}`);
    try {
      await api(`/core/api/v1/admin/hotel-setup/rooms/${room.id}`, {
        method: "PATCH",
        body: JSON.stringify({ operational_state: next }),
      });
      await load();
      done(next === "TECH_BLOCK" ? `Номер ${room.code} временно закрыт для продажи.` : `Номер ${room.code} снова доступен.`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Статус номера не изменён");
    } finally { setBusy(null); }
  }

  async function removeRoom(room: Room) {
    if (!window.confirm(`Удалить номер ${room.code}? Если у него есть история, система запретит удаление.`)) return;
    setBusy(`room-delete-${room.id}`);
    try {
      await api(`/core/api/v1/admin/hotel-setup/rooms/${room.id}`, { method: "DELETE" });
      await load();
      done(`Номер ${room.code} удалён.`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Номер удалить нельзя");
    } finally { setBusy(null); }
  }

  async function bulkCreate(event: FormEvent) {
    event.preventDefault();
    setBusy("bulk");
    try {
      const result = await api("/core/api/v1/admin/hotel-setup/rooms/bulk", {
        method: "POST",
        body: JSON.stringify({
          room_type_id: bulkType,
          start_number: bulkStart,
          end_number: bulkEnd,
          pad_width: bulkWidth,
          prefix: bulkPrefix,
          building_or_zone: bulkBuilding || null,
          floor_label: bulkFloor || null,
          operational_state: "CLEAN",
        }),
      });
      await load();
      done(`Создано номеров: ${result.created}.`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Массовое создание не выполнено");
    } finally { setBusy(null); }
  }

  async function compactDemo() {
    if (!window.confirm("Заменить текущий пустой номерной фонд на компактный тестовый: 12 номеров / 3 категории? Операция заблокируется, если уже есть рабочие брони или платежи.")) return;
    setBusy("demo");
    try {
      await api("/core/api/v1/admin/hotel-setup/compact-demo", {
        method: "POST",
        body: JSON.stringify({ confirmation: "CREATE_COMPACT_DEMO" }),
      });
      await load();
      done("Компактный демо-отель создан: 12 номеров / 3 категории.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Демо-фонд не создан");
    } finally { setBusy(null); }
  }

  if (loading && !data) return <main className="work-shell hotel-setup-shell"><div className="loading">Загрузка настроек MARINA SMART…</div></main>;
  if (!data) return <main className="work-shell hotel-setup-shell"><div className="error-box">{error || "Нет данных"}</div><button className="btn" onClick={() => void load()}>Повторить</button></main>;

  return (
    <main className="work-shell hotel-setup-shell">
      <header className="work-head hotel-setup-head">
        <div><p className="eyebrow">MARINA SMART · Конструктор Hotel OS</p><h1>Настройка отеля</h1><p>Объект, категории и физический номерной фонд — без программиста.</p></div>
        <div className="work-actions"><button className="btn secondary" onClick={() => void load()}>Обновить</button>{data.rules?.demo_layout_enabled && <button className="btn" disabled={busy === "demo"} onClick={() => void compactDemo()}>12 номеров для теста</button>}</div>
      </header>

      {error && <div className="error-box">{error}</div>}
      {notice && <div className="management-notice">{notice}</div>}

      <section className="hotel-setup-kpis">
        <article><strong>{data.summary.rooms}</strong><span>номеров</span></article>
        <article><strong>{data.summary.room_types}</strong><span>категорий</span></article>
        <article><strong>{data.summary.ready}</strong><span>готовы</span></article>
        <article><strong>{data.summary.blocked}</strong><span>временно закрыты</span></article>
      </section>

      <section className="hotel-setup-panel hotel-onboarding">
        <div className="hotel-setup-section-title">
          <div><small>Готовность запуска</small><h2>{data.onboarding.ready ? "Отель настроен" : "Завершите базовую настройку"}</h2></div>
          <span>{data.onboarding.completed}/{data.onboarding.total}</span>
        </div>
        <div className="hotel-onboarding-steps">
          {[
            ["property", "Объект"],
            ["room_types", "Категории"],
            ["rooms", "Номера"],
            ["rates", "Тарифы"],
            ["staff", "Персонал"],
          ].map(([key, label]) => {
            const complete = data.onboarding.steps[key as keyof typeof data.onboarding.steps];
            return <div className={complete ? "complete" : ""} key={key}><b>{complete ? "✓" : "○"}</b><span>{label}</span></div>;
          })}
        </div>
        {!data.onboarding.ready && <p className="hotel-onboarding-copy">MARINA SMART подсказывает только базовые обязательные шаги. Дополнительные модули можно включить позже.</p>}
        {(!data.onboarding.steps.rates || !data.onboarding.steps.staff) && <div className="hotel-onboarding-actions">
          {!data.onboarding.steps.rates && <button className="btn secondary" onClick={() => onNavigate?.("RATES")}>Настроить тарифы</button>}
          {!data.onboarding.steps.staff && <button className="btn secondary" onClick={() => onNavigate?.("STAFF")}>Настроить персонал</button>}
        </div>}
      </section>

      <section className="hotel-setup-panel">
        <div className="hotel-setup-section-title"><div><small>01 · Объект</small><h2>Основные данные</h2></div><span>{data.property.code}</span></div>
        <form className="hotel-setup-grid" onSubmit={saveProperty}>
          <label><span>Название отеля</span><input value={propertyName} onChange={(e) => setPropertyName(e.target.value)} required /></label>
          <label><span>Часовой пояс</span><input value={timezone} onChange={(e) => setTimezone(e.target.value)} placeholder="Asia/Bishkek" required /></label>
          <label><span>Валюта</span><input value={currency} onChange={(e) => setCurrency(e.target.value.toUpperCase())} maxLength={3} required /></label>
          <label><span>Check-in</span><input type="time" value={checkInTime} onChange={(e) => setCheckInTime(e.target.value)} required /></label>
          <label><span>Check-out</span><input type="time" value={checkOutTime} onChange={(e) => setCheckOutTime(e.target.value)} required /></label>
          <label className="hotel-logo-field"><span>Логотип отеля — URL</span><input type="url" value={hotelLogoUrl} onChange={(e) => setHotelLogoUrl(e.target.value)} placeholder="https://hotel.kg/logo.png" /></label>
          <div className="hotel-logo-preview">{hotelLogoUrl ? <img src={hotelLogoUrl} alt="Логотип отеля" /> : <span>Логотип отеля не задан</span>}</div>
          <div className="hotel-setup-submit"><button className="btn primary" disabled={busy === "property"}>Сохранить объект</button></div>
        </form>
      </section>

      <section className="hotel-setup-panel">
        <div className="hotel-setup-section-title"><div><small>02 · Категории</small><h2>Типы размещения</h2></div><span>{data.room_types.length} категорий</span></div>
        <form className="hotel-type-create" onSubmit={createType}>
          <input placeholder="Код: STANDARD" value={typeCode} onChange={(e) => setTypeCode(e.target.value)} required />
          <input placeholder="Название: Стандарт" value={typeName} onChange={(e) => setTypeName(e.target.value)} required />
          <label><span>Взрослых</span><input type="number" min="1" max="20" value={typeAdults} onChange={(e) => setTypeAdults(Number(e.target.value) || 1)} /></label>
          <label><span>Детей</span><input type="number" min="0" max="20" value={typeChildren} onChange={(e) => setTypeChildren(Number(e.target.value) || 0)} /></label>
          <input placeholder="Площадь, например 24 м²" value={typeArea} onChange={(e) => setTypeArea(e.target.value)} />
          <button className="btn primary" disabled={busy === "type-create"}>+ Категория</button>
        </form>
        <div className="hotel-type-list">
          {data.room_types.map((item) => <article key={item.id}>
            <div><strong>{item.name}</strong><small>{item.code} · {item.capacity_adults}+{item.capacity_children ?? 0} гостей · {item.area_label || "площадь не задана"}</small></div>
            <div className="hotel-type-stats"><span>{item.room_count} ном.</span><span>{item.rate_count} тариф.</span></div>
            <div className="hotel-row-actions"><button className="btn mini secondary" onClick={() => setEditingType({ ...item })}>Изменить</button><button className="btn mini danger-ghost" disabled={busy === `type-${item.id}`} onClick={() => void removeType(item)}>Удалить</button></div>
          </article>)}
        </div>
      </section>

      <section className="hotel-setup-panel">
        <div className="hotel-setup-section-title"><div><small>03 · Номерной фонд</small><h2>Добавить один номер</h2></div><span>сразу появится в шахматке</span></div>
        <form className="hotel-room-create" onSubmit={createRoom}>
          <label><span>Категория</span><select value={roomDraft.room_type_id} onChange={(e) => setRoomDraft({ ...roomDraft, room_type_id: e.target.value })} required><option value="">Выберите</option>{data.room_types.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label>
          <label><span>Номер</span><input value={roomDraft.code} onChange={(e) => setRoomDraft({ ...roomDraft, code: e.target.value })} placeholder="101" required /></label>
          <label><span>Название</span><input value={roomDraft.name} onChange={(e) => setRoomDraft({ ...roomDraft, name: e.target.value })} placeholder="Номер 101" /></label>
          <label><span>Корпус / зона</span><input value={roomDraft.building_or_zone} onChange={(e) => setRoomDraft({ ...roomDraft, building_or_zone: e.target.value })} /></label>
          <label><span>Этаж</span><input value={roomDraft.floor_label} onChange={(e) => setRoomDraft({ ...roomDraft, floor_label: e.target.value })} /></label>
          <label><span>Кровати</span><input value={roomDraft.bed_configuration} onChange={(e) => setRoomDraft({ ...roomDraft, bed_configuration: e.target.value })} placeholder="1 двуспальная + диван" /></label>
          <label><span>Площадь</span><input value={roomDraft.area_label} onChange={(e) => setRoomDraft({ ...roomDraft, area_label: e.target.value })} /></label>
          <button className="btn primary" disabled={busy === "room-create"}>+ Добавить номер</button>
        </form>
      </section>

      <section className="hotel-setup-panel">
        <div className="hotel-setup-section-title"><div><small>04 · Быстрое заполнение</small><h2>Создать диапазон номеров</h2></div><span>до 200 за раз</span></div>
        <form className="hotel-bulk-create" onSubmit={bulkCreate}>
          <label><span>Категория</span><select value={bulkType} onChange={(e) => setBulkType(e.target.value)} required><option value="">Выберите</option>{data.room_types.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label>
          <label><span>От</span><input type="number" value={bulkStart} onChange={(e) => setBulkStart(Number(e.target.value))} /></label>
          <label><span>До</span><input type="number" value={bulkEnd} onChange={(e) => setBulkEnd(Number(e.target.value))} /></label>
          <label><span>Знаков</span><input type="number" min="1" max="6" value={bulkWidth} onChange={(e) => setBulkWidth(Number(e.target.value))} /></label>
          <label><span>Префикс</span><input value={bulkPrefix} onChange={(e) => setBulkPrefix(e.target.value)} placeholder="A-" /></label>
          <label><span>Корпус</span><input value={bulkBuilding} onChange={(e) => setBulkBuilding(e.target.value)} /></label>
          <label><span>Этаж</span><input value={bulkFloor} onChange={(e) => setBulkFloor(e.target.value)} /></label>
          <button className="btn primary" disabled={busy === "bulk"}>Создать диапазон</button>
        </form>
      </section>

      <section className="hotel-setup-panel">
        <div className="hotel-setup-section-title"><div><small>05 · Управление</small><h2>Все номера</h2></div><span>{filteredRooms.length} показано</span></div>
        <div className="hotel-room-filters">
          <input placeholder="Поиск номера, корпуса, категории…" value={search} onChange={(e) => setSearch(e.target.value)} />
          <select value={filterType} onChange={(e) => setFilterType(e.target.value)}><option value="ALL">Все категории</option>{data.room_types.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select>
        </div>
        <div className="hotel-room-table">
          <div className="hotel-room-row header"><span>Номер</span><span>Категория</span><span>Корпус / этаж</span><span>Кровати</span><span>Статус</span><span>Действия</span></div>
          {filteredRooms.map((room) => <div className="hotel-room-row" key={room.id}>
            <span><strong>{room.code}</strong><small>{room.name}</small></span>
            <span>{room.room_type_name}</span>
            <span>{[room.building_or_zone, room.floor_label].filter(Boolean).join(" · ") || "—"}</span>
            <span>{room.bed_configuration || "—"}</span>
            <span><b className={`hotel-state state-${room.operational_state.toLowerCase()}`}>{ROOM_STATE_LABELS[room.operational_state] || room.operational_state}</b></span>
            <span className="hotel-row-actions"><button className="btn mini secondary" onClick={() => openRoom(room)}>Изменить</button><button className="btn mini secondary" disabled={busy === `room-state-${room.id}`} onClick={() => void toggleRoom(room)}>{room.operational_state === "TECH_BLOCK" ? "Открыть" : "Закрыть"}</button><button className="btn mini danger-ghost" disabled={busy === `room-delete-${room.id}`} onClick={() => void removeRoom(room)}>Удалить</button></span>
          </div>)}
        </div>
      </section>

      <section className="hotel-setup-panel">
        <div className="hotel-setup-section-title"><div><small>06 · Модули</small><h2>Что показывать в системе</h2></div><span>ядро всегда включено</span></div>
        <p className="management-truth compact">Главная, шахматка, брони, CRM, финансы, сервис, операции, отчёты и настройки остаются всегда. Дополнительные модули можно скрывать без удаления данных и кода.</p>
        <div className="hotel-module-presets">
          {MODULE_PRESETS.map((preset) => {
            const active = preset.modules.length === enabledModules.length && preset.modules.every((module) => enabledModules.includes(module));
            return <button type="button" key={preset.key} className={active ? "active" : ""} disabled={busy === "modules"} onClick={() => void saveModules([...preset.modules])}><strong>{preset.title}</strong><small>{preset.copy}</small></button>;
          })}
        </div>
        <div className="hotel-module-grid">
          {data.product_settings.available_modules.map((module) => {
            const meta = MODULE_LABELS[module] || { title: module, copy: "" };
            const active = enabledModules.includes(module);
            return <button type="button" key={module} className={`hotel-module-card ${active ? "active" : ""}`} disabled={busy === "modules"} onClick={() => toggleModule(module)}>
              <span className="hotel-module-check">{active ? "✓" : "○"}</span>
              <strong>{meta.title}</strong>
              <small>{meta.copy}</small>
            </button>;
          })}
        </div>
      </section>

      {editingType && <div className="management-modal-backdrop" onMouseDown={() => setEditingType(null)}><form className="management-modal" onSubmit={saveType} onMouseDown={(e) => e.stopPropagation()}>
        <div className="management-modal-head"><div><p className="eyebrow">Категория номера</p><h2>{editingType.name}</h2></div><button type="button" className="btn mini secondary" onClick={() => setEditingType(null)}>Закрыть</button></div>
        <div className="management-form-grid">
          <label><span>Код</span><input value={editingType.code} onChange={(e) => setEditingType({ ...editingType, code: e.target.value })} /></label>
          <label><span>Название</span><input value={editingType.name} onChange={(e) => setEditingType({ ...editingType, name: e.target.value })} /></label>
          <label><span>Взрослых</span><input type="number" min="1" value={editingType.capacity_adults} onChange={(e) => setEditingType({ ...editingType, capacity_adults: Number(e.target.value) })} /></label>
          <label><span>Детей</span><input type="number" min="0" value={editingType.capacity_children ?? 0} onChange={(e) => setEditingType({ ...editingType, capacity_children: Number(e.target.value) })} /></label>
          <label className="management-form-wide"><span>Площадь</span><input value={editingType.area_label || ""} onChange={(e) => setEditingType({ ...editingType, area_label: e.target.value })} /></label>
        </div>
        <div className="management-modal-actions"><button type="button" className="btn secondary" onClick={() => setEditingType(null)}>Отмена</button><button className="btn primary" disabled={busy === "type-edit"}>Сохранить</button></div>
      </form></div>}

      {editingRoom && <div className="management-modal-backdrop" onMouseDown={() => setEditingRoom(null)}><form className="management-modal" onSubmit={saveRoom} onMouseDown={(e) => e.stopPropagation()}>
        <div className="management-modal-head"><div><p className="eyebrow">Физический номер</p><h2>Номер {editingRoom.code}</h2></div><button type="button" className="btn mini secondary" onClick={() => setEditingRoom(null)}>Закрыть</button></div>
        <div className="management-form-grid">
          <label><span>Категория</span><select value={editRoomDraft.room_type_id} onChange={(e) => setEditRoomDraft({ ...editRoomDraft, room_type_id: e.target.value })}>{data.room_types.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label>
          <label><span>Код / номер</span><input value={editRoomDraft.code} onChange={(e) => setEditRoomDraft({ ...editRoomDraft, code: e.target.value })} /></label>
          <label><span>Название</span><input value={editRoomDraft.name} onChange={(e) => setEditRoomDraft({ ...editRoomDraft, name: e.target.value })} /></label>
          <label><span>Статус</span><select value={editRoomDraft.operational_state} onChange={(e) => setEditRoomDraft({ ...editRoomDraft, operational_state: e.target.value })}><option value="CLEAN">Готов</option><option value="DIRTY">Нужна уборка</option><option value="IN_INSPECTION">Проверка</option><option value="TECH_BLOCK">Ремонт / закрыт</option><option value="UNKNOWN">Не задан</option></select></label>
          <label><span>Корпус / зона</span><input value={editRoomDraft.building_or_zone} onChange={(e) => setEditRoomDraft({ ...editRoomDraft, building_or_zone: e.target.value })} /></label>
          <label><span>Этаж</span><input value={editRoomDraft.floor_label} onChange={(e) => setEditRoomDraft({ ...editRoomDraft, floor_label: e.target.value })} /></label>
          <label><span>Кровати</span><input value={editRoomDraft.bed_configuration} onChange={(e) => setEditRoomDraft({ ...editRoomDraft, bed_configuration: e.target.value })} /></label>
          <label><span>Площадь</span><input value={editRoomDraft.area_label} onChange={(e) => setEditRoomDraft({ ...editRoomDraft, area_label: e.target.value })} /></label>
          <label className="management-form-wide"><span>Комментарий</span><textarea rows={3} value={editRoomDraft.notes} onChange={(e) => setEditRoomDraft({ ...editRoomDraft, notes: e.target.value })} /></label>
        </div>
        <div className="management-modal-actions"><button type="button" className="btn secondary" onClick={() => setEditingRoom(null)}>Отмена</button><button className="btn primary" disabled={busy === "room-edit"}>Сохранить номер</button></div>
      </form></div>}
    </main>
  );
}
