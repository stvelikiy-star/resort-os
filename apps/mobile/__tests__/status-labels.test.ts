import { chatStatusLabel, contactInitials, deliveryStatusLabel, messageDirectionLabel, orderStatusLabel } from '../src/i18n/statusLabels';
import { mobileCopyStrings } from '../src/i18n/mobileCopy';

describe('server status presentation is localized and does not change semantics', () => {
  for (const locale of ['ru', 'kg', 'en', 'kz'] as const) {
    const c = mobileCopyStrings[locale];
    it('translates known statuses for ' + locale, () => {
      expect(chatStatusLabel('WAITING_STAFF', c)).toBe(c.chatWaitingStaff);
      expect(messageDirectionLabel('INBOUND', c)).toBe(c.messageIncoming);
      expect(deliveryStatusLabel('DELIVERED', c)).toBe(c.messageDelivered);
      expect(orderStatusLabel('COOKING', c)).toBe(c.orderCooking);
      expect(chatStatusLabel('FUTURE_STATE', c)).toBe('FUTURE_STATE');
    });
  }
  it('renders compact avatar initials only for an actual contact name', () => {
    expect(contactInitials('Ирина Петрова')).toBe('ИП');
    expect(contactInitials('Marina')).toBe('MA');
    expect(contactInitials('')).toBeNull();
    expect(contactInitials(null)).toBeNull();
  });
});
