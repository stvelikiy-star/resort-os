import React, { useCallback, useMemo, useRef, useState } from 'react';
import { Text, TextInput, View } from 'react-native';
import { useFocusEffect, useRouter } from 'expo-router';
import { MessageCircle, ChevronRight, Search, ShieldCheck } from 'lucide-react-native';
import { Badge, Empty, Segmented, DemoBanner } from '../../src/components/ui';
import { ErrorState, FutureScreen, GlassCard, LoadingShimmer, PremiumHeader, StaggerItem } from '../../src/components/Future';
import { Conversation, useLiveModules } from '../../src/api/liveModules';
import { useMobileCopy } from '../../src/i18n/mobileCopy';
import { chatStatusLabel, contactInitials } from '../../src/i18n/statusLabels';
import { formatChatTimestamp } from '../../src/i18n/dateLabels';
import { demoConversations } from '../../src/api/demoPresentation';
import { useAsync } from '../../src/lib/useAsync';
import { useSession } from '../../src/state/session';
import { hasTabForSession } from '../../src/roles/registry';
import { useTheme } from '../../src/theme/ThemeProvider';
import { font, radius, space } from '../../src/theme/tokens';

export default function Inbox() {
  const { hotel, user, locale, api, serverAuthMode } = useSession();
  const showroom = api?.mode === 'DEMO';
  const allowed = !!user && hasTabForSession(user.role, user.module_permissions, api?.mode ?? 'LIVE', 'inbox', serverAuthMode);
  const live = useLiveModules();
  const router = useRouter();
  const copy = useMobileCopy();
  const { c } = useTheme();
  const [filter, setFilter] = useState<'needs' | 'all'>('needs');
  const [search, setSearch] = useState('');
  const { data, loading, error, reload } = useAsync<Conversation[] | null>(() => !allowed ? Promise.resolve(null) : showroom ? Promise.resolve(demoConversations(locale).filter(x => filter !== 'needs' || x.needs_reply)) : live ? live.conversations(filter === 'needs') : Promise.resolve(null), [live, showroom, filter, user?.id, locale, allowed]);
  const focused = useRef(false);
  useFocusEffect(useCallback(() => { if (focused.current) void reload(); else focused.current = true; }, [reload]));
  const visible = useMemo(() => (user?.role === 'RECEPTION' ? (data ?? []).filter(x => x.channel_kind === 'WHATSAPP') : data ?? []).filter(x => {
    const query = search.toLocaleLowerCase().trim();
    if (!query) return true;
    return [x.contact_name, x.contact_phone, x.last_message_text].some(value => (value ?? '').toLocaleLowerCase().includes(query));
  }), [data, user?.role, search]);
  if (!allowed) return <FutureScreen><Empty text={copy.denied}/></FutureScreen>;
  return <FutureScreen>
    <PremiumHeader title={copy.inboxTitle} subtitle={hotel?.name} eyebrow="MARINA SMART"
      right={<View style={{ width:44,height:44,borderRadius:14,backgroundColor:c.primarySoft,alignItems:'center',justifyContent:'center' }}><MessageCircle color={c.primary} size={24}/></View>}/>
    {showroom ? <DemoBanner/> : null}
    <Segmented value={filter} options={[{key:'needs', label:copy.needsReply},{key:'all', label:copy.all}]} onChange={setFilter}/>
    <View style={{flexDirection:'row',alignItems:'center',gap:10,borderWidth:1,borderColor:c.border,borderRadius:radius.md,backgroundColor:c.surface,paddingHorizontal:14,minHeight:54}}>
      <Search size={20} color={c.textMuted}/>
      <TextInput accessibilityLabel={copy.inboxTitle} placeholder={copy.inboxTitle} placeholderTextColor={c.textMuted}
        value={search} onChangeText={setSearch} autoCorrect={false} style={[font.body,{color:c.text,flex:1,paddingVertical:9}]}/>
    </View>
    {!live && !showroom ? <Empty text={copy.unavailable}/> : null}
    {loading && (live || showroom) ? <LoadingShimmer count={4}/> : null}
    {error ? <ErrorState text={error.message} retry={copy.retry} onRetry={reload}/> : null}
    {!loading && !error && (live || showroom) && visible.length > 0 ? <Text style={[font.label,{color:c.textMuted}]}>{visible.length} · {filter==='needs'?copy.needsReply:copy.all}</Text> : null}
    {visible.map((x, i) => <StaggerItem key={x.id} index={i}>
      <GlassCard testID={'conversation-' + x.id} onPress={() => router.push({ pathname:'/conversation/[id]', params:{id:x.id} })}>
        <View style={{flexDirection:'row',alignItems:'center',gap:space.md}}>
          <View style={{width:48,height:48,borderRadius:24,alignItems:'center',justifyContent:'center',backgroundColor:c.primarySoft}}>
            {contactInitials(x.contact_name) ? <Text style={[font.h2, { color: c.primary }]}>{contactInitials(x.contact_name)}</Text> : <MessageCircle color={c.primary} size={24}/>}
          </View>
          <View style={{flex:1,gap:6}}>
            <View style={{flexDirection:'row',alignItems:'center',justifyContent:'space-between',gap:6}}>
              <Text style={[font.h2,{color:c.text,flex:1,minWidth:0}]} numberOfLines={1}>{x.contact_name || x.contact_phone || '—'}</Text>
              {x.needs_reply ? <View accessible accessibilityLabel={copy.needsReply} style={{width:9,height:9,borderRadius:5,backgroundColor:c.warning}}/> : null}
            </View>
            {formatChatTimestamp(x.last_message_at, locale) ? <Text style={[font.label,{color:c.textMuted}]}>{formatChatTimestamp(x.last_message_at, locale)}</Text> : null}
            <Text style={[font.small,{color:c.textMuted}]} numberOfLines={2}>{x.last_message_text || copy.empty}</Text>
            <View style={{flexDirection:'row',alignItems:'center',gap:6,flexWrap:'wrap'}}>
              <Badge label={x.channel_kind} tone="info"/>
              <Badge label={chatStatusLabel(x.status, copy)} tone={x.status === 'RESOLVED' ? 'success' : 'primary'}/>
              {x.needs_reply ? <Badge label={copy.needsReply} tone="warning"/> : null}
              {x.assigned_to_name ? <Badge label={copy.assigned + ': ' + x.assigned_to_name} tone="neutral"/> : null}
            </View>
          </View>
          <ChevronRight color={c.primary} size={21}/>
        </View>
      </GlassCard>
    </StaggerItem>)}
    {!loading && !error && (live || showroom) && visible.length === 0 ? <Empty text={copy.empty}/> : null}
    <GlassCard style={{flexDirection:'row',gap:10,alignItems:'center'}}>
      <ShieldCheck size={22} color={c.warning}/>
      <Text style={[font.small,{color:c.textMuted,flex:1}]}>{copy.noSend}</Text>
    </GlassCard>
  </FutureScreen>;
}
