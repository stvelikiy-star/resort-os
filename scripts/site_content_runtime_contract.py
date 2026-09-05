#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "apps/web/components/SiteContentRuntime.tsx"
I18N = ROOT / "apps/web/components/PublicUiI18nRuntime.tsx"


def require(text: str, *needles: str) -> None:
    missing = [needle for needle in needles if needle not in text]
    if missing:
        raise AssertionError(f"missing site-content runtime contract markers: {missing}")


def main() -> int:
    runtime = RUNTIME.read_text(encoding="utf-8")
    i18n = I18N.read_text(encoding="utf-8")

    require(
        runtime,
        'fallbackSiteContent, type SiteContent, type SiteLocale',
        'commitContent(fallbackSiteContent[locale], locale);',
        'if (payload?.content) commitContent(payload.content, locale);',
        'function commitContent(content: SiteContent, locale: SiteLocale)',
        'applyContent(content, locale);\n  dispatchReady(locale);',
        'queueMicrotask(() => applyContent(content, locale));',
        'text(".v3-advantages .v3-section-head > p", content.advantages?.intro);',
        "help.textContent = `${locale === \"en\" ? \"Call\" : locale === \"kg\" ? \"Чалуу\" : \"Позвонить\"} · ${phone}`",
    )

    # The generic i18n layer is allowed to localize non-CMS UI and currently
    # touches some of the same DOM nodes. The CMS runtime must therefore make a
    # final microtask pass after content-ready listeners so DB/fallback content wins.
    require(
        i18n,
        'window.addEventListener("three-crowns:content-ready", run);',
        'setText(".v3-advantages .v3-section-head > p", c.advantageIntro);',
        'document.querySelectorAll<HTMLElement>(".v3-help-actions a")',
    )

    apply_start = runtime.index("function applyContent")
    commit_start = runtime.index("function commitContent")
    apply_body = runtime[apply_start:commit_start]
    if "dispatchReady(locale)" in apply_body:
        raise AssertionError("applyContent must not dispatch before CMS ownership is finalized")

    print("SITE_CONTENT_RUNTIME_CONTRACT_OK: locale fallback is explicit and CMS-owned selectors win after i18n listeners")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
