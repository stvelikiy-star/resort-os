"""Single-customer public Web cannot inherit any older property's content."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CustomerWebPublicationGuard(unittest.TestCase):
    def test_new_customer_production_compose_is_always_gated(self):
        source = (ROOT / "compose.marina-production.yaml").read_text()
        web = source.split("\n  web:\n", 1)[1].split("\n  admin:\n", 1)[0]
        self.assertIn('MARINA_CUSTOMER_SITE_GUARD: "true"', web)

    def test_unpublished_page_never_renders_legacy_children(self):
        source = (ROOT / "apps/web/middleware.ts").read_text()
        self.assertIn('process.env.MARINA_CUSTOMER_SITE_GUARD !== "true"', source)
        self.assertIn('return NextResponse.next()', source)
        self.assertIn('X-Robots-Tag', source)
        self.assertIn('noindex, nofollow', source)
        self.assertIn('no-store', source)
        self.assertIn('matcher: "/:path*"', source)
        self.assertNotIn('3korony.com', source)
        self.assertNotIn('Три Короны', source)
        self.assertNotIn('996558085002', source)

    def test_all_non_html_paths_fail_closed(self):
        source = (ROOT / "apps/web/middleware.ts").read_text()
        self.assertIn('request.method === "GET" && acceptsHtml', source)
        self.assertIn('status: safePage ? 200 : 503', source)


if __name__ == "__main__":
    unittest.main()
