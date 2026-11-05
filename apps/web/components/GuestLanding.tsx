"use client";

import { useState } from "react";

type Locale = "ru" | "kg" | "kz" | "en";

const COPY: Record<Locale, {
  guest: string;
  instructions: string;
  support: string;
}> = {
  ru: {
    guest: "Гостевой кабинет",
    instructions: "Для входа отсканируйте QR-код в номере или откройте персональную ссылку, которую вы получили при заселении.",
    support: "Если доступ не открывается, обратитесь на ресепшен AK BERMET.",
  },
  kg: {
    guest: "Конок кабинети",
    instructions: "Кирүү үчүн бөлмөдөгү QR-кодду сканерлеңиз же каттоо учурунда алган жеке шилтемени ачыңыз.",
    support: "Эгер кирүү ачылбаса, AK BERMET кабыл алуу кызматына кайрылыңыз.",
  },
  kz: {
    guest: "Қонақ кабинеті",
    instructions: "Кіру үшін бөлмедегі QR-кодты сканерлеңіз немесе орналасу кезінде алған жеке сілтемені ашыңыз.",
    support: "Егер қолжетімділік ашылмаса, AK BERMET қабылдау бөліміне хабарласыңыз.",
  },
  en: {
    guest: "Guest area",
    instructions: "Scan the QR code in your room or open the personal link you received at check-in.",
    support: "If access does not open, please contact AK BERMET reception.",
  },
};

const LOCALES: Locale[] = ["ru", "kg", "kz", "en"];

export default function GuestLanding() {
  const [locale, setLocale] = useState<Locale>("ru");
  const copy = COPY[locale];

  return (
    <main style={{
      minHeight: "100vh",
      display: "grid",
      placeItems: "center",
      padding: "32px 20px",
      background: "radial-gradient(circle at top, #173a34 0%, #0b1c1a 46%, #07110f 100%)",
      color: "#f7f4ea",
    }}>
      <section style={{
        width: "min(720px, 100%)",
        border: "1px solid rgba(214, 184, 111, 0.34)",
        borderRadius: 28,
        padding: "clamp(28px, 6vw, 56px)",
        background: "rgba(8, 25, 22, 0.82)",
        boxShadow: "0 28px 80px rgba(0,0,0,0.34)",
        textAlign: "center",
      }}>
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 6, marginBottom: 28 }} aria-label="Language">
          {LOCALES.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setLocale(item)}
              aria-pressed={locale === item}
              style={{
                border: "1px solid rgba(214, 184, 111, 0.42)",
                borderRadius: 999,
                padding: "7px 11px",
                background: locale === item ? "#d6b86f" : "transparent",
                color: locale === item ? "#173a34" : "#f7f4ea",
                cursor: "pointer",
                fontSize: 12,
                fontWeight: 700,
                letterSpacing: "0.06em",
              }}
            >
              {item.toUpperCase()}
            </button>
          ))}
        </div>
        <div style={{ letterSpacing: "0.24em", fontSize: 13, opacity: 0.72, marginBottom: 18 }}>
          AK BERMET
        </div>
        <h1 style={{ fontSize: "clamp(38px, 8vw, 72px)", lineHeight: 0.98, margin: 0, fontWeight: 700 }}>
          MARINA SMART
        </h1>
        <p style={{ fontSize: "clamp(18px, 3vw, 24px)", margin: "18px 0 0", opacity: 0.92 }}>
          {copy.guest}
        </p>
        <div style={{ height: 1, background: "rgba(214, 184, 111, 0.32)", margin: "32px 0" }} />
        <p style={{ fontSize: 17, lineHeight: 1.7, margin: 0, opacity: 0.86 }}>
          {copy.instructions}
        </p>
        <p style={{ fontSize: 15, lineHeight: 1.6, margin: "18px 0 0", opacity: 0.64 }}>
          {copy.support}
        </p>
      </section>
    </main>
  );
}
