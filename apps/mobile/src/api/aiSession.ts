import type { AuthUser } from './types';

/** React remount boundary: never preserve an assistant transcript across
 * hotel, property, tenant, role or verified staff identity changes.
 * Do not put credentials, cookies or guest records into the key.
 */
export function assistantSessionKey(hotelId: string, user: AuthUser, mode: 'LIVE' | 'DEMO'): string {
  return JSON.stringify([
    mode, hotelId, user.tenant_id ?? null, user.property_id ?? null,
    user.property_code, user.id, user.role,
  ]);
}
