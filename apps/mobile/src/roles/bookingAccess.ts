import type { AuthUser, Role } from '../api/types';

/** Roles the server admits to POST /admin/pms/reservations/new/{preview,commit}
 * (pms_reservation_create.py manager_access). Cancellation and date changes are
 * deliberately NOT derived from this list: they stay OWNER/MANAGER only.
 * The server still enforces role, property, module grant and, for RECEPTION,
 * published core-rate only (403 RECEPTION_* codes). UI is a convenience. */
export const BOOKING_CREATE_ROLES: readonly Role[] = ['OWNER', 'MANAGER', 'AGENT', 'RECEPTION'];

export function canCreateBooking(user: Pick<AuthUser, 'role' | 'module_permissions'> | null | undefined): boolean {
  return !!user && BOOKING_CREATE_ROLES.includes(user.role) && !!user.module_permissions?.includes('PMS');
}
export function canStartBookingFromPms(role: Role | undefined | null): boolean {
  return !!role && BOOKING_CREATE_ROLES.includes(role);
}
