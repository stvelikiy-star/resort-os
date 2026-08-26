"use client";

import { useEffect, useState } from "react";

export default function SiteHeader() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

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

  return (
    <header className={`site-header ${scrolled ? "is-scrolled" : ""}`}>
      <div className="wrap header-inner">
        <a className="brand" href="#top" aria-label="Три Короны — на главную" onClick={closeMenu}><strong>ТРИ КОРОНЫ</strong><span>Resort & SPA · Issyk-Kul</span></a>
        <nav className="desktop-nav" aria-label="Основная навигация"><a href="#rooms">Номера</a><a href="#resort">Курорт</a><a href="#spa">SPA</a><a href="#gallery">Галерея</a><a href="#contacts">Контакты</a></nav>
        <a className="header-book desktop-only" href="#booking">Проверить даты</a>
        <button className="menu-toggle" type="button" aria-expanded={open} aria-controls="mobile-menu" aria-label={open ? "Закрыть меню" : "Открыть меню"} onClick={() => setOpen((value) => !value)}><span /><span /></button>
      </div>
      <div className={`mobile-menu ${open ? "is-open" : ""}`} id="mobile-menu" aria-hidden={!open}><nav className="wrap" aria-label="Мобильная навигация"><a href="#rooms" onClick={closeMenu}>Номера</a><a href="#resort" onClick={closeMenu}>Курорт</a><a href="#spa" onClick={closeMenu}>SPA</a><a href="#gallery" onClick={closeMenu}>Галерея</a><a href="#contacts" onClick={closeMenu}>Контакты</a><a className="button button-accent" href="#booking" onClick={closeMenu}>Проверить даты</a></nav></div>
    </header>
  );
}
