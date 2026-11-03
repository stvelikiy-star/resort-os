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
  it('live staff missing OPS permission see profile only despite a valid role', () => {
    expect(workspaceForSession('MAID', ['OPS'], 'LIVE').tabs).toContain('tasks');
    expect(workspaceForSession('MANAGER', ['PMS', 'STAFF'], 'LIVE').mobileReady).toBe(false);
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
