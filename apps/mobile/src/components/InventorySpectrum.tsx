import React from 'react';
import { Animated, Text, View } from 'react-native';
import { Sparkles, Droplets, ClipboardCheck, Wrench } from 'lucide-react-native';
import { useTheme } from '../theme/ThemeProvider';
import { useRevealProgress } from '../theme/motion';
import { font, radius, space } from '../theme/tokens';

/** State composition is a distribution of the source's room counts, not a fictitious time series. */
type Inventory = { clean: number; dirty: number; in_inspection: number; tech_block: number };
export function inventorySegments(data: Inventory, total: number) {
  const entries = [data.clean, data.dirty, data.in_inspection, data.tech_block].map(v => Number.isFinite(v) ? Math.max(0, Math.floor(v)) : 0);
  const sum = entries.reduce((acc, v) => acc + v, 0);
  const safeTotal = Number.isFinite(total) ? Math.max(sum, Math.floor(total)) : sum;
  // Rooms unaccounted for are shown as "unknown" rather than being silently counted as clean.
  return [...entries, Math.max(0, safeTotal - sum)];
}
export function InventorySpectrum({ totals, total, labels }: { totals: Inventory; total: number; labels: { clean: string; dirty: string; inspection: string; blocked: string } }) {
  const { c } = useTheme();
  // The bar grows left-to-right once when the verified distribution first appears.
  const reveal = useRevealProgress(140, 480);
  const values = inventorySegments(totals, total);
  const colors = [c.success, c.warning, c.info, c.danger, c.border];
  const icons = [Sparkles, Droplets, ClipboardCheck, Wrench];
  const keys = [labels.clean, labels.dirty, labels.inspection, labels.blocked];
  const valid = values.reduce((a,v)=>a+v,0);
  return <View style={{ backgroundColor:c.glass, borderWidth:1, borderColor:c.glassBorder, borderRadius:radius.lg, padding:space.lg, gap:space.md }}>
    <Animated.View accessibilityLabel={keys.map((k,i)=>k+': '+values[i]).join(', ')}
      style={{ opacity: reveal, transform: [{ scaleX: reveal.interpolate({ inputRange: [0, 1], outputRange: [0.15, 1] }) }], transformOrigin: 'left center',
        flexDirection:'row', height:13, borderRadius:radius.pill, overflow:'hidden', backgroundColor:c.surfaceAlt }}>
      {valid>0 ? values.map((value,i)=>value>0 ? <View key={i} style={{ flex:value, minWidth:value>0?2:0, backgroundColor:colors[i], borderRightWidth:i===4?0:2, borderColor:c.surface }}/> : null) : null}
    </Animated.View>
    <View style={{ flexDirection:'row', flexWrap:'wrap', gap:space.md }}>
      {keys.map((label,i)=>{
        const Icon=icons[i];
        return <View key={i} style={{ minWidth:'43%', flexGrow:1, flexBasis:'43%', flexDirection:'row', alignItems:'center', gap:9 }}>
          <View style={{ width:34, height:34, alignItems:'center', justifyContent:'center', borderRadius:11, backgroundColor:c.surfaceAlt }}>
            <Icon color={colors[i]} size={19} strokeWidth={1.9}/>
          </View>
          <View style={{ flex:1, minWidth:0 }}>
            <Text style={[font.small,{color:c.textMuted}]} numberOfLines={2}>{label}</Text>
            <Text style={[font.h2,{color:c.text}]}>{values[i]}</Text>
          </View>
        </View>;
      })}
    </View>
  </View>;
}
