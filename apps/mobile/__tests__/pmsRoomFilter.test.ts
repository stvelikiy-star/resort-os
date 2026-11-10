import { filterPmsRooms } from '../src/roles/pmsRoomFilter';
import type { GridRoom } from '../src/api/liveModules';

const base: GridRoom = {
  id: '11111111-2222-3333-4444-555555555555',
  code: '1', name: 'Номер 1 · Спальный (тест)', room_type_name: 'Спальный',
  operational_state: 'CLEAN', blocks: [],
};
const occupied: GridRoom = {
  ...base, id: '22222222-3333-4444-5555-666666666666',
  code: '2', name: 'Гостевой', room_type_name: 'Стандарт',
  blocks: [{ id: 'booking', type: 'RESERVATION', start: '2026-11-09', end: '2026-11-12',
    reservation_id: '33333333-4444-5555-6666-777777777777', guest_name: null, booking_number: 'B-1' }],
};
const blocked: GridRoom = {
  ...base, id: '44444444-5555-6666-7777-888888888888',
  code: '3', name: 'Ремонт', operational_state: 'TECH_BLOCK',
};

describe('PMS client-side room filters use only authorized grid data', () => {
  it('finds code, actual name and category case-insensitively', () => {
    expect(filterPmsRooms([base, occupied], '  спальный ', 'all', '2026-11-09', '2026-11-09')).toEqual([base]);
    expect(filterPmsRooms([base, occupied], '2', 'all', '2026-11-09', '2026-11-09')).toEqual([occupied]);
    expect(filterPmsRooms([base, occupied], 'СТАНДАРТ', 'all', '2026-11-09', '2026-11-09')).toEqual([occupied]);
  });
  it('does not confuse free rooms with reserved or technical blocks', () => {
    const rooms = [base, occupied, blocked];
    expect(filterPmsRooms(rooms, '', 'free', '2026-11-09', '2026-11-09')).toEqual([base]);
    expect(filterPmsRooms(rooms, '', 'reserved', '2026-11-09', '2026-11-09')).toEqual([occupied]);
    expect(filterPmsRooms(rooms, '', 'attention', '2026-11-09', '2026-11-09')).toEqual([blocked]);
  });
  it('re-evaluates availability on calendar change and excludes past-day new bookings', () => {
    const rooms = [base, occupied, blocked];
    expect(filterPmsRooms(rooms, '', 'free', '2026-11-13', '2026-11-09')).toEqual([base, occupied]);
    expect(filterPmsRooms(rooms, '', 'reserved', '2026-11-13', '2026-11-09')).toEqual([]);
    expect(filterPmsRooms(rooms, '', 'free', '2026-11-08', '2026-11-09')).toEqual([]);
  });
  it('does not mix names from unrelated properties or fabricate rooms', () => {
    expect(filterPmsRooms([], 'спальный', 'all', '2026-11-09', '2026-11-09')).toEqual([]);
    expect(filterPmsRooms([base], 'unknown', 'all', '2026-11-09', '2026-11-09')).toEqual([]);
  });
});
