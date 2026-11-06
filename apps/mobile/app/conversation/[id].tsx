import React, { useRef, useState } from 'react';
import { Alert, Text, View, useWindowDimensions } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { ChevronLeft, MessageSquareText, CheckCheck, AlertTriangle } from 'lucide-react-native';
import { Badge, Button, Empty, Field, PressScale, SectionLabel, DemoBanner } from '../../src/components/ui';
import { ErrorState, FutureScreen, GlassCard, LoadingShimmer, PremiumHeader } from '../../src/components/Future';
import { ConversationDetail, useLiveModules } from '../../src/api/liveModules';
import { useMobileCopy } from '../../src/i18n/mobileCopy';
import { chatStatusLabel, deliveryStatusLabel, messageDirectionLabel } from '../../src/i18n/statusLabels';
import { formatChatTimestamp } from '../../src/i18n/dateLabels';
import { demoConversationDetail } from '../../src/api/demoPresentation';
import { useAsync } from '../../src/lib/useAsync';
import { wasWriteRejected } from '../../src/lib/writeOutcome';
import { hasTabForSession } from '../../src/roles/registry';
import { useSession } from '../../src/state/session';
import { useTheme } from '../../src/theme/ThemeProvider';
import { font, space } from '../../src/theme/tokens';

export default function ConversationScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { user, serverAuthMode, locale, api } = useSession();
  const showroom = api?.mode === 'DEMO';
  const allowed = !!user && hasTabForSession(user.role, user.module_permissions, api?.mode ?? 'LIVE', 'inbox', serverAuthMode);
  const modules = useLiveModules();
  const live = modules;
  const copy = useMobileCopy();
  const router = useRouter();
  const { c } = useTheme();
  const { width } = useWindowDimensions();
  const [note, setNote] = useState('');
  const [feedback, setFeedback] = useState<string | null>(null);
  const locked = useRef(false);
  const [busy, setBusy] = useState(false);
  const [unknownResult, setUnknownResult] = useState(false);
  const { data, loading, error, reload } = useAsync<ConversationDetail | null>(() => !allowed ? Promise.resolve(null) : showroom && id ? Promise.resolve(demoConversationDetail(id, locale)) : live && id ? live.conversation(id) : Promise.resolve(null), [live, showroom, id, user?.id, locale, allowed]);
  const act = async (run: () => Promise<unknown>, clear = false) => {
    if (locked.current || unknownResult || !allowed || !live) return;
    locked.current = true; setBusy(true); setFeedback(null);
    try { await run(); if (clear) setNote(''); setFeedback(copy.confirmed); await reload(); }
    catch(error: unknown) {
      const rejected = wasWriteRejected(error);
      if (!rejected) setUnknownResult(true);
      setFeedback(rejected ? copy.conflict : copy.resultUnknown);
    }
    finally { locked.current = false; setBusy(false); }
  };
  if (!allowed) return <FutureScreen><Empty text={copy.denied}/></FutureScreen>;
  const conversation = data?.conversation;
  return <FutureScreen>
    <PressScale accessibilityLabel={copy.close} onPress={() => router.back()} style={{ flexDirection: 'row', alignItems: 'center', minHeight: 44, gap: 6 }}><ChevronLeft size={22} color={c.primary}/><Text style={[font.body, { color: c.primary }]}>{copy.close}</Text></PressScale>
    <PremiumHeader title={conversation?.contact_name || conversation?.contact_phone || copy.inboxTitle} subtitle={conversation?.channel_kind} eyebrow="MARINA SMART"/>
    {showroom ? <DemoBanner/> : null}
    {loading ? <LoadingShimmer count={3}/> : null}
    {error ? <ErrorState text={error.message} retry={copy.retry} onRetry={reload}/> : null}
    {conversation ? <>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: space.sm }}>
        <Badge label={chatStatusLabel(conversation.status, copy)} tone="primary"/>
        {conversation.needs_reply ? <Badge label={copy.needsReply} tone="warning"/> : null}
      </View>
      <Text style={[font.small, { color: c.textMuted }]}>{copy.assigned}: {conversation.assigned_to_name || '—'}</Text>
      <SectionLabel>{copy.inboxTitle}</SectionLabel>
      {(data?.messages ?? []).map(m => <GlassCard key={m.id} style={{
        alignSelf: m.direction === 'OUTBOUND' ? 'flex-end' : m.direction === 'INBOUND' ? 'flex-start' : 'stretch',
        maxWidth: m.direction === 'INTERNAL' ? '100%' : width < 350 ? '96%' : '88%',
        gap: space.sm,
        borderBottomLeftRadius: m.direction === 'INBOUND' ? 8 : undefined,
        borderBottomRightRadius: m.direction === 'OUTBOUND' ? 8 : undefined,
        backgroundColor: m.direction === 'INTERNAL' ? c.warningSoft : m.direction === 'OUTBOUND' ? c.primarySoft : c.surface,
      }}>
        <Text style={[font.label, { color: c.textMuted }]}>{messageDirectionLabel(m.direction, copy)}</Text>
        <Text style={[font.body, { color: c.text }]}>{m.text || '—'}</Text>
        <View style={{flexDirection:'row',justifyContent:'flex-end',alignItems:'center',gap:5,flexWrap:'wrap'}}>
          {m.delivery_status === 'FAILED' ? <AlertTriangle size={14} color={c.danger}/> : m.delivery_status === 'READ' ? <CheckCheck size={14} color={c.success}/> : null}
          {m.delivery_status ? <Text style={[font.small, { color: m.delivery_status === 'FAILED' ? c.danger : c.textMuted }]}>{deliveryStatusLabel(m.delivery_status, copy)}</Text> : null}
          {formatChatTimestamp(m.created_at, locale) ? <Text style={[font.small, { color: c.textMuted }]}>{formatChatTimestamp(m.created_at, locale)}</Text> : null}
        </View>
      </GlassCard>)}
      {data?.messages.length === 0 ? <Empty text={copy.empty}/> : null}
      {!showroom && conversation.assigned_to_id === null ? <Button testID="claim-conversation" label={copy.claim} disabled={busy || unknownResult} onPress={() => void act(() => live!.claimConversation(id!))}/> : null}
      {!showroom ? <View style={{ flexDirection: 'row', gap: space.sm }}>
        <View style={{ flex: 1 }}><Button variant="secondary" label={conversation.status === 'RESOLVED' ? copy.reopen : copy.resolve} disabled={busy || unknownResult}
          onPress={() => Alert.alert(copy.confirm, '', [{text: copy.close, style:'cancel'}, {text: copy.choose, onPress: () => void act(() => live!.conversationStatus(id!, conversation.status === 'RESOLVED' ? 'OPEN' : 'RESOLVED'))}])}/></View>
      </View> : null}
      {!showroom ? <>
      <SectionLabel>{copy.note}</SectionLabel>
      <Field label={copy.notePlaceholder} value={note} onChangeText={setNote} multiline maxLength={12000} testID="internal-note-input"/>
      <Button label={copy.saveNote} testID="save-internal-note" disabled={busy || unknownResult || !note.trim()} onPress={() => void act(() => live!.internalNote(id!, note.trim()), true)}/>
      </> : null}
      <GlassCard><View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}><MessageSquareText size={22} color={c.warning}/><Text style={[font.small, { flex: 1, color: c.textMuted }]}>{copy.noSend}</Text></View></GlassCard>
      {feedback ? <Text testID={unknownResult ? 'inbox-unknown-result' : 'inbox-feedback'} accessibilityRole="alert" style={[font.small, { color: unknownResult ? c.warning : c.primary }]}>{feedback}</Text> : null}
    </> : null}
  </FutureScreen>;
}
