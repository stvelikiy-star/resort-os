import type { Role } from '../api/types';

export type TabKey = 'tasks' | 'rooms' | 'requests' | 'admin' | 'profile';

export interface Workspace {
  tabs: TabKey[];
  /** task types shown on the main screen */
  taskTypes: ('HOUSEKEEPING' | 'MAINTENANCE' | 'GUEST_REQUEST')[];
  canCreateMaintenance: boolean;
  canManage: boolean; // inspection queue, assignment, summary
  canSetRoomState: boolean;
  mobileReady: boolean; // false = role has no dedicated mobile workspace yet
}

const FIELD: Workspace = { tabs: ['profile'], taskTypes: [], canCreateMaintenance: false, canManage: false, canSetRoomState: false, mobileReady: false };

/** Role → workspace. UI gating only; the server remains the single authority (403). */
export const WORKSPACES: Record<Role, Workspace> = {
  OWNER: { tabs: ['tasks', 'rooms', 'requests', 'admin', 'profile'], taskTypes: ['HOUSEKEEPING', 'MAINTENANCE', 'GUEST_REQUEST'], canCreateMaintenance: true, canManage: true, canSetRoomState: true, mobileReady: true },
  MANAGER: { tabs: ['tasks', 'rooms', 'requests', 'admin', 'profile'], taskTypes: ['HOUSEKEEPING', 'MAINTENANCE', 'GUEST_REQUEST'], canCreateMaintenance: true, canManage: true, canSetRoomState: true, mobileReady: true },
  RECEPTION: { tabs: ['profile'], taskTypes: [], canCreateMaintenance: false, canManage: false, canSetRoomState: false, mobileReady: false },
  MAID: { tabs: ['tasks', 'rooms', 'profile'], taskTypes: ['HOUSEKEEPING'], canCreateMaintenance: false, canManage: false, canSetRoomState: false, mobileReady: true },
  TECHNICIAN: { tabs: ['tasks', 'requests', 'rooms', 'profile'], taskTypes: ['MAINTENANCE'], canCreateMaintenance: true, canManage: false, canSetRoomState: false, mobileReady: true },
  AGENT: FIELD, STORE_STAFF: FIELD, COOK: FIELD, WAITER: FIELD, CONTENT_MANAGER: FIELD, BEACH_PARTNER: FIELD,
};

export const workspaceFor = (role: Role): Workspace => WORKSPACES[role] ?? FIELD;
export const hasTab = (role: Role, tab: TabKey) => workspaceFor(role).tabs.includes(tab);

/** First tab a role may open — used as the landing route after sign-in. */
export const homeFor = (role: Role): `/${TabKey}` => `/${workspaceFor(role).tabs[0]}`;

/**
 * Server-provided permission grants are authoritative for LIVE accounts.
 * A role alone does not prove access when the owner has revoked OPS.
 * Demo users use simplified local labels, so this gate applies only to LIVE.
 */
export function workspaceForSession(role: Role, permissions: string[] | undefined, mode: 'LIVE' | 'DEMO'): Workspace {
  const base = workspaceFor(role);
  if (mode === 'DEMO') return base;
  if (!Array.isArray(permissions) || !permissions.includes('OPS')) {
    return FIELD;
  }
  return base;
}

export function hasTabForSession(role: Role, permissions: string[] | undefined, mode: 'LIVE' | 'DEMO', tab: TabKey): boolean {
  return workspaceForSession(role, permissions, mode).tabs.includes(tab);
}

export function homeForSession(role: Role, permissions: string[] | undefined, mode: 'LIVE' | 'DEMO'): `/${TabKey}` {
  return `/${workspaceForSession(role, permissions, mode).tabs[0]}`;
}
