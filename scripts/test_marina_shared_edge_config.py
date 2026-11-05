#!/usr/bin/env python3
"""Pure render/negative contract for one edge and isolated hotel gateways."""
import unittest

from marina_shared_edge_config import render, validate_shared_edge
from test_verify_marina_customer_isolation import hotel


class SharedEdgeContract(unittest.TestCase):
    def config(self):
        a, b = hotel(1), hotel(2)
        b["MARINA_DEPLOYMENT_HOST_ID"] = a["MARINA_DEPLOYMENT_HOST_ID"]
        return a, b

    def test_two_hotels_have_one_edge_and_two_distinct_networks(self):
        a, b = self.config()
        caddy, compose = render([a, b])
        self.assertIn("80:80", compose)
        self.assertEqual(compose.count("443:443"), 2)
        for env in (a, b):
            self.assertIn(env["PUBLIC_HOST"], caddy)
            self.assertIn(env["API_HOST"], caddy)
            self.assertIn("marina_" + env["COMPOSE_PROJECT_NAME"] + "_gateway:80", caddy)
            self.assertIn("name: marina_ingress_" + env["COMPOSE_PROJECT_NAME"], compose)
        self.assertNotIn("postgres", caddy.lower())
        self.assertNotIn("postgres", compose.lower())

    def test_rejects_cross_customer_secrets_storage_and_domains(self):
        a, b = self.config()
        b["POSTGRES_PASSWORD"] = a["POSTGRES_PASSWORD"]
        b["BACKUP_DIR"] = a["HOST_DATA_DIR"] + "/backups"
        b["PUBLIC_HOST"] = a["PUBLIC_HOST"]
        result = " ".join(validate_shared_edge([a, b]))
        for part in ("POSTGRES_PASSWORD", "HOST_DATA_DIR and BACKUP_DIR", "hostnames"):
            self.assertIn(part, result)

    def test_same_host_is_required_only_in_shared_edge_mode(self):
        a, b = hotel(1), hotel(2)
        self.assertIn("SAME actual Ubuntu host", " ".join(validate_shared_edge([a, b])))

    def test_www_redirect_cannot_shadow_other_customer_admin_route(self):
        a, b = self.config()
        b["ADMIN_HOST"] = "www." + a["PUBLIC_HOST"]
        self.assertIn("www aliases collide", " ".join(validate_shared_edge([a, b])))

    def test_foreign_customer_cors_and_shared_cookie_domain_are_rejected(self):
        a, b = self.config()
        a["CORS_ORIGINS"] += ",https://" + b["ADMIN_HOST"]
        a["COOKIE_DOMAIN"] = ".test-hotels.kg"
        findings = " ".join(validate_shared_edge([a, b]))
        self.assertIn("CORS_ORIGINS", findings)
        self.assertIn("COOKIE_DOMAIN", findings)

    def test_bad_hostname_cannot_inject_caddy_config(self):
        a, b = self.config()
        b["PUBLIC_HOST"] = "bad.example.kg {\n reverse_proxy evil"
        self.assertIn("PUBLIC_HOST", " ".join(validate_shared_edge([a, b])))
        with self.assertRaises(ValueError):
            render([a, b])


if __name__ == "__main__":
    unittest.main()
