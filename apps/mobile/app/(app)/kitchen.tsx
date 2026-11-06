import React, { useCallback, useRef } from 'react';
import { Text, View, useWindowDimensions } from 'react-native';
import { useFocusEffect, useRouter } from 'expo-router';
import { ChefHat, CircleCheck, ClipboardList, CookingPot, ListChecks, UtensilsCrossed } from 'lucide-react-native';
import { DemoBanner, Empty, SectionLabel, Button } from '../../src/components/ui';
import { ErrorState, FutureScreen, GlassCard, LoadingShimmer, PremiumHeader } from '../../src/components/Future';
import { DiningProductionSnapshots, KitchenOrder, useLiveModules } from '../../src/api/liveModules';
import { demoKitchenOrders } from '../../src/api/demoPresentation';
import { kitchenWorkload } from '../../src/roles/kitchenSummary';
import { hasTabForSession } from '../../src/roles/registry';
import { useAsync } from '../../src/lib/useAsync';
import { useMobileCopy } from '../../src/i18n/mobileCopy';
import { useSession } from '../../src/state/session';
import { useTheme } from '../../src/theme/ThemeProvider';
import { font, radius, space } from '../../src/theme/tokens';

/** COOK dashboard is an aggregation of authenticated active kitchen orders.
 * Separate server production snapshots are needed for included meal portions;
 * orders are never combined numerically with included portions. */
export default function KitchenDashboard() {
  const { user, hotel, api, locale, serverAuthMode } = useSession();
  const showroom = api?.mode === 'DEMO';
  const allowed = user?.role === 'COOK' &&
    hasTabForSession(user.role, user.module_permissions, api?.mode ?? 'LIVE', 'kitchen', serverAuthMode);
  const live = useLiveModules();
  const copy = useMobileCopy();
  const router = useRouter();
  const { c } = useTheme();
  const { width, fontScale } = useWindowDimensions();
  const compact = width < 350 || fontScale > 1.25;
  const { data, loading, error, reload } = useAsync<KitchenOrder[] | null>(
    () => !allowed ? Promise.resolve(null) : showroom ? Promise.resolve(demoKitchenOrders(locale)) :
      live ? live.kitchenOrders() : Promise.resolve(null),
    [live, showroom, locale, user?.id, allowed],
  );
  const focused = useRef(false);
  const { data: production, loading: productionLoading, error: productionError, reload: reloadProduction } =
    useAsync<DiningProductionSnapshots | null>(
      () => !allowed || showroom || !live ? Promise.resolve(null) : live.diningProductionSnapshots(),
      [live, showroom, hotel?.id, user?.id, allowed],
    );
  useFocusEffect(useCallback(() => { if(focused.current) { void reload(); void reloadProduction(); } else focused.current = true; }, [reload, reloadProduction]));
  const summary = kitchenWorkload(data ?? [], locale);
  const tile = (title: string, value: number, icon: React.ElementType, color: string) => {
    const Icon = icon;
    return <GlassCard key={title} style={{ flex: 1, minWidth: 0, minHeight: compact ? 113 : 126,
      padding: compact ? 11 : 15, gap: 8, borderTopWidth: 2, borderTopColor: color }}>
      <Icon size={23} color={color}/>
      <Text style={[font.metric, { color: c.text, fontSize: compact ? 24 : 29 }]}>{value}</Text>
      <Text numberOfLines={2} style={[font.small, {color:c.textMuted}]}>{title}</Text>
    </GlassCard>;
  };
  if (!allowed) return <FutureScreen><Empty text={copy.denied}/></FutureScreen>;
  return <FutureScreen>
    <PremiumHeader title={copy.kitchen} subtitle={hotel?.name} eyebrow="MARINA SMART"
      right={<ChefHat color={c.primary} size={25}/>}/>
    {showroom ? <DemoBanner/> : null}
    {!showroom && !live ? <Empty text={copy.unavailable}/> : null}
    {loading ? <LoadingShimmer count={3}/> : null}
    {error ? <ErrorState text={error.message} retry={copy.retry} onRetry={reload}/> : null}
    {data ? <>
      <SectionLabel>{copy.kitchenMealPlan}</SectionLabel>
      {showroom ? <GlassCard testID="kitchen-demo-meals-not-live" style={{gap:7}}>
        <Text style={[font.body,{color:c.text}]}>{copy.kitchenMealPlanDemo}</Text>
        <Text style={[font.small,{color:c.textMuted}]}>{copy.kitchenMealPlanExplanation}</Text>
      </GlassCard> : null}
      {!showroom && productionLoading ? <LoadingShimmer count={1}/> : null}
      {!showroom && productionError ? <ErrorState text={productionError.message}
        retry={copy.retry} onRetry={reloadProduction}/> : null}
      {production?.days.slice(0,2).map(day => <View key={day.service_date} testID={'kitchen-production-'+day.service_date} style={{gap:space.sm}}>
        <Text style={[font.small,{color:c.cyan,fontWeight:'700'}]}>{day.service_date}</Text>
        {day.meals.map(meal => <GlassCard key={meal.meal_type} testID={'kitchen-meal-'+day.service_date+'-'+meal.meal_type}
          style={{minHeight:78,padding:13,gap:5,flexDirection:'row',alignItems:'center'}}>
          <View style={{flex:1,minWidth:0,gap:4}}>
            <Text style={[font.body,{color:c.text,fontWeight:'700'}]}>
              {meal.meal_type === 'BREAKFAST' ? copy.kitchenBreakfast : meal.meal_type === 'LUNCH' ? copy.kitchenLunch : copy.kitchenDinner}
            </Text>
            <Text style={[font.small,{color:c.textMuted}]}>
              {meal.current_adult_portions} {copy.kitchenAdults} · {meal.current_child_portions} {copy.kitchenChildren}
            </Text>
            {meal.state === 'FROZEN' ? <Text style={[font.small,{color:meal.changed_since_snapshot?c.warning:c.success}]}>
              {copy.kitchenFrozen}: {meal.frozen_total_portions} · {copy.kitchenDelta}: {meal.delta_total_portions}
            </Text> : null}
            {meal.cutoff_status === 'UNCONFIGURED' ? <Text style={[font.small,{color:c.warning}]}>{copy.kitchenUnconfigured}</Text> : null}
          </View>
          <View style={{minWidth:44,alignItems:'center'}}>
            <Text style={[font.h2,{color:c.primary,fontSize:25}]}>{meal.current_total_portions}</Text>
            <Text style={[font.small,{color:c.textMuted}]}>{copy.kitchenPortions}</Text>
          </View>
        </GlassCard>)}
      </View>)}
      {!showroom && production ? <Text style={[font.small,{color:c.textMuted}]}>{copy.kitchenMealsNotOrders}</Text> : null}
      <SectionLabel>{copy.kitchenActiveNow}</SectionLabel>
      <View style={{ gap: space.sm }}>
        <View style={{ flexDirection: 'row', gap: space.sm }}>
          {tile(copy.kitchenNew,summary.newOrders,ClipboardList,c.warning)}
          {tile(copy.kitchenPreparing,summary.preparing,CookingPot,c.cyan)}
        </View>
        <View style={{ flexDirection: 'row', gap: space.sm }}>
          {tile(copy.kitchenReady,summary.ready,CircleCheck,c.success)}
          {tile(copy.kitchenActive,summary.totalActive,UtensilsCrossed,c.primary)}
        </View>
      </View>
      <SectionLabel>{copy.kitchenByDish}</SectionLabel>
      {summary.dishesToPrepare.length ?
        summary.dishesToPrepare.map(dish => <GlassCard key={dish.name} testID={'kitchen-dish-'+dish.name}
          style={{ flexDirection: 'row', alignItems: 'center', gap: space.md, minHeight: 77 }}>
          <View style={{ backgroundColor: c.primarySoft, borderRadius: radius.md, minWidth: 49, height: 49,
            justifyContent:'center', alignItems:'center' }}>
            <Text style={[font.h2,{color:c.primary}]}>{dish.quantity}</Text>
          </View>
          <View style={{ flex: 1, minWidth: 0, gap: 5 }}>
            <Text style={[font.body,{color:c.text,fontWeight:'700'}]}>{dish.name}</Text>
            <Text style={[font.small,{color:c.textMuted}]}>{dish.destinations.join(' · ')}</Text>
          </View>
        </GlassCard>) : <Empty text={copy.kitchenNoDishes}/>}
      {summary.unknownDishOrders ? <Text accessibilityRole="alert" style={[font.small,{color:c.warning}]}>
        {copy.kitchenMissingItems}: {summary.unknownDishOrders}
      </Text> : null}
      <Button testID="kitchen-open-orders" label={copy.orders} icon={ListChecks} onPress={() => router.push('/dining')}/>
      <Text style={[font.small,{color:c.textMuted}]}>{copy.kitchenMealPlanExplanation}</Text>
    </> : null}
  </FutureScreen>;
}
