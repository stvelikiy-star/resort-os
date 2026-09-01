"use client";

import { useEffect } from "react";
import { fallbackSiteContent, type SiteContent, type SiteLocale } from "../lib/siteContent";

type Payload = { locale: SiteLocale; content: SiteContent; published_version: number };

function localeFromLocation(): SiteLocale {
  const query = new URLSearchParams(window.location.search).get("lang");
  if (query === "kg" || query === "en" || query === "ru") return query;
  const stored = window.localStorage.getItem("three-crowns-site-language");
  if (stored === "kg" || stored === "en" || stored === "ru") return stored;
  return "ru";
}

function text(selector: string, value?: string) {
  if (!value) return;
  const element = document.querySelector<HTMLElement>(selector);
  if (element) element.textContent = value;
}

function setHref(selector: string, href: string | undefined) {
  if (!href) return;
  const element = document.querySelector<HTMLAnchorElement>(selector);
  if (element) element.href = href;
}

function preserveInternalLanguage(locale: SiteLocale) {
  if (locale === "ru") return;
  document.querySelectorAll<HTMLAnchorElement>('a[href^="/"]').forEach((link) => {
    try {
      const url = new URL(link.href, window.location.origin);
      if (url.origin !== window.location.origin) return;
      url.searchParams.set("lang", locale);
      link.href = `${url.pathname}${url.search}${url.hash}`;
    } catch {
      return;
    }
  });
}

function dispatchReady(locale: SiteLocale) {
  window.dispatchEvent(new CustomEvent("three-crowns:content-ready", { detail: { locale } }));
}

function applyContent(content: SiteContent, locale: SiteLocale) {
  document.documentElement.lang = locale === "kg" ? "ky" : locale;

  if (window.location.pathname === "/" || window.location.pathname === "") {
    text(".v3-hero-content .eyebrow", content.hero?.eyebrow);
    text("#hero-title", content.hero?.title);
    text(".v3-hero-copy", content.hero?.copy);
    text(".v3-hero-actions .button-accent", content.hero?.primary_cta);
    text(".v3-hero-actions .button-quiet", content.hero?.secondary_cta);

    text(".v3-booking-heading .eyebrow", content.booking?.eyebrow);
    text("#booking-experience-title", content.booking?.title);
    text(".v3-booking-intro-copy > p", content.booking?.intro);

    text(".v3-advantages .v3-section-head .eyebrow", content.advantages?.eyebrow);
    text("#advantages-title", content.advantages?.title);
    text(".v3-advantages .v3-section-head > p", content.advantages?.intro);

    text(".v3-groups-intro .eyebrow", content.groups?.eyebrow);
    text("#groups-title", content.groups?.title);
    text(".v3-groups-intro > p:not(.eyebrow)", content.groups?.copy);

    const phone = content.contacts?.phone;
    const whatsapp = content.contacts?.whatsapp;
    const email = content.contacts?.email;
    const address = content.contacts?.address;
    if (phone) {
      text('.v3-contact-actions a[href^="tel:"] strong', phone);
      setHref('.v3-contact-actions a[href^="tel:"]', `tel:${phone.replace(/[^+\d]/g, "")}`);
      const help = document.querySelector<HTMLAnchorElement>('.v3-help-actions a[href^="tel:"]');
      if (help) { help.textContent = `${locale === "en" ? "Call" : locale === "kg" ? "Чалуу" : "Позвонить"} · ${phone}`; help.href = `tel:${phone.replace(/[^+\d]/g, "")}`; }
    }
    if (whatsapp) {
      text('.v3-contact-actions a[href*="wa.me"] strong', whatsapp);
      const digits = whatsapp.replace(/\D/g, "");
      document.querySelectorAll<HTMLAnchorElement>('a[href*="wa.me"]').forEach((link) => { link.href = `https://wa.me/${digits}`; });
    }
    if (email) {
      text('.v3-contact-actions a[href^="mailto:"] strong', email);
      setHref('.v3-contact-actions a[href^="mailto:"]', `mailto:${email}`);
    }
    if (address) {
      const paragraph = document.querySelector<HTMLElement>(".v3-contact-head > div > p:last-child");
      if (paragraph) {
        const prefix = locale === "en" ? "Three Crowns Resort & SPA: " : locale === "kg" ? "Үч Таажы Resort & SPA: " : "Три Короны Resort & SPA: ";
        paragraph.textContent = `${prefix}${address}.`;
      }
    }

    if (content.seo?.title) document.title = content.seo.title;
    if (content.seo?.description) {
      let meta = document.querySelector<HTMLMetaElement>('meta[name="description"]');
      if (!meta) { meta = document.createElement("meta"); meta.name = "description"; document.head.appendChild(meta); }
      meta.content = content.seo.description;
    }
  }

  preserveInternalLanguage(locale);
}

function commitContent(content: SiteContent, locale: SiteLocale) {
  applyContent(content, locale);
  dispatchReady(locale);
  // content-ready listeners localize non-CMS UI synchronously. Re-apply only the
  // CMS-owned selectors afterwards so published content stays authoritative.
  queueMicrotask(() => applyContent(content, locale));
}

export default function SiteContentRuntime() {
  useEffect(() => {
    const locale = localeFromLocation();
    window.localStorage.setItem("three-crowns-site-language", locale);

    // Fail soft without falling back to Russian: every locale has an approved
    // local fallback and is replaced by the published Core payload when available.
    commitContent(fallbackSiteContent[locale], locale);

    const controller = new AbortController();
    fetch(`/core/api/v1/site/content?locale=${locale}`, { cache: "no-store", signal: controller.signal })
      .then(async (response) => response.ok ? (await response.json()) as Payload : null)
      .then((payload) => {
        if (payload?.content) commitContent(payload.content, locale);
      })
      .catch(() => undefined);
    return () => controller.abort();
  }, []);
  return null;
}
