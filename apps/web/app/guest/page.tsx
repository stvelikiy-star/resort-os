import type { Metadata } from "next";
// Supported guest landing locales: RU · KG · KZ · EN
import GuestLanding from "../../components/GuestLanding";

export const metadata: Metadata = {
  title: { absolute: "AK BERMET — MARINA SMART · гостевой кабинет" },
  description: "Вход в цифровой гостевой кабинет AK BERMET на платформе MARINA SMART.",
  alternates: null,
  openGraph: null,
  twitter: null,
  robots: { index: false, follow: false, noarchive: true, nosnippet: true },
};

export default function GuestWebHome() {
  return <GuestLanding />;
}
