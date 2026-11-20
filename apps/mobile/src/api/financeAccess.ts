import type { AuthUser } from './types';

/** UI gate matches the FINANCE section grant; server OWNER/MANAGER and 403 remain final authority. */
export function canReadFinance(user: AuthUser | null | undefined): boolean {
  return !!user && (user.role === 'OWNER' || user.role === 'MANAGER') &&
    Array.isArray(user.module_permissions) && user.module_permissions.includes('FINANCE');
}

/** Never expose dashboard payment amounts on a general DASHBOARD-only grant.
 * Dashboard read access and FINANCE read access are different permissions.
 * This is UI minimization; server authorization remains authoritative.
 */
export function dashboardFinanceForUser(
  user: AuthUser | null | undefined,
  finance: { confirmed_payments_today_kgs: number; active_reservations_remaining_kgs: number },
): typeof finance | null {
  return canReadFinance(user) ? finance : null;
}
