"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type Room = { id: string; code: string; room_type_name: string; operational_state: string };
type Block = { id: string; room_id: string; room_code: string; block_type: "MAINTENANCE" | "MANUAL"; start_date: string; end_date: string; reason: string; usage_category?: string | null; usage_label?: string | null };
type Context = { rooms: Room[]; blocks: Block[] };

const isoToday = () => new Date().toISOString().slice(0, 10);
const addDays = (iso: string, amount: number) => {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d + amount)).toISOString().slice(0, 10);
};
const usageLabels: Record<string, string> = { OWNER: "Владелец", STAFF: "Сотрудник", GUEST_HOLD: "Оставить гостю", SERVICE: "Служебный", OTHER: "Другое" };

export default function RoomBlocksPanel() {
  const [fromDate, setFromDate] = useState(isoToday());
  const [toDate, setToDate] = useState(addDays(isoToday(), 31));
  const [filterType, setFilterType] = useState("ALL");
  const [context, setContext] = useState<Context>({ rooms: [], blocks: [] });
  const [roomId, setRoomId] = useState("");
  const [blockType, setBlockType] = useState<"MAINTENANCE" | "MANUAL">("MANUAL");
  const [usageCategory, setUsageCategory] = useState("OWNER");
  const [usageLabel, setUsageLabel] = useState("");
  const [startDate, setStartDate] = useState(isoToday());
  const [endDate, setEndDate] = useState(addDays(isoToday(), 1));
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const params = new URLSearchParams({ from_date: fromDate, to_date: toDate, block_type: filterType });
      const response = await fetch(`/core/api/v1/admin/owner-corrections/room-blocks/context?${params}`, { cache: "no-store" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Не удалось загрузить блокировки");
      setContext(body as Context);
      if (!roomId && body.rooms?.length) setRoomId(body.rooms[0].id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось загрузить блокировки");
    }
  }, [fromDate, toDate, filterType, roomId]);

  useEffect(() => { void load(); }, [fromDate, toDate, filterType]); // eslint-disable-line react-hooks/exhaustive-deps

  const selectedRoom = useMemo(() => context.rooms.find((room) => room.id === roomId), [context.rooms, roomId]);

  async function createBlock(event: FormEvent) {
    event.preventDefault();
    if (!roomId) return;
    setBusy(true); setError(null); setSuccess(null);
    try {
      const response = await fetch("/core/api/v1/admin/owner-corrections/room-blocks", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          room_id: roomId,
          block_type: blockType,
          start_date: startDate,
          end_date: endDate,
          usage_category: blockType === "MANUAL" ? usageCategory : null,
          usage_label: usageLabel.trim() || null,
          reason: reason.trim(),
        }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        if (body?.detail?.code === "ROOM_BLOCK_CONFLICT") throw new Error(`№ ${body.detail.room_code}: на выбранный период уже есть бронь или блокировка.`);
        throw new Error(typeof body.detail === "string" ? body.detail : "Не удалось закрыть номер");
      }
      setSuccess(`Номер ${body.room_code} закрыт на выбранный период.`);
      setReason(""); setUsageLabel("");
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось закрыть номер");
    } finally { setBusy(false); }
  }

  async function deactivate(block: Block) {
    const text = block.block_type === "MAINTENANCE" ? "снять ремонтную блокировку" : "снять служебную блокировку";
    if (!window.confirm(`№ ${block.room_code}: ${text} ${block.start_date} → ${block.end_date}?`)) return;
    setBusy(true); setError(null); setSuccess(null);
    try {
      const response = await fetch(`/core/api/v1/admin/owner-corrections/room-blocks/${block.id}`, { method: "DELETE" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Не удалось снять блокировку");
      setSuccess(`Блокировка номера ${block.room_code} снята.`);
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось снять блокировку");
    } finally { setBusy(false); }
  }

  return <section className="pms-v2-card" style={{ marginBottom: 20 }}>
    <div className="topbar">
      <div><p className="eyebrow">Ресепшен · управление фондом</p><h2>Закрыть номер на период</h2><p className="subtitle">Ремонт или служебное удержание. Такой период сразу исключается из доступности и показывается отдельной полосой в шахматке.</p></div>
    </div>

    <form className="controls" onSubmit={createBlock}>
      <div className="control"><label>Номер</label><select value={roomId} onChange={(e) => setRoomId(e.target.value)}>{context.rooms.map((room) => <option key={room.id} value={room.id}>{room.code} · {room.room_type_name}</option>)}</select>{selectedRoom?.operational_state === "TECH_BLOCK" && <small>Сейчас номер уже имеет статус «Ремонт».</small>}</div>
      <div className="control"><label>Тип</label><select value={blockType} onChange={(e) => setBlockType(e.target.value as "MAINTENANCE" | "MANUAL")}><option value="MANUAL">Оставить / закрыть</option><option value="MAINTENANCE">Ремонт на период</option></select></div>
      {blockType === "MANUAL" && <div className="control"><label>Для кого</label><select value={usageCategory} onChange={(e) => setUsageCategory(e.target.value)}>{Object.entries(usageLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div>}
      <div className="control"><label>С</label><input type="date" required value={startDate} onChange={(e) => setStartDate(e.target.value)} /></div>
      <div className="control"><label>По</label><input type="date" required min={addDays(startDate, 1)} value={endDate} onChange={(e) => setEndDate(e.target.value)} /></div>
      <div className="control"><label>Имя / метка</label><input value={usageLabel} onChange={(e) => setUsageLabel(e.target.value)} placeholder={blockType === "MAINTENANCE" ? "например: кондиционер" : "владелец / сотрудник / имя гостя"} /></div>
      <div className="control"><label>Причина *</label><input required minLength={2} value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Почему номер закрываем" /></div>
      <div className="date-actions"><button className="btn primary" disabled={busy || !roomId}>{busy ? "Сохраняю…" : "Закрыть номер"}</button></div>
    </form>

    {error && <div className="error-box compact">{error}</div>}
    {success && <div className="reception-readiness-ok"><b>{success}</b></div>}

    <div className="controls" style={{ marginTop: 16 }}>
      <div className="control"><label>Показать с</label><input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} /></div>
      <div className="control"><label>По</label><input type="date" value={toDate} onChange={(e) => setToDate(e.target.value)} /></div>
      <div className="control"><label>Фильтр</label><select value={filterType} onChange={(e) => setFilterType(e.target.value)}><option value="ALL">Все блокировки</option><option value="MAINTENANCE">Только ремонт</option><option value="MANUAL">Только служебные</option></select></div>
      <div className="date-actions"><button type="button" className="btn" onClick={() => void load()}>Обновить</button></div>
    </div>

    {context.blocks.length === 0 ? <div className="empty">На выбранный период активных ремонтных/служебных блокировок нет.</div> : <div style={{ overflowX: "auto" }}><table style={{ width: "100%", borderCollapse: "collapse" }}><thead><tr><th>Номер</th><th>Тип</th><th>Период</th><th>Для кого / метка</th><th>Причина</th><th /></tr></thead><tbody>{context.blocks.map((block) => <tr key={block.id}><td><strong>№ {block.room_code}</strong></td><td>{block.block_type === "MAINTENANCE" ? "Ремонт" : usageLabels[block.usage_category || ""] || "Служебный"}</td><td>{block.start_date} → {block.end_date}</td><td>{block.usage_label || "—"}</td><td>{block.reason}</td><td><button type="button" className="btn" disabled={busy} onClick={() => void deactivate(block)}>Снять</button></td></tr>)}</tbody></table></div>}
  </section>;
}