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

/**
 * WhatsApp RC8 has a special HTTP 409: OUTBOX_RECONCILIATION_REQUIRED.
 * The provider may already have accepted the message. A generic 409 is
 * therefore NOT proof of rejection for send-text. Keep the durable outbound
 * journal and require human reconciliation. Never use wasWriteRejected()
 * to decide whether a WhatsApp message can be submitted again.
 *
 * RBAC/auth/validation errors, unlike 409 and network failures, are
 * definitive rejections before reaching the message provider.
 */
export function wasWhatsAppSendRejected(error: unknown): boolean {
  return error instanceof ApiError && (
    error.code === 'BAD_REQUEST' ||
    error.code === 'UNAUTHORIZED' ||
    error.code === 'NOT_FOUND'
  );
}
