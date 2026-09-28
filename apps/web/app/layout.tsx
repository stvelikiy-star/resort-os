import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "AK BERMET — MARINA SMART",
    template: "%s · MARINA SMART",
  },
  description: "Цифровой гостевой кабинет AK BERMET на платформе MARINA SMART.",
  applicationName: "MARINA SMART",
  robots: { index: false, follow: false, noarchive: true, nosnippet: true },
};

export const viewport: Viewport = {
  themeColor: "#0B1C1A",
  colorScheme: "dark",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  );
}
