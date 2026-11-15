import React, { useRef, useState } from 'react';
import { Alert, Text, TextInput, View } from 'react-native';
import type { createLiveModules } from '../api/liveModules';
import { useAsync } from '../lib/useAsync';
import { useSession } from '../state/session';
import { useTheme } from '../theme/ThemeProvider';
import { GlassCard, ErrorState, LoadingShimmer } from './Future';
import { Button, SectionLabel } from './ui';
import { useMobileCopy } from '../i18n/mobileCopy';

const copy = {
  ru: { title:'Стоп-лист кухни', stop:'Убрать из заказов', stopped:'В стоп-листе', ready:'В продаже',
    reason:'Причина отсутствия ингредиентов', confirm:'Остановить блюдо?',
    note:'Повар может приостановить продажу. Возобновление выполняет OWNER или MANAGER.', empty:'Опубликованных блюд нет' },
  kg: { title:'Ашкананын стоп тизмеси', stop:'Заказдан алып салуу', stopped:'Стоп тизмеде', ready:'Сатууда',
    reason:'Керектүү азык жок', confirm:'Тамакты токтотобузбу?',
    note:'Ашпозчу сатууну токтото алат. Кайра иштетүүнү OWNER же MANAGER аткарат.', empty:'Жарыяланган тамак жок' },
  en: { title:'Kitchen stop-list', stop:'Stop new orders', stopped:'Stopped', ready:'Available',
    reason:'Ingredients unavailable', confirm:'Stop new orders for this dish?',
    note:'COOK may stop sales. Only OWNER or MANAGER can restore.', empty:'No published dishes' },
  kz: { title:'Асүйдің тоқтату тізімі', stop:'Тапсырыстан алып тастау', stopped:'Тоқтатылған', ready:'Сатылымда',
    reason:'Ингредиенттер жоқ', confirm:'Бұл тағамды тоқтатасыз ба?',
    note:'Аспаз сатуды тоқтата алады. Тек OWNER немесе MANAGER қайта қоса алады.', empty:'Жарияланған тағам жоқ' },
} as const;

export function KitchenStopList({live}: {live: ReturnType<typeof createLiveModules>}) {
  const {user,hotel,locale} = useSession();
  const t = copy[locale];
  const common = useMobileCopy();
  const {c} = useTheme();
  const stock = useAsync(() => live.kitchenAvailability(), [live,hotel?.id,user?.id]);
  const busy = useRef(false);
  const [busyId,setBusyId] = useState<string | null>(null);
  const [reason,setReason] = useState('');
  const stop = (id:string) => {
    if (user?.role !== 'COOK' || busy.current || reason.trim().length < 3) return;
    Alert.alert(t.confirm, t.reason, [
      {text:common.close,style:'cancel'},
      {text:common.confirm,onPress:async()=>{
        if (busy.current || user?.role !== 'COOK') return;
        busy.current=true;setBusyId(id);
        try {
          await live.stopKitchenItem(id,reason.trim());
          setReason('');
          await stock.reload();
        } catch(e) {
          Alert.alert(common.unknown,e instanceof Error?e.message:common.resultUnknown);
        } finally {busy.current=false;setBusyId(null);}
      }},
    ]);
  };
  return <GlassCard testID="kitchen-stoplist" style={{gap:10}}>
    <SectionLabel>{t.title}</SectionLabel>
    <Text style={{color:c.textMuted}}>{t.note}</Text>
    {user?.role==='COOK' ? <TextInput testID="kitchen-stop-reason" value={reason}
      onChangeText={setReason} placeholder={t.reason} placeholderTextColor={c.textMuted}
      accessibilityLabel={t.reason} maxLength={500} multiline
      style={{color:c.text,borderColor:c.border,borderWidth:1,borderRadius:8,padding:10,minHeight:46}}/> : null}
    {stock.loading?<LoadingShimmer count={1}/>:null}
    {stock.error?<ErrorState text={stock.error.message} retry={common.retry} onRetry={stock.reload}/>:null}
    {stock.data?.map(row=><View key={row.id} style={{gap:5,paddingVertical:7,borderBottomColor:c.border,borderBottomWidth:1}}>
      <Text style={{color:c.text,fontWeight:'700'}}>{row[`name_${locale}`] || row.name_ru}</Text>
      <Text style={{color:row.is_available?c.success:c.warning}}>{row.is_available?t.ready:t.stopped}</Text>
      {row.is_available&&user?.role==='COOK'?
        <Button testID={'kitchen-stop-'+row.id} label={t.stop} variant="secondary"
          disabled={busyId!==null || reason.trim().length<3} onPress={()=>stop(row.id)}/>:null}
    </View>)}
    {stock.data?.length===0?<Text style={{color:c.textMuted}}>{t.empty}</Text>:null}
  </GlassCard>;
}
