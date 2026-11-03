import i18n, { changeLanguage, use as i18nUse } from 'i18next';
import { initReactI18next } from 'react-i18next';
import { ru } from './ru';
import { en } from './en';
import { kg } from './kg';
import { kz } from './kz';

export const LOCALES = ['ru', 'kg', 'en', 'kz'] as const;
export type Locale = (typeof LOCALES)[number];
export const LOCALE_LABEL: Record<Locale, string> = { ru: 'Русский', kg: 'Кыргызча', en: 'English', kz: 'Қазақша' };
export const dictionaries = { ru, kg, en, kz };

/** Map device language codes (ISO 639-1) to app locale keys. Kyrgyz = "ky", Kazakh = "kk". */
export function localeFromDevice(code?: string | null): Locale {
  const c = (code ?? '').toLowerCase().slice(0, 2);
  if (c === 'ky') return 'kg';
  if (c === 'kk') return 'kz';
  if (c === 'en') return 'en';
  return 'ru';
}

let ready = false;
export function initI18n(lng: Locale = 'ru') {
  if (!ready) {
    void i18nUse(initReactI18next).init({
      resources: Object.fromEntries(LOCALES.map((l) => [l, { translation: dictionaries[l] }])),
      lng, fallbackLng: 'ru', interpolation: { escapeValue: false }, compatibilityJSON: 'v4', returnNull: false,
    });
    ready = true;
  } else if (i18n.language !== lng) {
    void changeLanguage(lng);
  }
  return i18n;
}
export default i18n;
