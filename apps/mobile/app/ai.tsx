import React, { useRef, useState } from 'react';
import { Keyboard, Text, TextInput, View } from 'react-native';
import { Redirect, useRouter } from 'expo-router';
import { ChevronLeft, Send, ShieldCheck, Sparkles, UserRound } from 'lucide-react-native';
import { useTheme } from '../src/theme/ThemeProvider';
import { useSession } from '../src/state/session';
import { useMobileCopy, aiMobileCopy } from '../src/i18n/mobileCopy';
import { AssistantCapabilities, AssistantMessage, useLiveModules } from '../src/api/liveModules';
import { useAsync } from '../src/lib/useAsync';
import { AIOrb, ErrorState, FutureScreen, GlassCard, LoadingShimmer, PremiumHeader, StatusPill } from '../src/components/Future';
import { Button, DemoBanner, Empty, PressScale, SectionLabel } from '../src/components/ui';
import { font, radius, space } from '../src/theme/tokens';


export default function Assistant() {
  const { user, locale, serverAuthMode, api } = useSession();
  const modules = useLiveModules();
  const live = serverAuthMode === 'shared_auth_preview' ? null : modules;
  const copy = useMobileCopy();
  const { c } = useTheme();
  const t = aiMobileCopy[locale];
  const router = useRouter();
  const [prompt, setPrompt] = useState('');
  const [inputFocused, setInputFocused] = useState(false);
  const [messages, setMessages] = useState<AssistantMessage[]>([]);
  const [lastLive, setLastLive] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);
  const lock = useRef(false);
  const [busy, setBusy] = useState(false);
  const { data: capabilities, loading, error: capsError, reload } = useAsync<AssistantCapabilities | null>(() => live ? live.assistantCapabilities() : Promise.resolve(null), [live, user?.id]);
  const send = async () => {
    const query = prompt.trim();
    if (!live || !capabilities?.configured || lock.current || !query || query.length > 3000) return;
    lock.current = true; setBusy(true); setError(null);
    try {
      const transcript: AssistantMessage[] = [...messages.slice(-9), { role: 'user', content: query }];
      const answer = await live.assistantChat(transcript, locale, 'DASHBOARD');
      if (!answer || !answer.read_only || typeof answer.answer !== 'string' || answer.property_code !== user?.property_code) {
        throw new Error('Invalid assistant response context');
      }
      setMessages([...transcript, { role: 'assistant' as const, content: answer.answer }].slice(-10));
      setLastLive(answer.live_context_available);
      setPrompt('');
      Keyboard.dismiss();
    } catch (e) { setError(e instanceof Error ? e.message : copy.unknown); }
    finally { lock.current = false; setBusy(false); }
  };
  if (!user) return <Redirect href="/connect"/>;
  if (serverAuthMode === 'shared_auth_preview') return <FutureScreen><Empty text={copy.unavailable}/></FutureScreen>;
  if (!['OWNER','MANAGER','RECEPTION'].includes(user.role)) return <FutureScreen><Empty text={copy.denied}/></FutureScreen>;
  return <FutureScreen>
    <PressScale accessibilityLabel={t.back} onPress={() => router.back()} style={{ flexDirection: 'row', alignItems: 'center', minHeight: 44, gap: 4 }}>
      <ChevronLeft size={22} color={c.primary}/><Text style={[font.body, { color: c.primary }]}>{t.back}</Text>
    </PressScale>
    <PremiumHeader title={t.title} subtitle={t.sub} eyebrow="MARINA SMART"/>
    {api?.mode === 'DEMO' ? <DemoBanner/> : null}
    <View style={{ alignItems: 'center', gap: 8 }}>
      <AIOrb state={!live ? 'offline' : error || capsError ? 'error' : busy ? 'processing' : 'idle'} size={110} label={t.title}/>
      <StatusPill label={busy ? t.processing : capabilities?.configured ? t.ready : t.offline} tone={capabilities?.configured ? 'success' : 'warning'}/>
    </View>
    {loading ? <LoadingShimmer count={1}/> : null}
    {capsError ? <ErrorState text={capsError.message} retry={copy.retry} onRetry={reload}/> : null}
    {!live || capabilities?.configured === false ? <GlassCard><Text style={[font.body, { color: c.textMuted }]}>{t.unavailable}</Text></GlassCard> : null}
    <GlassCard style={{ flexDirection: 'row', alignItems: 'flex-start', gap: 10 }}>
      <ShieldCheck size={22} color={c.success}/><Text style={[font.small, { color: c.textMuted, flex: 1 }]}>{t.rights}</Text>
    </GlassCard>
    <SectionLabel>{t.title}</SectionLabel>
    {messages.length === 0 ? <Empty text={t.empty}/> : messages.map((m, i) =>
      <GlassCard key={i} style={{
        alignSelf: m.role === 'user' ? 'flex-end' : 'stretch', maxWidth: m.role === 'user' ? '92%' : '100%',
        borderLeftWidth: m.role === 'assistant' ? 3 : 1,
        borderLeftColor: m.role === 'assistant' ? c.cyan : c.glassBorder,
        backgroundColor: m.role === 'user' ? c.primarySoft : c.surface, gap: space.sm,
      }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 7 }}>
          {m.role === 'assistant' ? <Sparkles size={17} color={c.cyan}/> : <UserRound size={17} color={c.primary}/>}
          <Text style={[font.label, { color: c.textMuted }]}>{m.role === 'assistant' ? t.title : user.display_name}</Text>
        </View>
        <Text selectable style={[font.body, { color: c.text }]}>{m.content}</Text>
      </GlassCard>)}
    {busy ? <GlassCard style={{ gap: space.sm, borderLeftWidth: 3, borderLeftColor: c.cyan }}>
      <Text accessibilityRole="alert" style={[font.small, { color: c.textMuted }]}>{t.processing}</Text>
      <LoadingShimmer count={1}/>
    </GlassCard> : null}
    {lastLive !== null ? <Text style={[font.small, { color: c.textMuted }]}>{t.source}: {lastLive ? t.yes : t.no}</Text> : null}
    {error ? <GlassCard><Text accessibilityRole="alert" style={[font.small, { color: c.danger }]}>{error}</Text></GlassCard> : null}
    <View style={{ gap: space.sm }}>
      <TextInput testID="ai-question" accessibilityLabel={t.prompt} placeholder={t.prompt} placeholderTextColor={c.textMuted}
        value={prompt} onChangeText={setPrompt} editable={!!live && !!capabilities?.configured && !busy}
        onFocus={() => setInputFocused(true)} onBlur={() => setInputFocused(false)} maxLength={3000} multiline style={{
          color: c.text, backgroundColor: c.surface, borderWidth: inputFocused ? 2 : 1, borderColor: inputFocused ? c.primary : c.border, borderRadius: radius.lg,
          padding: space.lg, minHeight: 80, fontSize: 16, textAlignVertical: 'top',
        }}/>
      <Button testID="ai-send" label={t.send} icon={Send} disabled={busy || !capabilities?.configured || !prompt.trim()} onPress={() => void send()}/>
    </View>
  </FutureScreen>;
}
