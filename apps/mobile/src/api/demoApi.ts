import { ApiError, AuthUser, canTransition, DaySummary, HousekeepingReport, NewMaintenance, Role, Room, RoomState, StaffApi, StaffMember, Task, TaskStatus, TaskType, HOUSEKEEPING_CHECKLIST } from './types';

export const DEMO_USERS: Record<string, { user: AuthUser; password: string }> = {
  maid: { password: 'demo', user: { id: 'u-maid', username: 'maid', display_name: 'Айгерим Т.', role: 'MAID', property_code: 'DEMO', module_permissions: ['housekeeping'] } },
  tech: { password: 'demo', user: { id: 'u-tech', username: 'tech', display_name: 'Бакыт Э.', role: 'TECHNICIAN', property_code: 'DEMO', module_permissions: ['maintenance'] } },
  reception: { password: 'demo', user: { id: 'u-rec', username: 'reception', display_name: 'Нурзат К.', role: 'RECEPTION', property_code: 'DEMO', module_permissions: ['reception', 'housekeeping'] } },
  manager: { password: 'demo', user: { id: 'u-mgr', username: 'manager', display_name: 'Эмиль С.', role: 'MANAGER', property_code: 'DEMO', module_permissions: ['*'] } },
  waiter: { password: 'demo', user: { id: 'u-wait', username: 'waiter', display_name: 'Тимур А.', role: 'WAITER', property_code: 'DEMO', module_permissions: ['dining'] } },
};
export const DEMO_ROLE_LOGINS: { username: string; role: Role }[] = Object.values(DEMO_USERS).map((d) => ({ username: d.user.username, role: d.user.role }));

const STAFF: StaffMember[] = [
  { id: 'u-maid', display_name: 'Айгерим Т.', role: 'MAID', open_tasks: 3 },
  { id: 'u-maid2', display_name: 'Гульзат М.', role: 'MAID', open_tasks: 1 },
  { id: 'u-tech', display_name: 'Бакыт Э.', role: 'TECHNICIAN', open_tasks: 2 },
];

function seed(hotelId: string): { rooms: Room[]; tasks: Task[] } {
  // Distinct data per hotel proves a connection never reads another hotel's state.
  const second = hotelId.includes('sunrise');
  const prefix = second ? 'S' : 'M';
  const rooms: Room[] = [
    { id: 'r1', code: `${prefix}-101`, floor: 1, state: 'DIRTY', guest: null, checkout: 'сегодня 12:00' },
    { id: 'r2', code: `${prefix}-102`, floor: 1, state: 'CLEAN', guest: 'A. Ivanov', arrival: null },
    { id: 'r3', code: `${prefix}-205`, floor: 2, state: 'IN_INSPECTION', guest: null },
    { id: 'r4', code: `${prefix}-206`, floor: 2, state: 'DIRTY', guest: null, checkout: 'сегодня 11:00' },
    { id: 'r5', code: `${prefix}-310`, floor: 3, state: 'TECH_BLOCK', note: 'AC' },
    { id: 'r6', code: `${prefix}-311`, floor: 3, state: 'CLEAN', arrival: 'сегодня 14:00' },
  ];
  const tasks: Task[] = [
    { id: 't1', type: 'HOUSEKEEPING', status: 'OPEN', priority: 'URGENT', title: 'Уборка после выезда', room_code: rooms[0].code, room_id: 'r1', assigned_to_id: 'u-maid', due_label: '12:30' },
    { id: 't2', type: 'HOUSEKEEPING', status: 'IN_PROGRESS', priority: 'HIGH', title: 'Генеральная уборка', room_code: rooms[3].code, room_id: 'r4', assigned_to_id: 'u-maid', due_label: '13:00' },
    { id: 't3', type: 'HOUSEKEEPING', status: 'IN_INSPECTION', priority: 'NORMAL', title: 'Проверка после уборки', room_code: rooms[2].code, room_id: 'r3', assigned_to_id: 'u-maid2', due_label: '11:00' },
    { id: 't4', type: 'MAINTENANCE', status: 'OPEN', priority: 'HIGH', title: 'Не охлаждает кондиционер', room_code: rooms[4].code, room_id: 'r5', assigned_to_id: 'u-tech', due_label: '15:00' },
    { id: 't5', type: 'MAINTENANCE', status: 'IN_PROGRESS', priority: 'NORMAL', title: 'Течёт кран в ванной', room_code: rooms[1].code, room_id: 'r2', assigned_to_id: 'u-tech', due_label: '16:00' },
    { id: 't6', type: 'GUEST_REQUEST', status: 'OPEN', priority: 'NORMAL', title: 'Дополнительные полотенца', room_code: rooms[1].code, room_id: 'r2', assigned_to_id: null, due_label: '10:30' },
    { id: 't7', type: 'HOUSEKEEPING', status: 'DONE', priority: 'LOW', title: 'Уборка завершена', room_code: rooms[5].code, room_id: 'r6', assigned_to_id: 'u-maid', due_label: '09:00' },
    { id: 't8', type: 'HOUSEKEEPING', status: 'OPEN', priority: 'HIGH', title: 'Уборка к заселению', room_code: rooms[5].code, room_id: 'r6', assigned_to_id: null, due_label: '14:00' },
    { id: 't9', type: 'MAINTENANCE', status: 'OPEN', priority: 'NORMAL', title: 'Проверить освещение', room_code: rooms[1].code, room_id: 'r2', assigned_to_id: null, due_label: '17:00' },
  ];
  return { rooms, tasks };
}

const delay = (ms = 120) => new Promise<void>((r) => setTimeout(r, ms));

export function createDemoApi(hotelId: string, latency = 120): StaffApi {
  const data = seed(hotelId);
  let user: AuthUser | null = null;
  const need = (): AuthUser => { if (!user) throw new ApiError('UNAUTHORIZED'); return user; };
  const find = (id: string) => { const t = data.tasks.find((x) => x.id === id); if (!t) throw new ApiError('NOT_FOUND'); return t; };
  const nameOf = (id: string | null) => STAFF.find((s) => s.id === id)?.display_name ?? null;
  const out = (t: Task): Task => ({ ...t, assigned_to_name: nameOf(t.assigned_to_id) });
  const isManager = (u: AuthUser) => u.role === 'MANAGER' || u.role === 'OWNER';
  const allowedTypes = (u: AuthUser): TaskType[] =>
    isManager(u) ? ['HOUSEKEEPING', 'MAINTENANCE', 'GUEST_REQUEST'] :
    u.role === 'MAID' ? ['HOUSEKEEPING'] :
    u.role === 'TECHNICIAN' ? ['MAINTENANCE'] : [];
  const mayOperate = (u: AuthUser, task: Task) => allowedTypes(u).includes(task.type);

  return {
    mode: 'DEMO',
    async authMode() { return 'demo' as const; },
    async login(username, password) {
      await delay(latency);
      const d = DEMO_USERS[username.trim().toLowerCase()];
      if (!d || d.password !== password) throw new ApiError('UNAUTHORIZED');
      user = d.user;
      return d.user;
    },
    async logout() { user = null; },
    async me() { return need(); },
    async listTasks(filter) {
      await delay(latency);
      const u = need();
      const allowed = allowedTypes(u);
      return data.tasks
        .filter((t) => allowed.includes(t.type) && (!filter?.type || t.type === filter.type) && (!filter?.status || t.status === filter.status))
        .filter((t) => isManager(u) || t.assigned_to_id === u.id || t.assigned_to_id === null)
        .map(out);
    },
    async claimTask(id) {
      await delay(latency); const u = need(); const t = find(id);
      if (!mayOperate(u, t)) throw new ApiError('FORBIDDEN');
      if (t.assigned_to_id && t.assigned_to_id !== u.id) throw new ApiError('CONFLICT');
      if (t.status !== 'OPEN' && t.status !== 'IN_PROGRESS') throw new ApiError('CONFLICT');
      t.assigned_to_id = u.id; t.status = 'IN_PROGRESS'; return out(t);
    },
    async setTaskStatus(id, status: TaskStatus) {
      await delay(latency); const u = need(); const t = find(id);
      if (!mayOperate(u, t)) throw new ApiError('FORBIDDEN');
      if (!isManager(u) && t.assigned_to_id !== u.id) throw new ApiError('FORBIDDEN');
      if (status === 'CANCELLED' && !isManager(u)) throw new ApiError('FORBIDDEN');
      if (t.type === 'HOUSEKEEPING' && t.status === 'IN_INSPECTION' && !isManager(u)) throw new ApiError('FORBIDDEN');
      if (!canTransition(t.type, t.status, status)) throw new ApiError('CONFLICT');
      t.status = status; return out(t);
    },
    async completeHousekeeping(id, report: HousekeepingReport) {
      await delay(latency); const u = need(); const t = find(id);
      if (u.role !== 'MAID' || t.type !== 'HOUSEKEEPING') throw new ApiError('FORBIDDEN');
      if (t.assigned_to_id !== u.id) throw new ApiError('FORBIDDEN');
      if (t.status !== 'IN_PROGRESS') throw new ApiError('CONFLICT');
      if (!HOUSEKEEPING_CHECKLIST.every((c) => report.checklist[c])) throw new ApiError('BAD_REQUEST');
      t.status = 'IN_INSPECTION'; return out(t);
    },
    async createMaintenance(req: NewMaintenance) {
      await delay(latency); const u = need();
      if (!allowedTypes(u).includes('MAINTENANCE')) throw new ApiError('FORBIDDEN');
      if (req.description.trim().length < 2) throw new ApiError('BAD_REQUEST');
      const room = data.rooms.find((r) => r.id === req.room_id) ?? null;
      const t: Task = { id: `t${data.tasks.length + 1}`, type: 'MAINTENANCE', status: 'OPEN', priority: req.priority, title: req.description.trim().slice(0, 80), room_code: room?.code ?? null, room_id: room?.id ?? null, assigned_to_id: null, due_label: '—' };
      void u; data.tasks.unshift(t); return out(t);
    },
    async listRooms() { await delay(latency); need(); return data.rooms.map((r) => ({ ...r })); },
    async setRoomState(roomId, state: RoomState) {
      await delay(latency); const u = need(); const r = data.rooms.find((x) => x.id === roomId);
      if (!r) throw new ApiError('NOT_FOUND');
      if (!isManager(u)) throw new ApiError('FORBIDDEN');
      r.state = state; return { ...r };
    },
    async listStaff() {
      await delay(latency); if (!isManager(need())) throw new ApiError('FORBIDDEN');
      return STAFF.map((s) => ({ ...s, open_tasks: data.tasks.filter((t) => t.assigned_to_id === s.id && t.status !== 'DONE' && t.status !== 'CANCELLED').length }));
    },
    async assignTask(taskId, staffId) {
      await delay(latency); if (!isManager(need())) throw new ApiError('FORBIDDEN');
      const t = find(taskId); const s = STAFF.find((x) => x.id === staffId);
      if (t.status === 'DONE' || t.status === 'CANCELLED') throw new ApiError('CONFLICT');
      if (staffId && !s) throw new ApiError('NOT_FOUND');
      const expected = t.type === 'HOUSEKEEPING' ? 'MAID' : t.type === 'MAINTENANCE' ? 'TECHNICIAN' : null;
      if (s && (!expected || s.role !== expected || s.active === false)) throw new ApiError('BAD_REQUEST');
      t.assigned_to_id = staffId; return out(t);
    },
    async daySummary(): Promise<DaySummary> {
      await delay(latency); if (!isManager(need())) throw new ApiError('FORBIDDEN');
      return { occupancy_pct: 72, dirty: data.rooms.filter((r) => r.state === 'DIRTY').length, blocked: data.rooms.filter((r) => r.state === 'TECH_BLOCK').length, overdue: 1 };
    },
  };
}
