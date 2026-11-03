import React, { useCallback, useMemo, useRef } from 'react';
import { Text, View } from 'react-native';
import { useFocusEffect, useRouter } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { Plus } from 'lucide-react-native';
import { AnimatedProgressBar, Card, DemoBanner, Empty, FadeIn, PressScale, Screen, SectionLabel } from '../../src/components/ui';
import { TaskCard } from '../../src/components/domain';
import { Hero } from '../../src/components/Brand';
import { useAsync } from '../../src/lib/useAsync';
import { useSession } from '../../src/state/session';
import { workspaceForSession } from '../../src/roles/registry';
import { useTheme } from '../../src/theme/ThemeProvider';
import { font, radius, space } from '../../src/theme/tokens';
import type { Task } from '../../src/api/types';

export default function Tasks() {
  const { t } = useTranslation();
  const { c } = useTheme();
  const router = useRouter();
  const { api, user, hotel } = useSession();
  const ws = workspaceForSession(user!.role, user!.module_permissions, api?.mode ?? 'LIVE');
  const { data, loading, error, reload } = useAsync<Task[]>(() => (ws.mobileReady ? api!.listTasks() : Promise.resolve([])), [api, user?.id]);
  const hasFocused = useRef(false);
  useFocusEffect(useCallback(() => {
    if (hasFocused.current) void reload();
    else hasFocused.current = true;
  }, [reload]));

  const { active, finished, pct } = useMemo(() => {
    const list = data ?? [];
    const finished = list.filter((x) => x.status === 'DONE');
    const active = list.filter((x) => x.status !== 'DONE' && x.status !== 'CANCELLED').sort((a, b) => (a.priority === 'URGENT' ? -1 : 0) - (b.priority === 'URGENT' ? -1 : 0));
    return { active, finished, pct: list.length ? Math.round((finished.length / list.length) * 100) : 0 };
  }, [data]);

  return (
    <Screen>
      <FadeIn>
        <Hero>
          <Text style={[font.label, { color: '#D4E3F4' }]}>{hotel?.name.toUpperCase()} · {t(`roles.${user!.role}`).toUpperCase()}</Text>
          <Text style={[font.title, { color: '#fff', marginTop: 4 }]}>{user!.display_name}</Text>
          <View style={{ marginTop: space.lg, gap: 6 }}>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
              <Text style={[font.small, { color: '#D4E3F4' }]}>{t(api?.mode === 'LIVE' ? 'tasks.progressVisible' : 'tasks.progress')}</Text>
              <Text testID="progress-pct" style={[font.small, { color: '#fff', fontWeight: '800' }]}>{pct}%</Text>
            </View>
            <AnimatedProgressBar percent={pct} />
          </View>
        </Hero>
      </FadeIn>
      {hotel?.demo ? <DemoBanner /> : null}

      {ws.canCreateMaintenance ? (
        <>
          <SectionLabel>{t('tasks.quick')}</SectionLabel>
          <PressScale testID="quick-new-request" onPress={() => router.push('/new-request')} style={{ flexDirection: 'row', alignItems: 'center', gap: space.md, backgroundColor: c.primarySoft, borderRadius: radius.lg, padding: space.lg, minHeight: 64 }}>
            <Plus size={26} color={c.primary} /><Text style={[font.h2, { color: c.primary }]}>{t('mt.newRequest')}</Text>
          </PressScale>
        </>
      ) : null}

      <SectionLabel>{t(api?.mode === 'LIVE' ? 'tasks.visible' : 'tasks.today')}</SectionLabel>
      {loading && !data ? <Empty text={t('common.loading')} /> : null}
      {error ? <Card onPress={reload}><Text style={[font.body, { color: c.danger }]}>{t('errors.generic')} · {t('common.retry')}</Text></Card> : null}
      {!loading && !error && !ws.mobileReady ? <Empty text={t('admin.forbidden')} /> : null}
      {!loading && ws.mobileReady && active.length === 0 ? <Empty text={t('tasks.none')} /> : null}
      {active.map((task, i) => (
        <FadeIn key={task.id} delay={50 * i}><TaskCard task={task} onPress={() => router.push({ pathname: '/task/[id]', params: { id: task.id } })} /></FadeIn>
      ))}
      {finished.length ? <SectionLabel>{t('tasks.done')}</SectionLabel> : null}
      {finished.map((task) => <TaskCard key={task.id} task={task} onPress={() => router.push({ pathname: '/task/[id]', params: { id: task.id } })} />)}
    </Screen>
  );
}
