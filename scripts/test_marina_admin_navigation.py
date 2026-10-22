#!/usr/bin/env python3
"""Navigation contract: operational priorities plus owner-first WhatsApp access."""
from pathlib import Path
import re
import unittest

FILE = Path(__file__).resolve().parents[1] / "apps/admin/components/AdminShell.tsx"
source = FILE.read_text(encoding="utf-8")
DASHBOARD = Path(__file__).resolve().parents[1] / "apps/admin/components/DashboardBoard.tsx"
dashboard = DASHBOARD.read_text(encoding="utf-8")


class AdminNavigationTest(unittest.TestCase):
    def test_every_tab_has_expected_navigation_entries(self):
        definition = re.search(r"^type Tab = (.+);$", source, flags=re.MULTILINE)
        self.assertIsNotNone(definition)
        tabs = re.findall(r'"([A-Z_]+)"', definition.group(1))
        nav = source.split('<nav className="admin-tabs"', 1)[1].split("</nav>", 1)[0]
        for tab in tabs:
            with self.subTest(tab=tab):
                expected = 2 if tab == "WHATSAPP" else 1
                self.assertEqual(nav.count(f'setTab("{tab}")'), expected)

    def test_owner_whatsapp_is_first_navigation_item(self):
        nav = source.split('<nav className="admin-tabs"', 1)[1].split("</nav>", 1)[0]
        owner_entry = nav.index('{user.role === "OWNER" && <button className={tab === "WHATSAPP"')
        pms_entry = nav.index('setTab("PMS")')
        self.assertLess(owner_entry, pms_entry)
        self.assertIn('WhatsApp / AI</button>}', nav[owner_entry:nav.index("\n", owner_entry)])

    def test_owner_dashboard_has_direct_whatsapp_entry(self):
        self.assertIn('isOwner={user.role === "OWNER"}', source)
        self.assertIn('isOwner && <section className="command-panel" aria-label="WhatsApp и MARINA AI для собственника">', dashboard)
        self.assertIn('Drill to="WHATSAPP" onNavigate={onNavigate}>Открыть раздел</Drill>', dashboard)

    def test_daily_work_order_is_preserved_for_other_roles(self):
        nav = source.split('<nav className="admin-tabs"', 1)[1].split("</nav>", 1)[0]
        priority = ["PMS", "RESERVATIONS", "REQUESTS", "RATES",
                    "SERVICES", "OPS", "DASHBOARD", "FINANCE"]
        offsets = [nav.index(f'setTab("{tab}")') for tab in priority]
        self.assertEqual(offsets, sorted(offsets))
        self.assertLess(max(offsets), nav.index('<summary>Все разделы</summary>'))

    def test_role_guards_remain(self):
        nav = source.split('<nav className="admin-tabs"', 1)[1].split("</nav>", 1)[0]
        self.assertIn('{(canUseReception || isAgent) && <button', nav)
        self.assertIn('{user.role === "OWNER" && <button className={tab === "WHATSAPP"', nav)
        self.assertIn('{canUseReception && user.role !== "OWNER" && <button className={tab === "WHATSAPP"', nav)
        self.assertIn('{isManager && <button className={tab === "RATES"', nav)
        self.assertIn('{(isManager || canUseReception) && <details', nav)
        self.assertNotIn("GREEN_API_TOKEN_INSTANCE", nav)

    def test_secondary_sections_named(self):
        for title in ("Бронирования и продажи", "Работа гостиницы", "Управление и настройки"):
            self.assertIn(f'>{title}</p>', source)


if __name__ == "__main__":
    unittest.main()
