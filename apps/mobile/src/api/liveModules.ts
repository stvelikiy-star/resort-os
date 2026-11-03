import { useMemo } from 'react';
import { useSession } from '../state/session';
import { parseHotelAddress } from './hotels';
import { ApiError } from './types';

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
function encoded(id: string) { return encodeURIComponent(id); }
function list<T>(payload: unknown): T[] {
  if (!payload || typeof payload !== 'object' || !Array.isArray((payload as { items?: unknown }).items)) {
    throw new ApiError('UNKNOWN', 'Invalid list response');
  }
  return (payload as { items: T[] }).items;
}
export function createLiveModules(baseUrl: string, transport: typeof fetch = fetch) {
  const parsed = parseHotelAddress(baseUrl);
  if (!parsed.ok) throw new Error('HTTPS hotel origin required');
  const root = parsed.baseUrl;
  async function request<T>(method: 'GET' | 'POST' | 'PATCH', path: string, body?: unknown): Promise<T> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), method === 'GET' ? 15000 : 25000);
    let response: Response;
    try {
      response = await transport(root + path, {
        method, credentials: 'include', signal: controller.signal,
        headers: { Accept: 'application/json', ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    } catch {
      throw new ApiError('OFFLINE', 'Hotel connection unavailable');
    } finally {
      clearTimeout(timeout);
    }
    if (!response.ok) {
      const code = response.status === 401 ? 'UNAUTHORIZED' : response.status === 403 ? 'FORBIDDEN'
        : response.status === 404 ? 'NOT_FOUND' : response.status === 409 ? 'CONFLICT'
        : response.status === 400 || response.status === 422 ? 'BAD_REQUEST' : 'UNKNOWN';
      throw new ApiError(code, 'HTTP ' + response.status);
    }
    if (response.status === 204) return undefined as T;
    try { return await response.json() as T; }
    catch { throw new ApiError('UNKNOWN', 'Invalid hotel API response'); }
  }
  const p = '/api/v1';
  return {
    dashboard: () => request<Dashboard>('GET', p + '/admin/dashboard'),
    reception: async () => {
      const value = await request<ReceptionList>('GET', p + '/admin/reception/reservations');
      if (!value || !Array.isArray(value.items)) throw new ApiError('UNKNOWN', 'Invalid reception response');
      return value;
    },
    reservation: (id: string) => request<Record<string, unknown>>('GET', p + '/admin/reception/reservations/' + encoded(id)),
    checkIn: (id: string) => request<unknown>('POST', p + '/admin/stays/reservations/' + encoded(id) + '/check-in'),
    checkOut: (id: string) => request<unknown>('POST', p + '/admin/stays/reservations/' + encoded(id) + '/check-out'),
    pmsGrid: async (start: string, end: string) => {
      const value = await request<Grid>('GET', p + '/pms/grid?start=' + encoded(start) + '&end=' + encoded(end));
      if (!value || !Array.isArray(value.rooms)) throw new ApiError('UNKNOWN', 'Invalid PMS grid');
      return value;
    },
    conversations: async (needsReply?: boolean) => list<Conversation>(await request('GET', p + '/admin/inbox/conversations?limit=150' + (needsReply ? '&needs_reply=true' : ''))),
    conversation: async (id: string) => {
      const value = await request<ConversationDetail>('GET', p + '/admin/inbox/conversations/' + encoded(id));
      if (!value?.conversation || !Array.isArray(value.messages)) throw new ApiError('UNKNOWN', 'Invalid conversation');
      return value;
    },
    claimConversation: (id: string) => request<unknown>('POST', p + '/admin/inbox/conversations/' + encoded(id) + '/claim'),
    conversationStatus: (id: string, status: ConversationStatus) => request<unknown>('PATCH', p + '/admin/inbox/conversations/' + encoded(id) + '/status', { status }),
    internalNote: (id: string, text: string) => request<unknown>('POST', p + '/admin/inbox/conversations/' + encoded(id) + '/notes', { text }),
    // WhatsApp sending is intentionally not exposed: the current backend send-text is Telegram-only.
    kitchenOrders: async () => list<KitchenOrder>(await request('GET', p + '/kitchen/orders?status=ACTIVE')),
    kitchenStatus: (id: string, status: KitchenStatus) => request<unknown>('PATCH', p + '/kitchen/orders/' + encoded(id) + '/status', { status }),
    diningFloor: () => request<DiningFloor>('GET', p + '/dining/floor'),
    claimWaiterOrder: (id: string, waiterId: string) => request<unknown>('PATCH', p + '/dining/orders/' + encoded(id) + '/waiter', { waiter_id: waiterId }),
    assistantCapabilities: () => request<Record<string, unknown>>('GET', p + '/assistant/capabilities'),
  };
}
export function useLiveModules() {
  const { hotel, api } = useSession();
  return useMemo(() => hotel && api?.mode === 'LIVE' ? createLiveModules(hotel.baseUrl) : null, [hotel?.id, hotel?.baseUrl, api?.mode]);
}

/** Hotel-local calendar dates for the occupancy grid; do not use UTC toISOString(). */
export function localDate(offset = 0): string {
  const d = new Date(); d.setDate(d.getDate() + offset);
  return [d.getFullYear(), String(d.getMonth() + 1).padStart(2, '0'), String(d.getDate()).padStart(2, '0')].join('-');
}
