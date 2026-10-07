import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AK BERMET — MARINA SMART · гостевой кабинет",
  description: "Вход в цифровой гостевой кабинет AK BERMET на платформе MARINA SMART.",
  robots: { index: false, follow: false, noarchive: true, nosnippet: true },
};

export default function GuestWebHome() {
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
        <div style={{ letterSpacing: "0.24em", fontSize: 13, opacity: 0.72, marginBottom: 18 }}>
          AK BERMET
        </div>
        <h1 style={{ fontSize: "clamp(38px, 8vw, 72px)", lineHeight: 0.98, margin: 0, fontWeight: 700 }}>
          MARINA SMART
        </h1>
        <p style={{ fontSize: "clamp(18px, 3vw, 24px)", margin: "18px 0 0", opacity: 0.92 }}>
          Гостевой кабинет
        </p>
        <div style={{ height: 1, background: "rgba(214, 184, 111, 0.32)", margin: "32px 0" }} />
        <p style={{ fontSize: 17, lineHeight: 1.7, margin: 0, opacity: 0.86 }}>
          Для входа отсканируйте QR-код в номере или откройте персональную ссылку,
          которую вы получили при заселении.
        </p>
        <p style={{ fontSize: 15, lineHeight: 1.6, margin: "18px 0 0", opacity: 0.64 }}>
          Если доступ не открывается, обратитесь на ресепшен AK BERMET.
        </p>
        <div style={{ marginTop: 30, fontSize: 13, letterSpacing: "0.08em", opacity: 0.5 }}>
          RU · KG · KZ · EN
        </div>
      </section>
    </main>
  );
}
