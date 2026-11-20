import fs from 'node:fs';

const read = (path) => fs.readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');
const tabSource = read('apps/mobile/src/roles/registry.ts');
const mobileSource = read('apps/mobile/src/theme/moduleIcons.ts');
const webSource = read('apps/admin/lib/module-icon-manifest.ts');

const tabMatch = tabSource.match(/export type TabKey\s*=\s*([^;]+);/);
if (!tabMatch) throw new Error('TabKey declaration not found');
const tabs = [...tabMatch[1].matchAll(/'([^']+)'/g)].map((match) => match[1]);

const expected = {
  overview: 'LayoutDashboard', reception: 'ConciergeBell', pms: 'CalendarDays',
  inbox: 'MessageCircle', dining: 'UtensilsCrossed', kitchen: 'ChefHat',
  tasks: 'ClipboardCheck', rooms: 'BedDouble', requests: 'Wrench',
  admin: 'UsersRound', profile: 'CircleUserRound',
};
const failures = [];

if (tabs.length !== 11) failures.push(`expected 11 TabKey values, found ${tabs.length}`);
if (new Set(tabs).size !== tabs.length) failures.push('TabKey contains duplicates');
if (new Set(Object.values(expected)).size !== Object.keys(expected).length) failures.push('icon mapping contains duplicate icon names');

for (const tab of tabs) {
  const icon = expected[tab];
  if (!icon) {
    failures.push(`missing canonical icon for TabKey ${tab}`);
    continue;
  }
  if (!new RegExp(`\\b${tab}:\\s*${icon}[,\\n]`).test(mobileSource)) failures.push(`mobile mismatch: ${tab} -> ${icon}`);
  if (!new RegExp(`\\b${tab}:\\s*\\{\\s*name:\\s*'${icon}'`).test(webSource)) failures.push(`web mismatch: ${tab} -> ${icon}`);
  if (!new RegExp(`\\b${icon}\\b`).test(mobileSource.split("from 'lucide-react-native'")[0])) failures.push(`Lucide import missing: ${icon}`);
}

for (const tab of Object.keys(expected)) {
  if (!tabs.includes(tab)) failures.push(`manifest key is not a TabKey: ${tab}`);
}

if (!mobileSource.includes('satisfies Record<TabKey, LucideIcon>')) failures.push('mobile mapping is not type-checked against TabKey');
if (failures.length) {
  console.error(failures.join('\n'));
  process.exit(1);
}
console.log(`Module icons OK: ${tabs.length} unique tabs and ${new Set(Object.values(expected)).size} unique Lucide icons; mobile/web aligned.`);
