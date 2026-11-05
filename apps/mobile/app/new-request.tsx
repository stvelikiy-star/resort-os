import React, { useEffect, useRef, useState } from 'react';
import { Text, View } from 'react-native';
import { Redirect, useRouter } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { Droplets, Fan, Lamp, Package, Zap, X } from 'lucide-react-native';
import { Button, Field, PressScale, SectionLabel, Segmented } from '../src/components/ui';
import { useAsync } from '../src/lib/useAsync';
import { FutureScreen, PremiumHeader, GlassCard, LoadingShimmer, ErrorState } from '../src/components/Future';
import { useSession } from '../src/state/session';
import { workspaceForSession } from '../src/roles/registry';
import { useTheme } from '../src/theme/ThemeProvider';
import { font, radius, space } from '../src/theme/tokens';
import type { Priority, Room } from '../src/api/types';
import { wasWriteRejected } from '../src/lib/writeOutcome';

const CATS = [{ k: 'PLUMBING', I: Droplets }, { k: 'ELECTRIC', I: Zap }, { k: 'HVAC', I: Fan }, { k: 'FURNITURE', I: Lamp }, { k: 'OTHER', I: Package }] as const;

export default function NewRequest() {
  const { t } = useTranslation();
  const { c } = useTheme();
  const router = useRouter();
  const { api, user, hotel, serverAuthMode } = useSession();
  const rooms = useAsync<Room[]>(() => api ? api.listRooms() : Promise.resolve([]), [api]);
  const [cat, setCat] = useState<string>('PLUMBING');
  const [prio, setPrio] = useState<Priority>('NORMAL');
  const [roomId, setRoomId] = useState<string | null>(null);
  const [text, setText] = useState('');
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [unknownResult, setUnknownResult] = useState(false);
  const sendLock = useRef(false);
  const returnTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => () => { if (returnTimer.current) clearTimeout(returnTimer.current); }, []);

  const send = async () => {
    if (sendLock.current || unknownResult || !api || !user || !workspaceForSession(user.role, user.module_permissions, api.mode, serverAuthMode).canCreateMaintenance) return;
    sendLock.current = true;
    setBusy(true); setMsg(null);
    let accepted = false;
    let rejected = false;
    try {
      await api.createMaintenance({ room_id: roomId, category: cat, priority: prio, description: text });
      accepted = true;
      setMsg(t('mt.sent'));
      returnTimer.current = setTimeout(() => router.back(), 600);
    } catch (error: unknown) {
      rejected = wasWriteRejected(error);
      if (!rejected) setUnknownResult(true);
      setMsg(rejected ? t('errors.generic') : t('mt.resultUnknown'));
    } finally {
      // Never unlock an ambiguous POST. The server might have committed it
      // even though the acknowledgment could not reach this device.
      if (!accepted && rejected) sendLock.current = false;
      if (!accepted) setBusy(false);
    }
  };

  if (!user || !api) return <Redirect href="/connect" />;
  if (!workspaceForSession(user.role, user.module_permissions, api.mode).canCreateMaintenance) return <Redirect href="/profile" />;

  return (
    <FutureScreen>
      <PremiumHeader title={t('mt.title')} subtitle={hotel?.name} eyebrow="MARINA SMART" inlineCompactRight
        right={<PressScale onPress={() => router.back()} accessibilityLabel={t('common.cancel')}
          style={{ minHeight: 48, minWidth: 48, borderRadius: radius.pill, backgroundColor: c.surfaceAlt, alignItems: 'center', justifyContent: 'center' }}><X size={25} color={c.textMuted}/></PressScale>}/>
      <SectionLabel>{t('common.room')}</SectionLabel>
      {rooms.loading && !rooms.data ? <LoadingShimmer count={1}/> : null}
      {rooms.error ? <ErrorState text={rooms.error.message} retry={t('common.retry')} onRetry={rooms.reload}/> : null}
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.sm }}>
        {(rooms.data ?? []).map((r) => (
          <PressScale key={r.id} testID={`pick-room-${r.id}`} onPress={() => setRoomId(roomId === r.id ? null : r.id)} style={{ minHeight: 48, paddingHorizontal: 16, justifyContent: 'center', borderRadius: radius.pill, backgroundColor: roomId === r.id ? c.primary : c.surfaceAlt }}>
            <Text style={[font.small, { fontWeight: '800', color: roomId === r.id ? c.primaryText : c.text }]}>{r.code}</Text>
          </PressScale>
        ))}
      </View>
      <SectionLabel>{t('mt.category')}</SectionLabel>
      <GlassCard style={{ gap: space.sm }}>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.sm }}>
        {CATS.map(({ k, I }) => (
          <PressScale key={k} testID={`cat-${k}`} onPress={() => setCat(k)} style={{ width: 104, height: 84, alignItems: 'center', justifyContent: 'center', gap: 6, borderRadius: radius.md, backgroundColor: cat === k ? c.primarySoft : c.surface, borderWidth: 1.5, borderColor: cat === k ? c.primary : c.border }}>
            <I size={26} color={cat === k ? c.primary : c.textMuted} /><Text style={[font.small, { color: c.text }]}>{t(`mt.cats.${k}`)}</Text>
          </PressScale>
        ))}
      </View>
      </GlassCard>
      <SectionLabel>{t('mt.priority')}</SectionLabel>
      <Segmented<Priority> value={prio} onChange={setPrio} options={[{ key: 'LOW', label: t('tasks.low') }, { key: 'NORMAL', label: t('tasks.normal') }, { key: 'HIGH', label: t('tasks.high') }, { key: 'URGENT', label: t('tasks.urgent') }]} />
      <Field label={t('mt.describe')} placeholder={t('mt.describePh')} value={text} onChangeText={setText} multiline testID="mt-text" style={{ minHeight: 110, paddingTop: 14, textAlignVertical: 'top' }} />
      <Button testID="mt-send" label={t('mt.send')} onPress={send} disabled={busy || unknownResult || text.trim().length < 2} />
      {unknownResult ? <Button testID="mt-check-existing" variant="secondary" label={t('mt.checkExisting')} onPress={() => router.back()} /> : null}
      {msg ? <GlassCard><Text testID={unknownResult ? 'mt-unknown-result' : 'mt-msg'} accessibilityRole="alert" style={[font.body, { color: unknownResult ? c.warning : c.primary, fontWeight: '700' }]}>{msg}</Text></GlassCard> : null}
    </FutureScreen>
  );
}
