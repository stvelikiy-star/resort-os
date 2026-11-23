'use strict';
const translations={
  ru:{
    language:'Язык',title:'Новый пароль MARINA SMART FLEX',description:'Введите новый пароль для подтверждённой почты. Дополнительные приложения не нужны.',
    password:'Новый пароль (от 12 символов)',confirm:'Повторите пароль',save:'Сохранить пароль',
    invalid:'Ссылка отсутствует или недействительна.',mismatch:'Пароли не совпадают.',
    success:'Пароль сохранён. Теперь войдите по почте и новому паролю.',
    failed:'Ссылка недействительна или срок её действия истёк. Пароль не изменён.'
  },
  kg:{
    language:'Тил',title:'MARINA SMART FLEX — жаңы сырсөз',description:'Ырасталган электрондук почтаңыз үчүн жаңы сырсөз киргизиңиз. Кошумча колдонмо кереги жок.',
    password:'Жаңы сырсөз (кеминде 12 белги)',confirm:'Сырсөздү кайталаңыз',save:'Сырсөздү сактоо',
    invalid:'Шилтеме жок же жараксыз.',mismatch:'Сырсөздөр дал келбейт.',
    success:'Сырсөз сакталды. Электрондук почтаңыз жана жаңы сырсөз менен кириңиз.',
    failed:'Шилтеме жараксыз же мөөнөтү бүттү. Сырсөз өзгөргөн жок.'
  },
  en:{
    language:'Language',title:'New MARINA SMART FLEX password',description:'Set a new password for your verified email. No additional application is needed.',
    password:'New password (at least 12 characters)',confirm:'Repeat password',save:'Save password',
    invalid:'The link is missing or invalid.',mismatch:'Passwords do not match.',
    success:'Password saved. Sign in with your email and new password.',
    failed:'The link is invalid or expired. Your password was not changed.'
  }
};
const form=document.getElementById('recover');
const message=document.getElementById('status');
const language=document.getElementById('recover-lang');
const token=location.hash.slice(1);
history.replaceState(null,'',location.pathname);
const validToken=/^[A-Za-z0-9_-]{43}$/.test(token);
let result=validToken?'':'invalid';
let currentLanguage='ru';
try{
  const saved=localStorage.getItem('flex_lang');
  if(Object.hasOwn(translations,saved))currentLanguage=saved;
}catch{}
function renderCopy(){
  const t=translations[currentLanguage];
  document.documentElement.lang=currentLanguage==='kg'?'ky':currentLanguage;
  document.title=t.title;
  language.value=currentLanguage;
  for(const [id,key] of [
    ['recover-lang-label','language'],['recover-title','title'],
    ['recover-description','description'],['recover-password-label','password'],
    ['recover-confirm-label','confirm'],['recover-submit','save']
  ])document.getElementById(id).textContent=t[key];
  message.textContent=result?t[result]:'';
}
if(!validToken)form.hidden=true;
language.addEventListener('change',()=>{
  currentLanguage=language.value;
  try{localStorage.setItem('flex_lang',currentLanguage);}catch{}
  renderCopy();
});
form.addEventListener('submit',async event=>{
  event.preventDefault();
  const password=String(form.elements.password.value||'');
  if(password!==form.elements.confirm.value){result='mismatch';renderCopy();return;}
  const button=form.querySelector('button');
  button.disabled=true;
  try{
    const response=await fetch('/api/identity/recover',{
      method:'POST',credentials:'same-origin',cache:'no-store',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({token,password})
    });
    if(response.status!==204)throw Error('RECOVERY_DENIED');
    form.reset();
    form.hidden=true;
    result='success';
  }catch{
    result='failed';
  }finally{
    button.disabled=false;
    renderCopy();
  }
});
renderCopy();
