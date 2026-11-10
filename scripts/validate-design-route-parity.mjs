import fs from 'node:fs';
const baseline = JSON.parse(fs.readFileSync(new URL('../docs/design/mobile-routes-baseline.json', import.meta.url), 'utf8'));
const missing = baseline.routes.filter(p => !fs.existsSync(new URL('../' + p, import.meta.url)));
if (new Set(baseline.routes).size !== baseline.routes.length) throw new Error('Duplicate routes in visual baseline');
if (missing.length) { console.error('CRITICAL: visual redesign removed existing routes:', missing); process.exit(1); }
console.log(`Visual no-removal guard OK: ${baseline.routes.length} mobile route files retained.`);
