import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';

const mem = new Map<string, string>();
/** Non-secret preferences. No auth credentials are written to web storage. */
function webStorage(): Storage | null {
  if (Platform.OS !== 'web' || typeof globalThis.localStorage === 'undefined') return null;
  try { return globalThis.localStorage; } catch { return null; }
}
export async function getItem(key: string): Promise<string | null> {
  const web = webStorage();
  if (web) { try { return web.getItem(key) ?? mem.get(key) ?? null; } catch { return mem.get(key) ?? null; } }
  try { return (await SecureStore.getItemAsync(key)) ?? mem.get(key) ?? null; }
  catch { return mem.get(key) ?? null; }
}
export async function setItem(key: string, value: string): Promise<void> {
  mem.set(key, value);
  const web = webStorage();
  if (web) { try { web.setItem(key, value); } catch { /* private-mode quota */ } return; }
  try { await SecureStore.setItemAsync(key, value); } catch { /* memory fallback */ }
}
export async function removeItem(key: string): Promise<void> {
  mem.delete(key);
  const web = webStorage();
  if (web) { try { web.removeItem(key); } catch { /* ignore */ } return; }
  try { await SecureStore.deleteItemAsync(key); } catch { /* ignore */ }
}
