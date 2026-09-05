import type { Metadata } from "next";

import GuestConciergeRuntime from "../../../components/GuestConciergeRuntime";
import GuestMarketplace from "../../../components/GuestMarketplace";
import "../../guest-concierge.css";
import "../../guest-marketplace.css";
import "../../guest-owner-corrections.css";

type GuestOsPageProps = { params: Promise<{ token: string }> };

export const metadata: Metadata = {
  title: "Три Короны — цифровой консьерж",
  description: "Личный цифровой сервис гостя курорта Три Короны.",
  robots: { index: false, follow: false, noarchive: true, nosnippet: true },
};

export default async function GuestOsPage({ params }: GuestOsPageProps) {
  const { token } = await params;
  return <>
    <GuestConciergeRuntime token={token} />
    <div className="concierge-page guest-marketplace-host"><GuestMarketplace token={token} /></div>
    <style>{`.concierge-page ~ .ai-admin-root{display:none!important}`}</style>
  </>;
}
