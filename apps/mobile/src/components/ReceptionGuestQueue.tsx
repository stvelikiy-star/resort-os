import React, { useRef, useState } from 'react';
import { Text } from 'react-native';
import type { createLiveModules, ReceptionGuestRequest } from '../api/liveModules';
import type { Locale } from '../i18n';
import type { AuthUser, AuthMode } from '../api/types';
import { useMobileCopy } from '../i18n/mobileCopy';
import { useAsync } from '../lib/useAsync';
import { useTheme } from '../theme/ThemeProvider';
import { font, space } from '../theme/tokens';
import { Badge, Button, Card, Empty, SectionLabel } from './ui';

const labels = {
  ru: ['Заявки гостей', 'Взять в работу', 'Завершить', 'Новая', 'В работе', 'Выполнено', 'Обновить', 'Не удалось загрузить заявки', 'Действие не подтверждено. Проверьте статус в очереди.'],
  kg: ['Коноктордун өтүнүчтөрү', 'Ишке алуу', 'Аяктоо', 'Жаңы', 'Аткарылууда', 'Аткарылды', 'Жаңыртуу', 'Өтүнүчтөр жүктөлгөн жок', 'Аракет ырасталган жок. Өтүнүчтөрдүн абалын текшериңиз.'],
  kz: ['Қонақтардың өтініштері', 'Жұмысқа алу', 'Аяқтау', 'Жаңа', 'Жұмыста', 'Орындалды', 'Жаңарту', 'Өтініштер жүктелмеді', 'Әрекет расталмады. Өтініштердің күйін тексеріңіз.'],
  en: ['Guest requests', 'Claim', 'Complete', 'New', 'In progress', 'Completed', 'Refresh', 'Could not load guest requests', 'Action unconfirmed. Check the refreshed queue.'],
} as const;

export function canUseStaffGuestQueue(user: AuthUser | null | undefined, mode: AuthMode | null) {
  return !!user && mode !== 'shared_auth_preview' &&
    ['RECEPTION', 'MAID', 'TECHNICIAN'].includes(user.role) &&
    (!user.module_permissions_custom || user.module_permissions.includes('OPS') || user.module_permissions.includes('SERVICES'));
}

export function StaffGuestQueue({ live, userId, locale }: {
  live: Pick<ReturnType<typeof createLiveModules>, 'receptionGuestRequests' | 'updateReceptionGuestRequest'>;
  userId: string;
  locale: Locale;
}) {
  const copy = useMobileCopy();
  const { c } = useTheme();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState('');
  const lock = useRef(false);
  const t = labels[locale];
  const queue = useAsync(() => open ? live.receptionGuestRequests() : Promise.resolve([]), [open, live]);

  async function act(item: ReceptionGuestRequest, action: 'claim' | 'complete') {
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    setFeedback('');
    try {
      const status = await live.updateReceptionGuestRequest(item.id, action, userId);
      setFeedback(item.title + ' · ' + (status === 'DONE' ? t[5] : t[4]));
    } catch {
      // The request could have committed before the connection failed.
      // Refresh the server state before offering another action.
      setFeedback(t[8]);
    } finally {
      await queue.reload();
      setBusy(false);
      lock.current = false;
    }
  }

  return <>
    <Button testID="reception-guest-queue" label={t[0]} variant="secondary" disabled={busy}
      onPress={() => setOpen(value => !value)}/>
    {open ? <>
      <SectionLabel>{t[0]}</SectionLabel>
      <Button label={t[6]} variant="secondary" disabled={busy || queue.loading} onPress={() => void queue.reload()}/>
      {feedback ? <Text accessibilityRole="alert" style={[font.small, { color: c.text }]}>{feedback}</Text> : null}
      {queue.error ? <Empty text={t[7]}/> : null}
      {!queue.loading && queue.data?.length === 0 ? <Empty text={copy.empty}/> : null}
      {queue.data?.map(item => <Card key={item.id} testID={'guest-request-' + item.id} style={{ gap: space.sm }}>
        <Text style={[font.h2, { color: c.text }]}>{item.title}</Text>
        <Badge label={item.status === 'OPEN' ? t[3] : t[4]} tone="info"/>
        <Text style={[font.small, { color: c.textMuted }]}>
          {[item.room_code, item.service_date, item.service_time, item.description].filter(Boolean).join(' · ')}
        </Text>
        {item.status === 'OPEN' && (!item.assigned_to_id || item.assigned_to_id === userId) ?
          <Button testID={'guest-claim-' + item.id} label={t[1]} disabled={busy} onPress={() => void act(item, 'claim')}/> : null}
        {item.status === 'IN_PROGRESS' && item.assigned_to_id === userId ?
          <Button testID={'guest-complete-' + item.id} label={t[2]} disabled={busy} onPress={() => void act(item, 'complete')}/> : null}
      </Card>)}
    </> : null}
  </>;
}
