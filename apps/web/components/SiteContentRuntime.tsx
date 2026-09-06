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

function text(selector: string, value?: string, root: ParentNode = document) {
  if (value === undefined) return;
  const element = root.querySelector<HTMLElement>(selector);
  if (element) element.textContent = value;
}

function setHref(selector: string, href: string | undefined, root: ParentNode = document) {
  if (href === undefined) return;
  const element = root.querySelector<HTMLAnchorElement>(selector);
  if (element) element.href = href;
}

function applyIndexedCards(
  selector: string,
  section: Record<string, string> | undefined,
  count: number,
  titleSelector: string,
  bodySelector: string,
) {
  if (!section) return;
  document.querySelectorAll<HTMLElement>(selector).forEach((card, rawIndex) => {
    const index = (rawIndex % count) + 1;
    text(titleSelector, section[`card_${index}_title`], card);
    text(bodySelector, section[`card_${index}_text`], card);
  });
}

function applyJourney(section: Record<string, string> | undefined) {
  if (!section) return;
  document.querySelectorAll<HTMLElement>(".v3-territory-route article").forEach((card, rawIndex) => {
    const index = rawIndex + 1;
    text("h3", section[`journey_${index}_title`], card);
    text("p", section[`journey_${index}_text`], card);
  });
}

function replacePriceSuffix(root: HTMLElement, suffix?: string) {
  if (suffix === undefined) return;
  const strong = root.querySelector<HTMLElement>("strong");
  if (!strong) return;
  const number = strong.textContent?.match(/[\d\s.,]+/)?.[0]?.trim();
  if (number) strong.textContent = `${number} ${suffix}`;
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

function ensureConferenceBlock(content: SiteContent, locale: SiteLocale) {
  const conference = content.conference;
  if (!conference?.title) return;

  let section = document.querySelector<HTMLElement>("#conference");
  if (!section) {
    const target = document.querySelector<HTMLElement>(".v3-groups");
    if (!target?.parentNode) return;
    section = document.createElement("section");
    section.id = "conference";
    section.className = "owner-conference";
    section.innerHTML = `
      <div class="wrap owner-conference-grid">
        <div class="owner-conference-copy">
          <p class="eyebrow" data-conference="eyebrow"></p>
          <h2 class="display-title" data-conference="title"></h2>
          <p class="owner-conference-lead" data-conference="copy"></p>
          <div class="owner-conference-facts">
            <article><small>${locale === "en" ? "Capacity" : locale === "kg" ? "Сыйымдуулук" : "Вместимость"}</small><strong data-conference="capacity"></strong></article>
            <article><small>${locale === "en" ? "Banquet" : locale === "kg" ? "Банкет" : "Банкет"}</small><strong data-conference="banquet"></strong></article>
            <article><small>${locale === "en" ? "Menu" : locale === "kg" ? "Меню" : "Меню"}</small><strong data-conference="menu"></strong></article>
          </div>
          <a class="button button-accent owner-conference-cta" data-conference="cta" target="_blank" rel="noreferrer"></a>
        </div>
        <div class="owner-conference-visual" aria-hidden="true">
          <span class="owner-conference-number">20</span>
          <div><strong>—</strong><span class="owner-conference-number">120</span></div>
          <p>${locale === "en" ? "conference · event · banquet" : locale === "kg" ? "конференция · иш-чара · банкет" : "конференция · событие · банкет"}</p>
        </div>
      </div>`;
    target.parentNode.insertBefore(section, target);
  }

  const set = (key: string, value?: string) => {
    if (value === undefined) return;
    const node = section?.querySelector<HTMLElement>(`[data-conference="${key}"]`);
    if (node) node.textContent = value;
  };
  set("eyebrow", conference.eyebrow);
  set("title", conference.title);
  set("copy", conference.copy);
  set("capacity", conference.capacity);
  set("banquet", conference.banquet);
  set("menu", conference.menu);
  set("cta", conference.cta);

  const button = section.querySelector<HTMLAnchorElement>('[data-conference="cta"]');
  const digits = (content.contacts?.whatsapp || content.contacts?.phone || "+996 558 08 50 02").replace(/\D/g, "");
  if (button) button.href = `https://wa.me/${digits}`;
}

function applyContent(content: SiteContent, locale: SiteLocale) {
  document.documentElement.lang = locale === "kg" ? "ky" : locale;

  if (window.location.pathname === "/" || window.location.pathname === "") {
    text(".v3-hero-content .eyebrow", content.hero?.eyebrow);
    text("#hero-title", content.hero?.title);
    text(".v3-hero-copy", content.hero?.copy);
    text(".v3-hero-actions .button-accent", content.hero?.primary_cta);
    text(".v3-hero-actions .button-quiet", content.hero?.secondary_cta);
    text(".v3-scroll-cue span", content.hero?.scroll_cta);

    text(".v3-booking-heading .eyebrow", content.booking?.eyebrow);
    text("#booking-experience-title", content.booking?.title);
    text(".v3-booking-intro-copy > p", content.booking?.intro);
    document.querySelectorAll<HTMLElement>(".v3-booking-trust span").forEach((node, index) => {
      const value = content.booking?.[`trust_${index + 1}`];
      if (value !== undefined) node.textContent = value;
    });
    text(".v3-booking-help .eyebrow", content.booking?.help_eyebrow);
    text(".v3-booking-help h3", content.booking?.help_title);
    text(".v3-booking-help > div:first-child > p:last-child", content.booking?.help_copy);
    const helpLinks = document.querySelectorAll<HTMLAnchorElement>(".v3-help-actions a");
    if (helpLinks[0] && content.booking?.help_call_label !== undefined) {
      const phone = content.contacts?.phone || "+996 558 08 50 02";
      helpLinks[0].textContent = `${content.booking.help_call_label} · ${phone}`;
    }
    if (helpLinks[1] && content.booking?.help_whatsapp_label !== undefined) helpLinks[1].textContent = content.booking.help_whatsapp_label;
    text(".v3-booking-rule strong", content.booking?.rule_title);
    text(".v3-booking-rule p", content.booking?.rule_copy);

    text(".v3-advantages .v3-section-head .eyebrow", content.advantages?.eyebrow);
    text("#advantages-title", content.advantages?.title);
    text(".v3-advantages .v3-section-head > p", content.advantages?.intro);
    applyIndexedCards(".v3-advantage-card", content.advantages, 6, "h3", "p");

    text(".v3-rooms .v3-section-head .eyebrow", content.rooms?.eyebrow);
    text("#rooms-title", content.rooms?.title);
    text(".v3-rooms .v3-section-head > div:last-child > p", content.rooms?.intro);
    text(".v3-rooms .v3-section-head .text-link", content.rooms?.catalog_cta);
    document.querySelectorAll<HTMLElement>(".v3-room-card").forEach((card) => {
      text(".v3-room-card-price small", content.rooms?.high_season_label, card);
      text(".v3-room-card-body > b", content.rooms?.card_cta, card);
      const price = card.querySelector<HTMLElement>(".v3-room-card-price");
      if (price) replacePriceSuffix(price, content.rooms?.per_night_label);
    });

    text(".v3-territory .v3-section-head .eyebrow", content.territory?.eyebrow);
    text("#territory-title", content.territory?.title);
    text(".v3-territory .v3-section-head > p", content.territory?.intro);
    text(".v3-film-caption span", content.territory?.visual_label);
    text(".v3-film-caption strong", content.territory?.visual_caption);
    applyJourney(content.territory);

    text(".v3-amenities-copy .eyebrow", content.amenities?.eyebrow);
    text("#amenities-title", content.amenities?.title);
    text(".v3-amenities-copy .lead", content.amenities?.intro);
    document.querySelectorAll<HTMLElement>(".v3-water-tags span").forEach((node, index) => {
      const value = content.amenities?.[`tag_${index + 1}`];
      if (value !== undefined) node.textContent = value;
    });
    text(".v3-amenities-copy .button", content.amenities?.cta);
    text(".v3-lake-film figcaption span", content.amenities?.visual_label);
    text(".v3-lake-film figcaption strong", content.amenities?.visual_caption);
    if (content.amenities) {
      document.querySelectorAll<HTMLElement>(".v3-amenity-grid article").forEach((card, rawIndex) => {
        const index = rawIndex + 1;
        if (index > 5) return; // card 6 is the canonical included-in-stay fact, not generic marketing CMS.
        text("h3", content.amenities?.[`card_${index}_title`], card);
        text("p", content.amenities?.[`card_${index}_text`], card);
      });
    }

    ensureConferenceBlock(content, locale);

    text(".v3-groups-intro .eyebrow", content.groups?.eyebrow);
    text("#groups-title", content.groups?.title);
    text(".v3-groups-intro > p:not(.eyebrow)", content.groups?.copy);
    text(".v3-groups-intro .button", content.groups?.cta);
    applyIndexedCards(".v3-group-grid article", content.groups, 4, "h3", "p");

    text(".v3-contact-head .eyebrow", content.contacts?.eyebrow);
    text("#contacts-title", content.contacts?.title);
    text(".v3-contact-head > div > p:last-child", content.contacts?.intro);
    const contactLabels = document.querySelectorAll<HTMLElement>(".v3-contact-actions a span");
    [content.contacts?.phone_label, content.contacts?.whatsapp_label, content.contacts?.email_label].forEach((value, index) => {
      if (contactLabels[index] && value !== undefined) contactLabels[index].textContent = value;
    });
    text(".v3-arrival-card .eyebrow", content.contacts?.pretrip_eyebrow);
    text(".v3-arrival-card h3", content.contacts?.pretrip_title);
    text(".v3-arrival-card > p:not(.eyebrow)", content.contacts?.pretrip_copy);
    text(".v3-arrival-card .button", content.contacts?.booking_cta);
    text(".v3-arrival-card .text-link", content.contacts?.map_cta);

    const phone = content.contacts?.phone;
    const whatsapp = content.contacts?.whatsapp;
    const email = content.contacts?.email;
    const address = content.contacts?.address;
    if (phone) {
      text('.v3-contact-actions a[href^="tel:"] strong', phone);
      setHref('.v3-contact-actions a[href^="tel:"]', `tel:${phone.replace(/[^+\d]/g, "")}`);
      const help = document.querySelector<HTMLAnchorElement>('.v3-help-actions a[href^="tel:"]');
      if (help) {
        help.textContent = `${content.booking?.help_call_label || (locale === "en" ? "Call" : locale === "kg" ? "Чалуу" : "Позвонить")} · ${phone}`;
        help.href = `tel:${phone.replace(/[^+\d]/g, "")}`;
      }
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
      const encoded = encodeURIComponent(address);
      const map = document.querySelector<HTMLIFrameElement>(".v3-map-card iframe");
      if (map) map.src = `https://www.google.com/maps?q=${encoded}&output=embed`;
      setHref(".v3-arrival-card .text-link", `https://www.google.com/maps/search/?api=1&query=${encoded}`);
    }

    text(".v3-final-cta .eyebrow", content.final?.eyebrow);
    text(".v3-final-cta h2", content.final?.title);
    text(".v3-final-cta .v3-final-layout > div:last-child > p", content.final?.copy);
    text(".v3-final-cta .button", content.final?.cta);
    text(".home-footer-inner > strong", content.final?.footer_brand);
    const footerLinks = document.querySelectorAll<HTMLElement>(".home-footer-links a");
    [content.final?.footer_rooms, content.final?.footer_resort, content.final?.footer_groups, content.final?.footer_contacts].forEach((value, index) => {
      if (footerLinks[index] && value !== undefined) footerLinks[index].textContent = value;
    });
    text(".mobile-book", content.final?.mobile_cta);

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
  // content-ready listeners localize non-CMS/domain UI synchronously. Re-apply
  // CMS-owned selectors afterwards so published editorial copy stays authoritative.
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
