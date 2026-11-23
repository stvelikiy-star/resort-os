import assert from 'node:assert/strict';
import {randomBytes,createHash,createHmac,generateKeyPairSync,verify} from 'node:crypto';
import pg from 'pg';
import {getMigrations} from 'better-auth/db/migration';
import {hashPassword} from 'better-auth/crypto';
import {createFlexAuthConfig} from '../auth/identity-enabled.mjs';
import {redeemFirstInvite} from '../auth/first-invite.mjs';
import {redeemRecovery} from '../auth/recovery.mjs';
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
// Password-only Preview mode must mint a real platform cookie after server-verified credentials.
// Test before TOTP enrollment, so the identity is in the same state as the first QA administrator.
const savedEnv={FLEX_ENVIRONMENT:process.env.FLEX_ENVIRONMENT,VERCEL_ENV:process.env.VERCEL_ENV,FLEX_QA_PASSWORD_LOGIN:process.env.FLEX_QA_PASSWORD_LOGIN};
process.env.FLEX_ENVIRONMENT='qa';
process.env.VERCEL_ENV='preview';
process.env.FLEX_QA_PASSWORD_LOGIN='true';
const passwordAuth=createFlexAuthConfig({database:db,baseURL:origin});
const passwordRequest=value=>new Request(origin+'/api/identity/sign-in/email',{
 method:'POST',headers:{origin,'content-type':'application/json'},body:JSON.stringify({email,password:value})
});
const passwordIssue=(sub,method)=>{minted=mint(sub,method);return 'test_session=ok; Secure; HttpOnly';};
assert.equal((await verifiedLogin(passwordAuth,passwordRequest('invalid-password'),origin,passwordIssue,true)).status,401);
assert.equal(minted,undefined);
const passwordReply=await verifiedLogin(passwordAuth,passwordRequest(password),origin,passwordIssue,true);
assert.equal(passwordReply.status,200);
assert.equal((await passwordReply.json()).platform_session,true);
assert.deepEqual(JSON.parse(Buffer.from(minted.token.split('.')[1],'base64url')).amr,['pwd']);
assert.equal(JSON.parse(Buffer.from(minted.token.split('.')[1],'base64url')).sub,(await db.query('select id from "user"')).rows[0].id);
for(const [key,value] of Object.entries(savedEnv)){if(value===undefined)delete process.env[key];else process.env[key]=value;}
minted=undefined;
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
// One-time recovery is bound to a pre-verified email and cannot be replayed.
const recoveryToken=randomBytes(32).toString('base64url');
const recoveryPassword=randomBytes(26).toString('hex');
await db.query('INSERT INTO flex_auth.verification(id,identifier,value,"expiresAt","createdAt","updatedAt") VALUES ($1,$2,$3,now()+interval \'15 minutes\',now(),now())',[
  crypto.randomUUID(),'flex-recovery:'+createHash('sha256').update(recoveryToken).digest('hex'),email
]);
assert.equal(await redeemRecovery(db,randomBytes(32).toString('base64url'),recoveryPassword,hashPassword),false);
assert.equal(await redeemRecovery(db,recoveryToken,'short',hashPassword),false);
assert.equal(await redeemRecovery(db,recoveryToken,recoveryPassword,hashPassword),true);
assert.equal(await redeemRecovery(db,recoveryToken,recoveryPassword,hashPassword),false);
assert.equal((await post('sign-in/email',{email,password})).status,401);
assert.equal((await post('sign-in/email',{email,password:recoveryPassword})).status,200);
await db.end(); console.log('PASS invite concurrency, mailbox-bound credentials, TOTP enrollment, login, negative TOTP, Ed25519 JWT');
