import React, { useState } from 'react';
import { Text, View } from 'react-native';
import { Redirect, useRouter } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { Droplets, Fan, Lamp, Package, Zap, X } from 'lucide-react-native';
import { Button, Field, PressScale, Screen, SectionLabel, Segmented, Title } from '../src/components/ui';
import { useAsync } from '../src/lib/useAsync';
import { useSession } from '../src/state/session';
import { workspaceForSession } from '../src/roles/registry';
import { useTheme } from '../src/theme/ThemeProvider';
import { font, radius, space } from '../src/theme/tokens';
import type { Priority, Room } from '../src/api/types';

const CATS = [{ k: 'PLUMBING', I: Droplets }, { k: 'ELECTRIC', I: Zap }, { k: 'HVAC', I: Fan }, { k: 'FURNITURE', I: Lamp }, { k: 'OTHER', I: Package }] as const;

export default function NewRequest() {
  const { t } = useTranslation();
  const { c } = useTheme();
  const router = useRouter();
  const { api, user } = useSession();
  const rooms = useAsync<Room[]>(() => api ? api.listRooms() : Promise.resolve([]), [api]);
  const [cat, setCat] = useState<string>('PLUMBING');
  const [prio, setPrio] = useState<Priority>('NORMAL');
  const [roomId, setRoomId] = useState<string | null>(null);
  const [text, setText] = useState('');
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const send = async () => {
    if (busy || !api || !user || !workspaceForSession(user.role, user.module_permissions, api.mode).canCreateMaintenance) return;
    setBusy(true); setMsg(null);
    try { await api!.createMaintenance({ room_id: roomId, category: cat, priority: prio, description: text }); setMsg(t('mt.sent')); setTimeout(() => router.back(), 600); }
    catch { setMsg(t('errors.generic')); } finally { setBusy(false); }
  };

  if (!user || !api) return <Redirect href="/connect" />;
  if (!workspaceForSession(user.role, user.module_permissions, api.mode).canCreateMaintenance) return <Redirect href="/profile" />;

  return (
    <Screen>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title>{t('mt.title')}</Title>
        <PressScale onPress={() => router.back()} accessibilityLabel={t('common.cancel')}><X size={28} color={c.textMuted} /></PressScale>
      </View>
      <SectionLabel>{t('common.room')}</SectionLabel>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.sm }}>
        {(rooms.data ?? []).map((r) => (
          <PressScale key={r.id} testID={`pick-room-${r.id}`} onPress={() => setRoomId(roomId === r.id ? null : r.id)} style={{ minHeight: 48, paddingHorizontal: 16, justifyContent: 'center', borderRadius: radius.pill, backgroundColor: roomId === r.id ? c.primary : c.surfaceAlt }}>
            <Text style={[font.small, { fontWeight: '800', color: roomId === r.id ? c.primaryText : c.text }]}>{r.code}</Text>
          </PressScale>
        ))}
      </View>
      <SectionLabel>{t('mt.category')}</SectionLabel>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.sm }}>
        {CATS.map(({ k, I }) => (
          <PressScale key={k} testID={`cat-${k}`} onPress={() => setCat(k)} style={{ width: 104, height: 84, alignItems: 'center', justifyContent: 'center', gap: 6, borderRadius: radius.md, backgroundColor: cat === k ? c.primarySoft : c.surface, borderWidth: 1.5, borderColor: cat === k ? c.primary : c.border }}>
            <I size={26} color={cat === k ? c.primary : c.textMuted} /><Text style={[font.small, { color: c.text }]}>{t(`mt.cats.${k}`)}</Text>
          </PressScale>
        ))}
      </View>
      <SectionLabel>{t('mt.priority')}</SectionLabel>
      <Segmented<Priority> value={prio} onChange={setPrio} options={[{ key: 'LOW', label: t('tasks.low') }, { key: 'NORMAL', label: t('tasks.normal') }, { key: 'HIGH', label: t('tasks.high') }, { key: 'URGENT', label: t('tasks.urgent') }]} />
      <Field label={t('mt.describe')} placeholder={t('mt.describePh')} value={text} onChangeText={setText} multiline testID="mt-text" style={{ minHeight: 110, paddingTop: 14, textAlignVertical: 'top' }} />
      <Button testID="mt-send" label={t('mt.send')} onPress={send} disabled={busy || text.trim().length < 2} />
      {msg ? <Text testID="mt-msg" style={[font.body, { color: c.primary, fontWeight: '700' }]}>{msg}</Text> : null}
    </Screen>
  );
}
