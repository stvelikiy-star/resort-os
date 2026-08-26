"use client";

import { useEffect } from "react";

export default function ActionRuntime() {
  useEffect(() => {
    const root = document.documentElement;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let raf = 0;

    const updateScroll = () => {
      if (raf) return;
      raf = window.requestAnimationFrame(() => {
        raf = 0;
        const max = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
        const progress = Math.min(1, Math.max(0, window.scrollY / max));
        root.style.setProperty("--action-progress", String(progress));
        root.style.setProperty("--action-hero-y", `${Math.min(window.scrollY * 0.16, 130)}px`);
      });
    };

    const onPointerMove = (event: PointerEvent) => {
      if (reduced || event.pointerType === "touch") return;
      const x = ((event.clientX / window.innerWidth) - 0.5) * 16;
      const y = ((event.clientY / window.innerHeight) - 0.5) * 10;
      root.style.setProperty("--action-pointer-x", `${x.toFixed(2)}px`);
      root.style.setProperty("--action-pointer-y", `${y.toFixed(2)}px`);
    };

    const revealNodes = Array.from(document.querySelectorAll<HTMLElement>("[data-reveal]"));
    let observer: IntersectionObserver | null = null;

    if (reduced) {
      revealNodes.forEach((node) => node.classList.add("is-revealed"));
    } else {
      observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              (entry.target as HTMLElement).classList.add("is-revealed");
              observer?.unobserve(entry.target);
            }
          });
        },
        { rootMargin: "0px 0px -10% 0px", threshold: 0.08 },
      );
      revealNodes.forEach((node) => observer?.observe(node));
    }

    document.body.classList.add("action-ready");
    window.addEventListener("scroll", updateScroll, { passive: true });
    window.addEventListener("resize", updateScroll, { passive: true });
    window.addEventListener("pointermove", onPointerMove, { passive: true });
    updateScroll();

    return () => {
      document.body.classList.remove("action-ready");
      window.removeEventListener("scroll", updateScroll);
      window.removeEventListener("resize", updateScroll);
      window.removeEventListener("pointermove", onPointerMove);
      observer?.disconnect();
      if (raf) window.cancelAnimationFrame(raf);
    };
  }, []);

  return <div className="action-progress" aria-hidden="true"><span /></div>;
}
