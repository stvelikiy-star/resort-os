import { assistantSessionKey } from '../src/api/aiSession';
import type { AuthUser } from '../src/api/types';

const staff = (property: string, id='staff-1'): AuthUser => ({
  id, username: 'owner', display_name: 'Owner', role: 'OWNER',
  property_code: property, module_permissions: ['DASHBOARD'],
});

describe('MARINA AI transcript identity boundary', () => {
  it('remounts the conversation when switching hotels, including same-host tenants', () => {
    const a = staff('HOTEL_A');
    const b = staff('HOTEL_B');
    expect(assistantSessionKey('hotel-a', a, 'LIVE')).not.toBe(assistantSessionKey('hotel-b', b, 'LIVE'));
    expect(assistantSessionKey('same-host', a, 'LIVE')).not.toBe(assistantSessionKey('same-host', b, 'LIVE'));
    expect(assistantSessionKey('hotel-a', a, 'LIVE')).toBe(assistantSessionKey('hotel-a', a, 'LIVE'));
  });

  it('does not reuse an AI transcript for another staff identity, role or DEMO mode', () => {
    const a = staff('HOTEL_A');
    expect(assistantSessionKey('hotel-a', a, 'LIVE')).not.toBe(assistantSessionKey('hotel-a', staff('HOTEL_A', 'staff-2'), 'LIVE'));
    expect(assistantSessionKey('hotel-a', a, 'LIVE')).not.toBe(assistantSessionKey('hotel-a', { ...a, role: 'MANAGER' }, 'LIVE'));
    expect(assistantSessionKey('hotel-a', a, 'LIVE')).not.toBe(assistantSessionKey('hotel-a', a, 'DEMO'));
    expect(assistantSessionKey('hotel-a', a, 'LIVE')).not.toContain('password');
  });
});
