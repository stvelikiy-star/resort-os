'use strict';
const form=document.getElementById('recover');
const message=document.getElementById('status');
const token=location.hash.slice(1);
history.replaceState(null,'',location.pathname);
if(!/^[A-Za-z0-9_-]{43}$/.test(token)){form.hidden=true;message.textContent='Ссылка отсутствует или недействительна.';}
form.addEventListener('submit',async event=>{
  event.preventDefault();
  const password=String(form.elements.password.value||'');
  if(password!==form.elements.confirm.value){message.textContent='Пароли не совпадают.';return;}
  const button=form.querySelector('button');button.disabled=true;
  try{
    const response=await fetch('/api/identity/recover',{
      method:'POST',credentials:'same-origin',cache:'no-store',
      headers:{'Content-Type':'application/json'},body:JSON.stringify({token,password})
    });
    if(response.status!==204)throw Error('RECOVERY_DENIED');
    form.reset();form.hidden=true;
    message.textContent='Пароль сохранён. Теперь можно войти в MARINA SMART FLEX по почте и новому паролю.';
  }catch{
    message.textContent='Ссылка недействительна или срок действия истёк. Пароль не изменён.';
  }finally{button.disabled=false;}
});
