import { getDurableItem, removeDurableItem, setDurableItem } from './storage';

/** One unresolved dispatch per authenticated staff member and conversation.
 * A lost HTTP acknowledgement is never permission to send again automatically.
 */
export interface PendingOutbound { key: string; recorded_at: number; text: string }
const claiming = new Set<string>();
export function outboundJournalKey(property: string, user: string, conversation: string): string {
  return 'pending-outbound:' + encodeURIComponent(property) + ':' + encodeURIComponent(user) + ':' + encodeURIComponent(conversation);
}
export function newOutboundKey(): string {
  // This key is an idempotency identifier, not an authentication secret.
  return 'mobile-' + Date.now().toString(36) + '-' +
    Math.random().toString(36).slice(2) + Math.random().toString(36).slice(2);
}
export async function readPendingOutbound(key: string): Promise<PendingOutbound | null> {
  const value = await getDurableItem(key);
  if (value === null) return null;
  const record: unknown = JSON.parse(value);
  if (!record || typeof record !== 'object') throw new Error('Invalid pending outbound record');
  const item = record as Record<string, unknown>;
  if (typeof item.key !== 'string' || !/^[A-Za-z0-9._:-]{8,160}$/.test(item.key) ||
      typeof item.text !== 'string' || !item.text || item.text.length > 4096 ||
      typeof item.recorded_at !== 'number' || !Number.isSafeInteger(item.recorded_at))
    throw new Error('Invalid pending outbound record');
  return item as unknown as PendingOutbound;
}
export async function recordPendingOutbound(journal: string, text: string, key: string): Promise<boolean> {
  if (claiming.has(journal)) return false;
  claiming.add(journal);
  let recorded = false;
  try {
    if (await readPendingOutbound(journal)) return false;
    await setDurableItem(journal, JSON.stringify({ text, key, recorded_at: Date.now() }));
    recorded = true;
    return true;
  } finally {
    if (!recorded) claiming.delete(journal);
  }
}
export async function clearPendingOutbound(journal: string): Promise<void> {
  await removeDurableItem(journal);
}
export function finishPendingOutbound(journal: string): void { claiming.delete(journal); }
export async function acknowledgePendingOutbound(journal: string, existing: PendingOutbound): Promise<boolean> {
  if (claiming.has(journal)) return false;
  claiming.add(journal);
  try {
    if (JSON.stringify(await readPendingOutbound(journal)) !== JSON.stringify(existing)) return false;
    await clearPendingOutbound(journal);
    return true;
  } finally { claiming.delete(journal); }
}
