import React from 'react';
import { Text, View } from 'react-native';
import { BedDouble, CalendarDays, ChefHat, CircleUserRound, ClipboardCheck,
  ConciergeBell, LayoutDashboard, MessageCircle, UsersRound,
  UtensilsCrossed, Wrench } from 'lucide-react-native';
import type { LucideIcon } from 'lucide-react-native';
import type { TabKey } from '../roles/registry';
import { useMobileCopy } from '../i18n/mobileCopy';
import { useTheme } from '../theme/ThemeProvider';
import { font, radius, space } from '../theme/tokens';
import { GlassCard } from './Future';
import { SectionLabel } from './ui';

const ICONS: Record<TabKey, LucideIcon> = {
  overview: LayoutDashboard, reception: ConciergeBell, pms: CalendarDays,
  inbox: MessageCircle, dining: UtensilsCrossed, kitchen: ChefHat,
  tasks: ClipboardCheck, rooms: BedDouble, requests: Wrench,
  admin: UsersRound, profile: CircleUserRound,
};

/** A view of *already granted* tabs; never adds a hidden server operation.
 * No fabricated shift, earnings, inventory, or employee-performance data. */
export function RoleProfileWorkspaces({
  tabs, onOpen,
}: {
  tabs: readonly TabKey[];
  onOpen: (route: TabKey) => void;
}) {
  const copy = useMobileCopy();
  const { c } = useTheme();
  const workTabs = tabs.filter(tab => tab !== 'profile');
  if (!workTabs.length) return null;
  return <View testID="role-workspaces" style={{ gap: space.sm }}>
    <SectionLabel>{copy.profileWorkspaces}</SectionLabel>
    <Text style={[font.small, { color: c.textMuted }]}>{copy.profileWorkspacesHint}</Text>
    {Array.from({length:Math.ceil(workTabs.length/2)},(_,rowIndex) => {
      const visible = workTabs.slice(rowIndex*2,rowIndex*2+2);
      return <View key={rowIndex} style={{ flexDirection: 'row', gap: space.sm }}>
        {visible.map(tab=>{
          const Icon = ICONS[tab];
          return <GlassCard key={tab} testID={'profile-work-'+tab} onPress={()=>onOpen(tab)} style={{
            flex: 1, minWidth: 0, minHeight: 94, gap: space.sm,
            padding: 14, borderRadius: radius.lg,
          }}>
            <Icon color={c.primary} size={25} strokeWidth={2}/>
            <Text numberOfLines={2} style={[font.small, { color:c.text, fontWeight:'700' }]}>
              {copy[tab]}
            </Text>
          </GlassCard>;
        })}
        {visible.length===1 ? <View style={{ flex:1 }}/> : null}
      </View>;
    })}
  </View>;
}
