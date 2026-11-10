import React, { useRef, useState } from 'react';
import { Text, View } from 'react-native';
import { KITCHEN_MENU_CATEGORIES, KitchenMenuDraft } from '../api/liveModules';
import { wasWriteRejected } from '../lib/writeOutcome';
import { beginPendingDiningWrite, clearPendingDiningWrite, readPendingDiningWrite } from '../lib/durableDiningWrites';
import { useAsync } from '../lib/useAsync';
import { useSession } from '../state/session';
import { useMobileCopy } from '../i18n/mobileCopy';
import { Button, Field, SectionLabel } from './ui';
import { GlassCard } from './Future';
import { useTheme } from '../theme/ThemeProvider';

const EMPTY = { code: '', name_ru: '', name_kg: '', name_en: '', name_kz: '' };
const FIELDS = ['name_ru', 'name_kg', 'name_en', 'name_kz'] as const;
const labels = {
  ru: ['Добавить блюдо', 'Код блюда', 'Цена (сом)', 'Черновик сохранён'],
  kg: ['Тамак кошуу', 'Тамактын коду', 'Баасы (сом)', 'Долбоор сакталды'],
  en: ['Add dish', 'Dish code', 'Price (KGS)', 'Draft saved'],
  kz: ['Тағам қосу', 'Тағам коды', 'Бағасы (сом)', 'Нобай сақталды'],
} as const;
const categories = {
  ru: ['Завтрак', 'Суп', 'Салат', 'Основное', 'Гарнир', 'Десерт', 'Напиток'],
  kg: ['Эртең мененки тамак', 'Шорпо', 'Салат', 'Негизги тамак', 'Гарнир', 'Десерт', 'Суусундук'],
  en: ['Breakfast', 'Soup', 'Salad', 'Main', 'Side', 'Dessert', 'Drink'],
  kz: ['Таңғы ас', 'Сорпа', 'Салат', 'Негізгі тағам', 'Гарнир', 'Десерт', 'Сусын'],
} as const;

export function KitchenMenuDraftForm({ save }: { save: (draft: KitchenMenuDraft) => Promise<string> }) {
  const { locale, hotel, user } = useSession();
  const identity = hotel?.id && user?.id ? { hotelId: hotel.id, userId: user.id } : null;
  const pending = useAsync(() => identity ? readPendingDiningWrite(identity.hotelId, identity.userId) : Promise.reject(new Error('Missing hotel identity')),
    [identity?.hotelId, identity?.userId]);
  const blocked = pending.loading || !!pending.error || !!pending.data;
  const copy = useMobileCopy();
  const { c } = useTheme();
  const [open, setOpen] = useState(false);
  const [values, setValues] = useState(EMPTY);
  const [category, setCategory] = useState<KitchenMenuDraft['category']>('MAIN');
  const [busy, setBusy] = useState(false);
  const [unknown, setUnknown] = useState(false);
  const [message, setMessage] = useState('');
  const lock = useRef(false);
  const [title, codeLabel, , saved] = labels[locale];
  const code = values.code.trim().toUpperCase();
  const valid = /^[A-Z0-9](?:[A-Z0-9_]{0,58}[A-Z0-9])$/.test(code) &&
    FIELDS.every(field => values[field].trim());
  const update = (field: keyof typeof EMPTY, value: string) => {
    setValues(current => ({ ...current, [field]: value }));
  };
  const submit = async () => {
    if (!valid || unknown || blocked || !identity || lock.current) return;
    lock.current = true;
    setBusy(true);
    setMessage('');
    let recorded = false;
    try {
      await beginPendingDiningWrite(identity.hotelId, identity.userId, 'CREATE_MENU_DRAFT');
      recorded = true;
      await pending.reload();
      await save({
        code, category, price_kgs: 0, name_ru: values.name_ru.trim(), name_kg: values.name_kg.trim(),
        name_en: values.name_en.trim(), name_kz: values.name_kz.trim(),
      });
      await clearPendingDiningWrite(identity.hotelId, identity.userId);
      await pending.reload();
      setValues(EMPTY);
      setMessage(saved);
    } catch (error) {
      const rejected = recorded && wasWriteRejected(error);
      if (recorded && rejected) {
        try { await clearPendingDiningWrite(identity.hotelId, identity.userId); }
        catch { setUnknown(true); }
      } else {
        setUnknown(true);
      }
      await pending.reload();
      setMessage(rejected ? copy.denied : copy.resultUnknown);
    } finally {
      lock.current = false;
      setBusy(false);
    }
  };
  if (!open) return <Button label={title} variant="secondary" onPress={() => setOpen(true)}/>;
  return <GlassCard style={{ gap: 8 }}>
    <SectionLabel>{title}</SectionLabel>
    <Text style={{color:c.textMuted}}>Цена и публикация утверждаются менеджером · Price requires approval</Text>
    <Field label={codeLabel} value={values.code} onChangeText={value => update('code', value)} maxLength={60}/>
    {FIELDS.map(field => <Field key={field} label={field.slice(-2).toUpperCase()}
      value={values[field]} maxLength={160} onChangeText={value => update(field, value)}/>)}
    <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
      {KITCHEN_MENU_CATEGORIES.map((item, index) => <Button key={item}
        label={categories[locale][index]} variant={category === item ? 'primary' : 'secondary'}
        onPress={() => setCategory(item)}/>)}
    </View>
    {blocked || unknown ? <Text accessibilityRole="alert" style={{ color: c.text }}>{copy.resultUnknown}</Text> : null}
    <Button label={copy.confirm} disabled={!valid || busy || unknown || blocked} onPress={() => void submit()}/>
    {message ? <Text accessibilityRole="alert" style={{ color: c.text }}>{message}</Text> : null}
    <Button label={copy.close} variant="secondary" disabled={busy} onPress={() => setOpen(false)}/>
  </GlassCard>;
}
