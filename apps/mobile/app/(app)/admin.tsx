import React, { useCallback, useRef, useState } from 'react';
import { Text, View } from 'react-native';
import { useFocusEffect, useRouter } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { BedDouble, CheckCircle2, Clock, Percent, Wrench } from 'lucide-react-native';
import { Badge, Button, Card, Empty, FadeIn, PressScale, Screen, SectionLabel, Title } from '../../src/components/ui';
import { TaskCard } from '../../src/components/domain';
import { useAsync } from '../../src/lib/useAsync';
import { useSession } from '../../src/state/session';
import { workspaceFor } from '../../src/roles/registry';
import { useTheme } from '../../src/theme/ThemeProvider';
import { font, radius, space } from '../../src/theme/tokens';
import type { DaySummary, StaffMember, Task } from '../../src/api/types';

function Stat({ icon: Icon, label, value, tone }: { icon: any; label: string; value: string; tone: string }) {
  const { c } = useTheme();
  return (
    <Card style={{ flexBasis: '47%', flexGrow: 1, gap: 4 }}>
      <Icon size={22} color={tone} />
      <Text style={[font.title, { color: c.text }]}>{value}</Text>
      <Text style={[font.small, { color: c.textMuted }]}>{label}</Text>
    </Card>
  );
}

export default function Admin() {
  const { t } = useTranslation();
  const { c } = useTheme();
  const router = useRouter();
  const { api, user } = useSession();
  const allowed = workspaceFor(user!.role).canManage;
  const [pick, setPick] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const summary = useAsync<DaySummary | null>(() => (allowed ? api!.daySummary().catch(() => null) : Promise.resolve(null)), [api, tick]);
  const tasks = useAsync<Task[]>(() => (allowed ? api!.listTasks() : Promise.resolve([])), [api, tick]);
  const staff = useAsync<StaffMember[]>(() => (allowed ? api!.listStaff() : Promise.resolve([])), [api, tick]);
  const hasFocused = useRef(false);
  useFocusEffect(useCallback(() => {
    if (hasFocused.current) {
      void summary.reload(); void tasks.reload(); void staff.reload();
    } else hasFocused.current = true;
  }, [summary.reload, tasks.reload, staff.reload]));

  if (!allowed) return <Screen><Title>{t('admin.title')}</Title><Empty text={t('admin.forbidden')} /></Screen>;
  const s = summary.data;
  const queue = (tasks.data ?? []).filter((x) => x.status === 'IN_INSPECTION');
  const unassigned = (tasks.data ?? []).filter((x) => !x.assigned_to_id && x.status === 'OPEN' && (x.type === 'HOUSEKEEPING' || x.type === 'MAINTENANCE'));
  const eligibleStaff = (task: Task) => (staff.data ?? []).filter((member) => member.active !== false && member.role === (task.type === 'HOUSEKEEPING' ? 'MAID' : 'TECHNICIAN'));
  const assign = async (staffId: string) => { if (!pick) return; await api!.assignTask(pick, staffId); setPick(null); setTick((n) => n + 1); };
  const approve = async (id: string) => { await api!.setTaskStatus(id, 'DONE'); setTick((n) => n + 1); };
  const back = async (id: string) => { await api!.setTaskStatus(id, 'IN_PROGRESS'); setTick((n) => n + 1); };

  return (
    <Screen>
      <Title>{t('admin.title')}</Title>
      {tasks.error ? <Card onPress={tasks.reload}><Text style={[font.body, { color: c.danger }]}>{t('errors.generic')} · {t('common.retry')}</Text></Card> : null}
      {staff.error ? <Card onPress={staff.reload}><Text style={[font.body, { color: c.danger }]}>{t('errors.forbidden')} · {t('common.retry')}</Text></Card> : null}
      {s ? (
        <FadeIn style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.md }}>
          <Stat icon={Percent} label={t('admin.occupancy')} value={`${s.occupancy_pct}%`} tone={c.primary} />
          <Stat icon={BedDouble} label={t('admin.dirty')} value={String(s.dirty)} tone={c.warning} />
          <Stat icon={Wrench} label={t('admin.blocked')} value={String(s.blocked)} tone={c.danger} />
          <Stat icon={Clock} label={t('admin.overdue')} value={String(s.overdue)} tone={c.info} />
        </FadeIn>
      ) : null}

      <SectionLabel>{t('admin.inspection')}</SectionLabel>
      {!tasks.loading && !tasks.error && queue.length === 0 ? <Empty text={t('common.empty')} /> : null}
      {queue.map((task) => (
        <View key={task.id} style={{ gap: space.sm }}>
          <TaskCard task={task} onPress={() => router.push({ pathname: '/task/[id]', params: { id: task.id } })} />
          <View style={{ flexDirection: 'row', gap: space.sm }}>
            <View style={{ flex: 1 }}><Button testID={`approve-${task.id}`} label={t('tasks.approve')} icon={CheckCircle2} onPress={() => approve(task.id)} /></View>
            <View style={{ flex: 1 }}><Button label={t('tasks.reject')} variant="secondary" onPress={() => back(task.id)} /></View>
          </View>
        </View>
      ))}

      <SectionLabel>{t('admin.unassigned')}</SectionLabel>
      {!tasks.loading && !tasks.error && unassigned.length === 0 ? <Empty text={t('common.empty')} /> : null}
      {unassigned.map((task) => (
        <View key={task.id} style={{ gap: space.sm }}>
          <TaskCard task={task} onPress={() => setPick(pick === task.id ? null : task.id)} />
          {pick === task.id ? (
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.sm }}>
              {eligibleStaff(task).map((m) => (
                <PressScale key={m.id} testID={`assign-${m.id}`} onPress={() => assign(m.id)} style={{ minHeight: 48, paddingHorizontal: 16, justifyContent: 'center', borderRadius: radius.pill, backgroundColor: c.primarySoft }}>
                  <Text style={[font.small, { color: c.primary, fontWeight: '700' }]}>{m.display_name} · {m.open_tasks}</Text>
                </PressScale>
              ))}
              {eligibleStaff(task).length === 0 ? <Empty text={t('admin.noEligible')} /> : null}
            </View>
          ) : <Badge label={t('admin.assign')} tone="primary" />}
        </View>
      ))}

      <SectionLabel>{t('admin.staff')}</SectionLabel>
      {(staff.data ?? []).filter((m) => m.active !== false).map((m) => (
        <Card key={m.id} style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
          <View><Text style={[font.h2, { color: c.text }]}>{m.display_name}</Text><Text style={[font.small, { color: c.textMuted }]}>{t(`roles.${m.role}`)}</Text></View>
          <Badge label={String(m.open_tasks)} tone={m.open_tasks > 2 ? 'warning' : 'success'} />
        </Card>
      ))}
    </Screen>
  );
}
