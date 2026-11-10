import React, { useRef, useState } from 'react';
import { Text, View } from 'react-native';
import type { KitchenProductionInput, KitchenProductionMenuItem, KitchenProductionTargets, createLiveModules } from '../api/liveModules';
import { localDate } from '../api/liveModules';
import { useAsync } from '../lib/useAsync';
import { beginPendingDiningWrite, clearPendingDiningWrite, readPendingDiningWrite } from '../lib/durableDiningWrites';
import { wasWriteRejected } from '../lib/writeOutcome';
import { useSession } from '../state/session';
import { useTheme } from '../theme/ThemeProvider';
import { Button, Field, SectionLabel } from './ui';
import { GlassCard } from './Future';

const messages = {
  ru: ['Производственный план', 'Дата (ГГГГ-ММ-ДД)', 'Запланировано порций', 'Приготовлено порций', 'Сохранить план', 'Блюда для приготовления ещё не утверждены', 'План сохранён', 'Выберите блюдо', 'Нет заданий на период'],
  kg: ['Даярдоо планы', 'Күнү (ЖЖЖЖ-АА-КК)', 'Пландалган порция', 'Даяр порция', 'Планды сактоо', 'Даярдоо үчүн тамактар бекитиле элек', 'План сакталды', 'Тамак тандаңыз', 'Бул мезгилге тапшырма жок'],
  en: ['Production plan', 'Date (YYYY-MM-DD)', 'Planned portions', 'Prepared portions', 'Save plan', 'No approved dishes yet', 'Plan saved', 'Select a dish', 'No production targets'],
  kz: ['Дайындау жоспары', 'Күні (ЖЖЖЖ-АА-КК)', 'Жоспарланған порция', 'Дайын порция', 'Жоспарды сақтау', 'Әзірге бекітілген тағамдар жоқ', 'Жоспар сақталды', 'Тағам таңдаңыз', 'Бұл кезеңге тапсырма жоқ'],
} as const;
const meals = ['BREAKFAST', 'LUNCH', 'DINNER', 'OTHER'] as const;
type Meal = typeof meals[number];

export function KitchenProductionPlanner({
  live, menu, targets, reload, readOnly,
}: {
  live: ReturnType<typeof createLiveModules>;
  menu: KitchenProductionMenuItem[];
  targets: KitchenProductionTargets;
  reload: () => Promise<unknown>;
  readOnly: boolean;
}) {
  const { locale, user, hotel } = useSession();
  const { c } = useTheme();
  const t = messages[locale];
  const [date, setDate] = useState(localDate());
  const [meal, setMeal] = useState<Meal>('LUNCH');
  const [dish, setDish] = useState('');
  const [planned, setPlanned] = useState('');
  const [prepared, setPrepared] = useState('0');
  const [status, setStatus] = useState('');
  const [unknown, setUnknown] = useState(false);
  const [busy, setBusy] = useState(false);
  const lock = useRef(false);
  const identity = hotel?.id && user?.id ? { hotelId: hotel.id, userId: user.id } : null;
  const pending = useAsync(() => identity ? readPendingDiningWrite(identity.hotelId, identity.userId) :
    Promise.reject(new Error('Missing hotel identity')), [identity?.hotelId, identity?.userId]);
  const blocked = pending.loading || !!pending.error || !!pending.data || unknown;
  const dateValid = /^\d{4}-\d{2}-\d{2}$/.test(date) &&
    !Number.isNaN(Date.parse(date + 'T00:00:00Z'));
  const plannedValid = /^\d{1,5}$/.test(planned) && Number(planned) <= 10000;
  const preparedValid = /^\d{1,5}$/.test(prepared) && Number(prepared) <= Number(planned);
  const valid = !!menu.find(x => x.id === dish) && dateValid && plannedValid && preparedValid;
  const choose = (item: KitchenProductionMenuItem) => {
    setDish(item.id);
    const existing = targets.items.find(x => x.menu_item_id === item.id &&
      x.service_date === date && x.meal_type === meal);
    setPlanned(existing ? String(existing.planned_quantity) : '');
    setPrepared(existing ? String(existing.prepared_quantity) : '0');
  };
  const save = async () => {
    if (readOnly || !valid || blocked || busy || !identity || lock.current) return;
    lock.current = true; setBusy(true); setStatus('');
    let recorded = false;
    try {
      await beginPendingDiningWrite(identity.hotelId, identity.userId, 'PRODUCTION_TARGET');
      recorded = true;
      await pending.reload();
      const input: KitchenProductionInput = {
        menu_item_id: dish, service_date: date, meal_type: meal,
        planned_quantity: Number(planned), prepared_quantity: Number(prepared),
      };
      await live.saveKitchenProductionTarget(input);
      await clearPendingDiningWrite(identity.hotelId, identity.userId);
      await pending.reload();
      await reload();
      setStatus(t[6]);
    } catch (e) {
      const rejected = recorded && wasWriteRejected(e);
      if (rejected) {
        try { await clearPendingDiningWrite(identity.hotelId, identity.userId); }
        catch { setUnknown(true); }
      } else {
        setUnknown(true);
      }
      await pending.reload();
      setStatus(e instanceof Error ? e.message : 'Unknown write outcome');
    } finally {
      lock.current = false; setBusy(false);
    }
  };
  return <GlassCard style={{gap:10}} testID="kitchen-production-planner">
    <SectionLabel>{t[0]}</SectionLabel>
    {targets.items.length ? targets.items.map(item => <View key={item.id} testID={'production-'+item.id}
      style={{borderBottomWidth:1,borderBottomColor:c.border,paddingVertical:7,gap:4}}>
      <Text style={{color:c.text,fontWeight:'700'}}>{item['name_'+locale as 'name_ru'|'name_kg'|'name_en'|'name_kz'] || item.name_ru}</Text>
      <Text style={{color:c.textMuted}}>{item.service_date} · {item.meal_type}</Text>
      <Text style={{color:c.text}}>{t[2]}: {item.planned_quantity} · {t[3]}: {item.prepared_quantity} · Осталось: {item.remaining_quantity}</Text>
    </View>) : <Text style={{color:c.textMuted}}>{t[8]}</Text>}
    {!readOnly ? <>
      {menu.length ? <>
        <Field label={t[1]} value={date} onChangeText={setDate} maxLength={10}/>
        <View style={{flexDirection:'row',flexWrap:'wrap',gap:6}}>
          {meals.map(x => <Button key={x} label={x} variant={meal===x?'primary':'secondary'}
            onPress={() => { setMeal(x); setDish(''); }}/>)}
        </View>
        <Text style={{color:c.textMuted}}>{t[7]}</Text>
        <View style={{gap:6}}>
          {menu.map(item => <Button key={item.id} label={item['name_'+locale as 'name_ru'|'name_kg'|'name_en'|'name_kz'] || item.name_ru}
            variant={dish===item.id?'primary':'secondary'} onPress={() => choose(item)}/>)}
        </View>
        <Field label={t[2]} value={planned} onChangeText={setPlanned} keyboardType="number-pad" maxLength={5}/>
        <Field label={t[3]} value={prepared} onChangeText={setPrepared} keyboardType="number-pad" maxLength={5}/>
        <Button label={t[4]} disabled={!valid || blocked || busy} onPress={() => void save()}/>
        {blocked ? <Text accessibilityRole="alert" style={{color:c.warning}}>Результат предыдущего сохранения требует проверки</Text> : null}
        {status ? <Text accessibilityRole="alert" style={{color:c.text}}>{status}</Text> : null}
      </> : <Text style={{color:c.textMuted}}>{t[5]}</Text>}
    </> : null}
  </GlassCard>;
}
