import type { Metadata } from "next";

import ServicePointRuntime from "../../../components/ServicePointRuntime";
import "../../service-point.css";

type ServicePointPageProps = { params: Promise<{ token: string }> };

export const metadata: Metadata = {
  title: "Помощь на территории · Три Короны",
  description: "Анонимная заявка по QR-коду общественной зоны Три Короны Resort & SPA.",
  robots: { index: false, follow: false, noarchive: true, nosnippet: true },
};

export default async function ServicePointPage({ params }: ServicePointPageProps) {
  const { token } = await params;
  return <ServicePointRuntime token={token} />;
}
