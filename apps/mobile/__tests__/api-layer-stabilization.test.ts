import { createLiveModules } from '../src/api/liveModules';
import { createRealApi } from '../src/api/realApi';
import { safeRouteId, safeIsoDate } from '../src/api/routeId';
import {
  authUserResponse, itemsEnvelope, kitchenOrdersResponse, diningFloorResponse,
  assistantCapabilitiesResponse, assistantAnswerResponse, objectResponse,
} from '../src/api/contractValidation';

const ok = (data: unknown) => ({ status: 200, ok: true, redirected: false, json: async () => data } as Response);
const transportOf = (data: unknown) => jest.fn(async (_u: RequestInfo | URL, _i?: RequestInit) => ok(data));
const user = { id: 'u1', username: 'maid', display_name: 'A', role: 'MAID', property_code: 'P1', module_permissions: ['OPS'] };
const live = (data: unknown) => { const t = transportOf(data); return { t, api: createLiveModules('https://hotel.example', t as unknown as typeof fetch) }; };

describe('shared route guards', () => {
  it('accepts opaque ids and rejects separators/encodings', () => {
    expect(safeRouteId('3f2a-BC_9')).toBe('3f2a-BC_9');
    for (const bad of ['', '../x', 'a/b', 'a%2fb', 'a?b', 'a#b', ' a', '-a']) expect(() => safeRouteId(bad)).toThrow();
    expect(() => safeRouteId(undefined as unknown as string)).toThrow();
  });
  it('accepts only calendar dates in query strings', () => {
    expect(safeIsoDate('2026-11-04')).toBe('2026-11-04');
    for (const bad of ['2026-11-04&x=1', '2026/11/04', '']) expect(() => safeIsoDate(bad)).toThrow();
  });
});

describe('LIVE modules use the shared guards before any network call', () => {
  it.each([
    ['reservation', (a: ReturnType<typeof createLiveModules>) => a.reservation('../x')],
    ['checkIn', (a: ReturnType<typeof createLiveModules>) => a.checkIn('a/b')],
    ['claimConversation', (a: ReturnType<typeof createLiveModules>) => Promise.resolve().then(() => a.claimConversation('a%2fb'))],
    ['kitchenStatus', (a: ReturnType<typeof createLiveModules>) => Promise.resolve().then(() => a.kitchenStatus('a?b', 'READY'))],
    ['claimWaiterOrder waiter', (a: ReturnType<typeof createLiveModules>) => Promise.resolve().then(() => a.claimWaiterOrder('o1', '../u'))],
    ['pmsGrid', (a: ReturnType<typeof createLiveModules>) => a.pmsGrid('2026-11-04&x=1', '2026-11-05')],
  ])('%s rejects a malformed reference', async (_n, run) => {
    const { t, api } = live({});
    await expect(Promise.resolve().then(() => run(api))).rejects.toMatchObject({ code: 'BAD_REQUEST' });
    expect(t).not.toHaveBeenCalled();
  });
  it('still builds the exact pinned route for a valid id', async () => {
    const { t, api } = live({ id: 'r1' });
    await api.reservation('r1');
    expect(t.mock.calls[0][0]).toBe('https://hotel.example/api/v1/admin/reception/reservations/r1');
  });
});

describe('response validators', () => {
  it('auth: requires identity and permission list; keeps valid optional fields', () => {
    expect(authUserResponse({ ...user, property_id: null, module_permissions_custom: false }).role).toBe('MAID');
    expect(() => authUserResponse({ ...user, module_permissions: 'OPS' })).toThrow();
    expect(() => authUserResponse({ ...user, role: '' })).toThrow();
    expect(() => authUserResponse(null)).toThrow();
  });
  it('items envelope: bare array only when allowed', () => {
    expect(itemsEnvelope([1], 'x', true)).toEqual([1]);
    expect(() => itemsEnvelope([1], 'x')).toThrow();
    expect(itemsEnvelope({ items: [] }, 'x')).toEqual([]);
    expect(() => itemsEnvelope({ items: 'no' }, 'x', true)).toThrow();
  });
  it('kitchen orders: rejects rows without id/status/items', () => {
    expect(kitchenOrdersResponse({ items: [{ id: 'o', order_number: 'K1', status: 'NEW', items: [] }] })).toHaveLength(1);
    expect(() => kitchenOrdersResponse({ items: [{ id: 'o', status: 'NEW', items: [] }] })).toThrow();
    expect(() => kitchenOrdersResponse({ items: [{ id: 'o', order_number: 'K1', status: 'NEW' }] })).toThrow();
    expect(() => kitchenOrdersResponse([])).toThrow();
  });
  it('dining floor: requires tables and orders arrays', () => {
    expect(diningFloorResponse({ tables: [{ id: 't', code: 'T1' }], orders: [] }).tables).toHaveLength(1);
    expect(() => diningFloorResponse({ tables: [] })).toThrow();
    expect(() => diningFloorResponse({ tables: [{ id: 't' }], orders: [] })).toThrow();
  });
  it('assistant: capabilities typed, answer must be read-only', () => {
    const caps = { configured: true, read_only: true, can_mutate: false, live_read_only: true, role: 'OWNER', property_code: 'P1' };
    expect(assistantCapabilitiesResponse(caps).role).toBe('OWNER');
    expect(() => assistantCapabilitiesResponse({ ...caps, can_mutate: 'no' })).toThrow();
    expect(() => assistantAnswerResponse({ answer: 'hi', read_only: false })).toThrow();
    expect(assistantAnswerResponse({ answer: 'hi', read_only: true }).answer).toBe('hi');
  });
  it('object response rejects arrays and null', () => {
    expect(() => objectResponse([], 'r')).toThrow();
    expect(() => objectResponse(null, 'r')).toThrow();
  });
});

describe('realApi validates auth and task list payloads', () => {
  it('login/me return a validated user and reject a malformed identity', async () => {
    const good = createRealApi('https://hotel.example', transportOf(user) as unknown as typeof fetch);
    expect((await good.me()).id).toBe('u1');
    const bad = createRealApi('https://hotel.example', transportOf({ id: 'u1', role: 'OWNER' }) as unknown as typeof fetch);
    await expect(bad.login('a', 'b')).rejects.toMatchObject({ code: 'UNKNOWN' });
    await expect(bad.me()).rejects.toMatchObject({ code: 'UNKNOWN' });
  });
  it('listTasks accepts bare array and {items}, rejects anything else', async () => {
    const task = { id: 't1', type: 'HOUSEKEEPING', status: 'OPEN' };
    for (const payload of [[task], { items: [task] }]) {
      const api = createRealApi('https://hotel.example', transportOf(payload) as unknown as typeof fetch);
      expect((await api.listTasks())[0].id).toBe('t1');
    }
    const api = createRealApi('https://hotel.example', transportOf({ tasks: [task] }) as unknown as typeof fetch);
    await expect(api.listTasks()).rejects.toMatchObject({ code: 'UNKNOWN' });
  });
  it('claimTask still rejects a malformed id before the network', async () => {
    const t = transportOf({});
    const api = createRealApi('https://hotel.example', t as unknown as typeof fetch);
    await expect(api.claimTask('../x')).rejects.toMatchObject({ code: 'BAD_REQUEST' });
    expect(t).not.toHaveBeenCalled();
  });
});
