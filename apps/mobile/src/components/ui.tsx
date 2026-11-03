import React, { useEffect, useState } from 'react';
import { Animated, Easing, Pressable, ScrollView, StyleProp, StyleSheet, Text, TextInput, TextInputProps, View, ViewStyle } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTranslation } from 'react-i18next';
import * as Haptics from 'expo-haptics';
import { useTheme } from '../theme/ThemeProvider';
import { font, radius, space, TOUCH } from '../theme/tokens';
import type { LucideIcon } from 'lucide-react-native';

export function FadeIn({ children, delay = 0, style }: { children: React.ReactNode; delay?: number; style?: StyleProp<ViewStyle> }) {
  const [v] = useState(() => new Animated.Value(0));
  useEffect(() => { Animated.timing(v, { toValue: 1, duration: 320, delay, easing: Easing.out(Easing.cubic), useNativeDriver: true }).start(); }, [v, delay]);
  return <Animated.View style={[style, { opacity: v, transform: [{ translateY: v.interpolate({ inputRange: [0, 1], outputRange: [12, 0] }) }] }]}>{children}</Animated.View>;
}

const OUTER_KEYS = ['flex', 'flexGrow', 'flexShrink', 'flexBasis', 'width', 'alignSelf'] as const;

export function PressScale({ children, onPress, style, disabled, testID, accessibilityLabel }: { children: React.ReactNode; onPress?: () => void; style?: StyleProp<ViewStyle>; disabled?: boolean; testID?: string; accessibilityLabel?: string }) {
  const [s] = useState(() => new Animated.Value(1));
  const to = (x: number) => Animated.spring(s, { toValue: x, useNativeDriver: true, speed: 40, bounciness: 4 }).start();
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
    <Pressable testID={testID} accessibilityRole="button" accessibilityLabel={accessibilityLabel} disabled={disabled} style={outer as ViewStyle}
      onPressIn={() => to(0.97)} onPressOut={() => to(1)}
      onPress={() => { void Haptics.selectionAsync().catch(() => {}); onPress?.(); }}>
      <Animated.View style={[inner as ViewStyle, fill ? { flex: 1 } : null, { transform: [{ scale: s }], opacity: disabled ? 0.5 : 1 }]}>{children}</Animated.View>
    </Pressable>
  );
}

export function Screen({ children, scroll = true, padded = true }: { children: React.ReactNode; scroll?: boolean; padded?: boolean }) {
  const { c } = useTheme();
  const insets = useSafeAreaInsets();
  const pad = padded ? space.lg : 0;
  return (
    <View style={{ flex: 1, backgroundColor: c.bg }}>
      {scroll ? (
        <ScrollView style={{ flex: 1 }} contentContainerStyle={{ padding: pad, paddingTop: insets.top + space.md, paddingBottom: 120, gap: space.md }}>{children}</ScrollView>
      ) : (
        <View style={{ flex: 1, padding: pad, paddingTop: insets.top + space.md, gap: space.md }}>{children}</View>
      )}
    </View>
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
  const base: ViewStyle = { backgroundColor: c.surface, borderRadius: radius.lg, padding: space.lg, borderWidth: StyleSheet.hairlineWidth, borderColor: c.border, shadowColor: c.shadow, shadowOpacity: 0.08, shadowRadius: 14, shadowOffset: { width: 0, height: 6 }, elevation: 2 };
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

export function Badge({ label, tone = 'neutral', icon: Icon }: { label: string; tone?: Tone; icon?: LucideIcon }) {
  const { c } = useTheme();
  const t = toneColors(c, tone);
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: t.bg, paddingHorizontal: 10, paddingVertical: 5, borderRadius: radius.pill, alignSelf: 'flex-start' }}>
      {Icon ? <Icon size={13} color={t.fg} /> : null}
      <Text style={[font.label, { color: t.fg }]}>{label}</Text>
    </View>
  );
}

export function Button({ label, onPress, icon: Icon, variant = 'primary', disabled, testID }: { label: string; onPress: () => void; icon?: LucideIcon; variant?: 'primary' | 'secondary' | 'danger' | 'ghost'; disabled?: boolean; testID?: string }) {
  const { c } = useTheme();
  const bg = variant === 'primary' ? c.primary : variant === 'danger' ? c.danger : variant === 'secondary' ? c.primarySoft : 'transparent';
  const fg = variant === 'primary' ? c.primaryText : variant === 'danger' ? '#fff' : c.primary;
  return (
    <PressScale testID={testID} disabled={disabled} onPress={onPress} accessibilityLabel={label}
      style={{ minHeight: TOUCH, borderRadius: radius.md, backgroundColor: bg, paddingHorizontal: space.xl, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: space.sm }}>
      {Icon ? <Icon size={22} color={fg} /> : null}
      <Text style={[font.h2, { color: fg, fontSize: 17 }]}>{label}</Text>
    </PressScale>
  );
}

export function Field({ label, ...rest }: TextInputProps & { label: string }) {
  const { c } = useTheme();
  return (
    <View style={{ gap: 6 }}>
      <Text style={[font.label, { color: c.textMuted }]}>{label.toUpperCase()}</Text>
      <TextInput accessibilityLabel={label} placeholderTextColor={c.textMuted} {...rest}
        style={[{ minHeight: TOUCH, borderRadius: radius.md, borderWidth: 1.5, borderColor: c.border, backgroundColor: c.surface, color: c.text, paddingHorizontal: space.lg, fontSize: 17 }, rest.style]} />
    </View>
  );
}

export function SectionLabel({ children }: { children: React.ReactNode }) {
  const { c } = useTheme();
  return <Text style={[font.label, { color: c.textMuted, marginTop: space.sm }]}>{String(children).toUpperCase()}</Text>;
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
  return (
    <View style={{ flexDirection: 'row', backgroundColor: c.surfaceAlt, borderRadius: radius.md, padding: 4, gap: 4 }}>
      {options.map((o) => {
        const on = o.key === value;
        return (
          <PressScale key={o.key} onPress={() => onChange(o.key)} style={{ flex: 1, minHeight: 44, alignItems: 'center', justifyContent: 'center', borderRadius: radius.sm, backgroundColor: on ? c.surface : 'transparent' }} accessibilityLabel={o.label}>
            <Text style={[font.small, { fontWeight: '700', color: on ? c.primary : c.textMuted }]}>{o.label}</Text>
          </PressScale>
        );
      })}
    </View>
  );
}
