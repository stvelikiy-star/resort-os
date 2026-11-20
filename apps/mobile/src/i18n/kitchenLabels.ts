import type { KitchenOrder } from '../api/liveModules';
export type KitchenLocale = 'ru' | 'kg' | 'en' | 'kz';
export type KitchenItem = KitchenOrder['items'][number];

/** The live Kitchen API sends name_ru/name_kg/name_en/name_kz, NOT name.
 * Synthetic DEMO fixtures may still use name. No made-up translation. */
export function kitchenItemName(item: KitchenItem, locale: KitchenLocale): string {
  const localized: Record<KitchenLocale, string | null | undefined> = {
    ru: item.name_ru, kg: item.name_kg, en: item.name_en, kz: item.name_kz,
  };
  const choices = [localized[locale], item.name_ru, item.name_kg, item.name_en, item.name_kz, item.name];
  return choices.find(n => typeof n === 'string' && n.trim().length > 0)?.trim() ?? '';
}
