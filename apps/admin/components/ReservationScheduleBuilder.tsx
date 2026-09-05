"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type RoomOption = {
  id: string;
  code: string;
  room_type_code: string;
  room_type_name: string;
  operational_state: string;
  building_or_zone?: string | null;
  floor?: string | null;
};

type ScheduleSegment = {
  inventory_block_id?: string;
  room_id: string;
  room_code?: string;
  room_state?: string;
  room_type_code?: string;
  room_type_name?: string;
  start: string;
  end: string;
};

type ScheduleResponse = {
  reservation: {
    id: string;
    booking_number: string;
    status: string;
    check_in: string;
    check_out: string;
    stored_total_kgs: number;
    version: string;
  };
  guest: { name?: string | null; phone?: string | null; email?: string | null };
  schedule: ScheduleSegment[];
  local_today: string;
};

type PreviewResponse = {
  reservation: { id: string; booking_number: string; status: string; stored_total_kgs: number; version: string };
  proposed_schedule: ScheduleSegment[];
  proposed_check_in: string;
  proposed_check_out: string;
  can_commit: boolean;
  category_changed: boolean;
  conflicts: Array<{ room_code: string; block_type: string; start: string; end: string; booking_number?: string | null; reason?: string | null }>;
  pricing: {
    sellable: boolean;
    reason?: string | null;
    suggested_total_kgs?: number | null;
    stored_total_kgs: number;
    delta_kgs?: number | null;
    stored_total_will_change_on_commit: boolean;
  };
};

export type ScheduleIntent =
  | { kind: "OPEN"; segmentBlockId?: string; sourceRoomId?: string; segmentStart?: string; segmentEnd?: string }
  | { kind: "SPLIT"; segmentBlockId?: string; sourceRoomId?: string; segmentStart: string; segmentEnd: string; splitDate: string }
  | { kind: "MOVE_SEGMENT"; segmentBlockId?: string; sourceRoomId: string; segmentStart: string; segmentEnd: string; targetRoomId: string }
  | { kind: "MOVE_STAY"; targetRoomId: string; targetStart: string };

const money = (value?: number | null) => value == null ? "—" : `${new Intl.NumberFormat("ru-RU").format(value)} сом`;

function shiftDate(value: string, amount: number) {
  const [y, m, d] = value.split("-").map(Number);
  const next = new Date(Date.UTC(y, m - 1, d + amount));
  return next.toISOString().slice(0, 10);
}

function dayOrdinal(value: string) {
  const [y, m, d] = value.split("-").map(Number);
  return Math.floor(Date.UTC(y, m - 1, d) / 86400000);
}

function daysBetween(start: string, end: string) {
  return dayOrdinal(end) - dayOrdinal(start);
}

function canonicalize(items: ScheduleSegment[]) {
  const source = [...items].sort((a, b) => a.start.localeCompare(b.start));
  const result: ScheduleSegment[] = [];
  source.forEach((item) => {
    const last = result[result.length - 1];
    if (last && last.room_id === item.room_id && last.end === item.start) {
      last.end = item.end;
      return;
    }
    result.push({ ...item });
  });
  return result;
}

function errorText(body: any, fallback: string) {
  if (typeof body?.detail === "string") return body.detail;
  const code = body?.detail?.code;
  if (code === "STALE_RESERVATION") return "Бронь уже изменена в другом окне. Обновите график и повторите.";
  if (["ROOM_CONFLICT", "ROOM_CONFLICT_RACE"].includes(code)) return "Есть пересечение с другим активным блоком. Изменение не сохранено.";
  if (code === "PAST_ROOM_HISTORY_IMMUTABLE") return "Уже прожитые ночи защищены. Переносите только будущий сегмент или разрежьте график с сегодняшней даты.";
  if (code === "TARGET_ROOM_TECH_BLOCK") return "Целевой номер находится в ремонте.";
  if (code === "TARGET_ROOM_NOT_READY") return "Целевой номер не готов для немедленного переселения.";
  if (code === "SCHEDULE_NOT_CONTIGUOUS") return "График должен оставаться непрерывным без разрывов и наложений.";
  return fallback;
}

function sameSegment(item: ScheduleSegment, intent: Exclude<ScheduleIntent, { kind: "MOVE_STAY" }>) {
  if (intent.segmentBlockId && item.inventory_block_id === intent.segmentBlockId) return true;
  return item.room_id === intent.sourceRoomId && item.start === intent.segmentStart && item.end === intent.segmentEnd;
}

export default function ReservationScheduleBuilder({
  reservationId,
  rooms,
  intent,
  onClose,
  onUpdated,
}: {
  reservationId: string;
  rooms: RoomOption[];
  intent: ScheduleIntent;
  onClose: () => void;
  onUpdated: () => void;
}) {
  const [data, setData] = useState<ScheduleResponse | null>(null);
  const [draft, setDraft] = useState<ScheduleSegment[]>([]);
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [splitInputs, setSplitInputs] = useState<Record<number, string>>({});

  const roomById = useMemo(() => new Map(rooms.map((room) => [room.id, room])), [rooms]);

  const applyIntent = useCallback((payload: ScheduleResponse) => {
    let next = payload.schedule.map((item) => ({ ...item }));
    if (intent.kind === "OPEN") return next;

    if (intent.kind === "MOVE_STAY") {
      if (payload.reservation.status === "CHECKED_IN") {
        setError("Проживающую бронь нельзя сдвигать целиком: прошлые ночи защищены. Используйте режим «Кусок» — он создаст переселение с сегодняшней даты.");
        return next;
      }
      const delta = daysBetween(payload.reservation.check_in, intent.targetStart);
      return canonicalize(next.map((item) => ({ ...item, room_id: intent.targetRoomId, start: shiftDate(item.start, delta), end: shiftDate(item.end, delta) })));
    }

    const index = next.findIndex((item) => sameSegment(item, intent));
    if (index < 0) {
      setError("Выбранный сегмент уже изменился. Обновите шахматку и повторите действие.");
      return next;
    }

    if (intent.kind === "SPLIT") {
      const item = next[index];
      if (intent.splitDate <= item.start || intent.splitDate >= item.end) {
        setError("Линия разреза должна находиться внутри выбранного сегмента.");
        return next;
      }
      if (payload.reservation.status === "CHECKED_IN" && intent.splitDate < payload.local_today) {
        setError("Нельзя разрезать уже прожитую часть графика.");
        return next;
      }
      next.splice(index, 1, { ...item, end: intent.splitDate }, { ...item, inventory_block_id: undefined, start: intent.splitDate });
      return next;
    }

    const item = next[index];
    if (payload.reservation.status === "CHECKED_IN") {
      if (item.end <= payload.local_today) {
        setError("Этот кусок относится только к уже прожитым ночам и защищён от переноса.");
        return next;
      }
      if (item.start < payload.local_today && payload.local_today < item.end) {
        next.splice(index, 1, { ...item, end: payload.local_today }, { ...item, inventory_block_id: undefined, room_id: intent.targetRoomId, start: payload.local_today });
        return canonicalize(next);
      }
    }
    next[index] = { ...item, room_id: intent.targetRoomId };
    return canonicalize(next);
  }, [intent]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setPreview(null);
    try {
      const response = await fetch(`/core/api/v1/admin/pms/reservations/${reservationId}/schedule`, { cache: "no-store" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(errorText(body, "Не удалось загрузить график размещения"));
      const payload = body as ScheduleResponse;
      setData(payload);
      setDraft(applyIntent(payload));
    } catch (cause) {
      setData(null);
      setDraft([]);
      setError(cause instanceof Error ? cause.message : "Ошибка загрузки графика");
    } finally {
      setLoading(false);
    }
  }, [reservationId, applyIntent]);

  useEffect(() => { void load(); }, [load]);

  function resetDraft() {
    if (!data) return;
    setDraft(data.schedule.map((item) => ({ ...item })));
    setPreview(null);
    setError(null);
  }

  function setRoom(index: number, roomId: string) {
    if (!data) return;
    const item = draft[index];
    const historyLocked = data.reservation.status === "CHECKED_IN" && item.start < data.local_today;
    if (historyLocked) {
      setError(item.end > data.local_today ? "Сначала нажмите «Отделить с сегодня», затем переносите будущую часть." : "Этот сегмент относится к защищённой истории проживания.");
      return;
    }
    const next = draft.map((segment, i) => i === index ? { ...segment, room_id: roomId } : { ...segment });
    setDraft(canonicalize(next));
    setPreview(null);
    setError(null);
  }

  function splitSegment(index: number, splitDate?: string) {
    if (!data) return;
    const item = draft[index];
    const date = splitDate || splitInputs[index];
    if (!date || date <= item.start || date >= item.end) {
      setError(`Разрез должен быть внутри ${item.start} → ${item.end}.`);
      return;
    }
    if (data.reservation.status === "CHECKED_IN" && date < data.local_today) {
      setError("Нельзя разрезать уже прожитые ночи.");
      return;
    }
    const next = [...draft];
    next.splice(index, 1, { ...item, end: date }, { ...item, inventory_block_id: undefined, start: date });
    setDraft(next);
    setPreview(null);
    setError(null);
  }

  function splitToday(index: number) {
    if (!data) return;
    splitSegment(index, data.local_today);
  }

  function changeBoundary(index: number, value: string) {
    const left = draft[index];
    const right = draft[index + 1];
    if (!left || !right || value <= left.start || value >= right.end) {
      setError("Граница должна оставлять минимум одну ночь с каждой стороны.");
      return;
    }
    if (data?.reservation.status === "CHECKED_IN" && value < data.local_today) {
      setError("Граница в прожитой истории защищена.");
      return;
    }
    const next = draft.map((item) => ({ ...item }));
    next[index].end = value;
    next[index + 1].start = value;
    setDraft(canonicalize(next));
    setPreview(null);
    setError(null);
  }

  function changeOuter(edge: "start" | "end", value: string) {
    if (!data || !draft.length) return;
    const next = draft.map((item) => ({ ...item }));
    if (edge === "start") {
      if (value >= next[0].end) { setError("Новая дата заезда должна быть раньше конца первого сегмента."); return; }
      if (data.reservation.status === "CHECKED_IN" && value !== data.reservation.check_in) { setError("Дата уже начавшегося проживания не меняется через этот конструктор."); return; }
      next[0].start = value;
    } else {
      const last = next[next.length - 1];
      if (value <= last.start) { setError("Новая дата выезда должна быть позже начала последнего сегмента."); return; }
      last.end = value;
    }
    setDraft(next);
    setPreview(null);
    setError(null);
  }

  function absorb(index: number, direction: "left" | "right") {
    if (!data || draft.length < 2) return;
    const current = draft[index];
    if (data.reservation.status === "CHECKED_IN" && current.start < data.local_today) {
      setError("Нельзя объединять сегмент, который содержит защищённую историю проживания.");
      return;
    }
    const next = draft.map((item) => ({ ...item }));
    if (direction === "left" && index > 0) {
      next[index - 1].end = current.end;
      next.splice(index, 1);
    } else if (direction === "right" && index < next.length - 1) {
      next[index + 1].start = current.start;
      next.splice(index, 1);
    } else return;
    setDraft(canonicalize(next));
    setPreview(null);
    setError(null);
  }

  async function runPreview() {
    if (!draft.length) return;
    setBusy(true);
    setPreview(null);
    setError(null);
    try {
      const response = await fetch(`/core/api/v1/admin/pms/reservations/${reservationId}/schedule/preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ segments: draft.map(({ room_id, start, end }) => ({ room_id, start, end })) }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(errorText(body, "Core отклонил предложенный график"));
      setPreview(body as PreviewResponse);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Ошибка предварительной проверки");
    } finally {
      setBusy(false);
    }
  }

  async function commit() {
    if (!preview) return;
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(`/core/api/v1/admin/pms/reservations/${reservationId}/schedule/commit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          segments: preview.proposed_schedule.map(({ room_id, start, end }) => ({ room_id, start, end })),
          expected_version: preview.reservation.version,
        }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(errorText(body, "Не удалось сохранить график"));
      onUpdated();
      onClose();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Ошибка сохранения");
    } finally {
      setBusy(false);
    }
  }

  const totalNights = draft.length ? daysBetween(draft[0].start, draft[draft.length - 1].end) : 0;

  return <div className="v8-builder-backdrop" role="dialog" aria-modal="true" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <section className="v8-builder">
      <header className="v8-builder-head">
        <div><p className="eyebrow">Universal Stay Builder · V8</p><h2>{data?.reservation.booking_number || "График размещения"}</h2><span>{data?.guest.name || "Гость"}{data?.guest.phone ? ` · ${data.guest.phone}` : ""}</span></div>
        <div className="v8-builder-head-actions"><button className="btn" onClick={resetDraft} disabled={!data || busy}>Сбросить</button><button className="btn" onClick={onClose}>Закрыть</button></div>
      </header>

      {loading ? <div className="v8-builder-loading">Загрузка полного графика из Resort Core…</div> : !data ? <div className="v8-builder-error">{error || "График недоступен"}</div> : <>
        <div className="v8-builder-summary">
          <div><span>Статус</span><strong>{data.reservation.status}</strong></div>
          <div><span>Ночей</span><strong>{totalNights}</strong></div>
          <div><span>Сегментов</span><strong>{draft.length}</strong></div>
          <div><span>Стоимость в брони</span><strong>{money(data.reservation.stored_total_kgs)}</strong></div>
        </div>

        <div className="v8-builder-rules"><strong>Правило:</strong> одна бронь остаётся одной бронью. Сегменты обязаны непрерывно покрывать весь stay. Уже прожитые ночи CHECKED_IN не переписываются; для переселения текущий кусок разрезается с сегодняшней даты.</div>

        <section className="v8-builder-dates">
          <label><span>Заезд</span><input type="date" value={draft[0]?.start || data.reservation.check_in} onChange={(event) => changeOuter("start", event.target.value)} /></label>
          <span className="v8-arrow">→</span>
          <label><span>Выезд</span><input type="date" value={draft[draft.length - 1]?.end || data.reservation.check_out} onChange={(event) => changeOuter("end", event.target.value)} /></label>
        </section>

        <section className="v8-segment-timeline">
          {draft.map((item, index) => {
            const nights = Math.max(1, daysBetween(item.start, item.end));
            const room = roomById.get(item.room_id);
            return <div key={`${item.start}-${item.end}-${item.room_id}-${index}`} className="v8-mini-segment" style={{ flexGrow: nights }} title={`${item.start} → ${item.end} · № ${room?.code || item.room_code || "—"}`}><strong>№ {room?.code || item.room_code || "—"}</strong><span>{nights} н.</span></div>;
          })}
        </section>

        <section className="v8-segments">
          {draft.map((item, index) => {
            const room = roomById.get(item.room_id);
            const lockedPast = data.reservation.status === "CHECKED_IN" && item.end <= data.local_today;
            const crossesToday = data.reservation.status === "CHECKED_IN" && item.start < data.local_today && data.local_today < item.end;
            const roomLocked = lockedPast || crossesToday;
            const defaultSplit = splitInputs[index] || shiftDate(item.start, Math.max(1, Math.floor(daysBetween(item.start, item.end) / 2)));
            return <div className={`v8-segment-card ${lockedPast ? "is-history" : ""} ${crossesToday ? "crosses-today" : ""}`} key={`${item.start}-${item.end}-${item.room_id}-${index}`}>
              <div className="v8-segment-index"><b>{index + 1}</b><span>{lockedPast ? "история" : crossesToday ? "сегодня внутри" : "активный кусок"}</span></div>
              <div className="v8-segment-room">
                <label><span>Номер</span><select value={item.room_id} disabled={roomLocked} onChange={(event) => setRoom(index, event.target.value)}>{rooms.map((option) => <option key={option.id} value={option.id} disabled={option.operational_state === "TECH_BLOCK"}>№ {option.code} · {option.room_type_name}{option.operational_state === "TECH_BLOCK" ? " · РЕМОНТ" : ""}</option>)}</select></label>
                <small>{room?.building_or_zone || ""}{room?.floor ? ` · ${room.floor}` : ""}</small>
              </div>
              <div className="v8-segment-range"><span>{item.start}</span><b>→</b><span>{item.end}</span><small>{daysBetween(item.start, item.end)} ноч.</small></div>
              <div className="v8-segment-cut">
                {crossesToday ? <button onClick={() => splitToday(index)}>Отделить с сегодня</button> : !lockedPast && daysBetween(item.start, item.end) > 1 ? <><input type="date" min={shiftDate(item.start, 1)} max={shiftDate(item.end, -1)} value={defaultSplit} onChange={(event) => setSplitInputs((current) => ({ ...current, [index]: event.target.value }))} /><button onClick={() => splitSegment(index, defaultSplit)}>✂ Разрезать</button></> : <span>Защищено</span>}
              </div>
              <div className="v8-segment-merge">{index > 0 && !lockedPast && <button onClick={() => absorb(index, "left")}>← к предыдущему</button>}{index < draft.length - 1 && !lockedPast && <button onClick={() => absorb(index, "right")}>к следующему →</button>}</div>
              {index < draft.length - 1 && <div className="v8-boundary"><span>Граница переселения</span><input type="date" min={shiftDate(item.start, 1)} max={shiftDate(draft[index + 1].end, -1)} value={item.end} onChange={(event) => changeBoundary(index, event.target.value)} /></div>}
            </div>;
          })}
        </section>

        {error && <div className="v8-builder-error">{error}</div>}

        <div className="v8-builder-preview-actions"><button className="btn primary" onClick={() => void runPreview()} disabled={busy || !draft.length}>{busy ? "Проверяю…" : "Проверить в Resort Core"}</button><span>Сначала preview: конфликты, категории, цена и версия брони. Только затем commit.</span></div>

        {preview && <section className={`v8-preview ${preview.can_commit ? "ok" : "bad"}`}>
          <header><div><strong>{preview.can_commit ? "График можно сохранить" : "Core запретил сохранение"}</strong><span>{preview.proposed_check_in} → {preview.proposed_check_out} · {preview.proposed_schedule.length} сегм.</span></div><b>{preview.category_changed ? "Категория меняется" : "Категория без изменения"}</b></header>
          <div className="v8-preview-money"><div><span>В брони</span><strong>{money(preview.pricing.stored_total_kgs)}</strong></div><div><span>Текущий тариф Core</span><strong>{preview.pricing.sellable ? money(preview.pricing.suggested_total_kgs) : "—"}</strong></div><div><span>Разница</span><strong>{preview.pricing.delta_kgs == null ? "—" : money(preview.pricing.delta_kgs)}</strong></div></div>
          {preview.conflicts.length > 0 && <div className="v8-preview-conflicts">{preview.conflicts.map((conflict, index) => <div key={`${conflict.room_code}-${conflict.start}-${index}`}><strong>№ {conflict.room_code}</strong><span>{conflict.start} → {conflict.end} · {conflict.booking_number || conflict.reason || conflict.block_type}</span></div>)}</div>}
          <p>Коммерческая сумма брони не меняется автоматически. Любая тарифная разница только показывается менеджеру.</p>
          <button className="btn primary" onClick={() => void commit()} disabled={busy || !preview.can_commit}>{busy ? "Сохраняю…" : "Подтвердить и сохранить график"}</button>
        </section>}
      </>}
    </section>
  </div>;
}
