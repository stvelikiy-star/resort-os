import React, { useRef, useState } from 'react';
import { Text, View } from 'react-native';
import type { DiningFloor, createLiveModules } from '../api/liveModules';
import { useMobileCopy } from '../i18n/mobileCopy';
import { useAsync } from '../lib/useAsync';
import { wasWriteRejected } from '../lib/writeOutcome';
import { beginPendingDiningWrite, clearPendingDiningWrite, readPendingDiningWrite } from '../lib/durableDiningWrites';
import { useSession } from '../state/session';
import { useTheme } from '../theme/ThemeProvider';
import { GlassCard } from './Future';
import { Button, Field } from './ui';

const labels = {
  ru: ['Добавить стол', 'Новый заказ', 'Код стола', 'Название', 'Мест'],
  en: ['Add table', 'New order', 'Table code', 'Name', 'Seats'],
  kg: ['Үстөл кошуу', 'Жаңы буйрутма', 'Үстөлдүн коду', 'Аталышы', 'Орундар'],
  kz: ['Үстел қосу', 'Жаңа тапсырыс', 'Үстел коды', 'Атауы', 'Орын саны'],
} as const;

export function WaiterOperations({ live, tables, reload }: {
  live: ReturnType<typeof createLiveModules>;
  tables: DiningFloor['tables'];
  reload: () => Promise<unknown>;
}) {
  const { locale, hotel, user } = useSession();
  const identity = hotel?.id && user?.id ? { hotelId: hotel.id, userId: user.id } : null;
  const pending = useAsync(() => identity ? readPendingDiningWrite(identity.hotelId, identity.userId) : Promise.reject(new Error('Missing hotel identity')),
    [identity?.hotelId, identity?.userId]);
  const blocked = pending.loading || !!pending.error || !!pending.data;
  const { c } = useTheme();
  const copy = useMobileCopy();
  const [tableLabel, orderLabel, codeLabel, nameLabel, seatsLabel] = labels[locale];
  const [mode, setMode] = useState<'table' | 'order' | null>(null);
  const [code, setCode] = useState('');
  const [name, setName] = useState('');
  const [seats, setSeats] = useState('4');
  const [table, setTable] = useState('');
  const [quantities, setQuantities] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [unknown, setUnknown] = useState(false);
  const [message, setMessage] = useState('');
  const lock = useRef(false);
  const menu = useAsync(() => mode === 'order' ? live.waiterMenu() : Promise.resolve([]), [live, mode]);
  const items = (menu.data ?? []).flatMap(item => {
    const quantity = Number(quantities[item.id]);
    return quantity > 0 ? [{ menu_item_id: item.id, quantity }] : [];
  });
  const validOrder = tables.some(item => item.id === table && item.status !== 'OUT_OF_SERVICE') &&
    items.length > 0 && items.length <= 50 && Object.values(quantities).every(value => !value || /^\d{1,2}$/.test(value) && Number(value) <= 30);
  const validTable = !!code.trim() && !!name.trim() && /^\d{1,2}$/.test(seats) && Number(seats) >= 1 && Number(seats) <= 30;
  const submit = async () => {
    if (lock.current || unknown || blocked || !identity || (mode === 'table' ? !validTable : !validOrder)) return;
    lock.current = true;
    setBusy(true);
    setMessage('');
    let recorded = false;
    try {
      await beginPendingDiningWrite(identity.hotelId, identity.userId, mode === 'table' ? 'CREATE_TABLE' : 'CREATE_ORDER');
      recorded = true;
      await pending.reload();
      if (mode === 'table') {
        await live.createDiningTable({ code: code.trim().toUpperCase(), name: name.trim(), seats: Number(seats) });
        setCode(''); setName('');
      } else {
        await live.createDiningTableOrder(table, items);
        setQuantities({});
      }
      await clearPendingDiningWrite(identity.hotelId, identity.userId);
      await pending.reload();
      setMessage(copy.confirmed);
      void reload();
    } catch (error) {
      const rejected = recorded && wasWriteRejected(error);
      if (recorded && rejected) {
        try { await clearPendingDiningWrite(identity.hotelId, identity.userId); }
        catch { setUnknown(true); }
      } else {
        setUnknown(true);
      }
      await pending.reload();
      setMessage(rejected && error instanceof Error ? error.message : copy.resultUnknown);
    } finally {
      lock.current = false;
      setBusy(false);
    }
  };
  return <GlassCard style={{ gap: 8 }}>
    <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
      <Button label={tableLabel} variant={mode === 'table' ? 'primary' : 'secondary'} disabled={busy} onPress={() => setMode('table')}/>
      <Button label={orderLabel} variant={mode === 'order' ? 'primary' : 'secondary'} disabled={busy} onPress={() => setMode('order')}/>
    </View>
    {mode === 'table' ? <>
      <Field label={codeLabel} value={code} onChangeText={setCode} maxLength={40}/>
      <Field label={nameLabel} value={name} onChangeText={setName} maxLength={120}/>
      <Field label={seatsLabel} value={seats} onChangeText={setSeats} keyboardType="number-pad" maxLength={2}/>
    </> : null}
    {mode === 'order' ? <>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
        {tables.filter(item => item.status !== 'OUT_OF_SERVICE').map(item => <Button key={item.id}
          label={item.code} variant={table === item.id ? 'primary' : 'secondary'} onPress={() => setTable(item.id)}/>)}
      </View>
      {menu.error ? <Button label={copy.retry} onPress={menu.reload}/> : null}
      {(menu.data ?? []).map(item => <Field key={item.id}
        label={item['name_' + locale as 'name_ru' | 'name_kg' | 'name_en' | 'name_kz'] + ' · ' + item.price_kgs + ' KGS'}
        value={quantities[item.id] ?? ''} keyboardType="number-pad" maxLength={2}
        onChangeText={value => setQuantities(current => ({ ...current, [item.id]: value }))}/>)}
    </> : null}
    {blocked || unknown ? <Text accessibilityRole="alert" style={{ color: c.text }}>{copy.resultUnknown}</Text> : null}
    {mode ? <Button label={copy.confirm} disabled={busy || unknown || blocked || (mode === 'table' ? !validTable : menu.loading || !validOrder)}
      onPress={() => void submit()}/> : null}
    {message ? <Text accessibilityRole="alert" style={{ color: c.text }}>{message}</Text> : null}
  </GlassCard>;
}
