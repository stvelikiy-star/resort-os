import { queueCookieLogout, flushPendingCookieLogouts, hasUnrevokedCookieForHost } from '../src/lib/pendingLogout';
import { getDurableItem, setDurableItem, removeDurableItem } from '../src/lib/storage';

jest.mock('../src/lib/storage', () => {
  const data = new Map<string, string>();
  return {
    getDurableItem: jest.fn(async (key: string) => data.get(key) ?? null),
    setDurableItem: jest.fn(async (key: string, value: string) => {data.set(key, value);}),
    removeDurableItem: jest.fn(async (key: string) => {data.delete(key);}),
  };
});

const key = 'marina.pending-cookie-logouts.v1';
const original = process.env.EXPO_PUBLIC_MARINA_TRUSTED_API_ORIGINS;
beforeEach(async () => {
  process.env.EXPO_PUBLIC_MARINA_TRUSTED_API_ORIGINS = 'https://hotel.example,https://hotel.example/core,https://other.example';
  await removeDurableItem(key);
});
afterAll(() => {
  if (original === undefined) delete process.env.EXPO_PUBLIC_MARINA_TRUSTED_API_ORIGINS;
  else process.env.EXPO_PUBLIC_MARINA_TRUSTED_API_ORIGINS = original;
});
describe('offline cookie logout compensation', () => {
  it('persists origin without storing session secrets and keeps it on network failure', async () => {
    await queueCookieLogout('https://hotel.example/core');
    expect(await hasUnrevokedCookieForHost('https://hotel.example')).toBe(true);
    expect(await getDurableItem(key)).toBe('["https://hotel.example/core"]');
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
    expect(await getDurableItem(key)).toBeNull();
  });
  it('does not send an untrusted origin despite older saved logout intent', async () => {
    await queueCookieLogout('https://hotel.example');
    process.env.EXPO_PUBLIC_MARINA_TRUSTED_API_ORIGINS = 'https://other.example';
    const logout = jest.fn(async () => {});
    await flushPendingCookieLogouts(logout);
    expect(logout).not.toHaveBeenCalled();
    expect(await hasUnrevokedCookieForHost('https://hotel.example')).toBe(true);
  });
  it('refuses to treat failed durable storage reads as revoked credentials', async () => {
    jest.mocked(getDurableItem).mockRejectedValueOnce(new Error('secure storage unreadable'));
    expect(await hasUnrevokedCookieForHost('https://hotel.example/core')).toBe(true);
  });
  it('reports a failed logout journal write instead of claiming durable persistence', async () => {
    jest.mocked(setDurableItem).mockRejectedValueOnce(new Error('secure storage write refused'));
    await expect(queueCookieLogout('https://hotel.example/core')).rejects.toThrow('secure storage write refused');
    expect(await getDurableItem(key)).toBeNull();
  });
  it('treats a corrupt journal as unresolved instead of silently forgetting a possible cookie', async () => {
    await setDurableItem(key, '{not valid json');
    expect(await hasUnrevokedCookieForHost('https://hotel.example')).toBe(true);
  });
  it('does not place arbitrary QR domains into the logout queue', async () => {
    await expect(queueCookieLogout('https://evil.example')).rejects.toThrow();
    expect(await getDurableItem(key)).toBeNull();
  });
});
