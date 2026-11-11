import fs from 'node:fs';

const future = fs.readFileSync(new URL('../apps/mobile/src/components/Future.tsx', import.meta.url), 'utf8');
const owner = fs.readFileSync(new URL('../apps/mobile/src/components/OwnerControlDashboard.tsx', import.meta.url), 'utf8');
const failures = [];

for (const [name, source] of [['PremiumEntrance', future], ['OwnerControlDashboard', owner]]) {
  if (!source.includes('useMotionPreference')) failures.push(`${name}: missing reduced-motion/app-state gate`);
  if (!source.includes('animation.stop()')) failures.push(`${name}: missing animation cleanup`);
}
if (!future.includes('new Animated.Value(1)')) failures.push('PremiumEntrance: content must be visible before preference resolution');
if (/Animated\.loop/.test(owner)) failures.push('OwnerControlDashboard: endless animation is forbidden');
if (!owner.includes('accessibilityRole="progressbar"')) failures.push('OwnerControlDashboard: progressbar semantics missing');
if (!owner.includes('occupancyKnown ? <OccupancyProgress')) failures.push('OwnerControlDashboard: unknown occupancy must remain absent');

if (failures.length) {
  console.error(failures.join('\n'));
  process.exit(1);
}
console.log('Motion safety OK: gated, finite, fail-visible, accessible, cleanup present.');
