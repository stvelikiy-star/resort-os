import type { Metadata } from "next";
import "./globals.css";
import "./footer.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://3korony.com"),
  title: {
    default: "Три Короны — Resort & SPA, Иссык-Куль",
    template: "%s · Три Короны",
  },
  description: "Пансионат «Три Короны» в Чолпон-Ате: 84 номера, собственный пляж, 150-метровый пирс, SPA, бассейн и онлайн-проверка доступности номеров.",
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    locale: "ru_RU",
    url: "/",
    siteName: "Три Короны Resort & SPA",
    title: "Три Короны — Resort & SPA, Иссык-Куль",
    description: "Отдых в Чолпон-Ате: собственный пляж, пирс, SPA, бассейн и 12 категорий номеров.",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  );
}
