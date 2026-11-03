import { queueCookieLogout, flushPendingCookieLogouts, hasUnrevokedCookieForHost } from '../src/lib/pendingLogout';
import { getItem, removeItem } from '../src/lib/storage';

jest.mock('../src/lib/storage', () => {
  const data = new Map<string, string>();
  return {
    getItem: jest.fn(async (key: string) => data.get(key) ?? null),
    setItem: jest.fn(async (key: string, value: string) => {data.set(key, value);}),
    removeItem: jest.fn(async (key: string) => {data.delete(key);}),
  };
});

const key = 'marina.pending-cookie-logouts.v1';
const original = process.env.EXPO_PUBLIC_MARINA_TRUSTED_API_ORIGINS;
beforeEach(async () => {
  process.env.EXPO_PUBLIC_MARINA_TRUSTED_API_ORIGINS = 'https://hotel.example,https://hotel.example/core,https://other.example';
  await removeItem(key);
});
afterAll(() => {
  if (original === undefined) delete process.env.EXPO_PUBLIC_MARINA_TRUSTED_API_ORIGINS;
  else process.env.EXPO_PUBLIC_MARINA_TRUSTED_API_ORIGINS = original;
});
describe('offline cookie logout compensation', () => {
  it('persists origin without storing session secrets and keeps it on network failure', async () => {
    await queueCookieLogout('https://hotel.example/core');
    expect(await hasUnrevokedCookieForHost('https://hotel.example')).toBe(true);
    expect(await getItem(key)).toBe('["https://hotel.example/core"]');
    const logout = jest.fn(async () => { throw new Error('offline'); });
    await flushPendingCookieLogouts(logout);
    expect(logout).toHaveBeenCalledTimes(1);
    expect(await hasUnrevokedCookieForHost('https://hotel.example/core')).toBe(true);
  });
  it('removes an entry only after successful server logout', async () => {
    await queueCookieLogout('https://hotel.example');
    const logout = jest.fn(async () => {});
    await flushPendingCookieLogouts(logout);
    expect(logout).toHaveBeenCalledWith('https://hotel.example');
    expect(await hasUnrevokedCookieForHost('https://hotel.example/core')).toBe(false);
    expect(await getItem(key)).toBeNull();
  });
  it('does not send an untrusted origin despite older saved logout intent', async () => {
    await queueCookieLogout('https://hotel.example');
    process.env.EXPO_PUBLIC_MARINA_TRUSTED_API_ORIGINS = 'https://other.example';
    const logout = jest.fn(async () => {});
    await flushPendingCookieLogouts(logout);
    expect(logout).not.toHaveBeenCalled();
    expect(await hasUnrevokedCookieForHost('https://hotel.example')).toBe(true);
  });
  it('does not place arbitrary QR domains into the logout queue', async () => {
    await expect(queueCookieLogout('https://evil.example')).rejects.toThrow();
    expect(await getItem(key)).toBeNull();
  });
});
