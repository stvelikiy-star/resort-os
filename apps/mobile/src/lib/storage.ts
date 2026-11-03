import * as SecureStore from 'expo-secure-store';

const mem = new Map<string, string>();
/** Non-secret app preferences/connection list. Tokens (when backend B1 lands) must use SecureStore only. */
export async function getItem(key: string): Promise<string | null> {
  try { return (await SecureStore.getItemAsync(key)) ?? mem.get(key) ?? null; } catch { return mem.get(key) ?? null; }
}
export async function setItem(key: string, value: string): Promise<void> {
  mem.set(key, value);
  try { await SecureStore.setItemAsync(key, value); } catch { /* web/preview: memory only */ }
}
export async function removeItem(key: string): Promise<void> {
  mem.delete(key);
  try { await SecureStore.deleteItemAsync(key); } catch { /* ignore */ }
}
