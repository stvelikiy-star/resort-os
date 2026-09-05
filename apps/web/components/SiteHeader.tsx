"use client";

import { useEffect, useState } from "react";

type Locale = "ru" | "kg" | "en";

type NavCopy = {
  rooms: string;
  territory: string;
  amenities: string;
  reviews: string;
  groups: string;
  contacts: string;
  book: string;
  menuOpen: string;
  menuClose: string;
  home: string;
  subtitle: string;
  nav: string;
  mobileNav: string;
  language: string;
};

const NAV: Record<Locale, NavCopy> = {
  ru: { rooms: "Номера", territory: "Территория", amenities: "На территории", reviews: "Отзывы", groups: "Группам", contacts: "Контакты", book: "Проверить даты", menuOpen: "Открыть меню", menuClose: "Закрыть меню", home: "Три Короны — на главную", subtitle: "Resort & SPA · Issyk-Kul", nav: "Основная навигация", mobileNav: "Мобильная навигация", language: "Язык сайта" },
  kg: { rooms: "Номерлер", territory: "Аймак", amenities: "Инфраструктура", reviews: "Пикирлер", groups: "Топторго", contacts: "Байланыш", book: "Даталарды текшерүү", menuOpen: "Менюну ачуу", menuClose: "Менюну жабуу", home: "Үч Таажы — башкы бет", subtitle: "Resort & SPA · Ысык-Көл", nav: "Негизги навигация", mobileNav: "Мобилдик навигация", language: "Сайттын тили" },
  en: { rooms: "Rooms", territory: "Resort", amenities: "Facilities", reviews: "Reviews", groups: "Groups", contacts: "Contacts", book: "Check dates", menuOpen: "Open menu", menuClose: "Close menu", home: "Three Crowns — home", subtitle: "Resort & SPA · Issyk-Kul", nav: "Main navigation", mobileNav: "Mobile navigation", language: "Site language" },
};

export default function SiteHeader() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const [locale, setLocale] = useState<Locale>("ru");

  useEffect(() => {
    const query = new URLSearchParams(window.location.search).get("lang");
    const stored = window.localStorage.getItem("three-crowns-site-language");
    const selected: Locale = query === "kg" || query === "en" || query === "ru" ? query : stored === "kg" || stored === "en" || stored === "ru" ? stored : "ru";
    setLocale(selected);
    window.localStorage.setItem("three-crowns-site-language", selected);
  }, []);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 36);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => { if (event.key === "Escape") setOpen(false); };
    document.body.classList.add("menu-open");
    window.addEventListener("keydown", onKeyDown);
    return () => { document.body.classList.remove("menu-open"); window.removeEventListener("keydown", onKeyDown); };
  }, [open]);

  const closeMenu = () => setOpen(false);
  const copy = NAV[locale];
  const withLanguage = (href: string) => {
    const hashIndex = href.indexOf("#");
    const base = hashIndex >= 0 ? href.slice(0, hashIndex) : href;
    const hash = hashIndex >= 0 ? href.slice(hashIndex) : "";
    if (locale === "ru") return `${base}${hash}`;
    const separator = base.includes("?") ? "&" : "?";
    return `${base}${separator}lang=${locale}${hash}`;
  };
  const links = [[withLanguage("/rooms"), copy.rooms],[withLanguage("/#resort"), copy.territory],[withLanguage("/#experience"), copy.amenities],[withLanguage("/#reviews"), copy.reviews],[withLanguage("/#groups"), copy.groups],[withLanguage("/#contacts"), copy.contacts]];

  function switchLanguage(next: Locale) {
    window.localStorage.setItem("three-crowns-site-language", next);
    const url = new URL(window.location.href);
    if (next === "ru") url.searchParams.delete("lang"); else url.searchParams.set("lang", next);
    window.location.href = `${url.pathname}${url.search}${url.hash}`;
  }

  const languageControl = (className: string) => <div className={`site-language-switcher ${className}`} aria-label={copy.language}><button className={locale === "ru" ? "active" : ""} onClick={() => switchLanguage("ru")} type="button">RU</button><button className={locale === "kg" ? "active" : ""} onClick={() => switchLanguage("kg")} type="button">KG</button><button className={locale === "en" ? "active" : ""} onClick={() => switchLanguage("en")} type="button">EN</button></div>;

  return (
    <header className={`site-header ${scrolled ? "is-scrolled" : ""}`}>
      <div className="wrap header-inner">
        <a className="brand" href={withLanguage("/")} aria-label={copy.home} onClick={closeMenu}>
          <img src="/brand/three-crowns-mark.svg" alt="" width="118" height="33" />
          <span className="brand-copy"><strong>{locale === "en" ? "THREE CROWNS" : locale === "kg" ? "ҮЧ ТААЖЫ" : "ТРИ КОРОНЫ"}</strong><small>{copy.subtitle}</small></span>
        </a>
        <nav className="desktop-nav" aria-label={copy.nav}>{links.map(([href,label]) => <a key={href} href={href}>{label}</a>)}</nav>
        {languageControl("desktop-language")}
        <a className="header-book desktop-only" href={withLanguage("/#booking")}>{copy.book}</a>
        <button className="menu-toggle" type="button" aria-expanded={open} aria-controls="mobile-menu" aria-label={open ? copy.menuClose : copy.menuOpen} onClick={() => setOpen((value) => !value)}><span /><span /></button>
      </div>
      <div className={`mobile-menu ${open ? "is-open" : ""}`} id="mobile-menu" aria-hidden={!open}><nav className="wrap" aria-label={copy.mobileNav}>{languageControl("mobile-language")}{links.map(([href,label]) => <a key={href} href={href} onClick={closeMenu}>{label}</a>)}<a className="button button-accent" href={withLanguage("/#booking")} onClick={closeMenu}>{copy.book}</a></nav></div>
    </header>
  );
}
