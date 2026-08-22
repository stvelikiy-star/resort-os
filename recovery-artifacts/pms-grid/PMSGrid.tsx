"use client";

// components/admin/PMSGrid.tsx
// Interactive room chessboard ("шахматка") for hotel receptionists: units on
// the Y-axis grouped by category, days of the month/week on the X-axis, each
// cell colored by housekeeping/booking status. Self-contained — swap the
// mock generator for a live feed from GET /api/v1/pms/grid when it's ready.

import { useMemo, useState } from "react";
import {
  Building2,
  ChevronLeft,
  ChevronRight,
  Crown,
  Home,
  Plus,
} from "lucide-react";

// --- Domain types --------------------------------------------------------

export type RoomStatus = "CLEAN" | "DIRTY" | "IN_INSPECTION" | "TECH_BLOCK" | "BOOKED";

export type PMSCategory = "COTTAGE" | "MAIN_BUILDING" | "VIP_SUITE";

export interface DaySegment {
  status: RoomStatus;
  /** 1-indexed day-of-range this segment starts on. */
  startDay: number;
  /** Number of days this segment covers. */
  length: number;
  guestName?: string;
}

export interface PMSUnit {
  id: string;
  name: string;
  category: PMSCategory;
  segments: DaySegment[];
}

interface PMSGridProps {
  units?: PMSUnit[];
  onNewBooking?: () => void;
  onCellClick?: (unit: PMSUnit, date: Date) => void;
}

// --- Presentation constants ----------------------------------------------

const CELL_WIDTH = 40; // px, must match header + body cells for alignment
const LABEL_WIDTH = 220; // px, sticky first column

const STATUS_META: Record<RoomStatus, { label: string; bg: string; text: string }> = {
  CLEAN: { label: "Clean", bg: "#22C55E", text: "#ffffff" },
  DIRTY: { label: "Dirty", bg: "#EF4444", text: "#ffffff" },
  IN_INSPECTION: { label: "Inspection", bg: "#EAB308", text: "#1E293B" },
  TECH_BLOCK: { label: "Tech block", bg: "#6B7280", text: "#ffffff" },
  BOOKED: { label: "Booked", bg: "#3B82F6", text: "#ffffff" },
};

const CATEGORY_META: Record<PMSCategory, { label: string; icon: typeof Home }> = {
  COTTAGE: { label: "Cottages", icon: Home },
  MAIN_BUILDING: { label: "Main Building", icon: Building2 },
  VIP_SUITE: { label: "VIP Suites", icon: Crown },
};

const CATEGORY_ORDER: PMSCategory[] = ["MAIN_BUILDING", "COTTAGE", "VIP_SUITE"];

// --- Deterministic mock data ----------------------------------------------
// Seeded PRNG so server and client render the same board (no hydration
// mismatch) — replace this whole block with a real PMS fetch.

function mulberry32(seed: number) {
  let a = seed;
  return function random() {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function hashSeed(text: string): number {
  let hash = 0;
  for (let i = 0; i < text.length; i++) {
    hash = (hash << 5) - hash + text.charCodeAt(i);
    hash |= 0;
  }
  return hash;
}

const GUEST_NAMES = [
  "A. Sadykova",
  "N. Ivanov",
  "M. Chen",
  "E. Petrov",
  "S. Karimov",
  "L. Novak",
  "R. Tashiev",
  "D. Volkov",
];

function generateMockSegments(unitId: string, totalDays: number): DaySegment[] {
  const rand = mulberry32(hashSeed(unitId));
  const segments: DaySegment[] = [];
  let day = 1;

  while (day <= totalDays) {
    const roll = rand();

    if (roll < 0.35 && totalDays - day >= 1) {
      // Multi-night booking, 2–5 nights (clamped to remaining days).
      const length = Math.min(2 + Math.floor(rand() * 4), totalDays - day + 1);
      segments.push({
        status: "BOOKED",
        startDay: day,
        length,
        guestName: GUEST_NAMES[Math.floor(rand() * GUEST_NAMES.length)],
      });
      day += length;
      continue;
    }

    let status: RoomStatus = "CLEAN";
    if (roll >= 0.35 && roll < 0.55) status = "DIRTY";
    else if (roll >= 0.55 && roll < 0.65) status = "IN_INSPECTION";
    else if (roll >= 0.65 && roll < 0.7) status = "TECH_BLOCK";

    segments.push({ status, startDay: day, length: 1 });
    day += 1;
  }

  return segments;
}

const MOCK_UNIT_DEFS: { id: string; name: string; category: PMSCategory }[] = [
  { id: "mb-101", name: "Room 101", category: "MAIN_BUILDING" },
  { id: "mb-102", name: "Room 102", category: "MAIN_BUILDING" },
  { id: "mb-103", name: "Room 103", category: "MAIN_BUILDING" },
  { id: "mb-201", name: "Room 201", category: "MAIN_BUILDING" },
  { id: "mb-202", name: "Room 202", category: "MAIN_BUILDING" },
  { id: "ct-issyk", name: "Issyk-Kul Standard", category: "COTTAGE" },
  { id: "ct-emerald", name: "Emerald Deluxe", category: "COTTAGE" },
  { id: "ct-birch", name: "Birch Cottage", category: "COTTAGE" },
  { id: "vip-tian-shan", name: "Tian Shan VIP Cottage", category: "VIP_SUITE" },
  { id: "vip-ala-too", name: "Ala-Too VIP Cottage", category: "VIP_SUITE" },
];

function buildMockUnits(totalDays: number): PMSUnit[] {
  return MOCK_UNIT_DEFS.map((def) => ({
    ...def,
    segments: generateMockSegments(def.id, totalDays),
  }));
}

// --- Date helpers ----------------------------------------------------------

const WEEKDAY_LABELS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"];

function daysInMonth(year: number, month: number): number {
  return new Date(year, month + 1, 0).getDate();
}

function startOfWeek(date: Date): Date {
  const result = new Date(date);
  const day = (result.getDay() + 6) % 7; // Monday = 0
  result.setDate(result.getDate() - day);
  result.setHours(0, 0, 0, 0);
  return result;
}

function addDays(date: Date, amount: number): Date {
  const result = new Date(date);
  result.setDate(result.getDate() + amount);
  return result;
}

function isSameDay(a: Date, b: Date): boolean {
  return a.toDateString() === b.toDateString();
}

// --- Component ---------------------------------------------------------

export default function PMSGrid({ units, onNewBooking, onCellClick }: PMSGridProps) {
  const [viewMode, setViewMode] = useState<"month" | "week">("month");
  const [anchorDate, setAnchorDate] = useState(() => new Date());
  const [categoryFilter, setCategoryFilter] = useState<PMSCategory | "ALL">("ALL");

  const today = new Date();

  const { rangeStart, totalDays, rangeLabel } = useMemo(() => {
    if (viewMode === "month") {
      const year = anchorDate.getFullYear();
      const month = anchorDate.getMonth();
      const start = new Date(year, month, 1);
      const total = daysInMonth(year, month);
      return {
        rangeStart: start,
        totalDays: total,
        rangeLabel: start.toLocaleDateString("en-US", { month: "long", year: "numeric" }),
      };
    }
    const start = startOfWeek(anchorDate);
    const end = addDays(start, 6);
    const sameMonth = start.getMonth() === end.getMonth();
    const label = sameMonth
      ? `${start.toLocaleDateString("en-US", { month: "short", day: "numeric" })} – ${end.toLocaleDateString("en-US", { day: "numeric" })}`
      : `${start.toLocaleDateString("en-US", { month: "short", day: "numeric" })} – ${end.toLocaleDateString("en-US", { month: "short", day: "numeric" })}`;
    return { rangeStart: start, totalDays: 7, rangeLabel: label };
  }, [viewMode, anchorDate]);

  const dayDates = useMemo(
    () => Array.from({ length: totalDays }, (_, i) => addDays(rangeStart, i)),
    [rangeStart, totalDays]
  );

  const units_ = useMemo(() => units ?? buildMockUnits(totalDays), [units, totalDays]);

  const filteredByCategory = useMemo(
    () => (categoryFilter === "ALL" ? units_ : units_.filter((u) => u.category === categoryFilter)),
    [units_, categoryFilter]
  );

  const groupedUnits = useMemo(() => {
    return CATEGORY_ORDER.map((category) => ({
      category,
      units: filteredByCategory.filter((u) => u.category === category),
    })).filter((group) => group.units.length > 0);
  }, [filteredByCategory]);

  const navigate = (direction: -1 | 1) => {
    setAnchorDate((prev) =>
      viewMode === "month"
        ? new Date(prev.getFullYear(), prev.getMonth() + direction, 1)
        : addDays(prev, direction * 7)
    );
  };

  const gridBodyWidth = totalDays * CELL_WIDTH;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white text-[#1E293B]">
      {/* Controls */}
      <div className="flex flex-col gap-3 border-b border-slate-100 p-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-wrap items-center gap-3">
          {/* Month / Week toggle */}
          <div className="flex rounded-lg border border-slate-200 p-0.5 text-sm">
            {(["month", "week"] as const).map((mode) => (
              <button
                key={mode}
                type="button"
                onClick={() => setViewMode(mode)}
                className={[
                  "rounded-md px-3 py-1.5 font-medium capitalize transition-colors",
                  viewMode === mode ? "bg-[#0F5132] text-white" : "text-slate-500 hover:bg-slate-50",
                ].join(" ")}
              >
                {mode}
              </button>
            ))}
          </div>

          {/* Navigation */}
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 text-slate-500 transition-colors hover:bg-slate-50"
              aria-label="Previous"
            >
              <ChevronLeft size={16} />
            </button>
            <span className="min-w-[10rem] text-center text-sm font-semibold">{rangeLabel}</span>
            <button
              type="button"
              onClick={() => navigate(1)}
              className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 text-slate-500 transition-colors hover:bg-slate-50"
              aria-label="Next"
            >
              <ChevronRight size={16} />
            </button>
          </div>

          {/* Category filter */}
          <div className="flex flex-wrap gap-1.5">
            <button
              type="button"
              onClick={() => setCategoryFilter("ALL")}
              className={[
                "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                categoryFilter === "ALL"
                  ? "border-[#0F5132] bg-[#0F5132]/10 text-[#0F5132]"
                  : "border-slate-200 text-slate-500 hover:border-slate-300",
              ].join(" ")}
            >
              All units
            </button>
            {CATEGORY_ORDER.map((category) => (
              <button
                key={category}
                type="button"
                onClick={() => setCategoryFilter(category)}
                className={[
                  "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                  categoryFilter === category
                    ? "border-[#0F5132] bg-[#0F5132]/10 text-[#0F5132]"
                    : "border-slate-200 text-slate-500 hover:border-slate-300",
                ].join(" ")}
              >
                {CATEGORY_META[category].label}
              </button>
            ))}
          </div>
        </div>

        <button
          type="button"
          onClick={onNewBooking}
          className="flex shrink-0 items-center justify-center gap-1.5 rounded-lg bg-[#D4AF37] px-4 py-2 text-sm font-semibold text-[#1E293B] transition-colors hover:bg-[#c49f2e]"
        >
          <Plus size={16} />
          New booking
        </button>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap items-center gap-4 border-b border-slate-100 px-4 py-2.5 text-xs text-slate-500">
        {(Object.keys(STATUS_META) as RoomStatus[]).map((status) => (
          <span key={status} className="flex items-center gap-1.5">
            <span
              className="h-2.5 w-2.5 rounded-sm"
              style={{ backgroundColor: STATUS_META[status].bg }}
            />
            {STATUS_META[status].label}
          </span>
        ))}
      </div>

      {/* Grid */}
      <div className="overflow-x-auto">
        <div className="inline-flex min-w-full flex-col">
          {/* Header row */}
          <div className="flex border-b border-slate-100 bg-white">
            <div
              className="sticky left-0 z-10 flex shrink-0 items-center bg-white px-4 py-2 text-xs font-semibold uppercase tracking-wide text-slate-400"
              style={{ width: LABEL_WIDTH }}
            >
              Unit
            </div>
            <div className="flex" style={{ width: gridBodyWidth }}>
              {dayDates.map((date) => {
                const weekend = date.getDay() === 0 || date.getDay() === 6;
                const isToday = isSameDay(date, today);
                return (
                  <div
                    key={date.toISOString()}
                    className={[
                      "flex shrink-0 flex-col items-center justify-center border-l border-slate-50 py-1.5 text-[11px]",
                      weekend ? "bg-[#F8F9FA] text-slate-500" : "text-slate-400",
                      isToday ? "bg-[#D4AF37]/10 font-semibold text-[#0F5132]" : "",
                    ].join(" ")}
                    style={{ width: CELL_WIDTH }}
                  >
                    <span>{WEEKDAY_LABELS[(date.getDay() + 6) % 7]}</span>
                    <span className="text-[13px] font-semibold text-[#1E293B]">{date.getDate()}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Body */}
          {groupedUnits.map((group) => {
            const Icon = CATEGORY_META[group.category].icon;
            return (
              <div key={group.category}>
                <div className="flex bg-[#F8F9FA]">
                  <div
                    className="sticky left-0 z-10 flex shrink-0 items-center gap-1.5 bg-[#F8F9FA] px-4 py-1.5 text-xs font-semibold text-[#0F5132]"
                    style={{ width: LABEL_WIDTH + gridBodyWidth }}
                  >
                    <Icon size={13} />
                    {CATEGORY_META[group.category].label}
                    <span className="font-normal text-slate-400">({group.units.length})</span>
                  </div>
                </div>

                {group.units.map((unit) => (
                  <div key={unit.id} className="flex border-b border-slate-50">
                    <div
                      className="sticky left-0 z-10 flex shrink-0 items-center truncate bg-white px-4 py-2 text-sm font-medium"
                      style={{ width: LABEL_WIDTH }}
                      title={unit.name}
                    >
                      {unit.name}
                    </div>
                    <div className="flex" style={{ width: gridBodyWidth }}>
                      {unit.segments.map((segment) => {
                        const meta = STATUS_META[segment.status];
                        const segmentDate = addDays(rangeStart, segment.startDay - 1);
                        const tooltip =
                          segment.status === "BOOKED"
                            ? `${segment.guestName} — ${segment.length} night${segment.length !== 1 ? "s" : ""}`
                            : meta.label;
                        return (
                          <button
                            key={`${unit.id}-${segment.startDay}`}
                            type="button"
                            onClick={() => onCellClick?.(unit, segmentDate)}
                            title={tooltip}
                            className="flex shrink-0 items-center justify-center overflow-hidden border-l border-white px-1 py-2 text-[11px] font-medium transition-opacity hover:opacity-90"
                            style={{
                              width: CELL_WIDTH * segment.length,
                              backgroundColor: meta.bg,
                              color: meta.text,
                            }}
                          >
                            {segment.status === "BOOKED" && segment.length >= 2 ? (
                              <span className="truncate">{segment.guestName}</span>
                            ) : null}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            );
          })}

          {groupedUnits.length === 0 && (
            <p className="p-8 text-center text-sm text-slate-400">No units match this filter.</p>
          )}
        </div>
      </div>
    </div>
  );
}
