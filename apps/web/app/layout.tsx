import type { Metadata, Viewport } from "next";
import "./globals.css";
import "./premium-expansion.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://3korony.com"),
  title: { default: "Три Короны — Resort & SPA на Иссык-Куле", template: "%s · Три Короны" },
  description: "Три Короны Resort & SPA в Чолпон-Ате: 84 номера, собственный пляж, 150-метровый пирс, SPA, открытый бассейн и проверка реальной доступности по датам.",
  alternates: { canonical: "/" },
  openGraph: { type: "website", locale: "ru_RU", url: "/", siteName: "Три Короны Resort & SPA", title: "Три Короны — Resort & SPA на Иссык-Куле", description: "Курорт в Чолпон-Ате с собственным пляжем, 150-метровым пирсом, SPA и 12 категориями номеров." },
  twitter: { card: "summary", title: "Три Короны — Resort & SPA на Иссык-Куле", description: "Проверяйте реальную доступность номеров на выбранные даты." },
  robots: { index: true, follow: true, googleBot: { index: true, follow: true, "max-image-preview": "large", "max-snippet": -1 } },
};

export const viewport: Viewport = { themeColor: "#10261f", colorScheme: "light" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="ru"><body>{children}</body></html>;
}
