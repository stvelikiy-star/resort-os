"use client";

import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";

export type ControlReservationV9 = {
  id: string;
  bookingNumber: string;
  status: "GUARANTEED" | "CHECKED_IN";
  checkIn: string;
  checkOut: string;
  adults: number;
  children: number;
  totalKgs: number;
  paidKgs: number;
  remainingKgs: number;
  firstName?: string | null;
  lastName?: string | null;
  phone?: string | null;
  email?: string | null;
  room_id?: string | null;
  room_code?: string | null;
  room_state?: string | null;
  room_type_name?: string | null;
  schedule_segments: number;
  has_room_move: boolean;
};

export type ControlTaskV9 = {
  id: string;
  type: "HOUSEKEEPING" | "MAINTENANCE" | "GUEST_REQUEST";
  status: "OPEN" | "IN_PROGRESS" | "IN_INSPECTION";
  priority: "LOW" | "NORMAL" | "HIGH" | "URGENT";
  title: string;
  description?: string | null;
  room_id?: string | null;
  room_code?: string | null;
  room_state?: string | null;
  assigned_to_id?: string | null;
  assigned_to_name?: string | null;
  source?: string | null;
  created_at: string;
  updated_at: string;
};

export type ControlRoomV9 = {
  id: string;
  code: string;
  name: string;
  state: "UNKNOWN" | "CLEAN" | "DIRTY" | "IN_INSPECTION" | "TECH_BLOCK";
  building_or_zone?: string | null;
  floor?: string | null;
  room_type_code: string;
  room_type_name: string;
};

export type ControlSnapshotV9 = {
  complete: true;
  generated_at: string;
  local_date: string;
  window: { start: string; end: string };
  room_states: Record<string, number>;
  rooms: ControlRoomV9[];
  reservations: ControlReservationV9[];
  tasks: ControlTaskV9[];
  summary: {
    room_count: number;
    active_reservations: number;
    active_tasks: number;
    debt_total_kgs: number;
    unassigned_guaranteed: number;
  };
  truth?: string;
};

type ContextValue = {
  snapshot: ControlSnapshotV9 | null;
  loading: boolean;
  refreshing: boolean;
  error: string | null;
  refresh: () => Promise<void>;
};

const Context = createContext<ContextValue | null>(null);

function dateOnly(value = new Date()) {
  const y = value.getFullYear();
  const m = String(value.getMonth() + 1).padStart(2, "0");
  const d = String(value.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function addDays(value: Date, amount: number) {
  const next = new Date(value.getFullYear(), value.getMonth(), value.getDate());
  next.setDate(next.getDate() + amount);
  return next;
}

export function PMSControlSnapshotProviderV9({ children }: { children: ReactNode }) {
  const [snapshot, setSnapshot] = useState<ControlSnapshotV9 | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    setError(null);
    try {
      const params = new URLSearchParams({ start: dateOnly(), end: dateOnly(addDays(new Date(), 31)) });
      const response = await fetch(`/core/api/v1/admin/pms/control-snapshot?${params}`, { cache: "no-store" });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : `Snapshot HTTP ${response.status}`);
      if (body.complete !== true || !Array.isArray(body.rooms) || !Array.isArray(body.reservations) || !Array.isArray(body.tasks)) {
        throw new Error("Resort Core вернул неполный V9 control snapshot");
      }
      setSnapshot(body as ControlSnapshotV9);
    } catch (cause) {
      setSnapshot(null);
      setError(cause instanceof Error ? cause.message : "V9 control snapshot недоступен");
    } finally {
      setRefreshing(false);
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => { void refresh(); }, 30_000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const value = useMemo(() => ({ snapshot, loading, refreshing, error, refresh }), [snapshot, loading, refreshing, error, refresh]);
  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function usePMSControlSnapshotV9() {
  const value = useContext(Context);
  if (!value) throw new Error("usePMSControlSnapshotV9 must be used inside PMSControlSnapshotProviderV9");
  return value;
}
