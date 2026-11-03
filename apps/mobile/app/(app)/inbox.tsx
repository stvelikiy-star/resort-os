import React, { useCallback, useRef, useState } from 'react';
import { Text, View } from 'react-native';
import { useFocusEffect, useRouter } from 'expo-router';
import { MessageCircle, ChevronRight } from 'lucide-react-native';
import { Badge, Card, Empty, Screen, Segmented, Title } from '../../src/components/ui';
import { Conversation, useLiveModules } from '../../src/api/liveModules';
import { useMobileCopy } from '../../src/i18n/mobileCopy';
import { useAsync } from '../../src/lib/useAsync';
import { useSession } from '../../src/state/session';
import { useTheme } from '../../src/theme/ThemeProvider';
import { font, space } from '../../src/theme/tokens';

export default function Inbox() {
  const { hotel, user } = useSession();
  const live = useLiveModules();
  const router = useRouter();
  const copy = useMobileCopy();
  const { c } = useTheme();
  const [filter, setFilter] = useState<'needs' | 'all'>('needs');
  const { data, loading, error, reload } = useAsync<Conversation[] | null>(() => live ? live.conversations(filter === 'needs') : Promise.resolve(null), [live, filter, user?.id]);
  const focused = useRef(false);
  useFocusEffect(useCallback(() => { if (focused.current) void reload(); else focused.current = true; }, [reload]));
  const filtered = user?.role === 'RECEPTION' ? (data ?? []).filter(x => x.channel_kind === 'WHATSAPP') : data ?? [];
  return <Screen>
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}><MessageCircle size={30} color={c.primary}/><View style={{ flex: 1 }}><Title sub={hotel?.name}>{copy.inboxTitle}</Title></View></View>
    <Segmented value={filter} options={[{key:'needs', label:copy.needsReply},{key:'all', label:copy.all}]} onChange={setFilter}/>
    {!live ? <Empty text={copy.unavailable} /> : null}
    {loading && live ? <Empty text={copy.loading} /> : null}
    {error ? <Card onPress={reload}><Text accessibilityRole="alert" style={[font.body, { color: c.danger }]}>{error.message} · {copy.retry}</Text></Card> : null}
    {filtered.map(x => <Card key={x.id} testID={'conversation-' + x.id} onPress={() => router.push({ pathname: '/conversation/[id]', params: { id: x.id } })}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: space.md }}>
        <View style={{ flex: 1, gap: 6 }}>
          <Text style={[font.h2, { color: c.text }]} numberOfLines={1}>{x.contact_name || x.contact_phone || '—'}</Text>
          <Text style={[font.small, { color: c.textMuted }]} numberOfLines={2}>{x.last_message_text || copy.empty}</Text>
          <View style={{ flexDirection: 'row', gap: 6 }}><Badge label={x.channel_kind} tone="info"/>{x.needs_reply ? <Badge label={copy.needsReply} tone="warning"/> : null}</View>
        </View>
        <ChevronRight size={22} color={c.primary}/>
      </View>
    </Card>)}
    {!loading && !error && live && filtered.length === 0 ? <Empty text={copy.empty} /> : null}
    <Card><Text style={[font.small, { color: c.textMuted }]}>{copy.noSend}</Text></Card>
  </Screen>;
}
