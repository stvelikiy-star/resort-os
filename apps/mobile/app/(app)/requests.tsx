import React, { useCallback, useRef } from 'react';
import { Text } from 'react-native';
import { useFocusEffect, useRouter } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { Plus } from 'lucide-react-native';
import { Button, Card, Empty, FadeIn, Screen, Title } from '../../src/components/ui';
import { TaskCard } from '../../src/components/domain';
import { useAsync } from '../../src/lib/useAsync';
import { useSession } from '../../src/state/session';
import { workspaceForSession } from '../../src/roles/registry';
import type { Task } from '../../src/api/types';
import { useTheme } from '../../src/theme/ThemeProvider';
import { font } from '../../src/theme/tokens';

export default function Requests() {
  const { t } = useTranslation();
  const router = useRouter();
  const { c } = useTheme();
  const { api, user } = useSession();
  const ws = workspaceForSession(user!.role, user!.module_permissions, api?.mode ?? 'LIVE');
  const { data, loading, error, reload } = useAsync<Task[]>(() => api!.listTasks({ type: 'MAINTENANCE' }), [api]);
  const hasFocused = useRef(false);
  useFocusEffect(useCallback(() => {
    if (hasFocused.current) void reload();
    else hasFocused.current = true;
  }, [reload]));
  return (
    <Screen>
      <Title>{t('mt.list')}</Title>
      {ws.canCreateMaintenance ? <Button testID="new-request-btn" label={t('mt.newRequest')} icon={Plus} onPress={() => router.push('/new-request')} /> : null}
      {loading && !data ? <Empty text={t('common.loading')} /> : null}
      {error ? <Card onPress={reload}><Text style={[font.body, { color: c.danger }]}>{t('errors.generic')} · {t('common.retry')}</Text></Card> : null}
      {!error && data && data.length === 0 ? <Empty text={t('common.empty')} /> : null}
      {(data ?? []).map((task, i) => <FadeIn key={task.id} delay={40 * i}><TaskCard task={task} onPress={() => router.push({ pathname: '/task/[id]', params: { id: task.id } })} /></FadeIn>)}
    </Screen>
  );
}
