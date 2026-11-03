import React from 'react';
import { Text, View } from 'react-native';
import Svg, { Defs, LinearGradient, Path, Rect, Stop } from 'react-native-svg';
import { LinearGradientFallback } from './gradient';
import { font } from '../theme/tokens';

/** Original MARINA STAFF mark: stylised wave over a key-tag. */
export function Logo({ size = 56 }: { size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 64 64" accessibilityLabel="MARINA STAFF">
      <Defs><LinearGradient id="g" x1="0" y1="0" x2="1" y2="1"><Stop offset="0" stopColor="#0B5F66" /><Stop offset="1" stopColor="#14C2BC" /></LinearGradient></Defs>
      <Rect width="64" height="64" rx="18" fill="url(#g)" />
      <Path d="M10 38c6-8 10-8 16 0s10 8 16 0 8-6 12-3" stroke="#fff" strokeWidth="4" strokeLinecap="round" fill="none" />
      <Path d="M10 26c6-8 10-8 16 0s10 8 16 0 8-6 12-3" stroke="#E9B872" strokeWidth="4" strokeLinecap="round" fill="none" />
    </Svg>
  );
}

export function Hero({ children, height }: { children: React.ReactNode; height?: number }) {
  return <LinearGradientFallback style={{ borderRadius: 26, padding: 20, minHeight: height, overflow: 'hidden' }}>{children}</LinearGradientFallback>;
}
export const Wordmark = ({ color }: { color: string }) => <Text style={[font.h2, { color, letterSpacing: 2 }]}>MARINA STAFF</Text>;
export const _v = View;
