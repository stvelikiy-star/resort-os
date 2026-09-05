"use client";

import { useEffect, useMemo, useState } from "react";

type Segment = {
  id: string;
  kind: string;
  start: string;
  end: string;
  reason?: string | null;
  reservation_id?: string | null;
  booking_number?: string | null;
  reservation_status?: string | null;
  guest_name?: string | null;
};

type MatrixRoom = {
  id: string;
  code: string;
  name: string;
  building?: string | null;
  floor?: string | null;
  operational_state: string;
  room_type_code: string;
  room_type_name: string;
  segments: Segment[];
};

type MatrixResponse = {
  range: { from: string; to: string; days: number };
  dates: string[];
  rooms: MatrixRoom[];
  truth: string;
};

function cellFor(room: MatrixRoom, date: string) {
  return room.segments.find((segment) => segment.start <= date && date < segment.end) || null;
}

function shortDate(value: string) {
  const [, month, day] = value.slice(0, 10).split("-");
  return `${day}.${month}`;
}

export default function OwnerOccupancyMatrix({ fromDate, toDate }: { fromDate: string; toDate: string }) {
  const [matrix, setMatrix] = useState<MatrixResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const days = useMemo(() => {
    if (!fromDate || !toDate) return 0;
    const start = new Date(`${fromDate}T00:00:00`);
    const end = new Date(`${toDate}T00:00:00`);
    return Math.round((end.getTime() - start.getTime()) / 86400000) + 1;
  }, [fromDate, toDate]);

  useEffect(() => {
    if (!fromDate || !toDate || days < 1 || days > 93) {
      setMatrix(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    const params = new URLSearchParams({ from_date: fromDate, to_date: toDate });
    fetch(`/core/api/v1/admin/intelligence/occupancy-matrix?${params}`, { cache: "no-store" })
      .then(async (response) => {
        const body = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(body.detail || "Не удалось построить карту занятости");
        return body as MatrixResponse;
      })
      .then((payload) => { if (!cancelled) setMatrix(payload); })
      .catch((e) => { if (!cancelled) setError(e instanceof Error ? e.message : "Ошибка карты занятости"); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [fromDate, toDate, days]);

  if (days > 93) {
    return <section className="report-card owner-matrix-card"><div className="report-card-head"><div><span>Номерной фонд</span><h2>Карта занятости по номерам</h2></div></div><p className="report-empty">Для heatmap выберите период до 93 дней. Годовой период остаётся доступен в KPI и Excel-выгрузке.</p></section>;
  }

  return (
    <section className="report-card owner-matrix-card">
      <div className="report-card-head">
        <div><span>Номерной фонд</span><h2>Карта занятости по каждому номеру</h2></div>
        <div className="owner-matrix-legend"><i className="reservation" />бронь <i className="maintenance" />тех/ручной блок <i className="free" />свободно</div>
      </div>
      {loading && !matrix && <div className="loading">Строю карту занятости…</div>}
      {error && <div className="error-box">{error}</div>}
      {matrix && (
        <>
          <div className="owner-matrix-scroll">
            <table className="owner-matrix-table">
              <thead><tr><th className="owner-matrix-room">Номер</th>{matrix.dates.map((date) => <th key={date}>{shortDate(date)}</th>)}</tr></thead>
              <tbody>
                {matrix.rooms.map((room) => (
                  <tr key={room.id}>
                    <th className="owner-matrix-room"><strong>№ {room.code}</strong><span>{room.room_type_name}</span><em>{[room.building, room.floor].filter(Boolean).join(" · ")}</em></th>
                    {matrix.dates.map((date) => {
                      const segment = cellFor(room, date);
                      const kind = segment?.kind === "RESERVATION" ? "reservation" : segment ? "maintenance" : "free";
                      const title = !segment
                        ? `${room.code} · ${date} · свободно`
                        : segment.kind === "RESERVATION"
                          ? `${room.code} · ${date} · ${segment.booking_number || "Бронь"} · ${segment.guest_name || "Гость"}`
                          : `${room.code} · ${date} · ${segment.kind}${segment.reason ? ` · ${segment.reason}` : ""}`;
                      return <td key={`${room.id}-${date}`} className={`owner-matrix-cell ${kind}`} title={title}><span>{segment?.kind === "RESERVATION" ? (segment.guest_name || "Б") : segment ? "×" : ""}</span></td>;
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="owner-matrix-truth">{matrix.truth}</p>
        </>
      )}
    </section>
  );
}
