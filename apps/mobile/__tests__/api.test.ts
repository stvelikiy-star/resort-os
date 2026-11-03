import { createDemoApi } from '../src/api/demoApi';
import { createRealApi } from '../src/api/realApi';
import { ApiError, canTransition } from '../src/api/types';
import { hotelConnectionId, parseHotelAddress } from '../src/api/hotels';

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
    expect((await g.assignTask('t3', 'u-maid')).assigned_to_id).toBe('u-maid');
    await expect(g.assignTask('t4', 'u-maid')).rejects.toMatchObject({ code: 'BAD_REQUEST' });
  });
  it('demo denies claiming work assigned to another employee and denies other role types', async () => {
    const maid = await login('h', 'maid');
    await expect(maid.claimTask('t3')).rejects.toMatchObject({ code: 'CONFLICT' });
    await expect(maid.claimTask('t4')).rejects.toMatchObject({ code: 'FORBIDDEN' });
    const tech = await login('h2', 'tech');
    expect((await tech.listTasks()).every((task) => task.type === 'MAINTENANCE')).toBe(true);
    await expect(tech.completeHousekeeping('t2', { checklist: {} })).rejects.toMatchObject({ code: 'FORBIDDEN' });
  });
  it('demo inspection is reserved for managers and only compatible task assignees are accepted', async () => {
    const reception = await login('h', 'reception');
    expect(await reception.listTasks()).toEqual([]);
    await expect(reception.setTaskStatus('t3', 'DONE')).rejects.toMatchObject({ code: 'FORBIDDEN' });
    const manager = await login('hotel-management', 'manager');
    await expect(manager.assignTask('t6', 'u-maid')).rejects.toMatchObject({ code: 'BAD_REQUEST' });
    await expect(manager.assignTask('t7', 'u-maid')).rejects.toMatchObject({ code: 'CONFLICT' });
  });
  it('manager assigns real demo unassigned cleaning and repair work to matching staff roles', async () => {
    const manager = await login('assign-demo', 'manager');
    const before = await manager.listTasks();
    expect(before.find((task) => task.id === 't8')).toMatchObject({ type: 'HOUSEKEEPING', assigned_to_id: null });
    expect(before.find((task) => task.id === 't9')).toMatchObject({ type: 'MAINTENANCE', assigned_to_id: null });
    await expect(manager.assignTask('t8', 'u-tech')).rejects.toMatchObject({ code: 'BAD_REQUEST' });
    await expect(manager.assignTask('t9', 'u-maid')).rejects.toMatchObject({ code: 'BAD_REQUEST' });
    expect(await manager.assignTask('t8', 'u-maid2')).toMatchObject({ assigned_to_id: 'u-maid2' });
    expect(await manager.assignTask('t9', 'u-tech')).toMatchObject({ assigned_to_id: 'u-tech' });
    const after = await manager.listTasks();
    expect(after.find((task) => task.id === 't8')?.assigned_to_name).toBe('Гульзат М.');
    expect(after.find((task) => task.id === 't9')?.assigned_to_name).toBe('Бакыт Э.');
  });
  it('hotels are isolated: different data and no shared state', async () => {
    const a = await login('demo-marina', 'manager'); const b = await login('demo-sunrise', 'manager');
    expect((await a.listRooms())[0].code.startsWith('M-')).toBe(true);
    expect((await b.listRooms())[0].code.startsWith('S-')).toBe(true);
    await a.setRoomState('r1', 'CLEAN');
    expect((await b.listRooms())[0].state).toBe('DIRTY');
  });
  it('creates maintenance requests and validates text', async () => {
    const reception = await login('h-reception', 'reception');
    await expect(reception.createMaintenance({ room_id: 'r1', category: 'OTHER', priority: 'LOW', description: 'Door' })).rejects.toMatchObject({ code: 'FORBIDDEN' });
    const a = await login('h', 'tech');
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
  it('rejects invalid JSON instead of treating a corrupted API response as success', async () => {
    const broken = (async () => ({
      ok: true, status: 200, json: async () => { throw new SyntaxError('not json'); },
    })) as unknown as typeof fetch;
    await expect(createRealApi('https://hotel.example', broken).listTasks()).rejects.toMatchObject({ code: 'UNKNOWN' });
  });
  it('rejects malformed task and staff responses rather than showing empty work queues', async () => {
    const { f } = mk([{ body: {} }, { body: { items: [{ id: 'bad', status: 'OPEN' }] } }, { body: {} }]);
    const a = createRealApi('https://hotel.example', f);
    await expect(a.listTasks()).rejects.toMatchObject({ code: 'UNKNOWN' });
    await expect(a.listTasks()).rejects.toMatchObject({ code: 'UNKNOWN' });
    await expect(a.listStaff()).rejects.toMatchObject({ code: 'UNKNOWN' });
  });
  it('uses an abort signal on requests and never stores auth tokens in request headers', async () => {
    const { f, calls } = mk([{ body: { id: 'a', property_code: 'HOTEL', role: 'MAID' } }]);
    await createRealApi('https://hotel.example', f).me();
    expect(calls[0].init.signal).toBeTruthy();
    expect(calls[0].init.credentials).toBe('include');
    expect(JSON.stringify(calls[0].init.headers)).not.toMatch(/bearer|token|secret/i);
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
  it('maps real room operational state from task-linked rooms without inventing occupancy', async () => {
    const { f } = mk([{ body: { items: [
      { id: 't1', type: 'HOUSEKEEPING', status: 'OPEN', room_id: 'r1', room_code: '101', room_state: 'DIRTY' },
      { id: 't2', type: 'MAINTENANCE', status: 'OPEN', room_id: 'r1', room_code: '101', room_state: 'DIRTY' },
      { id: 't3', type: 'MAINTENANCE', status: 'OPEN', room_id: 'r2', room_code: '202', room_state: 'INVALID' },
    ] } }]);
    const rooms = await createRealApi('https://hotel.example', f).listRooms();
    expect(rooms).toHaveLength(2);
    expect(rooms[0]).toMatchObject({ id: 'r1', code: '101', state: 'DIRTY' });
    expect(rooms[1]).toMatchObject({ id: 'r2', code: '202', state: 'UNKNOWN' });
    expect(rooms[0].guest).toBeUndefined();
  });
  it('maps active staff and real active_tasks from PMS overview', async () => {
    const { f, calls } = mk([{ body: { staff: [
      { id: 'm1', display_name: 'Housekeeper', role: 'MAID', active_tasks: 4, active: true },
      { id: 'm2', display_name: 'Former staff', role: 'MAID', active_tasks: 0, active: false },
    ] } }]);
    const members = await createRealApi('https://hotel.example', f).listStaff();
    expect(calls[0].url).toBe('https://hotel.example/api/v1/admin/staff/overview');
    expect(members[0]).toMatchObject({ id: 'm1', open_tasks: 4, active: true });
    expect(members[1]).toMatchObject({ id: 'm2', open_tasks: 0, active: false });
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
  it('does not report committed maintenance creation as failed when read-back misses recent ticket', async () => {
    const { f, calls } = mk([
      { status: 201, body: { id: 'created-2', status: 'OPEN' } },
      { status: 200, body: { items: [] } },
    ]);
    const api = createRealApi('https://hotel.example', f);
    const ticket = await api.createMaintenance({ room_id: 'r2', category: 'PLUMBING', priority: 'HIGH', description: 'Fix shower' });
    expect(ticket).toMatchObject({ id: 'created-2', type: 'MAINTENANCE', status: 'OPEN', title: 'Fix shower', priority: 'HIGH', room_id: 'r2' });
    expect(calls.filter((x) => x.init.method === 'POST')).toHaveLength(1);
  });
  it('does not retry a committed create when the follow-up GET loses connectivity', async () => {
    let calls = 0;
    const f = (async (_url: string, init: RequestInit) => {
      calls++;
      if (init.method === 'POST') return { ok: true, status: 201, json: async () => ({ id: 'created-3', status: 'OPEN' }) } as Response;
      throw new TypeError('disconnected after commit');
    }) as typeof fetch;
    const ticket = await createRealApi('https://hotel.example', f).createMaintenance({ room_id: null, category: 'OTHER', priority: 'LOW', description: 'Broken handle' });
    expect(ticket.id).toBe('created-3');
    expect(calls).toBe(2);
  });
  it('rejects an incomplete create response rather than rendering a false task', async () => {
    const { f } = mk([{ status: 201, body: { status: 'OPEN' } }]);
    await expect(createRealApi('https://hotel.example', f).createMaintenance({
      room_id: null, category: 'OTHER', priority: 'NORMAL', description: 'Door issue',
    })).rejects.toMatchObject({ code: 'UNKNOWN' });
  });

  it('uses server-acknowledged status after a committed update when follow-up list misses task', async () => {
    const { f, calls } = mk([
      { body: { items: [{ id: 't1', type: 'HOUSEKEEPING', status: 'IN_INSPECTION', priority: 'HIGH', title: 'Room clean', room_id: 'r1', room_state: 'IN_INSPECTION' }] } },
      { body: { id: 't1', status: 'DONE' } },
      { body: { items: [] } },
    ]);
    const api = createRealApi('https://hotel.example', f);
    await api.listTasks();
    const result = await api.setTaskStatus('t1', 'DONE');
    expect(result).toMatchObject({ id: 't1', status: 'DONE', type: 'HOUSEKEEPING', title: 'Room clean' });
    expect(calls.filter((x) => x.init.method === 'PATCH')).toHaveLength(1);
  });
  it('uses task_id acknowledgment after housekeeping report even if re-read is offline', async () => {
    let req = 0;
    const fetcher = (async (_url: string, init: RequestInit) => {
      req++;
      if (req === 1) return { ok: true, status: 200, json: async () => ({ items: [{ id: 't2', type: 'HOUSEKEEPING', status: 'IN_PROGRESS', title: 'Cleaning', room_id: 'r2', room_state: 'DIRTY' }] }) } as Response;
      if (init.method === 'POST') return { ok: true, status: 200, json: async () => ({ ok: true, task_id: 't2', status: 'IN_INSPECTION', room_state: 'IN_INSPECTION' }) } as Response;
      throw new TypeError('offline after commit');
    }) as typeof fetch;
    const api = createRealApi('https://hotel.example', fetcher);
    await api.listTasks();
    const report = await api.completeHousekeeping('t2', { checklist: { BED_LINEN: true, BATHROOM: true, SURFACES: true, AMENITIES: true, FINAL_CHECK: true } });
    expect(report).toMatchObject({ id: 't2', status: 'IN_INSPECTION', room_state: 'IN_INSPECTION', type: 'HOUSEKEEPING' });
    expect(req).toBe(3);
  });
  it('uses server confirmed assignee when follow-up list does not contain the task', async () => {
    const { f } = mk([
      { body: { items: [{ id: 't3', type: 'MAINTENANCE', status: 'OPEN', title: 'Repair', assigned_to_id: null }] } },
      { body: { id: 't3', assigned_to_id: 's3', assigned_to_name: 'Technician', idempotent: false } },
      { body: { items: [] } },
    ]);
    const api = createRealApi('https://hotel.example', f);
    await api.listTasks();
    expect(await api.assignTask('t3', 's3')).toMatchObject({ id: 't3', assigned_to_id: 's3', assigned_to_name: 'Technician' });
  });
  it('never accepts a mutation acknowledgment for another task id', async () => {
    const { f } = mk([{ body: { id: 'wrong', status: 'IN_PROGRESS' } }]);
    await expect(createRealApi('https://hotel.example', f).claimTask('t1')).rejects.toMatchObject({ code: 'UNKNOWN' });
  });

  it('uses backend routes for tasks, status, assignee, complete-report', async () => {
    const { f, calls } = mk([{ body: [] }, { body: { id: 't', status: 'DONE' } }, { body: [{ id: 't', type: 'MAINTENANCE', status: 'DONE' }] }, { body: { task_id: 't', status: 'IN_INSPECTION' } }, { body: [{ id: 't', type: 'HOUSEKEEPING', status: 'IN_INSPECTION' }] }, { body: { id: 't', assigned_to_id: null } }, { body: [{ id: 't', type: 'HOUSEKEEPING', status: 'OPEN' }] }]);
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
    expect(parseHotelAddress('https://api.marina.example/core/')).toEqual({ ok: true, baseUrl: 'https://api.marina.example/core' });
    expect(hotelConnectionId('https://api.marina.example')).not.toBe(hotelConnectionId('https://api.marina.example/core'));
  });
  it('accepts the approved /core proxy prefix without allowing URLs to supply arbitrary API paths', async () => {
    const { f, calls } = (() => {
      const calls: string[] = [];
      const fetchStub = (async (url: string) => {
        calls.push(url);
        return { ok: true, status: 200, json: async () => ({ id: 'staff', role: 'MAID' }) } as Response;
      }) as typeof fetch;
      return { f: fetchStub, calls };
    })();
    await createRealApi('https://api.marina.example/core', f).me();
    expect(calls).toEqual(['https://api.marina.example/core/api/v1/auth/me']);
    for (const address of ['https://api.marina.example/path?x=1', 'https://api.marina.example/core/api/v1/auth/login', 'https://api.marina.example/core?url=https://evil.example', 'https://api.marina.example/core#fragment']) {
      expect(parseHotelAddress(address)).toMatchObject({ ok: false });
    }
  });
  it('rejects alternate ports, IP literals and internal targets embedded in QR codes', () => {
    for (const address of [
      'https://127.0.0.1', 'https://192.168.1.12', 'https://169.254.169.254',
      'https://hotel.local', 'https://hotel.internal', 'https://hotel.example:8443',
      'https://hotel.example.', 'https://a..example', 'https://[::1]/',
    ]) {
      expect(parseHotelAddress(address)).toMatchObject({ ok: false });
    }
  });
  it('rejects http, credentials, empty and dotless hosts', () => {
    expect(parseHotelAddress('http://api.marina.example')).toEqual({ ok: false, reason: 'secureOnly' });
    expect(parseHotelAddress('https://u:p@api.marina.example')).toMatchObject({ ok: false });
    expect(parseHotelAddress('')).toMatchObject({ ok: false });
    expect(parseHotelAddress('localhost')).toMatchObject({ ok: false });
  });
});
