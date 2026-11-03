import { dictionaries, LOCALES, localeFromDevice } from '../src/i18n';

const flat = (o: any, p = ''): Record<string, string> =>
  Object.entries(o).reduce((a, [k, v]) => (typeof v === 'object' ? { ...a, ...flat(v, `${p}${k}.`) } : { ...a, [`${p}${k}`]: String(v) }), {});
const ph = (s: string) => (s.match(/\{\{\w+\}\}/g) ?? []).sort().join(',');

describe('localization RU/KG/EN/KZ', () => {
  const base = flat(dictionaries.ru);
  it('has four locales', () => expect([...LOCALES].sort()).toEqual(['en', 'kg', 'kz', 'ru']));
  for (const l of LOCALES) {
    it(`${l}: same keys as ru, none empty, same placeholders`, () => {
      const d = flat(dictionaries[l]);
      expect(Object.keys(d).sort()).toEqual(Object.keys(base).sort());
      for (const k of Object.keys(base)) { expect(d[k].trim()).not.toBe(''); expect(ph(d[k])).toBe(ph(base[k])); }
    });
  }
  it('maps device language codes', () => {
    expect(localeFromDevice('ky')).toBe('kg');
    expect(localeFromDevice('kk-KZ')).toBe('kz');
    expect(localeFromDevice('en-US')).toBe('en');
    expect(localeFromDevice('de')).toBe('ru');
    expect(localeFromDevice(null)).toBe('ru');
  });
});
