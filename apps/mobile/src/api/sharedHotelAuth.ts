import { ApiError } from './types';
import type { AuthUser } from './types';

/** Issued hotel selectors are public routing hints, NEVER authorization grants. */
export interface SharedHotelSelector {
  tenant_code: string;
  property_code: string;
}
const CODE = /^[A-Za-z0-9][A-Za-z0-9_-]{2,79}$/;
const UUID = /^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/i;

/** Do not accept URLs, UUID-based impersonation, whitespace or forged headers. */
export function checkedHotelSelector(value: SharedHotelSelector): SharedHotelSelector {
  if (!value || typeof value.tenant_code !== 'string' || typeof value.property_code !== 'string' ||
      !CODE.test(value.tenant_code) || !CODE.test(value.property_code)) {
    throw new ApiError('BAD_REQUEST', 'Enter the issued organization and hotel codes');
  }
  return { tenant_code: value.tenant_code, property_code: value.property_code };
}

/** A shared session is valid only when both login and /me identify the selected hotel. */
export function matchesSelectedHotel(
  login: AuthUser, verified: AuthUser, selector: SharedHotelSelector,
): boolean {
  const chosen = checkedHotelSelector(selector);
  return login.property_code === chosen.property_code &&
    verified.property_code === chosen.property_code &&
    !!login.property_id && UUID.test(login.property_id) &&
    !!login.tenant_id && UUID.test(login.tenant_id) &&
    login.property_id === verified.property_id &&
    login.tenant_id === verified.tenant_id &&
    login.id === verified.id && login.role === verified.role;
}

/** Reject a changed property or tenant even when user ID and hotel code match. */
export function sameSessionIdentity(expected: AuthUser, verified: AuthUser): boolean {
  return !!expected.id && expected.id === verified.id &&
    expected.property_code === verified.property_code &&
    (expected.property_id ?? null) === (verified.property_id ?? null) &&
    (expected.tenant_id ?? null) === (verified.tenant_id ?? null);
}
