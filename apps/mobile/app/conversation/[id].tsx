import React, { useRef, useState } from 'react';
import { Alert, Text, View } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { ChevronLeft, MessageSquareText } from 'lucide-react-native';
import { Badge, Button, Empty, Field, PressScale, SectionLabel } from '../../src/components/ui';
import { ErrorState, FutureScreen, GlassCard, LoadingShimmer, PremiumHeader } from '../../src/components/Future';
import { ConversationDetail, useLiveModules } from '../../src/api/liveModules';
import { useMobileCopy } from '../../src/i18n/mobileCopy';
import { useAsync } from '../../src/lib/useAsync';
import { wasWriteRejected } from '../../src/lib/writeOutcome';
import { useSession } from '../../src/state/session';
import { useTheme } from '../../src/theme/ThemeProvider';
import { font, space } from '../../src/theme/tokens';

export default function ConversationScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { user, serverAuthMode } = useSession();
  const modules = useLiveModules();
  const live = serverAuthMode === 'shared_auth_preview' ? null : modules;
  const copy = useMobileCopy();
  const router = useRouter();
  const { c } = useTheme();
  const [note, setNote] = useState('');
  const [feedback, setFeedback] = useState<string | null>(null);
  const locked = useRef(false);
  const [busy, setBusy] = useState(false);
  const [unknownResult, setUnknownResult] = useState(false);
  const { data, loading, error, reload } = useAsync<ConversationDetail | null>(() => live && id ? live.conversation(id) : Promise.resolve(null), [live, id, user?.id]);
  const act = async (run: () => Promise<unknown>, clear = false) => {
    if (locked.current || unknownResult) return;
    locked.current = true; setBusy(true); setFeedback(null);
    try { await run(); if (clear) setNote(''); setFeedback(copy.confirmed); await reload(); }
    catch(error: unknown) {
      const rejected = wasWriteRejected(error);
      if (!rejected) setUnknownResult(true);
      setFeedback(rejected ? copy.conflict : copy.resultUnknown);
    }
    finally { locked.current = false; setBusy(false); }
  };
  if (serverAuthMode === 'shared_auth_preview') return <FutureScreen><Empty text={copy.unavailable}/></FutureScreen>;
  if (!user || !(user.module_permissions?.includes('WHATSAPP') || (user.role !== 'RECEPTION' && user.module_permissions?.includes('INBOX'))) || !['OWNER','MANAGER','RECEPTION'].includes(user.role)) return <FutureScreen><Empty text={copy.denied}/></FutureScreen>;
  const conversation = data?.conversation;
  return <FutureScreen>
    <PressScale onPress={() => router.back()} style={{ flexDirection: 'row', alignItems: 'center', minHeight: 44, gap: 6 }}><ChevronLeft size={22} color={c.primary}/><Text style={[font.body, { color: c.primary }]}>{copy.close}</Text></PressScale>
    <PremiumHeader title={conversation?.contact_name || conversation?.contact_phone || copy.inboxTitle} subtitle={conversation?.channel_kind} eyebrow="MARINA SMART"/>
    {loading ? <LoadingShimmer count={3}/> : null}
    {error ? <ErrorState text={error.message} retry={copy.retry} onRetry={reload}/> : null}
    {conversation ? <>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.sm }}>
        <Badge label={conversation.status} tone="primary"/>
        {conversation.needs_reply ? <Badge label={copy.needsReply} tone="warning"/> : null}
      </View>
      <Text style={[font.small, { color: c.textMuted }]}>{copy.assigned}: {conversation.assigned_to_name || '—'}</Text>
      <SectionLabel>{copy.inboxTitle}</SectionLabel>
      {(data?.messages ?? []).map(m => <GlassCard key={m.id} style={{ backgroundColor: m.direction === 'INTERNAL' ? c.warningSoft : m.direction === 'OUTBOUND' ? c.primarySoft : c.surface }}>
        <Text style={[font.label, { color: c.textMuted }]}>{m.direction === 'INTERNAL' ? copy.note : m.direction} · {m.created_at.slice(0, 16)}</Text>
        <Text style={[font.body, { color: c.text, marginTop: 6 }]}>{m.text || '—'}</Text>
        {m.delivery_status ? <Text style={[font.small, { color: c.textMuted }]}>{m.delivery_status}</Text> : null}
      </GlassCard>)}
      {data?.messages.length === 0 ? <Empty text={copy.empty}/> : null}
      {conversation.assigned_to_id === null ? <Button testID="claim-conversation" label={copy.claim} disabled={busy || unknownResult} onPress={() => void act(() => live!.claimConversation(id!))}/> : null}
      <View style={{ flexDirection: 'row', gap: space.sm }}>
        <View style={{ flex: 1 }}><Button variant="secondary" label={conversation.status === 'RESOLVED' ? copy.reopen : copy.resolve} disabled={busy || unknownResult}
          onPress={() => Alert.alert(copy.confirm, '', [{text: copy.close, style:'cancel'}, {text: copy.choose, onPress: () => void act(() => live!.conversationStatus(id!, conversation.status === 'RESOLVED' ? 'OPEN' : 'RESOLVED'))}])}/></View>
      </View>
      <SectionLabel>{copy.note}</SectionLabel>
      <Field label={copy.notePlaceholder} value={note} onChangeText={setNote} multiline maxLength={12000} testID="internal-note-input"/>
      <Button label={copy.saveNote} testID="save-internal-note" disabled={busy || unknownResult || !note.trim()} onPress={() => void act(() => live!.internalNote(id!, note.trim()), true)}/>
      <GlassCard><View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}><MessageSquareText size={22} color={c.warning}/><Text style={[font.small, { flex: 1, color: c.textMuted }]}>{copy.noSend}</Text></View></GlassCard>
      {feedback ? <Text testID={unknownResult ? 'inbox-unknown-result' : 'inbox-feedback'} accessibilityRole="alert" style={[font.small, { color: unknownResult ? c.warning : c.primary }]}>{feedback}</Text> : null}
    </> : null}
  </FutureScreen>;
}
