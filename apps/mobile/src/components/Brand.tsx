import React from 'react';
import { Image, Text, View } from 'react-native';
import { LinearGradientFallback } from './gradient';
import { font } from '../theme/tokens';

/**
 * The MARINA SMART compass-and-ship seal, cropped from the approved project artwork.
 * Embedded to keep Expo native/web self-contained and avoid remote image dependencies.
 */
const APPROVED_SEAL = 'data:image/png;base64,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';

export function Logo({ size = 56 }: { size?: number }) {
  return <Image source={{ uri: APPROVED_SEAL }} style={{ width: size, height: size, borderRadius: size / 2 }} resizeMode="contain" accessibilityLabel="MARINA SMART — компас и корабль" />;
}

export function Hero({ children, height }: { children: React.ReactNode; height?: number }) {
  return <LinearGradientFallback style={{ borderRadius: 28, padding: 22, minHeight: height, overflow: 'hidden' }}>{children}</LinearGradientFallback>;
}
export const Wordmark = ({ color }: { color: string }) => <Text style={[font.h2, { color, letterSpacing: 1.7 }]}>MARINA SMART <Text style={{ fontSize: 12, fontWeight: '600' }}>STAFF</Text></Text>;
export const _v = View;
