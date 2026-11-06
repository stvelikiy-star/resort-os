"""Safe owner-published customer homepage. No legacy resort content or media fallbacks."""
from __future__ import annotations

import html
import os
import re
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from .customer_site_contract import validate_customer_site_content
from .site_content import CUSTOMER_SITE_SAFE_MODE, get_property_id, load_row, validate_locale

router = APIRouter(tags=["customer-site"])
LANG = {
    "ru": {"contact": "Связаться с гостиницей", "call": "Позвонить", "location": "Адрес", "home": "Главная", "whatsapp": "Написать в WhatsApp"},
    "kg": {"contact": "Мейманкана менен байланышуу", "call": "Чалуу", "location": "Дарек", "home": "Башкы бет", "whatsapp": "WhatsApp аркылуу жазуу"},
    "en": {"contact": "Contact the hotel", "call": "Call", "location": "Address", "home": "Home", "whatsapp": "WhatsApp"},
}
CSS = """
:root{font-family:Inter,ui-sans-serif,system-ui,sans-serif;color:#1c2840;background:#f8fafc}
*{box-sizing:border-box}body{margin:0}a{color:inherit;text-decoration:none}
.shell{width:min(1100px,calc(100% - 40px));margin:auto}
header{display:flex;align-items:center;justify-content:space-between;gap:18px;padding:28px 0}
.brand{letter-spacing:.17em;text-transform:uppercase;font-size:12px;font-weight:800}
.languages{display:flex;gap:12px}.languages a{font-size:13px;color:#526179}
.hero{background:linear-gradient(130deg,#122544,#21446b 57%,#315e76);color:white;border-radius:28px;padding:clamp(38px,7vw,100px) clamp(26px,6vw,88px);margin:22px 0 40px}
.label{font-size:12px;letter-spacing:.2em;text-transform:uppercase;opacity:.72}
h1{max-width:800px;font-size:clamp(38px,6.5vw,80px);line-height:1.08;letter-spacing:-.04em;margin:22px 0}
.hero p{max-width:680px;font-size:clamp(17px,2vw,22px);line-height:1.65;opacity:.9}
.details{padding:20px 0 90px;display:grid;grid-template-columns:1fr 1fr;gap:24px}
.card{background:white;border:1px solid #dce5ee;border-radius:22px;padding:32px;overflow-wrap:anywhere}
.card h2{margin-top:0;font-size:24px}.card p{line-height:1.8;color:#41516a}
.buttons{display:flex;flex-wrap:wrap;gap:12px;margin-top:24px}
.button{display:inline-block;padding:14px 20px;background:#204966;color:white;border-radius:12px;font-weight:700}
.button.secondary{background:#eaf0f5;color:#204966}
footer{font-size:12px;color:#667892;padding:0 0 35px}
@media(max-width:680px){header{align-items:flex-start}.details{grid-template-columns:1fr}.card{padding:24px}}
"""
UNPUBLISHED = {
    "ru": ("Сайт гостиницы готовится к публикации", "Контакты, фотографии и информация ещё не опубликованы."),
    "kg": ("Мейманкананын сайты жарыялоого даярдалууда", "Байланыш маалыматтары, сүрөттөр жана маалымат азырынча жарыялана элек."),
    "en": ("This hotel website is being prepared", "Contact details, photographs and information have not been published yet."),
}


def _response(body: str, *, published: bool = False, canonical: str = "") -> HTMLResponse:
    robots = "index, follow" if published and canonical else "noindex, nofollow"
    return HTMLResponse(
        body, status_code=200,
        headers={
            "Cache-Control": "private, no-store" if not published else "public, max-age=60",
            "X-Robots-Tag": robots,
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
        },
    )


def _canonical(locale: str) -> str:
    url = os.environ.get("GUEST_OS_PUBLIC_BASE_URL", "")
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname or parts.hostname.endswith((".invalid", ".test", ".localhost")):
        return ""
    if parts.username or parts.password or parts.port or parts.path not in ("", "/"):
        return ""
    host = parts.hostname
    if not re.fullmatch(r"[a-z0-9.-]{4,253}", host):
        return ""
    return f"https://{host}/?locale={locale}"


def render_customer_site(locale: str, content: dict | None) -> HTMLResponse:
    if locale not in LANG:
        raise HTTPException(404, detail="Unsupported locale")
    e = lambda text: html.escape(text, quote=True)
    navigation = "".join(
        f'<a href="/?locale={code}" lang="{code}">{label}</a>'
        for code, label in (("ru", "РУС"), ("kg", "КЫР"), ("en", "ENG"))
    )
    if content is None:
        title, message = UNPUBLISHED[locale]
        result = (
            f'<!doctype html><html lang="{locale}"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="robots" content="noindex,nofollow">'
            f'<title>MARINA SMART · {e(title)}</title><style>{CSS}</style></head><body>'
            f'<div class="shell"><header><div class="brand">MARINA SMART</div><nav class="languages">{navigation}</nav></header>'
            f'<main class="hero"><p class="label">MARINA SMART</p><h1>{e(title)}</h1><p>{e(message)}</p></main></div></body></html>'
        )
        return _response(result)

    data = validate_customer_site_content(locale, content)
    title = data["hero"]["title"]
    subtitle = data["hero"]["subtitle"]
    seo_title = data["seo"]["title"]
    seo_description = data["seo"]["description"]
    contacts = data["contacts"]
    labels = LANG[locale]
    canonical = _canonical(locale)
    canonical_tag = f'<link rel="canonical" href="{e(canonical)}">' if canonical else ""
    number = re.sub(r"[^0-9+]", "", contacts["phone"])
    whatsapp = re.sub(r"\D", "", contacts["whatsapp"])
    result = (
        f'<!doctype html><html lang="{locale}"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<meta name="description" content="{e(seo_description)}">'
        f'<meta name="robots" content="{"index,follow" if canonical else "noindex,nofollow"}">'
        f'<meta property="og:title" content="{e(seo_title)}">'
        f'<meta property="og:description" content="{e(seo_description)}">'
        f'{canonical_tag}<title>{e(seo_title)}</title><style>{CSS}</style></head><body>'
        f'<div class="shell"><header><div class="brand">{e(title)}</div><nav class="languages">{navigation}</nav></header>'
        f'<main><section class="hero"><p class="label">{e(labels["home"])}</p>'
        f'<h1>{e(title)}</h1><p>{e(subtitle)}</p></section><section class="details">'
        f'<div class="card"><h2>{e(labels["contact"])}</h2>'
        f'<p>{e(contacts["phone"])}<br>{e(contacts["email"])}</p>'
        f'<div class="buttons"><a class="button" href="tel:{e(number)}">{e(labels["call"])}</a>'
        f'<a class="button secondary" href="https://wa.me/{e(whatsapp)}" rel="noopener noreferrer">{e(labels["whatsapp"])}</a></div></div>'
        f'<div class="card"><h2>{e(labels["location"])}</h2><p>{e(contacts["address"])}</p></div>'
        f'</section></main><footer>MARINA SMART</footer></div></body></html>'
    )
    return _response(result, published=True, canonical=canonical)


@router.get("/api/v1/site/customer-page")
async def customer_page(request: Request, locale: str = "ru"):
    if not CUSTOMER_SITE_SAFE_MODE:
        raise HTTPException(404, detail="Customer page is disabled")
    locale = validate_locale(locale)
    async with request.app.state.db.acquire() as conn:
        property_id = await get_property_id(conn)
        row = await load_row(conn, property_id, locale)
    if not row or not row["publishedJson"] or not row["publishedVersion"]:
        return render_customer_site(locale, None)
    return render_customer_site(locale, row["publishedJson"])
