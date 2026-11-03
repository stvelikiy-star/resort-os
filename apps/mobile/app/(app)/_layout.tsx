import React, { useEffect, useRef } from 'react';
import { Animated, View } from 'react-native';
import { Redirect, Tabs } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { ClipboardList, DoorOpen, LayoutDashboard, UserCircle, Wrench } from 'lucide-react-native';
import type { LucideIcon } from 'lucide-react-native';
import { useSession } from '../../src/state/session';
import { useTheme } from '../../src/theme/ThemeProvider';
import { hasTab, TabKey } from '../../src/roles/registry';

const ICONS = { tasks: ClipboardList, rooms: DoorOpen, requests: Wrench, admin: LayoutDashboard, profile: UserCircle } as const;
const ORDER: TabKey[] = ['tasks', 'rooms', 'requests', 'admin', 'profile'];

function AnimatedTabIcon({ Icon, focused, color, activeBackground }: { Icon: LucideIcon; focused: boolean; color: string; activeBackground: string }) {
  const scale = useRef(new Animated.Value(focused ? 1 : 0)).current;
  useEffect(() => {
    Animated.spring(scale, { toValue: focused ? 1 : 0, damping: 16, stiffness: 230, mass: 0.7, useNativeDriver: true }).start();
  }, [focused, scale]);
  return (
    <View style={{ width: 50, height: 37, alignItems: 'center', justifyContent: 'center' }}>
      <Animated.View style={{ position: 'absolute', width: 50, height: 35, borderRadius: 13, backgroundColor: activeBackground, opacity: scale, transform: [{ scale: scale.interpolate({ inputRange: [0, 1], outputRange: [0.65, 1] }) }] }} />
      <Animated.View style={{ transform: [{ scale: scale.interpolate({ inputRange: [0, 1], outputRange: [1, 1.12] }) }] }}>
        <Icon size={22} color={color} strokeWidth={focused ? 2.4 : 1.9} />
      </Animated.View>
    </View>
  );
}

export default function AppTabs() {
  const { user } = useSession();
  const { t } = useTranslation();
  const { c } = useTheme();
  if (!user) return <Redirect href="/connect" />;
  return (
    <Tabs screenOptions={{
      headerShown: false,
      tabBarActiveTintColor: c.primary, tabBarInactiveTintColor: c.textMuted,
      tabBarStyle: { backgroundColor: c.surface, borderTopColor: c.border, borderTopWidth: 1, height: 76, paddingTop: 6, paddingBottom: 9, shadowColor: c.shadow, shadowOpacity: 0.10, shadowRadius: 16, elevation: 10 },
      tabBarLabelStyle: { fontSize: 11, fontWeight: '700', letterSpacing: 0.15, marginTop: 1 },
    }}>
      {ORDER.map((k) => {
        const Icon = ICONS[k];
        return (
          <Tabs.Screen key={k} name={k}
            options={{
              title: t(`nav.${k}`),
              href: hasTab(user.role, k) ? undefined : null,
              tabBarIcon: ({ color, focused }) => <AnimatedTabIcon Icon={Icon} color={color} focused={focused} activeBackground={c.primarySoft} />,
              tabBarButtonTestID: `tab-${k}`,
            }} />
        );
      })}
    </Tabs>
  );
}
