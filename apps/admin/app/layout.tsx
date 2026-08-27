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
import "./three-crowns-admin.css";

export const metadata: Metadata = {
  title: "Три Короны — Resort OS",
  description: "PMS, CRM, сайт и операционный центр Three Crowns",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  );
}
