import { parseHotelAddress } from './hotels';
import { ApiError, AuthUser, DaySummary, HousekeepingReport, NewMaintenance, Room, RoomState, StaffApi, StaffMember, Task, TaskStatus, TaskType, HOUSEKEEPING_CHECKLIST } from './types';

type Fetch = typeof fetch;

/**
 * Real implementation against the EXISTING MARINA SMART API of ONE hotel (property-pinned host).
 * Interim auth = the server's httpOnly cookie session (`resort_session`). No secrets live in the app.
 * Bearer/refresh tokens + device registry are backend work item B1/B2 (see docs) and are NOT assumed here.
 */
export function createRealApi(baseUrl: string, fetchImpl: Fetch = fetch): StaffApi {
  const validated = parseHotelAddress(baseUrl);
  if (!validated.ok) throw new Error('Invalid or insecure hotel API origin');
  const root = validated.baseUrl;

  async function call<T>(method: string, path: string, body?: unknown): Promise<T> {
    let res: Response;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), method === 'GET' ? 15000 : 25000);
    try {
      res = await fetchImpl(`${root}${path}`, {
        method, credentials: 'include', signal: controller.signal,
        headers: { Accept: 'application/json', ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}) },
        body: body !== undefined ? JSON.stringify(body) : undefined,
      });
    } catch {
      throw new ApiError('OFFLINE');
    } finally {
      clearTimeout(timeout);
    }
    if (res.status === 204) return undefined as T;
    if (!res.ok) {
      const code = res.status === 401 ? 'UNAUTHORIZED' : res.status === 403 ? 'FORBIDDEN' : res.status === 404 ? 'NOT_FOUND' : res.status === 409 ? 'CONFLICT' : res.status === 400 || res.status === 422 ? 'BAD_REQUEST' : 'UNKNOWN';
      throw new ApiError(code, `HTTP ${res.status}`);
    }
    try { return (await res.json()) as T; }
    catch { throw new ApiError('UNKNOWN', 'Invalid JSON response from hotel API'); }
  }

  const mapTask = (t: any): Task => {
    if (!t || typeof t.id !== 'string' || !t.id || !['HOUSEKEEPING', 'MAINTENANCE', 'GUEST_REQUEST'].includes(t.type) || !['OPEN', 'IN_PROGRESS', 'IN_INSPECTION', 'DONE', 'CANCELLED'].includes(t.status)) throw new ApiError('UNKNOWN', 'Invalid task record');
    return ({
    id: String(t.id), type: t.type, status: t.status, priority: t.priority ?? 'NORMAL',
    title: t.title ?? '', room_code: t.room_code ?? t.roomCode ?? null, room_id: t.room_id ?? t.roomId ?? null,
    room_state: ['CLEAN', 'DIRTY', 'IN_INSPECTION', 'TECH_BLOCK'].includes(t.room_state) ? t.room_state : 'UNKNOWN',
    assigned_to_id: t.assigned_to_id ?? t.assignedToId ?? null, assigned_to_name: t.assigned_to_name ?? null,
  });
  };

  return {
    mode: 'LIVE',
    login: (username, password) => call<AuthUser>('POST', '/api/v1/auth/login', { username, password }),
    logout: () => call<void>('POST', '/api/v1/auth/logout'),
    me: () => call<AuthUser>('GET', '/api/v1/auth/me'),
    async listTasks(filter?: { type?: TaskType; status?: TaskStatus }) {
      const q = new URLSearchParams();
      if (filter?.type) q.set('type', filter.type);
      if (filter?.status) q.set('status', filter.status);
      const raw = await call<any>('GET', `/api/v1/ops/tasks${q.size ? `?${q}` : ''}`);
      const items = Array.isArray(raw) ? raw : raw?.items;
      if (!Array.isArray(items)) throw new ApiError('UNKNOWN', 'Invalid tasks list response');
      return items.map(mapTask);
    },
    async claimTask(id) { await call('POST', `/api/v1/ops/tasks/${id}/claim`); return findTask(id); },
    async setTaskStatus(id, status) { await call('PATCH', `/api/v1/ops/tasks/${id}/status`, { status }); return findTask(id); },
    async completeHousekeeping(id, report: HousekeepingReport) {
      await call('POST', `/api/v1/ops/tasks/${id}/complete-report`, {
        summary: report.comment?.trim() || 'Cleaning completed',
        checklist: HOUSEKEEPING_CHECKLIST.map((code) => ({ code, label: code, done: !!report.checklist[code] })),
        evidence_urls: [], // photo upload needs the attachments API (backend item B5)
      });
      return findTask(id);
    },
    async createMaintenance(req: NewMaintenance) {
      const created = await call<any>('POST', '/api/v1/ops/tasks', {
        type: 'MAINTENANCE', room_id: req.room_id, priority: req.priority,
        title: req.description.trim().slice(0, 180), description: `[${req.category}] ${req.description.trim()}`, source: 'MOBILE',
      });
      // POST /tasks commits the mutation and returns only {id,status}.
      // Failure to re-read the first 300 tasks must NEVER make the user repeat
      // an already-created request (and accidentally create a duplicate).
      if (!created || typeof created.id !== 'string' || !created.id || created.status !== 'OPEN') {
        throw new ApiError('UNKNOWN', 'Unexpected create acknowledgment from hotel API');
      }
      try { return await findTask(created.id); }
      catch (e) {
        // The acknowledged create is already successful; show only values
        // guaranteed by the submitted payload and server acknowledgment.
        if (!(e instanceof ApiError) || !['NOT_FOUND', 'OFFLINE', 'UNKNOWN'].includes(e.code)) throw e;
        return {
          id: created.id, type: 'MAINTENANCE', status: 'OPEN',
          priority: req.priority, title: req.description.trim().slice(0, 180),
          room_id: req.room_id, room_code: null,
          assigned_to_id: null, assigned_to_name: null,
        };
      }
    },
    async listRooms(): Promise<Room[]> {
      // The existing API exposes no staff "rooms list" endpoint: derive rooms from tasks until backend item B7 lands.
      const tasks = await this.listTasks();
      const seen = new Map<string, Room>();
      for (const t of tasks) if (t.room_id) {
        const existing = seen.get(t.room_id);
        const state = t.room_state ?? 'UNKNOWN';
        if (!existing) seen.set(t.room_id, { id: t.room_id, code: t.room_code ?? '—', floor: 0, state });
        else if (existing.state === 'UNKNOWN' && state !== 'UNKNOWN') existing.state = state;
      }
      return [...seen.values()];
    },
    async setRoomState(roomId, state: RoomState) {
      await call('PATCH', `/api/v1/ops/rooms/${roomId}/state`, { state });
      return { id: roomId, code: '', floor: 0, state };
    },
    async listStaff(): Promise<StaffMember[]> {
      const raw = await call<any>('GET', '/api/v1/admin/staff/overview');
      const list: any[] = raw?.staff ?? raw?.items;
      if (!Array.isArray(list)) throw new ApiError('UNKNOWN', 'Invalid staff overview response');
      return list.map((s) => ({ id: String(s.id), display_name: s.display_name ?? s.username, role: s.role, open_tasks: s.active_tasks ?? s.open_tasks ?? 0, active: s.active !== false }));
    },
    async assignTask(taskId, staffId) {
      await call('PATCH', `/api/v1/ops/tasks/${taskId}/assignee`, { assigned_to_id: staffId });
      return findTask(taskId);
    },
    async daySummary(): Promise<DaySummary> {
      // No aggregate endpoint in the existing contract yet (backend item B8).
      throw new ApiError('NOT_FOUND', 'summary endpoint not available');
    },
  };

  async function findTask(id: string): Promise<Task> {
    const list = await call<any>('GET', '/api/v1/ops/tasks?limit=300');
    const items = Array.isArray(list) ? list : list?.items;
    if (!Array.isArray(items)) throw new ApiError('UNKNOWN', 'Invalid tasks list response');
    const t = items.find((x: any) => String(x.id) === id);
    if (!t) throw new ApiError('NOT_FOUND');
    return mapTask(t);
  }
}
