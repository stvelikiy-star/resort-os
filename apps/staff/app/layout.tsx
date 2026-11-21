import type { Metadata, Viewport } from "next";
import Script from "next/script";
import StaffLocaleRuntime from "../components/StaffLocaleRuntime";
import "./globals.css";
import "./shift-v2.css";
import "../../../packages/design/premium-motion.css";

export const metadata: Metadata = {
  title: "MARINA SMART · Моя смена",
  icons: { icon: "/marina-smart-approved.png", apple: "/marina-smart-approved.png" },
  description: "Мобильный операционный интерфейс Hotel OS для персонала",
  manifest: "/manifest.webmanifest",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#0B1F2A",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ru">
      <body><StaffLocaleRuntime />{children}</body>
      <Script src="https://telegram.org/js/telegram-web-app.js" strategy="beforeInteractive" />
    </html>
  );
}
