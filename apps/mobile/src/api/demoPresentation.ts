/** Strictly synthetic, in-memory visual fixtures for the isolated DEMO hotel.
 * Never returned for LIVE sessions and never sent to real PMS endpoints.
 */
import type { Dashboard, ReceptionList, Grid, Conversation, ConversationDetail, DiningFloor, KitchenOrder } from './liveModules';
import type { Locale } from '../i18n';
import type { Room, Task } from './types';

const one = (n: number) => String(n).padStart(2, '0');
function dateShift(offset: number): string {
  const d = new Date(); d.setHours(12, 0, 0, 0); d.setDate(d.getDate() + offset);
  return d.getFullYear() + '-' + one(d.getMonth() + 1) + '-' + one(d.getDate());
}
const guestLabel: Record<Locale, string> = { ru: 'Демо-гость', kg: 'Демо конок', en: 'Demo guest', kz: 'Демо қонақ' };
const text: Record<Locale, { welcome: string; luggage: string; late: string; reply: string; info: string; soup: string; fish: string; salad: string; cake: string }> = {
  ru: { welcome: 'Добрый день! Во сколько можно заселиться?', luggage: 'Можно оставить чемоданы до заселения?', late: 'Спасибо! Будем к 14:00.', reply: 'Да, камера хранения работает круглосуточно.', info: 'Тестовый диалог — сообщения никому не отправляются.', soup: 'Том-ям', fish: 'Форель на гриле', salad: 'Салат из овощей', cake: 'Чизкейк' },
  kg: { welcome: 'Саламатсызбы! Саат канчада жайгашсак болот?', luggage: 'Жайгашканга чейин жүктү калтырсак болобу?', late: 'Рахмат! Саат 14:00дө келебиз.', reply: 'Ооба, жүк сактоочу жай күнү-түнү иштейт.', info: 'Сыноо маеги — билдирүүлөр эч кимге жөнөтүлбөйт.', soup: 'Том-ям', fish: 'Грильде бышкан форель', salad: 'Жашылча салаты', cake: 'Чизкейк' },
  en: { welcome: 'Hello! What time is check-in?', luggage: 'May we leave our bags before check-in?', late: 'Thank you! We will arrive at 2 PM.', reply: 'Of course. Luggage storage is open around the clock.', info: 'Demo conversation — no messages are sent.', soup: 'Tom yum soup', fish: 'Grilled trout', salad: 'Vegetable salad', cake: 'Cheesecake' },
  kz: { welcome: 'Сәлеметсіз бе! Қай уақытта орналасуға болады?', luggage: 'Орналасқанға дейін жүкті қалдыруға бола ма?', late: 'Рақмет! Сағат 14:00-де келеміз.', reply: 'Иә, жүк сақтау орны тәулік бойы жұмыс істейді.', info: 'Сынақ диалогы — хабарламалар ешкімге жіберілмейді.', soup: 'Том-ям', fish: 'Грильдегі форель', salad: 'Көкөніс салаты', cake: 'Чизкейк' },
};
export function demoReception(locale: Locale, rooms: readonly Room[]): ReceptionList {
  const today = dateShift(0);
  const item = (index: number, status: string, checkIn: string, checkOut: string, roomIndex: number) => ({
    id: 'demo-booking-' + index, bookingNumber: 'DEMO-' + (200 + index),
    status, checkIn, checkOut, firstName: guestLabel[locale] + ' ' + one(index),
    phone: null, room_code: rooms[roomIndex % rooms.length]?.code ?? null,
    room_state: rooms[roomIndex % rooms.length]?.state ?? null,
    totalKgs: 25000, paidKgs: 15000, remainingKgs: 10000,
  });
  return { local_date: today, items: [
    item(1,'GUARANTEED',today,dateShift(3),0), item(2,'GUARANTEED',today,dateShift(2),1),
    item(3,'CHECKED_IN',dateShift(-2),today,2), item(4,'CHECKED_IN',dateShift(-1),dateShift(2),3),
    item(5,'PENDING',dateShift(1),dateShift(5),4),
  ] };
}
export function demoDashboard(name: string, rooms: readonly Room[], tasks: readonly Task[], locale: Locale): Dashboard {
  const active = tasks.filter(t => t.status !== 'DONE' && t.status !== 'CANCELLED');
  const reception = demoReception(locale, rooms);
  const arrival = reception.items.filter(x => x.checkIn === reception.local_date && x.status === 'GUARANTEED');
  const departing = reception.items.filter(x => x.checkOut === reception.local_date && x.status === 'CHECKED_IN');
  const counts = (state: string) => rooms.filter(x => x.state === state).length;
  return {
    property: { name, local_date: reception.local_date, currency: 'KGS' },
    rooms: { total: rooms.length, clean: counts('CLEAN'), dirty: counts('DIRTY'), in_inspection: counts('IN_INSPECTION'), tech_block: counts('TECH_BLOCK') },
    stays: { occupancy_percent: 72, occupied_rooms: 4, arrivals_today: arrival.length, departures_today: departing.length },
    communications: { active: 2, needs_reply: 1 },
    finance: { confirmed_payments_today_kgs: 142500, active_reservations_remaining_kgs: 38000 },
    tasks: { urgent_active: active.filter(t => t.priority === 'URGENT' || t.priority === 'HIGH').length, housekeeping_active: active.filter(t => t.type === 'HOUSEKEEPING').length, maintenance_active: active.filter(t => t.type === 'MAINTENANCE').length },
    today: { arrivals: arrival.map(x => ({ id:x.id, booking_number:x.bookingNumber, guest_name:x.firstName, room_code:x.room_code })), departures: departing.map(x => ({ id:x.id, booking_number:x.bookingNumber, guest_name:x.firstName, room_code:x.room_code })) },
    attention_tasks: active.slice(0,4).map(t => ({ id:t.id, title:t.title, priority:t.priority, room_code:t.room_code })),
  };
}
export function demoGrid(locale: Locale, rooms: readonly Room[], name: string): Grid {
  const reception=demoReception(locale,rooms);
  const blocks = reception.items.map(x => ({ id:'grid-'+x.id, type:'RESERVATION', start:x.checkIn, end:x.checkOut, reservation_id:x.id, booking_number:x.bookingNumber, guest_name:x.firstName }));
  return { property: name, start:dateShift(0), end:dateShift(7),
    rooms: rooms.map((r,i) => ({
      id:r.id, code:r.code, name:null, room_type_name:'STANDARD',
      operational_state:r.state,
      blocks:[...blocks.filter(b => reception.items.some(x => x.id===b.reservation_id && x.room_code===r.code)),
        ...(i===4?[{id:'demo-block-tech', type:'MAINTENANCE_BLOCK',start:dateShift(0),end:dateShift(4),reservation_id:null,booking_number:null,guest_name:null}]:[])],
    })) };
}
export function demoConversations(locale: Locale): Conversation[] {
  const stamp = new Date().toISOString();
  return [
    { id:'demo-chat-01', channel_kind:'WHATSAPP', channel_name:'DEMO WhatsApp', status:'WAITING_STAFF', contact_name:guestLabel[locale]+' 01', contact_phone:null, assigned_to_id:null,assigned_to_name:null,last_message_text:text[locale].luggage,last_message_at:stamp,needs_reply:true,waiting_seconds:600 },
    { id:'demo-chat-02', channel_kind:'WHATSAPP', channel_name:'DEMO WhatsApp', status:'WAITING_GUEST', contact_name:guestLabel[locale]+' 02', contact_phone:null,assigned_to_id:'demo-staff',assigned_to_name:'DEMO',last_message_text:text[locale].reply,last_message_at:stamp,needs_reply:false,waiting_seconds:null },
  ];
}
export function demoConversationDetail(id: string, locale: Locale): ConversationDetail | null {
  const conversation = demoConversations(locale).find(x=>x.id===id);
  if(!conversation)return null;
  const stamp = new Date().toISOString();
  return { conversation, messages:[
    { id:'demo-message-01', direction:'INBOUND',text:text[locale].welcome,created_at:stamp,delivery_status:null },
    { id:'demo-message-02', direction:'OUTBOUND',text:text[locale].reply,created_at:stamp,delivery_status:'READ' },
    { id:'demo-message-03', direction:'INBOUND',text:text[locale].luggage,created_at:stamp,delivery_status:null },
  ] };
}
export function demoDiningFloor(locale: Locale): DiningFloor {
  const tr = text[locale];
  return {
    tables: [{id:'d-table-1',code:'T-01',status:'OCCUPIED',seats:4},{id:'d-table-2',code:'T-02',status:'AVAILABLE',seats:2},{id:'d-table-3',code:'T-03',status:'RESERVED',seats:6}],
    orders: demoKitchenOrders(locale),
  };
}
export function demoKitchenOrders(locale: Locale): KitchenOrder[] {
  const tr=text[locale];
  return [
    {id:'d-order-01',order_number:'DEMO-021',status:'COOKING',table_code:'T-01',room_code:null,notes:null,waiter_id:null,items:[{id:'d-item-01',name:tr.soup,quantity:2},{id:'d-item-02',name:tr.fish,quantity:1}]},
    {id:'d-order-02',order_number:'DEMO-022',status:'NEW',table_code:'T-03',room_code:null,notes:null,waiter_id:null,items:[{id:'d-item-03',name:tr.salad,quantity:2},{id:'d-item-04',name:tr.cake,quantity:1}]},
  ];
}
