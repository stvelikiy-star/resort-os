import assert from 'node:assert/strict';
import {randomBytes,createHash,createHmac,generateKeyPairSync,verify} from 'node:crypto';
import pg from 'pg';
import {getMigrations} from 'better-auth/db/migration';
import {hashPassword} from 'better-auth/crypto';
import {createFlexAuthConfig} from '../auth/identity-enabled.mjs';
import {redeemFirstInvite} from '../auth/first-invite.mjs';
import {verifiedLogin,createMfaSigner} from '../auth/mfa-bridge.mjs';
const db=new pg.Pool({connectionString:'postgresql://ci_no_login:ci_no_secret@127.0.0.1:55449/flex_ci',options:'-c search_path=flex_auth'});
await db.query('create schema if not exists flex_auth');
const origin='https://qa.example.test';
process.env.BETTER_AUTH_SECRET=randomBytes(48).toString('hex');
const auth=createFlexAuthConfig({database:db,baseURL:origin});
await (await getMigrations(auth.options)).runMigrations();
const token=randomBytes(32).toString('base64url');
const email='owner@example.test',password=randomBytes(24).toString('hex');
await db.query('insert into verification(id,identifier,value,"expiresAt","createdAt","updatedAt") values ($1,$2,$3,now()+interval \'10 minutes\',now(),now())',[crypto.randomUUID(),'flex-first:'+createHash('sha256').update(token).digest('hex'),email]);
assert.equal(await redeemFirstInvite(db,randomBytes(32).toString('base64url'),password,hashPassword),false);
assert.deepEqual((await Promise.all([1,2].map(()=>redeemFirstInvite(db,token,password,hashPassword)))).sort(),[false,true]);
const jar=new Map();
const {privateKey,publicKey}=generateKeyPairSync('ed25519');
const mint=createMfaSigner({FLEX_ENVIRONMENT:'qa',FLEX_MFA_BRIDGE_ENABLED:'true',FLEX_MFA_PRIVATE_KEY:privateKey.export({format:'pem',type:'pkcs8'}),FLEX_MFA_KEY_ID:'qa-test',FLEX_API_AUDIENCE:'flex',BETTER_AUTH_URL:origin});
let minted;
async function post(path,body){
 const headers={origin,'content-type':'application/json',cookie:[...jar].map(([k,v])=>k+'='+v).join('; ')};
 const req=new Request(origin+'/api/identity/'+path,{method:'POST',headers,body:JSON.stringify(body)});
 const res=await verifiedLogin(auth,req,origin,sub=>{minted=mint(sub);return 'demo=accepted; HttpOnly; Secure';});
 for(const line of res.headers.getSetCookie()){const [k,...v]=line.split(';')[0].split('=');if(v.join('='))jar.set(k,v.join('='));else jar.delete(k);}
 const data=await res.json(); if(res.status!==200) console.log(path,res.status,data.code);
 return {status:res.status,...data};
}
const signin=()=>post('sign-in/email',{email,password});
assert.equal((await signin()).status,200);
const setup=await post('two-factor/enable',{password});
const key=new URL(setup.totpURI).searchParams.get('secret');
const bits=[...key.replace(/=/g,'')].map(c=>'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'.indexOf(c).toString(2).padStart(5,'0')).join('');
const secret=Buffer.from(bits.match(/.{8}/g).map(x=>parseInt(x,2)));
function otp(){const counter=Buffer.alloc(8);counter.writeBigUInt64BE(BigInt(Math.floor(Date.now()/30000)));const h=createHmac('sha1',secret).update(counter).digest();return ((h.readUInt32BE(h[19]&15)&0x7fffffff)%1e6).toString().padStart(6,'0');}
const totp=code=>post('two-factor/verify-totp',{code,trustDevice:false});
assert.equal((await totp(otp())).status,200);assert.equal(minted,undefined);
await post('sign-out',{});jar.clear();
assert.equal((await signin()).twoFactorRedirect,true);
assert.notEqual((await totp(otp()==='000000'?'000001':'000000')).status,200);assert.equal(minted,undefined);
assert.equal((await totp(otp())).platform_session,true);
const [head,payload,sig]=minted.token.split('.');
assert(verify(null,Buffer.from(head+'.'+payload),publicKey,Buffer.from(sig,'base64url')));
const claims=JSON.parse(Buffer.from(payload,'base64url'));assert.equal(claims.exp-claims.iat,300);assert(claims.amr.includes('mfa'));assert.equal(claims.sub,(await db.query('select id from "user"')).rows[0].id);
// Start mode reuses the original password and reports its actual authentication method.
process.env.FLEX_ENVIRONMENT='qa';
process.env.VERCEL_ENV='preview';
process.env.FLEX_QA_PASSWORD_LOGIN='true';
// Start a separate login scenario with its own rate-limit window in the disposable CI database.
await db.query('TRUNCATE flex_auth."rateLimit"');
const simpleAuth=createFlexAuthConfig({database:db,baseURL:origin});
const tryPassword=async value=>{
  const request=new Request(origin+'/api/identity/sign-in/email',{method:'POST',headers:{origin,'content-type':'application/json'},
    body:JSON.stringify({email,password:value})});
  return verifiedLogin(simpleAuth,request,origin,(sub,method)=>{
    minted=mint(sub,method);return 'test_session=ok; Secure; HttpOnly';
  },true);
};
minted=undefined;
assert.equal((await tryPassword('wrong-password-test')).status,401);
assert.equal(minted,undefined);
const accepted=await tryPassword(password);
const result=await accepted.json();
assert.equal(accepted.status,200,result.code || result.message);
assert.equal(result.platform_session,true);
assert.deepEqual(JSON.parse(Buffer.from(minted.token.split('.')[1],'base64url')).amr,['pwd']);
// Regression for the legacy #588/#590 behavior using the CURRENT Better Auth
// implementation, never the obsolete custom recovery endpoint. This is a
// disposable CI database; the only mail transport is an in-memory stub.
const cookieHeader=reply=>reply.headers.getSetCookie().map(line=>line.split(';')[0]).join('; ');
const loginCookie=cookieHeader(accepted);
const readSession=cookie=>simpleAuth.api.getSession({headers:new Headers({cookie}),query:{disableCookieCache:true}});
const subject=claims.sub;
const live=await readSession(loginCookie);
assert.equal(live?.user?.id,subject);
assert.equal(live?.user?.emailVerified,true);
assert.ok(live?.session?.token);
assert.equal(await readSession(''),null);
const replacement=await tryPassword(password);
assert.equal(replacement.status,200);
const replacementCookie=cookieHeader(replacement);
const replacementSession=await readSession(replacementCookie);
assert.equal(replacementSession?.user?.id,subject);
assert.notEqual(replacementSession?.session?.token,live.session.token,'separate login must have separate session binding');

const originalFetch=globalThis.fetch;
const mailEnv={FLEX_RESEND_API_KEY:process.env.FLEX_RESEND_API_KEY,FLEX_RECOVERY_FROM:process.env.FLEX_RECOVERY_FROM};
const messages=[];
process.env.FLEX_RESEND_API_KEY='ci-only-not-a-real-key';
process.env.FLEX_RECOVERY_FROM='qa@example.test';
globalThis.fetch=async (url,options)=>{
  assert.equal(String(url),'https://api.resend.com/emails','unexpected outbound request');
  assert.equal(options.method,'POST');
  messages.push(JSON.parse(options.body));
  return Response.json({id:'ci-mail'});
};
const request=async (path,body)=>simpleAuth.handler(new Request(origin+'/api/identity/'+path,{
  method:'POST',headers:{origin,'content-type':'application/json'},body:JSON.stringify(body)
}));
const newPassword=randomBytes(24).toString('hex');
try {
  await db.query('TRUNCATE flex_auth."rateLimit"');
  const requested=await request('request-password-reset',{email,redirectTo:origin+'/'});
  assert.equal(requested.status,200);
  assert.equal(messages.length,1);
  assert.deepEqual(messages[0].to,[email]);
  const linkLine=messages[0].text.split('\n').find(line=>line.startsWith(origin+'/'));
  assert.ok(linkLine,'reset link must use the configured Console origin');
  const link=new URL(linkLine);
  assert.equal(link.origin,origin);
  const resetToken=new URLSearchParams(link.hash.slice(1)).get('reset');
  assert.ok(resetToken);
  assert.notEqual((await request('reset-password',{token:randomBytes(32).toString('hex'),newPassword})).status,200);
  assert.notEqual((await request('reset-password',{token:resetToken,newPassword:'short'})).status,200);
  assert.equal((await request('reset-password',{token:resetToken,newPassword})).status,200);
  assert.notEqual((await request('reset-password',{token:resetToken,newPassword:password})).status,200);
  assert.equal(await readSession(loginCookie),null,'reset must revoke original session');
  assert.equal(await readSession(replacementCookie),null,'reset must revoke other session');
  await db.query('TRUNCATE flex_auth."rateLimit"');
  minted=undefined;
  assert.equal((await tryPassword(password)).status,401);
  assert.equal(minted,undefined);
  await db.query('TRUNCATE flex_auth."rateLimit"');
  const recovered=await tryPassword(newPassword);
  assert.equal(recovered.status,200);
  assert.equal((await recovered.clone().json()).platform_session,true);
  assert.equal((await readSession(cookieHeader(recovered)))?.user?.id,subject);
  console.log('PASS canonical password recovery, one-time token, prior session revocation and fresh bound login (stub mail)');
} finally {
  globalThis.fetch=originalFetch;
  for(const [key,value] of Object.entries(mailEnv)){
    if(value===undefined)delete process.env[key];else process.env[key]=value;
  }
}
// Exercise the new QA-only owner invitation using the existing disposable DB.
// It must not replace the first administrator or grant commercial roles itself.
const secondEmail='qa-owner@example.test',secondSubject='qa-owner:'+crypto.randomUUID();
const secondToken=randomBytes(32).toString('base64url');
await db.query('INSERT INTO flex_auth.verification(id,identifier,value,"expiresAt","createdAt","updatedAt") VALUES ($1,$2,$3,now()+interval \'10 minutes\',now(),now())',
  [crypto.randomUUID(),'flex-owner:'+createHash('sha256').update(secondToken).digest('hex'),JSON.stringify({kind:'QA_HOTEL_OWNER',subject:secondSubject,email:secondEmail})]);
const secondPassword=randomBytes(24).toString('hex');
assert.equal(await redeemFirstInvite(db,secondToken,secondPassword,hashPassword),false);
assert.equal(await redeemFirstInvite(db,secondToken,secondPassword,hashPassword,{allowOwnerInvite:true,email:'other@example.test'}),false);
assert.deepEqual((await Promise.all([1,2].map(()=>redeemFirstInvite(db,secondToken,secondPassword,hashPassword,{allowOwnerInvite:true,email:secondEmail})))).sort(),[false,true]);
assert.equal((await db.query('SELECT count(*)::int AS n FROM flex_auth."user"')).rows[0].n,2);
assert.equal((await db.query('SELECT id FROM flex_auth."user" WHERE email=$1',[secondEmail])).rows[0].id,secondSubject);
assert.equal(await redeemFirstInvite(db,secondToken,secondPassword,hashPassword,{allowOwnerInvite:true,email:secondEmail}),false);
const ownerLogin=await request('sign-in/email',{email:secondEmail,password:secondPassword});
assert.equal(ownerLogin.status,200);
assert.equal((await readSession(cookieHeader(ownerLogin)))?.user?.id,secondSubject);
console.log('PASS QA owner invite: restricted mode, email binding, concurrency, replay, existing admin retained, password login');
await db.end(); console.log('PASS invite concurrency, mailbox-bound credentials, TOTP enrollment, login, negative TOTP, Ed25519 JWT');
