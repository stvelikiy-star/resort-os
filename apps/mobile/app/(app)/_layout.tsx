import React from 'react';
import { View, useWindowDimensions } from 'react-native';
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
  const { user, api, serverAuthMode, locale } = useSession();
  const pathname = usePathname();
  const copy = useMobileCopy();
  const { c } = useTheme();
  const insets = useSafeAreaInsets();
  const { width, fontScale } = useWindowDimensions();
  const compact = width < 355 || fontScale > 1.35;
  const tabTitle = (key: TabKey) => {
    if (key === 'overview' && compact) return copy.homeShort;
    if (key === 'pms') return compact && locale === 'kg' ? 'Брон' : copy.pmsTabShort;
    if (key === 'admin') return copy.teamShort;
    if (key === 'tasks' && (locale === 'kg' || locale === 'kz')) return copy.tasksTabShort;
    if (key === 'rooms' && (locale === 'kg' || locale === 'kz')) return copy.roomsTabShort;
    if (key === 'requests' && (compact || locale === 'kz')) return copy.repairShort;
    return copy[key];
  };
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
        title: copy[key], tabBarLabel: tabTitle(key),
        // Keep overflow routes registered and navigable from More, but remove
        // their tab-bar slots entirely. A null button alone left empty flex
        // slots and compressed visible labels to "Об..." on 375 px phones.
        tabBarButton: !plan.primary.includes(key) ? () => null : undefined,
        tabBarItemStyle: plan.primary.includes(key)
          ? { flex: 1, minWidth: 0 }
          : { display: 'none', width: 0, flex: 0 },
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
