import { mobileTabPlan } from '../src/roles/navigation';
import { hasTabForSession, workspaceForSession } from '../src/roles/registry';
import { mobileCopyStrings } from '../src/i18n/mobileCopy';

describe('role-aware compact bottom navigation', () => {
  it('uses concise, localized navigation labels rather than truncating PMS and Home at 320–375dp', () => {
    for (const locale of ['ru', 'kg', 'en', 'kz'] as const) {
      const copy = mobileCopyStrings[locale];
      expect(copy.pmsTabShort.length).toBeLessThan(copy.pms.length);
      expect(copy.pmsTabShort.length).toBeLessThanOrEqual(7);
      expect(copy.homeShort.trim()).not.toBe('');
    }
  });

  it('keeps permission-filtered routes and caps bottom tabs at five including More', () => {
    const ws = workspaceForSession('OWNER', ['DASHBOARD', 'PMS', 'WHATSAPP', 'OPS', 'STAFF'], 'LIVE');
    const plan = mobileTabPlan(ws.tabs);
    expect(plan.primary).toEqual(['overview', 'pms', 'inbox', 'admin']);
    expect(plan.overflow).toEqual(['tasks', 'rooms', 'requests', 'profile']);
    expect(plan.showMore).toBe(true);
    expect(plan.primary.length + Number(plan.showMore)).toBeLessThanOrEqual(5);
  });
  it('makes manager staff management accessible only with OPS and STAFF grants', () => {
    const granted = workspaceForSession('MANAGER', ['DASHBOARD', 'PMS', 'WHATSAPP', 'OPS', 'STAFF'], 'LIVE');
    const plan = mobileTabPlan(granted.tabs);
    expect(granted.tabs).toEqual(['overview', 'pms', 'inbox', 'tasks', 'rooms', 'requests', 'admin', 'profile']);
    expect(granted.tabs).toContain('admin');
    expect([...plan.primary, ...plan.overflow]).toContain('admin');
    expect(plan.primary.length + Number(plan.showMore)).toBeLessThanOrEqual(5);

    const noStaff = workspaceForSession('MANAGER', ['DASHBOARD', 'PMS', 'OPS'], 'LIVE');
    expect(noStaff.tabs).not.toContain('admin');
    expect(workspaceForSession('RECEPTION', ['PMS', 'STAFF', 'OPS'], 'LIVE').tabs).not.toContain('admin');
  });
  it('offers owner and manager task, room and repair routes only with OPS permissions', () => {
    for (const role of ['OWNER', 'MANAGER'] as const) {
      const full = workspaceForSession(role, ['DASHBOARD', 'PMS', 'OPS', 'STAFF'], 'LIVE');
      for (const route of ['tasks', 'rooms', 'requests']) expect(full.tabs).toContain(route);
      const restricted = workspaceForSession(role, ['DASHBOARD', 'PMS'], 'LIVE');
      for (const route of ['tasks', 'rooms', 'requests', 'admin']) expect(restricted.tabs).not.toContain(route);
      expect(mobileTabPlan(full.tabs).primary.length).toBeLessThanOrEqual(4);
    }
  });
  it('has no More tab for limited staff and never introduces a forbidden module', () => {
    const ws = workspaceForSession('RECEPTION', ['RESERVATIONS', 'PMS', 'WHATSAPP'], 'LIVE', 'shared_auth_preview');
    const plan = mobileTabPlan(ws.tabs);
    expect(plan.primary).toEqual(['reception', 'pms', 'profile']);
    expect(plan.overflow).toEqual([]);
    expect(plan.showMore).toBe(false);
    expect([...plan.primary, ...plan.overflow]).not.toContain('inbox');
  });
  it('does not duplicate or invent privileges', () => {
    const p = mobileTabPlan(['tasks', 'rooms', 'requests', 'admin', 'profile', 'profile']);
    expect([...p.primary, ...p.overflow]).toEqual(['tasks', 'rooms', 'requests', 'admin', 'profile']);
  });
});

describe('direct Inbox route authorization', () => {
  it('requires WhatsApp/Inbox grant in LIVE and blocks server-disabled shared preview', () => {
    expect(hasTabForSession('MANAGER', ['DASHBOARD'], 'LIVE', 'inbox')).toBe(false);
    expect(hasTabForSession('MAID', ['WHATSAPP'], 'LIVE', 'inbox')).toBe(false);
    expect(hasTabForSession('RECEPTION', ['INBOX'], 'LIVE', 'inbox')).toBe(false);
    expect(hasTabForSession('RECEPTION', ['WHATSAPP'], 'LIVE', 'inbox')).toBe(true);
    expect(hasTabForSession('MANAGER', ['INBOX'], 'LIVE', 'inbox')).toBe(true);
    expect(hasTabForSession('OWNER', ['WHATSAPP'], 'LIVE', 'inbox', 'shared_auth_preview')).toBe(false);
  });
});

describe('direct PMS route authorization', () => {
  it('requires a real PMS grant and a PMS-supported role', () => {
    expect(hasTabForSession('MAID', ['PMS'], 'LIVE', 'pms')).toBe(false);
    expect(hasTabForSession('MANAGER', ['DASHBOARD'], 'LIVE', 'pms')).toBe(false);
    expect(hasTabForSession('RECEPTION', ['PMS'], 'LIVE', 'pms')).toBe(true);
    expect(hasTabForSession('AGENT', ['PMS'], 'LIVE', 'pms')).toBe(true);
  });
});
