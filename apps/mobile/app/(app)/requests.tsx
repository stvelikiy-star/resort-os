import React, { useCallback, useMemo, useRef } from 'react';
import { Text, View } from 'react-native';
import { useFocusEffect, useRouter } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { Plus, AlertTriangle, Wrench } from 'lucide-react-native';
import { Button, Empty, SectionLabel } from '../../src/components/ui';
import { ErrorState, FutureScreen, GlassCard, LoadingShimmer, PremiumHeader, StaggerItem } from '../../src/components/Future';
import { TaskCard } from '../../src/components/domain';
import { useAsync } from '../../src/lib/useAsync';
import { useSession } from '../../src/state/session';
import { useTheme } from '../../src/theme/ThemeProvider';
import { font, space } from '../../src/theme/tokens';
import { workspaceForSession } from '../../src/roles/registry';
import type { Task } from '../../src/api/types';

export default function Requests() {
  const { t } = useTranslation();
  const router = useRouter();
  const { c } = useTheme();
  const { api, user, hotel, serverAuthMode } = useSession();
  const ws = workspaceForSession(user!.role, user!.module_permissions, api?.mode ?? 'LIVE', serverAuthMode);
  const { data, loading, error, reload } = useAsync<Task[]>(() => (ws.mobileReady ? api!.listTasks({ type: 'MAINTENANCE' }) : Promise.resolve([])), [api, user?.id, ws.mobileReady]);
  const active = useMemo(() => (data ?? []).filter(x => x.status !== 'DONE' && x.status !== 'CANCELLED'), [data]);
  const urgent = active.filter(x => x.priority === 'URGENT').length;
  const finished = useMemo(() => (data ?? []).filter(x => x.status === 'DONE' || x.status === 'CANCELLED'), [data]);
  const focused = useRef(false);
  useFocusEffect(useCallback(() => { if (focused.current) void reload(); else focused.current = true; }, [reload]));
  return <FutureScreen>
    <PremiumHeader title={t('mt.list')} subtitle={hotel?.name} eyebrow={t('roles.' + user!.role)}/>
    {ws.mobileReady && ws.canCreateMaintenance ? <Button testID="new-request-btn" label={t('mt.newRequest')} icon={Plus} onPress={() => router.push('/new-request')}/> : null}
    {data && !error ? <GlassCard style={{ gap: space.sm }}>
      <View style={{ flexDirection: 'row', gap: space.md, alignItems: 'center' }}>
        <View style={{ width: 48, height: 48, alignItems: 'center', justifyContent: 'center', borderRadius: 16, backgroundColor: c.primarySoft }}><Wrench size={25} color={c.primary}/></View>
        <View style={{ flex: 1 }}><Text style={[font.metric, { color: c.text }]}>{active.length}</Text><Text style={[font.small, { color: c.textMuted }]}>{t('tasks.visible')}</Text></View>
        <View style={{ alignItems: 'center', gap: 4 }}><AlertTriangle size={22} color={c.warning}/><Text style={[font.h2, { color: c.warning }]}>{urgent}</Text><Text style={[font.small, { color: c.textMuted }]}>{t('tasks.urgent')}</Text></View>
      </View>
    </GlassCard> : null}
    {loading && !data ? <LoadingShimmer count={3}/> : null}
    {error ? <ErrorState text={error.message} retry={t('common.retry')} onRetry={reload}/> : null}
    {!error && data && data.length === 0 ? <Empty text={t('common.empty')}/> : null}
    {active.length ? <SectionLabel>{t('tasks.visible')}</SectionLabel> : null}
    {active.map((task, i) => <StaggerItem key={task.id} index={i}>
      <TaskCard task={task} onPress={() => router.push({ pathname:'/task/[id]', params:{id:task.id} })}/>
    </StaggerItem>)}
    {finished.length ? <SectionLabel>{t('tasks.done')}</SectionLabel> : null}
    {finished.map((task, i) => <StaggerItem key={task.id} index={i}>
      <TaskCard task={task} onPress={() => router.push({ pathname: '/task/[id]', params: { id: task.id } })}/>
    </StaggerItem>)}
  </FutureScreen>;
}
