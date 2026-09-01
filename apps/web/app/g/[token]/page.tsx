import type { Metadata } from "next";

import GuestConciergeRuntime from "../../../components/GuestConciergeRuntime";
import "../../guest-concierge.css";

type GuestOsPageProps = { params: Promise<{ token: string }> };

export const metadata: Metadata = {
  title: "Три Короны — цифровой консьерж",
  description: "Личный цифровой сервис гостя курорта Три Короны.",
  robots: { index: false, follow: false, noarchive: true, nosnippet: true },
};

export default async function GuestOsPage({ params }: GuestOsPageProps) {
  const { token } = await params;
  return <GuestConciergeRuntime token={token} />;
}
