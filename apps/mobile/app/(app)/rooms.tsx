import React, { useCallback, useRef } from 'react';
import { Text, View } from 'react-native';
import { useFocusEffect, useRouter } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { Card, Empty, FadeIn, Screen, Title, toneColors } from '../../src/components/ui';
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
    <Screen>
      <Title sub={hotel?.name}>{t('rooms.title')}</Title>
      {api?.mode === 'LIVE' ? <Card><Text style={[font.small, { color: c.textMuted }]}>{t('rooms.partial')}</Text></Card> : null}
      {loading && !data ? <Empty text={t('common.loading')} /> : null}
      {error ? <Card onPress={reload}><Text style={[font.body, { color: c.danger }]}>{t('errors.generic')} · {t('common.retry')}</Text></Card> : null}
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.md }}>
        {(data ?? []).map((r, i) => {
          const tc = toneColors(c, roomTone(r.state));
          return (
            <FadeIn key={r.id} delay={40 * i} style={{ width: '47.5%' }}>
              <Card testID={`room-${r.id}`} onPress={() => router.push({ pathname: '/room/[id]', params: { id: r.id } })} style={{ gap: 8, borderLeftWidth: 5, borderLeftColor: tc.fg }}>
                <Text style={[font.title, { color: c.text, fontSize: 24 }]}>{r.code}</Text>
                <RoomStateBadge state={r.state} />
                <Text style={[font.small, { color: c.textMuted }]} numberOfLines={1}>{r.guest ?? (r.arrival ? `${t('rooms.arrival')}: ${r.arrival}` : api?.mode === 'LIVE' ? t('rooms.state.UNKNOWN') : t('rooms.vacant'))}</Text>
              </Card>
            </FadeIn>
          );
        })}
      </View>
    </Screen>
  );
}
