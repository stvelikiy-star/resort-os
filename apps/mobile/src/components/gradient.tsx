import React from 'react';
import { StyleProp, View, ViewStyle } from 'react-native';
import Svg, { Circle, Defs, LinearGradient, Path, Rect, Stop } from 'react-native-svg';
import { useTheme } from '../theme/ThemeProvider';

/** Lightweight SVG gradient; no blur passes or external assets/native dependencies. */
export function LinearGradientFallback({ children, style }: { children: React.ReactNode; style?: StyleProp<ViewStyle> }) {
  const { c } = useTheme();
  return <View style={style}>
    <Svg pointerEvents="none" style={{ position: 'absolute', left: 0, top: 0, right: 0, bottom: 0 }} width="100%" height="100%" viewBox="0 0 380 220" preserveAspectRatio="xMidYMid slice">
      <Defs><LinearGradient id="marina_future_hero" x1="0" y1="0" x2="1" y2="1">
        <Stop offset="0" stopColor={c.heroFrom}/>
        <Stop offset="0.55" stopColor="#123E64"/>
        <Stop offset="1" stopColor={c.heroTo}/>
      </LinearGradient></Defs>
      <Rect width="380" height="220" fill="url(#marina_future_hero)"/>
      <Circle cx="360" cy="-6" r="133" fill="none" stroke={c.cyan} strokeOpacity="0.12" strokeWidth="1.5"/>
      <Circle cx="360" cy="-6" r="99" fill="none" stroke={c.gold} strokeOpacity="0.20" strokeWidth="1"/>
      <Path d="M0 210 Q 125 122 240 163 T 390 153" fill="none" stroke={c.cyan} strokeOpacity="0.14" strokeWidth="1.5"/>
    </Svg>
    {children}
  </View>;
}
