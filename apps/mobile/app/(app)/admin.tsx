import React, { useCallback, useRef, useState } from 'react';
import { Text, View } from 'react-native';
import { useFocusEffect, useRouter } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { CheckCircle2, UsersRound, ClipboardCheck } from 'lucide-react-native';
import { Badge, Button, Card, Empty, PressScale, SectionLabel } from '../../src/components/ui';
import { TaskCard } from '../../src/components/domain';
import { demoTaskTitle } from '../../src/i18n/demoLabels';
import { FutureScreen, GlassCard, LoadingShimmer, PremiumHeader } from '../../src/components/Future';
import { useAsync } from '../../src/lib/useAsync';
import { wasWriteRejected } from '../../src/lib/writeOutcome';
import { useSession } from '../../src/state/session';
import { contactInitials } from '../../src/i18n/statusLabels';
import { workspaceForSession } from '../../src/roles/registry';
import { useTheme } from '../../src/theme/ThemeProvider';
import { font, radius, space } from '../../src/theme/tokens';
import type { StaffMember, Task } from '../../src/api/types';

export default function Admin() {
  const { t } = useTranslation();
  const { c } = useTheme();
  const router = useRouter();
  const { api, user, hotel, serverAuthMode, locale } = useSession();
  const allowed = workspaceForSession(user!.role, user!.module_permissions, api?.mode ?? 'LIVE', serverAuthMode).canManage;
  const [pick, setPick] = useState<string | null>(null);
  const [actionBusy, setActionBusy] = useState(false);
  const actionLock = useRef(false);
  const [actionError, setActionError] = useState<string | null>(null);
  // Never repeat a staff write if its server acknowledgment was lost.
  const [unknownResult, setUnknownResult] = useState(false);
  const [tick, setTick] = useState(0);
  const tasks = useAsync<Task[]>(() => (allowed ? api!.listTasks() : Promise.resolve([])), [api, tick]);
  const staff = useAsync<StaffMember[]>(() => (allowed ? api!.listStaff() : Promise.resolve([])), [api, tick]);
  const reloadTasks = tasks.reload;
  const reloadStaff = staff.reload;
  const hasFocused = useRef(false);
  useFocusEffect(useCallback(() => {
    if (hasFocused.current) {
      void reloadTasks(); void reloadStaff();
    } else hasFocused.current = true;
  }, [reloadTasks, reloadStaff]));

  if (!allowed) return <FutureScreen><PremiumHeader title={t('admin.title')} subtitle={hotel?.name} eyebrow="MARINA SMART"/><Empty text={t('admin.forbidden')} /></FutureScreen>;
  const queue = (tasks.data ?? []).filter((x) => x.status === 'IN_INSPECTION');
  const unassigned = (tasks.data ?? []).filter((x) => !x.assigned_to_id && x.status === 'OPEN' && (x.type === 'HOUSEKEEPING' || x.type === 'MAINTENANCE'));
  const eligibleStaff = (task: Task) => (staff.data ?? []).filter((member) => member.active !== false && member.role === (task.type === 'HOUSEKEEPING' ? 'MAID' : 'TECHNICIAN'));
  const runMutation = async (operation: () => Promise<unknown>) => {
    if (actionLock.current || unknownResult || !api || !allowed) return;
    actionLock.current = true;
    setActionBusy(true);
    setActionError(null);
    try {
      await operation();
      setPick(null);
      setTick((n) => n + 1);
    } catch (e: unknown) {
      const rejected = wasWriteRejected(e);
      if (!rejected) setUnknownResult(true);
      const code = e && typeof e === 'object' && 'code' in e ? String(e.code) : '';
      setActionError(!rejected ? t('errors.resultUnknown') : t(code === 'FORBIDDEN' ? 'errors.forbidden' : 'errors.generic'));
      // Do not trust stale task data after a lost acknowledgment.
    } finally {
      actionLock.current = false;
      setActionBusy(false);
    }
  };
  const assign = (staffId: string) => { if (pick) void runMutation(() => api!.assignTask(pick, staffId)); };
  const approve = (id: string) => { void runMutation(() => api!.setTaskStatus(id, 'DONE')); };
  const back = (id: string) => { void runMutation(() => api!.setTaskStatus(id, 'IN_PROGRESS')); };

  return (
    <FutureScreen>
      <PremiumHeader title={t('admin.title')} subtitle={hotel?.name} eyebrow="MARINA SMART"/>
      {!tasks.loading && !staff.loading && !tasks.error && !staff.error ? <GlassCard style={{ flexDirection: 'row', gap: space.md, alignItems: 'center' }}>
        <View style={{ width: 48, height: 48, borderRadius: 16, backgroundColor: c.primarySoft, justifyContent: 'center', alignItems: 'center' }}><UsersRound size={25} color={c.primary}/></View>
        <View style={{ flex: 1 }}><Text style={[font.metric, { color: c.text }]}>{(staff.data ?? []).filter(m => m.active !== false).length}</Text><Text style={[font.small, { color: c.textMuted }]}>{t('admin.staff')}</Text></View>
        <View style={{ gap: 4, alignItems: 'center' }}><ClipboardCheck size={22} color={c.warning}/><Text style={[font.h2, { color: c.warning }]}>{queue.length}</Text><Text style={[font.small, { color: c.textMuted }]}>{t('admin.inspection')}</Text></View>
      </GlassCard> : null}
      {(tasks.loading || staff.loading) && !tasks.data && !staff.data ? <LoadingShimmer count={2}/> : null}
      {actionBusy ? <Text accessibilityRole="alert" style={[font.small, { color: c.textMuted }]}>{t('common.loading')}</Text> : null}
      {actionError ? <Text testID={unknownResult ? "admin-unknown-result" : "admin-action-error"} accessibilityRole="alert" style={[font.body, { color: unknownResult ? c.warning : c.danger }]}>{actionError}</Text> : null}
      {tasks.error ? <Card onPress={tasks.reload}><Text style={[font.body, { color: c.danger }]}>{t('errors.generic')} · {t('common.retry')}</Text></Card> : null}
      {staff.error ? <Card onPress={staff.reload}><Text style={[font.body, { color: c.danger }]}>{t('errors.forbidden')} · {t('common.retry')}</Text></Card> : null}

      <SectionLabel>{t('admin.inspection')}</SectionLabel>
      {!tasks.loading && !tasks.error && queue.length === 0 ? <Empty text={t('common.empty')} /> : null}
      {queue.map((task) => (
        <View key={task.id} style={{ gap: space.sm }}>
          <TaskCard task={api?.mode === 'DEMO' ? { ...task, title: demoTaskTitle(task.id, locale, task.title) } : task} onPress={() => router.push({ pathname: '/task/[id]', params: { id: task.id } })} />
          <View style={{ flexDirection: 'row', gap: space.sm }}>
            <View style={{ flex: 1 }}><Button testID={`approve-${task.id}`} label={t('tasks.approve')} icon={CheckCircle2} onPress={() => approve(task.id)} disabled={actionBusy || unknownResult} /></View>
            <View style={{ flex: 1 }}><Button label={t('tasks.reject')} variant="secondary" onPress={() => back(task.id)} disabled={actionBusy || unknownResult} /></View>
          </View>
        </View>
      ))}

      <SectionLabel>{t('admin.unassigned')}</SectionLabel>
      {!tasks.loading && !tasks.error && unassigned.length === 0 ? <Empty text={t('common.empty')} /> : null}
      {unassigned.map((task) => (
        <View key={task.id} style={{ gap: space.sm }}>
          <TaskCard task={api?.mode === 'DEMO' ? { ...task, title: demoTaskTitle(task.id, locale, task.title) } : task} onPress={() => setPick(pick === task.id ? null : task.id)} />
          {pick === task.id ? (
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.sm }}>
              {eligibleStaff(task).map((m) => (
                <PressScale key={m.id} testID={`assign-${m.id}`} onPress={() => assign(m.id)} disabled={actionBusy || unknownResult} style={{ minHeight: 48, paddingHorizontal: 16, justifyContent: 'center', borderRadius: radius.pill, backgroundColor: c.primarySoft }}>
                  <Text style={[font.small, { color: c.primary, fontWeight: '700' }]}>{m.display_name} · {m.open_tasks}</Text>
                </PressScale>
              ))}
              {eligibleStaff(task).length === 0 ? <Empty text={t('admin.noEligible')} /> : null}
            </View>
          ) : <PressScale testID={`open-assign-${task.id}`} accessibilityLabel={t('admin.assign')} onPress={() => setPick(task.id)} disabled={actionBusy || unknownResult}
              style={{ alignSelf: 'flex-start', minHeight: 48, paddingHorizontal: 18, justifyContent: 'center', borderRadius: radius.pill, backgroundColor: c.primarySoft, borderWidth: 1, borderColor: c.border }}>
              <Text style={[font.body, { color: c.primary, fontWeight: '700' }]}>{t('admin.assign')}</Text>
            </PressScale>}
        </View>
      ))}

      <SectionLabel>{t('admin.staff')}</SectionLabel>
      {(staff.data ?? []).filter((m) => m.active !== false).map((m) => (
        <Card key={m.id} style={{ flexDirection: 'row', gap: space.md, alignItems: 'center', minHeight: 76 }}>
          <View style={{ width: 45, height: 45, borderRadius: 23, backgroundColor: c.primarySoft, alignItems: 'center', justifyContent: 'center' }}><Text style={[font.h2, { color: c.primary }]}>{contactInitials(m.display_name) ?? '•'}</Text></View>
          <View style={{ flex: 1, minWidth: 0 }}><Text style={[font.h2, { color: c.text }]} numberOfLines={1}>{m.display_name}</Text><Text style={[font.small, { color: c.textMuted }]}>{t(`roles.${m.role}`)}</Text></View>
          <Badge label={String(m.open_tasks)} tone={m.open_tasks > 2 ? 'warning' : 'success'} />
        </Card>
      ))}
    </FutureScreen>
  );
}
