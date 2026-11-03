import React, { useCallback, useRef } from 'react';
import { Text, View } from 'react-native';
import { useFocusEffect, useRouter } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { toneColors } from '../../src/components/ui';
import { ErrorState, FutureScreen, GlassCard, LoadingShimmer, PremiumHeader, StaggerItem } from '../../src/components/Future';
import { RoomStateBadge, roomTone } from '../../src/components/domain';
import { useAsync } from '../../src/lib/useAsync';
import { useSession } from '../../src/state/session';
import { useTheme } from '../../src/theme/ThemeProvider';
import { font, space } from '../../src/theme/tokens';
import type { Room } from '../../src/api/types';

export default function Rooms() {
  const { t } = useTranslation();
  const { c } = useTheme();
  const router = useRouter();
  const { api, hotel } = useSession();
  const { data, loading, error, reload } = useAsync<Room[]>(() => api!.listRooms(), [api]);
  const hasFocused = useRef(false);
  useFocusEffect(useCallback(() => {
    if (hasFocused.current) void reload();
    else hasFocused.current = true;
  }, [reload]));
  return (
    <FutureScreen>
      <PremiumHeader title={t('rooms.title')} subtitle={hotel?.name} eyebrow="MARINA SMART"/>
      {api?.mode === 'LIVE' ? <GlassCard><Text style={[font.small, { color: c.textMuted }]}>{t('rooms.partial')}</Text></GlassCard> : null}
      {loading && !data ? <LoadingShimmer count={3}/> : null}
      {error ? <ErrorState text={error.message} retry={t('common.retry')} onRetry={reload}/> : null}
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.md }}>
        {(data ?? []).map((r, i) => {
          const tc = toneColors(c, roomTone(r.state));
          return (
            <View key={r.id} style={{ width: '47.5%' }}><StaggerItem index={i}>
              <GlassCard testID={`room-${r.id}`} onPress={() => router.push({ pathname: '/room/[id]', params: { id: r.id } })} style={{ gap: 8, borderLeftWidth: 5, borderLeftColor: tc.fg }}>
                <Text style={[font.title, { color: c.text, fontSize: 24 }]}>{r.code}</Text>
                <RoomStateBadge state={r.state} />
                <Text style={[font.small, { color: c.textMuted }]} numberOfLines={1}>{r.guest ?? (r.arrival ? `${t('rooms.arrival')}: ${r.arrival}` : api?.mode === 'LIVE' ? t('rooms.state.UNKNOWN') : t('rooms.vacant'))}</Text>
              </GlassCard></StaggerItem>
            </View>
          );
        })}
      </View>
    </FutureScreen>
  );
}
