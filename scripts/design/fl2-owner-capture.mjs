// Usage: node scripts/design/fl2-owner-capture.mjs <outDir> <label>
// Requires: admin dev/prod server on :3001 proxied to the QA mock Core (CORE_API_URL=http://127.0.0.1:8000).
import { createRequire } from "node:module";
import fs from "node:fs";
const require = createRequire(import.meta.url);
const { chromium } = require("playwright");
const [outDir = "out", label = "shot"] = process.argv.slice(2);
fs.mkdirSync(outDir, { recursive: true });
const base = process.env.ADMIN_URL || "http://127.0.0.1:3001";
const views = [
  { id: "desktop", viewport: { width: 1440, height: 900 } },
  { id: "tablet", viewport: { width: 768, height: 1024 } },
  { id: "phone", viewport: { width: 390, height: 844 }, mobile: true },
];
const browser = await chromium.launch();
for (const theme of ["dark", "light"]) for (const v of views) {
  const ctx = await browser.newContext({ viewport: v.viewport, deviceScaleFactor: 1, isMobile: !!v.mobile, hasTouch: !!v.mobile, reducedMotion: "reduce" });
  await ctx.addInitScript((t) => { localStorage.setItem("marina-admin-ui", "future-luxury"); localStorage.setItem("marina-fl2-theme", t); }, theme);
  const page = await ctx.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  page.on("console", (m) => { if (m.type() === "error" && !/404/.test(m.text())) errors.push(m.text()); });
  await page.goto(base, { waitUntil: "networkidle" });
  await page.waitForTimeout(1200);
  await page.screenshot({ path: `${outDir}/${label}-${v.id}-${theme}-fold.png` });
  await page.screenshot({ path: `${outDir}/${label}-${v.id}-${theme}-full.png`, fullPage: true });
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  console.log(`${label} ${v.id} ${theme}: hOverflow=${overflow}px errors=${errors.length}${errors.length ? " " + errors.slice(0, 2).join(" | ") : ""}`);
  await ctx.close();
}
await browser.close();
