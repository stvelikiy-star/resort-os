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
    if(invite){await post('first-invite',{token:invite,password,email:form.elements.email.value.trim()});invite='';}
    const session=await post('sign-in/email',{email:form.elements.email.value,password,rememberMe:false});
    if(session.platform_session){location.replace('/');return;}
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

el('resend-invite').onclick=async event=>{
  const field=el('enroll').elements.email;
  if(!field.reportValidity())return;
  const button=event.currentTarget;button.disabled=true;
  try{
    await post('resend-owner-invite',{email:field.value.trim()});
    el('status').textContent='Если приглашение доступно, письмо будет отправлено на указанный адрес. / Чакыруу жеткиликтүү болсо, кат көрсөтүлгөн дарекке жөнөтүлөт. / If an invitation is available, an email will be sent to that address.';
  }catch{el('status').textContent='Не удалось выполнить запрос. / Сурам аткарылган жок. / Request failed.';}
  finally{button.disabled=false;}
};
