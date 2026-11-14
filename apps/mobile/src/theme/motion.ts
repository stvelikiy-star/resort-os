import { useEffect, useRef, useState, useSyncExternalStore } from 'react';
import { AccessibilityInfo, Animated, AppState, Easing } from 'react-native';
import { motion } from './tokens';

export const motionPresets = {
  entrance: { duration: motion.card, easing: Easing.out(Easing.cubic) },
  modal: { duration: motion.modal, easing: Easing.out(Easing.cubic) },
  press: { duration: motion.press, easing: Easing.out(Easing.cubic) },
  tab: { duration: motion.tab, easing: Easing.out(Easing.cubic) },
  chart: { duration: motion.chart, easing: Easing.out(Easing.cubic) },
  sheetIn: { duration: motion.sheetIn, easing: Easing.out(Easing.cubic) },
  sheetOut: { duration: motion.sheetOut, easing: Easing.in(Easing.cubic) },
  status: { duration: motion.status, easing: Easing.out(Easing.cubic) },
} as const;

/* ------------------------------------------------------------------ *
 * Motion preference: ONE app-wide subscription (OS Reduce Motion +
 * foreground state) shared by every animated component. Previously each
 * animated card registered its own listeners and PressScale awaited an
 * async OS call on every touch; a shared synchronous snapshot removes both.
 * ------------------------------------------------------------------ */
export type MotionPreference = { allowed: boolean; ready: boolean };

const UNKNOWN: MotionPreference = { allowed: false, ready: false };
let snapshot: MotionPreference = UNKNOWN;
let reduceMotion: boolean | null = null;
let started = false;
let removers: (() => void)[] = [];
const listeners = new Set<() => void>();

function publish() {
  const ready = reduceMotion !== null;
  const allowed = ready && !reduceMotion && AppState.currentState === 'active';
  if (snapshot.allowed === allowed && snapshot.ready === ready) return;
  snapshot = { allowed, ready };
  listeners.forEach(listener => listener());
}

/** Idempotent. Safe to call at module load so the preference is known before the first screen mounts. */
export function primeMotionPreference(): void {
  if (started) return;
  started = true;
  try {
    void AccessibilityInfo.isReduceMotionEnabled()
      .then(enabled => { reduceMotion = !!enabled; publish(); })
      // Unknown preference fails SAFE: content stays static and visible.
      .catch(() => { reduceMotion = true; publish(); });
    const reduceSub = AccessibilityInfo.addEventListener('reduceMotionChanged', enabled => { reduceMotion = !!enabled; publish(); });
    const stateSub = AppState.addEventListener('change', () => publish());
    removers = [() => reduceSub?.remove?.(), () => stateSub?.remove?.()];
  } catch {
    reduceMotion = true;
    publish();
  }
}

/** Synchronous read for event handlers (press feedback). */
export function getMotionSnapshot(): MotionPreference {
  return snapshot;
}

function subscribe(listener: () => void) {
  primeMotionPreference();
  listeners.add(listener);
  return () => { listeners.delete(listener); };
}

/** Test helper only: forget the cached OS preference and subscriptions. */
export function resetMotionPreferenceForTests(): void {
  removers.forEach(remove => remove());
  removers = [];
  listeners.clear();
  snapshot = UNKNOWN;
  reduceMotion = null;
  started = false;
}

/** Resolves the OS preference before an entrance animation makes content visible.
 * Never run motion while backgrounded; Reduced Motion always takes priority.
 */
export function useMotionPreference(): MotionPreference {
  return useSyncExternalStore(subscribe, getMotionSnapshot, getMotionSnapshot);
}
export function useMotionAllowed(): boolean {
  return useMotionPreference().allowed;
}
export function cappedStagger(index: number): number {
  return Math.min(Math.max(index, 0), motion.maxStaggerCards) * motion.cardStagger;
}

/** Animates a REAL number from the API.
 * - First appearance with motion allowed: 0 -> value (a reveal of verified data).
 * - Later changes: previous -> new value.
 * - Reduced Motion / backgrounded / preference unknown: the exact value, immediately.
 * The target is always the server value, so the animation can never show a number the API did not send.
 */
export function useAnimatedNumber(target: number, duration: number = motion.chart): number {
  const { allowed, ready } = useMotionPreference();
  const safe = Number.isFinite(target) ? target : 0;
  const canAnimate = ready && allowed;
  const [revealFromZero] = useState(() => getMotionSnapshot().allowed);
  const [value] = useState(() => new Animated.Value(revealFromZero ? 0 : safe));
  const [shown, setShown] = useState(revealFromZero ? 0 : safe);
  // Subscribe to the animated value (external system); every update, animated or immediate, flows through here.
  useEffect(() => {
    const id = value.addListener(({ value: next }) => setShown(next));
    return () => value.removeListener(id);
  }, [value]);
  useEffect(() => {
    value.stopAnimation();
    if (!canAnimate) { value.setValue(safe); return; }
    const animation = Animated.timing(value, { toValue: safe, duration, easing: Easing.out(Easing.cubic), useNativeDriver: false });
    animation.start();
    return () => animation.stop();
  }, [canAnimate, safe, duration, value]);
  return shown;
}

/** One-time reveal driver (0 -> 1) shared by every entrance. Native-driver friendly.
 * - Starts hidden ONLY if motion is already known to be allowed at mount (no visible-then-hidden flash).
 * - Unknown preference, Reduce Motion, backgrounded app, unmount or interruption all leave content fully visible.
 * - Plays once per mounted instance; re-renders and data refreshes never replay it. */
export function useRevealProgress(delay = 0, duration: number = motion.card): Animated.Value {
  const { allowed, ready } = useMotionPreference();
  const [hiddenAtMount] = useState(() => getMotionSnapshot().allowed);
  const [progress] = useState(() => new Animated.Value(hiddenAtMount ? 0 : 1));
  const pending = useRef(hiddenAtMount);
  useEffect(() => {
    if (!pending.current) { progress.setValue(1); return; }
    if (!ready) return;
    if (!allowed) { pending.current = false; progress.setValue(1); return; }
    const animation = Animated.timing(progress, { toValue: 1, duration, delay, easing: Easing.out(Easing.cubic), useNativeDriver: true });
    animation.start(({ finished }) => { if (finished) pending.current = false; });
    return () => { animation.stop(); progress.setValue(1); pending.current = false; };
  }, [allowed, ready, progress, delay, duration]);
  return progress;
}
