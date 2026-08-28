import type { Metadata, Viewport } from "next";
import Script from "next/script";
import "./globals.css";
import "./shift-v2.css";

export const metadata: Metadata = {
  title: "Три Короны · Моя смена",
  description: "Мобильный операционный интерфейс Resort OS для персонала",
  manifest: "/manifest.webmanifest",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#0A1128",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ru">
      <body>{children}</body>
      <Script src="https://telegram.org/js/telegram-web-app.js" strategy="beforeInteractive" />
    </html>
  );
}
