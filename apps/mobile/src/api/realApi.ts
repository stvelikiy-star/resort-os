import { createHotelHttpClient, HttpMethod } from './http';
import { authUserResponse, itemsEnvelope } from './contractValidation';
import { safeRouteId } from './routeId';
import { checkedHotelSelector } from './sharedHotelAuth';
import { ApiError, DaySummary, HousekeepingReport, NewMaintenance, Room, RoomState, StaffApi, StaffMember, Task, TaskStatus, TaskType, HOUSEKEEPING_CHECKLIST } from './types';

type Fetch = typeof fetch;

/**
 * Real implementation against the EXISTING MARINA SMART API of ONE hotel (property-pinned host).
 * Interim auth = the server's httpOnly cookie session (`resort_session`). No secrets live in the app.
 * Bearer/refresh tokens + device registry are backend work item B1/B2 (see docs) and are NOT assumed here.
 */
export function createRealApi(baseUrl: string, fetchImpl: Fetch = fetch, sessionIsActive?: () => boolean): StaffApi {
  const http = createHotelHttpClient(baseUrl, fetchImpl, sessionIsActive);
  // Most recent server-provided records for safe post-commit readback fallback.
  // Never synthesize an unseen task or claim that a missing write succeeded.
  const lastKnownTasks = new Map<string, Task>();
  const lastKnownRooms = new Map<string, Room>();
  let verifiedServerMode: 'shared_auth_preview' | 'single_property' | null = null;

  const call = <T,>(method: string, path: string, body?: unknown) => http.request<T>(method as HttpMethod, path, body);

  const mapTask = (t: any): Task => {
    if (!t || typeof t.id !== 'string' || !t.id || !['HOUSEKEEPING', 'MAINTENANCE', 'GUEST_REQUEST'].includes(t.type) || !['OPEN', 'IN_PROGRESS', 'IN_INSPECTION', 'DONE', 'CANCELLED'].includes(t.status)) throw new ApiError('UNKNOWN', 'Invalid task record');
    const mapped: Task = {
      id: String(t.id), type: t.type, status: t.status, priority: t.priority ?? 'NORMAL',
      title: t.title ?? '', room_code: t.room_code ?? t.roomCode ?? null, room_id: t.room_id ?? t.roomId ?? null,
      room_state: ['CLEAN', 'DIRTY', 'IN_INSPECTION', 'TECH_BLOCK'].includes(t.room_state) ? t.room_state : 'UNKNOWN',
      assigned_to_id: t.assigned_to_id ?? t.assignedToId ?? null, assigned_to_name: t.assigned_to_name ?? null,
    };
    lastKnownTasks.set(mapped.id, mapped);
    return mapped;
  };

  /**
   * A mutation can commit even when its subsequent GET fails (e.g., >300 tasks,
   * temporary network failure). Accept only the server's acknowledged fields
   * and merge them into a previously observed task; never fabricate details.
   */
  async function committedTask(id: string, acknowledged: unknown): Promise<Task> {
    if (!acknowledged || typeof acknowledged !== 'object' ||
        ((acknowledged as { id?: unknown; task_id?: unknown }).id ?? (acknowledged as { task_id?: unknown }).task_id) !== id) {
      throw new ApiError('UNKNOWN', 'Invalid mutation acknowledgment');
    }
    const ack = acknowledged as { status?: TaskStatus; assigned_to_id?: string | null; assigned_to_name?: string | null; room_state?: RoomState };
    try {
      return await findTask(id);
    } catch (error) {
      if (!(error instanceof ApiError) || !['NOT_FOUND', 'OFFLINE', 'UNKNOWN'].includes(error.code)) throw error;
      const previous = lastKnownTasks.get(id);
      if (!previous) throw new ApiError('UNKNOWN', 'Mutation committed, but task details are unavailable');
      const status = ack.status && ['OPEN', 'IN_PROGRESS', 'IN_INSPECTION', 'DONE', 'CANCELLED'].includes(ack.status)
        ? ack.status : previous.status;
      const hasAssignee = Object.prototype.hasOwnProperty.call(ack, 'assigned_to_id');
      const updated: Task = {
        ...previous, status,
        assigned_to_id: hasAssignee ? ack.assigned_to_id ?? null : previous.assigned_to_id,
        assigned_to_name: hasAssignee ? (ack.assigned_to_name ?? (ack.assigned_to_id === previous.assigned_to_id ? previous.assigned_to_name : null)) : previous.assigned_to_name,
        room_state: ack.room_state && ['CLEAN', 'DIRTY', 'IN_INSPECTION', 'TECH_BLOCK'].includes(ack.room_state) ? ack.room_state : previous.room_state,
      };
      lastKnownTasks.set(id, updated);
      return updated;
    }
  }

  return {
    mode: 'LIVE',
    authMode: async () => {
      const response = await call<unknown>('GET', '/api/v1/auth/mode');
      const mode = (response as { mode?: unknown } | null)?.mode;
      if (mode !== 'shared_auth_preview' && mode !== 'single_property') {
        throw new ApiError('UNKNOWN', 'Unrecognized server authentication mode');
      }
      verifiedServerMode = mode;
      return mode;
    },
    login: async (username, password, selector) => {
      const chosen = selector === undefined ? {} : checkedHotelSelector(selector);
      return authUserResponse(await call<unknown>('POST', '/api/v1/auth/login', { username, password, ...chosen }));
    },
    logout: () => call<void>('POST', '/api/v1/auth/logout'),
    me: async () => authUserResponse(await call<unknown>('GET', '/api/v1/auth/me')),
    async listTasks(filter?: { type?: TaskType; status?: TaskStatus }) {
      const q = new URLSearchParams();
      if (filter?.type) q.set('type', filter.type);
      if (filter?.status) q.set('status', filter.status);
      const raw = await call<unknown>('GET', `/api/v1/ops/tasks${q.size ? `?${q}` : ''}`);
      return itemsEnvelope(raw, 'tasks', true).map(mapTask);
    },
    async claimTask(id) { const key = safeRouteId(id); const ack = await call('POST', `/api/v1/ops/tasks/${key}/claim`); return committedTask(key, ack); },
    async setTaskStatus(id, status) { const key = safeRouteId(id); const ack = await call('PATCH', `/api/v1/ops/tasks/${key}/status`, { status }); return committedTask(key, ack); },
    async completeHousekeeping(id, report: HousekeepingReport) {
      const key = safeRouteId(id);
      const ack = await call('POST', `/api/v1/ops/tasks/${key}/complete-report`, {
        summary: report.comment?.trim() || 'Cleaning completed',
        checklist: HOUSEKEEPING_CHECKLIST.map((code) => ({ code, label: code, done: !!report.checklist[code] })),
        // Optional evidence_urls omitted: no attachment API or fake evidence upload.
      });
      return committedTask(key, ack);
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
        if (!existing) seen.set(t.room_id, { id: t.room_id, code: t.room_code ?? '—', floor: null, state });
        else if (existing.state === 'UNKNOWN' && state !== 'UNKNOWN') existing.state = state;
      }
      for (const room of seen.values()) lastKnownRooms.set(room.id, room);
      return [...seen.values()];
    },
    async setRoomState(roomId, state: RoomState) {
      if (verifiedServerMode === 'shared_auth_preview') {
        // SharedAuthPreviewBoundary never admits room-state PATCH (503).
        // No optimistic writes or status simulation.
        throw new ApiError('UNKNOWN', 'Room-state override is unavailable in shared PMS staging');
      }
      const key = safeRouteId(roomId);
      // Never invent the code/floor after changing state. The current server
      // acknowledges only {room_id,state}; preserve an already observed room.
      const previous = lastKnownRooms.get(key) ?? (await this.listRooms()).find(r => r.id === key);
      if (!previous) throw new ApiError('NOT_FOUND', 'Room is not present in the staff-visible room list');
      const ack = await call<{room_id: string;state: RoomState}>('PATCH', `/api/v1/ops/rooms/${key}/state`, { state });
      if (!ack || ack.room_id !== key || ack.state !== state) throw new ApiError('UNKNOWN', 'Room state acknowledgment not verified');
      const updated = {...previous, state};
      lastKnownRooms.set(key, updated);
      return updated;
    },
    async listStaff(): Promise<StaffMember[]> {
      const raw = await call<any>('GET', '/api/v1/admin/staff/overview');
      const list: any[] = raw?.staff ?? raw?.items;
      if (!Array.isArray(list)) throw new ApiError('UNKNOWN', 'Invalid staff overview response');
      return list.map((s) => ({ id: String(s.id), display_name: s.display_name ?? s.username, role: s.role, open_tasks: s.active_tasks ?? s.open_tasks ?? 0, active: s.active !== false }));
    },
    async assignTask(taskId, staffId) {
      const key = safeRouteId(taskId);
      const assignedTo = staffId === null ? null : safeRouteId(staffId);
      const ack = await call('PATCH', `/api/v1/ops/tasks/${key}/assignee`, { assigned_to_id: assignedTo });
      return committedTask(key, ack);
    },
    async daySummary(): Promise<DaySummary> {
      // No aggregate endpoint in the existing contract yet (backend item B8).
      throw new ApiError('NOT_FOUND', 'summary endpoint not available');
    },
  };

  async function findTask(id: string): Promise<Task> {
    const items = itemsEnvelope(await call<unknown>('GET', '/api/v1/ops/tasks?limit=300'), 'tasks', true);
    const t = items.find((x: any) => String(x?.id) === id);
    if (!t) throw new ApiError('NOT_FOUND');
    return mapTask(t);
  }
}
