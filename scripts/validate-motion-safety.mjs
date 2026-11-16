import fs from 'node:fs';
const read = path => fs.readFileSync(new URL('../' + path, import.meta.url), 'utf8');
const future = read('apps/mobile/src/components/Future.tsx');
const owner = read('apps/mobile/src/components/OwnerControlDashboard.tsx');
const ui = read('apps/mobile/src/components/ui.tsx');
const motion = read('apps/mobile/src/theme/motion.ts');
const failures = [];
const requireText = (source, text, label) => { if (!source.includes(text)) failures.push(label + ': missing ' + text); };
// Follow the shared implementation rather than requiring obsolete inline animations.
requireText(future, 'useRevealProgress(', 'PremiumEntrance');
requireText(future, 'useAnimatedNumber(', 'Verified KPI');
requireText(owner, '<AnimatedProgressBar', 'OWNER occupancy');
requireText(owner, 'occupancyKnown ? <OccupancyProgress', 'Unknown occupancy remains absent');
requireText(ui, 'accessibilityRole="progressbar"', 'Occupancy semantics');
requireText(ui, 'getMotionSnapshot().allowed', 'Synchronous press preference');
requireText(motion, 'useMotionPreference()', 'Shared preference');
requireText(motion, "AppState.currentState === 'active'", 'Background gate');
requireText(motion, 'new Animated.Value(hiddenAtMount ? 0 : 1)', 'Content visible before preference resolution');
requireText(motion, 'animation.stop()', 'Animation cleanup');
requireText(motion, 'isReduceMotionEnabled()', 'OS Reduce Motion');
for (const source of [owner, ui, motion]) {
  if (/Animated\.loop/.test(source)) failures.push('Unbounded animation loop is forbidden');
}
requireText(future, 'iterations: motion.maxShimmerPulses', 'Bounded skeleton');
requireText(future, 'iterations: motion.maxOrbTurns', 'Bounded AI effect');
if (failures.length) { console.error(failures.join('\n')); process.exit(1); }
console.log('Motion safety PASS: shared OS/background gate, fail-visible content, verified progress, finite animation and cleanup.');
