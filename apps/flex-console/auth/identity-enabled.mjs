// This module is imported ONLY when audited auth data and explicit QA flags
// exist. It NEVER issues a platform JWT or grants SUPER ADMIN by a session.
import {betterAuth} from 'better-auth';
import {twoFactor} from 'better-auth/plugins';
import {toNodeHandler} from 'better-auth/node';
import pg from 'pg';
import {verifiedLogin} from './mfa-bridge.mjs';
import {hashPassword} from 'better-auth/crypto';
import {redeemFirstInvite,resendOwnerInvite} from './first-invite.mjs';
import {identityReadiness} from './identity-gate.mjs';
export const passwordMode=()=>process.env.FLEX_ENVIRONMENT==='qa' && process.env.VERCEL_ENV==='preview' && process.env.FLEX_QA_PASSWORD_LOGIN==='true';
async function sendAccountMail(to, subject, text) {
  const key=process.env.FLEX_RESEND_API_KEY;
  const from=process.env.FLEX_RECOVERY_FROM;
  if(!key||!from)throw Error('FLEX_RECOVERY_MAIL_NOT_CONFIGURED');
  const response=await fetch('https://api.resend.com/emails',{
    method:'POST',headers:{Authorization:'Bearer '+key,'Content-Type':'application/json'},
    body:JSON.stringify({from,to:[to],subject,text})
  });
  if(!response.ok)throw Error('FLEX_RECOVERY_MAIL_FAILED');
}
export function createFlexAuthConfig({database,baseURL}) {
  return betterAuth({
    appName:'MARINA SMART FLEX',
    baseURL,basePath:'/api/identity',database,
    user:{changeEmail:{enabled:true}},
    emailVerification:{
      async sendVerificationEmail({user,url}) {
        if(new URL(url).origin!==new URL(baseURL).origin) throw Error('FLEX_MAIL_ORIGIN');
        await sendAccountMail(user.email,'MARINA SMART FLEX · Подтверждение / Ырастоо / Verification',
          'Подтвердите электронную почту.\nЭлектрондук почтаңызды ырастаңыз.\nConfirm your email address.\n'+url);
      }
    },
    emailAndPassword:{
      enabled:true,disableSignUp:true,requireEmailVerification:true,
      minPasswordLength:12,maxPasswordLength:128,
      resetPasswordTokenExpiresIn:900,
      revokeSessionsOnPasswordReset:true,
      sendResetPassword:async ({user,token})=>{
        const link=new URL('/',baseURL);
        link.hash=new URLSearchParams({reset:token}).toString();
        await sendAccountMail(user.email,'MARINA SMART FLEX · Восстановление / Калыбына келтирүү / Reset',
          'Восстановление пароля / Сырсөздү калыбына келтирүү / Password reset\n'+link.href+'\n15 минут / 15 мүнөт / 15 minutes');
      }
    },
    session:{expiresIn:3600,updateAge:900},
    rateLimit:{enabled:true,storage:'database',window:60,max:15},
    advanced:{useSecureCookies:true,cookiePrefix:'msflex_identity'},
    plugins:passwordMode()?[]:[twoFactor({issuer:'MARINA SMART FLEX'})]
  });
}
// Neon pooled connections reject the 'options=-c search_path' startup
// parameter. The dedicated runtime login has a DB-scoped search_path
// configured on the server; prove it before serving any identity request.
let handlerPromise;
async function getHandler() {
  if(!identityReadiness(process.env).ready) throw Error('FLEX_IDENTITY_NOT_READY');
  if(handlerPromise) return handlerPromise;
  handlerPromise=(async()=>{
    const database=new pg.Pool({
      connectionString:process.env.FLEX_AUTH_DATABASE_URL,
      max:3,
      ssl:{rejectUnauthorized:true}
    });
    try {
      const {rows}=await database.query(
        "SELECT current_database() AS db, current_user AS role, " +
        "current_schema() AS schema, " +
        "has_schema_privilege(current_user,'flex_private','USAGE') AS commercial_access"
      );
      const row=rows[0];
      if(!row || row.db!=='flex_qa' || row.role!=='flex_auth_runtime' ||
         row.schema!=='flex_auth' || row.commercial_access!==false)
        throw Error('FLEX_AUTH_DATABASE_SCOPE_INVALID');
      const auth=createFlexAuthConfig({database,baseURL:process.env.BETTER_AUTH_URL});
      return {database,auth,handler:toNodeHandler(auth)};
    } catch (err) {
      await database.end();
      throw err;
    }
  })();
  return handlerPromise;
}
export async function currentIdentitySession(cookie) {
  const {auth} = await getHandler();
  return auth.api.getSession({headers:new Headers({cookie:cookie || ''}), query:{disableCookieCache:true}});
}
export async function handleEnabledIdentity(req,res,issueSessionCookie) {
  const {database,handler,auth}=await getHandler();
  const identityPath=new URL(req.url,'http://localhost').pathname;
  if(identityPath==='/api/identity/first-invite' || identityPath==='/api/identity/resend-owner-invite'){
    const respond=(code)=>{res.writeHead(code,{'Cache-Control':'no-store'});return res.end();};
    if(req.method!=='POST') return respond(405);
    if(req.headers.origin!==new URL(process.env.BETTER_AUTH_URL).origin ||
       req.headers['content-type']?.split(';')[0]!=='application/json') return respond(403);
    const chunks=[];
    let size=0;
    for await(const chunk of req){
      size+=Buffer.byteLength(chunk);
      if(size>2048) return respond(413);
      chunks.push(Buffer.from(chunk));
    }
    let body;
    try{body=JSON.parse(Buffer.concat(chunks).toString());}catch{return respond(400);}
    if(identityPath==='/api/identity/resend-owner-invite'){
      if(!passwordMode())return respond(404);
      try{
        await resendOwnerInvite(database,body?.email,async(email,token)=>{
          const link=new URL('/enroll',process.env.BETTER_AUTH_URL);
          link.hash=token;
          await sendAccountMail(email,'MARINA SMART FLEX · Приглашение / Чакыруу / Invitation',
            'Создайте пароль для тестового кабинета владельца гостиницы.\nСыноо мейманкана кабинетине сырсөз түзүңүз.\nSet your password for the test hotel-owner account.\n'+link.href+'\n30 минут / 30 мүнөт / 30 minutes');
        },{allowOwnerInvite:true});
      }catch{console.error('FLEX_QA_OWNER_INVITE_DELIVERY_FAILED');}
      // Same response for absent, exhausted, activated or eligible invitation.
      return respond(204);
    }
    return respond(await redeemFirstInvite(database,body?.token,body?.password,hashPassword,{allowOwnerInvite:passwordMode(),email:body?.email})?204:403);
  }
  const path=req.url.split('?')[0];
  if(issueSessionCookie && (path==='/api/identity/two-factor/verify-totp' || (passwordMode() && path==='/api/identity/sign-in/email'))){
    const origin=new URL(process.env.BETTER_AUTH_URL).origin;
    return toNodeHandler(request=>verifiedLogin(auth,request,origin,issueSessionCookie,passwordMode()))(req,res);
  }
  if(path==='/api/identity/reset-password' && req.method==='POST'){
    // Preserve Better Auth behavior; log bounded categories, never credentials.
    return toNodeHandler(async request=>{
      const response=await auth.handler(request);
      if(!response.ok){
        const body=await response.clone().json().catch(()=>({}));
        const known=['INVALID_TOKEN','TOKEN_EXPIRED','INVALID_RESET_TOKEN','RESET_PASSWORD_TOKEN_EXPIRED','PASSWORD_TOO_SHORT','PASSWORD_TOO_LONG','INVALID_PASSWORD','PASSWORD_VALIDATION_FAILED','INVALID_ORIGIN','FORBIDDEN'];
        console.warn('FLEX_RESET_REJECTED',response.status,known.includes(body?.code)?body.code:'OTHER');
      }
      return response;
    })(req,res);
  }
  return handler(req,res);
}
