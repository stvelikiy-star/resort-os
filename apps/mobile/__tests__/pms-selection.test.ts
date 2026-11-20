import { extendPmsDateSelection, isPmsDateFree, shortPmsGuestLabel } from '../src/roles/pmsSelection';
import type { GridRoom } from '../src/api/liveModules';

const room: GridRoom = {
  id: '11111111-2222-3333-4444-555555555555',
  code: 'M-101', name: null, room_type_name: 'Standard', operational_state: 'CLEAN', blocks: [],
};
const reserved = { ...room, blocks: [{
  id:'r1', type:'RESERVATION', start:'2026-11-10', end:'2026-11-13',
  reservation_id:'22222222-3333-4444-5555-666666666666',
  booking_number:'BOOK-7', guest_name:'ДЕМО · Гость А',
}] };
describe('PMS cell interaction semantics', () => {
  it('renders the guest label instead of an anonymous dot', () => {
    expect(shortPmsGuestLabel(reserved.blocks[0])).toBe('Гость А');
    expect(shortPmsGuestLabel({...reserved.blocks[0],guest_name:null})).toBe('BOOK-7');
  });
  it('starts on one free day, then extends only within the same room', () => {
    const a=extendPmsDateSelection(null,room,'2026-11-06','2026-11-06');
    expect(a).toEqual({roomId:room.id,roomCode:room.code,start:'2026-11-06',end:'2026-11-07'});
    const b=extendPmsDateSelection(a,room,'2026-11-08','2026-11-06');
    expect(b).toEqual({...a,end:'2026-11-09'});
    expect(extendPmsDateSelection(b,room,'2026-11-07','2026-11-06')).toEqual(b);
  });
  it('never bridges a booking or maintenance blackout', () => {
    const selection=extendPmsDateSelection(null,reserved,'2026-11-08','2026-11-06');
    expect(extendPmsDateSelection(selection,reserved,'2026-11-14','2026-11-06'))
      .toEqual({roomId:room.id,roomCode:room.code,start:'2026-11-14',end:'2026-11-15'});
    expect(isPmsDateFree(reserved,'2026-11-10','2026-11-06')).toBe(false);
    expect(isPmsDateFree({...room,operational_state:'TECH_BLOCK'},'2026-11-08','2026-11-06')).toBe(false);
    expect(isPmsDateFree(room,'2026-11-05','2026-11-06')).toBe(false);
  });
  it('resets selection when changing room and does not exceed 60 nights', () => {
    const a=extendPmsDateSelection(null,room,'2026-11-06','2026-11-06');
    const other={...room,id:'33333333-4444-5555-6666-777777777777',code:'M-102'};
    expect(extendPmsDateSelection(a,other,'2026-11-09','2026-11-06')?.roomId).toBe(other.id);
    const tooLong=extendPmsDateSelection(a,room,'2027-02-01','2026-11-06');
    expect(tooLong?.start).toBe('2027-02-01');
    expect(tooLong?.end).toBe('2027-02-02');
  });
});
