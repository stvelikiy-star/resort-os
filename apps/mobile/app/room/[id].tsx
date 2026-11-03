import React from 'react';
import { Text, View } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { ChevronLeft } from 'lucide-react-native';
import { Card, Empty, PressScale, Screen, SectionLabel, Title, toneColors } from '../../src/components/ui';
import { RoomStateBadge, roomTone, TaskCard } from '../../src/components/domain';
import { useAsync } from '../../src/lib/useAsync';
import { useSession } from '../../src/state/session';
import { workspaceFor } from '../../src/roles/registry';
import { useTheme } from '../../src/theme/ThemeProvider';
import { font, radius, space } from '../../src/theme/tokens';
import type { Room, RoomState, Task } from '../../src/api/types';

const STATES: RoomState[] = ['CLEAN', 'DIRTY', 'IN_INSPECTION', 'TECH_BLOCK'];

export default function RoomCard() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { t } = useTranslation();
  const { c } = useTheme();
  const router = useRouter();
  const { api, user } = useSession();
  const ws = workspaceFor(user!.role);
  const room = useAsync<Room | null>(async () => (await api!.listRooms()).find((r) => r.id === id) ?? null, [api, id]);
  const tasks = useAsync<Task[]>(async () => (await api!.listTasks()).filter((x) => x.room_id === id && x.status !== 'DONE' && x.status !== 'CANCELLED'), [api, id]);
  if (!room.data) return <Screen><Empty text={room.loading ? t('common.loading') : t('errors.notFound')} /></Screen>;
  const r = room.data;
  const set = async (s: RoomState) => { room.setData(await api!.setRoomState(r.id, s)); };
  return (
    <Screen>
      <PressScale onPress={() => router.back()} style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }} accessibilityLabel={t('common.back')}>
        <ChevronLeft size={22} color={c.primary} /><Text style={[font.body, { color: c.primary }]}>{t('common.back')}</Text>
      </PressScale>
      <Title sub={`${t('rooms.floor')} ${r.floor}`}>{r.code}</Title>
      <Card style={{ gap: space.sm }}>
        <RoomStateBadge state={r.state} />
        <Text style={[font.body, { color: c.text }]}>{t('rooms.guest')}: {r.guest ?? t('rooms.vacant')}</Text>
        {r.checkout ? <Text style={[font.body, { color: c.textMuted }]}>{t('rooms.checkout')}: {r.checkout}</Text> : null}
        {r.arrival ? <Text style={[font.body, { color: c.textMuted }]}>{t('rooms.arrival')}: {r.arrival}</Text> : null}
        {r.note ? <Text style={[font.small, { color: c.textMuted }]}>{t('rooms.notes')}: {r.note}</Text> : null}
      </Card>
      {ws.canSetRoomState ? (
        <>
          <SectionLabel>{t('rooms.setState')}</SectionLabel>
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.sm }}>
            {STATES.map((s) => {
              const tc = toneColors(c, roomTone(s));
              const on = r.state === s;
              return (
                <PressScale key={s} testID={`state-${s}`} onPress={() => set(s)} style={{ minHeight: 48, paddingHorizontal: 16, justifyContent: 'center', borderRadius: radius.pill, backgroundColor: on ? tc.fg : tc.bg }}>
                  <Text style={[font.small, { fontWeight: '800', color: on ? '#fff' : tc.fg }]}>{t(`rooms.state.${s}`)}</Text>
                </PressScale>
              );
            })}
          </View>
        </>
      ) : null}
      <SectionLabel>{t('rooms.openTasks')}</SectionLabel>
      {(tasks.data ?? []).length === 0 ? <Empty text={t('common.empty')} /> : null}
      {(tasks.data ?? []).map((task) => <TaskCard key={task.id} task={task} onPress={() => router.push({ pathname: '/task/[id]', params: { id: task.id } })} />)}
    </Screen>
  );
}
