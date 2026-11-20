import { demoConversations, demoConversationDetail, demoDiningFloor, demoKitchenOrders, demoDashboard, demoGrid, demoReception } from '../src/api/demoPresentation';
import { demoTaskTitle } from '../src/i18n/demoLabels';
import { demoShowcaseWorkspace, workspaceForSession } from '../src/roles/registry';
import { DEMO_USERS } from '../src/api/demoApi';
import type { Locale } from '../src/i18n';
import type { Room, Task } from '../src/api/types';

const ROOMS: Room[] = [
  { id:'r1',code:'DEMO-101',floor:1,state:'CLEAN' },
  { id:'r2',code:'DEMO-102',floor:1,state:'DIRTY' },
  { id:'r3',code:'DEMO-103',floor:1,state:'TECH_BLOCK' },
];
const TASKS: Task[] = [{ id:'t1',type:'HOUSEKEEPING',status:'OPEN',priority:'URGENT',title:'Уборка после выезда',room_id:'r2',room_code:'DEMO-102',assigned_to_id:'u-maid' }];

describe('showroom stays isolated from server RBAC', () => {
  it('offers synthetic owner/reception/chef views without enabling LIVE tabs', () => {
    expect(DEMO_USERS.owner.user.role).toBe('OWNER');
    expect(DEMO_USERS.cook.user.role).toBe('COOK');
    expect(demoShowcaseWorkspace('OWNER').tabs).toContain('overview');
    expect(workspaceForSession('RECEPTION',[], 'DEMO').tabs).toContain('reception');
    expect(workspaceForSession('COOK',[], 'DEMO').tabs).toContain('dining');
    expect(workspaceForSession('COOK',[], 'LIVE').tabs).toEqual(['profile']);
    expect(workspaceForSession('RECEPTION',[], 'LIVE').tabs).toEqual(['profile']);
    expect(workspaceForSession('OWNER',['PMS'], 'LIVE').tabs).not.toContain('inbox');
  });
  it('keeps unsupported roles fail-closed even for demo', () => {
    expect(workspaceForSession('STORE_STAFF',[], 'DEMO').tabs).toEqual(['profile']);
  });
});
describe.each(['ru','kg','en','kz'] as Locale[])('synthetic presentation is translated %s', locale => {
  it('shows role-specific sample cards without personal information', () => {
    const reception=demoReception(locale, ROOMS);
    expect(reception.items.length).toBeGreaterThan(3);
    expect(reception.items.every(x => x.phone === null)).toBe(true);
    expect(reception.items.every(x => x.bookingNumber.startsWith('DEMO-'))).toBe(true);
    expect(demoDashboard('DEMO', ROOMS,TASKS,locale).rooms.total).toBe(3);
    expect(demoGrid(locale,ROOMS,'DEMO').rooms).toHaveLength(3);
  });
  it('shows local task copy and real-looking but synthetic message/order examples', () => {
    expect(demoTaskTitle('t1',locale,'fallback')).not.toBe('fallback');
    expect(demoTaskTitle('unrecognized',locale,'fallback')).toBe('fallback');
    const chats=demoConversations(locale);
    expect(chats).toHaveLength(2);
    expect(chats[0].contact_phone).toBeNull();
    expect(demoConversationDetail(chats[0].id,locale)?.messages.length).toBeGreaterThan(1);
    expect(demoDiningFloor(locale).tables).toHaveLength(3);
    expect(demoKitchenOrders(locale).every(x=>x.order_number.startsWith('DEMO-'))).toBe(true);
  });
});
