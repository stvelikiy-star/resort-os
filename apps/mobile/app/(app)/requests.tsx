import React, { useCallback, useRef } from 'react';
import { useFocusEffect, useRouter } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { Plus } from 'lucide-react-native';
import { Button, Empty } from '../../src/components/ui';
import { ErrorState, FutureScreen, LoadingShimmer, PremiumHeader, StaggerItem } from '../../src/components/Future';
import { TaskCard } from '../../src/components/domain';
import { useAsync } from '../../src/lib/useAsync';
import { useSession } from '../../src/state/session';
import { workspaceForSession } from '../../src/roles/registry';
import type { Task } from '../../src/api/types';

export default function Requests() {
  const { t } = useTranslation();
  const router = useRouter();
  const { api, user } = useSession();
  const ws = workspaceForSession(user!.role, user!.module_permissions, api?.mode ?? 'LIVE');
  const { data, loading, error, reload } = useAsync<Task[]>(() => api!.listTasks({ type: 'MAINTENANCE' }), [api]);
  const focused = useRef(false);
  useFocusEffect(useCallback(() => { if (focused.current) void reload(); else focused.current = true; }, [reload]));
  return <FutureScreen>
    <PremiumHeader title={t('mt.list')} eyebrow="MARINA SMART"/>
    {ws.canCreateMaintenance ? <Button testID="new-request-btn" label={t('mt.newRequest')} icon={Plus} onPress={() => router.push('/new-request')}/> : null}
    {loading && !data ? <LoadingShimmer count={3}/> : null}
    {error ? <ErrorState text={error.message} retry={t('common.retry')} onRetry={reload}/> : null}
    {!error && data && data.length === 0 ? <Empty text={t('common.empty')}/> : null}
    {(data ?? []).map((task, i) => <StaggerItem key={task.id} index={i}>
      <TaskCard task={task} onPress={() => router.push({ pathname:'/task/[id]', params:{id:task.id} })}/>
    </StaggerItem>)}
  </FutureScreen>;
}
