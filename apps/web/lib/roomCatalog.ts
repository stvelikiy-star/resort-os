export type RoomCategory = {
  index: string;
  slug: string;
  name: string;
  capacity: string;
  area: string;
  summary: string;
  mediaKey?: string;
  rates: {
    early: number;
    peak: number;
    late: number;
  };
};

export const publicRatePeriods = [
  { key: "early" as const, label: "1 июня — 6 июля" },
  { key: "peak" as const, label: "7 июля — 25 августа" },
  { key: "late" as const, label: "26 августа — 15 сентября" },
];

export const roomCategories: RoomCategory[] = [
  {
    index: "01",
    slug: "single-basement",
    name: "Одноместный, цоколь",
    capacity: "1 гость",
    area: "16 м²",
    summary: "Компактная категория для одного гостя на цокольном уровне.",
    rates: { early: 3000, peak: 4000, late: 3000 },
  },
  {
    index: "02",
    slug: "double-standard-basement",
    name: "Двухместный стандарт, цоколь",
    capacity: "2 гостя",
    area: "16–24 м²",
    summary: "Базовая двухместная категория на цокольном уровне. Площадь зависит от конкретного номера.",
    rates: { early: 4500, peak: 6000, late: 4500 },
  },
  {
    index: "03",
    slug: "single-improved",
    name: "Одноместный улучшенный",
    capacity: "1 гость",
    area: "21 м²",
    summary: "Улучшенная одноместная категория с увеличенной площадью.",
    rates: { early: 4800, peak: 6000, late: 4800 },
  },
  {
    index: "04",
    slug: "double-improved",
    name: "Двухместный улучшенный",
    capacity: "2 гостя",
    area: "24–32 м²",
    summary: "Улучшенная двухместная категория. Площадь конкретного номера — от 24 до 32 м².",
    rates: { early: 5500, peak: 7500, late: 5500 },
  },
  {
    index: "05",
    slug: "cottage-double-standard",
    name: "Стандарт в коттеджном доме",
    capacity: "2 гостя",
    area: "27 м²",
    summary: "Двухместная категория в коттеджном доме площадью 27 м².",
    mediaKey: "cottage-double-standard",
    rates: { early: 6000, peak: 8000, late: 6000 },
  },
  {
    index: "06",
    slug: "junior-suite-no-balcony",
    name: "Полулюкс без балкона",
    capacity: "2 гостя",
    area: "26 м²",
    summary: "Двухместный полулюкс без балкона площадью 26 м².",
    rates: { early: 5500, peak: 7500, late: 5500 },
  },
  {
    index: "07",
    slug: "double-suite",
    name: "Люкс двухместный",
    capacity: "2 гостя",
    area: "36 м²",
    summary: "Просторная двухместная категория площадью 36 м².",
    mediaKey: "suite-double-pending-confirmation",
    rates: { early: 7000, peak: 8500, late: 7000 },
  },
  {
    index: "08",
    slug: "triple-suite",
    name: "Люкс трёхместный",
    capacity: "3 гостя",
    area: "36 м²",
    summary: "Просторная трёхместная категория площадью 36 м².",
    mediaKey: "suite-triple-pending-confirmation",
    rates: { early: 9000, peak: 11500, late: 9000 },
  },
  {
    index: "09",
    slug: "two-room-junior-suite",
    name: "Двухкомнатный полулюкс",
    capacity: "до 4 гостей",
    area: "36 м²",
    summary: "Двухкомнатный полулюкс для размещения до четырёх гостей.",
    rates: { early: 11000, peak: 14000, late: 11000 },
  },
  {
    index: "10",
    slug: "two-room-standard",
    name: "Двухкомнатный стандарт",
    capacity: "до 4 гостей",
    area: "30 м²",
    summary: "Двухкомнатный стандарт для размещения до четырёх гостей.",
    mediaKey: "corpus-1-two-room",
    rates: { early: 9500, peak: 12000, late: 9500 },
  },
  {
    index: "11",
    slug: "apartments",
    name: "Апартаменты",
    capacity: "до 4 гостей",
    area: "45–50 м²",
    summary: "Апартаменты увеличенной площади для размещения до четырёх гостей.",
    rates: { early: 12500, peak: 15000, late: 12500 },
  },
  {
    index: "12",
    slug: "apartments-with-kitchen",
    name: "Апартаменты с кухней",
    capacity: "до 4 гостей",
    area: "55–65 м²",
    summary: "Апартаменты с кухней площадью 55–65 м² для размещения до четырёх гостей.",
    mediaKey: "corpus-1-three-room-kitchen",
    rates: { early: 13000, peak: 15500, late: 13000 },
  },
];

export function getRoomCategory(slug: string) {
  return roomCategories.find((room) => room.slug === slug);
}

export function formatKgs(value: number) {
  return new Intl.NumberFormat("ru-RU").format(value);
}
