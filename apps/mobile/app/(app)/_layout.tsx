import React from 'react';
import { View } from 'react-native';
import { Redirect, Tabs, usePathname } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Grid2X2, ClipboardCheck, BedDouble, ChartNoAxesCombined, CircleUserRound, Wrench, MessageCircle, CalendarDays, ConciergeBell, UtensilsCrossed } from 'lucide-react-native';
import { useSession } from '../../src/state/session';
import { useTheme } from '../../src/theme/ThemeProvider';
import { hasTabForSession, homeForSession, workspaceForSession, TabKey } from '../../src/roles/registry';
import { mobileTabPlan } from '../../src/roles/navigation';
import { useMobileCopy } from '../../src/i18n/mobileCopy';
import { iconography, radius } from '../../src/theme/tokens';

const ICONS = {
  overview: ChartNoAxesCombined, reception: ConciergeBell, pms: CalendarDays, inbox: MessageCircle,
  dining: UtensilsCrossed, tasks: ClipboardCheck, rooms: BedDouble, requests: Wrench,
  admin: ChartNoAxesCombined, profile: CircleUserRound,
} as const;
const ORDER: TabKey[] = ['overview', 'reception', 'pms', 'inbox', 'dining', 'tasks', 'rooms', 'requests', 'admin', 'profile'];
export default function AppTabs() {
  const { user, api, serverAuthMode } = useSession();
  const pathname = usePathname();
  const copy = useMobileCopy();
  const { c } = useTheme();
  const insets = useSafeAreaInsets();
  if (!user) return <Redirect href="/connect" />;
  const mode = api?.mode ?? 'LIVE';
  const selected = pathname.split('/')[1] as TabKey | 'more';
  const workspace = workspaceForSession(user.role, user.module_permissions, mode, serverAuthMode);
  const plan = mobileTabPlan(workspace.tabs);
  if (selected === 'more' && !plan.showMore) return <Redirect href={homeForSession(user.role, user.module_permissions, mode, serverAuthMode)} />;
  if (selected !== 'more' && ORDER.includes(selected as TabKey) && !hasTabForSession(user.role, user.module_permissions, mode, selected, serverAuthMode)) {
    return <Redirect href={homeForSession(user.role, user.module_permissions, mode, serverAuthMode)} />;
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
        title: copy[key], href: workspace.tabs.includes(key) ? undefined : null,
        // Overflow routes remain registered in the navigator; only their tab buttons are hidden.
        // A null href here would make the screen unreachable from the More hub.
        tabBarButton: plan.overflow.includes(key) ? () => null : undefined,
        tabBarIcon: ({ color, focused }) =>
          <View style={{ minWidth: 50, height: 34, borderRadius: radius.pill, alignItems: 'center', justifyContent: 'center', backgroundColor: focused ? c.primarySoft : 'transparent' }}>
            <Icon size={iconography.nav} color={color} strokeWidth={focused ? iconography.strokeActive : iconography.stroke}/>
          </View>,
        tabBarButtonTestID: 'tab-' + key,
      }} />;
    })}
    <Tabs.Screen name="more" options={{
      title: copy.moreMenu, href: plan.showMore ? undefined : null,
      tabBarButtonTestID: 'tab-more',
      tabBarIcon: ({ color, focused }) => <View style={{ minWidth: 50, height: 34, borderRadius: radius.pill, alignItems: 'center', justifyContent: 'center', backgroundColor: focused ? c.primarySoft : 'transparent' }}><Grid2X2 size={iconography.nav} color={color} strokeWidth={focused ? iconography.strokeActive : iconography.stroke}/></View>,
    }}/>
  </Tabs>;
}
