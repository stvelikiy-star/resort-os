import { createDemoApi } from './demoApi';
import { createRealApi } from './realApi';
import type { HotelConnection } from './hotels';
import type { StaffApi } from './types';

const cache = new Map<string, StaffApi>();
/** API instances are keyed per connection. Native cookies are managed by the OS per host, not per instance; the PMS must enforce tenant isolation. */
export function apiFor(h: HotelConnection): StaffApi {
  let a = cache.get(h.id);
  if (!a) { a = h.demo ? createDemoApi(h.id) : createRealApi(h.baseUrl); cache.set(h.id, a); }
  return a;
}
export function dropApi(hotelId: string) { cache.delete(hotelId); }
