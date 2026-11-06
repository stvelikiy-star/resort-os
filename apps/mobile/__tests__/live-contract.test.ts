import { createLiveModules } from '../src/api/liveModules';
import { ApiError } from '../src/api/types';

describe('verified mobile live API boundaries', () => {
  const payload = (v: unknown, status = 200) => ({ ok: status < 400, status, json: async () => v }) as Response;
  it('uses the existing /core proxy exactly once with cookie credentials', async () => {
    const transport = jest.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => payload({ items: [] }));
    const api = createLiveModules('https://hotel.example/core', transport as unknown as typeof fetch);
    expect(await api.conversations(true)).toEqual([]);
    expect(transport).toHaveBeenCalledTimes(1);
    expect(transport.mock.calls[0]?.[0]).toBe('https://hotel.example/core/api/v1/admin/inbox/conversations?limit=150&needs_reply=true');
    expect((transport.mock.calls[0]?.[1] as RequestInit).credentials).toBe('include');
  });
  it('exposes only explicit human WhatsApp sending through RC8 server authority', () => {
    const api = createLiveModules('https://hotel.example');
    expect(typeof api.sendWhatsAppText).toBe('function');
    expect(typeof api.outboundCapabilities).toBe('function');
    expect('sendText' in api).toBe(false);
  });
  it('decodes the real reception camelCase list without guessing the values', async () => {
    const original = { local_date: '2026-11-03', items: [{ id: 'r1', bookingNumber: 'M-100', status: 'GUARANTEED', checkIn:'2026-11-03', checkOut:'2026-11-04', remainingKgs: 1200 }] };
    const transport = jest.fn(async () => payload(original));
    const api = createLiveModules('https://hotel.example', transport as unknown as typeof fetch);
    expect((await api.reception()).items[0].remainingKgs).toBe(1200);
  });
  it('fails closed on 403 and never retries a mutation', async () => {
    const transport = jest.fn(async () => payload({}, 403));
    const api = createLiveModules('https://hotel.example', transport as unknown as typeof fetch);
    await expect(api.internalNote('abc', 'internal')).rejects.toMatchObject({ code: 'FORBIDDEN' } as Partial<ApiError>);
    expect(transport).toHaveBeenCalledTimes(1);
  });
  it('provides an actionable error for a preview backend with no workspaces', async () => {
    const transport = jest.fn(async () => payload({}, 503));
    const api = createLiveModules('https://hotel.example', transport as unknown as typeof fetch);
    await expect(api.dashboard()).rejects.toThrow(/workspace is unavailable/);
  });
});
