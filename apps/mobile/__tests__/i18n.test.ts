import { dictionaries, LOCALES, localeFromDevice } from '../src/i18n';
import { mobileCopyStrings, aiMobileCopy, pmsWeekdayLabels } from '../src/i18n/mobileCopy';

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
  it('STORE_STAFF absence of server operations is explained in every locale', () => {
    for (const locale of LOCALES) {
      const notice = dictionaries[locale].profile.storeUnavailable;
      expect(notice.trim().length).toBeGreaterThan(60);
      expect(notice).toMatch(/API/);
      expect(notice).not.toMatch(/coming soon|скоро/i);
    }
  });
  it('LIVE mobile copy has equal keys and non-empty values in RU/KG/EN/KZ', () => {
    const baseline = Object.keys(mobileCopyStrings.ru).sort();
    for (const locale of LOCALES) {
      expect(Object.keys(mobileCopyStrings[locale]).sort()).toEqual(baseline);
      for (const value of Object.values(mobileCopyStrings[locale])) expect(value.trim()).not.toBe('');
    }
  });
  it('keeps the moved AI copy and 7 PMS weekday names complete in every locale', () => {
    const aiKeys = Object.keys(aiMobileCopy.ru).sort();
    for (const locale of LOCALES) {
      expect(Object.keys(aiMobileCopy[locale]).sort()).toEqual(aiKeys);
      expect(Object.values(aiMobileCopy[locale]).every(v => !!v.trim())).toBe(true);
      expect(pmsWeekdayLabels[locale]).toHaveLength(7);
      expect(pmsWeekdayLabels[locale].every(v => !!v.trim())).toBe(true);
      expect(mobileCopyStrings[locale].livePmsLabel).toBe('LIVE PMS');
    }
  });
  it('maps device language codes', () => {
    expect(localeFromDevice('ky')).toBe('kg');
    expect(localeFromDevice('kk-KZ')).toBe('kz');
    expect(localeFromDevice('en-US')).toBe('en');
    expect(localeFromDevice('de')).toBe('ru');
    expect(localeFromDevice(null)).toBe('ru');
  });
});
