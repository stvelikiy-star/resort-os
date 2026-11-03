import { ApiError } from '../api/types';

/**
 * Only a definitive server rejection permits submitting the same operation again.
 * A transport failure, 5xx response, malformed success response or failed readback
 * can mean the mutation was already committed. Fail closed until read-only
 * reconciliation or server idempotency is available.
 */
const REJECTED = new Set<ApiError['code']>([
  'BAD_REQUEST', 'CONFLICT', 'FORBIDDEN', 'UNAUTHORIZED', 'RATE_LIMIT', 'NOT_FOUND',
]);
export function wasWriteRejected(error: unknown): boolean {
  return error instanceof ApiError && REJECTED.has(error.code);
}
