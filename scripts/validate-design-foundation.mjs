import fs from 'node:fs';

const read = (path) => fs.readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');
const spec = JSON.parse(read('docs/design/marina-smart.tokens.json'));
const mobile = read('apps/mobile/src/theme/tokens.ts');
const admin = read('apps/admin/app/globals.css');
const staff = read('apps/staff/app/globals.css');
const roleSource = read('apps/mobile/src/api/types.ts');

const failures = [];
const expectSourceValue = (source, value, label) => {
  if (!source.includes(value)) failures.push(`${label}: ${value} отсутствует в runtime source`);
};

for (const [theme, tokens] of Object.entries(spec.mobile.color)) {
  for (const [name, value] of Object.entries(tokens)) expectSourceValue(mobile, value, `mobile.${theme}.${name}`);
}
for (const [surface, values] of Object.entries({ admin: spec.webLegacy.admin, staff: spec.webLegacy.staff })) {
  const source = surface === 'admin' ? admin : staff;
  const visit = (node, path) => Object.entries(node).forEach(([key, value]) => {
    if (typeof value === 'string' && value.startsWith('#')) expectSourceValue(source, value, `${surface}.${path}${key}`);
    else if (value && typeof value === 'object') visit(value, `${path}${key}.`);
  });
  visit(values, '');
}
for (const role of spec.roles) {
  if (!new RegExp(`['"]${role}['"]`).test(roleSource)) failures.push(`role ${role} отсутствует в mobile Role`);
}
if (new Set(spec.roles).size !== spec.roles.length) failures.push('roles содержит дубликаты');
if (spec.webLegacy.themeSupport !== 'light-only') failures.push('web themeSupport должен фиксировать текущий light-only контракт');
if (spec.mobile.motionPolicy.reducedMotion !== 'disable') failures.push('mobile reduced-motion policy должен быть disable');

if (failures.length) {
  console.error(failures.join('\n'));
  process.exit(1);
}
console.log(`Design foundation OK: ${Object.keys(spec.mobile.color.light).length} mobile color tokens, ${spec.roles.length} roles.`);
