import type { MetadataRoute } from "next";

import { roomCategories } from "../lib/roomCatalog";

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: "https://3korony.com",
      changeFrequency: "weekly",
      priority: 1,
    },
    {
      url: "https://3korony.com/rooms",
      changeFrequency: "weekly",
      priority: 0.9,
    },
    ...roomCategories.map((room) => ({
      url: `https://3korony.com/rooms/${room.slug}`,
      changeFrequency: "weekly" as const,
      priority: 0.8,
    })),
  ];
}
