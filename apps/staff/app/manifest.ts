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
      { src: "/marina-smart-approved.png", sizes: "1024x1024", type: "image/png", purpose: "any" },
      { src: "/marina-smart-maskable.png", sizes: "512x512", type: "image/png", purpose: "maskable" }
    ],
  };
}
