import { createDemoApi } from './demoApi';
import { createRealApi } from './realApi';
import type { HotelConnection } from './hotels';
import type { StaffApi } from './types';

const cache = new Map<string, StaffApi>();
/** One api instance per hotel connection: state/cookies never cross hotels. */
export function apiFor(h: HotelConnection): StaffApi {
  let a = cache.get(h.id);
  if (!a) { a = h.demo ? createDemoApi(h.id) : createRealApi(h.baseUrl); cache.set(h.id, a); }
  return a;
}
export function dropApi(hotelId: string) { cache.delete(hotelId); }
