export const HOTEL_TIME_ZONE = "Asia/Bishkek";

const HOTEL_DATE_FORMATTER = new Intl.DateTimeFormat("en-GB", {
  timeZone: HOTEL_TIME_ZONE,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

export function hotelDateIso(value: Date = new Date()): string {
  const values: Record<string, string> = {};
  for (const part of HOTEL_DATE_FORMATTER.formatToParts(value)) {
    if (part.type !== "literal") values[part.type] = part.value;
  }
  const year = values.year;
  const month = values.month;
  const day = values.day;
  if (!year || !month || !day) throw new Error("Unable to resolve hotel-local date");
  return `${year}-${month}-${day}`;
}

export function shiftHotelDateIso(days: number, value: Date = new Date()): string {
  const [year, month, day] = hotelDateIso(value).split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day + days)).toISOString().slice(0, 10);
}

export function hotelMonthStartIso(value: Date = new Date()): string {
  return `${hotelDateIso(value).slice(0, 7)}-01`;
}
