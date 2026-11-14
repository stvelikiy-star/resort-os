import React from 'react';
import { Easing, useWindowDimensions } from 'react-native';
import { Redirect, Tabs, usePathname } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Grid2X2 } from 'lucide-react-native';
import { useSession } from '../../src/state/session';
import { useTheme } from '../../src/theme/ThemeProvider';
import { hasTabForSession, homeForSession, workspaceForSession, TabKey } from '../../src/roles/registry';
import { mobileTabPlan } from '../../src/roles/navigation';
import { useMobileCopy } from '../../src/i18n/mobileCopy';
import { motion } from '../../src/theme/tokens';
import { useMotionAllowed } from '../../src/theme/motion';
import { TabIcon } from '../../src/components/Motion';
import { moduleIcons } from '../../src/theme/moduleIcons';

const ORDER: TabKey[] = ['overview', 'reception', 'pms', 'inbox', 'dining', 'kitchen', 'tasks', 'rooms', 'requests', 'admin', 'profile'];
export default function AppTabs() {
  const { user, api, serverAuthMode, locale } = useSession();
  const pathname = usePathname();
  const copy = useMobileCopy();
  const { c } = useTheme();
  const insets = useSafeAreaInsets();
  const { width, fontScale } = useWindowDimensions();
  const motionAllowed = useMotionAllowed();
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
    // Short cross-fade between tab scenes; none under Reduce Motion. Tab set and routes are unchanged.
    animation: motionAllowed ? 'fade' : 'none',
    transitionSpec: { animation: 'timing', config: { duration: motion.tab, easing: Easing.out(Easing.cubic) } },
    tabBarActiveTintColor: c.navActive, tabBarInactiveTintColor: c.navInactive,
    tabBarStyle: {
      backgroundColor: c.glass, borderTopColor: c.glassBorder, borderTopWidth: 1,
      borderTopLeftRadius: 22, borderTopRightRadius: 22, paddingHorizontal: 4,
      height: 76 + Math.max(insets.bottom, 8), paddingTop: 9, paddingBottom: Math.max(insets.bottom, 8),
      elevation: 12, shadowColor: c.shadow, shadowOpacity: 0.17, shadowRadius: 24,
    },
    tabBarLabelStyle: { fontSize: 11, fontWeight: '700', letterSpacing: 0.1, marginTop: 3 },
  }}>
    {ORDER.map((key) => {
      const Icon = moduleIcons[key];
      return <Tabs.Screen key={key} name={key} options={{
        title: copy[key], tabBarLabel: tabTitle(key),
        // Keep overflow routes registered and navigable from More, but remove
        // their tab-bar slots entirely. A null button alone left empty flex
        // slots and compressed visible labels to "Об..." on 375 px phones.
        tabBarButton: !plan.primary.includes(key) ? () => null : undefined,
        tabBarItemStyle: plan.primary.includes(key)
          ? { flex: 1, minWidth: 0 }
          : { display: 'none', width: 0, flex: 0 },
        tabBarIcon: ({ color, focused }) => <TabIcon icon={Icon} focused={focused} color={color}/>,
        tabBarButtonTestID: 'tab-' + key,
      }} />;
    })}
    <Tabs.Screen name="more" options={{
      title: copy.moreMenu, href: plan.showMore ? undefined : null,
      tabBarButtonTestID: 'tab-more',
      tabBarIcon: ({ color, focused }) => <TabIcon icon={Grid2X2} focused={focused} color={color}/>,
    }}/>
  </Tabs>;
}
