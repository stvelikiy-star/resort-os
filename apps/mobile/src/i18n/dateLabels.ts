/** Display-only formatting in the user's device timezone. Never changes server timestamps. */
export type UiLocale = 'ru' | 'kg' | 'en' | 'kz';
const LANGUAGE_TAG: Record<UiLocale, string> = {
  ru: 'ru-RU', kg: 'ky-KG', en: 'en-US', kz: 'kk-KZ',
};
export function formatChatTimestamp(timestamp: string | null | undefined, locale: UiLocale): string | null {
  if (!timestamp) return null;
  const date = new Date(timestamp);
  if (!Number.isFinite(date.getTime())) return null;
  return date.toLocaleString(LANGUAGE_TAG[locale], {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
  });
}
