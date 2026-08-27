"use client";

import { useEffect } from "react";

export default function PremiumMotion() {
  useEffect(() => {
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const finePointer = window.matchMedia("(pointer: fine)").matches;

    document.documentElement.classList.add("premium-js");

    const revealTargets = Array.from(
      document.querySelectorAll<HTMLElement>(
        ".display-title, .v3-section-head > p, .v3-booking-intro-copy, .v3-room-card, .v3-advantage-card, .v3-territory-route article, .v3-amenity-grid article, .v3-review-grid article, .v3-extra-grid article, .v3-group-grid article, .v3-contact-actions a"
      )
    );

    if (reduceMotion) {
      revealTargets.forEach((node) => node.classList.add("is-revealed"));
    } else {
      revealTargets.forEach((node) => node.classList.add("premium-reveal"));
      const observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              (entry.target as HTMLElement).classList.add("is-revealed");
              observer.unobserve(entry.target);
            }
          });
        },
        { rootMargin: "0px 0px -10% 0px", threshold: 0.08 }
      );
      revealTargets.forEach((node) => observer.observe(node));

      const parallaxTargets = Array.from(
        document.querySelectorAll<HTMLElement>(".v3-hero-media, .v3-territory-film, .v3-lake-media")
      );
      let raf = 0;
      const updateParallax = () => {
        raf = 0;
        const viewport = window.innerHeight || 1;
        parallaxTargets.forEach((node) => {
          const rect = node.getBoundingClientRect();
          const center = rect.top + rect.height / 2;
          const offset = Math.max(-1, Math.min(1, (center - viewport / 2) / viewport));
          node.style.setProperty("--premium-parallax", `${offset * -18}px`);
        });
      };
      const onScroll = () => {
        if (!raf) raf = window.requestAnimationFrame(updateParallax);
      };
      updateParallax();
      window.addEventListener("scroll", onScroll, { passive: true });
      window.addEventListener("resize", onScroll);

      if (finePointer) {
        const cursor = document.createElement("div");
        cursor.className = "premium-cursor";
        document.body.appendChild(cursor);
        const interactive = "a, button, input, select, video, .v3-room-card, .v3-advantage-card";
        const move = (event: MouseEvent) => {
          cursor.style.transform = `translate3d(${event.clientX}px, ${event.clientY}px, 0)`;
        };
        const over = (event: MouseEvent) => {
          const target = event.target as Element | null;
          cursor.classList.toggle("is-active", Boolean(target?.closest(interactive)));
        };
        window.addEventListener("mousemove", move, { passive: true });
        window.addEventListener("mouseover", over, { passive: true });

        return () => {
          observer.disconnect();
          if (raf) cancelAnimationFrame(raf);
          window.removeEventListener("scroll", onScroll);
          window.removeEventListener("resize", onScroll);
          window.removeEventListener("mousemove", move);
          window.removeEventListener("mouseover", over);
          cursor.remove();
          document.documentElement.classList.remove("premium-js");
        };
      }

      return () => {
        observer.disconnect();
        if (raf) cancelAnimationFrame(raf);
        window.removeEventListener("scroll", onScroll);
        window.removeEventListener("resize", onScroll);
        document.documentElement.classList.remove("premium-js");
      };
    }

    return () => document.documentElement.classList.remove("premium-js");
  }, []);

  return null;
}
