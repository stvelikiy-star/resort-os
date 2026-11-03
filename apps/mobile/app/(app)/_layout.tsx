import React from 'react';
import { Redirect, Tabs } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { ClipboardCheck, BedDouble, ChartNoAxesCombined, CircleUserRound, Wrench } from 'lucide-react-native';
import { useSession } from '../../src/state/session';
import { useTheme } from '../../src/theme/ThemeProvider';
import { hasTabForSession, TabKey } from '../../src/roles/registry';

const ICONS = { tasks: ClipboardCheck, rooms: BedDouble, requests: Wrench, admin: ChartNoAxesCombined, profile: CircleUserRound } as const;
const ORDER: TabKey[] = ['tasks', 'rooms', 'requests', 'admin', 'profile'];

export default function AppTabs() {
  const { user, api } = useSession();
  const { t } = useTranslation();
  const { c } = useTheme();
  if (!user) return <Redirect href="/connect" />;
  return (
    <Tabs screenOptions={{
      headerShown: false, tabBarActiveTintColor: c.primary, tabBarInactiveTintColor: c.textMuted,
      tabBarStyle: { backgroundColor: c.surface, borderTopColor: c.border, borderTopWidth: 1, height: 76, paddingTop: 8, paddingBottom: 10, elevation: 12, shadowColor: c.shadow, shadowOpacity: 0.09, shadowRadius: 16 },
      tabBarLabelStyle: { fontSize: 11, fontWeight: '800', letterSpacing: 0.1 },
    }}>
      {ORDER.map((k) => {
        const Icon = ICONS[k];
        return (
          <Tabs.Screen key={k} name={k === 'tasks' ? 'tasks' : k}
            options={{ title: t(`nav.${k}`), href: hasTabForSession(user.role, user.module_permissions, api?.mode ?? 'LIVE', k) ? undefined : null, tabBarIcon: ({ color, focused }) => (
              <Icon size={24} color={color} strokeWidth={focused ? 2.7 : 1.8} />
            ), tabBarButtonTestID: `tab-${k}` }} />
        );
      })}
    </Tabs>
  );
}
