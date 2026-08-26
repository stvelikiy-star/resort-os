export type PublicAnalyticsEvent =
  | "booking_search_started"
  | "booking_search_succeeded"
  | "booking_search_failed"
  | "booking_room_selected"
  | "booking_request_started"
  | "booking_request_succeeded"
  | "booking_request_failed";

type PublicAnalyticsPayload = Record<string, string | number | boolean | null | undefined>;
type AnalyticsRecord = PublicAnalyticsPayload & { event: PublicAnalyticsEvent; event_time: string };

type AnalyticsWindow = Window & {
  dataLayer?: AnalyticsRecord[];
};

/**
 * Vendor-neutral, privacy-safe public funnel events.
 *
 * Rules:
 * - never pass guest name, phone, email, free-text notes or request ids;
 * - when GTM/another consumer is installed later it can read window.dataLayer;
 * - local integrations can subscribe to `three-crowns:analytics` today.
 */
export function trackPublicEvent(event: PublicAnalyticsEvent, payload: PublicAnalyticsPayload = {}) {
  if (typeof window === "undefined") return;

  const record: AnalyticsRecord = {
    event,
    event_time: new Date().toISOString(),
    ...payload,
  };

  const analyticsWindow = window as AnalyticsWindow;
  analyticsWindow.dataLayer ??= [];
  analyticsWindow.dataLayer.push(record);
  window.dispatchEvent(new CustomEvent("three-crowns:analytics", { detail: record }));
}
