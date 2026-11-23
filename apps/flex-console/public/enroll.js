'use strict';
const el=id=>document.getElementById(id);
let invite=location.hash.slice(1);
history.replaceState(null,'',location.pathname);
async function post(path,body){
  const response=await fetch('/api/identity/'+path,{method:'POST',credentials:'same-origin',
    headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  if(!response.ok) throw Error('request failed');
  return response.status===204?null:response.json();
}
el('enroll').onsubmit=async event=>{
  event.preventDefault();
  const form=event.currentTarget;
  const button=form.querySelector('button');
  button.disabled=true;
  try{
    const password=form.elements.password.value;
    if(invite){await post('first-invite',{token:invite,password});invite='';}
    const session=await post('sign-in/email',{email:form.elements.email.value,password,rememberMe:false});
    // Password-only QA already has a verified server-issued platform session.
    // Do not start TOTP enrollment after the successful first login.
    if(session.platform_session===true){location.replace('/');return;}
    if(session.twoFactorRedirect){location.replace('/');return;}
    const setup=await post('two-factor/enable',{password});
    const key=new URL(setup.totpURI).searchParams.get('secret');
    if(!key)throw Error('missing key');
    form.reset();
    form.hidden=true;
    el('secret').textContent=key;
    el('backup').textContent=setup.backupCodes.join('\n');
    el('setup').hidden=false;
    el('status').textContent='';
  }catch{el('status').textContent='Проверьте адрес, пароль и срок приглашения. Если адрес уже подтверждён, откройте /enroll без приглашения для продолжения настройки.';}
  finally{button.disabled=false;}
};
el('verify').onsubmit=async event=>{
  event.preventDefault();
  try{
    await post('two-factor/verify-totp',{code:event.currentTarget.elements.code.value,trustDevice:false});
    el('setup').replaceChildren();
    el('status').textContent='Приложение-аутентификатор подтверждено.';
  }catch{el('status').textContent='Код не принят. Введите текущий код из приложения.';}
};
