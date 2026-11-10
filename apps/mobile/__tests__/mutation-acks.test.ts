import { createLiveModules } from '../src/api/liveModules';
import { errorForStatus } from '../src/api/http';

const ok = (data: unknown) => ({ status: 200, ok: true, redirected: false, json: async () => data } as Response);
const mod = (data: unknown) => createLiveModules('https://hotel.example', (async () => ok(data)) as unknown as typeof fetch);

describe('mutation acknowledgments echo the addressed record', () => {
  it('check-in / check-out accept the server ack and reject a wrong id or status', async () => {
    expect((await mod({ reservation_id: 'r1', status: 'CHECKED_IN' }).checkIn('r1')).status).toBe('CHECKED_IN');
    expect((await mod({ reservation_id: 'r1', status: 'CHECKED_OUT' }).checkOut('r1')).status).toBe('CHECKED_OUT');
    await expect(mod({ reservation_id: 'r2', status: 'CHECKED_IN' }).checkIn('r1')).rejects.toMatchObject({ code: 'UNKNOWN' });
    await expect(mod({ reservation_id: 'r1', status: 'CHECKED_IN' }).checkOut('r1')).rejects.toMatchObject({ code: 'UNKNOWN' });
    await expect(mod({}).checkIn('r1')).rejects.toMatchObject({ code: 'UNKNOWN' });
  });
  it('kitchen status must report the requested status', async () => {
    await expect(mod({ id: 'o1', status: 'READY' }).kitchenStatus('o1', 'READY')).resolves.toBeTruthy();
    await expect(mod({ id: 'o1', status: 'COOKING' }).kitchenStatus('o1', 'READY')).rejects.toMatchObject({ code: 'UNKNOWN' });
  });
  it('conversation claim, status and note acks are verified', async () => {
    await expect(mod({ id: 'c1', assigned_to_id: 'u1' }).claimConversation('c1')).resolves.toBeTruthy();
    await expect(mod({ id: 'c9' }).claimConversation('c1')).rejects.toMatchObject({ code: 'UNKNOWN' });
    await expect(mod({ id: 'c1', status: 'RESOLVED' }).conversationStatus('c1', 'RESOLVED')).resolves.toBeTruthy();
    await expect(mod({ id: 'c1', status: 'OPEN' }).conversationStatus('c1', 'RESOLVED')).rejects.toMatchObject({ code: 'UNKNOWN' });
    await expect(mod({ id: 'm1', conversation_id: 'c1', direction: 'INTERNAL' }).internalNote('c1', 'x')).resolves.toBeTruthy();
    await expect(mod({ conversation_id: 'c1' }).internalNote('c1', 'x')).rejects.toMatchObject({ code: 'UNKNOWN' });
    await expect(mod({ id: 'm1', conversation_id: 'other' }).internalNote('c1', 'x')).rejects.toMatchObject({ code: 'UNKNOWN' });
  });
  it('waiter claim must name the claiming waiter', async () => {
    await expect(mod({ id: 'o1', waiter_id: 'u1' }).claimWaiterOrder('o1', 'u1')).resolves.toBeTruthy();
    await expect(mod({ id: 'o1', waiter_id: 'u2' }).claimWaiterOrder('o1', 'u1')).rejects.toMatchObject({ code: 'UNKNOWN' });
    await expect(mod({ id: 'o1', waiter_id: null }).claimWaiterOrder('o1', 'u1')).rejects.toMatchObject({ code: 'UNKNOWN' });
  });
});

describe('single status -> error mapping', () => {
  it.each([
    [400, 'BAD_REQUEST'], [422, 'BAD_REQUEST'], [401, 'UNAUTHORIZED'], [403, 'FORBIDDEN'], [404, 'NOT_FOUND'],
    [409, 'CONFLICT'], [429, 'RATE_LIMIT'], [500, 'UNKNOWN'], [418, 'UNKNOWN'],
  ])('%i -> %s with a fixed safe message', (status, code) => {
    const e = errorForStatus(status);
    expect(e.code).toBe(code);
    expect(e.message.length).toBeGreaterThan(0);
  });
});
