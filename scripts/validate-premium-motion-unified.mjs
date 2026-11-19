/**
 * Premium Motion contract: prevents drift across the existing native motion
 * module and the two Web surfaces. This validates only the newly standardized
 * motion section; legacy UI CSS is intentionally outside migration scope.
 * No access to API, env, credentials or external services.
 */
import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(import.meta.dirname, '..');
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');
const mobile = read('apps/mobile/src/theme/tokens.ts');
const native = read('apps/mobile/src/theme/motion.ts');
const admin = read('apps/admin/app/fl2-shell.css');
const staff = read('apps/staff/app/globals.css');
const pms = read('apps/admin/components/PMSUniversalBoard.tsx');
const failures = [];

const durationTokens = { fast: 120, base: 200, slow: 320, stagger: 40 };
for (const [name, ms] of Object.entries(durationTokens)) {
  for (const [surface, text] of [['Admin', admin], ['Staff', staff]]) {
    const expected = `--marina-motion-${name}: ${ms}ms;`;
    if (!text.includes(expected)) failures.push(`${surface}: expected ${expected}`);
  }
}
const requiredNative = [
  /press:\s*120\b/, /tab:\s*200\b/, /card:\s*320\b/,
  /modal:\s*320\b/, /chart:\s*320\b/,
  /sheetIn:\s*320\b/, /sheetOut:\s*200\b/,
  /status:\s*200\b/, /tabIcon:\s*200\b/,
  /cardStagger:\s*40\b/, /maxStaggerCards:\s*8\b/,
];
for (const re of requiredNative) {
  if (!re.test(mobile)) failures.push(`Mobile: missing token ${re.source}`);
}
if (!native.includes('useMotionPreference') || !native.includes('AccessibilityInfo.isReduceMotionEnabled')) {
  failures.push('Mobile: shared OS Reduce Motion preference removed');
}
if (!native.includes("AppState.currentState === 'active'")) {
  failures.push('Mobile: background motion gate removed');
}

for (const [surface, code, start, end] of [
  ['Admin', admin, '/* Premium Motion System — FL2 only;', '\n@media (prefers-reduced-motion: reduce)'],
  ['Staff', staff, '/* Premium Motion — Staff.', '\n@media (prefers-reduced-motion: reduce)'],
]) {
  const p = code.indexOf(start);
  const stop = code.indexOf(end, p);
  if (p < 0 || stop < 0) { failures.push(`${surface}: missing scoped motion contract`); continue; }
  const section = code.slice(p, stop);
  const declarations = [...section.matchAll(/(?:transition|animation)(?:-[a-z]+)?:\s*([^;]+);/g)].map(x => x[1]);
  for (const value of declarations) {
    if (/\b\d+(?:\.\d+)?(?:ms|s)\b/.test(value) && !/\b0ms\b/.test(value)) {
      failures.push(`${surface}: hard-coded motion duration in ${value.trim()}`);
    }
  }
  if (/\b(?:width|height|top|left|right|bottom|margin|padding)\s*:/i.test(section.slice(section.indexOf('@keyframes')))) {
    failures.push(`${surface}: keyframe animates layout geometry`);
  }
  if (!section.includes('transform') || !section.includes('opacity')) failures.push(`${surface}: required safe motion properties missing`);
  if (!code.includes('@media (prefers-reduced-motion: reduce)')) failures.push(`${surface}: missing Reduce Motion fallback`);
  if (/animation-iteration-count:\s*infinite/.test(section)) failures.push(`${surface}: endless animation forbidden`);
}
if (pms.includes('Three Crowns · Universal Tape Chart')) failures.push('PMS: legacy hotel name remains in universal UI');

if (failures.length) {
  console.error('Premium Motion contract FAILED:\n' + failures.join('\n'));
  process.exit(1);
}
console.log('Premium Motion contract PASS: native tokens, FL2/Staff timing, reduced motion, branding and no new hardcoded timing.');
