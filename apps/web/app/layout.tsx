import type { Metadata, Viewport } from "next";
import AiAdministratorWidget from "../components/AiAdministratorWidget";
import GuestServicesRuntime from "../components/GuestServicesRuntime";
import PremiumMotion from "../components/PremiumMotion";
import PublicUiI18nRuntime from "../components/PublicUiI18nRuntime";
import SiteContentRuntime from "../components/SiteContentRuntime";
import SiteMediaRuntime from "../components/SiteMediaRuntime";
import { getPublishedSiteContent } from "../lib/siteContent";
import "./globals.css";
import "./premium-expansion.css";
import "./final-polish.css";
import "./home-v2.css";
import "./rooms-premium.css";
import "./gallery-premium.css";
import "./site-v3.css";
import "./video-sections.css";
import "./premium-experience.css";
import "./site-cms.css";
import "./owner-corrections.css";
import "./mobile-hardening.css";
import "./ai-admin.css";
import "./luxury-director.css";

export async function generateMetadata(): Promise<Metadata> {
  const { content } = await getPublishedSiteContent("ru");
  const title = content.seo?.title || "Три Короны — Resort & SPA на Иссык-Куле";
  const description = content.seo?.description || "Три Короны Resort & SPA в Чолпон-Ате: 84 номера, конференц-зал на 20–120 гостей, собственный пляж, пирс 150 м, SPA и открытый бассейн.";
  return {
    metadataBase: new URL("https://3korony.com"),
    title: { default: title, template: "%s · Три Короны" },
    description,
    keywords: ["Три Короны", "Иссык-Куль", "Чолпон-Ата", "отель Иссык-Куль", "Resort & SPA", "конференц-зал Иссык-Куль", "банкет Чолпон-Ата", "отдых на Иссык-Куле", "бронирование Чолпон-Ата", "семейный отдых Иссык-Куль", "корпоративный отдых Иссык-Куль"],
    alternates: { canonical: "/" },
    openGraph: {
      type: "website",
      locale: "ru_RU",
      url: "/",
      siteName: "Три Короны Resort & SPA",
      title,
      description,
      images: [{ url: "/media/three-crowns/hero-resort.webp", alt: "Три Короны Resort & SPA на Иссык-Куле" }],
    },
    twitter: { card: "summary_large_image", title, description, images: ["/media/three-crowns/hero-resort.webp"] },
    robots: { index: true, follow: true, googleBot: { index: true, follow: true, "max-image-preview": "large", "max-snippet": -1 } },
  };
}

export const viewport: Viewport = { themeColor: "#0A1128", colorScheme: "dark light" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="ru"><body><PremiumMotion /><SiteContentRuntime /><SiteMediaRuntime /><PublicUiI18nRuntime /><GuestServicesRuntime />{children}<AiAdministratorWidget /></body></html>;
}
