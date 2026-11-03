import React from 'react';
import { StyleProp, View, ViewStyle } from 'react-native';
import Svg, { Circle, Defs, LinearGradient, Path, Rect, Stop } from 'react-native-svg';
import { useTheme } from '../theme/ThemeProvider';

/** Midnight-blue MARINA hero with subtle silver navigation lines. Pure SVG: no new native dependency. */
export function LinearGradientFallback({ children, style }: { children: React.ReactNode; style?: StyleProp<ViewStyle> }) {
  const { c } = useTheme();
  return (
    <View style={style}>
      <Svg style={{ position: 'absolute', left: 0, top: 0, right: 0, bottom: 0 }} width="100%" height="100%" viewBox="0 0 380 240" preserveAspectRatio="xMidYMid slice">
        <Defs>
          <LinearGradient id="marinaHero" x1="0" y1="0" x2="1" y2="1">
            <Stop offset="0" stopColor={c.heroFrom} />
            <Stop offset="0.58" stopColor="#103867" />
            <Stop offset="1" stopColor={c.heroTo} />
          </LinearGradient>
        </Defs>
        <Rect width="380" height="240" fill="url(#marinaHero)" />
        <Circle cx="365" cy="-10" r="135" stroke="#E1EBF7" strokeOpacity="0.16" strokeWidth="1" fill="none" />
        <Circle cx="365" cy="-10" r="103" stroke="#E1EBF7" strokeOpacity="0.12" strokeWidth="1" fill="none" />
        <Circle cx="365" cy="-10" r="72" stroke="#E1EBF7" strokeOpacity="0.13" strokeWidth="1" fill="none" />
        <Path d="M165 244 Q285 165 395 190" stroke="#D6E6F8" strokeOpacity="0.16" strokeWidth="1.5" fill="none" />
        <Path d="M205 252 Q315 197 398 217" stroke="#D6E6F8" strokeOpacity="0.12" strokeWidth="1.5" fill="none" />
      </Svg>
      {children}
    </View>
  );
}
