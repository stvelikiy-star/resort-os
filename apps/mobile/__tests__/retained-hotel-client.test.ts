import { apiFor, dropApi } from '../src/api/factory';
import { createLiveModules } from '../src/api/liveModules';
import { activateClientSession, bindVerifiedHost, clientSessionGuard } from '../src/api/unauthorizedSession';

it('rejects retained A clients before fetch even after B verifies on the same origin', async () => {
  const hotel = { id: 'live-test', baseUrl: 'https://platform.example/core', demo: false, name: 'Fixture', city: '', accent: '' };
  const fetchMock = jest.spyOn(globalThis, 'fetch').mockResolvedValue({
    ok: true, status: 200, json: async () => ({ items: [] }),
  } as Response);
  const a = apiFor(hotel);
  const clearA = bindVerifiedHost(hotel.baseUrl, jest.fn());
  activateClientSession(a);
  const modulesA = createLiveModules(hotel.baseUrl, globalThis.fetch, 'shared_auth_preview', clientSessionGuard(a));
  dropApi(hotel.id);
  clearA();
  const b = apiFor(hotel);
  const clearB = bindVerifiedHost(hotel.baseUrl, jest.fn());
  try {
    await expect(b.listTasks()).rejects.toMatchObject({ code: 'STALE_SESSION' });
    activateClientSession(b);
    await expect(a.listTasks()).rejects.toMatchObject({ code: 'STALE_SESSION' });
    await expect(modulesA.pmsGrid('2026-11-04', '2026-11-05')).rejects.toMatchObject({ code: 'STALE_SESSION' });
    expect(fetchMock).not.toHaveBeenCalled();
    await expect(b.listTasks()).resolves.toEqual([]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  } finally {
    clearB();
    dropApi(hotel.id);
    fetchMock.mockRestore();
  }
});
