"""Client production Web must never serve another property's legacy site."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CustomerWebPublicationGuard(unittest.TestCase):
    def test_production_uses_dedicated_unpublished_web_not_legacy_next(self):
        source = (ROOT / "compose.marina-production.yaml").read_text()
        web = source.split("\n  web:\n", 1)[1].split("\n  admin:\n", 1)[0]
        self.assertIn("image: caddy:2.11.4-alpine", web)
        self.assertIn("customer-unpublished.Caddyfile", web)
        self.assertIn("customer-unpublished.html", web)
        self.assertNotIn("apps/web/Dockerfile", web)
        self.assertNotIn("marina-\u0024{MARINA_INSTANCE_SLUG", web)
        self.assertNotIn("ports:", web)

    def test_unpublished_gateway_blocks_non_html_and_assets(self):
        source = (ROOT / "deploy/marina/customer-unpublished.Caddyfile").read_text()
        self.assertIn("header Accept *text/html*", source)
        self.assertIn('respond "Not published" 503', source)
        self.assertIn('X-Robots-Tag "noindex, nofollow"', source)
        self.assertIn('Cache-Control "private, no-store"', source)
        self.assertIn("Content-Security-Policy", source)
        self.assertIn("path /healthz", source)

    def test_neutral_page_has_no_foreign_hotel_data(self):
        source = (ROOT / "deploy/marina/customer-unpublished.html").read_text()
        self.assertIn("MARINA SMART", source)
        self.assertIn('lang="ru"', source)
        self.assertIn('lang="ky"', source)
        self.assertIn('lang="en"', source)
        for old in ("Три Короны", "3korony", "three-crowns", "996558085002", "3koronykg", "https://", "wa.me"):
            self.assertNotIn(old, source)

    def test_live_customer_caddy_still_targets_private_web(self):
        source = (ROOT / "deploy/marina/Caddyfile").read_text()
        self.assertIn("reverse_proxy web:3000", source)


if __name__ == "__main__":
    unittest.main()
