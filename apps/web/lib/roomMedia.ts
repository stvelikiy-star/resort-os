export const ROOM_MEDIA_FALLBACK = "/media/three-crowns/hero-resort.webp";

export type RoomMediaSet = {
  hero: string;
  gallery: string[];
  status: "APPROVED_PROCESSED";
};

const media = (folder: string, prefix: string, count: number): RoomMediaSet => ({
  hero: `/media/three-crowns/rooms/${folder}/${prefix}-01.webp`,
  gallery: Array.from({ length: count }, (_, index) =>
    `/media/three-crowns/rooms/${folder}/${prefix}-${String(index + 1).padStart(2, "0")}.webp`,
  ),
  status: "APPROVED_PROCESSED",
});

export const roomMediaBySlug: Record<string, RoomMediaSet> = {
  "cottage-double-standard": media("05", "cottage-double-standard", 9),
  "two-room-standard": media("10", "two-room-standard", 6),
  "apartments-with-kitchen": media("12", "apartment-kitchen", 8),
};

export const roomMediaByCode: Record<string, RoomMediaSet> = {
  COTTAGE_DOUBLE_STANDARD: roomMediaBySlug["cottage-double-standard"],
  TWO_ROOM_STANDARD: roomMediaBySlug["two-room-standard"],
  APARTMENT_KITCHEN: roomMediaBySlug["apartments-with-kitchen"],
};

export function getRoomMedia(slug: string) {
  return roomMediaBySlug[slug] ?? null;
}

export function getRoomHero(slug: string) {
  return getRoomMedia(slug)?.hero ?? ROOM_MEDIA_FALLBACK;
}

export function getRoomMediaByCode(code: string) {
  return roomMediaByCode[code] ?? null;
}
