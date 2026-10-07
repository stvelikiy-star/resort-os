"use client";

import { useCallback, useEffect, useState } from "react";

export type MarinaGuestLocale = "ru" | "kg" | "kz" | "en";

export const MARINA_GUEST_LOCALE_EVENT = "marina-smart:guest-locale";
export const MARINA_GUEST_LOCALE_KEY = "marina-smart-guest-locale";

const MARINA_SITE_LOCALE_KEY = "marina-smart-site-language";

export const MARINA_GUEST_LOCALES: MarinaGuestLocale[] = ["ru", "kg", "kz", "en"];

export function isMarinaGuestLocale(value: string | null | undefined): value is MarinaGuestLocale {
  return value === "ru" || value === "kg" || value === "kz" || value === "en";
}

export function marinaGuestHtmlLang(locale: MarinaGuestLocale): "ru" | "ky" | "kk" | "en" {
  if (locale === "kg") return "ky";
  if (locale === "kz") return "kk";
  return locale;
}

export function marinaGuestIntlLocale(locale: MarinaGuestLocale): string {
  if (locale === "kg") return "ky-KG";
  if (locale === "kz") return "kk-KZ";
  if (locale === "en") return "en-GB";
  return "ru-RU";
}

export function readMarinaGuestLocale(): MarinaGuestLocale {
  if (typeof window === "undefined") return "ru";
  const query = new URLSearchParams(window.location.search).get("lang");
  if (isMarinaGuestLocale(query)) return query;

  for (const key of [MARINA_GUEST_LOCALE_KEY, MARINA_SITE_LOCALE_KEY]) {
    const stored = window.localStorage.getItem(key);
    if (isMarinaGuestLocale(stored)) return stored;
  }
  return "ru";
}

export function applyMarinaGuestLocale(
  locale: MarinaGuestLocale,
  options: { emit?: boolean; updateUrl?: boolean } = {},
) {
  if (typeof window === "undefined") return;
  const { emit = true, updateUrl = false } = options;

  window.localStorage.setItem(MARINA_GUEST_LOCALE_KEY, locale);
  window.localStorage.setItem(MARINA_SITE_LOCALE_KEY, locale);
  document.documentElement.lang = marinaGuestHtmlLang(locale);

  if (updateUrl) {
    const url = new URL(window.location.href);
    url.searchParams.set("lang", locale);
    window.history.replaceState(window.history.state, "", url);
  }

  if (emit) {
    window.dispatchEvent(new CustomEvent(MARINA_GUEST_LOCALE_EVENT, { detail: { locale } }));
  }
}

export function useMarinaGuestLocale(): readonly [MarinaGuestLocale, (locale: MarinaGuestLocale) => void] {
  const [locale, setLocale] = useState<MarinaGuestLocale>("ru");

  useEffect(() => {
    const initial = readMarinaGuestLocale();
    setLocale(initial);
    applyMarinaGuestLocale(initial, { emit: false, updateUrl: false });

    const onLocale = (event: Event) => {
      const next = (event as CustomEvent<{ locale?: string }>).detail?.locale;
      if (!isMarinaGuestLocale(next)) return;
      setLocale(next);
      document.documentElement.lang = marinaGuestHtmlLang(next);
    };

    const onStorage = (event: StorageEvent) => {
      if (![MARINA_GUEST_LOCALE_KEY, MARINA_SITE_LOCALE_KEY].includes(event.key || "")) return;
      if (!isMarinaGuestLocale(event.newValue)) return;
      setLocale(event.newValue);
      document.documentElement.lang = marinaGuestHtmlLang(event.newValue);
    };

    window.addEventListener(MARINA_GUEST_LOCALE_EVENT, onLocale);
    window.addEventListener("storage", onStorage);
    return () => {
      window.removeEventListener(MARINA_GUEST_LOCALE_EVENT, onLocale);
      window.removeEventListener("storage", onStorage);
    };
  }, []);

  const chooseLocale = useCallback((next: MarinaGuestLocale) => {
    setLocale(next);
    applyMarinaGuestLocale(next, { emit: true, updateUrl: true });
  }, []);

  return [locale, chooseLocale] as const;
}
