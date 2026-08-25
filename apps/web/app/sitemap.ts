import type { MetadataRoute } from "next";

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: "https://3korony.com",
      changeFrequency: "weekly",
      priority: 1,
    },
  ];
}
