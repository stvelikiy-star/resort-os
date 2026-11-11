import React, { useState } from 'react';
import { Alert, Text, View } from 'react-native';
import type { KitchenStockSnapshot, KitchenStockConsumeAck, KitchenProductionTargets } from '../api/liveModules';
import { useSession } from '../state/session';
import { useTheme } from '../theme/ThemeProvider';
import { font, space } from '../theme/tokens';
import { Button, SectionLabel } from './ui';
import { GlassCard } from './Future';

const COPY = {
  ru:{cancel:'Отмена',title:'Склад · фактические остатки',sample:'Тестовый продукт',cost:'Учётная себестоимость списаний',
    notPayment:'Складские списания не являются оплатой или прибылью.',prepared:'Приготовлено',
    consume:'Списать продукты',already:'Порции уже списаны',success:'Продукты списаны',confirm:'Подтвердите списание по утверждённой рецептуре',error:'Ошибка склада',empty:'Продукты ещё не добавлены'},
  kg:{cancel:'Жокко чыгаруу',title:'Кампа · учурдагы калдыктар',sample:'Сыноо азыгы',cost:'Сарпталган азыктардын эсептик наркы',
    notPayment:'Кампадан чыгаруу төлөм же пайда эмес.',prepared:'Даярдалды',consume:'Азыктарды эсептен чыгаруу',
    already:'Порциялар мурда эсептен чыгарылган',success:'Азыктар эсептен чыгарылды',confirm:'Бекитилген рецепт боюнча эсептен чыгарууну ырастаңыз',error:'Кампа катасы',empty:'Кампада азыктар жок'},
  en:{cancel:'Cancel',title:'Stock · current balances',sample:'Sample product',cost:'Cost of consumed ingredients',
    notPayment:'Inventory consumption is not a payment or profit.',prepared:'Prepared',consume:'Consume ingredients',
    already:'Portions already deducted',success:'Ingredients deducted',confirm:'Confirm deduction against the approved recipe',error:'Stock error',empty:'No stock items yet'},
  kz:{cancel:'Бас тарту',title:'Қойма · ағымдағы қалдықтар',sample:'Сынақ өнімі',cost:'Жұмсалған өнімнің есептік құны',
    notPayment:'Қоймадан есептен шығару төлем де, пайда да емес.',prepared:'Дайындалды',consume:'Өнімдерді есептен шығару',
    already:'Порциялар бұрын есептен шығарылған',success:'Өнімдер есептен шығарылды',confirm:'Бекітілген рецепт бойынша есептен шығаруды растаңыз',error:'Қойма қатесі',empty:'Өнімдер әлі қосылмаған'},
} as const;

export function KitchenStockMobile({stock,targets,consume,reload,readOnly}:{
  stock:KitchenStockSnapshot;targets:KitchenProductionTargets;
  consume:(productionTargetId:string)=>Promise<KitchenStockConsumeAck>;
  reload:()=>Promise<unknown>;readOnly:boolean;
}) {
  const {locale}=useSession(); const {c}=useTheme();const t=COPY[locale];
  const [busy,setBusy]=useState(false);
  const confirm = (id:string,label:string) => {
    if(readOnly||busy)return;
    Alert.alert(t.consume,t.confirm+' · '+label,[{text:t.cancel,style:'cancel'},
      {text:t.consume,onPress:async()=>{
        setBusy(true);
        try {
          const result=await consume(id);
          Alert.alert(result.already_processed?t.already:t.success,
            result.already_processed?'':result.consumed_portions+' · '+result.cost_kgs+' KGS');
          await reload();
        } catch(e){Alert.alert(t.error,e instanceof Error?e.message:String(e));}
        finally{setBusy(false);}
      }}]);
  };
  return <GlassCard testID="kitchen-stock-mobile" style={{gap:space.sm}}>
    <SectionLabel>{t.title}</SectionLabel>
    {stock.items.length?stock.items.map(item=><View key={item.id} style={{gap:3,paddingVertical:5}}>
      <Text style={[font.body,{color:c.text,fontWeight:'700'}]}>{item.name} · {item.balance} {item.unit}</Text>
      <Text style={[font.small,{color:item.is_sample?c.warning:c.textMuted}]}>
        {item.cost_per_unit_kgs} KGS/{item.unit} {item.is_sample?'· '+t.sample:''}
      </Text>
    </View>):<Text style={[font.small,{color:c.textMuted}]}>{t.empty}</Text>}
    <Text style={[font.body,{color:c.text}]}>{t.cost}: {stock.production_cost_kgs} KGS</Text>
    <Text style={[font.small,{color:c.textMuted}]}>{t.notPayment}</Text>
    {!readOnly?targets.items.filter(item=>item.prepared_quantity>0).map(item=><View key={item.id} style={{gap:6,marginTop:5}}>
      <Text style={[font.small,{color:c.text}]}>{item.name_ru} · {t.prepared}: {item.prepared_quantity}</Text>
      <Button disabled={busy} label={t.consume} variant="secondary" onPress={()=>confirm(item.id,item.name_ru)}/>
    </View>):null}
  </GlassCard>;
}
