import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "MARINA SMART · Персонал",
    short_name: "MARINA SMART",
    description: "Housekeeping and maintenance operations for MARINA SMART Hotel OS",
    start_url: "/",
    display: "standalone",
    background_color: "#f4f6f3",
    theme_color: "#173f31",
    lang: "ru",
    icons: [
      { src: "/icon.svg", sizes: "any", type: "image/svg+xml", purpose: "any" },
      { src: "/icon-maskable.svg", sizes: "any", type: "image/svg+xml", purpose: "maskable" }
    ],
  };
}
