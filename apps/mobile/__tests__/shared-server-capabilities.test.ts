import { createLiveModules } from '../src/api/liveModules';
import { createRealApi } from '../src/api/realApi';
import { workspaceForSession, homeForSession } from '../src/roles/registry';

const ok = (data: unknown) => ({
  ok: true, status: 200, redirected: false, json: async () => data,
}) as Response;

describe('canonical shared-auth staging server 503 admission contract', () => {
  it('hides inbox/dining tabs even if the server granted WHATSAPP, INBOX or DINING', () => {
    const grants = ['DASHBOARD','PMS','RESERVATIONS','WHATSAPP','INBOX','OPS','STAFF','DINING'];
    const owner = workspaceForSession('OWNER', grants, 'LIVE', 'shared_auth_preview');
    const manager = workspaceForSession('MANAGER', grants, 'LIVE', 'shared_auth_preview');
    const reception = workspaceForSession('RECEPTION', grants, 'LIVE', 'shared_auth_preview');
    const cook = workspaceForSession('COOK', grants, 'LIVE', 'shared_auth_preview');
    for (const w of [owner, manager, reception, cook]) {
      expect(w.tabs).not.toContain('inbox');
      expect(w.tabs).not.toContain('dining');
    }
    expect(owner.tabs).toContain('pms');
    expect(owner.canSetRoomState).toBe(false);
    expect(homeForSession('COOK', grants, 'LIVE', 'shared_auth_preview')).toBe('/profile');
    expect(reception.tabs).toEqual(['reception', 'pms', 'profile']);
    // Legacy single-property retains its existing workspace until the
    // server explicitly reports shared mode. Do not disable working modules.
    expect(workspaceForSession('COOK', grants, 'LIVE','single_property').tabs).toContain('dining');
    expect(workspaceForSession('MANAGER', grants, 'LIVE','single_property').tabs).toContain('inbox');
  });

  it('refuses all blocked shared workspaces BEFORE network, without simulating a 200', async () => {
    const transport = jest.fn(async (_url: RequestInfo | URL, _init?: RequestInit) => ok({items: []}));
    const api = createLiveModules('https://platform.example/core',transport as unknown as typeof fetch,'shared_auth_preview');
    const attempts = [
      () => api.conversations(),
      () => api.conversation('abc'),
      () => api.claimConversation('abc'),
      () => api.conversationStatus('abc','OPEN'),
      () => api.internalNote('abc','internal'),
      () => api.kitchenOrders(),
      () => api.kitchenStatus('abc','READY'),
      () => api.diningFloor(),
      () => api.claimWaiterOrder('abc','waiter'),
      () => api.assistantCapabilities(),
      () => api.assistantChat([{role:'user',content:'status'}],'ru','/overview'),
    ];
    for (const attempt of attempts) {
      await expect(attempt()).rejects.toMatchObject({code:'UNKNOWN'});
    }
    expect(transport).not.toHaveBeenCalled();
  });

  it('still allows reviewed shared PMS GET without extending server permissions', async () => {
    const transport=jest.fn(async (_url: RequestInfo | URL, _init?: RequestInit) => ok({property:'HOTEL_A',rooms:[]}));
    const api=createLiveModules('https://platform.example/core',transport as unknown as typeof fetch,'shared_auth_preview');
    expect((await api.pmsGrid('2026-11-04','2026-11-11')).rooms).toEqual([]);
    expect(transport).toHaveBeenCalledTimes(1);
    expect(transport.mock.calls[0][0]).toContain('/core/api/v1/pms/grid?start=');
  });

  it('does not PATCH room state in shared preview; single-property contract remains separate', async () => {
    const transport=jest.fn(async (_url: RequestInfo | URL, _init?: RequestInit) => ok({mode:'shared_auth_preview'}));
    const api=createRealApi('https://platform.example',transport as unknown as typeof fetch);
    expect(await api.authMode!()).toBe('shared_auth_preview');
    await expect(api.setRoomState('r1','CLEAN')).rejects.toMatchObject({code:'UNKNOWN'});
    expect(transport).toHaveBeenCalledTimes(1);
  });

  it('does not disable legacy Inbox by guessing the hostname', async () => {
    const transport=jest.fn(async (_url: RequestInfo | URL, _init?: RequestInit) => ok({items:[]}));
    const api=createLiveModules('https://platform.example',transport as unknown as typeof fetch,'single_property');
    expect(await api.conversations()).toEqual([]);
    expect(transport).toHaveBeenCalledTimes(1);
  });
});
