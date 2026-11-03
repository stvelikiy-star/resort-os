import React from 'react';
import { Text, View } from 'react-native';
import Svg, { Circle, Defs, LinearGradient, Path, Rect, Stop } from 'react-native-svg';
import { LinearGradientFallback } from './gradient';
import { font } from '../theme/tokens';

/** Brand geometry follows the M monogram in apps/web/public/brand/marina-smart-mark.svg.
 * It replaces the unrelated wave/key-tag illustration previously used in mobile.
 */
export function Logo({ size = 56 }: { size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 72 72" accessibilityLabel="MARINA SMART">
      <Defs>
        <LinearGradient id="marinaGold" x1="0" y1="0" x2="1" y2="1">
          <Stop offset="0" stopColor="#F5DEAB" />
          <Stop offset="1" stopColor="#B88A45" />
        </LinearGradient>
        <LinearGradient id="marinaNavy" x1="0" y1="0" x2="1" y2="1">
          <Stop offset="0" stopColor="#101D30" />
          <Stop offset="1" stopColor="#18515D" />
        </LinearGradient>
      </Defs>
      <Rect width="72" height="72" rx="20" fill="url(#marinaNavy)" />
      <Rect x="2" y="2" width="68" height="68" rx="18" stroke="#D4AE70" strokeOpacity=".28" fill="none" />
      <Path d="M13 53V19h10l13 15 13-15h10v34H49V34L36 49 23 34v19z" fill="none" stroke="url(#marinaGold)" strokeWidth="3.1" strokeLinejoin="round" />
    </Svg>
  );
}

export function Hero({ children, height }: { children: React.ReactNode; height?: number }) {
  return (
    <LinearGradientFallback style={{ borderRadius: 28, padding: 22, minHeight: height, overflow: 'hidden', borderWidth: 1, borderColor: 'rgba(212,174,112,0.30)' }}>
      <Svg pointerEvents="none" width="160" height="160" style={{ position: 'absolute', right: -38, top: -48 }} viewBox="0 0 160 160">
        <Circle cx="80" cy="80" r="72" stroke="#E5BF7B" strokeOpacity=".24" strokeWidth="1" fill="none" />
        <Circle cx="80" cy="80" r="52" stroke="#E5BF7B" strokeOpacity=".20" strokeWidth="1" fill="none" />
        <Circle cx="80" cy="80" r="32" stroke="#E5BF7B" strokeOpacity=".16" strokeWidth="1" fill="none" />
      </Svg>
      {children}
    </LinearGradientFallback>
  );
}
export const Wordmark = ({ color }: { color: string }) => <Text style={[font.h2, { color, letterSpacing: 2.2 }]}>MARINA SMART</Text>;
export const _v = View;
