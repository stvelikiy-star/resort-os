import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Три Короны — Resort & SPA, Иссык-Куль",
  description: "Отель «Три Короны» в Чолпон-Ате: 84 номера, собственный пляж, 150-метровый пирс, SPA и отдых на Иссык-Куле.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  );
}
