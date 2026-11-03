import { createDemoApi } from '../src/api/demoApi';
import { createRealApi } from '../src/api/realApi';
import { ApiError, canTransition } from '../src/api/types';
import { parseHotelAddress } from '../src/api/hotels';

describe('transitions mirror backend', () => {
  it('housekeeping needs inspection before done', () => {
    expect(canTransition('HOUSEKEEPING', 'IN_PROGRESS', 'DONE')).toBe(false);
    expect(canTransition('HOUSEKEEPING', 'IN_PROGRESS', 'IN_INSPECTION')).toBe(true);
    expect(canTransition('HOUSEKEEPING', 'IN_INSPECTION', 'DONE')).toBe(true);
  });
  it('maintenance goes straight to done', () => expect(canTransition('MAINTENANCE', 'IN_PROGRESS', 'DONE')).toBe(true));
});

describe('demo api', () => {
  const login = async (hotel: string, user: string) => { const a = createDemoApi(hotel, 0); await a.login(user, 'demo'); return a; };
  it('rejects wrong password and unauthenticated calls', async () => {
    const a = createDemoApi('h', 0);
    await expect(a.listTasks()).rejects.toMatchObject({ code: 'UNAUTHORIZED' });
    await expect(a.login('maid', 'x')).rejects.toBeInstanceOf(ApiError);
  });
  it('maid sees only housekeeping; technician no housekeeping', async () => {
    expect((await (await login('h', 'maid')).listTasks()).every((t) => t.type === 'HOUSEKEEPING')).toBe(true);
    expect((await (await login('h', 'tech')).listTasks()).some((t) => t.type === 'HOUSEKEEPING')).toBe(false);
  });
  it('housekeeping flow: claim → checklist → inspection → manager approves', async () => {
    const m = await login('h', 'maid');
    await m.claimTask('t1');
    await expect(m.completeHousekeeping('t1', { checklist: { BED_LINEN: true } })).rejects.toMatchObject({ code: 'BAD_REQUEST' });
    const all = { BED_LINEN: true, BATHROOM: true, SURFACES: true, AMENITIES: true, FINAL_CHECK: true };
    expect((await m.completeHousekeeping('t1', { checklist: all })).status).toBe('IN_INSPECTION');
    await expect(m.setTaskStatus('t1', 'DONE')).rejects.toMatchObject({ code: 'FORBIDDEN' });
  });
  it('manager-only endpoints are forbidden for others', async () => {
    const m = await login('h', 'maid');
    await expect(m.listStaff()).rejects.toMatchObject({ code: 'FORBIDDEN' });
    await expect(m.daySummary()).rejects.toMatchObject({ code: 'FORBIDDEN' });
    await expect(m.setRoomState('r1', 'CLEAN')).rejects.toMatchObject({ code: 'FORBIDDEN' });
    const g = await login('h', 'manager');
    expect((await g.assignTask('t6', 'u-maid')).assigned_to_id).toBe('u-maid');
    await expect(g.assignTask('t4', 'u-maid')).rejects.toMatchObject({ code: 'BAD_REQUEST' });
  });
  it('hotels are isolated: different data and no shared state', async () => {
    const a = await login('demo-marina', 'manager'); const b = await login('demo-sunrise', 'manager');
    expect((await a.listRooms())[0].code.startsWith('M-')).toBe(true);
    expect((await b.listRooms())[0].code.startsWith('S-')).toBe(true);
    await a.setRoomState('r1', 'CLEAN');
    expect((await b.listRooms())[0].state).toBe('DIRTY');
  });
  it('creates maintenance requests and validates text', async () => {
    const a = await login('h', 'reception');
    await expect(a.createMaintenance({ room_id: null, category: 'OTHER', priority: 'LOW', description: ' ' })).rejects.toMatchObject({ code: 'BAD_REQUEST' });
    expect((await a.createMaintenance({ room_id: 'r1', category: 'PLUMBING', priority: 'HIGH', description: 'Leak' })).type).toBe('MAINTENANCE');
  });
});

describe('real api contract (mock fetch)', () => {
  const mk = (responses: { status?: number; body?: unknown }[]) => {
    const calls: { url: string; init: RequestInit }[] = [];
    const f = jest.fn(async (url: string, init: RequestInit) => {
      calls.push({ url, init });
      const r = responses.shift() ?? { status: 200, body: {} };
      return { ok: (r.status ?? 200) < 400, status: r.status ?? 200, json: async () => r.body } as Response;
    });
    return { f: f as unknown as typeof fetch, calls };
  };
  it('refuses non-https base urls', () => expect(() => createRealApi('http://x.example')).toThrow());
  it('login posts credentials to existing auth route with cookie credentials and no secrets', async () => {
    const { f, calls } = mk([{ body: { id: '1', username: 'a', role: 'MAID' } }]);
    await createRealApi('https://api.hotel.example/', f).login('a', 'b');
    expect(calls[0].url).toBe('https://api.hotel.example/api/v1/auth/login');
    expect(calls[0].init.method).toBe('POST');
    expect(calls[0].init.credentials).toBe('include');
    expect(JSON.stringify(calls[0].init.headers)).not.toMatch(/authorization|api[-_]?key/i);
  });
  it('maps http errors and network failures', async () => {
    const { f } = mk([{ status: 403 }, { status: 401 }, { status: 409 }]);
    const a = createRealApi('https://h.example', f);
    await expect(a.me()).rejects.toMatchObject({ code: 'FORBIDDEN' });
    await expect(a.me()).rejects.toMatchObject({ code: 'UNAUTHORIZED' });
    await expect(a.claimTask('1')).rejects.toMatchObject({ code: 'CONFLICT' });
    const off = createRealApi('https://h.example', (async () => { throw new TypeError('x'); }) as unknown as typeof fetch);
    await expect(off.me()).rejects.toMatchObject({ code: 'OFFLINE' });
  });
  it('reads the canonical maintenance task after the create endpoint returns only id/status', async () => {
    const { f, calls } = mk([
      { status: 201, body: { id: 'created-1', status: 'OPEN' } },
      { status: 200, body: [{ id: 'created-1', type: 'MAINTENANCE', status: 'OPEN', title: 'Leak', priority: 'HIGH' }] },
    ]);
    const api = createRealApi('https://hotel.example', f);
    const created = await api.createMaintenance({ room_id: null, category: 'PLUMBING', priority: 'HIGH', description: 'Leak' });
    expect(created).toMatchObject({ id: 'created-1', type: 'MAINTENANCE', title: 'Leak', priority: 'HIGH' });
    expect(calls[0].url).toBe('https://hotel.example/api/v1/ops/tasks');
    expect(calls[1].url).toBe('https://hotel.example/api/v1/ops/tasks?limit=300');
  });
  it('rejects an incomplete create response rather than rendering a false task', async () => {
    const { f } = mk([{ status: 201, body: { status: 'OPEN' } }]);
    await expect(createRealApi('https://hotel.example', f).createMaintenance({
      room_id: null, category: 'OTHER', priority: 'NORMAL', description: 'Door issue',
    })).rejects.toMatchObject({ code: 'UNKNOWN' });
  });

  it('uses backend routes for tasks, status, assignee, complete-report', async () => {
    const { f, calls } = mk([{ body: [] }, {}, { body: [{ id: 't', type: 'MAINTENANCE', status: 'DONE' }] }, {}, { body: [{ id: 't', type: 'HOUSEKEEPING', status: 'IN_INSPECTION' }] }, {}, { body: [{ id: 't', type: 'HOUSEKEEPING', status: 'OPEN' }] }]);
    const a = createRealApi('https://h.example', f);
    await a.listTasks({ type: 'MAINTENANCE' });
    await a.setTaskStatus('t', 'DONE');
    await a.completeHousekeeping('t', { checklist: { BED_LINEN: true }, comment: 'ok' });
    await a.assignTask('t', null);
    const u = calls.map((c) => `${c.init.method} ${c.url.replace('https://h.example', '')}`);
    expect(u[0]).toBe('GET /api/v1/ops/tasks?type=MAINTENANCE');
    expect(u[1]).toBe('PATCH /api/v1/ops/tasks/t/status');
    expect(u).toContain('POST /api/v1/ops/tasks/t/complete-report');
    expect(u).toContain('PATCH /api/v1/ops/tasks/t/assignee');
    const body = JSON.parse(String(calls.find((c) => c.url.endsWith('complete-report'))!.init.body));
    expect(body.checklist).toHaveLength(5);
    expect(body.evidence_urls).toEqual([]);
  });
});

describe('hotel address parsing', () => {
  it('accepts https hosts and bare hostnames', () => {
    expect(parseHotelAddress('api.marina.example')).toEqual({ ok: true, baseUrl: 'https://api.marina.example' });
    expect(parseHotelAddress('https://api.marina.example/path?x=1')).toEqual({ ok: true, baseUrl: 'https://api.marina.example' });
  });
  it('rejects http, credentials, empty and dotless hosts', () => {
    expect(parseHotelAddress('http://api.marina.example')).toEqual({ ok: false, reason: 'secureOnly' });
    expect(parseHotelAddress('https://u:p@api.marina.example')).toMatchObject({ ok: false });
    expect(parseHotelAddress('')).toMatchObject({ ok: false });
    expect(parseHotelAddress('localhost')).toMatchObject({ ok: false });
  });
});
