import React from 'react';
import { Image, Text, View } from 'react-native';
import Svg, { Circle, Path } from 'react-native-svg';
import { LinearGradientFallback } from './gradient';
import { useTheme } from '../theme/ThemeProvider';
import { font, radius, space } from '../theme/tokens';

/** Existing compass-and-ship asset; original vector brand-master sign-off remains separate. */
const MARINA_SEAL = require('../../assets/marina-staff-app-icon.png');

export function Logo({ size = 56 }: { size?: number }) {
  return <Image source={MARINA_SEAL} style={{ width: size, height: size, borderRadius: size / 2 }} resizeMode="contain" accessibilityLabel="MARINA SMART" />;
}

/** One aligned brand lockup for all entry screens. Never replace the approved logo with a generated icon. */
export function BrandLockup({ size = 56, color = '#FFFFFF' }: { size?: number; color?: string }) {
  return <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12, minWidth: 0 }}>
    <Logo size={size}/>
    <View style={{ flexShrink: 1, justifyContent: 'center' }}><Wordmark color={color}/></View>
  </View>;
}

export function Hero({ children, height }: { children: React.ReactNode; height?: number }) {
  const { c } = useTheme();
  return <LinearGradientFallback style={{ borderRadius: radius.xl, padding: space.xl, minHeight: height ?? 184, overflow: 'hidden', borderWidth: 1, borderColor: c.glassBorder }}>
    <Svg pointerEvents="none" width={190} height={190} viewBox="0 0 190 190" style={{ position: 'absolute', top: -50, right: -47 }}>
      <Circle cx="95" cy="95" r="82" stroke={c.gold} strokeWidth="1.5" strokeOpacity="0.24" fill="none"/>
      <Circle cx="95" cy="95" r="63" stroke={c.cyan} strokeOpacity="0.26" fill="none" strokeWidth="1"/>
      <Circle cx="95" cy="95" r="42" stroke={c.gold} strokeOpacity="0.20" fill="none" strokeWidth="1"/>
      <Path d="M12 146 Q 95 50 180 110" stroke={c.cyan} strokeOpacity="0.28" fill="none"/>
    </Svg>
    {children}
  </LinearGradientFallback>;
}
export function Wordmark({ color }: { color: string }) {
  const { c, name } = useTheme();
  return <View style={{ flexDirection: 'row', alignItems: 'center', gap: 7 }}>
    <Text style={[font.h2, { color, letterSpacing: 1.3 }]}>MARINA</Text>
    <Text style={[font.h2, { color: name === 'light' ? c.warning : c.gold, letterSpacing: 1.3 }]}>SMART</Text>
  </View>;
}
