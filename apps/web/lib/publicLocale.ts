export type PublicLocale = "ru" | "kg" | "en";

export const localeIntl: Record<PublicLocale, string> = {
  ru: "ru-RU",
  kg: "ky-KG",
  en: "en-US",
};

export function normalizePublicLocale(value: string | null | undefined): PublicLocale {
  return value === "kg" || value === "en" || value === "ru" ? value : "ru";
}

export function resolveClientLocale(): PublicLocale {
  if (typeof window === "undefined") return "ru";
  const query = new URLSearchParams(window.location.search).get("lang");
  if (query === "kg" || query === "en" || query === "ru") return query;
  const stored = window.localStorage.getItem("three-crowns-site-language");
  return normalizePublicLocale(stored);
}

export function withPublicLocale(href: string, locale: PublicLocale): string {
  if (locale === "ru") return href;
  if (/^(https?:|mailto:|tel:|#)/.test(href)) return href;
  const hashIndex = href.indexOf("#");
  const base = hashIndex >= 0 ? href.slice(0, hashIndex) : href;
  const hash = hashIndex >= 0 ? href.slice(hashIndex) : "";
  const separator = base.includes("?") ? "&" : "?";
  return `${base}${separator}lang=${locale}${hash}`;
}

export function formatPublicNumber(value: number, locale: PublicLocale): string {
  return new Intl.NumberFormat(localeIntl[locale]).format(value);
}

export function formatPublicDate(iso: string, locale: PublicLocale): string {
  const [year, month, day] = iso.split("-").map(Number);
  return new Intl.DateTimeFormat(localeIntl[locale], { day: "numeric", month: "short" }).format(new Date(year, month - 1, day));
}

type LocalRoomCopy = { name: string; capacity: string; summary: string };

type RoomLocaleEntry = {
  ru: LocalRoomCopy;
  kg: LocalRoomCopy;
  en: LocalRoomCopy;
};

export const roomLocaleBySlug: Record<string, RoomLocaleEntry> = {
  "single-basement": {
    ru: { name: "Одноместный, цоколь", capacity: "1 гость", summary: "Компактная категория для одного гостя на цокольном уровне." },
    kg: { name: "Бир кишилик номер, цоколь", capacity: "1 конок", summary: "Цоколь кабатындагы бир конок үчүн компакттуу категория." },
    en: { name: "Single Room, Basement Level", capacity: "1 guest", summary: "A compact basement-level category for one guest." },
  },
  "double-standard-basement": {
    ru: { name: "Двухместный стандарт, цоколь", capacity: "2 гостя", summary: "Базовая двухместная категория на цокольном уровне. Площадь зависит от конкретного номера." },
    kg: { name: "Эки кишилик стандарт, цоколь", capacity: "2 конок", summary: "Цоколь кабатындагы базалык эки кишилик категория. Аянты конкреттүү номерге жараша өзгөрөт." },
    en: { name: "Double Standard, Basement Level", capacity: "2 guests", summary: "A standard double category on the basement level. Area varies by room." },
  },
  "single-improved": {
    ru: { name: "Одноместный улучшенный", capacity: "1 гость", summary: "Улучшенная одноместная категория с увеличенной площадью." },
    kg: { name: "Жакшыртылган бир кишилик номер", capacity: "1 конок", summary: "Аянты чоңойтулган жакшыртылган бир кишилик категория." },
    en: { name: "Superior Single", capacity: "1 guest", summary: "An upgraded single category with additional space." },
  },
  "double-improved": {
    ru: { name: "Двухместный улучшенный", capacity: "2 гостя", summary: "Улучшенная двухместная категория. Площадь конкретного номера — от 24 до 32 м²." },
    kg: { name: "Жакшыртылган эки кишилик номер", capacity: "2 конок", summary: "Жакшыртылган эки кишилик категория. Конкреттүү номердин аянты 24–32 м²." },
    en: { name: "Superior Double", capacity: "2 guests", summary: "An upgraded double category. Individual room area ranges from 24 to 32 m²." },
  },
  "cottage-double-standard": {
    ru: { name: "Стандарт в коттеджном доме", capacity: "2 гостя", summary: "Двухместная категория в коттеджном доме площадью 27 м²." },
    kg: { name: "Коттедждеги стандарт", capacity: "2 конок", summary: "Коттедж үйүндөгү 27 м² эки кишилик категория." },
    en: { name: "Cottage Double Standard", capacity: "2 guests", summary: "A 27 m² double category in the cottage building." },
  },
  "junior-suite-no-balcony": {
    ru: { name: "Полулюкс без балкона", capacity: "2 гостя", summary: "Двухместный полулюкс без балкона площадью 26 м²." },
    kg: { name: "Балкону жок жарым люкс", capacity: "2 конок", summary: "Балкону жок, 26 м² эки кишилик жарым люкс." },
    en: { name: "Junior Suite, No Balcony", capacity: "2 guests", summary: "A 26 m² double junior suite without a balcony." },
  },
  "double-suite": {
    ru: { name: "Люкс двухместный", capacity: "2 гостя", summary: "Просторная двухместная категория площадью 36 м²." },
    kg: { name: "Эки кишилик люкс", capacity: "2 конок", summary: "36 м² кең эки кишилик категория." },
    en: { name: "Double Suite", capacity: "2 guests", summary: "A spacious 36 m² double category." },
  },
  "triple-suite": {
    ru: { name: "Люкс трёхместный", capacity: "3 гостя", summary: "Просторная трёхместная категория площадью 36 м²." },
    kg: { name: "Үч кишилик люкс", capacity: "3 конок", summary: "36 м² кең үч кишилик категория." },
    en: { name: "Triple Suite", capacity: "3 guests", summary: "A spacious 36 m² triple category." },
  },
  "two-room-junior-suite": {
    ru: { name: "Двухкомнатный полулюкс", capacity: "до 4 гостей", summary: "Двухкомнатный полулюкс для размещения до четырёх гостей." },
    kg: { name: "Эки бөлмөлүү жарым люкс", capacity: "4 конокко чейин", summary: "Төрт конокко чейин жайгашууга ылайыктуу эки бөлмөлүү жарым люкс." },
    en: { name: "Two-Room Junior Suite", capacity: "up to 4 guests", summary: "A two-room junior suite for up to four guests." },
  },
  "two-room-standard": {
    ru: { name: "Двухкомнатный стандарт", capacity: "до 4 гостей", summary: "Двухкомнатный стандарт для размещения до четырёх гостей." },
    kg: { name: "Эки бөлмөлүү стандарт", capacity: "4 конокко чейин", summary: "Төрт конокко чейин жайгашууга ылайыктуу эки бөлмөлүү стандарт." },
    en: { name: "Two-Room Standard", capacity: "up to 4 guests", summary: "A two-room standard category for up to four guests." },
  },
  apartments: {
    ru: { name: "Апартаменты", capacity: "до 4 гостей", summary: "Апартаменты увеличенной площади для размещения до четырёх гостей." },
    kg: { name: "Апартаменттер", capacity: "4 конокко чейин", summary: "Төрт конокко чейин жайгашууга ылайыктуу чоң аянттагы апартаменттер." },
    en: { name: "Apartments", capacity: "up to 4 guests", summary: "Spacious apartments for up to four guests." },
  },
  "apartments-with-kitchen": {
    ru: { name: "Апартаменты с кухней", capacity: "до 4 гостей", summary: "Апартаменты с кухней площадью 55–65 м² для размещения до четырёх гостей." },
    kg: { name: "Ашканасы бар апартаменттер", capacity: "4 конокко чейин", summary: "Төрт конокко чейин жайгашууга ылайыктуу 55–65 м² ашканасы бар апартаменттер." },
    en: { name: "Apartments with Kitchen", capacity: "up to 4 guests", summary: "55–65 m² apartments with a kitchen for up to four guests." },
  },
};

const roomSlugByRussianName = Object.fromEntries(
  Object.entries(roomLocaleBySlug).map(([slug, entry]) => [entry.ru.name, slug]),
);

export function getLocalizedRoomCopy(slug: string, locale: PublicLocale): LocalRoomCopy | null {
  return roomLocaleBySlug[slug]?.[locale] ?? null;
}

export function localizeRoomTypeName(name: string, locale: PublicLocale): string {
  const slug = roomSlugByRussianName[name];
  return slug ? roomLocaleBySlug[slug]?.[locale]?.name ?? name : name;
}
