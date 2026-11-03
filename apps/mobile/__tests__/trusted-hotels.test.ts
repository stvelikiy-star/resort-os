import { approvedHotelOrigins, isTrustedHotelOrigin, parseHotelAddress } from '../src/api/hotels';

describe('P0 pinned hotel API origin', () => {
  const config = 'https://hotel.example/core,https://resort.example,https://hotel.example/core,https://*.evil.example, http://bad.example,https://hotel.example:9443';
  it('only exact canonical HTTPS hosts and API prefixes are approved', () => {
    expect(approvedHotelOrigins(config)).toEqual(['https://hotel.example/core','https://resort.example']);
    expect(isTrustedHotelOrigin('https://hotel.example/core',config)).toBe(true);
    expect(isTrustedHotelOrigin('https://resort.example',config)).toBe(true);
    for (const value of ['https://hotel.example','https://hotel.example.evil.com/core','https://evil.example','http://hotel.example/core','https://hotel.example:9443/core','https://resort.example/core','https://hotel.example/core/../malicious']) {
      expect(isTrustedHotelOrigin(value,config)).toBe(false);
    }
  });
  it('rejects all live origins when the trusted registry is empty', () => {
    expect(approvedHotelOrigins('')).toEqual([]);
    expect(isTrustedHotelOrigin('https://hotel.example','')).toBe(false);
  });
  it('syntax is not proof of trust', () => {
    expect(parseHotelAddress('https://untrusted.example').ok).toBe(true);
    expect(isTrustedHotelOrigin('https://untrusted.example',config)).toBe(false);
  });
});
