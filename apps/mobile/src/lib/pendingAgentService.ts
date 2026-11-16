import * as SecureStore from 'expo-secure-store';
import { agentServiceDraft, AgentServiceDraft, validServiceDate } from '../api/agentServices';

export type PendingAgentService = { reservationId: string; serviceCode: string; startedAt: string; serviceDate?: string; serviceTime?: string };

function key(hotelId: string, userId: string): string {
  if (![hotelId, userId].every(value => /^[A-Za-z0-9_-]{1,100}$/.test(value))) {
    throw new Error('Unverified agent service identity');
  }
  return 'marina.agent-service.pending.' + hotelId + '.' + userId;
}

export async function readPendingAgentService(hotelId: string, userId: string): Promise<PendingAgentService | null> {
  const raw = await SecureStore.getItemAsync(key(hotelId, userId));
  if (raw === null) return null;
  const parsed: unknown = JSON.parse(raw);
  if (!parsed || typeof parsed !== 'object') throw new Error('Invalid agent service journal');
  const record = parsed as Record<string, unknown>;
  if (typeof record.reservationId !== 'string' || !/^[0-9a-f-]{36}$/i.test(record.reservationId) ||
      typeof record.serviceCode !== 'string' || !/^[A-Z_]{2,40}$/.test(record.serviceCode) ||
      typeof record.startedAt !== 'string' || !Number.isFinite(Date.parse(record.startedAt)) ||
      (record.serviceDate !== undefined && (typeof record.serviceDate !== 'string' || !validServiceDate(record.serviceDate))) ||
      (record.serviceTime !== undefined && (typeof record.serviceTime !== 'string' || !record.serviceDate || !/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(record.serviceTime)))) {
    throw new Error('Invalid agent service journal');
  }
  return record as PendingAgentService;
}

/** Commit journal before network I/O. Unknown outcomes stay locked across restarts. */
export async function beginPendingAgentService(
  hotelId: string, userId: string, reservationId: string, serviceCode: string,
  schedule: AgentServiceDraft = {},
): Promise<void> {
  if (await readPendingAgentService(hotelId, userId)) {
    throw new Error('Pending agent service requires manual reconciliation');
  }
  if (!/^[0-9a-f-]{36}$/i.test(reservationId) || !/^[A-Z_]{2,40}$/.test(serviceCode)) {
    throw new Error('Invalid agent service operation');
  }
  const normalized = agentServiceDraft(schedule);
  await SecureStore.setItemAsync(key(hotelId, userId), JSON.stringify({
    reservationId, serviceCode, startedAt: new Date().toISOString(),
    ...(normalized.service_date ? { serviceDate: normalized.service_date } : {}),
    ...(normalized.service_time ? { serviceTime: normalized.service_time } : {}),
  } satisfies PendingAgentService));
}

export async function clearPendingAgentService(hotelId: string, userId: string): Promise<void> {
  await SecureStore.deleteItemAsync(key(hotelId, userId));
}

/** Clear only the exact journal the operator has reviewed in the platform.
 * This is a manual acknowledgement, NOT server proof of request delivery.
 */
export async function acknowledgePendingAgentService(
  hotelId: string, userId: string, inspected: PendingAgentService,
): Promise<boolean> {
  const current = await readPendingAgentService(hotelId, userId);
  if (!current || current.reservationId !== inspected.reservationId ||
      current.serviceCode !== inspected.serviceCode ||
      current.startedAt !== inspected.startedAt || current.serviceDate !== inspected.serviceDate ||
      current.serviceTime !== inspected.serviceTime) return false;
  await clearPendingAgentService(hotelId, userId);
  return true;
}
