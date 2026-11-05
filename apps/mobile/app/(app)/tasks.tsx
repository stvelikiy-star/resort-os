import React, { useCallback, useMemo, useRef, useState } from 'react';
import { Text, View } from 'react-native';
import { useFocusEffect, useRouter } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { Plus, ShieldCheck } from 'lucide-react-native';
import { AnimatedProgressBar, DemoBanner, Empty, SectionLabel, Segmented } from '../../src/components/ui';
import { FutureScreen, ErrorState, LoadingShimmer, PremiumHeader, QuickAction, StaggerItem } from '../../src/components/Future';
import { TaskCard } from '../../src/components/domain';
import { demoTaskTitle } from '../../src/i18n/demoLabels';
import { Hero } from '../../src/components/Brand';
import { useAsync } from '../../src/lib/useAsync';
import { useSession } from '../../src/state/session';
import { workspaceForSession } from '../../src/roles/registry';
import { font } from '../../src/theme/tokens';
import type { Task } from '../../src/api/types';

export default function Tasks() {
  const { t } = useTranslation();
  const router = useRouter();
  const [filter, setFilter] = useState<'all' | 'active' | 'urgent'>('all');
  const { api, user, hotel, serverAuthMode, locale } = useSession();
  const ws = workspaceForSession(user!.role, user!.module_permissions, api?.mode ?? 'LIVE', serverAuthMode);
  const { data, loading, error, reload } = useAsync<Task[]>(() => (ws.mobileReady ? api!.listTasks() : Promise.resolve([])), [api, user?.id]);
  const hasFocused = useRef(false);
  useFocusEffect(useCallback(() => { if (hasFocused.current) void reload(); else hasFocused.current = true; }, [reload]));
  const { active, finished, pct } = useMemo(() => {
    const list = data ?? [];
    const finished = list.filter(x => x.status === 'DONE');
    const priorityOrder = { URGENT: 0, HIGH: 1, NORMAL: 2, LOW: 3 };
    const active = list.filter(x => x.status !== 'DONE' && x.status !== 'CANCELLED').sort((a,b) =>
      priorityOrder[a.priority] - priorityOrder[b.priority]);
    return { active, finished, pct: list.length ? Math.round((finished.length / list.length) * 100) : 0 };
  }, [data]);
  const visibleActive = filter === 'urgent' ? active.filter(task => task.priority === 'URGENT') : active;
  return <FutureScreen>
    <PremiumHeader title={t('tasks.title')} subtitle={hotel?.name} eyebrow={t(`roles.${user!.role}`)}/>
    {hotel?.demo ? <DemoBanner/> : null}
    {data && !error ? <StaggerItem index={0}>
      <Hero height={170}>
        <View style={{flexDirection:'row',alignItems:'center',justifyContent:'space-between'}}>
          <Text style={[font.label,{color:'#D6E9F7'}]}>{user!.display_name}</Text>
          <ShieldCheck size={22} color="#E6BD70"/>
        </View>
        <Text style={[font.display,{color:'#FFFFFF',marginTop:10}]}>{active.length}</Text>
        <Text style={[font.body,{color:'#D6E9F7'}]}>{t(api?.mode === 'LIVE' ? 'tasks.visible' : 'tasks.today')}</Text>
        <View style={{marginTop:16,gap:6}}>
          <View style={{flexDirection:'row',justifyContent:'space-between'}}>
            <Text style={[font.small,{color:'#D6E9F7'}]}>{t(api?.mode === 'LIVE' ? 'tasks.progressVisible' : 'tasks.progress')}</Text>
            <Text testID="progress-pct" style={[font.small,{color:'#FFFFFF',fontWeight:'800'}]}>{pct}%</Text>
          </View>
          <AnimatedProgressBar percent={pct}/>
        </View>
      </Hero>
    </StaggerItem> : null}
    {ws.mobileReady && ws.canCreateMaintenance ? <>
      <SectionLabel>{t('tasks.quick')}</SectionLabel>
      <QuickAction icon={Plus} testID="quick-new-request" label={t('mt.newRequest')} onPress={() => router.push('/new-request')}/>
    </> : null}
    <SectionLabel>{t(api?.mode === 'LIVE' ? 'tasks.visible' : 'tasks.today')}</SectionLabel>
    {data && !error ? <Segmented value={filter} onChange={setFilter} options={[{key:'all',label:t('common.all')},{key:'active',label:t('tasks.visible')},{key:'urgent',label:t('tasks.urgent')}]} /> : null}
    {loading && !data ? <LoadingShimmer count={3}/> : null}
    {error ? <ErrorState text={error.message} retry={t('common.retry')} onRetry={reload}/> : null}
    {!loading && !error && !ws.mobileReady ? <Empty text={t('admin.forbidden')}/> : null}
    {!loading && !error && ws.mobileReady && visibleActive.length === 0 ? <Empty text={t('tasks.none')}/> : null}
    {visibleActive.map((task,i) => <StaggerItem key={task.id} index={i}><TaskCard task={api?.mode === 'DEMO' ? { ...task, title: demoTaskTitle(task.id, locale, task.title) } : task} onPress={() => router.push({ pathname:'/task/[id]', params:{id:task.id} })}/></StaggerItem>)}
    {filter === 'all' && finished.length ? <SectionLabel>{t('tasks.done')}</SectionLabel> : null}
    {filter === 'all' ? finished.map(task => <TaskCard key={task.id} task={task} onPress={() => router.push({ pathname:'/task/[id]', params:{id:task.id} })}/>) : null}
  </FutureScreen>;
}
