import { parseHotelAddress } from './hotels';
import { ApiError } from './types';
import { captureVerifiedHost, rejectVerifiedHost } from './unauthorizedSession';

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
type Transport = typeof fetch;

/**
 * Shared property-scoped transport. Deliberately keeps existing server cookie
 * auth until a revocable device-token API has been reviewed and implemented.
 * This function is a transport primitive; public sign-in is independently gated
 * by a signed-build trust allowlist in hotels.ts + SessionProvider.
 */
type ErrorCode = ApiError['code'];
const STATUS_CODE: Record<number, ErrorCode> = { 400: 'BAD_REQUEST', 401: 'UNAUTHORIZED', 403: 'FORBIDDEN', 404: 'NOT_FOUND', 409: 'CONFLICT', 422: 'BAD_REQUEST', 429: 'RATE_LIMIT' };
const SAFE_MESSAGE: Partial<Record<ErrorCode, string>> = {
  UNAUTHORIZED: 'Authentication required', FORBIDDEN: 'Access denied',
  NOT_FOUND: 'Record not found', CONFLICT: 'Data was changed; refresh before retrying',
  RATE_LIMIT: 'Too many requests; try again later', BAD_REQUEST: 'Check the entered data',
  UNKNOWN: 'Hotel service is temporarily unavailable',
};
/** Single HTTP-status -> ApiError mapping; messages are fixed strings, never server text. */
export function errorForStatus(status: number): { code: ErrorCode; message: string } {
  const code = STATUS_CODE[status] ?? 'UNKNOWN';
  return { code, message: SAFE_MESSAGE[code] ?? SAFE_MESSAGE.UNKNOWN! };
}

export function createHotelHttpClient(baseUrl: string, transport: Transport = fetch, sessionIsActive?: () => boolean) {
  const parsed = parseHotelAddress(baseUrl);
  if (!parsed.ok) throw new Error('Invalid hotel API address');
  const root = parsed.baseUrl;
  async function request<T>(method: HttpMethod, path: string, body?: unknown, idempotencyKey?: string): Promise<T> {
    if (idempotencyKey !== undefined && (method !== 'POST' || !/^[A-Za-z0-9._:-]{8,160}$/.test(idempotencyKey))) {
      throw new ApiError('BAD_REQUEST', 'Invalid mutation idempotency key');
    }
    const pathname = path.split('?')[0];
    // Reject relative-path tricks before URL normalization. No route may
    // escape the hotel API prefix or smuggle another path via encoded slashes.
    const unsafeSegments = pathname.split('/').some(
      segment => segment === '.' || segment === '..' || /%(?:2f|5c|2e)/i.test(segment),
    );
    if (!path.startsWith('/api/v1/') || path.startsWith('//') ||
        path.includes('://') || path.includes('#') || /[\r\n\\]/.test(path) || unsafeSegments) {
      throw new ApiError('BAD_REQUEST', 'Unsupported hotel API path');
    }
    const expectedUrl = root + path;
    // Capture the verified session at request START. Old hotel's delayed 401
    // must not clear a newer employee session on the same HTTPS hostname.
    // Auth endpoints are not protected-data requests: a wrong password must
    // never act as a global log-out event.
    const protectedRequest = !pathname.startsWith('/api/v1/auth/');
    const verifiedAtStart = protectedRequest ? captureVerifiedHost(root) : null;
    const requireSameSession = () => {
      if ((protectedRequest && sessionIsActive && !sessionIsActive()) ||
          (verifiedAtStart && captureVerifiedHost(root) !== verifiedAtStart)) {
        throw new ApiError('STALE_SESSION', 'The active hotel session changed');
      }
    };
    const attempts = method === 'GET' ? 2 : 1;
    for (let attempt = 0; attempt < attempts; attempt++) {
      requireSameSession();
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), method === 'GET' ? 15000 : 25000);
      let response: Response;
      try {
        response = await transport(expectedUrl, {
          method, credentials: 'include', redirect: 'error', signal: controller.signal,
          headers: { Accept: 'application/json', ...(body === undefined ? {} : { 'Content-Type': 'application/json' }), ...(idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {}) },
          body: body === undefined ? undefined : JSON.stringify(body),
        });
      } catch {
        // A native redirect refusal and an offline error both fail closed. No
        // automatic retry after an unknown transport failure (lost write ACK).
        requireSameSession();
        throw new ApiError('OFFLINE', 'Hotel connection unavailable; check connection before retrying');
      } finally {
        clearTimeout(timeout);
      }
      // Native networking adapters may not consistently set redirected.
      // A differing final response URL is also a cross-origin/path redirect.
      // This is defense-in-depth, not proof that the native adapter refused
      // an initial unsafe redirect before it sent a sensitive request.
      if (response.redirected === true || (typeof response.url === 'string' && response.url.length > 0 &&
          response.url !== expectedUrl)) {
        throw new ApiError('FORBIDDEN', 'Unexpected hotel API redirect');
      }
      if (!response.ok) {
        if (response.status === 401) {
          if (!sessionIsActive || sessionIsActive()) rejectVerifiedHost(root, verifiedAtStart);
          const { code, message } = errorForStatus(401);
          throw new ApiError(code, message);
        }
        requireSameSession();
        if (method === 'GET' && attempt + 1 < attempts && [502, 503, 504].includes(response.status)) continue;
        if (response.status === 503) throw new ApiError('UNKNOWN', 'Hotel workspace is unavailable in this environment');
        const { code, message } = errorForStatus(response.status);
        throw new ApiError(code, message);
      }
      requireSameSession();
      if (response.status === 204) return undefined as T;
      let value: T;
      try { value = await response.json() as T; }
      catch { throw new ApiError('UNKNOWN', 'Invalid hotel API response'); }
      requireSameSession();
      return value;
    }
    throw new ApiError('UNKNOWN', 'Hotel service unavailable');
  }
  return { request };
}
