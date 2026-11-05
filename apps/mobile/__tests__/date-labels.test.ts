import { formatChatTimestamp } from '../src/i18n/dateLabels';

describe('honest local timestamps for hotel communications', () => {
  it('does not render missing or invalid timestamps as fake dates', () => {
    expect(formatChatTimestamp(null, 'ru')).toBeNull();
    expect(formatChatTimestamp('', 'en')).toBeNull();
    expect(formatChatTimestamp('not-an-iso-date', 'kg')).toBeNull();
  });
  it.each(['ru', 'kg', 'en', 'kz'] as const)('formats a verified timestamp with %s locale', locale => {
    const label = formatChatTimestamp('2026-11-04T12:05:00Z', locale);
    expect(typeof label).toBe('string');
    expect(label).not.toContain('Invalid');
    expect(label!.length).toBeGreaterThan(5);
  });
});
