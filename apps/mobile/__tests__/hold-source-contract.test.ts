import {
  holdListResponse, holdCreateResponse, holdReleaseResponse,
} from '../src/api/contractValidation';
import { createLiveModules } from '../src/api/liveModules';

const holdId = '11111111-1111-4111-8111-111111111111';
const roomId = '22222222-2222-4222-8222-222222222222';
const row = {
  id: holdId,
  roomId,
  checkIn: '2026-11-05',
  checkOut: '2026-11-07',
  guestName: 'Synthetic Guest',
  expiresAt: '2026-11-04T10:30:00+00:00',
};
const expires = '2026-11-04T10:30:00+00:00';

describe('HOLD source contract: actual pms_holds.py projection, not historical matrix', () => {
  it('accepts only the server-list camelCase DB projection and returns the existing UI model', () => {
    expect(holdListResponse({ holds: [row] })).toEqual([row]);
    expect(holdListResponse({ holds: [] })).toEqual([]);
  });
  it('rejects incomplete, snake_case-only, cross-type and impossible HOLD responses', () => {
    for (const bad of [
      { holds: [{ ...row, roomId: undefined, room_id: roomId }] },
      { holds: [{ ...row, checkIn: '2026-02-30' }] },
      { holds: [{ ...row, checkOut: '2026-11-05' }] },
      { holds: [{ ...row, expiresAt: 'unknown' }] },
      { holds: [{ ...row, id: '../foreign-property' }] },
      { holds: [{ ...row, guestName: '' }] },
      { holds: [{ ...row, roomId: 123 }] },
      { holds: { ...row } },
      [{ ...row }],
    ]) {
      expect(() => holdListResponse(bad)).toThrow();
    }
  });
  it('requires the exact HELD 60-minute server commit acknowledgment', () => {
    const ack = { id: holdId, status: 'HELD', expires_at: expires, duration_minutes: 60 };
    expect(holdCreateResponse(ack)).toEqual(ack);
    for (const invalid of [
      { ...ack, status: 'OPEN' },
      { ...ack, duration_minutes: 120 },
      { ...ack, expires_at: 'not-an-ISO-time' },
      { ...ack, id: 'random' },
    ]) expect(() => holdCreateResponse(invalid)).toThrow();
  });
  it('never reports successful release without matching server UUID and status', () => {
    expect(holdReleaseResponse({ id: holdId, status: 'RELEASED' }, holdId))
      .toEqual({ id: holdId, status: 'RELEASED' });
    expect(() => holdReleaseResponse({ id: holdId, status: 'RELEASED' }, roomId)).toThrow();
    expect(() => holdReleaseResponse({ id: holdId, status: 'HELD' }, holdId)).toThrow();
  });
});

describe('HOLD remains blocked in the pinned mobile release despite its server-side source', () => {
  it('does not make any network call to list/create/release until separately accepted', async () => {
    const transport = jest.fn(async (_url: RequestInfo | URL, _options?: RequestInit) =>
      ({ status: 200, ok: true, redirected: false, json: async () => ({ holds: [row] }) } as Response));
    const api = createLiveModules('https://hotel.example', transport as unknown as typeof fetch);
    await expect(api.holds()).rejects.toMatchObject({ code: 'NOT_FOUND' });
    await expect(api.createHold({
      room_id: roomId, check_in: '2026-11-05', check_out: '2026-11-07',
      guest_name: 'Synthetic Guest', guest_phone: '+996555000000',
    })).rejects.toMatchObject({ code: 'NOT_FOUND' });
    await expect(api.releaseHold(holdId)).rejects.toMatchObject({ code: 'NOT_FOUND' });
    expect(transport).not.toHaveBeenCalled();
  });
});
