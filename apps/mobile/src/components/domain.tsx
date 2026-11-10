import React from 'react';
import { Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';
import { AlertTriangle, ArrowUpRight, BedDouble, Check, ClipboardCheck, Hammer, HelpCircle, Sparkles, Wrench } from 'lucide-react-native';
import type { Priority, RoomState, Task, TaskStatus, TaskType } from '../api/types';
import { useTheme } from '../theme/ThemeProvider';
import { font, radius, space } from '../theme/tokens';
import { Badge, Card, toneColors } from './ui';

export const typeIcon = (t: TaskType) => (t === 'HOUSEKEEPING' ? Sparkles : t === 'MAINTENANCE' ? Wrench : HelpCircle);
export const roomTone = (s: RoomState) => (s === 'CLEAN' ? 'success' : s === 'DIRTY' ? 'warning' : s === 'IN_INSPECTION' ? 'info' : s === 'TECH_BLOCK' ? 'danger' : 'neutral') as 'success' | 'warning' | 'info' | 'danger' | 'neutral';
export const priorityTone = (p: Priority) => (p === 'URGENT' ? 'danger' : p === 'HIGH' ? 'warning' : p === 'NORMAL' ? 'info' : 'neutral') as 'danger' | 'warning' | 'info' | 'neutral';
export const statusKey = (s: TaskStatus) => (s === 'OPEN' ? 'tasks.open' : s === 'IN_PROGRESS' ? 'tasks.inProgress' : s === 'IN_INSPECTION' ? 'tasks.inspection' : 'tasks.done');
export const prioKey = (p: Priority) => `tasks.${p.toLowerCase()}`;

export function RoomStateBadge({ state }: { state: RoomState }) {
  const { t } = useTranslation();
  return <Badge label={t(`rooms.state.${state}`)} tone={roomTone(state)} />;
}

export function TaskCard({ task, onPress }: { task: Task; onPress: () => void }) {
  const { t } = useTranslation();
  const { c } = useTheme();
  const tone = task.status === 'DONE' ? 'success' : task.status === 'IN_INSPECTION' ? 'info' : task.status === 'IN_PROGRESS' ? 'primary' : 'neutral';
  const tc = toneColors(c, priorityTone(task.priority));
  return (
    <Card testID={`task-${task.id}`} onPress={onPress} style={{
      flexDirection: 'row', gap: space.md, alignItems: 'center',
      borderLeftWidth: 4, borderLeftColor: tc.fg, minHeight: 118, paddingVertical: 17,
    }}>
      <View style={{ width: 54, height: 54, borderRadius: radius.md, backgroundColor: tc.bg, alignItems: 'center', justifyContent: 'center' }}>
        {task.priority === 'URGENT' ? <AlertTriangle size={27} color={tc.fg} strokeWidth={1.9}/> : React.createElement(typeIcon(task.type), { size: 27, color: tc.fg, strokeWidth: 1.9 })}
      </View>
      <View style={{ flex: 1, minWidth: 0, gap: 5 }}>
        <Text style={[font.h2, { color: c.text }]} numberOfLines={2}>{task.room_code ?? t('common.room')} · {t(`tasks.types.${task.type}`)}</Text>
        <Text style={[font.small, { color: c.textMuted }]} numberOfLines={2}>{task.title}</Text>
        <View style={{ flexDirection: 'row', gap: 6, flexWrap: 'wrap', marginTop: 3 }}>
          <Badge label={t(statusKey(task.status))} tone={tone}/>
          {['URGENT', 'HIGH'].includes(task.priority) ? <Badge label={t(prioKey(task.priority))} tone={priorityTone(task.priority)}/> : null}
          {task.due_label ? <Badge label={task.due_label}/> : null}
        </View>
      </View>
      <ArrowUpRight size={20} color={c.textMuted}/>
    </Card>
  );
}

export { BedDouble, Check, ClipboardCheck, Hammer };
