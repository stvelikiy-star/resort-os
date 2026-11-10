#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(import.meta.dirname, '..');
const file = name => fs.readFileSync(path.join(root, name), 'utf8');
const data = JSON.parse(file('docs/design/FL2_BRAND_TOKENS.json'));
const fail = message => { throw new Error('Future Luxury visual safety: '+message); };
const luminance = hex => {
 const rgb = [1,3,5].map(n=>parseInt(hex.slice(n,n+2),16)/255)
   .map(c => c <= 0.04045 ? c / 12.92 : ((c+0.055)/1.055)**2.4);
 return rgb[0]*0.2126 + rgb[1]*0.7152 + rgb[2]*0.0722;
};
const contrast = (a,b) => {
 const [hi,lo] = [luminance(a),luminance(b)].sort((a,b)=>b-a);
 return (hi+0.05)/(lo+0.05);
};
const required = [
 ['text','surface',4.5],['textMuted','surface',4.5],
 ['text','background',4.5],['onPrimary','primary',4.5],
 ['navInactive','background',4.5]
];
for(const [theme, colors] of Object.entries(data.theme)){
 for(const [fg,bg,minimum] of required){
  const ratio = contrast(colors[fg], colors[bg]);
  if(ratio < minimum) fail(`${theme} ${fg}/${bg}: ${ratio.toFixed(2)}:1 below ${minimum}:1`);
 }
}
if(data.currency.primary !== 'KGS' || data.currency.label !== 'сом') fail('Currency changed');
if(data.locales.join('/') !== 'RU/KG/EN') fail('Unapproved locale baseline change');
for(const character of ['Ң','ң','Ө','ө','Ү','ү']){
 if(!data.localeGlyphs.includes(character)) fail('Kyrgyz glyph coverage checklist lost '+character);
}
const ts = file('apps/mobile/src/theme/tokens.ts');
const mapped = {background:'bg',onPrimary:'primaryText'};
for (const theme of ['light','dark']) {
 const block = ts.split(`  ${theme}: {`)[1]?.split('  },')[0];
 if(!block) fail('Mobile theme source block missing '+theme);
 for (const [token,value] of Object.entries(data.theme[theme])) {
  const key = mapped[token] || token;
  if (!block.includes(`${key}: '${value}'`)) fail(`Mobile ${theme} token mismatch: ${token}`);
 }
}
console.log('FL2 visual safety PASS: light/dark WCAG text/nav pairs >=4.5, 29 token synchronization, KGS, RU/KG/EN glyph checklist.');
console.log('Note: static font coverage checklist is NOT physical Android glyph/rendering verification.');
