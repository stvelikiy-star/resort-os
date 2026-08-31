import type { Metadata } from "next";
import "./globals.css";
import "./auth.css";
import "./admin-nav-polish.css";
import "./nfc.css";
import "./finance.css";
import "./hotel-finance.css";
import "./reports.css";
import "./owner-intelligence.css";
import "./owner-control-v2.css";
import "./owner-executive.css";
import "./growth-control.css";
import "./guest-history.css";
import "./dashboard.css";
import "./reception.css";
import "./inbox.css";
import "./staff.css";
import "./room-detail.css";
import "./chessboard.css";
import "./chessboard-lifecycle.css";
import "./chessboard-payment.css";
import "./chessboard-v2.css";
import "./chessboard-v3.css";
import "./chessboard-v3-fixes.css";
import "./chessboard-v4.css";
import "./chessboard-v5.css";
import "./chessboard-v6.css";
import "./chessboard-v6-hover.css";
import "./chessboard-v7.css";
import "./chessboard-v8.css";
import "./chessboard-v9.css";
import "./chessboard-v9-bulk.css";
import "./three-crowns-admin.css";
import "./mobile-hardening.css";
import "./my-stay/my-stay-admin.css";

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
