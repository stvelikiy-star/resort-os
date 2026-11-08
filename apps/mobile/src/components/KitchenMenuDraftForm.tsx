import React, { useRef, useState } from 'react';
import { Text, View } from 'react-native';
import { KITCHEN_MENU_CATEGORIES, KitchenMenuDraft } from '../api/liveModules';
import { wasWriteRejected } from '../lib/writeOutcome';
import { useSession } from '../state/session';
import { useMobileCopy } from '../i18n/mobileCopy';
import { Button, Field, SectionLabel } from './ui';
import { GlassCard } from './Future';
import { useTheme } from '../theme/ThemeProvider';

const EMPTY = { code: '', name_ru: '', name_kg: '', name_en: '', name_kz: '', price: '' };
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
  const { locale } = useSession();
  const copy = useMobileCopy();
  const { c } = useTheme();
  const [open, setOpen] = useState(false);
  const [values, setValues] = useState(EMPTY);
  const [category, setCategory] = useState<KitchenMenuDraft['category']>('MAIN');
  const [busy, setBusy] = useState(false);
  const [unknown, setUnknown] = useState(false);
  const [message, setMessage] = useState('');
  const lock = useRef(false);
  const [title, codeLabel, priceLabel, saved] = labels[locale];
  const code = values.code.trim().toUpperCase();
  const price = Number(values.price);
  const valid = /^[A-Z0-9](?:[A-Z0-9_]{0,58}[A-Z0-9])$/.test(code) &&
    /^\d+$/.test(values.price) && price <= 100000 && FIELDS.every(field => values[field].trim());
  const update = (field: keyof typeof EMPTY, value: string) => {
    setValues(current => ({ ...current, [field]: value }));
  };
  const submit = async () => {
    if (!valid || unknown || lock.current) return;
    lock.current = true;
    setBusy(true);
    setMessage('');
    try {
      await save({
        code, category, price_kgs: price, name_ru: values.name_ru.trim(), name_kg: values.name_kg.trim(),
        name_en: values.name_en.trim(), name_kz: values.name_kz.trim(),
      });
      setValues(EMPTY);
      setMessage(saved);
    } catch (error) {
      const rejected = wasWriteRejected(error);
      setUnknown(!rejected);
      setMessage(rejected ? copy.denied : copy.resultUnknown);
    } finally {
      lock.current = false;
      setBusy(false);
    }
  };
  if (!open) return <Button label={title} variant="secondary" onPress={() => setOpen(true)}/>;
  return <GlassCard style={{ gap: 8 }}>
    <SectionLabel>{title}</SectionLabel>
    <Field label={codeLabel} value={values.code} onChangeText={value => update('code', value)} maxLength={60}/>
    {FIELDS.map(field => <Field key={field} label={field.slice(-2).toUpperCase()}
      value={values[field]} maxLength={160} onChangeText={value => update(field, value)}/>)}
    <Field label={priceLabel} value={values.price} onChangeText={value => update('price', value)}
      keyboardType="number-pad" maxLength={6}/>
    <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
      {KITCHEN_MENU_CATEGORIES.map((item, index) => <Button key={item}
        label={categories[locale][index]} variant={category === item ? 'primary' : 'secondary'}
        onPress={() => setCategory(item)}/>)}
    </View>
    <Button label={copy.confirm} disabled={!valid || busy || unknown} onPress={() => void submit()}/>
    {message ? <Text accessibilityRole="alert" style={{ color: c.text }}>{message}</Text> : null}
    <Button label={copy.close} variant="secondary" disabled={busy} onPress={() => setOpen(false)}/>
  </GlassCard>;
}
