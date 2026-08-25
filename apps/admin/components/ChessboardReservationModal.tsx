"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

type RoomOption = {
  id: string;
  code: string;
  room_type_code: string;
  room_type_name: string;
  operational_state: string;
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
    adults: number;
    children: number;
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

export type ChessboardMode = "MOVE" | "DATES" | "RELOCATE";

const money = (value?: number | null) => value == null ? "—" : `${new Intl.NumberFormat("ru-RU").format(value)} сом`;

function shiftDate(value: string, days: number) {
  const [y, m, d] = value.split("-").map(Number);
  const date = new Date(Date.UTC(y, m - 1, d + days));
  return date.toISOString().slice(0, 10);
}

function normalizeError(body: any, fallback: string) {
  if (typeof body?.detail === "string") return body.detail;
  if (body?.detail?.code === "STALE_RESERVATION") return "Бронь уже изменена в другом окне. Обновите данные и повторите.";
  if (["ROOM_CONFLICT", "ROOM_CONFLICT_RACE"].includes(body?.detail?.code)) return "Выбранный номер уже занят в части этого периода. Исходная бронь не изменена.";
  if (body?.detail?.code === "PAST_ROOM_HISTORY_IMMUTABLE") return "Нельзя переписать уже прожитые ночи. Используйте переселение с текущей даты.";
  if (body?.detail?.code === "TARGET_ROOM_TECH_BLOCK") return "Целевой номер находится в техническом блоке.";
  if (body?.detail?.code === "TARGET_ROOM_NOT_READY") return `Номер ${body.detail.room_code || ""} ещё не готов к переселению.`.trim();
  if (body?.detail?.code === "CHECK_IN_ROOM_NOT_READY") return `Номер ${body.detail.room_code || ""} не готов к заселению (${body.detail.room_state || "статус неизвестен"}).`.trim();
  if (body?.detail?.code === "CURRENT_SCHEDULE_NOT_CONTIGUOUS" || body?.detail?.code === "CURRENT_SCHEDULE_RANGE_MISMATCH") return "У этой брони нарушен текущий график размещения. Сначала требуется проверка менеджером.";
  return fallback;
}

export default function ChessboardReservationModal({
  reservationId,
  rooms,
  onClose,
  onUpdated,
  initialMode,
  initialTargetRoomId,
  initialCheckIn,
  initialCheckOut,
}: {
  reservationId: string;
  rooms: RoomOption[];
  onClose: () => void;
  onUpdated: () => void;
  initialMode?: ChessboardMode;
  initialTargetRoomId?: string;
  initialCheckIn?: string;
  initialCheckOut?: string;
}) {
  const [data, setData] = useState<ScheduleResponse | null>(null);
  const [mode, setMode] = useState<ChessboardMode>(initialMode || "MOVE");
  const [targetRoomId, setTargetRoomId] = useState(initialTargetRoomId || "");
  const [newCheckIn, setNewCheckIn] = useState("");
  const [newCheckOut, setNewCheckOut] = useState("");
  const [effectiveDate, setEffectiveDate] = useState("");
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const autoPreviewDone = useRef(false);

  useEffect(() => {
    autoPreviewDone.current = false;
  }, [reservationId, initialMode, initialTargetRoomId, initialCheckIn, initialCheckOut]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/core/api/v1/admin/pms/reservations/${reservationId}/schedule`, { cache: "no-store" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(normalizeError(body, "Не удалось загрузить бронь"));
      const payload = body as ScheduleResponse;
      const requestedMode = initialMode || "MOVE";
      const resolvedMode: ChessboardMode = payload.reservation.status === "CHECKED_IN" && requestedMode === "MOVE" ? "RELOCATE" : requestedMode;
      setData(payload);
      setMode(resolvedMode);
      setNewCheckIn(initialCheckIn || payload.reservation.check_in);
      setNewCheckOut(initialCheckOut || payload.reservation.check_out);
      setEffectiveDate(payload.local_today > payload.reservation.check_in ? payload.local_today : payload.reservation.check_in);
      setTargetRoomId(initialTargetRoomId || payload.schedule[0]?.room_id || "");
      setPreview(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка загрузки брони");
    } finally {
      setLoading(false);
    }
  }, [reservationId, initialMode, initialTargetRoomId, initialCheckIn, initialCheckOut]);

  useEffect(() => { void load(); }, [load]);

  const currentRoomIds = useMemo(() => new Set((data?.schedule || []).map((x) => x.room_id)), [data]);
  const hasInitialPlacementDates = Boolean(initialCheckIn || initialCheckOut);

  function proposedSchedule(currentMode = mode, roomId = targetRoomId): ScheduleSegment[] {
    if (!data || data.schedule.length === 0) return [];
    const source = data.schedule.map((x) => ({ ...x }));

    if (currentMode === "MOVE") {
      if (!roomId) return [];
      if (source.length === 1 && newCheckIn && newCheckOut && newCheckOut > newCheckIn) {
        return [{ ...source[0], room_id: roomId, start: newCheckIn, end: newCheckOut }];
      }
      return source.map((item) => ({ ...item, room_id: roomId }));
    }

    if (currentMode === "DATES") {
      if (!newCheckIn || !newCheckOut || newCheckOut <= newCheckIn) return [];
      const resized = source
        .filter((item) => item.end > newCheckIn && item.start < newCheckOut)
        .map((item) => ({ ...item }));
      if (resized.length === 0) {
        const base = source[0];
        return [{ ...base, start: newCheckIn, end: newCheckOut }];
      }
      resized[0].start = newCheckIn;
      resized[resized.length - 1].end = newCheckOut;
      return resized;
    }

    if (!roomId || !effectiveDate || effectiveDate >= data.reservation.check_out) return [];
    const kept: ScheduleSegment[] = [];
    for (const item of source) {
      if (item.end <= effectiveDate) {
        kept.push(item);
        continue;
      }
      if (item.start < effectiveDate && effectiveDate < item.end) {
        kept.push({ ...item, end: effectiveDate });
      }
      break;
    }
    kept.push({ room_id: roomId, start: effectiveDate, end: data.reservation.check_out });
    return kept;
  }

  async function requestPreview(segments: Array<{ room_id: string; start: string; end: string }>) {
    setBusy(true);
    setError(null);
    setPreview(null);
    try {
      const response = await fetch(`/core/api/v1/admin/pms/reservations/${reservationId}/schedule/preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ segments }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(normalizeError(body, "Изменение невозможно"));
      setPreview(body as PreviewResponse);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка предварительной проверки");
    } finally {
      setBusy(false);
    }
  }

  async function runPreview() {
    const segments = proposedSchedule().map(({ room_id, start, end }) => ({ room_id, start, end }));
    if (!segments.length) {
      setError("Проверьте выбранные даты и номер.");
      return;
    }
    await requestPreview(segments);
  }

  useEffect(() => {
    if (!data || autoPreviewDone.current) return;

    if (initialTargetRoomId && data.reservation.status === "GUARANTEED") {
      autoPreviewDone.current = true;
      const segments = proposedSchedule("MOVE", initialTargetRoomId).map(({ room_id, start, end }) => ({ room_id, start, end }));
      if (segments.length) void requestPreview(segments);
      return;
    }

    if ((initialCheckIn || initialCheckOut) && mode === "DATES") {
      autoPreviewDone.current = true;
      const segments = proposedSchedule("DATES").map(({ room_id, start, end }) => ({ room_id, start, end }));
      if (segments.length) void requestPreview(segments);
    }
    // Initial drag/drop and edge-resize gestures intentionally trigger one server preview only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, initialTargetRoomId, initialCheckIn, initialCheckOut, mode, newCheckIn, newCheckOut]);

  async function commit() {
    if (!preview) return;
    setBusy(true);
    setError(null);
    try {
      const segments = preview.proposed_schedule.map(({ room_id, start, end }) => ({ room_id, start, end }));
      const response = await fetch(`/core/api/v1/admin/pms/reservations/${reservationId}/schedule/commit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ segments, expected_version: preview.reservation.version }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(normalizeError(body, "Не удалось сохранить изменение"));
      await load();
      onUpdated();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка сохранения");
    } finally {
      setBusy(false);
    }
  }

  async function stayAction(action: "check-in" | "check-out") {
    if (!data) return;
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(`/core/api/v1/admin/stays/reservations/${reservationId}/${action}`, { method: "POST" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(normalizeError(body, action === "check-in" ? "Не удалось заселить" : "Не удалось выселить"));
      await load();
      onUpdated();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка операции проживания");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop chess-modal-backdrop" role="dialog" aria-modal="true" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <section className="chess-reservation-modal">
        <header className="chess-modal-head">
          <div>
            <p className="eyebrow">Шахматка · управление проживанием</p>
            <h2>{data?.reservation.booking_number || "Бронь"}</h2>
            {data && <p>{data.guest.name || "Гость"}{data.guest.phone ? ` · ${data.guest.phone}` : ""}</p>}
          </div>
          <button className="btn" onClick={onClose}>Закрыть</button>
        </header>

        {loading ? <div className="loading">Загрузка брони…</div> : !data ? <div className="error-box">{error || "Бронь не найдена"}</div> : <>
          <div className="chess-stay-summary">
            <div><span>Статус</span><strong>{data.reservation.status}</strong></div>
            <div><span>Даты</span><strong>{data.reservation.check_in} → {data.reservation.check_out}</strong></div>
            <div><span>Гостей</span><strong>{data.reservation.adults} взр. · {data.reservation.children} дет.</strong></div>
            <div><span>Стоимость в брони</span><strong>{money(data.reservation.stored_total_kgs)}</strong></div>
          </div>

          <div className="chess-current-schedule">
            <strong>Текущее размещение</strong>
            {data.schedule.map((item) => <div key={item.inventory_block_id || `${item.room_id}-${item.start}`}><b>№ {item.room_code}</b><span>{item.start} → {item.end}</span><small>{item.room_type_name}</small></div>)}
          </div>

          <div className="chess-lifecycle-actions">
            {data.reservation.status === "GUARANTEED" && <button className="btn primary" disabled={busy} onClick={() => stayAction("check-in")}>Заселить гостя</button>}
            {data.reservation.status === "CHECKED_IN" && <button className="btn primary" disabled={busy} onClick={() => stayAction("check-out")}>Оформить выезд</button>}
          </div>

          {["GUARANTEED", "CHECKED_IN"].includes(data.reservation.status) && <>
            <nav className="chess-mode-tabs">
              <button className={mode === "MOVE" ? "active" : ""} disabled={data.reservation.status === "CHECKED_IN"} onClick={() => { setMode("MOVE"); setPreview(null); setError(null); }}>Перенести бронь</button>
              <button className={mode === "DATES" ? "active" : ""} onClick={() => { setMode("DATES"); setPreview(null); setError(null); }}>Изменить даты</button>
              <button className={mode === "RELOCATE" ? "active" : ""} onClick={() => { setMode("RELOCATE"); setPreview(null); setError(null); }}>Переселить с даты</button>
            </nav>

            <div className="chess-mutation-form">
              {mode === "MOVE" && <div className="chess-move-fields">
                <label><span>Новый номер</span><select value={targetRoomId} onChange={(e) => { setTargetRoomId(e.target.value); setPreview(null); }}>
                  {rooms.map((room) => <option key={room.id} value={room.id} disabled={room.operational_state === "TECH_BLOCK"}>{room.code} · {room.room_type_name}{room.operational_state === "TECH_BLOCK" ? " · ремонт" : currentRoomIds.has(room.id) ? " · сейчас" : ""}</option>)}
                </select></label>
                {hasInitialPlacementDates && <div className="chess-placement-note"><span>Новая позиция</span><strong>{newCheckIn} → {newCheckOut}</strong><small>Длительность сохранена при перетаскивании.</small></div>}
              </div>}

              {mode === "DATES" && <div className="chess-date-grid">
                <label><span>Заезд</span><input type="date" value={newCheckIn} disabled={data.reservation.status === "CHECKED_IN"} onChange={(e) => { setNewCheckIn(e.target.value); setPreview(null); }} /></label>
                <label><span>Выезд</span><input type="date" value={newCheckOut} min={data.reservation.status === "CHECKED_IN" ? shiftDate(data.local_today, 1) : shiftDate(newCheckIn || data.reservation.check_in, 1)} onChange={(e) => { setNewCheckOut(e.target.value); setPreview(null); }} /></label>
              </div>}

              {mode === "RELOCATE" && <div className="chess-date-grid">
                <label><span>Переселить с</span><input type="date" value={effectiveDate} min={data.reservation.status === "CHECKED_IN" ? data.local_today : data.reservation.check_in} max={shiftDate(data.reservation.check_out, -1)} onChange={(e) => { setEffectiveDate(e.target.value); setPreview(null); }} /></label>
                <label><span>В новый номер</span><select value={targetRoomId} onChange={(e) => { setTargetRoomId(e.target.value); setPreview(null); }}>
                  {rooms.map((room) => <option key={room.id} value={room.id} disabled={room.operational_state === "TECH_BLOCK"}>{room.code} · {room.room_type_name}{room.operational_state === "TECH_BLOCK" ? " · ремонт" : ""}</option>)}
                </select></label>
              </div>}

              <button className="btn primary" disabled={busy} onClick={runPreview}>{busy ? "Проверяю…" : "Проверить изменение"}</button>
            </div>
          </>}

          {error && <div className="error-box compact">{error}</div>}

          {preview && <div className={`chess-preview ${preview.can_commit ? "ok" : "blocked"}`}>
            <div className="chess-preview-head"><strong>{preview.can_commit ? "Можно сохранить" : "Есть конфликт"}</strong><span>{preview.proposed_check_in} → {preview.proposed_check_out}</span></div>
            <div className="chess-preview-schedule">{preview.proposed_schedule.map((item) => <div key={`${item.room_id}-${item.start}`}><b>№ {item.room_code}</b><span>{item.start} → {item.end}</span><small>{item.room_type_name}</small></div>)}</div>
            {preview.conflicts.length > 0 && <div className="chess-conflicts">{preview.conflicts.map((item, index) => <div key={`${item.room_code}-${item.start}-${index}`}>№ {item.room_code}: занято {item.start} → {item.end}{item.booking_number ? ` · ${item.booking_number}` : item.reason ? ` · ${item.reason}` : ""}</div>)}</div>}
            <div className="chess-price-preview">
              <div><span>Стоимость в брони</span><b>{money(preview.pricing.stored_total_kgs)}</b></div>
              <div><span>Тариф Core для новых дат/номеров</span><b>{preview.pricing.sellable ? money(preview.pricing.suggested_total_kgs) : "требует проверки"}</b></div>
              <div><span>Разница</span><b>{preview.pricing.delta_kgs == null ? "—" : money(preview.pricing.delta_kgs)}</b></div>
            </div>
            <p className="chess-price-note">Перенос не меняет стоимость брони автоматически. Если категория или даты изменились, менеджер отдельно решает коммерческую корректировку.</p>
            {preview.can_commit && <button className="btn primary chess-confirm" disabled={busy} onClick={commit}>{busy ? "Сохраняю…" : "Подтвердить изменение"}</button>}
          </div>}
        </>}
      </section>
    </div>
  );
}
