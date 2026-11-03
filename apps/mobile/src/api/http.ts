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
    if (!path.startsWith('/api/v1/') || path.includes('://') || /[\r\n]/.test(path)) {
      throw new ApiError('BAD_REQUEST', 'Unsupported hotel API path');
    }
    const attempts = method === 'GET' ? 2 : 1;
    for (let attempt = 0; attempt < attempts; attempt++) {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), method === 'GET' ? 15000 : 25000);
      let response: Response;
      try {
        response = await transport(root + path, {
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
      if (response.redirected === true) throw new ApiError('FORBIDDEN', 'Unexpected hotel API redirect');
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
