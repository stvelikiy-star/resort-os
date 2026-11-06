import type { AuthMode, Role } from '../api/types';

export type TabKey = 'overview' | 'reception' | 'pms' | 'inbox' | 'dining' | 'kitchen' | 'tasks' | 'rooms' | 'requests' | 'admin' | 'profile';
export interface Workspace {
  tabs: TabKey[];
  taskTypes: ('HOUSEKEEPING' | 'MAINTENANCE' | 'GUEST_REQUEST')[];
  canCreateMaintenance: boolean;
  canManage: boolean;
  canSetRoomState: boolean;
  mobileReady: boolean;
}
const FIELD: Workspace = { tabs: ['profile'], taskTypes: [], canCreateMaintenance: false, canManage: false, canSetRoomState: false, mobileReady: false };
// Keep the isolated legacy demo workspace to preserve existing synthetic operational examples.
export const WORKSPACES: Record<Role, Workspace> = {
  OWNER: { tabs: ['tasks', 'rooms', 'requests', 'admin', 'profile'], taskTypes: ['HOUSEKEEPING', 'MAINTENANCE', 'GUEST_REQUEST'], canCreateMaintenance: true, canManage: true, canSetRoomState: true, mobileReady: true },
  MANAGER: { tabs: ['tasks', 'rooms', 'requests', 'admin', 'profile'], taskTypes: ['HOUSEKEEPING', 'MAINTENANCE', 'GUEST_REQUEST'], canCreateMaintenance: true, canManage: true, canSetRoomState: true, mobileReady: true },
  RECEPTION: FIELD,
  MAID: { tabs: ['tasks', 'rooms', 'profile'], taskTypes: ['HOUSEKEEPING'], canCreateMaintenance: false, canManage: false, canSetRoomState: false, mobileReady: true },
  TECHNICIAN: { tabs: ['tasks', 'requests', 'rooms', 'profile'], taskTypes: ['MAINTENANCE'], canCreateMaintenance: true, canManage: false, canSetRoomState: false, mobileReady: true },
  AGENT: FIELD, STORE_STAFF: FIELD, DINING_STAFF: FIELD, COOK: FIELD, WAITER: FIELD, CONTENT_MANAGER: FIELD, BEACH_PARTNER: FIELD,
};
export const workspaceFor = (role: Role): Workspace => WORKSPACES[role] ?? FIELD;

/** Isolated DEMO showroom. Navigation is richer than legacy synthetic operations,
 * but never implies a LIVE server permission or enables unsupported writes.
 * Existing WORKSPACES remain unchanged for the legacy task workflows.
 */
const DEMO_SHOWCASE_TABS: Partial<Record<Role, readonly TabKey[]>> = {
  OWNER: ['overview', 'pms', 'reception', 'inbox', 'admin', 'tasks', 'rooms', 'profile'],
  MANAGER: ['overview', 'tasks', 'admin', 'inbox', 'pms', 'reception', 'requests', 'rooms', 'profile'],
  RECEPTION: ['reception', 'pms', 'inbox', 'profile'],
  MAID: ['tasks', 'rooms', 'profile'],
  TECHNICIAN: ['tasks', 'requests', 'rooms', 'profile'],
  COOK: ['kitchen', 'dining', 'profile'],
  WAITER: ['dining', 'profile'],
  AGENT: ['pms', 'profile'],
};
export function demoShowcaseWorkspace(role: Role): Workspace {
  const tabs = DEMO_SHOWCASE_TABS[role];
  if (!tabs) return workspaceFor(role);
  return { ...workspaceFor(role), tabs: [...tabs], mobileReady: tabs.some(tab => tab !== 'profile') };
}

export const hasTab = (role: Role, tab: TabKey) => workspaceFor(role).tabs.includes(tab);
export const homeFor = (role: Role): `/${TabKey}` => ('/' + workspaceFor(role).tabs[0]) as `/${TabKey}`;

const LIVE_TABS: Partial<Record<Role, readonly TabKey[]>> = {
  OWNER: ['overview', 'pms', 'inbox', 'admin', 'tasks', 'rooms', 'requests', 'profile'],
  MANAGER: ['overview', 'pms', 'inbox', 'tasks', 'rooms', 'requests', 'admin', 'profile'],
  RECEPTION: ['reception', 'pms', 'inbox', 'profile'],
  MAID: ['tasks', 'rooms', 'profile'],
  TECHNICIAN: ['tasks', 'requests', 'rooms', 'profile'],
  COOK: ['kitchen', 'dining', 'profile'],
  WAITER: ['dining', 'profile'],
  AGENT: ['pms', 'profile'],
};
const MODULE: Record<TabKey, string | null> = {
  overview: 'DASHBOARD', reception: 'RESERVATIONS', pms: 'PMS', inbox: 'WHATSAPP',
  dining: 'DINING', kitchen: 'DINING', tasks: 'OPS', rooms: 'OPS', requests: 'OPS', admin: 'STAFF', profile: null,
};
/** UI visibility is only a convenience. Every endpoint still enforces hard role, property and custom module grants. */
export function workspaceForSession(
  role: Role, permissions: string[] | undefined, mode: 'LIVE' | 'DEMO',
  serverAuthMode: AuthMode | null = null,
): Workspace {
  if (mode === 'DEMO') return demoShowcaseWorkspace(role);
  const candidates = LIVE_TABS[role];
  if (!candidates || !Array.isArray(permissions)) return FIELD;
  const sharedPreview = serverAuthMode === 'shared_auth_preview';
  // SharedAuthPreviewBoundary returns 503 for inbox and dining irrespective
  // of grants. The UI must never suggest these routes are LIVE-ready.
  const tabs = candidates.filter((tab) => {
    if (sharedPreview && tab === 'dining') return false; // RC5 Inbox is server-gated; 403/503 still fail closed.
    if (tab === 'inbox') return permissions.includes('WHATSAPP') || (role !== 'RECEPTION' && permissions.includes('INBOX'));
    if (tab === 'admin') return permissions.includes('OPS') && permissions.includes('STAFF');
    return !MODULE[tab] || permissions.includes(MODULE[tab]!);
  });
  const ops = permissions.includes('OPS');
  const manager = role === 'OWNER' || role === 'MANAGER';
  return {
    tabs: tabs.length ? [...tabs] : ['profile'],
    taskTypes: ops ? workspaceFor(role).taskTypes : [],
    canCreateMaintenance: ops && workspaceFor(role).canCreateMaintenance,
    canManage: ops && permissions.includes('STAFF') && manager,
    canSetRoomState: ops && manager && !sharedPreview,
    mobileReady: tabs.some((tab) => tab !== 'profile'),
  };
}
export function hasTabForSession(
  role: Role, permissions: string[] | undefined, mode: 'LIVE' | 'DEMO',
  tab: TabKey, serverAuthMode: AuthMode | null = null,
) {
  return workspaceForSession(role, permissions, mode, serverAuthMode).tabs.includes(tab);
}
export function homeForSession(
  role: Role, permissions: string[] | undefined, mode: 'LIVE' | 'DEMO',
  serverAuthMode: AuthMode | null = null,
): `/${TabKey}` {
  return ('/' + workspaceForSession(role, permissions, mode, serverAuthMode).tabs[0]) as `/${TabKey}`;
}
