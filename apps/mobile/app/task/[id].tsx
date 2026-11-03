import React, { useState } from 'react';
import { Text, View } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { Camera, Check, ChevronLeft, Play, Send, Square } from 'lucide-react-native';
import { Badge, Button, Card, Empty, Field, PressScale, Screen, SectionLabel, Title } from '../../src/components/ui';
import { prioKey, priorityTone, statusKey } from '../../src/components/domain';
import { useAsync } from '../../src/lib/useAsync';
import { useSession } from '../../src/state/session';
import { workspaceFor } from '../../src/roles/registry';
import { useTheme } from '../../src/theme/ThemeProvider';
import { font, radius, space, TOUCH } from '../../src/theme/tokens';
import { canTransition, HOUSEKEEPING_CHECKLIST, Task } from '../../src/api/types';

export default function TaskDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { t } = useTranslation();
  const { c } = useTheme();
  const router = useRouter();
  const { api, user } = useSession();
  const ws = workspaceFor(user!.role);
  const { data: task, loading, setData } = useAsync<Task | null>(async () => (await api!.listTasks()).find((x) => x.id === id) ?? null, [api, id]);
  const [checks, setChecks] = useState<Record<string, boolean>>({});
  const [comment, setComment] = useState('');
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const run = async (fn: () => Promise<Task>, okMsg?: string) => {
    setBusy(true); setMsg(null);
    try { const n = await fn(); setData(n); if (okMsg) setMsg(okMsg); } catch (e: any) { setMsg(t(e?.code === 'FORBIDDEN' ? 'errors.forbidden' : e?.code === 'OFFLINE' ? 'errors.offline' : 'errors.generic')); } finally { setBusy(false); }
  };

  if (loading && !task) return <Screen><Empty text={t('common.loading')} /></Screen>;
  if (!task) return <Screen><Empty text={t('errors.notFound')} /></Screen>;
  const isHk = task.type === 'HOUSEKEEPING';
  const allChecked = HOUSEKEEPING_CHECKLIST.every((k) => checks[k]);
  const canInspect = ws.canManage || user!.role === 'RECEPTION';

  return (
    <Screen>
      <PressScale onPress={() => router.back()} style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }} accessibilityLabel={t('common.back')}>
        <ChevronLeft size={22} color={c.primary} /><Text style={[font.body, { color: c.primary }]}>{t('common.back')}</Text>
      </PressScale>
      <Title sub={t(`tasks.types.${task.type}`)}>{task.room_code ?? t('common.room')}</Title>
      <Card style={{ gap: space.sm }}>
        <Text style={[font.h2, { color: c.text }]}>{task.title}</Text>
        <View style={{ flexDirection: 'row', gap: 6, flexWrap: 'wrap' }}>
          <Badge label={t(statusKey(task.status))} tone="primary" />
          <Badge label={t(prioKey(task.priority))} tone={priorityTone(task.priority)} />
          {task.due_label ? <Badge label={task.due_label} /> : null}
        </View>
        {task.assigned_to_name ? <Text style={[font.small, { color: c.textMuted }]}>{task.assigned_to_name}</Text> : null}
      </Card>

      {isHk && task.status === 'IN_PROGRESS' ? (
        <>
          <SectionLabel>{t('hk.title')}</SectionLabel>
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
          <Card style={{ flexDirection: 'row', alignItems: 'center', gap: space.md, opacity: 0.7 }}>
            <Camera size={26} color={c.textMuted} /><Text style={[font.small, { color: c.textMuted, flex: 1 }]}>{t('hk.photoSoon')}</Text>
          </Card>
          <Field label={t('hk.comment')} value={comment} onChangeText={setComment} multiline />
          <Button testID="hk-submit" label={t('hk.submit')} icon={Send} disabled={busy || !allChecked}
            onPress={() => run(() => api!.completeHousekeeping(task.id, { checklist: checks, comment }), t('hk.sent'))} />
          {!allChecked ? <Text style={[font.small, { color: c.textMuted }]}>{t('hk.incomplete')}</Text> : null}
        </>
      ) : null}

      {task.status === 'OPEN' ? <Button testID="task-start" label={t('tasks.start')} icon={Play} disabled={busy} onPress={() => run(() => api!.claimTask(task.id))} /> : null}
      {!isHk && task.status === 'IN_PROGRESS' && canTransition(task.type, 'IN_PROGRESS', 'DONE') ? <Button testID="task-finish" label={t('tasks.finish')} icon={Check} disabled={busy} onPress={() => run(() => api!.setTaskStatus(task.id, 'DONE'))} /> : null}
      {isHk && task.status === 'IN_INSPECTION' && canInspect ? (
        <View style={{ gap: space.sm }}>
          <Button testID="task-approve" label={t('tasks.approve')} icon={Check} disabled={busy} onPress={() => run(() => api!.setTaskStatus(task.id, 'DONE'))} />
          <Button label={t('tasks.reject')} variant="secondary" disabled={busy} onPress={() => run(() => api!.setTaskStatus(task.id, 'IN_PROGRESS'))} />
        </View>
      ) : null}
      {msg ? <Text testID="task-msg" style={[font.body, { color: c.primary, fontWeight: '700' }]}>{msg}</Text> : null}
    </Screen>
  );
}
