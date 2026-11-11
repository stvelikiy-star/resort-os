import { kitchenRecipe, ingredientRequirements } from './kitchenRecipes';
import type { KitchenRecipe, IngredientRequirements, RecipeInput } from './kitchenRecipes';
import { clientSessionGuard } from './unauthorizedSession';
import { useMemo } from 'react';
import { useSession } from '../state/session';
import { isTrustedHotelOrigin } from './hotels';
import { createHotelHttpClient, HttpMethod } from './http';
import { ApiError } from './types';
import type { AuthMode } from './types';
import { safeRouteId, safeIsoDate } from './routeId';
import { diningStaysResponse, diningStayEntitlementsResponse, diningMealPlanAck, diningProductionSnapshotsResponse, stayAck, kitchenStatusAck, conversationStatusAck, conversationClaimAck, noteAck, waiterClaimAck, objectResponse, kitchenOrdersResponse, diningFloorResponse, assistantCapabilitiesResponse, assistantAnswerResponse, receptionResponse, dashboardResponse, gridResponse, inboxListResponse, conversationResponse, bookingPreviewResponse, bookingCommitResponse, holdListResponse, holdCreateResponse, holdReleaseResponse, financeSummaryResponse } from './contractValidation';
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
  period_payments: { received_kgs: number; pending_created_kgs: number; received_count: number;
    pending_created_count?: number; failed_count?: number; cancelled_count?: number };
  receivables_snapshot: { outstanding_kgs: number; debtor_count: number;
    checked_out_count?: number; checked_out_kgs?: number; in_house_count?: number; in_house_kgs?: number;
    pre_arrival_count?: number; pre_arrival_kgs?: number };
  active_reservations_snapshot: { reservation_count: number; outstanding_kgs: number;
    booked_total_kgs?: number; received_kgs?: number };
  /** Optional to support older server versions. Current RC409 supplies all of these.
   * Missing fields must be omitted from UI, NEVER replaced by invented zero values. */
  received_by_method?: { method: string; amount_kgs: number; payment_count: number }[];
  received_by_day?: { local_date: string; amount_kgs: number; payment_count: number }[];
  awaiting_prepayment_snapshot?: { request_count: number; required_kgs: number;
    received_kgs: number; remaining_kgs: number };
  refunded_snapshot_all_time?: { amount_kgs: number; payment_count: number };
  finance_exceptions?: { snapshot: { overpaid_count: number; overpaid_kgs: number;
    cancelled_with_received_count: number; cancelled_with_received_kgs: number } };
  debtors?: { reservation_id: string; booking_number: string; status: string;
    guest_name?: string | null; room_code?: string | null; remaining_kgs: number }[];
  recent_payments?: { id: string; amount_kgs: number; method: string; status: string;
    booking_number?: string | null; guest_name?: string | null }[];
}
export interface AssistantMessage { role: 'user' | 'assistant'; content: string }
export interface AssistantCapabilities { configured: boolean; read_only: boolean; can_mutate: boolean; live_read_only: boolean; role: string; property_code: string }
export interface AssistantAnswer { answer: string; read_only: true; live_context_available: boolean; hotel_rules_version: number; property_code: string; role: string; current_screen: string }
export type KitchenStatus = 'NEW' | 'ACCEPTED' | 'COOKING' | 'READY' | 'SERVED' | 'CANCELLED';
export interface KitchenOrderItem {
  id?: string; name?: string; name_ru?: string; name_kg?: string;
  name_en?: string; name_kz?: string | null; quantity?: number;
}
export interface KitchenOrder {
  id: string; order_number: string; status: KitchenStatus;
  table_code: string | null; room_code: string | null; total_kgs: number;
  source?: string; meal_type?: string | null; guest_count?: number;
  notes: string | null; items: KitchenOrderItem[];
}
/** GET /api/v1/dining/production-snapshots: explicit *included* portions,
 * separate from à-la-carte orders. A frozen baseline is never silently rewritten. */
export const KITCHEN_MENU_CATEGORIES = ['BREAKFAST', 'SOUP', 'SALAD', 'MAIN', 'SIDE', 'DESSERT', 'DRINK'] as const;
export type KitchenMenuDraft = {
  code: string;
  category: typeof KITCHEN_MENU_CATEGORIES[number];
  name_ru: string;
  name_kg: string;
  name_en: string;
  name_kz: string;
  price_kgs: number;
};

export interface KitchenProductionMenuItem {
  recipe?: KitchenRecipe | null;
  id: string; code: string; category: string;
  name_ru: string; name_kg: string; name_en: string; name_kz: string;
}
export interface KitchenProductionTarget {
  id: string; menu_item_id: string; service_date: string; meal_type: string;
  planned_quantity: number; prepared_quantity: number; remaining_quantity: number;
  name_ru: string; name_kg: string; name_en: string; name_kz: string; notes: string | null;
  updated_at: string;
}
export interface KitchenProductionTargets {
  from_date: string; through_date: string; items: KitchenProductionTarget[];
  ingredient_requirements?: IngredientRequirements;
}
export type KitchenProductionInput = {
  menu_item_id: string; service_date: string;
  meal_type: 'BREAKFAST' | 'LUNCH' | 'DINNER' | 'OTHER';
  planned_quantity: number; prepared_quantity: number;
};

export interface DiningProductionSnapshotMeal {
  service_date: string; meal_type: 'BREAKFAST' | 'LUNCH' | 'DINNER';
  current_adult_portions: number; current_child_portions: number;
  current_total_portions: number; current_entitlement_count: number;
  /** Newer Core: breakdown of verified meal portions by checked-in vs pending stays.
   * Optional until the matching server candidate is deployed; never infer it. */
  current_checked_in_adult_portions?: number; current_checked_in_child_portions?: number;
  current_checked_in_total_portions?: number; current_checked_in_stay_count?: number;
  current_expected_arrival_adult_portions?: number; current_expected_arrival_child_portions?: number;
  current_expected_arrival_total_portions?: number; current_expected_arrival_stay_count?: number;
  state: 'OPEN' | 'FROZEN'; cutoff_status: 'UNCONFIGURED' | 'BEFORE_CUTOFF' | 'CUTOFF_REACHED';
  frozen_total_portions: number | null; delta_total_portions: number | null;
  changed_since_snapshot: boolean; meal_start: string | null; cutoff_at: string | null;
}
export interface DiningProductionSnapshotDay {
  service_date: string; meals: DiningProductionSnapshotMeal[];
  /** Number of distinct stays/bookings with included meals, NOT unique guests. */
  checked_in_stays_with_meals?: number; expected_arrival_stays_with_meals?: number;
}
export interface DiningProductionSnapshots { from_date: string; through_date: string; days: DiningProductionSnapshotDay[] }
export interface DiningStay {
  stay_id: string; stay_status: string; reservation_id: string; reservation_status: string;
  booking_number: string; check_in: string; check_out: string;
  adults: number; children: number; guest_name: string;
  room_code: string | null; entitlement_count: number;
}
export interface DiningStays { local_date: string; items: DiningStay[] }
export type MealType = 'BREAKFAST' | 'LUNCH' | 'DINNER';
export interface DiningEntitlement {
  id: string; stay_id: string; service_date: string; meal_type: MealType;
  adult_portions: number; child_portions: number;
  status: 'ACTIVE' | 'CANCELLED'; notes: string | null;
}
export interface DiningStayEntitlements {
  stay: { id: string; booking_number: string; check_in: string; check_out: string; guest_name: string; room_code: string | null };
  items: DiningEntitlement[];
}
export interface MealPlanDraft {
  from_date: string; through_date: string; meals: MealType[];
  adult_portions: number; child_portions: number; notes?: string | null; replace_range: false;
}
export interface MealPlanAck {
  stay_id: string; updated_items: number; meals: MealType[];
  from_date: string; through_date: string; adult_portions: number; child_portions: number;
}
export const AGENT_SERVICES = ['TRANSFER', 'MEALS', 'PARKING', 'SAUNA', 'BILLIARDS', 'EXCURSIONS'] as const;
export type AgentServiceCode = typeof AGENT_SERVICES[number];

export interface WaiterMenuItem {
  id: string;
  name_ru: string;
  name_kg: string;
  name_en: string;
  name_kz: string;
  price_kgs: number;
}
export interface DiningFloor {
  tables: { id: string; code: string; name: string; status: string; seats: number }[];
  orders: { id: string; order_number: string; status: string; table_code: string | null;
    room_code: string | null; waiter_id: string | null; waiter_name: string | null }[];
}
export type ReceptionGuestRequest = {
  id: string;
  title: string;
  description: string | null;
  room_code: string | null;
  service_date: string | null;
  service_time: string | null;
  assigned_to_id: string | null;
  status: 'OPEN' | 'IN_PROGRESS';
};

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
    receptionGuestRequests: async (): Promise<ReceptionGuestRequest[]> => {
      reviewGate();
      const queue = objectResponse(await request<unknown>('GET', p + '/ops/guest-requests?status=ACTIVE&limit=200'), 'guest requests');
      if (!Array.isArray(queue.items)) throw new ApiError('UNKNOWN', 'Invalid guest request queue');
      return queue.items.map(value => {
        const item = objectResponse(value, 'guest request');
        const nullableString = (field: string): string | null => {
          const value = item[field];
          if (value === null || typeof value === 'string') return value;
          throw new ApiError('UNKNOWN', 'Invalid guest request field: ' + field);
        };
        if (typeof item.id !== 'string' || typeof item.title !== 'string' ||
            (item.status !== 'OPEN' && item.status !== 'IN_PROGRESS')) {
          throw new ApiError('UNKNOWN', 'Invalid guest request');
        }
        return {
          id: safeRouteId(item.id), title: item.title, status: item.status,
          description: nullableString('description'), room_code: nullableString('room_code'),
          service_date: nullableString('service_date'), service_time: nullableString('service_time'),
          assigned_to_id: nullableString('assigned_to_id'),
        };
      });
    },
    updateReceptionGuestRequest: async (id: string, action: 'claim' | 'complete', userId: string) => {
      reviewGate();
      const key = safeRouteId(id);
      const result = objectResponse(await request<unknown>('POST', p + '/ops/guest-requests/' + key + '/' + action), 'guest request action');
      const status = action === 'claim' ? 'IN_PROGRESS' : 'DONE';
      if (result.id !== key || result.status !== status ||
          (action === 'claim' && result.assigned_to_id !== userId)) {
        throw new ApiError('UNKNOWN', 'Invalid guest request acknowledgement');
      }
      return status;
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
    diningProductionSnapshots: async (from?: string, through?: string): Promise<DiningProductionSnapshots> => {
      reviewGate();
      // By default the backend uses the HOTEL-local date, not the phone timezone.
      const query = from && through ? '?from_date=' + safeIsoDate(from) + '&through_date=' + safeIsoDate(through) : '';
      return diningProductionSnapshotsResponse(await request<unknown>('GET', p + '/dining/production-snapshots' + query));
    },
    addAgentGuestService: async (reservation: string, serviceCode: AgentServiceCode) => {
      reviewGate();
      const reservationId = safeRouteId(reservation);
      const task = objectResponse(await request<unknown>('POST', p + '/admin/guest-services', {
        reservation_id: reservationId, service_code: serviceCode,
      }), 'guest service');
      if (typeof task.id !== 'string' || task.reservation_id !== reservationId || task.service_code !== serviceCode) {
        throw new ApiError('UNKNOWN', 'Invalid guest service acknowledgement');
      }
    },
    waiterMenu: async (): Promise<WaiterMenuItem[]> => {
      reviewGate();
      const menu = objectResponse(await request<unknown>('GET', p + '/kitchen/menu'), 'waiter menu');
      if (!Array.isArray(menu.items)) throw new ApiError('UNKNOWN', 'Invalid waiter menu');
      return menu.items.map(value => {
        const item = objectResponse(value, 'menu item');
        const { id, name_ru, name_kg, name_en, name_kz, price_kgs } = item;
        if (typeof id !== 'string' || typeof name_ru !== 'string' || typeof name_kg !== 'string' ||
          typeof name_en !== 'string' || typeof name_kz !== 'string' ||
          typeof price_kgs !== 'number' || !Number.isSafeInteger(price_kgs) || price_kgs < 0) {
          throw new ApiError('UNKNOWN', 'Invalid waiter menu item');
        }
        return item.is_active === true && item.is_draft === false
          ? { id: safeRouteId(id), name_ru, name_kg, name_en, name_kz, price_kgs } : null;
      }).filter((item): item is WaiterMenuItem => item !== null);
    },
    createDiningTable: async (table: { code: string; name: string; seats: number }) => {
      reviewGate();
      const result = objectResponse(await request<unknown>('POST', p + '/kitchen/tables', table), 'table');
      if (typeof result.id !== 'string' || result.code !== table.code) throw new ApiError('UNKNOWN', 'Invalid table acknowledgement');
    },
    createDiningTableOrder: async (table: string, items: { menu_item_id: string; quantity: number }[]) => {
      reviewGate();
      const result = objectResponse(await request<unknown>('POST', p + '/kitchen/orders', {
        source: 'TABLE', table_id: safeRouteId(table), items,
      }), 'table order');
      if (typeof result.id !== 'string' || result.status !== 'NEW') throw new ApiError('UNKNOWN', 'Invalid order acknowledgement');
    },
    kitchenProductionMenu: async (): Promise<KitchenProductionMenuItem[]> => {
      reviewGate();
      const payload = objectResponse(await request<unknown>('GET', p + '/kitchen/production-menu'), 'production menu');
      if (!Array.isArray(payload.items)) throw new ApiError('UNKNOWN', 'Invalid production menu');
      return payload.items.map(value => {
        const row = objectResponse(value, 'production menu item');
        for (const name of ['name_ru', 'name_kg', 'name_en', 'name_kz', 'code']) {
          if (typeof row[name] !== 'string') throw new ApiError('UNKNOWN', 'Invalid menu name');
        }
        return { id: safeRouteId(String(row.id)), code: String(row.code), category: String(row.category),
          name_ru: String(row.name_ru), name_kg: String(row.name_kg),
          name_en: String(row.name_en), name_kz: String(row.name_kz), recipe: kitchenRecipe(row.recipe) };
      });
    },
    kitchenProductionTargets: async (): Promise<KitchenProductionTargets> => {
      reviewGate();
      const payload = objectResponse(await request<unknown>('GET', p + '/kitchen/production-targets'), 'production targets');
      if (!Array.isArray(payload.items) || typeof payload.from_date !== 'string' ||
          typeof payload.through_date !== 'string') throw new ApiError('UNKNOWN', 'Invalid production targets');
      const items = payload.items.map(value => {
        const row = objectResponse(value, 'production target');
        for (const field of ['planned_quantity', 'prepared_quantity', 'remaining_quantity']) {
          if (!Number.isSafeInteger(row[field]) || Number(row[field]) < 0) throw new ApiError('UNKNOWN', 'Invalid production count');
        }
        return { ...row, id: safeRouteId(String(row.id)), menu_item_id: safeRouteId(String(row.menu_item_id)),
          service_date: safeIsoDate(String(row.service_date)) } as KitchenProductionTarget;
      });
      return { from_date: String(payload.from_date), through_date: String(payload.through_date), items,
        ingredient_requirements: ingredientRequirements(payload.ingredient_requirements) };
    },
    saveKitchenRecipe: async (menuItemId: string, input: RecipeInput): Promise<void> => {
      reviewGate();
      const response = objectResponse(await request<unknown>('PUT',
        p + '/kitchen/menu/' + safeRouteId(menuItemId) + '/recipe', input), 'recipe');
      const saved = kitchenRecipe(response.recipe);
      if (!saved || saved.version !== input.expected_version + 1) {
        throw new ApiError('UNKNOWN', 'Recipe acknowledgement mismatch');
      }
    },
    saveKitchenProductionTarget: async (target: KitchenProductionInput): Promise<void> => {
      reviewGate();
      if (!Number.isSafeInteger(target.planned_quantity) || target.planned_quantity < 0 ||
          target.planned_quantity > 10000 || !Number.isSafeInteger(target.prepared_quantity) ||
          target.prepared_quantity < 0 || target.prepared_quantity > target.planned_quantity) {
        throw new ApiError('BAD_REQUEST', 'Invalid planned/prepared servings');
      }
      const payload = { ...target, menu_item_id: safeRouteId(target.menu_item_id),
        service_date: safeIsoDate(target.service_date) };
      const result = objectResponse(await request<unknown>('PUT', p + '/kitchen/production-targets', payload), 'production target');
      if (result.planned_quantity !== payload.planned_quantity ||
          result.prepared_quantity !== payload.prepared_quantity ||
          result.remaining_quantity !== payload.planned_quantity - payload.prepared_quantity) {
        throw new ApiError('UNKNOWN', 'Production target acknowledgement mismatch');
      }
    },
    createKitchenMenuDraft: async (draft: KitchenMenuDraft) => {
      reviewGate();
      const item = objectResponse(await request<unknown>('POST', p + '/kitchen/menu', {
        ...draft, is_active: false, is_draft: true,
      }), 'menu draft');
      if (typeof item.id !== 'string' || item.is_draft !== true || item.code !== draft.code) {
        throw new ApiError('UNKNOWN', 'Menu draft could not be verified');
      }
      return item.id;
    },
    captureDiningProduction: async (day: string, meal: DiningProductionSnapshotMeal['meal_type']) => {
      reviewGate();
      const serviceDate = safeIsoDate(day);
      const path = p + '/dining/production-snapshots';
      await request<unknown>('POST', path, { service_date: serviceDate, meal_type: meal });
      const result = diningProductionSnapshotsResponse(await request<unknown>(
        'GET', path + '?from_date=' + serviceDate + '&through_date=' + serviceDate,
      ));
      if (!result.days.some(item => item.service_date === serviceDate &&
        item.meals.some(value => value.meal_type === meal && value.state === 'FROZEN'))) {
        throw new ApiError('UNKNOWN', 'Production snapshot could not be verified');
      }
    },
    diningStays: async (): Promise<DiningStays> => {
      reviewGate();
      return diningStaysResponse(await request<unknown>('GET', p + '/dining/stays'));
    },
    diningStayEntitlements: async (stayId: string): Promise<DiningStayEntitlements> => {
      reviewGate();
      return diningStayEntitlementsResponse(await request<unknown>(
        'GET', p + '/dining/stays/' + safeRouteId(stayId) + '/entitlements'), stayId);
    },
    diningMealPlan: async (stayId: string, draft: MealPlanDraft): Promise<MealPlanAck> => {
      reviewGate();
      if (!draft.meals.length || draft.meals.length > 3 ||
          new Set(draft.meals).size !== draft.meals.length ||
          draft.meals.some(m => !['BREAKFAST','LUNCH','DINNER'].includes(m)) ||
          !Number.isSafeInteger(draft.adult_portions) || draft.adult_portions < 0 ||
          !Number.isSafeInteger(draft.child_portions) || draft.child_portions < 0 ||
          draft.adult_portions + draft.child_portions < 1 || draft.replace_range !== false) {
        throw new ApiError('BAD_REQUEST', 'Invalid included-meal plan');
      }
      const payload = { ...draft, from_date: safeIsoDate(draft.from_date), through_date: safeIsoDate(draft.through_date) };
      if (payload.from_date > payload.through_date || payload.from_date === '' || payload.through_date === '') {
        throw new ApiError('BAD_REQUEST', 'Invalid meal plan dates');
      }
      return diningMealPlanAck(await request<unknown>(
        'PUT', p + '/dining/stays/' + safeRouteId(stayId) + '/meal-plan', payload), stayId, draft);
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