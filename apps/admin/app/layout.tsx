import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Три Короны — PMS",
  description: "Resort OS control center for Three Crowns",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  );
}
