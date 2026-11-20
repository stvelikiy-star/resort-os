import type { GridBlock } from '../api/liveModules';

/** Read-only interpretation of the PMS blocks returned by the selected hotel. */
export type GridCellState = 'FREE' | 'RESERVATION' | 'HOLD' | 'BLOCKED' | 'CONFLICT';
export function pmsCellState(blocks: readonly GridBlock[], day: string): GridCellState {
  const active = blocks.filter(b => b.start <= day && day < b.end);
  if (active.length > 1) return 'CONFLICT';
  if (!active.length) return 'FREE';
  const type = active[0].type.toUpperCase();
  if (type === 'RESERVATION') return 'RESERVATION';
  if (type === 'HOLD') return 'HOLD';
  // Repair/maintenance/unknown block types must never be presented as a hold.
  return 'BLOCKED';
}
export function canOpenPmsReservation(blocks: readonly GridBlock[], day: string, role?: string | null): boolean {
  const active = blocks.filter(b => b.start <= day && day < b.end);
  return active.length === 1 && active[0].type === 'RESERVATION' && !!active[0].reservation_id && role !== 'AGENT';
}
