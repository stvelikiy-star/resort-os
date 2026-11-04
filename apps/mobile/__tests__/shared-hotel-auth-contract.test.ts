import { createRealApi } from '../src/api/realApi';
import { checkedHotelSelector, matchesSelectedHotel, sameSessionIdentity } from '../src/api/sharedHotelAuth';
import type { AuthUser } from '../src/api/types';

const A = {
  tenant: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  property: '11111111-1111-4111-8111-111111111111',
};
const B = {
  tenant: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
  property: '22222222-2222-4222-8222-222222222222',
};
const user: AuthUser = {
  id: 'employee-1', username: 'manager', display_name: 'Manager', role: 'MANAGER',
  property_code: 'HOTEL_A', property_id: A.property, tenant_id: A.tenant,
  module_permissions: ['PMS', 'OPS'], module_permissions_custom: false,
};
const selector = { tenant_code: 'tenant_a', property_code: 'HOTEL_A' };
const response = (data: unknown) =>
  ({ status: 200, ok: true, redirected: false, json: async () => data } as Response);

describe('marina-shared-auth-v1 mobile transport (isolated mocked HTTP)', () => {
  it('detects the existing server mode without submitting credentials', async () => {
    const transport = jest.fn(async (_url: RequestInfo | URL, _opts?: RequestInit) => response({ mode: 'shared_auth_preview', workspaces_available: false }));
    const api = createRealApi('https://platform.example/core', transport as unknown as typeof fetch);
    expect(await api.authMode!()).toBe('shared_auth_preview');
    expect(transport.mock.calls[0][0]).toBe('https://platform.example/core/api/v1/auth/mode');
    expect(transport.mock.calls[0][1]).toMatchObject({ method: 'GET', credentials: 'include', redirect: 'error' });
    expect(transport.mock.calls[0][1]?.body).toBeUndefined();
  });

  it('sends only issued organization/hotel selectors and credentials to the existing login endpoint', async () => {
    const transport = jest.fn(async (_url: RequestInfo | URL, _opts?: RequestInit) => response(user));
    const api = createRealApi('https://platform.example/core', transport as unknown as typeof fetch);
    expect((await api.login('manager', 'synthetic-password', selector)).id).toBe('employee-1');
    const [url, opts] = transport.mock.calls[0];
    expect(url).toBe('https://platform.example/core/api/v1/auth/login');
    expect(opts).toMatchObject({ method: 'POST', credentials: 'include', redirect: 'error' });
    expect(JSON.parse(String(opts?.body))).toEqual({
      username: 'manager', password: 'synthetic-password',
      tenant_code: 'tenant_a', property_code: 'HOTEL_A',
    });
    expect(JSON.stringify(opts?.headers)).not.toMatch(/x-tenant-id|x-property-id|authorization|bearer/i);
  });

  it('leaves legacy single-property login unchanged without selectors', async () => {
    const transport = jest.fn(async (_url: RequestInfo | URL, _opts?: RequestInit) => response(user));
    await createRealApi('https://platform.example', transport as unknown as typeof fetch)
      .login('manager', 'synthetic-password');
    expect(JSON.parse(transport.mock.calls[0][1].body)).toEqual({
      username: 'manager', password: 'synthetic-password',
    });
  });

  it('rejects forged, missing and URL-like selectors before any network request', async () => {
    const transport = jest.fn(async (_url: RequestInfo | URL, _opts?: RequestInit) => response(user));
    const api = createRealApi('https://platform.example', transport as unknown as typeof fetch);
    for (const wrong of [
      { tenant_code: '', property_code: 'HOTEL_A' },
      { tenant_code: 'tenant_a', property_code: '' },
      { tenant_code: '../other', property_code: 'HOTEL_A' },
      { tenant_code: 'tenant_a', property_code: 'HOTEL_A?other=1' },
      { tenant_code: 'tenant a', property_code: 'HOTEL_A' },
      { tenant_code: 'tenant_a', property_code: 'A'.repeat(81) },
      { tenant_code: 'tenant_a', property_code: ' HOTEL_A' },
    ]) {
      expect(() => checkedHotelSelector(wrong)).toThrow();
      await expect(api.login('manager', 'synthetic-password', wrong)).rejects.toMatchObject({ code: 'BAD_REQUEST' });
    }
    expect(transport).not.toHaveBeenCalled();
  });

  it('does not assume that an unknown /auth/mode response is legacy auth', async () => {
    const transport = jest.fn(async (_url: RequestInfo | URL, _opts?: RequestInit) => response({ mode: 'unexpected' }));
    await expect(createRealApi('https://platform.example', transport as unknown as typeof fetch)
      .authMode()).rejects.toMatchObject({ code: 'UNKNOWN' });
  });
});

describe('server-issued identity for a shared origin', () => {
  it('requires property code plus both authoritative UUIDs on login and /me', () => {
    expect(matchesSelectedHotel(user, user, selector)).toBe(true);
    expect(matchesSelectedHotel(user, { ...user, property_id: B.property }, selector)).toBe(false);
    expect(matchesSelectedHotel(user, { ...user, tenant_id: B.tenant }, selector)).toBe(false);
    expect(matchesSelectedHotel({ ...user, property_code: 'HOTEL_B' }, user, selector)).toBe(false);
    expect(matchesSelectedHotel({ ...user, tenant_id: null }, user, selector)).toBe(false);
    expect(matchesSelectedHotel(user, { ...user, id: 'foreign' }, selector)).toBe(false);
  });

  it('rejects property and tenant changes during foreground session revalidation', () => {
    expect(sameSessionIdentity(user, user)).toBe(true);
    expect(sameSessionIdentity(user, { ...user, property_id: B.property })).toBe(false);
    expect(sameSessionIdentity(user, { ...user, tenant_id: B.tenant })).toBe(false);
    expect(sameSessionIdentity(user, { ...user, property_code: 'HOTEL_B' })).toBe(false);
  });
});
