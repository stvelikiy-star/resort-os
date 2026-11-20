import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "MARINA SMART · Персонал",
    short_name: "MARINA SMART",
    description: "Housekeeping and maintenance operations for MARINA SMART Hotel OS",
    start_url: "/",
    display: "standalone",
    background_color: "#0B1F2A",
    theme_color: "#0B1F2A",
    lang: "ru",
    icons: [
      // Use the exact approved MARINA SMART PNG, shared with Web/Admin/Mobile.
      // Maskable asset keeps the approved logo within its verified safe zone.
      { src: "/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" }
    ],
  };
}
