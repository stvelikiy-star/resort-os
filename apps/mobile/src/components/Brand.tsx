import React from 'react';
import { Image, Text, View } from 'react-native';
import { LinearGradientFallback } from './gradient';
import { font } from '../theme/tokens';

/**
 * The MARINA SMART compass-and-ship seal, cropped from the approved project artwork.
 * Embedded to keep Expo native/web self-contained and avoid remote image dependencies.
 */
const APPROVED_SEAL = require('../../assets/marina-compass-seal.png');

export function Logo({ size = 56 }: { size?: number }) {
  return <Image source={APPROVED_SEAL} style={{ width: size, height: size, borderRadius: size / 2 }} resizeMode="contain" accessibilityLabel="MARINA SMART — компас и корабль" />;
}

export function Hero({ children, height }: { children: React.ReactNode; height?: number }) {
  return <LinearGradientFallback style={{ borderRadius: 28, padding: 22, minHeight: height, overflow: 'hidden' }}>{children}</LinearGradientFallback>;
}
export const Wordmark = ({ color }: { color: string }) => <Text style={[font.h2, { color, letterSpacing: 1.7 }]}>MARINA SMART <Text style={{ fontSize: 12, fontWeight: '600' }}>STAFF</Text></Text>;
export const _v = View;
