import { ApiError } from './types';

/**
 * PMS identifiers are opaque server references, never user-provided URL syntax.
 * Single guard shared by every authenticated route builder (realApi + liveModules).
 * The backend uses UUID/CUID-style IDs; a malformed ID is rejected, never normalized.
 */
export function safeRouteId(value: string): string {
  if (typeof value !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$/.test(value)) {
    throw new ApiError('BAD_REQUEST', 'Invalid hotel record reference');
  }
  return value;
}

/** Calendar date (YYYY-MM-DD) used in query strings; anything else is rejected before the network. */
export function safeIsoDate(value: string): string {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    throw new ApiError('BAD_REQUEST', 'Invalid date');
  }
  return value;
}
