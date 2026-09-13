"use client";

import { useEffect, useState } from "react";

type Locale = "ru" | "kg" | "en";
type NavPhrase = { ru: string; kg: string; en: string };

const STORAGE_KEY = "three-crowns-admin-locale";

export const ADMIN_NAV_PHRASES: NavPhrase[] = [
  { ru: "Главная", kg: "Башкы", en: "Home" },
  { ru: "Супершахматка", kg: "Супершахматка", en: "Super Grid" },
  { ru: "Цены / Сезоны", kg: "Баалар / Мезгилдер", en: "Rates / Seasons" },
  { ru: "Групповая бронь", kg: "Топтук брондоо", en: "Group Booking" },
  { ru: "CRM / Заявки", kg: "CRM / Өтүнмөлөр", en: "CRM / Requests" },
  { ru: "Маркетинг", kg: "Маркетинг", en: "Marketing" },
  { ru: "Ресепшен / Брони", kg: "Ресепшен / Брондор", en: "Reception / Reservations" },
  { ru: "Сервис гостя", kg: "Конок сервиси", en: "Guest Services" },
  { ru: "Питание / Ресторан", kg: "Тамактануу / Ресторан", en: "Dining / Restaurant" },
  { ru: "Настройки услуг", kg: "Кызмат жөндөөлөрү", en: "Service Settings" },
  { ru: "Гости / История", kg: "Коноктор / Тарых", en: "Guests / History" },
  { ru: "Офферы гостю", kg: "Конокко сунуштар", en: "Guest Offers" },
  { ru: "QR номеров", kg: "Бөлмө QR", en: "Room QR" },
  { ru: "QR зон", kg: "Аймак QR", en: "Zone QR" },
  { ru: "Рост / Отзывы", kg: "Өсүү / Пикирлер", en: "Growth / Reviews" },
  { ru: "Финансы", kg: "Каржы", en: "Finance" },
  { ru: "Отчёты / Аналитика", kg: "Отчёттор / Аналитика", en: "Reports / Analytics" },
  { ru: "Сайт / Контент", kg: "Сайт / Контент", en: "Site / Content" },
  { ru: "Уборка / Ремонт", kg: "Тазалоо / Оңдоо", en: "Housekeeping / Maintenance" },
  { ru: "Персонал", kg: "Кызматкерлер", en: "Staff" },
  { ru: "Сообщения", kg: "Билдирүүлөр", en: "Messages" },
  { ru: "Выйти", kg: "Чыгуу", en: "Sign out" },
];

const byAnyLabel = new Map<string, NavPhrase>();
for (const phrase of ADMIN_NAV_PHRASES) {
  byAnyLabel.set(phrase.ru, phrase);
  byAnyLabel.set(phrase.kg, phrase);
  byAnyLabel.set(phrase.en, phrase);
}

function storedLocale(): Locale {
  const value = window.localStorage.getItem(STORAGE_KEY);
  return value === "kg" || value === "en" || value === "ru" ? value : "ru";
}

function translateNavigation(locale: Locale) {
  document.querySelectorAll<HTMLButtonElement>(".admin-tabs button, .logout-button").forEach((button) => {
    const current = (button.textContent || "").trim();
    const phrase = byAnyLabel.get(current);
    if (phrase && current !== phrase[locale]) button.textContent = phrase[locale];
  });
}

export default function AdminNavLocaleCoverage() {
  const [locale, setLocale] = useState<Locale>("ru");

  useEffect(() => { setLocale(storedLocale()); }, []);

  useEffect(() => {
    translateNavigation(locale);
    const observer = new MutationObserver(() => translateNavigation(locale));
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, [locale]);

  useEffect(() => {
    const onClick = (event: MouseEvent) => {
      const button = (event.target as Element | null)?.closest<HTMLButtonElement>(".admin-locale-switcher button");
      if (!button) return;
      const next = (button.textContent || "").trim().toLowerCase();
      if (next === "ru" || next === "kg" || next === "en") setLocale(next);
    };
    document.addEventListener("click", onClick, true);
    return () => document.removeEventListener("click", onClick, true);
  }, []);

  return null;
}
