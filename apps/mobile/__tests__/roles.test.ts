import { hasTab, hasTabForSession, homeFor, homeForSession, WORKSPACES, workspaceFor, workspaceForSession } from '../src/roles/registry';
import type { Role } from '../src/api/types';

describe('role → workspace', () => {
  it('maid sees tasks/rooms/profile only', () => {
    expect(WORKSPACES.MAID.tabs).toEqual(['tasks', 'rooms', 'profile']);
    expect(hasTab('MAID', 'admin')).toBe(false);
    expect(workspaceFor('MAID').taskTypes).toEqual(['HOUSEKEEPING']);
  });
  it('technician sees maintenance, not housekeeping', () => {
    expect(workspaceFor('TECHNICIAN').taskTypes).not.toContain('HOUSEKEEPING');
    expect(hasTab('TECHNICIAN', 'requests')).toBe(true);
  });
  it('default mobile rights never offer actions denied by the current server role contract', () => {
    expect(workspaceFor('MAID').canCreateMaintenance).toBe(false);
    expect(workspaceFor('RECEPTION').canSetRoomState).toBe(false);
    expect(workspaceFor('RECEPTION').mobileReady).toBe(false);
    expect(workspaceFor('TECHNICIAN').taskTypes).toEqual(['MAINTENANCE']);
    for (const r of ['OWNER', 'MANAGER'] as Role[]) {
      expect(workspaceFor(r).canManage).toBe(true);
      expect(workspaceFor(r).canSetRoomState).toBe(true);
    }
  });
  it('only manager/owner get admin and manage rights', () => {
    const withAdmin = (Object.keys(WORKSPACES) as Role[]).filter((r) => hasTab(r, 'admin')).sort();
    expect(withAdmin).toEqual(['MANAGER', 'OWNER']);
    expect(workspaceFor('RECEPTION').canManage).toBe(false);
  });
  it('roles without a mobile workspace are marked not ready and have no data tabs', () => {
    for (const r of ['WAITER', 'COOK', 'STORE_STAFF', 'AGENT', 'CONTENT_MANAGER', 'BEACH_PARTNER'] as Role[]) {
      expect(workspaceFor(r).mobileReady).toBe(false);
      expect(workspaceFor(r).tabs).toEqual(['profile']);
    }
  });
  it('live module grants do not require unrelated OPS and hard role guards remain enforced', () => {
    expect(workspaceForSession('MAID', ['OPS'], 'LIVE').tabs).toContain('tasks');
    expect(workspaceForSession('MANAGER', ['PMS', 'STAFF'], 'LIVE').mobileReady).toBe(true);
    expect(workspaceForSession('MANAGER', ['PMS', 'WHATSAPP'], 'LIVE').tabs).toEqual(['pms', 'inbox', 'profile']);
    expect(workspaceForSession('RECEPTION', ['WHATSAPP', 'PMS', 'RESERVATIONS'], 'LIVE').tabs).toEqual(['reception', 'pms', 'inbox', 'profile']);
    expect(workspaceForSession('COOK', ['DINING'], 'LIVE').tabs).toEqual(['dining', 'profile']);
    expect(workspaceForSession('WAITER', ['DINING'], 'LIVE').tabs).toEqual(['dining', 'profile']);
    expect(workspaceForSession('RECEPTION', ['OPS'], 'LIVE').tabs).toEqual(['profile']);
    expect(hasTabForSession('MANAGER', [], 'LIVE', 'admin')).toBe(false);
    expect(homeForSession('MAID', [], 'LIVE')).toBe('/profile');
    expect(workspaceForSession('MAID', ['housekeeping'], 'DEMO').tabs).toContain('tasks');
  });
  it('unknown future server roles fail closed to profile only', () => {
    const unknown = 'DINING_STAFF' as Role;
    expect(workspaceFor(unknown).mobileReady).toBe(false);
    expect(homeFor(unknown)).toBe('/profile');
    expect(hasTab(unknown, 'admin')).toBe(false);
    expect(hasTab(unknown, 'tasks')).toBe(false);
  });
  it('landing route is always an allowed tab', () => {
    for (const r of Object.keys(WORKSPACES) as Role[]) expect(WORKSPACES[r].tabs).toContain(homeFor(r).slice(1));
    expect(homeFor('WAITER')).toBe('/profile');
    expect(homeFor('MAID')).toBe('/tasks');
  });
});

describe('LIVE backend section permissions vs mobile tab policy', () => {
  it('OWNER with OPS but without STAFF cannot open staff assignment module', () => {
    const role = workspaceForSession('OWNER', ['DASHBOARD','PMS','OPS'], 'LIVE');
    expect(role.tabs).not.toContain('admin');
    expect(role.canManage).toBe(false);
  });
  it('OWNER with both OPS and STAFF can manage assignments', () => {
    const role = workspaceForSession('OWNER', ['DASHBOARD','PMS','OPS','STAFF'], 'LIVE');
    expect(role.tabs).toContain('admin');
    expect(role.canManage).toBe(true);
  });
  it('MANAGER with INBOX grant sees Inbox; RECEPTION requires WHATSAPP grant', () => {
    expect(workspaceForSession('MANAGER',['INBOX'], 'LIVE').tabs).toContain('inbox');
    expect(workspaceForSession('RECEPTION',['INBOX'], 'LIVE').tabs).not.toContain('inbox');
    expect(workspaceForSession('RECEPTION',['WHATSAPP'], 'LIVE').tabs).toContain('inbox');
  });
});


describe('STORE_STAFF release gate', () => {
  it('never exposes inventory or another operational workspace even with unrelated grants', () => {
    const allGrants = ['OPS', 'PMS', 'FINANCE', 'STAFF', 'DINING', 'WHATSAPP', 'RESERVATIONS', 'DASHBOARD'];
    const store = workspaceForSession('STORE_STAFF', allGrants, 'LIVE');
    expect(store.tabs).toEqual(['profile']);
    expect(store.mobileReady).toBe(false);
    expect(store.canManage).toBe(false);
    expect(store.canSetRoomState).toBe(false);
    expect(store.canCreateMaintenance).toBe(false);
    expect(store.taskTypes).toEqual([]);
    for (const tab of ['overview', 'pms', 'reception', 'admin', 'dining', 'tasks', 'rooms', 'inbox', 'requests'] as const) {
      expect(hasTabForSession('STORE_STAFF', allGrants, 'LIVE', tab)).toBe(false);
    }
  });

  it('all eight operational roles keep their hard LIVE ceilings', () => {
    const allGrants = ['OPS', 'PMS', 'FINANCE', 'STAFF', 'DINING', 'WHATSAPP', 'RESERVATIONS', 'DASHBOARD'];
    const expected: Record<string, readonly string[]> = {
      OWNER: ['overview', 'pms', 'inbox', 'admin', 'tasks', 'rooms', 'requests', 'profile'],
      MANAGER: ['overview', 'pms', 'inbox', 'tasks', 'rooms', 'requests', 'admin', 'profile'],
      RECEPTION: ['reception', 'pms', 'inbox', 'profile'],
      MAID: ['tasks', 'rooms', 'profile'],
      TECHNICIAN: ['tasks', 'requests', 'rooms', 'profile'],
      COOK: ['dining', 'profile'],
      WAITER: ['dining', 'profile'],
      STORE_STAFF: ['profile'],
    };
    for (const [role, tabs] of Object.entries(expected)) {
      expect(workspaceForSession(role as Role, allGrants, 'LIVE').tabs).toEqual(tabs);
    }
  });
});
