import { mobileTabPlan } from '../src/roles/navigation';
import { workspaceForSession } from '../src/roles/registry';

describe('role-aware compact bottom navigation', () => {
  it('keeps permission-filtered routes and caps bottom tabs at five including More', () => {
    const ws = workspaceForSession('OWNER', ['DASHBOARD', 'PMS', 'WHATSAPP', 'OPS', 'STAFF'], 'LIVE');
    const plan = mobileTabPlan(ws.tabs);
    expect(plan.primary).toEqual(['overview', 'pms', 'inbox', 'admin']);
    expect(plan.overflow).toEqual(['profile']);
    expect(plan.showMore).toBe(true);
    expect(plan.primary.length + Number(plan.showMore)).toBeLessThanOrEqual(5);
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
