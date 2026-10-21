#!/usr/bin/env python3
"""Navigation contract: all modules remain accessible and operational priorities stay first."""
from pathlib import Path
import re
import unittest

FILE = Path(__file__).resolve().parents[1] / "apps/admin/components/AdminShell.tsx"
source = FILE.read_text(encoding="utf-8")


class AdminNavigationTest(unittest.TestCase):
    def test_every_tab_appears_exactly_once(self):
        definition = re.search(r"^type Tab = (.+);$", source, flags=re.MULTILINE)
        self.assertIsNotNone(definition)
        tabs = re.findall(r'"([A-Z_]+)"', definition.group(1))
        nav = source.split('<nav className="admin-tabs"', 1)[1].split("</nav>", 1)[0]
        for tab in tabs:
            with self.subTest(tab=tab):
                self.assertEqual(nav.count(f'setTab("{tab}")'), 1)

    def test_daily_work_is_first(self):
        nav = source.split('<nav className="admin-tabs"', 1)[1].split("</nav>", 1)[0]
        priority = ["PMS", "RESERVATIONS", "REQUESTS", "WHATSAPP", "RATES",
                    "SERVICES", "OPS", "DASHBOARD", "FINANCE"]
        offsets = [nav.index(f'setTab("{tab}")') for tab in priority]
        self.assertEqual(offsets, sorted(offsets))
        self.assertLess(max(offsets), nav.index('<summary>Все разделы</summary>'))

    def test_role_guards_remain(self):
        nav = source.split('<nav className="admin-tabs"', 1)[1].split("</nav>", 1)[0]
        self.assertIn('{(canUseReception || isAgent) && <button', nav)
        self.assertIn('{canUseReception && <button className={tab === "WHATSAPP"', nav)
        self.assertIn('{isManager && <button className={tab === "RATES"', nav)
        self.assertIn('{(isManager || canUseReception) && <details', nav)
        self.assertNotIn("GREEN_API_TOKEN_INSTANCE", nav)

    def test_secondary_sections_named(self):
        for title in ("Бронирования и продажи", "Работа гостиницы", "Управление и настройки"):
            self.assertIn(f'>{title}</p>', source)


if __name__ == "__main__":
    unittest.main()
