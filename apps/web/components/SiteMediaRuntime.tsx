"use client";

import { useEffect } from "react";

type MediaSlot = {
  slot: string;
  asset_id: string;
  filename: string;
  mime_type: string;
  byte_size: number;
  alt_text?: string | null;
  url: string;
  published_at?: string | null;
};

type MediaPayload = { items: MediaSlot[]; slots: Record<string, MediaSlot> };

function setImage(image: HTMLImageElement | null, media?: MediaSlot) {
  if (!image || !media?.url) return;
  image.removeAttribute("srcset");
  image.removeAttribute("sizes");
  image.src = media.url;
  if (media.alt_text) image.alt = media.alt_text;
}

function setFeatureVisual(selector: string, media?: MediaSlot, withShade = false) {
  if (!media?.url) return;
  const root = document.querySelector<HTMLElement>(selector);
  if (!root) return;
  const video = root.querySelector<HTMLVideoElement>("video");
  if (video) video.poster = media.url;
  root.style.backgroundImage = withShade
    ? `linear-gradient(rgba(8,17,38,.20),rgba(8,17,38,.60)),url("${media.url}")`
    : `url("${media.url}")`;
  root.style.backgroundSize = "cover";
  root.style.backgroundPosition = "center";
}

function applyMedia(slots: Record<string, MediaSlot>) {
  setFeatureVisual(".v3-hero-media", slots.HERO);
  setFeatureVisual(".v3-territory-film", slots.TERRITORY);
  setFeatureVisual(".v3-lake-film", slots.WATER);

  const conference = slots.CONFERENCE;
  if (conference?.url) {
    const visual = document.querySelector<HTMLElement>(".owner-conference-visual");
    if (visual) {
      visual.style.backgroundImage = `linear-gradient(rgba(8,17,38,.32),rgba(8,17,38,.72)),url("${conference.url}")`;
      visual.style.backgroundSize = "cover";
      visual.style.backgroundPosition = "center";
    }
  }

  const groups = slots.GROUPS;
  if (groups?.url) {
    const visual = document.querySelector<HTMLImageElement>(".v3-groups-media img");
    setImage(visual, groups);
    const fallback = document.querySelector<HTMLElement>(".v3-groups-media");
    if (fallback) {
      fallback.style.backgroundImage = `url("${groups.url}")`;
      fallback.style.backgroundSize = "cover";
      fallback.style.backgroundPosition = "center";
    }
  }

  const gallery = Array.from(document.querySelectorAll<HTMLImageElement>(".gallery-grid .gallery-item img"));
  gallery.forEach((image, index) => setImage(image, slots[`GALLERY_${index + 1}`]));

  const advantages = Array.from(document.querySelectorAll<HTMLImageElement>(".v3-advantage-track .v3-advantage-card .v3-advantage-image img"));
  advantages.forEach((image, index) => setImage(image, slots[`ADVANTAGE_${(index % 6) + 1}`]));

  const rooms = Array.from(document.querySelectorAll<HTMLImageElement>(".v3-room-grid .v3-room-card .v3-room-card-photo img"));
  rooms.forEach((image, index) => setImage(image, slots[`ROOM_${String(index + 1).padStart(2, "0")}`]));
}

export default function SiteMediaRuntime() {
  useEffect(() => {
    const controller = new AbortController();
    let payload: MediaPayload | null = null;
    let scheduled = 0;

    const apply = () => {
      if (payload?.slots) applyMedia(payload.slots);
    };
    const scheduleApply = () => {
      window.clearTimeout(scheduled);
      scheduled = window.setTimeout(apply, 30);
    };

    fetch("/core/api/v1/site/media-config", { cache: "no-store", signal: controller.signal })
      .then(async (response) => response.ok ? (await response.json()) as MediaPayload : null)
      .then((next) => {
        if (!next) return;
        payload = next;
        apply();
        window.setTimeout(apply, 250);
      })
      .catch(() => undefined);

    window.addEventListener("three-crowns:content-ready", scheduleApply);
    const observer = new MutationObserver((mutations) => {
      if (!payload) return;
      if (mutations.some((mutation) => mutation.addedNodes.length > 0)) scheduleApply();
    });
    observer.observe(document.body, { childList: true, subtree: true });

    return () => {
      controller.abort();
      window.removeEventListener("three-crowns:content-ready", scheduleApply);
      observer.disconnect();
      window.clearTimeout(scheduled);
    };
  }, []);
  return null;
}
