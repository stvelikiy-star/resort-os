import type { Metadata } from "next";

import GuestOsRuntime from "../../../components/GuestOsRuntime";
import "../../guest-os.css";

type GuestOsPageProps = { params: Promise<{ token: string }> };

export const metadata: Metadata = {
  title: "Guest OS",
  description: "Цифровой консьерж гостя Три Короны Resort & SPA.",
  robots: { index: false, follow: false, noarchive: true, nosnippet: true },
};

export default async function GuestOsPage({ params }: GuestOsPageProps) {
  const { token } = await params;
  return <GuestOsRuntime token={token} />;
}
