"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import styles from "./GroupBookingBoard.module.css";

type Room = {
  room_id: string; code: string; name: string; room_type_code: string; room_type_name: string;
  building_or_zone?: string | null; floor?: string | null; beds_raw?: string | null;
  capacity_adults: number; capacity_children: number; operational_state: string;
  available: boolean; reason?: string | null;
  pricing?: { sellable: boolean; total_kgs?: number | null; reason?: string | null } | null;
};
type Group = { id: string; code: string; name: string; contact_name: string; contact_phone: string; check_in: string; check_out: string; status: string; room_count: number; total_kgs: number; paid_kgs: number };

const money = (value: number) => `${new Intl.NumberFormat("ru-RU").format(value)} сом`;

function dateOffset(days: number) {
  const value = new Date();
  value.setDate(value.getDate() + days);
  const shifted = new Date(value.getTime() - value.getTimezoneOffset() * 60000);
  return shifted.toISOString().slice(0, 10);
}

async function api(path: string, init?: RequestInit) {
  const response = await fetch(path, { cache: "no-store", ...init });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(typeof body?.detail === "string" ? body.detail : body?.detail?.message || body?.detail?.code || "Ошибка Resort Core");
  return body;
}

export default function GroupBookingBoard() {
  const [checkIn, setCheckIn] = useState(dateOffset(1));
  const [checkOut, setCheckOut] = useState(dateOffset(4));
  const [adults, setAdults] = useState(2);
  const [children, setChildren] = useState(0);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [overrides, setOverrides] = useState<Record<string, string>>({});
  const [groups, setGroups] = useState<Group[]>([]);
  const [query, setQuery] = useState("");
  const [roomType, setRoomType] = useState("ALL");
  const [zone, setZone] = useState("ALL");
  const [onlyPriced, setOnlyPriced] = useState(true);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [groupName, setGroupName] = useState("");
  const [contactName, setContactName] = useState("");
  const [contactPhone, setContactPhone] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [notes, setNotes] = useState("");

  const loadGroups = useCallback(async () => {
    try { const body = await api("/core/api/v1/admin/pms/groups"); setGroups(body.items ?? []); }
    catch { /* group history is secondary to availability */ }
  }, []);
  useEffect(() => { void loadGroups(); }, [loadGroups]);

  async function search() {
    setLoading(true); setError(null); setNotice(null); setSelected(new Set()); setOverrides({});
    try {
      const body = await api("/core/api/v1/admin/pms/groups/availability", {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ check_in: checkIn, check_out: checkOut, adults_per_room: adults, children_per_room: children }),
      });
      setRooms(body.items ?? []);
      setNotice(`Свободно: ${body.available_count}. С подтверждённой ценой: ${body.priced_count}.`);
    } catch (cause) { setRooms([]); setError(cause instanceof Error ? cause.message : "Не удалось проверить свободные номера"); }
    finally { setLoading(false); }
  }

  const roomTypes = useMemo(() => Array.from(new Set(rooms.map((room) => room.room_type_name))).sort(), [rooms]);
  const zones = useMemo(() => Array.from(new Set(rooms.map((room) => room.building_or_zone).filter(Boolean) as string[])).sort(), [rooms]);
  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return rooms.filter((room) => {
      if (!room.available) return false;
      if (onlyPriced && (!room.pricing?.sellable || room.pricing.total_kgs == null) && !Number(overrides[room.room_id])) return false;
      if (roomType !== "ALL" && room.room_type_name !== roomType) return false;
      if (zone !== "ALL" && room.building_or_zone !== zone) return false;
      if (q && ![room.code, room.name, room.room_type_name, room.building_or_zone, room.floor].some((value) => String(value || "").toLowerCase().includes(q))) return false;
      return true;
    });
  }, [rooms, query, roomType, zone, onlyPriced, overrides]);

  const selectedRooms = useMemo(() => rooms.filter((room) => selected.has(room.room_id)), [rooms, selected]);
  const selectedTotal = useMemo(() => selectedRooms.reduce((sum, room) => {
    const override = Number(overrides[room.room_id]);
    return sum + (override > 0 ? override : Number(room.pricing?.total_kgs || 0));
  }, 0), [selectedRooms, overrides]);

  function toggle(id: string) {
    setSelected((current) => { const next = new Set(current); if (next.has(id)) next.delete(id); else next.add(id); return next; });
  }
  function selectVisible() { setSelected(new Set(visible.filter((room) => room.pricing?.sellable || Number(overrides[room.room_id]) > 0).map((room) => room.room_id))); }

  async function commit(event: FormEvent) {
    event.preventDefault();
    if (!selectedRooms.length) { setError("Выберите хотя бы один номер."); return; }
    const unresolved = selectedRooms.find((room) => (!room.pricing?.sellable || room.pricing.total_kgs == null) && !(Number(overrides[room.room_id]) > 0));
    if (unresolved) { setError(`Для номера ${unresolved.code} нет подтверждённой цены. Укажите ручную цену.`); return; }
    if (!window.confirm(`Создать группу «${groupName}» на ${selectedRooms.length} номеров? Общая сумма: ${money(selectedTotal)}. Операция атомарная.`)) return;
    setBusy(true); setError(null); setNotice(null);
    try {
      const body = await api("/core/api/v1/admin/pms/groups", {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({
          name: groupName, contact_name: contactName, contact_phone: contactPhone,
          contact_email: contactEmail.trim() || null, check_in: checkIn, check_out: checkOut, notes: notes.trim() || null,
          rooms: selectedRooms.map((room) => ({
            room_id: room.room_id, adults, children,
            manager_total_kgs: Number(overrides[room.room_id]) > 0 ? Math.round(Number(overrides[room.room_id])) : null,
          })),
        }),
      });
      setNotice(`Группа ${body.group_code} создана: ${body.room_count} номеров · ${money(body.total_kgs)}. Частичных броней нет.`);
      setSelected(new Set()); setGroupName(""); setNotes(""); setOverrides({});
      await Promise.all([search(), loadGroups()]);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Не удалось создать групповую бронь"); }
    finally { setBusy(false); }
  }

  return <main className={styles.shell}>
    <header className={styles.head}><div><p>PMS · Group Booking</p><h1>Групповая бронь</h1><span>Один фильтр → несколько номеров → одна атомарная операция. Если доступность изменилась, группа не создаётся частично.</span></div><button onClick={() => void loadGroups()}>↻ История</button></header>
    {error && <div className={styles.error}>{error}</div>}{notice && <div className={styles.notice}>{notice}</div>}

    <section className={styles.searchCard}>
      <div className={styles.searchFields}><label>Заезд<input type="date" value={checkIn} onChange={(e) => setCheckIn(e.target.value)} /></label><label>Выезд<input type="date" value={checkOut} onChange={(e) => setCheckOut(e.target.value)} /></label><label>Взр. / номер<input type="number" min="1" max="20" value={adults} onChange={(e) => setAdults(Math.max(1, Number(e.target.value) || 1))} /></label><label>Дет. / номер<input type="number" min="0" max="20" value={children} onChange={(e) => setChildren(Math.max(0, Number(e.target.value) || 0))} /></label><button className={styles.primary} onClick={() => void search()} disabled={loading}>{loading ? "Проверяю…" : "Найти свободные"}</button></div>
      {rooms.length > 0 && <div className={styles.filters}><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Номер / категория / корпус" /><select value={roomType} onChange={(e) => setRoomType(e.target.value)}><option value="ALL">Все категории</option>{roomTypes.map((value) => <option key={value}>{value}</option>)}</select><select value={zone} onChange={(e) => setZone(e.target.value)}><option value="ALL">Все корпуса / зоны</option>{zones.map((value) => <option key={value}>{value}</option>)}</select><label><input type="checkbox" checked={onlyPriced} onChange={(e) => setOnlyPriced(e.target.checked)} /> Только с ценой</label><button onClick={selectVisible}>Выбрать показанные</button><button onClick={() => setSelected(new Set())}>Снять выбор</button></div>}
    </section>

    {rooms.length > 0 && <div className={styles.layout}>
      <section className={styles.roomsCard}>
        <div className={styles.cardHead}><div><small>Результат фильтра</small><h2>Свободные номера · {visible.length}</h2></div><strong>{selected.size} выбрано</strong></div>
        <div className={styles.rooms}>{visible.map((room) => {
          const override = overrides[room.room_id] || "";
          const needsOverride = !room.pricing?.sellable || room.pricing.total_kgs == null;
          return <article key={room.room_id} className={selected.has(room.room_id) ? styles.selected : ""}>
            <label className={styles.roomMain}><input type="checkbox" checked={selected.has(room.room_id)} onChange={() => toggle(room.room_id)} /><span><strong>№ {room.code}</strong><b>{room.room_type_name}</b><small>{room.building_or_zone || "—"} · {room.floor || "—"} · до {room.capacity_adults}+{room.capacity_children}</small></span></label>
            <div className={styles.price}>{needsOverride ? <><span>Цена требует решения</span><input type="number" min="1" value={override} onChange={(e) => setOverrides((current) => ({ ...current, [room.room_id]: e.target.value }))} placeholder="Ручная цена" /></> : <><span>Core rate</span><strong>{money(Number(room.pricing!.total_kgs))}</strong>{selected.has(room.room_id) && <input type="number" min="1" value={override} onChange={(e) => setOverrides((current) => ({ ...current, [room.room_id]: e.target.value }))} placeholder="или override" />}</>}</div>
          </article>;
        })}</div>
      </section>

      <form className={styles.commitCard} onSubmit={commit}>
        <div className={styles.cardHead}><div><small>Одна группа</small><h2>Оформление</h2></div></div>
        <label>Название группы<input value={groupName} onChange={(e) => setGroupName(e.target.value)} placeholder="Компания / команда / семья" required minLength={2} /></label>
        <label>Контактное лицо<input value={contactName} onChange={(e) => setContactName(e.target.value)} required minLength={2} /></label>
        <label>Телефон<input value={contactPhone} onChange={(e) => setContactPhone(e.target.value)} required minLength={5} /></label>
        <label>Email<input type="email" value={contactEmail} onChange={(e) => setContactEmail(e.target.value)} /></label>
        <label>Комментарий<textarea value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Особенности группы, питание, конференция…" /></label>
        <div className={styles.summary}><span>Номеров<strong>{selectedRooms.length}</strong></span><span>Гостей<strong>{selectedRooms.length * (adults + children)}</strong></span><span>Сумма<strong>{money(selectedTotal)}</strong></span></div>
        <button className={styles.primary} disabled={busy || !selectedRooms.length}>{busy ? "Создаю всю группу…" : `Создать группу в один клик · ${selectedRooms.length}`}</button>
        <p>Все номера бронируются в одной транзакции. Оплата отдельно фиксируется по факту.</p>
      </form>
    </div>}

    <section className={styles.history}><div className={styles.cardHead}><div><small>История</small><h2>Группы</h2></div></div>{groups.length === 0 ? <p>Групповых броней пока нет.</p> : groups.map((group) => <article key={group.id}><div><strong>{group.code} · {group.name}</strong><span>{group.contact_name} · {group.contact_phone}</span></div><div><b>{group.check_in} → {group.check_out}</b><span>{group.room_count} номеров</span></div><div><b>{money(group.paid_kgs)} / {money(group.total_kgs)}</b><span>{group.status}</span></div></article>)}</section>
  </main>;
}
