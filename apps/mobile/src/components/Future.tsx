import React, { useEffect, useRef, useState } from 'react';
import { Animated, Easing, StyleProp, Text, TextStyle, View, ViewStyle } from 'react-native';
import { AlertCircle, ArrowUpRight, CircleHelp, CloudOff, LockKeyhole, Sparkles } from 'lucide-react-native';
import type { LucideIcon } from 'lucide-react-native';
import Svg, { Circle, Defs, LinearGradient, Path, Stop } from 'react-native-svg';
import { useTheme } from '../theme/ThemeProvider';
import { cappedStagger, useMotionAllowed, useMotionPreference } from '../theme/motion';
import { elevation, font, iconography, motion, radius, space } from '../theme/tokens';
import { Badge, Card, PressScale, Screen, Title } from './ui';
import { Logo } from './Brand';

export function FutureScreen({ children }: { children: React.ReactNode }) {
  const { c } = useTheme();
  return <Screen><View style={{ position: 'absolute', top: -100, right: -140, width: 320, height: 320, borderRadius: 160, backgroundColor: c.glow, opacity: 0.5 }} pointerEvents="none" />{children}</Screen>;
}
export function PremiumHeader({ title, subtitle, eyebrow, right }: { title: string; subtitle?: string; eyebrow?: string; right?: React.ReactNode }) {
  const { c } = useTheme();
  return <View style={{ flexDirection: 'row', alignItems: 'center', gap: space.md, paddingVertical: space.sm }}>
    <Logo size={50}/><View style={{ flex: 1, minWidth: 0, gap: 2 }}>
      {eyebrow ? <Text style={[font.label, { color: c.cyan }]}>{eyebrow.toUpperCase()}</Text> : null}
      <Title sub={subtitle}>{title}</Title>
    </View>{right}
  </View>;
}
export function GlassCard({ children, style, onPress, testID }: { children: React.ReactNode; style?: StyleProp<ViewStyle>; onPress?: () => void; testID?: string }) {
  const { c } = useTheme();
  return <Card testID={testID} onPress={onPress} style={[{ backgroundColor: c.glass, borderColor: c.glassBorder, borderWidth: 1, ...elevation.card }, style]}>{children}</Card>;
}
export function MetricCard({ icon: Icon, label, value, detail, onPress }: { icon: LucideIcon; label: string; value: string; detail?: string; onPress?: () => void }) {
  const { c } = useTheme();
  return <GlassCard onPress={onPress} style={{ flexGrow: 1, flexBasis: '46%', minWidth: 136, gap: 10, padding: 16 }}>
    <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
      <View style={{ width: 42, height: 42, borderRadius: 14, backgroundColor: c.primarySoft, alignItems: 'center', justifyContent: 'center' }}><Icon color={c.primary} size={iconography.metric}/></View>
      {onPress ? <ArrowUpRight size={18} color={c.textMuted}/> : null}
    </View>
    <Text style={[font.metric, { color: c.text }]} adjustsFontSizeToFit numberOfLines={1}>{value}</Text>
    <Text style={[font.small, { color: c.textMuted }]}>{label}</Text>
    {detail ? <Text style={[font.label, { color: c.cyan }]}>{detail}</Text> : null}
  </GlassCard>;
}
/** Real, server-sourced numeric KPI. Motion is disabled until OS preference is known. */
export function AnimatedKpi({ value, suffix = '', style, testID }: { value: number; suffix?: string; style?: StyleProp<TextStyle>; testID?: string }) {
  const allowed = useMotionAllowed();
  const safe = Number.isFinite(value) ? Math.max(0, value) : 0;
  const [shown, setShown] = useState(safe);
  const progress = useRef(new Animated.Value(safe)).current;
  const previous = useRef(safe);
  useEffect(() => {
    const from = previous.current;
    previous.current = safe;
    if (!allowed || from === safe) {
      progress.setValue(safe);
      setShown(safe);
      return;
    }
    progress.setValue(from);
    const subscription = progress.addListener(({ value: next }) => setShown(Math.round(next)));
    const anim = Animated.timing(progress, { toValue: safe, duration: motion.chart, easing: Easing.out(Easing.cubic), useNativeDriver: false });
    anim.start();
    return () => { anim.stop(); progress.removeListener(subscription); };
  }, [allowed, safe, progress]);
  return <Text testID={testID} accessibilityLabel={String(Math.round(safe)) + suffix} style={style}>{Math.round(shown)}{suffix}</Text>;
}

/** Chart showing only the confirmed platform occupancy percentage. Static numeric fallback. */
export function OccupancyRing({ percent, label }: { percent: number; label: string }) {
  const safe = Math.max(0, Math.min(100, Number.isFinite(percent) ? percent : 0));
  const circumference = 2 * Math.PI * 42;
  const length = circumference * safe / 100;
  return <View accessible accessibilityRole="progressbar" accessibilityLabel={label}
    accessibilityValue={{ min: 0, max: 100, now: Math.round(safe) }}
    style={{ width: 112, height: 112, justifyContent: 'center', alignItems: 'center' }}>
    <Svg pointerEvents="none" width={112} height={112} viewBox="0 0 112 112">
      <Circle cx="56" cy="56" r="42" fill="none" stroke="rgba(255,255,255,0.22)" strokeWidth="8"/>
      <Circle cx="56" cy="56" r="42" fill="none" stroke="#00D8FF" strokeWidth="8"
        strokeLinecap="round" strokeDasharray={`${length} ${circumference}`} transform="rotate(-90 56 56)"/>
    </Svg>
    <View pointerEvents="none" style={{ position: 'absolute', alignItems: 'center', justifyContent: 'center' }}>
      <Text style={[font.h2, { color: '#FFFFFF', fontSize: 22 }]}>{Math.round(safe)}%</Text>
    </View>
  </View>;
}
export function QuickAction({ icon: Icon, label, onPress, testID }: { icon: LucideIcon; label: string; onPress: () => void; testID?: string }) {
  const { c } = useTheme();
  return <PressScale onPress={onPress} testID={testID} accessibilityLabel={label} style={{ minHeight: 72, flexDirection: 'row', alignItems: 'center', gap: space.md, paddingHorizontal: space.lg, borderRadius: radius.lg, backgroundColor: c.primarySoft, borderWidth: 1, borderColor: c.border }}>
    <View style={{ width: 44, height: 44, borderRadius: 14, backgroundColor: c.surface, alignItems: 'center', justifyContent: 'center' }}><Icon color={c.primary} size={22}/></View>
    <Text style={[font.h2, { color: c.text, flex: 1 }]}>{label}</Text><ArrowUpRight color={c.primary} size={20}/>
  </PressScale>;
}
export function StatusPill({ label, tone = 'primary' }: { label: string; tone?: 'primary' | 'success' | 'warning' | 'danger' | 'info' }) {
  return <Badge label={label} tone={tone} />;
}
export function PermissionDenied({ text }: { text: string }) {
  const { c } = useTheme();
  return <GlassCard style={{ gap: 10, alignItems: 'center', padding: space.xl }}><LockKeyhole size={32} color={c.warning}/><Text style={[font.body, { color: c.text, textAlign: 'center' }]}>{text}</Text></GlassCard>;
}
export function OfflineBanner({ text }: { text: string }) {
  const { c } = useTheme();
  return <View accessibilityRole="alert" style={{ padding: space.md, borderRadius: radius.md, backgroundColor: c.warningSoft, flexDirection: 'row', gap: 10, alignItems: 'center' }}>
    <CloudOff size={22} color={c.warning}/><Text style={[font.small, { color: c.warning, flex: 1 }]}>{text}</Text>
  </View>;
}
export function ErrorState({ text, retry, onRetry }: { text: string; retry: string; onRetry: () => void }) {
  const { c } = useTheme();
  return <GlassCard style={{ alignItems: 'center', gap: 10 }}>
    <AlertCircle size={30} color={c.danger}/><Text style={[font.body, { color: c.text, textAlign: 'center' }]}>{text}</Text>
    <PressScale accessibilityLabel={retry} onPress={onRetry} style={{ minHeight: 48, justifyContent: 'center', paddingHorizontal: 22, backgroundColor: c.primarySoft, borderRadius: radius.pill }}>
      <Text style={[font.body, { color: c.primary }]}>{retry}</Text>
    </PressScale>
  </GlassCard>;
}
export function LoadingShimmer({ count = 3 }: { count?: number }) {
  const { c } = useTheme();
  const allowed = useMotionAllowed();
  const [alpha] = useState(() => new Animated.Value(0.65));
  useEffect(() => {
    if (!allowed) { alpha.setValue(0.85); return; }
    const animation = Animated.loop(Animated.sequence([
      Animated.timing(alpha, { toValue: 1, duration: 650, useNativeDriver: true, easing: Easing.inOut(Easing.quad) }),
      Animated.timing(alpha, { toValue: 0.65, duration: 650, useNativeDriver: true, easing: Easing.inOut(Easing.quad) }),
    ]));
    animation.start();
    return () => animation.stop();
  }, [allowed, alpha]);
  return <View accessibilityLabel="Loading" style={{ gap: space.md }}>
    {Array.from({ length: Math.min(count, 6) }, (_, i) => <Animated.View key={i} style={{ opacity: alpha, borderRadius: radius.lg, height: 84, backgroundColor: c.surfaceAlt, borderWidth: 1, borderColor: c.border }} />)}
  </View>;
}
/** Accessible, state-driven visual only. Mic permission/audio are NOT simulated. */
export type AIOrbState = 'idle' | 'processing' | 'error' | 'offline';
export function AIOrb({ state = 'idle', size = 76, label, onPress }: { state?: AIOrbState; size?: number; label: string; onPress?: () => void }) {
  const { c } = useTheme();
  const allowed = useMotionAllowed();
  const [progress] = useState(() => new Animated.Value(0));
  useEffect(() => {
    if (!allowed || state !== 'processing') { progress.setValue(0); return; }
    const loop = Animated.loop(Animated.timing(progress, { toValue: 1, duration: 1700, useNativeDriver: true }));
    loop.start(); return () => loop.stop();
  }, [allowed, progress, state]);
  const ring = state === 'error' ? c.danger : state === 'offline' ? c.textMuted : c.cyan;
  return <PressScale disabled={!onPress} onPress={onPress} accessibilityLabel={label} style={{ width: size + 16, height: size + 16, justifyContent: 'center', alignItems: 'center' }}>
    <Animated.View style={{ position: 'absolute', transform: [{ rotate: progress.interpolate({ inputRange: [0, 1], outputRange: ['0deg', '360deg'] }) }] }}>
      <Svg width={size + 16} height={size + 16} viewBox="0 0 100 100">
        <Defs><LinearGradient id="orbRing" x1="0" x2="1" y1="0" y2="1"><Stop offset="0" stopColor={ring}/><Stop offset="1" stopColor={c.iris}/></LinearGradient></Defs>
        <Circle cx="50" cy="50" r="45" stroke="url(#orbRing)" strokeWidth="2.5" strokeOpacity="0.85" fill="none" />
        <Circle cx="50" cy="50" r="36" stroke={ring} strokeOpacity="0.28" strokeWidth="1.5" fill="none"/>
        <Path d="M 28 45 Q 50 12 72 45 Q 82 75 50 82 Q 18 72 28 45 Z" fill={c.primarySoft} stroke={ring} strokeWidth="2"/>
      </Svg>
    </Animated.View>
    {state === 'error' || state === 'offline' ? <CircleHelp size={size / 3} color={ring}/> : <Sparkles size={size / 3} color={ring}/>}
  </PressScale>;
}
export function StaggerItem({ index, children }: { index: number; children: React.ReactNode }) {
  const { allowed, ready } = useMotionPreference();
  const [fade] = useState(() => new Animated.Value(0));
  const appeared = useRef(false);
  useEffect(() => {
    if (!ready) return;
    if (appeared.current || !allowed) {
      appeared.current = true;
      fade.setValue(1);
      return;
    }
    appeared.current = true;
    fade.setValue(0);
    const animation = Animated.timing(fade, { toValue: 1, duration: motion.card, delay: cappedStagger(index), useNativeDriver: true });
    animation.start(); return () => animation.stop();
  }, [allowed, ready, fade, index]);
  return <Animated.View style={{ opacity: fade, transform: [{ translateY: fade.interpolate({ inputRange: [0, 1], outputRange: [12, 0] }) }] }}>{children}</Animated.View>;
}
