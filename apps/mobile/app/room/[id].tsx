import React, { useState } from 'react';
import { Text, View } from 'react-native';
import { Redirect, useLocalSearchParams, useRouter } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { ChevronLeft, BedDouble } from 'lucide-react-native';
import { Empty, PressScale, SectionLabel, toneColors } from '../../src/components/ui';
import { RoomStateBadge, roomTone, TaskCard } from '../../src/components/domain';
import { useAsync } from '../../src/lib/useAsync';
import { FutureScreen, GlassCard, PremiumHeader, LoadingShimmer, ErrorState } from '../../src/components/Future';
import { useSession } from '../../src/state/session';
import { workspaceForSession } from '../../src/roles/registry';
import { useTheme } from '../../src/theme/ThemeProvider';
import { font, radius, space } from '../../src/theme/tokens';
import type { Room, RoomState, Task } from '../../src/api/types';

const STATES: RoomState[] = ['CLEAN', 'DIRTY', 'IN_INSPECTION', 'TECH_BLOCK'];

export default function RoomCard() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { t } = useTranslation();
  const { c } = useTheme();
  const router = useRouter();
  const { api, user, hotel, serverAuthMode } = useSession();
  const [busy, setBusy] = useState(false);
  const [mutationError, setMutationError] = useState(false);
  const ws = workspaceForSession(user?.role ?? 'AGENT', user?.module_permissions, api?.mode ?? 'LIVE', serverAuthMode);
  const room = useAsync<Room | null>(async () => user && api && ws.mobileReady ? (await api.listRooms()).find((r) => r.id === id) ?? null : null, [api, id, user?.id]);
  const tasks = useAsync<Task[]>(async () => user && api && ws.mobileReady ? (await api.listTasks()).filter((x) => x.room_id === id && x.status !== 'DONE' && x.status !== 'CANCELLED') : [], [api, id, user?.id]);
  if (!user || !api) return <Redirect href="/connect" />;
  if (!ws.mobileReady) return <Redirect href="/profile" />;
  if (room.error) return <FutureScreen><ErrorState text={room.error.message} retry={t('common.retry')} onRetry={room.reload}/></FutureScreen>;
  if (!room.data) return <FutureScreen>{room.loading ? <LoadingShimmer count={3}/> : <Empty text={t('errors.notFound')}/>}</FutureScreen>;
  const r = room.data;
  const set = async (s: RoomState) => {
    if (busy) return;
    setBusy(true);
    setMutationError(false);
    try { room.setData(await api!.setRoomState(r.id, s)); }
    catch { setMutationError(true); }
    finally { setBusy(false); }
  };
  return (
    <FutureScreen>
      <PressScale onPress={() => router.back()} style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }} accessibilityLabel={t('common.back')}>
        <ChevronLeft size={22} color={c.primary} /><Text style={[font.body, { color: c.primary }]}>{t('common.back')}</Text>
      </PressScale>
      <PremiumHeader title={r.code} subtitle={hotel?.name} eyebrow={t('rooms.title')}/>
      <GlassCard style={{ gap: space.sm, borderLeftWidth: 4, borderLeftColor: toneColors(c, roomTone(r.state)).fg }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: space.md }}><BedDouble size={27} color={c.primary}/><RoomStateBadge state={r.state}/></View>
        <Text style={[font.body, { color: c.text }]}>{t('rooms.guest')}: {r.guest ?? (api?.mode === 'LIVE' ? t('rooms.state.UNKNOWN') : t('rooms.vacant'))}</Text>
        {api?.mode === 'LIVE' ? <Text style={[font.small, { color: c.textMuted }]}>{t('rooms.partial')}</Text> : null}
        {r.checkout ? <Text style={[font.body, { color: c.textMuted }]}>{t('rooms.checkout')}: {r.checkout}</Text> : null}
        {r.arrival ? <Text style={[font.body, { color: c.textMuted }]}>{t('rooms.arrival')}: {r.arrival}</Text> : null}
        {r.note ? <Text style={[font.small, { color: c.textMuted }]}>{t('rooms.notes')}: {r.note}</Text> : null}
      </GlassCard>
      {ws.canSetRoomState && api?.mode === 'DEMO' ? (
        <>
          <SectionLabel>{t('rooms.setState')}</SectionLabel>
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.sm }}>
            {STATES.map((s) => {
              const tc = toneColors(c, roomTone(s));
              const on = r.state === s;
              return (
                <PressScale key={s} testID={`state-${s}`} onPress={() => set(s)} disabled={busy} style={{ minHeight: 48, paddingHorizontal: 16, justifyContent: 'center', borderRadius: radius.pill, backgroundColor: on ? tc.fg : tc.bg }}>
                  <Text style={[font.small, { fontWeight: '800', color: on ? '#fff' : tc.fg }]}>{t(`rooms.state.${s}`)}</Text>
                </PressScale>
              );
            })}
          </View>
        </>
      ) : null}
      {mutationError ? <Text style={[font.small, { color: c.danger }]}>{t('errors.generic')}</Text> : null}
      <SectionLabel>{t('rooms.openTasks')}</SectionLabel>
      {tasks.error ? <ErrorState text={tasks.error.message} retry={t('common.retry')} onRetry={tasks.reload}/> : null}
      {!tasks.loading && !tasks.error && (tasks.data ?? []).length === 0 ? <Empty text={t('common.empty')} /> : null}
      {(tasks.data ?? []).map((task) => <TaskCard key={task.id} task={task} onPress={() => router.push({ pathname: '/task/[id]', params: { id: task.id } })} />)}
    </FutureScreen>
  );
}
