import React, { useEffect, useState } from 'react';
import { Animated, Easing, StyleProp, Text, TextStyle, View, ViewStyle, useWindowDimensions } from 'react-native';
import { AlertCircle, ArrowUpRight, CircleHelp, CloudOff, LockKeyhole, Sparkles } from 'lucide-react-native';
import type { LucideIcon } from 'lucide-react-native';
import Svg, { Circle, Defs, LinearGradient, Path, Stop } from 'react-native-svg';
import { useTheme } from '../theme/ThemeProvider';
import { cappedStagger, motionPresets, useAnimatedNumber, useMotionAllowed, useRevealProgress } from '../theme/motion';
import { elevation, font, iconography, motion, radius, space } from '../theme/tokens';
import { Badge, Card, PressScale, Screen, Title } from './ui';
import { Logo } from './Brand';
import { metricNeedsFullWidth } from '../theme/layout';

export function FutureScreen({ children }: { children: React.ReactNode }) {
  const { c } = useTheme();
  return <Screen>
    <View pointerEvents="none" style={{ position: 'absolute', top: -110, right: -140, width: 340, height: 340, borderRadius: 170,
      backgroundColor: c.glow, opacity: 0.52 }}/>
    <View pointerEvents="none" style={{ position: 'absolute', top: 120, left: -158, width: 280, height: 280, borderRadius: 140,
      backgroundColor: c.primarySoft, opacity: 0.22 }}/>
    {children}
  </Screen>;
}
export function PremiumHeader({ title, subtitle, eyebrow, right, inlineCompactRight = false }: { title: string; subtitle?: string; eyebrow?: string; right?: React.ReactNode; inlineCompactRight?: boolean }) {
  const { c } = useTheme();
  const { width, fontScale } = useWindowDimensions();
  const compact = !!right && (width < 375 || fontScale > 1.25);
  const stackRight = compact && !inlineCompactRight;
  return <View style={{
    flexDirection: stackRight ? 'column' : 'row',
    alignItems: stackRight ? 'stretch' : 'center', gap: space.md,
    marginBottom: 2, paddingHorizontal: 15, paddingVertical: 13,
    borderRadius: radius.lg, backgroundColor: c.glass,
    borderWidth: 1, borderColor: c.glassBorder,
    shadowColor: c.shadow, shadowOpacity: 0.07, shadowRadius: 14,
    shadowOffset: { width: 0, height: 5 }, elevation: 2, overflow: 'hidden',
  }}>
    <View pointerEvents="none" style={{ position: 'absolute', left: 20, right: 20, top: 0, height: 2,
      borderRadius: 1, backgroundColor: c.cyan, opacity: 0.6 }}/>
    <View pointerEvents="none" style={{ position: 'absolute', right: -55, top: -85, width: 174, height: 174,
      borderRadius: 87, backgroundColor: c.primarySoft, opacity: 0.32 }}/>
    <View style={{ flexDirection: 'row', gap: space.md, alignItems: 'center', flex: stackRight ? undefined : 1, minWidth: 0 }}>
      <Logo size={width < 350 ? 42 : 50}/>
      <View style={{ flex: 1, minWidth: 0, gap: 2 }}>
        {eyebrow ? <Text style={[font.label, { color: c.cyan }]} numberOfLines={2}>{eyebrow.toUpperCase()}</Text> : null}
        <Title sub={subtitle}>{title}</Title>
      </View>
    </View>
    {right ? <View style={{ alignSelf: stackRight ? 'flex-end' : 'center', flexShrink: 0 }}>{right}</View> : null}
  </View>;
}
export function GlassCard({ children, style, onPress, testID }: { children: React.ReactNode; style?: StyleProp<ViewStyle>; onPress?: () => void; testID?: string }) {
  const { c } = useTheme();
  return <Card testID={testID} onPress={onPress} style={[{
    backgroundColor: c.glass, borderColor: c.glassBorder, borderWidth: 1,
    borderRadius: radius.lg, shadowColor: c.shadow, ...elevation.card,
    overflow: 'hidden',
  }, style]}>{children}</Card>;
}
export type MetricTone = 'primary' | 'gold' | 'cyan' | 'success' | 'warning';
export function MetricCard({ icon: Icon, label, value, detail, onPress, tone = 'primary' }: {
  icon: LucideIcon; label: string; value: string; detail?: string; onPress?: () => void; tone?: MetricTone;
}) {
  const { c } = useTheme();
  const { width, fontScale } = useWindowDimensions();
  const oneColumn = metricNeedsFullWidth(width, fontScale, value);
  const accent = tone === 'gold' ? c.gold : tone === 'cyan' ? c.cyan : tone === 'success' ? c.success : tone === 'warning' ? c.warning : c.primary;
  const soft = tone === 'gold' || tone === 'warning' ? c.warningSoft : tone === 'success' ? c.successSoft : tone === 'cyan' ? c.infoSoft : c.primarySoft;
  return <GlassCard onPress={onPress} style={{
    flexGrow: 1, flexBasis: oneColumn ? '100%' : '46%', minWidth: 0,
    gap: 10, minHeight: 174, padding: 17, borderTopWidth: 3, borderTopColor: accent,
  }}>
    <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
      <View style={{ width: 48, height: 48, borderRadius: 16, backgroundColor: soft,
        borderWidth: 1, borderColor: c.glassBorder, alignItems: 'center', justifyContent: 'center' }}>
        <Icon color={accent} size={iconography.metric + 2} strokeWidth={1.9}/>
      </View>
      {onPress ? <ArrowUpRight size={21} color={accent}/> : null}
    </View>
    <Text style={[font.metric, { color: c.text, flexShrink: 1, fontSize: oneColumn ? 32 : 29 }]}
      adjustsFontSizeToFit minimumFontScale={0.7} numberOfLines={oneColumn ? 2 : 1}>{value}</Text>
    <Text style={[font.small, { color: c.textMuted, flexShrink: 1, fontWeight: '600' }]}>{label}</Text>
    {detail ? <Text style={[font.small, { color: c.info }]}>{detail}</Text> : null}
  </GlassCard>;
}
/** Real, server-sourced numeric KPI. Counts up once when verified data first appears and
 * between later server values; Reduced Motion shows the exact value immediately. */
export function AnimatedKpi({ value, suffix = '', style, testID }: { value: number; suffix?: string; style?: StyleProp<TextStyle>; testID?: string }) {
  const safe = Number.isFinite(value) ? Math.max(0, value) : 0;
  const shown = useAnimatedNumber(safe);
  return <Text testID={testID} accessibilityLabel={String(Math.round(safe)) + suffix} style={style}>{Math.round(shown)}{suffix}</Text>;
}

/** Chart showing only the confirmed platform occupancy percentage. The arc sweeps once when the
 * verified value first appears; accessibility always reports the exact server value. */
export function OccupancyRing({ percent, label, size = 112 }: { percent: number; label: string; size?: number }) {
  const { c } = useTheme();
  const safe = Math.max(0, Math.min(100, Number.isFinite(percent) ? percent : 0));
  const shown = Math.max(0, Math.min(100, useAnimatedNumber(safe)));
  const circumference = 2 * Math.PI * 42;
  const length = circumference * shown / 100;
  return <View accessible accessibilityRole="progressbar" accessibilityLabel={label}
    accessibilityValue={{ min: 0, max: 100, now: Math.round(safe) }}
    style={{ width: size, height: size, justifyContent: 'center', alignItems: 'center' }}>
    <Svg pointerEvents="none" width={size} height={size} viewBox="0 0 112 112">
      <Circle cx="56" cy="56" r="42" fill="none" stroke={c.border} strokeWidth="8"/>
      <Circle cx="56" cy="56" r="42" fill="none" stroke={c.cyan} strokeWidth="8"
        strokeLinecap="round" strokeDasharray={`${length} ${circumference}`} transform="rotate(-90 56 56)"/>
    </Svg>
    <View pointerEvents="none" style={{ position: 'absolute', alignItems: 'center', justifyContent: 'center' }}>
      <Text style={[font.h2, { color: c.text, fontSize: 22 }]}>{Math.round(shown)}%</Text>
    </View>
  </View>;
}
export function QuickAction({ icon: Icon, label, onPress, testID }: { icon: LucideIcon; label: string; onPress: () => void; testID?: string }) {
  const { c } = useTheme();
  return <PressScale onPress={onPress} testID={testID} accessibilityLabel={label} style={{ minHeight: 72,
    flexDirection: 'row', alignItems: 'center', gap: space.md, paddingHorizontal: space.lg,
    borderRadius: radius.lg, backgroundColor: c.glass, borderWidth: 1, borderColor: c.glassBorder,
    shadowColor: c.shadow, ...elevation.card }}>
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
/** Pulses a bounded number of times, then settles static: a request that hangs offline must not
 * leave an endless decorative animation running. */
export function LoadingShimmer({ count = 3 }: { count?: number }) {
  const { c } = useTheme();
  const allowed = useMotionAllowed();
  const [alpha] = useState(() => new Animated.Value(0.65));
  useEffect(() => {
    if (!allowed) { alpha.setValue(0.85); return; }
    const animation = Animated.loop(Animated.sequence([
      Animated.timing(alpha, { toValue: 1, duration: 650, useNativeDriver: true, easing: Easing.inOut(Easing.quad) }),
      Animated.timing(alpha, { toValue: 0.65, duration: 650, useNativeDriver: true, easing: Easing.inOut(Easing.quad) }),
    ]), { iterations: motion.maxShimmerPulses });
    animation.start(({ finished }) => { if (finished) alpha.setValue(0.85); });
    return () => { animation.stop(); alpha.setValue(0.85); };
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
    // Real request in flight only, and bounded: a hung request must not spin forever.
    const loop = Animated.loop(Animated.timing(progress, { toValue: 1, duration: 1700, useNativeDriver: true }), { iterations: motion.maxOrbTurns });
    loop.start(({ finished }) => { if (finished) progress.setValue(0); });
    return () => loop.stop();
  }, [allowed, progress, state]);
  const ring = state === 'error' ? c.danger : state === 'offline' ? c.textMuted : c.cyan;
  return <PressScale disabled={!onPress} dimWhenDisabled={false} onPress={onPress} accessibilityLabel={label} style={{ width: size + 16, height: size + 16, justifyContent: 'center', alignItems: 'center' }}>
    <Animated.View style={{ position: 'absolute', transform: [{ rotate: progress.interpolate({ inputRange: [0, 1], outputRange: ['0deg', '360deg'] }) }] }}>
      <Svg width={size + 16} height={size + 16} viewBox="0 0 100 100">
        <Defs><LinearGradient id="orbRing" x1="0" x2="1" y1="0" y2="1"><Stop offset="0" stopColor={ring}/><Stop offset="1" stopColor={c.iris}/></LinearGradient></Defs>
        <Circle cx="50" cy="50" r="45" stroke="url(#orbRing)" strokeWidth="2.5" strokeOpacity="0.85" fill="none" />
        <Circle cx="50" cy="50" r="36" stroke={ring} strokeOpacity="0.28" strokeWidth="1.5" fill="none"/>
        <Path d="M 28 45 Q 50 12 72 45 Q 82 75 50 82 Q 18 72 28 45 Z" fill={c.primarySoft} stroke={ring} strokeWidth="2"/>
      </Svg>
    </Animated.View>
    <View style={{ width: size * 0.56, height: size * 0.56, borderRadius: size * 0.28, backgroundColor: c.primarySoft,
      alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: c.glassBorder }}>
      {state === 'error' ? <CircleHelp size={Math.max(20, size * 0.30)} color={c.danger}/>
        : <Sparkles size={Math.max(20, size * 0.34)} color={state === 'offline' ? c.textMuted : c.cyan} strokeWidth={2.1}/>}
    </View>
  </PressScale>;
}
export function PremiumEntrance({ index = 0, children, distance = 12, scaleFrom = 1 }: {
  index?: number; children: React.ReactNode; distance?: number; scaleFrom?: number;
}) {
  const progress = useRevealProgress(cappedStagger(index), motionPresets.entrance.duration);
  return <Animated.View style={{
    opacity: progress,
    transform: [
      { translateY: progress.interpolate({ inputRange: [0, 1], outputRange: [distance, 0] }) },
      { scale: progress.interpolate({ inputRange: [0, 1], outputRange: [scaleFrom, 1] }) },
    ],
  }}>{children}</Animated.View>;
}

export function StaggerItem({ index, children }: { index: number; children: React.ReactNode }) {
  return <PremiumEntrance index={index}>{children}</PremiumEntrance>;
}
