import type { GridRoom, GridBlock } from '../api/liveModules';
import { pmsCellState } from './pmsPresentation';

export interface PmsDateSelection { roomId: string; roomCode: string; start: string; end: string }
export function addDays(date: string, count: number): string {
  const parsed = new Date(date + 'T12:00:00');
  if (!Number.isFinite(parsed.getTime())) throw new Error('Invalid PMS date');
  parsed.setDate(parsed.getDate() + count);
  return [parsed.getFullYear(), String(parsed.getMonth()+1).padStart(2,'0'), String(parsed.getDate()).padStart(2,'0')].join('-');
}
export function shortPmsGuestLabel(block: Pick<GridBlock,'guest_name'|'booking_number'>): string {
  const name = (block.guest_name || '').replace(/^ДЕМО\s*[·:-]\s*/i, '').trim();
  return (name || block.booking_number || '●').slice(0, 24);
}
export function isPmsDateFree(room: GridRoom, day: string, today: string): boolean {
  return day >= today && room.operational_state !== 'TECH_BLOCK' &&
    pmsCellState(room.blocks, day) === 'FREE';
}
/** Second tap on another free day extends within one room. Invalid/occupied
 * intervals never become a booking; a fresh tap starts a one-night selection. */
export function extendPmsDateSelection(
  current: PmsDateSelection | null,
  room: GridRoom, day: string, today: string,
): PmsDateSelection | null {
  if (!isPmsDateFree(room, day, today)) return null;
  const single = { roomId: room.id, roomCode: room.code, start: day, end: addDays(day, 1) };
  if (!current || current.roomId !== room.id || day < current.start) return single;
  if (day < current.end) return current;
  const days = Math.round((new Date(day + 'T12:00:00').getTime() - new Date(current.start + 'T12:00:00').getTime()) / 86400000);
  if (days > 59) return single; // Server booking stays are capped at 60 nights.
  for (let i = 0; i <= days; i++) {
    if (!isPmsDateFree(room, addDays(current.start, i), today)) return single;
  }
  return { ...current, end: addDays(day, 1) };
}
