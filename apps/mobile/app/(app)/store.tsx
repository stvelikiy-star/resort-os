import React, {useCallback, useRef, useState} from 'react';
import { Alert, Text } from 'react-native';
import { useFocusEffect } from 'expo-router';
import { FutureScreen, PremiumHeader, GlassCard, LoadingShimmer, ErrorState } from '../../src/components/Future';
import { Button, Empty, Field, SectionLabel } from '../../src/components/ui';
import { useSession } from '../../src/state/session';
import { useLiveModules } from '../../src/api/liveModules';
import { hasTabForSession } from '../../src/roles/registry';
import { useAsync } from '../../src/lib/useAsync';
import { useTheme } from '../../src/theme/ThemeProvider';
import { font,space } from '../../src/theme/tokens';
const COPY = {
  ru:{title:'Склад',receipt:'Приход продукта',select:'Выберите продукт',quantity:'Количество',save:'Записать приход',success:'Приход сохранён',warning:'Тестовые продукты не являются реальными запасами.',noPayment:'Приход не создаёт платёж. Себестоимость списаний ведётся отдельно.',invalid:'Введите положительное количество.',empty:'Продукты не добавлены собственником.'},
  kg:{title:'Кампа',receipt:'Азык кабыл алуу',select:'Азыкты тандаңыз',quantity:'Саны',save:'Кирешелөө',success:'Кабыл алуу сакталды',warning:'Сыноо азыктары чыныгы кампа запасы эмес.',noPayment:'Азык кабыл алуу төлөм түзбөйт. Өздүк нарк өзүнчө эсептелет.',invalid:'Оң санды киргизиңиз.',empty:'Азыктар ээси тарабынан кошула элек.'},
  en:{title:'Stock',receipt:'Receive stock',select:'Select product',quantity:'Quantity',save:'Record receipt',success:'Stock receipt saved',warning:'Sample ingredients are not real inventory.',noPayment:'Receiving stock does not create a payment. Consumption cost is tracked separately.',invalid:'Enter a positive quantity.',empty:'No products set up by the owner yet.'},
  kz:{title:'Қойма',receipt:'Өнім қабылдау',select:'Өнімді таңдаңыз',quantity:'Саны',save:'Кірісті тіркеу',success:'Кіріс сақталды',warning:'Сынақ өнімдері нақты қойма қоры емес.',noPayment:'Қабылдау төлем жасамайды. Өзіндік құн бөлек есептеледі.',invalid:'Оң сан енгізіңіз.',empty:'Өнімдерді иесі әлі қоспаған.'},
} as const;
export default function StoreWorkspace() {
 const {user,api,hotel,locale,serverAuthMode}=useSession();const live=useLiveModules();const {c}=useTheme();
 const allowed=!!user && api?.mode==='LIVE' && hasTabForSession(user.role,user.module_permissions,'LIVE','store',serverAuthMode);
 const t=COPY[locale];const [selected,setSelected]=useState('');const [quantity,setQuantity]=useState('');const [busy,setBusy]=useState(false);
 const {data,error,loading,reload}=useAsync(()=>allowed&&live?live.kitchenStock():Promise.resolve(null),[allowed,live,user?.id,hotel?.id]);
 const focused=useRef(false);useFocusEffect(useCallback(()=>{if(focused.current)void reload();else focused.current=true;},[reload]));
 const save=()=>{
  const q=quantity.replace(',','.');if(!selected||!/^(?:0|[1-9]\d*)(?:\.\d{1,6})?$/.test(q)||Number(q)<=0){Alert.alert(t.invalid);return;}
  Alert.alert(t.receipt,`${q} · ${data?.items.find(i=>i.id===selected)?.name||''}`,[{text:locale==='en'?'Cancel':locale==='kg'?'Жокко чыгаруу':locale==='kz'?'Бас тарту':'Отмена',style:'cancel'},
   {text:t.save,onPress:async()=>{if(!live||busy)return;setBusy(true);try{await live.receiveKitchenStock(selected,q);await reload();setQuantity('');Alert.alert(t.success);}catch(e){Alert.alert(t.title,e instanceof Error?e.message:String(e));}finally{setBusy(false);}}}]);
 };
 if(!allowed)return <FutureScreen><Empty text={t.title+' — access denied'}/></FutureScreen>;
 return <FutureScreen><PremiumHeader title={t.title} subtitle={hotel?.name} eyebrow="MARINA SMART"/>
 {loading?<LoadingShimmer count={2}/>:null}{error?<ErrorState text={error.message} onRetry={reload} retry={locale==='en'?'Retry':'Повторить'}/>:null}
 {data?<><GlassCard style={{gap:space.sm}}><SectionLabel>{t.title}</SectionLabel>
 {data.items.length?data.items.map(i=><Text key={i.id} style={[font.body,{color:c.text}]}>{i.name} · {i.balance} {i.unit}{i.is_sample?' · ТЕСТ':''}</Text>):<Text style={{color:c.textMuted}}>{t.empty}</Text>}
 <Text style={[font.small,{color:c.warning}]}>{t.warning}</Text><Text style={[font.small,{color:c.textMuted}]}>{t.noPayment}</Text>
 </GlassCard><GlassCard style={{gap:space.sm}}><SectionLabel>{t.receipt}</SectionLabel>
 {data.items.map(i=><Button key={i.id} variant={selected===i.id?'primary':'secondary'} label={i.name+' ('+i.unit+')'} onPress={()=>setSelected(i.id)} />)}
 <Field label={t.quantity} keyboardType="decimal-pad" value={quantity} onChangeText={setQuantity}/>
 <Button disabled={busy||!selected||!quantity} label={t.save} onPress={save}/>
 </GlassCard></>:null}
 </FutureScreen>;
}
