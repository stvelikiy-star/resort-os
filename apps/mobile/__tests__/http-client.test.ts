import { createHotelHttpClient } from '../src/api/http';

const response = (status: number, data: unknown) => ({
  status, ok: status >= 200 && status < 300, redirected: false, json: async () => data,
} as Response);
describe('one safe HTTP client for realApi and LIVE modules', () => {
  it('uses cookie auth, exact prefixed endpoint, redirect refusal and abort signal', async () => {
    const f = jest.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => response(200, { ok: true }));
    const api = createHotelHttpClient('https://hotel.example/core', f as unknown as typeof fetch);
    await api.request('GET', '/api/v1/auth/me');
    expect(f).toHaveBeenCalledTimes(1);
    expect(f.mock.calls[0][0]).toBe('https://hotel.example/core/api/v1/auth/me');
    expect(f.mock.calls[0][1]).toMatchObject({ credentials:'include', redirect:'error' });
    expect(f.mock.calls[0]?.[1]?.signal).toBeTruthy();
  });
  it('never retries a mutation, even on 503 or lost response', async () => {
    const f = jest.fn(async () => response(503, {}));
    const api = createHotelHttpClient('https://hotel.example',f as unknown as typeof fetch);
    await expect(api.request('POST','/api/v1/admin/pms/reservations/new/commit',{})).rejects.toMatchObject({code:'UNKNOWN'});
    expect(f).toHaveBeenCalledTimes(1);
  });
  it('retries only a safe GET on gateway failures', async () => {
    const f = jest.fn().mockResolvedValueOnce(response(503, {})).mockResolvedValueOnce(response(200, { rooms: [] }));
    const api = createHotelHttpClient('https://hotel.example',f as typeof fetch);
    expect(await api.request('GET','/api/v1/pms/grid?start=2026-11-03')).toEqual({rooms:[]});
    expect(f).toHaveBeenCalledTimes(2);
  });
  it('does not retry a mutation on network loss', async () => {
    const f = jest.fn(async () => { throw new Error('network disconnected'); });
    const api = createHotelHttpClient('https://hotel.example',f as unknown as typeof fetch);
    await expect(api.request('DELETE','/api/v1/admin/pms/holds/id')).rejects.toMatchObject({code:'OFFLINE'});
    expect(f).toHaveBeenCalledTimes(1);
  });
  it('refuses path traversal and encoded slash tricks before issuing any request', async () => {
    const transport = jest.fn(async () => response(200, {}));
    const api = createHotelHttpClient('https://hotel.example/core', transport as unknown as typeof fetch);
    for (const path of [
      '/api/v1/../auth/me', '/api/v1/%2e%2e/auth/me',
      '/api/v1/ops/tasks/a%2Fb', '/api/v1/ops/tasks/a%5Cb',
      '/api/v1/ops\\\\evil', '//evil.example/api/v1/auth/me',
    ]) {
      await expect(api.request('GET', path)).rejects.toMatchObject({code:'BAD_REQUEST'});
    }
    expect(transport).not.toHaveBeenCalled();
  });
  it('refuses a final response URL different from the requested hotel endpoint', async () => {
    const url='https://evil.example/core/api/v1/auth/me';
    const transport=jest.fn(async () => ({...response(200,{id:'u1'}), url} as Response));
    const api=createHotelHttpClient('https://hotel.example/core', transport as unknown as typeof fetch);
    await expect(api.request('GET','/api/v1/auth/me')).rejects.toMatchObject({code:'FORBIDDEN'});
    expect(transport).toHaveBeenCalledTimes(1);
  });

  it('hides untrusted server errors and declines off-prefix paths', async () => {
    const f = jest.fn(async () => response(409, { detail: 'PRIVATE GUEST DATA' }));
    const api = createHotelHttpClient('https://hotel.example',f as unknown as typeof fetch);
    await expect(api.request('POST','/api/v1/ops/tasks/id/status',{status:'DONE'})).rejects.not.toThrow(/PRIVATE GUEST DATA/);
    await expect(api.request('GET','https://evil.example/api/v1/auth/me')).rejects.toMatchObject({code:'BAD_REQUEST'});
    await expect(api.request('GET','/redirect')).rejects.toMatchObject({code:'BAD_REQUEST'});
    expect(f).toHaveBeenCalledTimes(1);
  });
});
