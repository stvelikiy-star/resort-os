import React, { useEffect, useRef, useState } from 'react';
import { Animated, ColorValue, Easing, Modal, Pressable, StyleProp, View, ViewStyle, useWindowDimensions } from 'react-native';
import type { LucideIcon } from 'lucide-react-native';
import { useTheme } from '../theme/ThemeProvider';
import { motionPresets, useMotionPreference } from '../theme/motion';
import { iconography, radius } from '../theme/tokens';

/**
 * Shared motion primitives that complement PremiumEntrance / PressScale / AnimatedKpi (Future.tsx, ui.tsx).
 * Rules for every component here:
 *  - Reduced Motion, backgrounded app or unknown preference => the final state is applied immediately.
 *  - Only transform/opacity with the native driver; nothing loops; nothing blocks touches.
 *  - Motion is driven by props that come from the server / navigation state, never by local optimism.
 */

const FILL = { position: 'absolute', top: 0, left: 0, right: 0, bottom: 0 } as const;

/** Bottom-tab icon: the highlight pill fades/stretches in and the glyph lifts slightly on selection. */
export function TabIcon({ icon: Icon, focused, color }: { icon: LucideIcon; focused: boolean; color: ColorValue }) {
  const { c } = useTheme();
  // The navigator always supplies its tint as a string; anything else falls back to the inactive nav color.
  const tint = typeof color === 'string' ? color : c.navInactive;
  const { allowed, ready } = useMotionPreference();
  const [focus] = useState(() => new Animated.Value(focused ? 1 : 0));
  const target = focused ? 1 : 0;
  useEffect(() => {
    focus.stopAnimation();
    if (!ready || !allowed) { focus.setValue(target); return; }
    const animation = focused
      ? Animated.spring(focus, { toValue: 1, useNativeDriver: true, speed: 20, bounciness: 6 })
      : Animated.timing(focus, { toValue: 0, duration: motionPresets.tab.duration, easing: motionPresets.tab.easing, useNativeDriver: true });
    animation.start();
    return () => { animation.stop(); focus.setValue(target); };
  }, [focused, target, allowed, ready, focus]);
  return <View style={{ minWidth: 50, height: 38, borderRadius: radius.pill, alignItems: 'center', justifyContent: 'center' }}>
    <Animated.View pointerEvents="none" style={{
      ...FILL, borderRadius: radius.pill, backgroundColor: c.primarySoft,
      borderWidth: 1, borderColor: c.glassBorder, opacity: focus,
      transform: [{ scaleX: focus.interpolate({ inputRange: [0, 1], outputRange: [0.62, 1] }) }],
    }}/>
    <Animated.View style={{ transform: [
      { scale: focus.interpolate({ inputRange: [0, 1], outputRange: [1, 1.08] }) },
      { translateY: focus.interpolate({ inputRange: [0, 1], outputRange: [0, -1] }) },
    ] }}>
      <Icon size={iconography.nav} color={tint} strokeWidth={focused ? iconography.strokeActive : iconography.stroke}/>
    </Animated.View>
  </View>;
}

/** Swaps a displayed STATUS with a short fade/settle, but only when `value` itself changes.
 * `value` must come from the server record (for example the reservation status after a reload),
 * never from a pending/optimistic local flag: a failed or unknown write changes nothing, so nothing animates.
 * No check marks, no celebration: it is the same badge, replaced smoothly. */
export function ConfirmedChange({ value, children, style }: { value: string | number | null | undefined; children: React.ReactNode; style?: StyleProp<ViewStyle> }) {
  const { allowed, ready } = useMotionPreference();
  const [progress] = useState(() => new Animated.Value(1));
  const last = useRef(value);
  useEffect(() => {
    if (last.current === value) return;
    last.current = value;
    progress.stopAnimation();
    if (!ready || !allowed) { progress.setValue(1); return; }
    progress.setValue(0);
    const animation = Animated.timing(progress, { toValue: 1, duration: motionPresets.status.duration, easing: motionPresets.status.easing, useNativeDriver: true });
    animation.start();
    return () => { animation.stop(); progress.setValue(1); };
  }, [value, allowed, ready, progress]);
  return <Animated.View style={[{ alignSelf: 'flex-start', maxWidth: '100%' }, style, {
    opacity: progress.interpolate({ inputRange: [0, 1], outputRange: [0.2, 1] }),
    transform: [
      { translateY: progress.interpolate({ inputRange: [0, 1], outputRange: [5, 0] }) },
      { scale: progress.interpolate({ inputRange: [0, 1], outputRange: [0.94, 1] }) },
    ],
  }]}>{children}</Animated.View>;
}

/** Bottom sheet shell: backdrop fades, the sheet itself rises and settles; it also animates out.
 * Wraps the platform Modal, so Android back (`onRequestClose`), accessibility focus and the
 * existing sheet content/testIDs are unchanged. The last visible content stays rendered while the exit plays. */
export function AnimatedSheet({ visible, onRequestClose, closeLabel, children }: {
  visible: boolean; onRequestClose: () => void; closeLabel: string; children: React.ReactNode;
}) {
  const { allowed, ready } = useMotionPreference();
  const canAnimate = ready && allowed;
  const { height } = useWindowDimensions();
  const [progress] = useState(() => new Animated.Value(visible ? 1 : 0));
  const [previous, setPrevious] = useState(visible);
  const [closing, setClosing] = useState(false);
  const [held, setHeld] = useState<React.ReactNode>(children);
  // Derived during render (guarded, converges in one extra pass) so the Modal is never
  // unmounted before the exit animation can play and nothing can get stuck half-open.
  if (visible && held !== children) setHeld(children);
  if (previous !== visible) {
    setPrevious(visible);
    setClosing(!visible && canAnimate);
  } else if (closing && !canAnimate) {
    setClosing(false);
  }
  useEffect(() => {
    progress.stopAnimation();
    if (!canAnimate) { progress.setValue(visible ? 1 : 0); return; }
    const animation = visible
      ? Animated.timing(progress, { toValue: 1, duration: motionPresets.sheetIn.duration, easing: motionPresets.sheetIn.easing, useNativeDriver: true })
      : Animated.timing(progress, { toValue: 0, duration: motionPresets.sheetOut.duration, easing: Easing.in(Easing.cubic), useNativeDriver: true });
    animation.start(({ finished }) => { if (finished && !visible) setClosing(false); });
    return () => animation.stop();
  }, [visible, canAnimate, progress]);
  return <Modal visible={visible || closing} transparent animationType="none" onRequestClose={onRequestClose}>
    <View style={{ flex: 1, justifyContent: 'flex-end' }}>
      <Animated.View pointerEvents="none" style={{ ...FILL, backgroundColor: 'rgba(0,9,20,0.68)', opacity: progress }}/>
      <Pressable accessibilityRole="button" accessibilityLabel={closeLabel} onPress={onRequestClose} style={{ flex: 1 }}/>
      <Animated.View pointerEvents={visible ? 'auto' : 'none'} style={{
        opacity: progress.interpolate({ inputRange: [0, 0.35, 1], outputRange: [0, 1, 1] }),
        transform: [{ translateY: progress.interpolate({ inputRange: [0, 1], outputRange: [Math.min(height * 0.55, 460), 0] }) }],
      }}>{visible ? children : held}</Animated.View>
    </View>
  </Modal>;
}
