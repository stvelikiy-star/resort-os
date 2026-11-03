import React from 'react';
import { View } from 'react-native';
import { Redirect, Tabs, usePathname } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { ClipboardCheck, BedDouble, ChartNoAxesCombined, CircleUserRound, Wrench, MessageCircle, CalendarDays, ConciergeBell, UtensilsCrossed } from 'lucide-react-native';
import { useSession } from '../../src/state/session';
import { useTheme } from '../../src/theme/ThemeProvider';
import { hasTabForSession, homeForSession, TabKey } from '../../src/roles/registry';
import { useMobileCopy } from '../../src/i18n/mobileCopy';
import { iconography, radius } from '../../src/theme/tokens';

const ICONS = {
  overview: ChartNoAxesCombined, reception: ConciergeBell, pms: CalendarDays, inbox: MessageCircle,
  dining: UtensilsCrossed, tasks: ClipboardCheck, rooms: BedDouble, requests: Wrench,
  admin: ChartNoAxesCombined, profile: CircleUserRound,
} as const;
const ORDER: TabKey[] = ['overview', 'reception', 'pms', 'inbox', 'dining', 'tasks', 'rooms', 'requests', 'admin', 'profile'];
export default function AppTabs() {
  const { user, api } = useSession();
  const pathname = usePathname();
  const copy = useMobileCopy();
  const { c } = useTheme();
  const insets = useSafeAreaInsets();
  if (!user) return <Redirect href="/connect" />;
  const mode = api?.mode ?? 'LIVE';
  const selected = pathname.split('/')[1] as TabKey;
  if (ORDER.includes(selected) && !hasTabForSession(user.role, user.module_permissions, mode, selected)) {
    return <Redirect href={homeForSession(user.role, user.module_permissions, mode)} />;
  }
  return <Tabs screenOptions={{
    headerShown: false,
    tabBarActiveTintColor: c.navActive, tabBarInactiveTintColor: c.navInactive,
    tabBarStyle: {
      backgroundColor: c.surface, borderTopColor: c.border, borderTopWidth: 1,
      height: 68 + Math.max(insets.bottom, 8), paddingTop: 6, paddingBottom: Math.max(insets.bottom, 8),
      elevation: 12, shadowColor: c.shadow, shadowOpacity: 0.13, shadowRadius: 24,
    },
    tabBarLabelStyle: { fontSize: 11, fontWeight: '700', letterSpacing: 0.1, marginTop: 1 },
  }}>
    {ORDER.map((key) => {
      const Icon = ICONS[key];
      return <Tabs.Screen key={key} name={key} options={{
        title: copy[key], href: hasTabForSession(user.role, user.module_permissions, mode, key) ? undefined : null,
        tabBarIcon: ({ color, focused }) =>
          <View style={{ minWidth: 50, height: 34, borderRadius: radius.pill, alignItems: 'center', justifyContent: 'center', backgroundColor: focused ? c.primarySoft : 'transparent' }}>
            <Icon size={iconography.nav} color={color} strokeWidth={focused ? iconography.strokeActive : iconography.stroke}/>
          </View>,
        tabBarButtonTestID: 'tab-' + key,
      }} />;
    })}
  </Tabs>;
}
