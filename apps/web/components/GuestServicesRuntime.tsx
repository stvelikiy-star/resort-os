"use client";

import { useEffect } from "react";

import { GuestFactsLocale, ownerApprovedGuestFacts, TWO_GIS_REVIEWS_URL } from "../lib/ownerApprovedGuestFacts";

function localeFromLocation(): GuestFactsLocale {
  const query = new URLSearchParams(window.location.search).get("lang");
  if (query === "kg" || query === "en" || query === "ru") return query;
  const stored = window.localStorage.getItem("three-crowns-site-language");
  return stored === "kg" || stored === "en" || stored === "ru" ? stored : "ru";
}

function setText(selector: string, value: string) {
  const element = document.querySelector<HTMLElement>(selector);
  if (element) element.textContent = value;
}

function localizedInternalHref(href: string, locale: GuestFactsLocale) {
  if (locale === "ru" || !href.startsWith("/")) return href;
  const url = new URL(href, window.location.origin);
  url.searchParams.set("lang", locale);
  return `${url.pathname}${url.search}${url.hash}`;
}

function renderReviews(locale: GuestFactsLocale) {
  const facts = ownerApprovedGuestFacts[locale].reviews;
  setText(".v3-reviews .v3-section-head .eyebrow", facts.eyebrow);
  setText("#reviews-title", facts.title);
  setText(".v3-reviews .v3-section-head > p", facts.intro);

  const grid = document.querySelector<HTMLElement>(".v3-review-grid");
  if (!grid) return;
  grid.replaceChildren();
  facts.cards.forEach((card, index) => {
    const article = document.createElement("article");
    const number = document.createElement("span");
    const title = document.createElement("h3");
    const text = document.createElement("p");
    number.textContent = String(index + 1).padStart(2, "0");
    title.textContent = card.title;
    text.textContent = card.text;
    article.append(number, title, text);
    grid.append(article);
  });

  let actions = document.querySelector<HTMLElement>("[data-owner-review-actions]");
  if (!actions) {
    actions = document.createElement("div");
    actions.className = "wrap v3-hero-actions";
    actions.dataset.ownerReviewActions = "true";
    grid.insertAdjacentElement("afterend", actions);
  }
  actions.replaceChildren();
  const read = document.createElement("a");
  read.className = "button button-dark";
  read.href = TWO_GIS_REVIEWS_URL;
  read.target = "_blank";
  read.rel = "noreferrer";
  read.textContent = facts.readCta;
  const leave = document.createElement("a");
  leave.className = "button button-outline";
  leave.href = TWO_GIS_REVIEWS_URL;
  leave.target = "_blank";
  leave.rel = "noreferrer";
  leave.textContent = facts.leaveCta;
  actions.append(read, leave);
}

function renderIncluded(locale: GuestFactsLocale) {
  const fact = ownerApprovedGuestFacts[locale].included;
  const card = document.querySelector<HTMLElement>(".v3-amenity-grid article:nth-child(6)");
  if (!card) return;
  const title = card.querySelector<HTMLElement>("h3");
  const text = card.querySelector<HTMLElement>("p");
  if (title) title.textContent = fact.title;
  if (text) text.textContent = fact.text;
}

function renderServices(locale: GuestFactsLocale) {
  const facts = ownerApprovedGuestFacts[locale].services;
  setText(".v3-extra-heading .eyebrow", facts.eyebrow);
  setText(".v3-extra-heading h3", facts.title);
  setText(".v3-extra-heading > p:not(.eyebrow)", facts.intro);

  const grid = document.querySelector<HTMLElement>(".v3-extra-grid");
  if (!grid) return;
  grid.replaceChildren();

  facts.cards.forEach((card, index) => {
    const article = document.createElement("article");
    article.dataset.serviceCode = card.code;
    const number = document.createElement("span");
    const title = document.createElement("h4");
    const text = document.createElement("p");
    number.textContent = String(index + 1).padStart(2, "0");
    title.textContent = card.title;
    text.textContent = card.text;
    article.append(number, title, text);
    if (card.cta && card.href) {
      const link = document.createElement("a");
      link.className = "text-link";
      link.href = localizedInternalHref(card.href, locale);
      if (/^https?:/.test(card.href)) {
        link.target = "_blank";
        link.rel = "noreferrer";
      }
      link.textContent = `${card.cta} →`;
      article.append(link);
    }
    grid.append(article);
  });
}

function applyOwnerApprovedFacts() {
  if (window.location.pathname !== "/") return;
  const locale = localeFromLocation();
  renderReviews(locale);
  renderIncluded(locale);
  renderServices(locale);
}

function refreshOwnerApprovedFacts() {
  applyOwnerApprovedFacts();
  window.requestAnimationFrame(() => applyOwnerApprovedFacts());
}

export default function GuestServicesRuntime() {
  useEffect(() => {
    refreshOwnerApprovedFacts();
    const handleReady = () => refreshOwnerApprovedFacts();
    window.addEventListener("three-crowns:content-ready", handleReady);
    window.addEventListener("popstate", handleReady);
    return () => {
      window.removeEventListener("three-crowns:content-ready", handleReady);
      window.removeEventListener("popstate", handleReady);
    };
  }, []);
  return null;
}
