import { reservationAmount, reservationGuestName, reservationStatusLabel, reservationTelephone } from '../src/roles/reservationPresentation';

const copy = {
  awaitingArrival: 'Ожидает заезда', checkedIn: 'Заселён', checkedOut: 'Выселен',
  cancelled: 'Отменён', pendingConfirmation: 'Ждёт подтверждения',
};
describe('live reservation card presentation is truthful and role-independent', () => {
  it('does not invent a guest name or show dash dash for absent fields', () => {
    expect(reservationGuestName(null, undefined, 'Гость')).toBe('Гость');
    expect(reservationGuestName('  Иван ', ' Иванов ', 'Гость')).toBe('Иван Иванов');
    expect(reservationGuestName(13, null, 'Гость')).toBe('Гость');
  });
  it('displays localized statuses without mutating server status codes', () => {
    expect(reservationStatusLabel('GUARANTEED', copy)).toBe('Ожидает заезда');
    expect(reservationStatusLabel('CHECKED_IN', copy)).toBe('Заселён');
    expect(reservationStatusLabel('REQUESTED', copy)).toBe('Ждёт подтверждения');
    expect(reservationStatusLabel('UNRECOGNIZED', copy)).toBe('UNRECOGNIZED');
  });
  it('exposes only a valid guest phone from verified reservation details', () => {
    expect(reservationTelephone('+996 555 123 456')).toBe('tel:+996555123456');
    expect(reservationTelephone('bad:+996555123')).toBeNull();
    expect(reservationTelephone(null)).toBeNull();
    expect(reservationTelephone('123')).toBeNull();
  });
  it('never displays nonexistent or corrupt financial amounts as zero', () => {
    expect(reservationAmount(undefined)).toBeNull();
    expect(reservationAmount('0')).toBeNull();
    expect(reservationAmount(-3)).toBeNull();
    expect(reservationAmount(Number.NaN)).toBeNull();
    expect(reservationAmount(0)).toContain('0');
    expect(reservationAmount(5200)).toContain('KGS');
  });
});
