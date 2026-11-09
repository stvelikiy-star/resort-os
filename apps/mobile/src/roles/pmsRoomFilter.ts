import type { GridRoom } from '../api/liveModules';
import { pmsCellState } from './pmsPresentation';
import { isPmsDateFree } from './pmsSelection';

export type PmsRoomFilter = 'all' | 'attention' | 'free' | 'reserved';

/** Display-only filters against the authenticated PMS grid; no inferred inventory. */
export function filterPmsRooms(
  rooms: readonly GridRoom[], search: string, filter: PmsRoomFilter, selectedDate: string, today: string,
): GridRoom[] {
  const query = search.trim().toLocaleLowerCase();
  return rooms.filter(room => {
    const searchable = [room.code, room.name, room.room_type_name].filter(Boolean)
      .join(' ').toLocaleLowerCase();
    if (query && !searchable.includes(query)) return false;
    if (filter === 'attention') return ['DIRTY', 'IN_INSPECTION', 'TECH_BLOCK'].includes(room.operational_state);
    if (filter === 'free') return isPmsDateFree(room, selectedDate, today);
    if (filter === 'reserved') return pmsCellState(room.blocks, selectedDate) === 'RESERVATION';
    return true;
  });
}
