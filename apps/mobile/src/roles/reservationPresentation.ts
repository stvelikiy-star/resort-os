import type { MobileCopy } from '../i18n/mobileCopy';

type Labels = Pick<MobileCopy,
  'awaitingArrival' | 'checkedIn' | 'checkedOut' | 'cancelled' | 'pendingConfirmation'>;

/** Presentation only. Never equate a missing guest with literal "— —". */
export function reservationGuestName(first: unknown, last: unknown, fallback: string): string {
  const name = [first, last].filter((value): value is string =>
    typeof value === 'string' && value.trim().length > 0).map(x => x.trim()).join(' ');
  return name || fallback;
}

/** Unknown statuses remain explicit; the UI does not grant actions from display labels. */
export function reservationStatusLabel(code: string, copy: Labels): string {
  switch (code) {
    case 'GUARANTEED': return copy.awaitingArrival;
    case 'CHECKED_IN': return copy.checkedIn;
    case 'CHECKED_OUT': return copy.checkedOut;
    case 'CANCELLED': return copy.cancelled;
    case 'REQUESTED':
    case 'PENDING': return copy.pendingConfirmation;
    default: return code;
  }
}

/** The phone is sourced only from the authenticated reservation detail response. */
export function reservationTelephone(value: unknown): string | null {
  if (typeof value !== 'string') return null;
  const clean = value.trim();
  if (!/^\+?[\d() .-]{5,25}$/.test(clean)) return null;
  const dial = clean.replace(/[^\d+]/g, '');
  if (dial.replace(/\D/g, '').length < 5) return null;
  return 'tel:' + dial;
}

/** Missing or invalid financial data is unknown, never a fabricated zero. */
export function reservationAmount(value: unknown): string | null {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0) return null;
  return Math.round(value).toLocaleString('ru-RU') + ' KGS';
}
