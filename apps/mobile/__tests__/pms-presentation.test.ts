import { canOpenPmsReservation, pmsCellState } from '../src/roles/pmsPresentation';
import type { GridBlock } from '../src/api/liveModules';
const example = (type: string, id: string | null = null): GridBlock =>
  ({ id: 'b', type, start: '2026-11-01', end: '2026-11-05', reservation_id: id, booking_number: null, guest_name: null });
describe('PMS grid truthful read-only display', () => {
  it('renders calendar boundaries and all verified types correctly', () => {
    expect(pmsCellState([example('RESERVATION', 'r1')], '2026-11-05')).toBe('FREE');
    expect(pmsCellState([example('RESERVATION', 'r1')], '2026-11-04')).toBe('RESERVATION');
    expect(pmsCellState([example('HOLD')], '2026-11-02')).toBe('HOLD');
    expect(pmsCellState([example('TECH_BLOCK')], '2026-11-02')).toBe('BLOCKED');
    expect(pmsCellState([example('MAINTENANCE')], '2026-11-02')).toBe('BLOCKED');
    expect(pmsCellState([example('RESERVATION'), example('HOLD')], '2026-11-02')).toBe('CONFLICT');
  });
  it('does not pretend that agent/hold/repair/conflicts can open a reservation', () => {
    expect(canOpenPmsReservation([example('RESERVATION', 'r1')], '2026-11-02', 'MANAGER')).toBe(true);
    expect(canOpenPmsReservation([example('RESERVATION', 'r1')], '2026-11-02', 'AGENT')).toBe(false);
    expect(canOpenPmsReservation([example('RESERVATION')], '2026-11-02', 'OWNER')).toBe(false);
    expect(canOpenPmsReservation([example('HOLD')], '2026-11-02', 'OWNER')).toBe(false);
    expect(canOpenPmsReservation([example('RESERVATION', 'r1'), example('HOLD')], '2026-11-02', 'MANAGER')).toBe(false);
  });
});
