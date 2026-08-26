import type { Metadata } from "next";
import "./globals.css";
import "./auth.css";
import "./admin-nav-polish.css";
import "./nfc.css";
import "./finance.css";
import "./hotel-finance.css";
import "./dashboard.css";
import "./reception.css";
import "./inbox.css";
import "./staff.css";
import "./room-detail.css";
import "./chessboard.css";
import "./chessboard-lifecycle.css";
import "./chessboard-payment.css";
import "./chessboard-v2.css";

export const metadata: Metadata = {
  title: "Три Короны — PMS",
  description: "Resort OS control center for Three Crowns",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  );
}
