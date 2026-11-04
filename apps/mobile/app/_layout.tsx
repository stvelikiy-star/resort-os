import React from 'react';
import { Platform, View, useWindowDimensions } from 'react-native';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { ThemeProvider, useTheme } from '../src/theme/ThemeProvider';
import { SessionProvider } from '../src/state/session';
import { shouldFrameMobileWeb, WEB_MOBILE_PREVIEW_WIDTH } from '../src/theme/layout';

function Shell() {
  const { name, c } = useTheme();
  const { width } = useWindowDimensions();
  const framed = shouldFrameMobileWeb(Platform.OS, width);
  const navigation = <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: c.bg }, animation: 'fade_from_bottom' }}>
    <Stack.Screen name="task/[id]" options={{ presentation: 'card' }} />
    <Stack.Screen name="room/[id]" options={{ presentation: 'card' }} />
    <Stack.Screen name="new-request" options={{ presentation: 'modal' }} />
    <Stack.Screen name="scan" options={{ presentation: 'modal' }} />
    <Stack.Screen name="ai" options={{ presentation: 'modal' }} />
  </Stack>;
  return (
    <>
      <StatusBar style={name === 'dark' ? 'light' : 'dark'} />
      {Platform.OS === 'web' ? (
        <View style={{ flex: 1, backgroundColor: framed ? c.surfaceAlt : c.bg, alignItems: 'center', justifyContent: 'center', paddingVertical: framed ? 20 : 0 }}>
          <View testID="mobile-web-viewport" style={{ flex: 1, width: '100%', maxWidth: framed ? WEB_MOBILE_PREVIEW_WIDTH : undefined, maxHeight: framed ? 920 : undefined, borderRadius: framed ? 26 : 0, borderWidth: framed ? 1 : 0, borderColor: c.border, overflow: 'hidden', backgroundColor: c.bg }}>
            {navigation}
          </View>
        </View>
      ) : navigation}
    </>
  );
}

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <ThemeProvider>
        <SessionProvider>
          <Shell />
        </SessionProvider>
      </ThemeProvider>
    </SafeAreaProvider>
  );
}
