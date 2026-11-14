import React, { useEffect, useState } from 'react';
import { AccessibilityInfo, Animated, Easing, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleProp, StyleSheet, Text, TextInput, TextInputProps, View, ViewStyle, useWindowDimensions } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTranslation } from 'react-i18next';
import * as Haptics from 'expo-haptics';
import { useTheme } from '../theme/ThemeProvider';
import { elevation, font, motion, radius, space, TOUCH } from '../theme/tokens';
import { AlertTriangle, CheckCircle2, CircleDot, Info, XCircle } from 'lucide-react-native';
import type { LucideIcon } from 'lucide-react-native';

export function FadeIn({ children, delay = 0, style }: { children: React.ReactNode; delay?: number; style?: StyleProp<ViewStyle> }) {
  const [v] = useState(() => new Animated.Value(0));
  useEffect(() => {
    let mounted = true;
    let animation: Animated.CompositeAnimation | undefined;
    void AccessibilityInfo.isReduceMotionEnabled().then((reduceMotion) => {
      if (!mounted) return;
      if (reduceMotion) { v.setValue(1); return; }
      animation = Animated.timing(v, { toValue: 1, duration: motion.card, delay: Math.min(delay, motion.cardStagger * motion.maxStaggerCards), easing: Easing.out(Easing.cubic), useNativeDriver: true });
      animation.start();
    }).catch(() => { if (mounted) v.setValue(1); });
    return () => { mounted = false; animation?.stop(); };
  }, [v, delay]);
  return <Animated.View style={[style, { opacity: v, transform: [{ translateY: v.interpolate({ inputRange: [0, 1], outputRange: [18, 0] }) }] }]}>{children}</Animated.View>;
}

const OUTER_KEYS = ['flex', 'flexGrow', 'flexShrink', 'flexBasis', 'width', 'alignSelf'] as const;


/** Animated progress with reduced-motion support and screen-reader value. */
export function AnimatedProgressBar({ percent }: { percent: number }) {
  const { c } = useTheme();
  const safePercent = Math.min(100, Math.max(0, Number.isFinite(percent) ? percent : 0));
  const [progress] = useState(() => new Animated.Value(0));
  useEffect(() => {
    let active = true;
    let animation: Animated.CompositeAnimation | undefined;
    void AccessibilityInfo.isReduceMotionEnabled().then((reduceMotion) => {
      if (!active) return;
      if (reduceMotion) { progress.setValue(safePercent); return; }
      animation = Animated.timing(progress, { toValue: safePercent, duration: motion.chart, easing: Easing.out(Easing.cubic), useNativeDriver: false });
      animation.start();
    }).catch(() => { if (active) progress.setValue(safePercent); });
    return () => { active = false; animation?.stop(); };
  }, [progress, safePercent]);
  return (
    <View accessible accessibilityRole="progressbar" accessibilityValue={{ min: 0, max: 100, now: safePercent }}
      style={{ height: 11, borderRadius: 8, backgroundColor: 'rgba(255,255,255,0.20)', overflow: 'hidden' }}>
      <Animated.View style={{ width: progress.interpolate({ inputRange: [0, 100], outputRange: ['0%', '100%'], extrapolate: 'clamp' }), height: 11, borderRadius: 8, backgroundColor: c.cyan }} />
    </View>
  );
}

export function PressScale({ children, onPress, style, disabled, testID, accessibilityLabel, dimWhenDisabled = true }: { children: React.ReactNode; onPress?: () => void; style?: StyleProp<ViewStyle>; disabled?: boolean; testID?: string; accessibilityLabel?: string; dimWhenDisabled?: boolean }) {
  const [s] = useState(() => new Animated.Value(1));
  const to = (x: number) => {
    if (disabled) return;
    void AccessibilityInfo.isReduceMotionEnabled().then((reduceMotion) => {
      if (reduceMotion) { s.setValue(1); return; }
      Animated.spring(s, { toValue: x, useNativeDriver: true, speed: motion.spring.speed, bounciness: motion.spring.bounciness }).start();
    }).catch(() => s.setValue(1));
  };
  // Layout props belong to the touchable wrapper so flex rows (segmented controls, button pairs) share width.
  const flat = (StyleSheet.flatten(style) ?? {}) as Record<string, unknown>;
  const outer: Record<string, unknown> = {};
  const inner: Record<string, unknown> = {};
  for (const k of Object.keys(flat)) {
    if ((OUTER_KEYS as readonly string[]).includes(k)) outer[k] = flat[k];
    else inner[k] = flat[k];
  }
  const fill = outer.flex !== undefined || outer.flexGrow !== undefined;
  return (
    <Pressable testID={testID} accessibilityRole="button" accessibilityState={{ disabled: !!disabled }} accessibilityLabel={accessibilityLabel} disabled={disabled} style={outer as ViewStyle}
      onPressIn={() => to(0.97)} onPressOut={() => to(1)}
      onPress={() => { void Haptics.selectionAsync().catch(() => {}); onPress?.(); }}>
      <Animated.View style={[inner as ViewStyle, fill ? { flex: 1 } : null, { transform: [{ scale: s }], opacity: disabled && dimWhenDisabled ? 0.5 : 1 }]}>{children}</Animated.View>
    </Pressable>
  );
}

export function Screen({ children, scroll = true, padded = true }: { children: React.ReactNode; scroll?: boolean; padded?: boolean }) {
  const { c } = useTheme();
  const insets = useSafeAreaInsets();
  const pad = padded ? space.lg : 0;
  return (
    <KeyboardAvoidingView style={{ flex: 1, backgroundColor: c.bg }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      {scroll ? (
        <ScrollView style={{ flex: 1 }} keyboardDismissMode="on-drag" keyboardShouldPersistTaps="handled" contentContainerStyle={{ padding: pad, paddingTop: insets.top + space.md, paddingBottom: 112 + insets.bottom, gap: space.md }}>{children}</ScrollView>
      ) : (
        <View style={{ flex: 1, padding: pad, paddingTop: insets.top + space.md, gap: space.md }}>{children}</View>
      )}
    </KeyboardAvoidingView>
  );
}

export function Title({ children, sub }: { children: React.ReactNode; sub?: string }) {
  const { c } = useTheme();
  return (
    <View style={{ gap: 2 }}>
      <Text accessibilityRole="header" style={[font.title, { color: c.text }]}>{children}</Text>
      {sub ? <Text style={[font.small, { color: c.textMuted }]}>{sub}</Text> : null}
    </View>
  );
}

export function Card({ children, style, onPress, testID }: { children: React.ReactNode; style?: StyleProp<ViewStyle>; onPress?: () => void; testID?: string }) {
  const { c } = useTheme();
  const base: ViewStyle = { backgroundColor: c.surface, borderRadius: radius.lg, padding: space.lg, borderWidth: 1, borderColor: c.border, shadowColor: c.shadow, ...elevation.card };
  return onPress ? <PressScale testID={testID} onPress={onPress} style={[base, style]}>{children}</PressScale> : <View testID={testID} style={[base, style]}>{children}</View>;
}

type Tone = 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'neutral';
export function toneColors(c: ReturnType<typeof useTheme>['c'], tone: Tone) {
  switch (tone) {
    case 'success': return { fg: c.success, bg: c.successSoft };
    case 'warning': return { fg: c.warning, bg: c.warningSoft };
    case 'danger': return { fg: c.danger, bg: c.dangerSoft };
    case 'info': return { fg: c.info, bg: c.infoSoft };
    case 'primary': return { fg: c.primary, bg: c.primarySoft };
    default: return { fg: c.textMuted, bg: c.surfaceAlt };
  }
}

/** Shared visual language: color is never the only status signal.
 * A translated label remains authoritative; icon is decorative/redundant.
 * Caller-supplied icon always wins, preserving existing domain semantics.
 */
const BADGE_ICONS: Record<Exclude<Tone, 'neutral'>, LucideIcon> = {
  primary: CircleDot, success: CheckCircle2, warning: AlertTriangle,
  danger: XCircle, info: Info,
};
export function Badge({ label, tone = 'neutral', icon: Icon }: { label: string; tone?: Tone; icon?: LucideIcon }) {
  const SemanticIcon = Icon ?? (tone === 'neutral' ? undefined : BADGE_ICONS[tone]);
  const { c } = useTheme();
  const t = toneColors(c, tone);
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: t.bg, paddingHorizontal: 11, paddingVertical: 6, borderRadius: radius.pill,
      borderWidth: 1, borderColor: c.glassBorder, alignSelf: 'flex-start', maxWidth: '100%' }}>
      {SemanticIcon ? <SemanticIcon size={13} color={t.fg} /> : null}
      <Text style={[font.label, { color: t.fg, flexShrink: 1 }]}>{label}</Text>
    </View>
  );
}

export function Button({ label, onPress, icon: Icon, variant = 'primary', disabled, testID }: { label: string; onPress: () => void; icon?: LucideIcon; variant?: 'primary' | 'secondary' | 'danger' | 'ghost'; disabled?: boolean; testID?: string }) {
  const { c } = useTheme();
  const bg = variant === 'primary' ? c.primary : variant === 'danger' ? c.danger : variant === 'secondary' ? c.primarySoft : 'transparent';
  const fg = variant === 'primary' || variant === 'danger' ? c.primaryText : c.primary;
  return (
    <PressScale testID={testID} disabled={disabled} onPress={onPress} accessibilityLabel={label}
      style={{ minHeight: TOUCH, borderRadius: radius.lg, backgroundColor: bg, paddingHorizontal: space.xl, borderWidth: variant === 'secondary' ? 1 : 0, borderColor: c.border, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: space.sm }}>
      {Icon ? <Icon size={22} color={fg} /> : null}
      <Text style={[font.h2, { color: fg, fontSize: 17, flexShrink: 1, textAlign: 'center' }]}>{label}</Text>
    </PressScale>
  );
}

export function Field({ label, ...rest }: TextInputProps & { label: string }) {
  const { c } = useTheme();
  return (
    <View style={{ gap: 6 }}>
      <Text style={[font.label, { color: c.textMuted }]}>{label.toUpperCase()}</Text>
      <TextInput accessibilityLabel={label} placeholderTextColor={c.textMuted} {...rest}
        style={[{ minHeight: TOUCH, borderRadius: radius.md, borderWidth: 1.3, borderColor: c.border, backgroundColor: c.surface, color: c.text, paddingHorizontal: space.lg, fontSize: 16 }, rest.style]} />
    </View>
  );
}

/** Compose translated headings with dates/counts without Array#toString commas. */
export function sectionLabelText(children: React.ReactNode): string {
  const parts = Array.isArray(children) ? children : [children];
  return parts.map(part => (part == null || typeof part === 'boolean') ? '' : String(part)).join('').toUpperCase();
}
export function SectionLabel({ children }: { children: React.ReactNode }) {
  const { c } = useTheme();
  return <Text style={[font.label, { color: c.textMuted, marginTop: space.sm }]}>{sectionLabelText(children)}</Text>;
}

export function DemoBanner() {
  const { t } = useTranslation();
  const { c } = useTheme();
  return (
    <View testID="demo-banner" accessibilityRole="alert" style={{ backgroundColor: c.warningSoft, borderRadius: radius.pill, paddingVertical: 6, paddingHorizontal: 12, alignSelf: 'flex-start' }}>
      <Text style={[font.label, { color: c.warning }]}>{t('common.demo')}</Text>
    </View>
  );
}

export function Empty({ text }: { text: string }) {
  const { c } = useTheme();
  return <Text style={[font.body, { color: c.textMuted, textAlign: 'center', paddingVertical: space.xxl }]}>{text}</Text>;
}

export function Segmented<T extends string>({ value, options, onChange }: { value: T; options: { key: T; label: string }[]; onChange: (k: T) => void }) {
  const { c } = useTheme();
  const { width, fontScale } = useWindowDimensions();
  const wrap = options.length >= 4 && (width < 430 || fontScale > 1.25);
  return (
    <View style={{ flexDirection: 'row', flexWrap: wrap ? 'wrap' : 'nowrap', backgroundColor: c.surfaceAlt, borderRadius: wrap ? radius.md : radius.pill, padding: 4, gap: 4 }}>
      {options.map((o) => {
        const on = o.key === value;
        return (
          <Pressable key={o.key} testID={`segment-${o.key}`} onPress={() => onChange(o.key)}
            accessibilityRole="radio" accessibilityState={{ checked: on }} accessibilityLabel={o.label}
            style={{ flex: wrap ? undefined : 1, width: wrap ? '48%' : undefined, minWidth: 0, minHeight: 48, paddingHorizontal: 3, alignItems: 'center', justifyContent: 'center', borderRadius: radius.pill, backgroundColor: on ? c.surface : 'transparent', borderWidth: on ? 1 : 0, borderColor: c.border }}>
            <Text numberOfLines={2} style={[font.small, { fontWeight: '700', color: on ? c.primary : c.textMuted, textAlign: 'center', flexShrink: 1 }]}>{o.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}
