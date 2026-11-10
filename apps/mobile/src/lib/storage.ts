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

/** Security decisions must never rely on memory-only fallback.
 * These methods report real persistence/read failures to callers.
 * The pending logout journal contains ONLY public host origins, never tokens.
 */
export async function getDurableItem(key: string): Promise<string | null> {
  if (Platform.OS === 'web') {
    const web = webStorage();
    if (!web) throw new Error('Durable browser storage unavailable');
    return web.getItem(key);
  }
  return SecureStore.getItemAsync(key);
}
export async function setDurableItem(key: string, value: string): Promise<void> {
  if (Platform.OS === 'web') {
    const web = webStorage();
    if (!web) throw new Error('Durable browser storage unavailable');
    web.setItem(key, value);
    return;
  }
  await SecureStore.setItemAsync(key, value);
}
export async function removeDurableItem(key: string): Promise<void> {
  if (Platform.OS === 'web') {
    const web = webStorage();
    if (!web) throw new Error('Durable browser storage unavailable');
    web.removeItem(key);
    return;
  }
  await SecureStore.deleteItemAsync(key);
}
