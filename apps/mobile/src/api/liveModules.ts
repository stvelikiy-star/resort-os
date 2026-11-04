import { useMemo } from 'react';
import { useSession } from '../state/session';
import { isTrustedHotelOrigin } from './hotels';
import { createHotelHttpClient, HttpMethod } from './http';
import { ApiError } from './types';
import type { AuthMode } from './types';
import { safeRouteId, safeIsoDate } from './routeId';
import { stayAck, kitchenStatusAck, conversationStatusAck, conversationClaimAck, noteAck, waiterClaimAck, objectResponse, kitchenOrdersResponse, diningFloorResponse, assistantCapabilitiesResponse, assistantAnswerResponse, receptionResponse, dashboardResponse, gridResponse, inboxListResponse, conversationResponse, bookingPreviewResponse, bookingCommitResponse, holdListResponse, holdCreateResponse, holdReleaseResponse } from './contractValidation';
import { CONFIRMED_BACKEND_FEATURES } from './features';

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
export function createLiveModules(baseUrl: string, transport: typeof fetch = fetch, serverAuthMode: AuthMode | null = null) {
  const http = createHotelHttpClient(baseUrl, transport);
  const request = <T,>(method: HttpMethod, path: string, body?: unknown) => http.request<T>(method, path, body);
  const p = '/api/v1';
  const reviewGate = () => {
    if (serverAuthMode === 'shared_auth_preview') {
      // The reviewed server boundary returns 503 for these modules.
      throw new ApiError('UNKNOWN', 'Workspace is unavailable in shared PMS staging');
    }
  };
  return {
    dashboard: async () => dashboardResponse(await request<unknown>('GET', p + '/admin/dashboard')),
    reception: async () => {
      const value = await request<ReceptionList>('GET', p + '/admin/reception/reservations');
      return receptionResponse(value);
    },
    reservation: async (id: string) => objectResponse(await request<unknown>('GET', p + '/admin/reception/reservations/' + safeRouteId(id)), 'reservation'),
    checkIn: async (id: string) => stayAck(await request<unknown>('POST', p + '/admin/stays/reservations/' + safeRouteId(id) + '/check-in'), id, 'CHECKED_IN'),
    checkOut: async (id: string) => stayAck(await request<unknown>('POST', p + '/admin/stays/reservations/' + safeRouteId(id) + '/check-out'), id, 'CHECKED_OUT'),
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
      reviewGate();
      return inboxListResponse(await request('GET', p + '/admin/inbox/conversations?limit=150' + (needsReply ? '&needs_reply=true' : '')));
    },
    conversation: async (id: string) => {
      reviewGate();
      const value = await request<ConversationDetail>('GET', p + '/admin/inbox/conversations/' + safeRouteId(id));
      return conversationResponse(value);
    },
    claimConversation: async (id: string) => {
      reviewGate();
      return conversationClaimAck(await request<unknown>('POST', p + '/admin/inbox/conversations/' + safeRouteId(id) + '/claim'), id);
    },
    conversationStatus: async (id: string, status: ConversationStatus) => {
      reviewGate();
      return conversationStatusAck(await request<unknown>('PATCH', p + '/admin/inbox/conversations/' + safeRouteId(id) + '/status', { status }), id, status);
    },
    internalNote: async (id: string, text: string) => {
      reviewGate();
      return noteAck(await request<unknown>('POST', p + '/admin/inbox/conversations/' + safeRouteId(id) + '/notes', { text }), id);
    },
    // No WhatsApp sending: current server outbound is not multi-tenant accepted.
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
      ? createLiveModules(hotel.baseUrl, fetch, serverAuthMode) : null,
    [hotel, api, user, serverAuthMode],
  );
}

/** Hotel-local calendar dates for the occupancy grid; do not use UTC toISOString(). */
export function localDate(offset = 0): string {
  const d = new Date(); d.setDate(d.getDate() + offset);
  return [d.getFullYear(), String(d.getMonth() + 1).padStart(2, '0'), String(d.getDate()).padStart(2, '0')].join('-');
}
