import React, { useCallback, useMemo, useRef, useState } from 'react';
import { Text, View, useWindowDimensions } from 'react-native';
import { ArrowUpRight, BedDouble } from 'lucide-react-native';
import { useFocusEffect, useRouter } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { Empty, SectionLabel, Segmented, toneColors } from '../../src/components/ui';
import { ErrorState, FutureScreen, GlassCard, LoadingShimmer, PremiumHeader, StaggerItem } from '../../src/components/Future';
import { RoomStateBadge, roomTone } from '../../src/components/domain';
import { useAsync } from '../../src/lib/useAsync';
import { hasTabForSession } from '../../src/roles/registry';
import { useSession } from '../../src/state/session';
import { useMobileCopy } from '../../src/i18n/mobileCopy';
import { useTheme } from '../../src/theme/ThemeProvider';
import { font, radius, space } from '../../src/theme/tokens';
import type { Room } from '../../src/api/types';

export default function Rooms() {
  const { t } = useTranslation();
  const { c } = useTheme();
  const copy = useMobileCopy();
  const { width, fontScale } = useWindowDimensions();
  const singleColumn = width < 375 || fontScale > 1.35;
  const [filter, setFilter] = useState<'all' | 'clean' | 'attention'>('all');
  const router = useRouter();
  const { api, hotel, user, serverAuthMode } = useSession();
  const allowed = !!api && !!user && hasTabForSession(user.role, user.module_permissions, api.mode, 'rooms', serverAuthMode);
  const { data, loading, error, reload } = useAsync<Room[]>(() => allowed ? api!.listRooms() : Promise.resolve([]), [api, user?.id, allowed]);
  const visible = useMemo(() => (data ?? []).filter(r => filter === 'all' || (filter === 'clean' ? r.state === 'CLEAN' : r.state === 'DIRTY' || r.state === 'IN_INSPECTION' || r.state === 'TECH_BLOCK')), [data, filter]);
  const hasFocused = useRef(false);
  useFocusEffect(useCallback(() => {
    if (hasFocused.current) void reload();
    else hasFocused.current = true;
  }, [reload]));
  if (!allowed) return <FutureScreen><Empty text={t('admin.forbidden')}/></FutureScreen>;
  return (
    <FutureScreen>
      <PremiumHeader title={t('rooms.title')} subtitle={hotel?.name} eyebrow="MARINA SMART"/>
      {api?.mode === 'LIVE' ? <GlassCard><Text style={[font.small, { color: c.textMuted }]}>{t('rooms.partial')}</Text></GlassCard> : null}
      {data ? <>
        <SectionLabel>{copy.rooms} · {data.length}</SectionLabel>
        <Segmented value={filter} onChange={setFilter} options={[{ key: 'all', label: copy.all }, { key: 'clean', label: copy.clean }, { key: 'attention', label: copy.needsAttention }]}/>
      </> : null}
      {loading && !data ? <LoadingShimmer count={3}/> : null}
      {error ? <ErrorState text={error.message} retry={t('common.retry')} onRetry={reload}/> : null}
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.md }}>
        {visible.map((r, i) => {
          const tc = toneColors(c, roomTone(r.state));
          return (
            <View key={r.id} style={{ width: singleColumn ? '100%' : '47%' }}><StaggerItem index={i}>
              <GlassCard testID={`room-${r.id}`} onPress={() => router.push({ pathname: '/room/[id]', params: { id: r.id } })} style={{ gap: 8, minHeight: singleColumn ? 146 : 168, borderLeftWidth: 5, borderLeftColor: tc.fg }}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
                  <View style={{ width: 40, height: 40, borderRadius: radius.md, backgroundColor: tc.bg, alignItems: 'center', justifyContent: 'center' }}>
                    <BedDouble size={22} color={tc.fg} strokeWidth={1.9}/>
                  </View>
                  <View style={{ flex: 1, minWidth: 0 }}>
                    <Text style={[font.title, { color: c.text, fontSize: 22 }]} numberOfLines={2}>{r.code}</Text>
                    <Text style={[font.small, { color: c.textMuted }]}>{t('rooms.floor')} {r.floor}</Text>
                  </View>
                  <ArrowUpRight size={19} color={c.textMuted}/>
                </View>
                <RoomStateBadge state={r.state}/>
                <Text style={[font.small, { color: c.textMuted, flexShrink: 1 }]} numberOfLines={2}>{r.guest ?? (r.arrival ? `${t('rooms.arrival')}: ${r.arrival}` : api?.mode === 'LIVE' ? t('rooms.state.UNKNOWN') : t('rooms.vacant'))}</Text>
              </GlassCard></StaggerItem>
            </View>
          );
        })}
      </View>
      {data && visible.length === 0 ? <Empty text={copy.empty}/> : null}
    </FutureScreen>
  );
}
