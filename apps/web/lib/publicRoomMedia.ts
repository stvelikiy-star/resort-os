export type PublicRoomMedia = {
  hero: string;
  gallery: string[];
  source: "OWNER_APPROVED_2026_09_02";
};

const APPROVED_ROOM_MEDIA: Record<string, PublicRoomMedia> = {
  "cottage-double-standard": {
    hero: "/media/rooms/cottage-double-standard/hero.webp",
    gallery: ["/media/rooms/cottage-double-standard/hero.webp"],
    source: "OWNER_APPROVED_2026_09_02",
  },
  "two-room-standard": {
    hero: "/media/rooms/two-room-standard/hero.webp",
    gallery: ["/media/rooms/two-room-standard/hero.webp"],
    source: "OWNER_APPROVED_2026_09_02",
  },
  "apartments-with-kitchen": {
    hero: "/media/rooms/apartments-with-kitchen/hero.webp",
    gallery: ["/media/rooms/apartments-with-kitchen/hero.webp"],
    source: "OWNER_APPROVED_2026_09_02",
  },
};

export const approvedPublicRoomSlugs = Object.freeze(Object.keys(APPROVED_ROOM_MEDIA));

export function getPublicRoomMedia(slug: string): PublicRoomMedia | undefined {
  return APPROVED_ROOM_MEDIA[slug];
}
