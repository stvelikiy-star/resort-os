"use client";
import {useEffect,useState} from 'react';

/** Browser-only appearance. Never modifies login, hotel, API, data or privileges. */
type Appearance='classic'|'future-luxury';
const KEY='marina-ui-appearance-v2';
export default function FutureLuxuryAppearance(){
 const [mode,setMode]=useState<Appearance>('classic');
 const [theme,setTheme]=useState<'dark'|'light'>('dark');
 useEffect(()=>{
  const saved=(()=>{try{return window.localStorage.getItem(KEY)}catch{return null}})();
  const value=saved==='future-luxury'?'future-luxury':'classic';
  const appearance=(()=>{try{return window.localStorage.getItem('marina-fl2-theme')}catch{return null}})();
  const nextTheme=appearance==='light'?'light':'dark';
  document.documentElement.dataset.marinaUi=value;
  document.documentElement.dataset.fl2Theme=nextTheme;
  setMode(value);setTheme(nextTheme);
  return ()=>{delete document.documentElement.dataset.marinaUi;delete document.documentElement.dataset.fl2Theme;};
 },[]);
 const changeMode=(next:Appearance)=>{
  document.documentElement.dataset.marinaUi=next;setMode(next);
  try{window.localStorage.setItem(KEY,next)}catch{}
 };
 const changeTheme=(next:'light'|'dark')=>{
  document.documentElement.dataset.fl2Theme=next;setTheme(next);
  try{window.localStorage.setItem('marina-fl2-theme',next)}catch{}
 };
 return <div className="marina-appearance-control" data-i18n-skip aria-label="Оформление MARINA SMART">
  <button type="button" aria-pressed={mode==='classic'} onClick={()=>changeMode('classic')}>Классика</button>
  <button type="button" aria-pressed={mode==='future-luxury'} onClick={()=>changeMode('future-luxury')}>Future Luxury</button>
  {mode==='future-luxury'&&<>
   <button type="button" aria-pressed={theme==='dark'} onClick={()=>changeTheme('dark')}>Тёмная</button>
   <button type="button" aria-pressed={theme==='light'} onClick={()=>changeTheme('light')}>Светлая</button>
  </>}
 </div>;
}
