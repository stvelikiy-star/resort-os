import test from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { spawn } from 'node:child_process';
import { generateKeyPairSync, sign, randomBytes } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { createServer as createNetServer } from 'node:net';

const localPort=()=>new Promise((resolve,reject)=>{
  const server=createNetServer();
  server.once('error',reject);
  server.listen(0,'127.0.0.1',()=>{
    const port=server.address().port;
    server.close(e=>e?reject(e):resolve(port));
  });
});
const b64=v=>Buffer.from(typeof v==='string'?v:JSON.stringify(v)).toString('base64url');
const reply=(res,status,obj)=>{res.writeHead(status,{'Content-Type':'application/json'});res.end(JSON.stringify(obj));};
const cookieHead=r=>r.headers.get('set-cookie')?.split(';')[0]||'';
const serverFile=fileURLToPath(new URL('../server.mjs',import.meta.url));
const sleep=t=>new Promise(resolve=>setTimeout(resolve,t));

test('authenticated QA: platform login, CSRF-gated PENDING registration, safe read and idempotency', {timeout:25000}, async()=>{
  const [backendPort,consolePort]=await Promise.all([localPort(),localPort()]);
  const issuer='http://127.0.0.1:'+backendPort;
  const origin='http://127.0.0.1:'+consolePort;
  const {publicKey,privateKey}=generateKeyPairSync('ed25519');
  const jwk={...publicKey.export({format:'jwk'}),kid:'qa-test-key',alg:'EdDSA',use:'sig'};
  const grants=new Map(),hotels=[],idem=new Map();
  const jwt=claims=>{
    const head=b64({typ:'JWT',alg:'EdDSA',kid:'qa-test-key'});
    const payload=b64({iss:issuer,iat:Math.floor(Date.now()/1000),exp:Math.floor(Date.now()/1000)+900,sub:'qa-platform-admin',...claims});
    const data=head+'.'+payload;
    return data+'.'+sign(null,Buffer.from(data),privateKey).toString('base64url');
  };
  const fake=createServer(async(req,res)=>{
    const url=new URL(req.url,issuer);
    if(url.pathname==='/.well-known/openid-configuration')
      return reply(res,200,{issuer,authorization_endpoint:issuer+'/authorize',token_endpoint:issuer+'/token',jwks_uri:issuer+'/jwks'});
    if(url.pathname==='/jwks')return reply(res,200,{keys:[jwk]});
    if(url.pathname==='/token'){
      const chunks=[];for await(const p of req)chunks.push(p);
      const params=new URLSearchParams(Buffer.concat(chunks).toString());
      const item=grants.get(params.get('code'));
      if(!item||params.get('code_verifier')?.length<40)return reply(res,400,{error:'invalid_grant'});
      grants.delete(params.get('code'));
      return reply(res,200,{token_type:'Bearer',expires_in:900,id_token:jwt({aud:'flex-console-test',nonce:item.nonce}),
        access_token:jwt({aud:'flex-api-test'})});
    }
    if(req.headers.authorization?.startsWith('Bearer ')&&req.url==='/v1/me')return reply(res,200,{role:'SUPER_ADMIN',hotels:[]});
    if(req.headers.authorization?.startsWith('Bearer ')&&req.url==='/v1/hotels')return reply(res,200,hotels);
    if(req.method==='POST'&&url.pathname==='/v1/onboarding/hotels'){
      if(!req.headers.authorization?.startsWith('Bearer '))return reply(res,403,{error:'unauthorized'});
      const chunks=[];for await(const p of req)chunks.push(p);
      const body=JSON.parse(Buffer.concat(chunks).toString());
      const key=req.headers['idempotency-key'];
      if(!key || body.currency!=='KGS')return reply(res,422,{error:'invalid'});
      if(idem.has(key)){
        const previous=idem.get(key);
        if(previous.name!==body.display_name)return reply(res,409,{error:'conflict'});
        return reply(res,200,{hotel_id:previous.id,status:'PENDING',billable:false,idempotent_replay:true});
      }
      const id='123e4567-e89b-12d3-a456-426614174000';
      hotels.push({id,name:body.display_name,status:'PENDING',currency:'KGS'});
      idem.set(key,{id,name:body.display_name});
      return reply(res,201,{hotel_id:id,status:'PENDING',billable:false,idempotent_replay:false});
    }
    return reply(res,404,{error:'not_found'});
  });
  await new Promise(r=>fake.listen(backendPort,'127.0.0.1',r));
  const child=spawn(process.execPath,[serverFile],{
    env:{...process.env,NODE_ENV:'development',PORT:String(consolePort),HOST:'127.0.0.1',
      FLEX_PUBLIC_ORIGIN:origin,FLEX_API_ORIGIN:issuer,FLEX_PARTNER_API_ORIGIN:issuer,
      FLEX_OIDC_ISSUER:issuer,FLEX_OIDC_CLIENT_ID:'flex-console-test',FLEX_API_AUDIENCE:'flex-api-test',
      FLEX_SESSION_KEY:randomBytes(32).toString('base64'),FLEX_ENVIRONMENT:'qa',
      FLEX_ONBOARDING_API_ORIGIN:issuer,FLEX_ENABLE_QA_ONBOARDING:'true'},
    stdio:'ignore'
  });
  try{
    let ready=false;
    for(let attempt=0;attempt<60;attempt++){
      if(child.exitCode!==null)throw Error('FLEX console process exited early');
      try {const r=await fetch(origin+'/api/status');if(r.ok){const json=await r.json();assert.equal(json.qa_onboarding_enabled,true);ready=true;break;}}catch{}
      await sleep(100);
    }
    assert.equal(ready,true,'QA server startup');
    const login=await fetch(origin+'/api/auth/login',{redirect:'manual'});
    assert.equal(login.status,302);
    const authorization=new URL(login.headers.get('location'));
    assert.equal(authorization.origin,issuer);
    assert.equal(authorization.searchParams.get('code_challenge_method'),'S256');
    const state=authorization.searchParams.get('state');
    const nonce=authorization.searchParams.get('nonce');
    assert.ok(state?.length>20&&nonce?.length>20);
    grants.set('qa-approved',{nonce});
    const callback=await fetch(origin+'/api/auth/callback?state='+encodeURIComponent(state)+'&code=qa-approved',{
      redirect:'manual',headers:{Cookie:cookieHead(login)}
    });
    assert.equal(callback.status,302);
    const allSet=callback.headers.getSetCookie?.()||[callback.headers.get('set-cookie')||''];
    const sessionCookie=allSet.map(x=>x.split(';')[0]).find(x=>x.startsWith('flex_session='));
    assert.ok(sessionCookie,'encrypted HttpOnly session cookie');
    assert.match(allSet.join(';'),/HttpOnly/);
    const sessions=await fetch(origin+'/api/session',{headers:{Cookie:sessionCookie}});
    assert.equal(sessions.status,200);
    const session=await sessions.json();assert.ok(session.csrf);
    const badOrigin=await fetch(origin+'/api/actions/hotels',{method:'POST',headers:{
      Cookie:sessionCookie,Origin:'https://evil.example','Content-Type':'application/json','Idempotency-Key':'registration-00001',
      'X-Flex-CSRF':session.csrf
    },body:JSON.stringify({display_name:'QA HOTEL 1',currency:'KGS'})});
    assert.equal(badOrigin.status,403);
    const badCsrf=await fetch(origin+'/api/actions/hotels',{method:'POST',headers:{
      Cookie:sessionCookie,Origin:origin,'Content-Type':'application/json','Idempotency-Key':'registration-00001',
      'X-Flex-CSRF':'wrong'
    },body:JSON.stringify({display_name:'QA HOTEL 1',currency:'KGS'})});
    assert.equal(badCsrf.status,403);
    const headers={Cookie:sessionCookie,Origin:origin,'Content-Type':'application/json',
      'Idempotency-Key':'registration-00001','X-Flex-CSRF':session.csrf};
    const body=JSON.stringify({display_name:'QA HOTEL 1',currency:'KGS'});
    const created=await fetch(origin+'/api/actions/hotels',{method:'POST',headers,body});
    assert.equal(created.status,201);assert.equal((await created.json()).status,'PENDING');
    const replay=await fetch(origin+'/api/actions/hotels',{method:'POST',headers,body});
    assert.equal(replay.status,200);assert.equal((await replay.json()).idempotent_replay,true);
    const changed=await fetch(origin+'/api/actions/hotels',{method:'POST',headers,
      body:JSON.stringify({display_name:'SOME OTHER HOTEL',currency:'KGS'})});
    assert.equal(changed.status,409);
    const unauthorizedCurrency=await fetch(origin+'/api/actions/hotels',{method:'POST',headers,
      body:JSON.stringify({display_name:'QA HOTEL 2',currency:'USD'})});
    assert.equal(unauthorizedCurrency.status,422);
    assert.equal(hotels.length,1);
    const list=await fetch(origin+'/api/data/v1/hotels',{headers:{Cookie:sessionCookie}});
    assert.equal(list.status,200);assert.equal((await list.json()).length,1);
    const forbidden=await fetch(origin+'/api/data/v1/payouts',{headers:{Cookie:sessionCookie}});
    assert.equal(forbidden.status,404);
  }finally{
    child.kill('SIGTERM');
    await new Promise(r=>fake.close(()=>r()));
  }
});
