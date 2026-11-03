import React from 'react';
import { StyleProp, View, ViewStyle } from 'react-native';
import Svg, { Defs, LinearGradient, Rect, Stop } from 'react-native-svg';
import { useTheme } from '../theme/ThemeProvider';

/** Gradient background without extra native deps: SVG absolutely positioned behind children. */
export function LinearGradientFallback({ children, style }: { children: React.ReactNode; style?: StyleProp<ViewStyle> }) {
  const { c } = useTheme();
  return (
    <View style={style}>
      <Svg style={{ position: 'absolute', left: 0, top: 0, right: 0, bottom: 0 }} width="100%" height="100%" preserveAspectRatio="none">
        <Defs><LinearGradient id="hero" x1="0" y1="0" x2="1" y2="1"><Stop offset="0" stopColor={c.heroFrom} /><Stop offset="1" stopColor={c.heroTo} /></LinearGradient></Defs>
        <Rect width="100%" height="100%" fill="url(#hero)" />
      </Svg>
      {children}
    </View>
  );
}
