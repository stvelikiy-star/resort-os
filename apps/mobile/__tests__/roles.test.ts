import { hasTab, homeFor, WORKSPACES, workspaceFor } from '../src/roles/registry';
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
  it('landing route is always an allowed tab', () => {
    for (const r of Object.keys(WORKSPACES) as Role[]) expect(WORKSPACES[r].tabs).toContain(homeFor(r).slice(1));
    expect(homeFor('WAITER')).toBe('/profile');
    expect(homeFor('MAID')).toBe('/tasks');
  });
});
