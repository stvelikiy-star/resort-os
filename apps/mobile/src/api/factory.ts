import { createDemoApi } from './demoApi';
import { createRealApi } from './realApi';
import { registerClientSession } from './unauthorizedSession';
import type { HotelConnection } from './hotels';
import type { StaffApi } from './types';

const cache = new Map<string, { api: StaffApi; revoke: () => void }>();

export function apiFor(h: HotelConnection): StaffApi {
  const existing = cache.get(h.id);
  if (existing) return existing.api;
  const session = { active: false, revoked: false };
  const api = h.demo ? createDemoApi(h.id) : createRealApi(h.baseUrl, fetch, () => session.active && !session.revoked);
  if (!h.demo) registerClientSession(api, session);
  cache.set(h.id, { api, revoke: () => { session.revoked = true; } });
  return api;
}

export function dropApi(hotelId: string): void {
  cache.get(hotelId)?.revoke();
  cache.delete(hotelId);
}
