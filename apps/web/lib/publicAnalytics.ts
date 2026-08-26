type AnalyticsValue = string | number | boolean | null;

type PublicAnalyticsPayloads = {
  booking_search_started: {
    adults: number;
    children: number;
  };
  booking_search_succeeded: {
    nights: number;
    adults: number;
    children: number;
    room_type_count: number;
    available_room_count: number;
    sellable_type_count: number;
  };
  booking_search_failed: {
    adults: number;
    children: number;
  };
  booking_room_selected: {
    room_type_code: string;
    sellable: boolean;
    quoted_total_kgs: number | null;
    available_count: number;
  };
  booking_request_started: {
    room_type_code: string;
    nights: number;
    adults: number;
    children: number;
    quoted_total_kgs: number | null;
  };
  booking_request_succeeded: {
    room_type_code: string;
    nights: number;
    adults: number;
    children: number;
    quoted_total_kgs: number | null;
  };
  booking_request_failed: {
    room_type_code: string;
    nights: number;
    adults: number;
    children: number;
    quoted_total_kgs: number | null;
  };
};

export type PublicAnalyticsEvent = keyof PublicAnalyticsPayloads;

type AnalyticsRecord = Record<string, AnalyticsValue> & {
  event: PublicAnalyticsEvent;
  event_time: string;
};

type AnalyticsWindow = Window & {
  dataLayer?: AnalyticsRecord[];
};

const ALLOWED_PAYLOAD_KEYS = {
  booking_search_started: ["adults", "children"],
  booking_search_succeeded: [
    "nights",
    "adults",
    "children",
    "room_type_count",
    "available_room_count",
    "sellable_type_count",
  ],
  booking_search_failed: ["adults", "children"],
  booking_room_selected: ["room_type_code", "sellable", "quoted_total_kgs", "available_count"],
  booking_request_started: ["room_type_code", "nights", "adults", "children", "quoted_total_kgs"],
  booking_request_succeeded: ["room_type_code", "nights", "adults", "children", "quoted_total_kgs"],
  booking_request_failed: ["room_type_code", "nights", "adults", "children", "quoted_total_kgs"],
} as const satisfies {
  [Event in PublicAnalyticsEvent]: readonly (keyof PublicAnalyticsPayloads[Event])[];
};

/**
 * Vendor-neutral public funnel events with a fail-closed privacy boundary.
 *
 * Only event-specific aggregate/commercial fields are accepted. Guest name,
 * phone, email, free-text notes, request ids and exact travel dates have no
 * allowed payload key and therefore cannot be emitted silently, including
 * when a future caller passes a wider object at runtime.
 */
export function trackPublicEvent<Event extends PublicAnalyticsEvent>(
  event: Event,
  payload: PublicAnalyticsPayloads[Event],
) {
  if (typeof window === "undefined") return;

  const allowedKeys = new Set<string>(ALLOWED_PAYLOAD_KEYS[event] as readonly string[]);
  const safePayload: Record<string, AnalyticsValue> = {};

  for (const [key, value] of Object.entries(payload as Record<string, unknown>)) {
    if (!allowedKeys.has(key)) {
      throw new Error(`Public analytics rejected non-allowlisted field: ${key}`);
    }
    if (value !== null && typeof value !== "string" && typeof value !== "number" && typeof value !== "boolean") {
      throw new Error(`Public analytics rejected non-scalar field: ${key}`);
    }
    safePayload[key] = value;
  }

  const record: AnalyticsRecord = {
    ...safePayload,
    event,
    event_time: new Date().toISOString(),
  };

  const analyticsWindow = window as AnalyticsWindow;
  analyticsWindow.dataLayer ??= [];
  analyticsWindow.dataLayer.push(record);
  window.dispatchEvent(new CustomEvent("three-crowns:analytics", { detail: record }));
}
