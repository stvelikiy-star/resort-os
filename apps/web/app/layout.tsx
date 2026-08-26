import type { Metadata, Viewport } from "next";
import "./globals.css";
import "./premium-expansion.css";
import "./final-polish.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://3korony.com"),
  title: { default: "Три Короны — Resort & SPA на Иссык-Куле", template: "%s · Три Короны" },
  description: "Три Короны Resort & SPA в Чолпон-Ате: 84 номера, 12 категорий, собственный пляж, 150-метровый пирс, SPA, открытый бассейн и реальная проверка наличия по датам.",
  alternates: { canonical: "/" },
  openGraph: { type: "website", locale: "ru_RU", url: "/", siteName: "Три Короны Resort & SPA", title: "Три Короны — Resort & SPA на Иссык-Куле", description: "Курорт в Чолпон-Ате: собственный пляж, пирс 150 м, SPA, бассейн и 12 категорий номеров." },
  twitter: { card: "summary_large_image", title: "Три Короны — Resort & SPA на Иссык-Куле", description: "Проверяйте реальную доступность и стоимость проживания на выбранные даты." },
  robots: { index: true, follow: true, googleBot: { index: true, follow: true, "max-image-preview": "large", "max-snippet": -1 } },
};

export const viewport: Viewport = { themeColor: "#0b2d63", colorScheme: "light" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="ru"><body>{children}</body></html>;
}