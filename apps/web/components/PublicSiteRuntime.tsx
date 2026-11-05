"use client";

import { usePathname } from "next/navigation";

import AiAdministratorWidget from "./AiAdministratorWidget";
import GuestServicesRuntime from "./GuestServicesRuntime";
import PremiumMotion from "./PremiumMotion";
import PublicUiI18nRuntime from "./PublicUiI18nRuntime";
import SiteContentRuntime from "./SiteContentRuntime";
import SiteMediaRuntime from "./SiteMediaRuntime";

export default function PublicSiteRuntime() {
  const pathname = usePathname();
  if (pathname === "/guest" || pathname.startsWith("/g/") || pathname.startsWith("/p/")) return null;

  return <>
    <PremiumMotion />
    <SiteContentRuntime />
    <SiteMediaRuntime />
    <PublicUiI18nRuntime />
    <GuestServicesRuntime />
    <AiAdministratorWidget />
  </>;
}
