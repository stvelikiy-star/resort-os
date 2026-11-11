import React, { useState } from 'react';
import { Text, View } from 'react-native';
import type { IngredientRequirements, KitchenRecipe, RecipeIngredient, RecipeInput, RecipeUnit } from '../api/kitchenRecipes';
import { useSession } from '../state/session';
import { useTheme } from '../theme/ThemeProvider';
import { GlassCard } from './Future';
import { Button, Field, SectionLabel } from './ui';

export const RECIPE_COPY = {
  ru: { title:'Продукты по рецептурам', sample:'Учебные нормы — замените своими', missing:'Нет утверждённой рецептуры', plan:'На весь план', prepared:'На приготовленные порции', remaining:'На оставшиеся порции', stock:'Складские остатки не вычтены.', empty:'Нет потребности на выбранный период', recipe:'Нормы на одну порцию', name:'Продукт', norm:'Количество на порцию', add:'Добавить продукт', remove:'Убрать продукт', approved:'Использовать в расчёте', draft:'Черновик', real:'Собственные нормы', save:'Сохранить рецептуру', error:'Не удалось сохранить рецептуру', choose:'Выберите блюдо для рецептуры' },
  kg: { title:'Рецепт боюнча азыктар', sample:'Окуу нормалары — өзүңүздүкүнө алмаштырыңыз', missing:'Бекитилген рецепт жок', plan:'Толук планга', prepared:'Даяр порцияларга', remaining:'Калган порцияларга', stock:'Кампадагы калдыктар кемитилген жок.', empty:'Бул мезгилге керектөө жок', recipe:'Бир порцияга нормалар', name:'Азык', norm:'Бир порцияга өлчөм', add:'Азык кошуу', remove:'Азыкты алып салуу', approved:'Эсептөөгө колдонуу', draft:'Долбоор', real:'Өз нормалары', save:'Рецептти сактоо', error:'Рецепт сакталган жок', choose:'Рецепт үчүн тамак тандаңыз' },
  en: { title:'Recipe ingredients', sample:'Sample norms — replace with your own', missing:'Approved recipe missing', plan:'For the full plan', prepared:'For prepared portions', remaining:'For remaining portions', stock:'Warehouse stock has not been deducted.', empty:'No requirements for this period', recipe:'Per-portion norms', name:'Ingredient', norm:'Quantity per portion', add:'Add ingredient', remove:'Remove ingredient', approved:'Use in calculation', draft:'Draft', real:'Own norms', save:'Save recipe', error:'Could not save recipe', choose:'Select a dish for the recipe' },
  kz: { title:'Рецепт бойынша өнімдер', sample:'Оқу нормалары — өзіңіздікіне ауыстырыңыз', missing:'Бекітілген рецепт жоқ', plan:'Толық жоспарға', prepared:'Дайын порцияларға', remaining:'Қалған порцияларға', stock:'Қойма қалдықтары шегерілген жоқ.', empty:'Бұл кезеңге қажеттілік жоқ', recipe:'Бір порцияға нормалар', name:'Өнім', norm:'Бір порцияға мөлшер', add:'Өнім қосу', remove:'Өнімді алып тастау', approved:'Есептеуге қолдану', draft:'Жоба', real:'Өз нормалары', save:'Рецептті сақтау', error:'Рецепт сақталмады', choose:'Рецепт үшін тағам таңдаңыз' },
} as const;

export function KitchenIngredients({ data }: { data: IngredientRequirements }) {
  const { locale } = useSession();
  const { c } = useTheme();
  const t = RECIPE_COPY[locale];
  return <GlassCard testID="kitchen-ingredient-requirements" style={{gap:10}}>
    <SectionLabel>{t.title}</SectionLabel>
    {data.contains_sample_data ? <Text style={{color:c.warning}}>{t.sample}</Text> : null}
    {data.missing_recipes.map((item, index) => <Text key={index} style={{color:c.warning}}>
      {t.missing}: {item.name_ru} · {item.service_date}
    </Text>)}
    {data.items.map(item => <View key={item.name+item.unit} style={{gap:4}}>
      <Text style={{color:c.text,fontWeight:'700'}}>{item.name} · {item.unit}</Text>
      <Text style={{color:c.text}}>{t.plan}: {item.planned_quantity} · {t.prepared}: {item.prepared_quantity} · {t.remaining}: {item.remaining_quantity}</Text>
    </View>)}
    {!data.items.length && data.is_complete ? <Text style={{color:c.textMuted}}>{t.empty}</Text> : null}
    <Text style={{color:c.textMuted}}>{t.stock}</Text>
  </GlassCard>;
}

export function KitchenRecipeEditor({ recipe, save, reload }: {
  recipe: KitchenRecipe | null | undefined;
  save: (input: RecipeInput) => Promise<void>;
  reload: () => Promise<unknown>;
}) {
  const { locale } = useSession();
  const { c } = useTheme();
  const t = RECIPE_COPY[locale];
  const [ingredients, setIngredients] = useState<RecipeIngredient[]>(recipe?.ingredients ??
    [{name:'',unit:'KG',quantity_per_portion:''}]);
  const [approved, setApproved] = useState(recipe?.status === 'APPROVED');
  const [sample, setSample] = useState(recipe?.is_sample ?? true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const valid = ingredients.length > 0 && ingredients.every(x => x.name.trim() &&
    /^\d+(?:\.\d{1,6})?$/.test(x.quantity_per_portion) &&
    Number(x.quantity_per_portion) > 0 && Number(x.quantity_per_portion) <= 1000);
  const change = (index: number, patch: Partial<RecipeIngredient>) =>
    setIngredients(rows => rows.map((row, i) => i === index ? {...row,...patch} : row));
  const submit = async () => {
    if (busy || !valid) return;
    setBusy(true); setError('');
    try {
      await save({expected_version:recipe?.version ?? 0, status:approved?'APPROVED':'DRAFT',
        is_sample:sample, ingredients});
    } catch (e) {
      setError(e instanceof Error ? e.message : t.error);
    } finally {
      await reload();
      setBusy(false);
    }
  };
  return <View testID="kitchen-recipe-editor" style={{gap:10}}>
    <SectionLabel>{t.recipe}</SectionLabel>
    {ingredients.map((item,index) => <View key={index} style={{gap:6}}>
      <Field editable={!busy} label={t.name} value={item.name} maxLength={120}
        onChangeText={name=>change(index,{name})}/>
      <Field editable={!busy} label={t.norm} value={item.quantity_per_portion} keyboardType="decimal-pad"
        onChangeText={value=>change(index,{quantity_per_portion:value.replace(',','.')})}/>
      <View style={{flexDirection:'row',gap:6}}>
        {(['KG','L','PCS'] as RecipeUnit[]).map(unit=><Button key={unit} disabled={busy} label={unit}
          variant={unit===item.unit?'primary':'secondary'} onPress={()=>change(index,{unit})}/>)}
      </View>
      {ingredients.length > 1 ? <Button disabled={busy} label={t.remove} variant="secondary"
        onPress={()=>setIngredients(rows=>rows.filter((_,i)=>i!==index))}/> : null}
    </View>)}
    <Button label={t.add} variant="secondary" disabled={busy||ingredients.length>=100}
      onPress={()=>setIngredients(rows=>[...rows,{name:'',unit:'KG',quantity_per_portion:''}])}/>
    <Button disabled={busy} label={approved?t.approved:t.draft} variant="secondary" onPress={()=>setApproved(x=>!x)}/>
    <Button disabled={busy} label={sample?t.sample:t.real} variant="secondary" onPress={()=>setSample(x=>!x)}/>
    <Button label={t.save} disabled={!valid||busy} onPress={()=>void submit()}/>
    {error ? <Text accessibilityRole="alert" style={{color:c.warning}}>{error}</Text> : null}
  </View>;
}

