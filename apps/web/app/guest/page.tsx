import type { Metadata } from "next";
// Supported guest landing locales: RU · KG · KZ · EN
import GuestLanding from "../../components/GuestLanding";

export const metadata: Metadata = {
  title: { absolute: "MARINA SMART · гостевой кабинет" },
  description: "Цифровой гостевой кабинет MARINA SMART. Вход по персональной ссылке или QR-коду.",
  alternates: null,
  openGraph: null,
  twitter: null,
  robots: { index: false, follow: false, noarchive: true, nosnippet: true },
};

export default function GuestWebHome() {
  return <GuestLanding />;
}
