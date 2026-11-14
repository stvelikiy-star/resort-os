#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
const root = path.resolve(import.meta.dirname, '..');
const read = p => fs.readFileSync(path.join(root,p),'utf8');
const fail = m => { throw new Error('FL2 brand validation: '+m); };
const bridge = JSON.parse(read('docs/design/FL2_BRAND_TOKENS.json'));
const foundation = JSON.parse(read('docs/design/marina-smart.tokens.json'));
for(const theme of ['light','dark']) {
 const actual=foundation.mobile.color[theme];
 const desired=bridge.theme[theme];
 if(JSON.stringify(actual)!==JSON.stringify(desired)) fail(theme+' no longer matches canonical inventory');
 if(Object.keys(desired).length!==29) fail('Expected 29 '+theme+' color tokens');
 for(const [k,v] of Object.entries(desired)) if(!/^#[\da-fA-F]{6}$/.test(v)) fail(theme+'.'+k+' invalid HEX');
}
if(bridge.logo.sha256_1024!=='24678424bf13e4a983f6225fa72c3a73cabc573205832652ee39ed7b27f15356') fail('logo master checksum changed');
if(bridge.logo.sha256_512!=='8b41fcf0ca7a6069b90331aa17a7f23e6650ad86d5c01c0f1aab4f5a5c22d739') fail('logo smaller checksum changed');
if(bridge.logo.installed!==false) fail('unverified logo runtime installation claim');
if(bridge.roleCount!==12) fail('role baseline differs');
if(!bridge.localeGlyphs.includes('Ң')||!bridge.localeGlyphs.includes('Ө')||!bridge.localeGlyphs.includes('Ү')) fail('Kyrgyz glyph list incomplete');
const docs=read('docs/design/FL2_BRAND_SYSTEM.md');
for (const token of ['LIVE NOT VERIFIED','Android E2E NOT VERIFIED','dark','light','RU/KG/EN']) if(!docs.includes(token)) fail('missing '+token+' review gate');
const luminance = value => {
 const channels=[1,3,5].map(i=>parseInt(value.slice(i,i+2),16)/255)
   .map(c=>c<=0.04045?c/12.92:Math.pow((c+0.055)/1.055,2.4));
 return channels[0]*0.2126+channels[1]*0.7152+channels[2]*0.0722;
};
const contrast=(a,b)=>{
 const [lighter,darker]=[luminance(a),luminance(b)].sort((x,y)=>y-x);
 return (lighter+0.05)/(darker+0.05);
};
for(const theme of ['light','dark']){
 const c=bridge.theme[theme];
 for(const [textColor,background] of [['text','surface'],['textMuted','surface'],['text','background'],['onPrimary','primary']]){
  const ratio=contrast(c[textColor],c[background]);
  if(ratio<4.5) fail(`WCAG AA text pair ${theme} ${textColor}/${background} too low: ${ratio.toFixed(2)}`);
 }
}
const light=bridge.theme.light;
const navContrast=contrast(light.navInactive,light.background);
const goldContrast=contrast(light.accent,light.surface);
if(navContrast<4.5) fail(`WCAG AA nav text/background ${navContrast.toFixed(2)}:1 <4.5:1`);
if(goldContrast<4.5)console.warn(`USAGE RESTRICTION: light champagne on white ${goldContrast.toFixed(2)}:1; decoration only, never standard text`);
console.log('FL2 brand tokens PASS: 29 colors x 2 themes; original SHA-256 master; 12 roles; Kyrgyz glyph checklist; no runtime deployment claim.');
