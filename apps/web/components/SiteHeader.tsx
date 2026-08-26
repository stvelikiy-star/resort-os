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
  const links = [["/rooms","Номера"],["/#rates","Цены"],["/#resort","Курорт"],["/#experience","Отдых"],["/#gallery","Галерея"],["/#contacts","Контакты"]];

  return (
    <header className={`site-header ${scrolled ? "is-scrolled" : ""}`}>
      <div className="wrap header-inner">
        <a className="brand" href="/" aria-label="Три Короны — на главную" onClick={closeMenu}>
          <img src="/brand/three-crowns-mark.svg" alt="" width="118" height="33" />
          <span className="brand-copy"><strong>ТРИ КОРОНЫ</strong><small>Resort & SPA · Issyk-Kul</small></span>
        </a>
        <nav className="desktop-nav" aria-label="Основная навигация">{links.map(([href,label]) => <a key={href} href={href}>{label}</a>)}</nav>
        <a className="header-book desktop-only" href="/#booking">Проверить даты</a>
        <button className="menu-toggle" type="button" aria-expanded={open} aria-controls="mobile-menu" aria-label={open ? "Закрыть меню" : "Открыть меню"} onClick={() => setOpen((value) => !value)}><span /><span /></button>
      </div>
      <div className={`mobile-menu ${open ? "is-open" : ""}`} id="mobile-menu" aria-hidden={!open}><nav className="wrap" aria-label="Мобильная навигация">{links.map(([href,label]) => <a key={href} href={href} onClick={closeMenu}>{label}</a>)}<a className="button button-accent" href="/#booking" onClick={closeMenu}>Проверить даты</a></nav></div>
    </header>
  );
}
