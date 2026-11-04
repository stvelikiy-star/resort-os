import React, { useRef, useState } from 'react';
import { Text, View } from 'react-native';
import { Redirect, useLocalSearchParams, useRouter } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { Camera, Check, ChevronLeft, Play, Send, Square } from 'lucide-react-native';
import { AnimatedProgressBar, Badge, Button, Empty, Field, PressScale, SectionLabel } from '../../src/components/ui';
import { prioKey, priorityTone, statusKey } from '../../src/components/domain';
import { useAsync } from '../../src/lib/useAsync';
import { ErrorState, FutureScreen, GlassCard, LoadingShimmer, PremiumHeader } from '../../src/components/Future';
import { wasWriteRejected } from '../../src/lib/writeOutcome';
import { useSession } from '../../src/state/session';
import { workspaceForSession } from '../../src/roles/registry';
import { useTheme } from '../../src/theme/ThemeProvider';
import { font, radius, space, TOUCH } from '../../src/theme/tokens';
import { ApiError, canTransition, HOUSEKEEPING_CHECKLIST, Task } from '../../src/api/types';

export default function TaskDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { t } = useTranslation();
  const { c } = useTheme();
  const router = useRouter();
  const { api, user, hotel, serverAuthMode } = useSession();
  const ws = workspaceForSession(user?.role ?? 'AGENT', user?.module_permissions, api?.mode ?? 'LIVE', serverAuthMode);
  const { data: task, loading, error, reload, setData } = useAsync<Task | null>(async () => user && api && ws.mobileReady ? (await api.listTasks()).find((x) => x.id === id) ?? null : null, [api, id, user?.id]);
  const [checks, setChecks] = useState<Record<string, boolean>>({});
  const [comment, setComment] = useState('');
  const [msg, setMsg] = useState<string | null>(null);
  const [actionError, setActionError] = useState(false);
  const [busy, setBusy] = useState(false);
  const [unknownResult, setUnknownResult] = useState(false);
  const actionLock = useRef(false);

  const run = async (fn: () => Promise<Task>, okMsg?: string) => {
    if (actionLock.current || unknownResult || !user || !api || !ws.mobileReady) return;
    actionLock.current = true;
    setBusy(true); setMsg(null); setActionError(false);
    try {
      const n = await fn();
      setData(n);
      if (okMsg) setMsg(okMsg);
    } catch (e: unknown) {
      const rejected = wasWriteRejected(e);
      if (!rejected) setUnknownResult(true);
      setActionError(rejected);
      const code = e instanceof ApiError ? e.code : 'UNKNOWN';
      setMsg(!rejected ? t('errors.resultUnknown') : t(code === 'FORBIDDEN' ? 'errors.forbidden' : 'errors.generic'));
    } finally {
      actionLock.current = false;
      setBusy(false);
    }
  };

  if (!user || !api) return <Redirect href="/connect" />;
  if (!ws.mobileReady) return <Redirect href="/profile" />;
  if (loading && !task) return <FutureScreen><LoadingShimmer count={3}/></FutureScreen>;
  if (error) return <FutureScreen><ErrorState text={error.message} retry={t('common.retry')} onRetry={reload}/></FutureScreen>;
  if (!task) return <FutureScreen><Empty text={t('errors.notFound')} /></FutureScreen>;
  const isHk = task.type === 'HOUSEKEEPING';
  const allChecked = HOUSEKEEPING_CHECKLIST.every((k) => checks[k]);
  const checkedCount = HOUSEKEEPING_CHECKLIST.filter(k => checks[k]).length;
  const canInspect = ws.canManage;

  return (
    <FutureScreen>
      <PressScale onPress={() => router.back()} style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }} accessibilityLabel={t('common.back')}>
        <ChevronLeft size={22} color={c.primary} /><Text style={[font.body, { color: c.primary }]}>{t('common.back')}</Text>
      </PressScale>
      <PremiumHeader title={task.room_code ?? t('common.room')} subtitle={hotel?.name} eyebrow={t(`tasks.types.${task.type}`)}/>
      <GlassCard style={{ gap: space.sm, borderLeftWidth: 4, borderLeftColor: priorityTone(task.priority) === 'danger' ? c.danger : priorityTone(task.priority) === 'warning' ? c.warning : c.primary }}>
        <Text style={[font.h2, { color: c.text }]}>{task.title}</Text>
        <View style={{ flexDirection: 'row', gap: 6, flexWrap: 'wrap' }}>
          <Badge label={t(statusKey(task.status))} tone={task.status === 'DONE' ? 'success' : task.status === 'IN_INSPECTION' ? 'info' : task.status === 'IN_PROGRESS' ? 'primary' : 'neutral'} />
          <Badge label={t(prioKey(task.priority))} tone={priorityTone(task.priority)} />
          {task.due_label ? <Badge label={task.due_label} /> : null}
        </View>
        {task.assigned_to_name ? <Text style={[font.small, { color: c.textMuted }]}>{task.assigned_to_name}</Text> : null}
      </GlassCard>

      {isHk && task.status === 'IN_PROGRESS' ? (
        <>
          <SectionLabel>{t('hk.title')} · {checkedCount}/{HOUSEKEEPING_CHECKLIST.length}</SectionLabel>
          <GlassCard style={{ gap: 7 }}>
            <Text style={[font.small, { color: c.textMuted }]}>{t('tasks.progress')} · {checkedCount}/{HOUSEKEEPING_CHECKLIST.length}</Text>
            <AnimatedProgressBar percent={Math.round(checkedCount / HOUSEKEEPING_CHECKLIST.length * 100)}/>
          </GlassCard>
          {HOUSEKEEPING_CHECKLIST.map((k) => {
            const on = !!checks[k];
            return (
              <PressScale key={k} testID={`check-${k}`} onPress={() => setChecks((s) => ({ ...s, [k]: !s[k] }))}
                style={{ minHeight: TOUCH + 8, flexDirection: 'row', alignItems: 'center', gap: space.md, padding: space.md, borderRadius: radius.md, backgroundColor: on ? c.successSoft : c.surface, borderWidth: 1.5, borderColor: on ? c.success : c.border }}>
                <View style={{ width: 34, height: 34, borderRadius: 10, alignItems: 'center', justifyContent: 'center', backgroundColor: on ? c.success : c.surfaceAlt }}>
                  {on ? <Check size={20} color="#fff" /> : <Square size={18} color={c.textMuted} />}
                </View>
                <Text style={[font.body, { color: c.text, flex: 1, fontWeight: '700' }]}>{t(`hk.${k}`)}</Text>
              </PressScale>
            );
          })}
          <SectionLabel>{t('hk.photo')}</SectionLabel>
          <GlassCard style={{ flexDirection: 'row', alignItems: 'center', gap: space.md, opacity: 0.7 }}>
            <Camera size={26} color={c.textMuted} /><Text style={[font.small, { color: c.textMuted, flex: 1 }]}>{t('hk.photoSoon')}</Text>
          </GlassCard>
          <Field label={t('hk.comment')} value={comment} onChangeText={setComment} multiline />
          <Button testID="hk-submit" label={t('hk.submit')} icon={Send} disabled={busy || unknownResult || !allChecked}
            onPress={() => run(() => api!.completeHousekeeping(task.id, { checklist: checks, comment }), t('hk.sent'))} />
          {!allChecked ? <Text style={[font.small, { color: c.textMuted }]}>{t('hk.incomplete')}</Text> : null}
        </>
      ) : null}

      {task.status === 'OPEN' ? <Button testID="task-start" label={t('tasks.start')} icon={Play} disabled={busy || unknownResult} onPress={() => run(() => api!.claimTask(task.id))} /> : null}
      {!isHk && task.status === 'IN_PROGRESS' && canTransition(task.type, 'IN_PROGRESS', 'DONE') ? <Button testID="task-finish" label={t('tasks.finish')} icon={Check} disabled={busy || unknownResult} onPress={() => run(() => api!.setTaskStatus(task.id, 'DONE'))} /> : null}
      {isHk && task.status === 'IN_INSPECTION' && canInspect ? (
        <View style={{ gap: space.sm }}>
          <Button testID="task-approve" label={t('tasks.approve')} icon={Check} disabled={busy || unknownResult} onPress={() => run(() => api!.setTaskStatus(task.id, 'DONE'))} />
          <Button label={t('tasks.reject')} variant="secondary" disabled={busy || unknownResult} onPress={() => run(() => api!.setTaskStatus(task.id, 'IN_PROGRESS'))} />
        </View>
      ) : null}
      {msg ? <Text testID={unknownResult ? "task-unknown-result" : "task-msg"} accessibilityRole="alert"
        style={[font.body, { color: unknownResult ? c.warning : actionError ? c.danger : c.success, fontWeight: '700' }]}>{msg}</Text> : null}
    </FutureScreen>
  );
}
