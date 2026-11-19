import fs from 'node:fs';

const read = (name) => fs.readFileSync(new URL(name, import.meta.url), 'utf8');
const future = read('../apps/mobile/src/components/Future.tsx');
const owner = read('../apps/mobile/src/components/OwnerControlDashboard.tsx');
const ui = read('../apps/mobile/src/components/ui.tsx');
const shared = read('../apps/mobile/src/theme/motion.ts');
const failures = [];

/* Validate the CURRENT shared architecture; do not mistake delegated motion
 * for missing accessibility behavior. These checks run in addition to Jest. */
if (!future.includes('useRevealProgress(cappedStagger(index), motionPresets.entrance.duration)'))
  failures.push('PremiumEntrance: must use shared finite native-driver reveal');
if (!shared.includes('useMotionPreference') || !shared.includes('AccessibilityInfo.isReduceMotionEnabled()'))
  failures.push('Motion store: must observe OS Reduce Motion');
if (!shared.includes("AppState.currentState === 'active'"))
  failures.push('Motion store: do not animate while backgrounded');
if (!shared.includes('new Animated.Value(hiddenAtMount ? 0 : 1)'))
  failures.push('Motion store: unknown preference must keep content visible');
if (!shared.includes('animation.stop(); progress.setValue(1); pending.current = false'))
  failures.push('Motion store: entrance must stop and reveal content on cleanup');
if (!future.includes('useMotionAllowed()'))
  failures.push('Future: limited decorative animation must observe motion preference');
if (!future.includes('iterations: motion.maxOrbTurns') || !future.includes('iterations: motion.maxShimmerPulses'))
  failures.push('Future: decorative loops must be finite');
if (!ui.includes('useNativeDriver: true') || !ui.includes('if (disabled) { s.stopAnimation(); s.setValue(1); }'))
  failures.push('PressScale: native press and disabled cleanup required');
if (!ui.includes('accessibilityRole="progressbar"') || !ui.includes('accessibilityValue={{ min: 0, max: 100, now: safePercent }}'))
  failures.push('AnimatedProgressBar: semantic and server-verified value required');
if (!owner.includes('occupancyKnown ? <OccupancyProgress') ||
    !owner.includes('Number.isInteger(data.rooms.total) && data.rooms.total > 0'))
  failures.push('OwnerControlDashboard: unknown occupancy must not be animated as zero');
if (!owner.includes('canReadFinance(user)'))
  failures.push('OwnerControlDashboard: financial role guard must remain');

if (failures.length) {
  console.error(failures.join('\n'));
  process.exit(1);
}
console.log('Motion safety OK: shared OS gating, visible fallbacks, finite animation, cleanup and accessibility.');
