import { parseHotelAddress } from './hotels';
import { ApiError } from './types';

export type HttpMethod = 'GET' | 'POST' | 'PATCH' | 'DELETE';
type Transport = typeof fetch;

/**
 * Shared property-scoped transport. Deliberately keeps existing server cookie
 * auth until a revocable device-token API has been reviewed and implemented.
 * This function is a transport primitive; public sign-in is independently gated
 * by a signed-build trust allowlist in hotels.ts + SessionProvider.
 */
export function createHotelHttpClient(baseUrl: string, transport: Transport = fetch) {
  const parsed = parseHotelAddress(baseUrl);
  if (!parsed.ok) throw new Error('Invalid hotel API address');
  const root = parsed.baseUrl;
  async function request<T>(method: HttpMethod, path: string, body?: unknown): Promise<T> {
    const pathname = path.split('?')[0];
    // Reject relative-path tricks before URL normalization. No route may
    // escape the hotel API prefix or smuggle another path via encoded slashes.
    const unsafeSegments = pathname.split('/').some(
      segment => segment === '.' || segment === '..' || /%(?:2f|5c|2e)/i.test(segment),
    );
    if (!path.startsWith('/api/v1/') || path.startsWith('//') ||
        path.includes('://') || /[\\r\\n\\\\]/.test(path) || unsafeSegments) {
      throw new ApiError('BAD_REQUEST', 'Unsupported hotel API path');
    }
    const expectedUrl = root + path;
    const attempts = method === 'GET' ? 2 : 1;
    for (let attempt = 0; attempt < attempts; attempt++) {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), method === 'GET' ? 15000 : 25000);
      let response: Response;
      try {
        response = await transport(expectedUrl, {
          method, credentials: 'include', redirect: 'error', signal: controller.signal,
          headers: { Accept: 'application/json', ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) },
          body: body === undefined ? undefined : JSON.stringify(body),
        });
      } catch {
        // A native redirect refusal and an offline error both fail closed. No
        // automatic retry after an unknown transport failure (lost write ACK).
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
        if (method === 'GET' && attempt + 1 < attempts && [502, 503, 504].includes(response.status)) continue;
        if (response.status === 503) throw new ApiError('UNKNOWN', 'Hotel workspace is unavailable in this environment');
        const code = response.status === 401 ? 'UNAUTHORIZED' : response.status === 403 ? 'FORBIDDEN'
          : response.status === 404 ? 'NOT_FOUND' : response.status === 409 ? 'CONFLICT'
          : response.status === 429 ? 'RATE_LIMIT' : response.status === 400 || response.status === 422 ? 'BAD_REQUEST'
          : 'UNKNOWN';
        const safe = ({
          UNAUTHORIZED: 'Authentication required', FORBIDDEN: 'Access denied',
          NOT_FOUND: 'Record not found', CONFLICT: 'Data was changed; refresh before retrying',
          RATE_LIMIT: 'Too many requests; try again later', BAD_REQUEST: 'Check the entered data',
          UNKNOWN: 'Hotel service is temporarily unavailable',
        } as const)[code];
        throw new ApiError(code, safe);
      }
      if (response.status === 204) return undefined as T;
      try { return await response.json() as T; }
      catch { throw new ApiError('UNKNOWN', 'Invalid hotel API response'); }
    }
    throw new ApiError('UNKNOWN', 'Hotel service unavailable');
  }
  return { request };
}
