import type { AuthUser } from './types';

/** UI gate matches the FINANCE section grant; server OWNER/MANAGER and 403 remain final authority. */
export function canReadFinance(user: AuthUser | null | undefined): boolean {
  return !!user && (user.role === 'OWNER' || user.role === 'MANAGER') &&
    Array.isArray(user.module_permissions) && user.module_permissions.includes('FINANCE');
}
