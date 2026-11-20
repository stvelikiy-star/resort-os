import React from 'react';
import { Text, View } from 'react-native';
import type { createLiveModules } from '../api/liveModules';
import { useAsync } from '../lib/useAsync';
import { useSession } from '../state/session';
import { useTheme } from '../theme/ThemeProvider';
import { useMobileCopy } from '../i18n/mobileCopy';
import { GlassCard, ErrorState, LoadingShimmer } from './Future';
import { SectionLabel } from './ui';
import { KitchenMenuDraftForm } from './KitchenMenuDraftForm';
import { KitchenDraftPublication } from './KitchenDraftPublication';
import { KitchenRecipeEditor } from './KitchenIngredients';

const labels = {
  ru: ['Черновики для утверждения', 'Сохранённые черновики доступны собственнику и менеджеру. Утверждение и публикация выполняются отдельно.', 'Черновиков пока нет'],
  kg: ['Бекитүүгө даяр долбоорлор', 'Сакталган долбоорлор ээсине жана менеджерге жеткиликтүү. Бекитүү жана жарыялоо өзүнчө аткарылат.', 'Азырынча долбоор жок'],
  en: ['Drafts for approval', 'Saved drafts are available to the owner and manager. Approval and publication are separate actions.', 'No drafts yet'],
  kz: ['Бекітуге арналған нобайлар', 'Сақталған нобайлар иесіне және менеджерге қолжетімді. Бекіту мен жариялау бөлек орындалады.', 'Әзірге нобай жоқ'],
} as const;

export function KitchenDrafts({ live, onPublished }: { live: ReturnType<typeof createLiveModules>; onPublished?:()=>Promise<unknown> }) {
  const { hotel, user, locale } = useSession();
  const { c } = useTheme();
  const copy = useMobileCopy();
  const t = labels[locale];
  const drafts = useAsync(() => live.kitchenAuthorMenu(), [live, hotel?.id, user?.id]);
  return <GlassCard testID="kitchen-author-drafts" style={{gap:10}}>
    <SectionLabel>{t[0]}</SectionLabel>
    <Text style={{color:c.textMuted}}>{t[1]}</Text>
    <KitchenMenuDraftForm save={async input => {
      const id = await live.createKitchenMenuDraft(input);
      await drafts.reload();
      return id;
    }}/>
    {drafts.loading ? <LoadingShimmer count={1}/> : null}
    {drafts.error ? <ErrorState text={drafts.error.message} retry={copy.retry} onRetry={drafts.reload}/> : null}
    {drafts.data?.filter(item => item.is_draft && !item.is_active).map(item =>
      <View key={item.id} style={{gap:8}}>
        <Text style={{color:c.text,fontWeight:'700'}}>{item['name_'+locale as 'name_ru'|'name_kg'|'name_en'|'name_kz'] || item.name_ru}</Text>
        <KitchenMenuDraftForm key={JSON.stringify(item)} initial={item}
          save={async input => {
            const id = await live.updateKitchenMenuDraft(item.id, input);
            await drafts.reload();
            return id;
          }}/>
        {item.recipe?.status !== 'APPROVED' ? <KitchenRecipeEditor key={item.id+':'+(item.recipe?.version ?? 0)} recipe={item.recipe}
          canApprove={user?.role === 'OWNER' || user?.role === 'MANAGER'} save={input => live.saveKitchenRecipe(item.id,input)} reload={drafts.reload}/> : <Text style={{color:c.textMuted}}>{item.recipe.status}</Text>}
        <KitchenDraftPublication item={item} live={live} onPublished={async()=>{await drafts.reload();await onPublished?.();}}/>
      </View>)}
    {drafts.data?.length === 0 ? <Text style={{color:c.textMuted}}>{t[2]}</Text> : null}
  </GlassCard>;
}
