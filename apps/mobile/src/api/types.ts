/** Types mirror the existing MARINA SMART contract (services/api/app/operations.py, auth.py). */
export type Role = 'OWNER' | 'MANAGER' | 'RECEPTION' | 'AGENT' | 'MAID' | 'TECHNICIAN' | 'STORE_STAFF' | 'COOK' | 'WAITER' | 'CONTENT_MANAGER' | 'BEACH_PARTNER';
export type TaskType = 'HOUSEKEEPING' | 'MAINTENANCE' | 'GUEST_REQUEST';
export type TaskStatus = 'OPEN' | 'IN_PROGRESS' | 'IN_INSPECTION' | 'DONE' | 'CANCELLED';
export type Priority = 'LOW' | 'NORMAL' | 'HIGH' | 'URGENT';
export type RoomState = 'UNKNOWN' | 'CLEAN' | 'DIRTY' | 'IN_INSPECTION' | 'TECH_BLOCK';

export interface AuthUser {
  id: string; username: string; display_name: string; role: Role;
  property_code: string; module_permissions: string[];
}
export interface Task {
  id: string; type: TaskType; status: TaskStatus; priority: Priority;
  title: string; room_code: string | null; room_id: string | null;
  assigned_to_id: string | null; assigned_to_name?: string | null; due_label?: string;
}
export interface Room {
  id: string; code: string; floor: number; state: RoomState;
  guest?: string | null; checkout?: string | null; arrival?: string | null; note?: string | null;
}
export interface StaffMember { id: string; display_name: string; role: Role; open_tasks: number; active?: boolean }
export interface DaySummary { occupancy_pct: number; dirty: number; blocked: number; overdue: number }
export interface NewMaintenance { room_id: string | null; category: string; priority: Priority; description: string }
export interface HousekeepingReport { checklist: Record<string, boolean>; comment?: string }

export class ApiError extends Error {
  constructor(public code: 'OFFLINE' | 'FORBIDDEN' | 'NOT_FOUND' | 'CONFLICT' | 'UNAUTHORIZED' | 'BAD_REQUEST' | 'UNKNOWN', message?: string) {
    super(message ?? code);
  }
}

/** One implementation per hotel connection. Screens depend only on this interface. */
export interface StaffApi {
  readonly mode: 'DEMO' | 'LIVE';
  login(username: string, password: string): Promise<AuthUser>;
  logout(): Promise<void>;
  me(): Promise<AuthUser>;
  listTasks(filter?: { type?: TaskType; status?: TaskStatus }): Promise<Task[]>;
  claimTask(id: string): Promise<Task>;
  setTaskStatus(id: string, status: TaskStatus): Promise<Task>;
  completeHousekeeping(id: string, report: HousekeepingReport): Promise<Task>;
  createMaintenance(req: NewMaintenance): Promise<Task>;
  listRooms(): Promise<Room[]>;
  setRoomState(roomId: string, state: RoomState): Promise<Room>;
  listStaff(): Promise<StaffMember[]>;
  assignTask(taskId: string, staffId: string | null): Promise<Task>;
  daySummary(): Promise<DaySummary>;
}

export const HOUSEKEEPING_CHECKLIST = ['BED_LINEN', 'BATHROOM', 'SURFACES', 'AMENITIES', 'FINAL_CHECK'] as const;

/** Mirrors TASK_TRANSITIONS in services/api/app/operations.py. */
export const TRANSITIONS: Record<TaskType, Record<TaskStatus, TaskStatus[]>> = {
  HOUSEKEEPING: { OPEN: ['IN_PROGRESS', 'CANCELLED'], IN_PROGRESS: ['IN_INSPECTION', 'CANCELLED'], IN_INSPECTION: ['IN_PROGRESS', 'DONE', 'CANCELLED'], DONE: [], CANCELLED: [] },
  MAINTENANCE: { OPEN: ['IN_PROGRESS', 'CANCELLED'], IN_PROGRESS: ['DONE', 'CANCELLED'], IN_INSPECTION: [], DONE: [], CANCELLED: [] },
  GUEST_REQUEST: { OPEN: ['IN_PROGRESS', 'CANCELLED'], IN_PROGRESS: ['DONE', 'CANCELLED'], IN_INSPECTION: [], DONE: [], CANCELLED: [] },
};
export function canTransition(type: TaskType, from: TaskStatus, to: TaskStatus): boolean {
  return TRANSITIONS[type][from].includes(to);
}
