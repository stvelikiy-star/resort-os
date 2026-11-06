import { clientSessionGuard } from './unauthorizedSession';
import { useMemo } from 'react';
import { useSession } from '../state/session';
import { isTrustedHotelOrigin } from './hotels';
import { createHotelHttpClient, HttpMethod } from './http';
import { ApiError } from './types';
import type { AuthMode } from './types';
import { safeRouteId, safeIsoDate } from './routeId';
import { stayAck, kitchenStatusAck, conversationStatusAck, conversationClaimAck, noteAck, waiterClaimAck, objectResponse, kitchenOrdersResponse, diningFloorResponse, assistantCapabilitiesResponse, assistantAnswerResponse, receptionResponse, dashboardResponse, gridResponse, inboxListResponse, conversationResponse, bookingPreviewResponse, bookingCommitResponse, holdListResponse, holdCreateResponse, holdReleaseResponse, financeSummaryResponse } from './contractValidation';
import { CONFIRMED_BACKEND_FEATURES } from './features';

export type WhatsAppDeliveryStatus = 'QUEUED' | 'SENT' | 'DELIVERED' | 'READ';
export interface OutboundCapabilities { whatsapp: { configured: boolean; human_only: boolean; queued_only: boolean; max_text_length: number } }
export interface OutboundAck { conversation_id: string; message_id: string; delivery_status: WhatsAppDeliveryStatus; idempotent_replay: boolean; counts_as_response: boolean; auto_sent: false }
export type ConversationStatus = 'OPEN' | 'WAITING_GUEST' | 'WAITING_STAFF' | 'RESOLVED' | 'ARCHIVED';
export interface Conversation {
  id: string; channel_kind: string; channel_name: string | null; status: ConversationStatus;
  contact_name: string | null; contact_phone: string | null; assigned_to_id: string | null;
  assigned_to_name: string | null; last_message_text: string | null; last_message_at: string | null;
  needs_reply: boolean; waiting_seconds: number | null;
}
export interface ConversationMessage {
  id: string; direction: 'INBOUND' | 'OUTBOUND' | 'INTERNAL'; text: string | null;
  created_at: string; delivery_status?: string | null;
}
export interface ConversationDetail { conversation: Conversation; messages: ConversationMessage[] }
export interface ReceptionReservation {
  id: string; bookingNumber: string; status: string; checkIn: string; checkOut: string;
  firstName: string | null; phone: string | null; room_code: string | null;
  room_state: string | null; totalKgs: number; paidKgs: number; remainingKgs: number;
}
export interface ReceptionList { local_date: string; items: ReceptionReservation[] }
export interface GridBlock {
  id: string; type: string; start: string; end: string; reservation_id: string | null;
  booking_number: string | null; guest_name: string | null;
}
export interface GridRoom {
  id: string; code: string; name: string | null; room_type_name: string;
  operational_state: string; blocks: GridBlock[];
}
export interface Grid { property: string; start: string; end: string; rooms: GridRoom[] }
export interface Dashboard {
  property: { name: string; local_date: string; currency: string };
  rooms: { total: number; clean: number; dirty: number; in_inspection: number; tech_block: number };
  stays: { occupancy_percent: number; occupied_rooms: number; arrivals_today: number; departures_today: number };
  communications: { active: number; needs_reply: number };
  finance: { confirmed_payments_today_kgs: number; active_reservations_remaining_kgs: number };
  tasks: { urgent_active: number; housekeeping_active: number; maintenance_active: number };
  today: { arrivals: { id: string; booking_number: string; guest_name: string | null; room_code: string | null }[];
    departures: { id: string; booking_number: string; guest_name: string | null; room_code: string | null }[] };
  attention_tasks: { id: string; title: string; priority: string; room_code: string | null }[];
}
export interface BookingPreview {
  room: { id: string; code: string; room_type_name: string };
  check_in: string; check_out: string; nights: number; can_commit: boolean;
  conflicts: { block_type: string; start: string; end: string }[];
  pricing: { source: 'CORE_RATE' | 'MANAGER_OVERRIDE'; sellable: boolean; total_kgs: number | null; discount_percent: number; reason?: string | null };
}
export interface ScheduleSegment { room_id: string; start: string; end: string }
export interface SchedulePreview {
  reservation: { version: string }; can_commit: boolean;
  proposed_check_in: string; proposed_check_out: string;
  conflicts: unknown[]; pricing: { suggested_total_kgs: number | null; delta_kgs: number | null };
}
export interface ScheduleCommitAck { ok: true; reservation_id: string; version: string; check_in: string; check_out: string }
export interface BookingDraft {
  room_id: string; check_in: string; check_out: string; adults: number; children: number;
  guest_phone: string;
}
export interface BookingCommit extends BookingDraft {
  guest_name: string; phone: string; expected_total_kgs: number; expected_pricing_source: 'CORE_RATE' | 'MANAGER_OVERRIDE';
}
export interface Hold {
  id: string; roomId: string; checkIn: string; checkOut: string; guestName: string; expiresAt: string;
}
export interface FinanceSummary {
  range: { from: string; to: string; currency: string };
  period_payments: { received_kgs: number; pending_created_kgs: number; received_count: number };
  receivables_snapshot: { outstanding_kgs: number; debtor_count: number };
  active_reservations_snapshot: { reservation_count: number; outstanding_kgs: number };
}
export interface AssistantMessage { role: 'user' | 'assistant'; content: string }
export interface AssistantCapabilities { configured: boolean; read_only: boolean; can_mutate: boolean; live_read_only: boolean; role: string; property_code: string }
export interface AssistantAnswer { answer: string; read_only: true; live_context_available: boolean; hotel_rules_version: number; property_code: string; role: string; current_screen: string }
export type KitchenStatus = 'NEW' | 'ACCEPTED' | 'COOKING' | 'READY' | 'SERVED' | 'CANCELLED';
export interface KitchenOrder {
  id: string; order_number: string; status: KitchenStatus;
  table_code: string | null; room_code: string | null; total_kgs: number;
  notes: string | null; items: { id?: string; name?: string; quantity?: number }[];
}
export interface DiningFloor {
  tables: { id: string; code: string; name: string; status: string; seats: number }[];
  orders: { id: string; order_number: string; status: string; table_code: string | null;
    room_code: string | null; waiter_id: string | null; waiter_name: string | null }[];
}
export function createLiveModules(baseUrl: string, transport: typeof fetch = fetch, serverAuthMode: AuthMode | null = null, sessionIsActive?: () => boolean) {
  const http = createHotelHttpClient(baseUrl, transport, sessionIsActive);
  const request = <T,>(method: HttpMethod, path: string, body?: unknown, idempotencyKey?: string) => http.request<T>(method, path, body, idempotencyKey);
  const p = '/api/v1';
  const reviewGate = () => {
    if (serverAuthMode === 'shared_auth_preview') {
      // The reviewed server boundary returns 503 for these modules.
      throw new ApiError('UNKNOWN', 'Workspace is unavailable in shared PMS staging');
    }
  };
  return {
    dashboard: async () => dashboardResponse(await request<unknown>('GET', p + '/admin/dashboard')),
    financeSummary: async (from: string, to: string): Promise<FinanceSummary> => {
      // Server OWNER/MANAGER + FINANCE permission guards remain authoritative;
      // shared_auth_preview explicitly allows this read. No 503 bypass.
      return financeSummaryResponse(await request<unknown>('GET', p + '/admin/finance/summary?from_date=' + safeIsoDate(from) + '&to_date=' + safeIsoDate(to)));
    },
    reception: async () => {
      const value = await request<ReceptionList>('GET', p + '/admin/reception/reservations');
      return receptionResponse(value);
    },
    reservation: async (id: string) => objectResponse(await request<unknown>('GET', p + '/admin/reception/reservations/' + safeRouteId(id)), 'reservation'),
    checkIn: async (id: string) => stayAck(await request<unknown>('POST', p + '/admin/stays/reservations/' + safeRouteId(id) + '/check-in'), id, 'CHECKED_IN'),
    checkOut: async (id: string) => stayAck(await request<unknown>('POST', p + '/admin/stays/reservations/' + safeRouteId(id) + '/check-out'), id, 'CHECKED_OUT'),
    schedulePreview: async (id: string, segments: ScheduleSegment[]): Promise<SchedulePreview> => {
      if (segments.length !== 1) throw new ApiError('BAD_REQUEST', 'Only one-room date changes are enabled on mobile');
      const segment = segments[0];
      if (segment.start >= segment.end) throw new ApiError('BAD_REQUEST', 'Invalid reservation dates');
      const payload = { segments: [{ room_id: safeRouteId(segment.room_id), start: safeIsoDate(segment.start), end: safeIsoDate(segment.end) }] };
      const value = await request<unknown>('POST', p + '/admin/pms/reservations/' + safeRouteId(id) + '/schedule/preview', payload);
      if (!value || typeof value !== 'object') throw new ApiError('UNKNOWN', 'Invalid schedule preview');
      const x = value as Record<string, unknown>, reservation = x.reservation as Record<string, unknown> | null;
      if (!reservation || typeof reservation.version !== 'string' || typeof x.can_commit !== 'boolean' ||
          !Array.isArray(x.conflicts) || typeof x.proposed_check_in !== 'string' || typeof x.proposed_check_out !== 'string' ||
          !x.pricing || typeof x.pricing !== 'object')
        throw new ApiError('UNKNOWN', 'Invalid schedule preview');
      return value as SchedulePreview;
    },
    scheduleCommit: async (id: string, segments: ScheduleSegment[], version: string): Promise<ScheduleCommitAck> => {
      if (segments.length !== 1 || typeof version !== 'string' || version.length < 10 || version.length > 80)
        throw new ApiError('BAD_REQUEST', 'Invalid reservation schedule');
      const segment = segments[0];
      if (segment.start >= segment.end) throw new ApiError('BAD_REQUEST', 'Invalid reservation dates');
      const payload = {
        segments: [{ room_id: safeRouteId(segment.room_id), start: safeIsoDate(segment.start), end: safeIsoDate(segment.end) }],
        expected_version: version,
      };
      const value = await request<unknown>('POST', p + '/admin/pms/reservations/' + safeRouteId(id) + '/schedule/commit', payload);
      if (!value || typeof value !== 'object') throw new ApiError('UNKNOWN', 'Invalid schedule commit acknowledgement');
      const x = value as Record<string, unknown>;
      if (x.ok !== true || x.reservation_id !== id || typeof x.version !== 'string' ||
          typeof x.check_in !== 'string' || typeof x.check_out !== 'string')
        throw new ApiError('UNKNOWN', 'Invalid schedule commit acknowledgement');
      return value as ScheduleCommitAck;
    },
    bookingPreview: async (draft: BookingDraft) => bookingPreviewResponse(await request<unknown>('POST', p + '/admin/pms/reservations/new/preview', draft)),
    bookingCommit: async (draft: BookingCommit) => bookingCommitResponse(await request<unknown>('POST', p + '/admin/pms/reservations/new/commit', draft)),
    holds: async (): Promise<Hold[]> => {
      if (!CONFIRMED_BACKEND_FEATURES.pmsHolds) throw new ApiError('NOT_FOUND','HOLD API not accepted for mobile LIVE');
      // Actual SQL projection in pms_holds.py uses quoted camelCase columns,
      // NOT the snake_case format stated in the older handoff matrix.
      return holdListResponse(await request<unknown>('GET', p + '/admin/pms/holds'));
    },
    createHold: async (draft: {room_id: string;check_in: string;check_out: string;guest_name: string;guest_phone: string}) => {
      if (!CONFIRMED_BACKEND_FEATURES.pmsHolds) throw new ApiError('NOT_FOUND','HOLD API not accepted for mobile LIVE');
      // Never return a claimed 60-minute hold without the server's 201 ACK.
      return holdCreateResponse(await request<unknown>('POST', p + '/admin/pms/holds', draft));
    },
    releaseHold: async (id: string) => {
      if (!CONFIRMED_BACKEND_FEATURES.pmsHolds) throw new ApiError('NOT_FOUND','HOLD API not accepted for mobile LIVE');
      const key = safeRouteId(id);
      return holdReleaseResponse(await request<unknown>('DELETE', p + '/admin/pms/holds/' + key), key);
    },
    pmsGrid: async (start: string, end: string) => {
      const value = await request<Grid>('GET', p + '/pms/grid?start=' + safeIsoDate(start) + '&end=' + safeIsoDate(end));
      return gridResponse(value);
    },
    conversations: async (needsReply?: boolean) => {
      return inboxListResponse(await request('GET', p + '/admin/inbox/conversations?limit=150' + (needsReply ? '&needs_reply=true' : '')));
    },
    conversation: async (id: string) => {
      const value = await request<ConversationDetail>('GET', p + '/admin/inbox/conversations/' + safeRouteId(id));
      return conversationResponse(value);
    },
    claimConversation: async (id: string) => {
      return conversationClaimAck(await request<unknown>('POST', p + '/admin/inbox/conversations/' + safeRouteId(id) + '/claim'), id);
    },
    conversationStatus: async (id: string, status: ConversationStatus) => {
      return conversationStatusAck(await request<unknown>('PATCH', p + '/admin/inbox/conversations/' + safeRouteId(id) + '/status', { status }), id, status);
    },
    internalNote: async (id: string, text: string) => {
      return noteAck(await request<unknown>('POST', p + '/admin/inbox/conversations/' + safeRouteId(id) + '/notes', { text }), id);
    },
    // RC5/RC8 remain opt-in and server-gated. A server 403/503 is authoritative.
    outboundCapabilities: async (): Promise<OutboundCapabilities> => {
      const value = await request<unknown>('GET', p + '/admin/inbox/outbound-capabilities');
      if (!value || typeof value !== 'object') throw new ApiError('UNKNOWN', 'Invalid outbound capability response');
      const w = (value as Record<string, unknown>).whatsapp;
      if (!w || typeof w !== 'object') throw new ApiError('UNKNOWN', 'Missing WhatsApp capability');
      const x = w as Record<string, unknown>;
      if (typeof x.configured !== 'boolean' || typeof x.human_only !== 'boolean' || typeof x.queued_only !== 'boolean' || typeof x.max_text_length !== 'number')
        throw new ApiError('UNKNOWN', 'Unverified WhatsApp capability');
      return value as OutboundCapabilities;
    },
    sendWhatsAppText: async (id: string, text: string, key: string): Promise<OutboundAck> => {
      if (!text.trim() || text.length > 4096) throw new ApiError('BAD_REQUEST', 'Invalid message length');
      const value = await request<unknown>('POST', p + '/admin/inbox/conversations/' + safeRouteId(id) + '/send-text', { text: text.trim() }, key);
      if (!value || typeof value !== 'object') throw new ApiError('UNKNOWN', 'Unverified send acknowledgement');
      const ack = value as Record<string, unknown>;
      if (ack.conversation_id !== id || typeof ack.message_id !== 'string' || !['QUEUED','SENT','DELIVERED','READ'].includes(String(ack.delivery_status)) ||
          typeof ack.idempotent_replay !== 'boolean' || typeof ack.counts_as_response !== 'boolean' || ack.auto_sent !== false)
        throw new ApiError('UNKNOWN', 'Invalid message acknowledgement');
      return ack as unknown as OutboundAck;
    },
    kitchenOrders: async () => {
      reviewGate();
      return kitchenOrdersResponse(await request<unknown>('GET', p + '/kitchen/orders?status=ACTIVE'));
    },
    kitchenStatus: async (id: string, status: KitchenStatus) => {
      reviewGate();
      return kitchenStatusAck(await request<unknown>('PATCH', p + '/kitchen/orders/' + safeRouteId(id) + '/status', { status }), id, status);
    },
    diningFloor: async () => {
      reviewGate();
      return diningFloorResponse(await request<unknown>('GET', p + '/dining/floor'));
    },
    claimWaiterOrder: async (id: string, waiterId: string) => {
      reviewGate();
      return waiterClaimAck(await request<unknown>('PATCH', p + '/dining/orders/' + safeRouteId(id) + '/waiter', { waiter_id: safeRouteId(waiterId) }), id, waiterId);
    },
    assistantCapabilities: async () => {
      reviewGate();
      return assistantCapabilitiesResponse(await request<unknown>('GET', p + '/assistant/capabilities'));
    },
    assistantChat: async (messages: AssistantMessage[], locale: 'ru' | 'kg' | 'en' | 'kz', currentScreen: string) => {
      reviewGate();
      return assistantAnswerResponse(await request<unknown>('POST', p + '/assistant/chat', {
        messages: messages.slice(-10), locale, current_screen: currentScreen,
      }));
    },
  };
}
export function useLiveModules() {
  const { hotel, api, user, serverAuthMode } = useSession();
  // A connection URL is NOT an authenticated hotel identity. In the shared
  // multi-owner PMS a leftover OS cookie may belong to a DIFFERENT property.
  // Never issue a module request until /auth/me verified the selected session.
  // Recreate the module client whenever identity or its API instance changes,
  // so dependent screens invalidate old hotel data before issuing fresh reads.
  return useMemo(() =>
    hotel && user && api?.mode === 'LIVE' && isTrustedHotelOrigin(hotel.baseUrl)
      ? createLiveModules(hotel.baseUrl, fetch, serverAuthMode, clientSessionGuard(api)) : null,
    [hotel, api, user, serverAuthMode],
  );
}

/** Hotel-local calendar dates for the occupancy grid; do not use UTC toISOString(). */
export function localDate(offset = 0): string {
  const d = new Date(); d.setDate(d.getDate() + offset);
  return [d.getFullYear(), String(d.getMonth() + 1).padStart(2, '0'), String(d.getDate()).padStart(2, '0')].join('-');
}
