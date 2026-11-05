import { NextRequest, NextResponse } from "next/server";

// Customer deployments must never serve the legacy Three Crowns fallback.
// This temporary, deliberately fail-closed gate remains until a per-hotel
// published-site contract and cross-customer media checks are accepted.
const UNPUBLISHED_HTML = `<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="robots" content="noindex,nofollow">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MARINA SMART · Сайт готовится к публикации</title></head>
<body style="font-family:system-ui,sans-serif;max-width:680px;margin:12vh auto;padding:24px;color:#172036;background:#fff">
<main><h1>Сайт гостиницы готовится к публикации</h1>
<p>Информация, фотографии и контакты этой гостиницы ещё не опубликованы.</p>
<p lang="ky">Мейманкананын сайты жарыялоого даярдалууда.</p>
<p lang="en">This hotel's website is not published yet.</p></main></body></html>`;

export function middleware(request: NextRequest) {
  if (process.env.MARINA_CUSTOMER_SITE_GUARD !== "true") {
    return NextResponse.next();
  }
  const acceptsHtml = request.headers.get("accept")?.includes("text/html") ?? false;
  const safePage = request.method === "GET" && acceptsHtml;
  return new NextResponse(safePage ? UNPUBLISHED_HTML : "Not published", {
    status: safePage ? 200 : 503,
    headers: {
      "Content-Type": safePage ? "text/html; charset=utf-8" : "text/plain; charset=utf-8",
      "Cache-Control": "private, no-store",
      "X-Robots-Tag": "noindex, nofollow",
      "X-Content-Type-Options": "nosniff",
      "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
    },
  });
}

export const config = { matcher: "/:path*" };
