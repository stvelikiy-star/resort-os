"use client";

import { useEffect } from "react";

const REVEAL_SELECTOR = [
  ".display-title",
  ".v3-hero-content > *",
  ".v3-section-head > p",
  ".v3-booking-intro-copy",
  ".v3-room-card",
  ".v3-advantage-card",
  ".v3-territory-route article",
  ".v3-territory-photo-strip figure",
  ".v3-amenity-grid article",
  ".v3-review-visual",
  ".v3-review-grid article",
  ".v3-extra-grid article",
  ".v3-group-grid article",
  ".v3-contact-actions a",
  ".v3-map-card",
  ".v3-arrival-card",
  ".room-catalog-card",
  ".room-detail-copy > *",
  ".room-rate-card",
  ".room-detail-gallery .gallery-item",
].join(",");

const SPOTLIGHT_SELECTOR = [
  ".v3-room-card",
  ".v3-advantage-card",
  ".v3-amenity-grid article",
  ".v3-review-grid article",
  ".v3-extra-grid article",
  ".v3-group-grid article",
  ".room-catalog-card",
].join(",");

const PARALLAX_SELECTOR = [
  ".v3-hero-media",
  ".v3-territory-film",
  ".v3-lake-film",
  ".v3-groups-media",
  ".rooms-hero-media",
  ".room-detail-hero-media",
].join(",");

export default function PremiumMotion() {
  useEffect(() => {
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const finePointer = window.matchMedia("(pointer: fine) and (hover: hover)").matches;
    const root = document.documentElement;
    const cleanup: Array<() => void> = [];
    let revealObserver: IntersectionObserver | null = null;
    let parallaxTargets: HTMLElement[] = [];
    let raf = 0;

    root.classList.add("premium-js");
    if (finePointer && !reduceMotion) root.classList.add("premium-cursor-enabled");

    const progress = document.createElement("div");
    progress.className = "premium-scroll-progress";
    progress.setAttribute("aria-hidden", "true");
    document.body.appendChild(progress);
    cleanup.push(() => progress.remove());

    const refreshParallaxTargets = () => {
      parallaxTargets = Array.from(document.querySelectorAll<HTMLElement>(PARALLAX_SELECTOR));
    };

    const updateFrame = () => {
      raf = 0;
      const doc = document.documentElement;
      const maxScroll = Math.max(1, doc.scrollHeight - window.innerHeight);
      progress.style.setProperty("--scroll-progress", String(Math.max(0, Math.min(1, window.scrollY / maxScroll))));

      if (!reduceMotion) {
        const viewport = window.innerHeight || 1;
        parallaxTargets.forEach((node) => {
          const rect = node.getBoundingClientRect();
          if (rect.bottom < -120 || rect.top > viewport + 120) return;
          const center = rect.top + rect.height / 2;
          const normalized = Math.max(-1, Math.min(1, (center - viewport / 2) / viewport));
          const distance = node.matches(".v3-hero-media,.rooms-hero-media,.room-detail-hero-media") ? -22 : -12;
          node.style.setProperty("--premium-parallax", `${normalized * distance}px`);
        });
      }
    };

    const requestFrame = () => {
      if (!raf) raf = window.requestAnimationFrame(updateFrame);
    };

    refreshParallaxTargets();
    updateFrame();
    window.addEventListener("scroll", requestFrame, { passive: true });
    window.addEventListener("resize", requestFrame);
    cleanup.push(() => {
      window.removeEventListener("scroll", requestFrame);
      window.removeEventListener("resize", requestFrame);
      if (raf) cancelAnimationFrame(raf);
    });

    if (!reduceMotion) {
      revealObserver = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (!entry.isIntersecting) return;
            (entry.target as HTMLElement).classList.add("is-revealed");
            revealObserver?.unobserve(entry.target);
          });
        },
        { rootMargin: "0px 0px -9% 0px", threshold: 0.08 },
      );
    }

    const registerRevealTargets = () => {
      const targets = Array.from(document.querySelectorAll<HTMLElement>(REVEAL_SELECTOR));
      targets.forEach((node, index) => {
        if (node.dataset.premiumRevealBound === "true") return;
        node.dataset.premiumRevealBound = "true";
        node.style.setProperty("--reveal-delay", `${Math.min(index % 6, 5) * 55}ms`);
        if (reduceMotion) {
          node.classList.add("is-revealed");
        } else {
          node.classList.add("premium-reveal");
          revealObserver?.observe(node);
        }
      });
    };

    registerRevealTargets();
    cleanup.push(() => revealObserver?.disconnect());

    const videoBindings: Array<() => void> = [];
    const bindVideo = (video: HTMLVideoElement, host: HTMLElement, hero = false) => {
      if (video.dataset.premiumControlBound === "true") return;
      video.dataset.premiumControlBound = "true";
      host.style.position = "relative";

      const button = document.createElement("button");
      button.type = "button";
      button.className = `premium-video-toggle${hero ? " premium-video-toggle-hero" : ""}`;
      button.dataset.state = video.paused ? "paused" : "playing";

      const update = () => {
        const playing = !video.paused && !video.ended;
        button.dataset.state = playing ? "playing" : "paused";
        button.setAttribute("aria-label", playing ? "Поставить видео на паузу" : "Воспроизвести видео");
        button.setAttribute("title", playing ? "Пауза" : "Воспроизвести");
      };

      const toggle = async () => {
        if (video.paused || video.ended) {
          try {
            await video.play();
          } catch {
            // Browser autoplay policy may still block play; media events keep state authoritative.
          }
        } else {
          video.pause();
        }
        update();
      };

      button.addEventListener("click", toggle);
      video.addEventListener("play", update);
      video.addEventListener("pause", update);
      video.addEventListener("ended", update);
      host.appendChild(button);

      if (reduceMotion) video.pause();
      update();

      videoBindings.push(() => {
        button.removeEventListener("click", toggle);
        video.removeEventListener("play", update);
        video.removeEventListener("pause", update);
        video.removeEventListener("ended", update);
        button.remove();
        delete video.dataset.premiumControlBound;
      });
    };

    const registerVideoControls = () => {
      const heroVideo = document.querySelector<HTMLVideoElement>(".v3-hero-media video");
      const heroHost = heroVideo?.closest<HTMLElement>(".v3-hero");
      if (heroVideo && heroHost) bindVideo(heroVideo, heroHost, true);

      const territoryVideo = document.querySelector<HTMLVideoElement>(".v3-territory-film video");
      const territoryHost = territoryVideo?.closest<HTMLElement>(".v3-territory-film");
      if (territoryVideo && territoryHost) bindVideo(territoryVideo, territoryHost);

      const lakeVideo = document.querySelector<HTMLVideoElement>(".v3-lake-film video");
      const lakeHost = lakeVideo?.closest<HTMLElement>(".v3-lake-film");
      if (lakeVideo && lakeHost) bindVideo(lakeVideo, lakeHost);
    };

    registerVideoControls();
    cleanup.push(() => videoBindings.splice(0).forEach((dispose) => dispose()));

    const handleContentReady = () => {
      registerRevealTargets();
      registerVideoControls();
      refreshParallaxTargets();
      requestFrame();
    };
    window.addEventListener("three-crowns:content-ready", handleContentReady);
    cleanup.push(() => window.removeEventListener("three-crowns:content-ready", handleContentReady));

    const onAnchorClick = (event: MouseEvent) => {
      if (reduceMotion) return;
      const anchor = (event.target as Element | null)?.closest<HTMLAnchorElement>("a[href*='#']");
      if (!anchor) return;
      const url = new URL(anchor.href, window.location.href);
      if (!url.hash || url.pathname !== window.location.pathname || url.origin !== window.location.origin) return;
      const target = document.querySelector<HTMLElement>(url.hash);
      if (!target) return;
      event.preventDefault();
      target.scrollIntoView({ behavior: "smooth", block: "start" });
      history.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
    };
    document.addEventListener("click", onAnchorClick);
    cleanup.push(() => document.removeEventListener("click", onAnchorClick));

    const onPointerMove = (event: PointerEvent) => {
      const card = (event.target as Element | null)?.closest<HTMLElement>(SPOTLIGHT_SELECTOR);
      if (!card) return;
      const rect = card.getBoundingClientRect();
      card.style.setProperty("--spot-x", `${event.clientX - rect.left}px`);
      card.style.setProperty("--spot-y", `${event.clientY - rect.top}px`);
    };
    if (finePointer && !reduceMotion) {
      document.addEventListener("pointermove", onPointerMove, { passive: true });
      cleanup.push(() => document.removeEventListener("pointermove", onPointerMove));
    }

    if (finePointer && !reduceMotion) {
      const cursor = document.createElement("div");
      cursor.className = "premium-cursor";
      cursor.setAttribute("aria-hidden", "true");
      document.body.appendChild(cursor);

      const interactive = "a, button, input, select, .v3-room-card, .v3-advantage-card, .room-catalog-card";
      const videoInteractive = ".v3-hero, .v3-territory-film, .v3-lake-film";
      let cursorRaf = 0;
      let x = -100;
      let y = -100;
      const renderCursor = () => {
        cursorRaf = 0;
        cursor.style.transform = `translate3d(${x}px,${y}px,0)`;
      };
      const move = (event: MouseEvent) => {
        x = event.clientX;
        y = event.clientY;
        if (!cursorRaf) cursorRaf = requestAnimationFrame(renderCursor);
      };
      const over = (event: MouseEvent) => {
        const target = event.target as Element | null;
        cursor.classList.toggle("is-active", Boolean(target?.closest(interactive)));
        cursor.classList.toggle("is-video", Boolean(target?.closest(videoInteractive)));
      };
      window.addEventListener("mousemove", move, { passive: true });
      window.addEventListener("mouseover", over, { passive: true });
      cleanup.push(() => {
        window.removeEventListener("mousemove", move);
        window.removeEventListener("mouseover", over);
        if (cursorRaf) cancelAnimationFrame(cursorRaf);
        cursor.remove();
      });
    }

    return () => {
      cleanup.reverse().forEach((dispose) => dispose());
      root.classList.remove("premium-js", "premium-cursor-enabled");
    };
  }, []);

  return null;
}
