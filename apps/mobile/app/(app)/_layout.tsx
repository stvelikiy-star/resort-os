import React from 'react';
import { Redirect, Tabs } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { ClipboardList, DoorOpen, LayoutDashboard, UserCircle, Wrench } from 'lucide-react-native';
import { useSession } from '../../src/state/session';
import { useTheme } from '../../src/theme/ThemeProvider';
import { hasTab, TabKey } from '../../src/roles/registry';

const ICONS = { tasks: ClipboardList, rooms: DoorOpen, requests: Wrench, admin: LayoutDashboard, profile: UserCircle } as const;
const ORDER: TabKey[] = ['tasks', 'rooms', 'requests', 'admin', 'profile'];

export default function AppTabs() {
  const { user } = useSession();
  const { t } = useTranslation();
  const { c } = useTheme();
  if (!user) return <Redirect href="/connect" />;
  return (
    <Tabs screenOptions={{
      headerShown: false, tabBarActiveTintColor: c.primary, tabBarInactiveTintColor: c.textMuted,
      tabBarStyle: { backgroundColor: c.surface, borderTopColor: c.border, height: 68, paddingTop: 6, paddingBottom: 8 },
      tabBarLabelStyle: { fontSize: 12, fontWeight: '700' },
    }}>
      {ORDER.map((k) => {
        const Icon = ICONS[k];
        return (
          <Tabs.Screen key={k} name={k === 'tasks' ? 'tasks' : k}
            options={{ title: t(`nav.${k}`), href: hasTab(user.role, k) ? undefined : null, tabBarIcon: ({ color }) => <Icon size={24} color={color} />, tabBarButtonTestID: `tab-${k}` }} />
        );
      })}
    </Tabs>
  );
}
