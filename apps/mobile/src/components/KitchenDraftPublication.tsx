import React,{useRef,useState} from 'react';
import {Alert,Text} from 'react-native';
import type {createLiveModules,KitchenAuthorMenuItem} from '../api/liveModules';
import {useSession} from '../state/session';
import {useTheme} from '../theme/ThemeProvider';
import {useMobileCopy} from '../i18n/mobileCopy';
import {Button,Field} from './ui';
import {GlassCard} from './Future';
const COPY={
 ru:{price:'Цена блюда, сом',publish:'Утвердить и опубликовать блюдо',notice:'После подтверждения блюдо появится в действующем меню по указанной цене.',missing:'Перед публикацией заполните все переводы названия.'},
 kg:{price:'Тамактын баасы, сом',publish:'Тамакты бекитүү жана жарыялоо',notice:'Ырасталгандан кийин тамак көрсөтүлгөн баа менен менюда пайда болот.',missing:'Жарыялоодон мурун аталыштын бардык котормолорун толтуруңуз.'},
 en:{price:'Dish price, KGS',publish:'Approve and publish dish',notice:'After confirmation the dish appears in the active menu at this price.',missing:'Complete all name translations before publishing.'},
 kz:{price:'Тағам бағасы, сом',publish:'Тағамды бекіту және жариялау',notice:'Растаудан кейін тағам көрсетілген бағамен мәзірде пайда болады.',missing:'Жарияламас бұрын атаудың барлық аудармасын толтырыңыз.'},
} as const;
export function KitchenDraftPublication({item,live,onPublished}:{item:KitchenAuthorMenuItem;live:ReturnType<typeof createLiveModules>;onPublished:()=>Promise<unknown>}){
 const {user,locale}=useSession();const {c}=useTheme();const copy=useMobileCopy();const t=COPY[locale];
 const [price,setPrice]=useState('');const [busy,setBusy]=useState(false);const [message,setMessage]=useState('');const lock=useRef(false);
 const allowed=!!user&&['OWNER','MANAGER'].includes(user.role);
 const translated=[item.name_ru,item.name_kg,item.name_en,item.name_kz].every(name=>typeof name==='string'&&!!name.trim());
 const valid=/^(?:0|[1-9]\d{0,5})$/.test(price)&&Number(price)<=100000;
 const publish=()=>Alert.alert(t.publish,`${item.name_ru} · ${price} KGS\n${t.notice}`,[
  {text:copy.close,style:'cancel'},
  {text:copy.confirm,onPress:async()=>{
   if(!allowed||!valid||!translated||lock.current)return;lock.current=true;setBusy(true);setMessage('');
   try{await live.publishKitchenMenuDraft(item.id,Number(price));setMessage(copy.confirmed);await onPublished();}
   catch(e){setMessage(e instanceof Error?e.message:copy.resultUnknown);}
   finally{lock.current=false;setBusy(false);}
  }},
 ]);
 if(!allowed||!item.is_draft||item.is_active)return null;
 return <GlassCard testID={'menu-publish-'+item.id} style={{gap:8}}>
  <Text style={{color:c.textMuted}}>{t.notice}</Text>
  <Field testID={'menu-publish-price-'+item.id} label={t.price} value={price} onChangeText={setPrice} keyboardType="number-pad" editable={!busy} maxLength={6}/>
  {!translated?<Text style={{color:c.warning}}>{t.missing}</Text>:null}
  <Button testID={'menu-publish-submit-'+item.id} label={t.publish} disabled={!valid||!translated||busy} onPress={publish}/>
  {message?<Text accessibilityRole="alert" style={{color:c.text}}>{message}</Text>:null}
 </GlassCard>;
}
