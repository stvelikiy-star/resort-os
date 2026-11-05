/**
 * Isolated, read-only showroom fixtures for the existing offline DEMO API.
 * NEVER use this module to fill a LIVE server response or claim live financials.
 * The demo account, hotel connection and every synthetic booking are marked DEMO.
 */
import type { Locale } from '../i18n';
import type { Room, Task } from './types';
import type {
  Conversation, ConversationDetail, Dashboard, DiningFloor, Grid, GridBlock,
  KitchenOrder, ReceptionList, ReceptionReservation,
} from './liveModules';

const labels: Record<Locale, {
  guestA: string; guestB: string; guestC: string; guestD: string;
  roomType: string; channelA: string; channelB: string;
  inboundA: string; outboundA: string; inboundB: string;
  dishA: string; dishB: string; note: string;
}> = {
  ru: {
    guestA: 'ДЕМО · Гость А', guestB: 'ДЕМО · Гость Б',
    guestC: 'ДЕМО · Гость В', guestD: 'ДЕМО · Гость Г',
    roomType: 'Номер', channelA: 'WhatsApp · ДЕМО', channelB: 'Сайт · ДЕМО',
    inboundA: 'Здравствуйте! Подскажите время заезда.',
    outboundA: 'ДЕМО: время заезда уточняется у администратора.',
    inboundB: 'ДЕМО: можно заказать дополнительные полотенца?',
    dishA: 'Овощной салат', dishB: 'Чай', note: 'Пример заказа — не отправлен на кухню',
  },
  kg: {
    guestA: 'ДЕМО · Конок А', guestB: 'ДЕМО · Конок Б',
    guestC: 'ДЕМО · Конок В', guestD: 'ДЕМО · Конок Г',
    roomType: 'Бөлмө', channelA: 'WhatsApp · ДЕМО', channelB: 'Сайт · ДЕМО',
    inboundA: 'Саламатсызбы! Катталуу убактысын айта аласызбы?',
    outboundA: 'ДЕМО: катталуу убактысын администратордон тактайбыз.',
    inboundB: 'ДЕМО: кошумча сүлгү алсак болобу?',
    dishA: 'Жашылча салаты', dishB: 'Чай', note: 'Үлгү буйрутма — ашканага жөнөтүлгөн жок',
  },
  en: {
    guestA: 'DEMO · Guest A', guestB: 'DEMO · Guest B',
    guestC: 'DEMO · Guest C', guestD: 'DEMO · Guest D',
    roomType: 'Room', channelA: 'WhatsApp · DEMO', channelB: 'Website · DEMO',
    inboundA: 'Hello! What time is check-in?',
    outboundA: 'DEMO: our team will confirm the check-in time.',
    inboundB: 'DEMO: may we request extra towels?',
    dishA: 'Vegetable salad', dishB: 'Tea', note: 'Sample order — not sent to a kitchen',
  },
  kz: {
    guestA: 'ДЕМО · Қонақ А', guestB: 'ДЕМО · Қонақ Ә',
    guestC: 'ДЕМО · Қонақ Б', guestD: 'ДЕМО · Қонақ В',
    roomType: 'Бөлме', channelA: 'WhatsApp · ДЕМО', channelB: 'Сайт · ДЕМО',
    inboundA: 'Сәлеметсіз бе! Қонақүйге кіру уақытын айта аласыз ба?',
    outboundA: 'ДЕМО: кіру уақытын әкімшімен нақтылаймыз.',
    inboundB: 'ДЕМО: қосымша сүлгі алуға бола ма?',
    dishA: 'Көкөніс салаты', dishB: 'Шай', note: 'Үлгі тапсырыс — асүйге жіберілген жоқ',
  },
};

function demoDate(offset: number): string {
  const d = new Date();
  d.setDate(d.getDate() + offset);
  return [d.getFullYear(), String(d.getMonth() + 1).padStart(2, '0'), String(d.getDate()).padStart(2, '0')].join('-');
}

function demoRoom(rooms: readonly Room[], index: number): Room | undefined {
  return rooms[index % (rooms.length || 1)];
}

/** Synthetic reservation cards only, without any personal/financial records. */
export function demoReception(locale: Locale, rooms: readonly Room[]): ReceptionList {
  const l = labels[locale];
  const definitions: { status: string; start: number; end: number; guest: string; roomIndex: number }[] = [
    { status: 'GUARANTEED', start: 0, end: 2, guest: l.guestA, roomIndex: 0 },
    { status: 'CHECKED_IN', start: -2, end: 0, guest: l.guestB, roomIndex: 1 },
    { status: 'CHECKED_IN', start: -1, end: 2, guest: l.guestC, roomIndex: 2 },
    { status: 'PENDING', start: 1, end: 3, guest: l.guestD, roomIndex: 3 },
    { status: 'CHECKED_OUT', start: -4, end: -1, guest: l.guestA, roomIndex: 4 },
  ];
  const items: ReceptionReservation[] = definitions.map((row, i) => {
    const room = demoRoom(rooms, row.roomIndex);
    return {
      id: 'demo-reservation-' + (i + 1),
      bookingNumber: 'DEMO-' + String(i + 1).padStart(4, '0'),
      status: row.status, checkIn: demoDate(row.start), checkOut: demoDate(row.end),
      firstName: row.guest, phone: null, room_code: room?.code ?? null,
      room_state: room?.state ?? null, totalKgs: 0, paidKgs: 0, remainingKgs: 0,
    };
  });
  return { local_date: demoDate(0), items };
}

export function demoDashboard(hotelName: string, rooms: readonly Room[], tasks: readonly Task[], locale: Locale): Dashboard {
  const reservations = demoReception(locale, rooms);
  const occupied = rooms.filter(room => !!room.guest).length;
  const active = tasks.filter(task => task.status !== 'DONE' && task.status !== 'CANCELLED');
  const arriving = reservations.items.filter(item => item.status === 'GUARANTEED' && item.checkIn === reservations.local_date);
  const leaving = reservations.items.filter(item => item.status === 'CHECKED_IN' && item.checkOut === reservations.local_date);
  const daily = (values: readonly ReceptionReservation[]) => values.map(item => ({
    id: item.id, booking_number: item.bookingNumber, guest_name: item.firstName, room_code: item.room_code,
  }));
  return {
    property: { name: hotelName + ' · DEMO', local_date: reservations.local_date, currency: 'KGS' },
    rooms: {
      total: rooms.length,
      clean: rooms.filter(r => r.state === 'CLEAN').length,
      dirty: rooms.filter(r => r.state === 'DIRTY').length,
      in_inspection: rooms.filter(r => r.state === 'IN_INSPECTION').length,
      tech_block: rooms.filter(r => r.state === 'TECH_BLOCK').length,
    },
    stays: {
      occupancy_percent: rooms.length ? Math.round(100 * occupied / rooms.length) : 0,
      occupied_rooms: occupied, arrivals_today: arriving.length, departures_today: leaving.length,
    },
    communications: { active: 2, needs_reply: 1 },
    // There is no DEMO payment ledger. Zero is deliberate, NOT fabricated revenue.
    finance: { confirmed_payments_today_kgs: 0, active_reservations_remaining_kgs: 0 },
    tasks: {
      urgent_active: active.filter(t => t.priority === 'URGENT').length,
      housekeeping_active: active.filter(t => t.type === 'HOUSEKEEPING').length,
      maintenance_active: active.filter(t => t.type === 'MAINTENANCE').length,
    },
    today: { arrivals: daily(arriving), departures: daily(leaving) },
    attention_tasks: active.filter(t => t.priority === 'URGENT' || t.priority === 'HIGH').map(t => ({
      id: t.id, title: t.title, priority: t.priority, room_code: t.room_code,
    })),
  };
}

export function demoGrid(locale: Locale, rooms: readonly Room[], hotelName: string): Grid {
  const bookings = demoReception(locale, rooms).items.slice(0, 3);
  return {
    property: hotelName + ' · DEMO', start: demoDate(-7), end: demoDate(14),
    rooms: rooms.map((room, index) => {
      const booking = bookings[index];
      const blocks: GridBlock[] = booking ? [{
        id: 'demo-block-' + (index + 1), type: 'RESERVATION',
        start: booking.checkIn, end: booking.checkOut,
        reservation_id: booking.id, booking_number: booking.bookingNumber,
        guest_name: booking.firstName,
      }] : [];
      return {
        id: room.id, code: room.code, name: null,
        room_type_name: labels[locale].roomType, operational_state: room.state,
        blocks,
      };
    }),
  };
}

/** Two synthetic chats: sample text, no phone numbers, no network calls. */
export function demoConversations(locale: Locale): Conversation[] {
  const l = labels[locale];
  const timestamp = new Date().toISOString();
  return [
    {
      id: 'demo-chat-1', channel_kind: 'WHATSAPP', channel_name: l.channelA,
      status: 'OPEN', contact_name: l.guestA, contact_phone: null,
      assigned_to_id: null, assigned_to_name: null,
      last_message_text: l.inboundA, last_message_at: timestamp,
      needs_reply: true, waiting_seconds: 120,
    },
    {
      id: 'demo-chat-2', channel_kind: 'WEBCHAT', channel_name: l.channelB,
      status: 'WAITING_GUEST', contact_name: l.guestB, contact_phone: null,
      assigned_to_id: 'demo-staff', assigned_to_name: 'DEMO',
      last_message_text: l.inboundB, last_message_at: timestamp,
      needs_reply: false, waiting_seconds: null,
    },
  ];
}

export function demoConversationDetail(id: string, locale: Locale): ConversationDetail | null {
  const conversation = demoConversations(locale).find(item => item.id === id);
  if (!conversation) return null;
  const l = labels[locale];
  const timestamp = new Date().toISOString();
  return {
    conversation,
    messages: [
      { id: id + '-1', direction: 'INBOUND', text: id === 'demo-chat-1' ? l.inboundA : l.inboundB,
        created_at: timestamp, delivery_status: 'DELIVERED' },
      { id: id + '-2', direction: 'OUTBOUND', text: l.outboundA,
        created_at: timestamp, delivery_status: 'READ' },
    ],
  };
}

export function demoKitchenOrders(locale: Locale): KitchenOrder[] {
  const l = labels[locale];
  return [
    {
      id: 'demo-order-1', order_number: 'DEMO-0001', status: 'NEW',
      table_code: 'T-01', room_code: null, total_kgs: 0, notes: l.note,
      items: [{ id: 'demo-item-1', name: l.dishA, quantity: 1 }],
    },
    {
      id: 'demo-order-2', order_number: 'DEMO-0002', status: 'READY',
      table_code: 'T-03', room_code: null, total_kgs: 0, notes: l.note,
      items: [{ id: 'demo-item-2', name: l.dishB, quantity: 2 }],
    },
  ];
}

export function demoDiningFloor(locale: Locale): DiningFloor {
  const orders = demoKitchenOrders(locale);
  return {
    tables: [
      { id: 'demo-table-1', code: 'T-01', name: 'T-01', status: 'OCCUPIED', seats: 2 },
      { id: 'demo-table-2', code: 'T-02', name: 'T-02', status: 'AVAILABLE', seats: 4 },
      { id: 'demo-table-3', code: 'T-03', name: 'T-03', status: 'RESERVED', seats: 6 },
    ],
    orders: orders.map(order => ({
      id: order.id, order_number: order.order_number, status: order.status,
      table_code: order.table_code, room_code: order.room_code,
      waiter_id: null, waiter_name: null,
    })),
  };
}
