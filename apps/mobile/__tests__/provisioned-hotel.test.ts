import { provisionedHotelConnection } from '../src/api/hotels';

describe('one pinned hotel in customer mobile build', () => {
  const aska = 'https://leeds-biology-charming-employ.trycloudflare.com/core';
  it('automatically identifies a single trusted hotel without creating a second property', () => {
    const chosen = provisionedHotelConnection(aska);
    expect(chosen?.baseUrl).toBe(aska);
    expect(chosen?.demo).toBe(false);
    expect(chosen?.id).toBe('live-leeds-biology-charming-employ.trycloudflare.com-core');
  });
  it('fails closed for missing, multiple, or invalid trusted origins', () => {
    expect(provisionedHotelConnection('')).toBeNull();
    expect(provisionedHotelConnection(aska+',https://hotel2.example/core')).toBeNull();
    expect(provisionedHotelConnection('http://untrusted.example')).toBeNull();
  });
});
