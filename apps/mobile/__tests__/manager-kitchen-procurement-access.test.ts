import {hasTabForSession,workspaceForSession} from '../src/roles/registry';

test('MANAGER with the Dining grant can reach kitchen procurement approval',()=>{
 const tabs=workspaceForSession('MANAGER',['DASHBOARD','DINING','PMS','OPS','STAFF'],'LIVE');
 expect(tabs.tabs).toContain('kitchen');
 expect(hasTabForSession('MANAGER',['DINING'],'LIVE','kitchen')).toBe(true);
});

test('MANAGER without Dining grant cannot reach kitchen; grants do not change roles',()=>{
 expect(hasTabForSession('MANAGER',['OPS','STAFF'],'LIVE','kitchen')).toBe(false);
 expect(hasTabForSession('RECEPTION',['DINING'],'LIVE','kitchen')).toBe(false);
 expect(hasTabForSession('WAITER',['DINING'],'LIVE','kitchen')).toBe(false);
});

test('shared PMS preview keeps all Dining API routes disabled for MANAGER',()=>{
 expect(hasTabForSession('MANAGER',['DINING'],'LIVE','kitchen','shared_auth_preview')).toBe(false);
});

test('OWNER already has authorized read-only kitchen access',()=>{
 expect(hasTabForSession('OWNER',['DINING'],'LIVE','kitchen')).toBe(true);
});
