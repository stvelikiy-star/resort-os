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
      // Do not declare it maskable until a safe-zone-compliant branded asset is verified.
      { src: "/marina-smart-approved.png", sizes: "any", type: "image/png", purpose: "any" }
    ],
  };
}
