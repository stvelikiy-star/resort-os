import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {identityReadiness,handleFlexIdentity} from '../auth/identity-gate.mjs';
test('no identity access without explicit QA gates',()=>{
  for(const cfg of [{},{FLEX_ENVIRONMENT:'qa',FLEX_AUTH_ENABLED:'false'},
    {FLEX_ENVIRONMENT:'production',FLEX_AUTH_ENABLED:'true'},
    {FLEX_ENVIRONMENT:'qa',FLEX_AUTH_ENABLED:'true'}])
      assert.equal(identityReadiness(cfg).ready,false);
});
test('auth rejects PMS owner, insecure URLs and unmigrated schema',()=>{
  const ok={FLEX_ENVIRONMENT:'qa',FLEX_AUTH_ENABLED:'true',FLEX_AUTH_SCHEMA_READY:'true',
    BETTER_AUTH_SECRET:'K'.repeat(44),
    BETTER_AUTH_URL:'https://flex-qa.example.org',
    FLEX_AUTH_DATABASE_URL:'postgresql://flex_auth_runtime:masked@host.neon.tech/flex_qa?sslmode=require'};
  assert.equal(identityReadiness(ok).ready,true);
  for(const change of [
    {FLEX_ENVIRONMENT:'production'},
    {BETTER_AUTH_URL:'http://flex-qa.example.org'},
    {BETTER_AUTH_URL:'https://flex-qa.example.org/another-path'},
    {BETTER_AUTH_SECRET:'weak'},
    {FLEX_AUTH_SCHEMA_READY:'false'},
    {FLEX_AUTH_DATABASE_URL:'postgresql://flex_qa_owner:masked@host.neon.tech/flex_qa?sslmode=require'},
    {FLEX_AUTH_DATABASE_URL:'postgresql://flex_auth_runtime:masked@host.neon.tech/pms?sslmode=require'},
    {FLEX_AUTH_DATABASE_URL:'postgresql://flex_auth_runtime:masked@host.neon.tech/flex_qa?sslmode=disable'}])
      assert.equal(identityReadiness({...ok,...change}).ready,false,JSON.stringify(change));
});
test('disabled identity route is fail-closed without importing auth package',async()=>{
  const state={code:0,body:'',headers:{}};
  const res={writeHead(c,h){state.code=c;state.headers=h},end(x){state.body=x}};
  const prev=process.env.FLEX_AUTH_ENABLED;
  try {
    process.env.FLEX_AUTH_ENABLED='false';
    await handleFlexIdentity({},res);
    assert.equal(state.code,503);
    assert.match(state.body,/FLEX_IDENTITY_NOT_ENABLED/);
    assert.match(state.headers['Cache-Control'],/no-store/);
  }finally{
    if(prev===undefined)delete process.env.FLEX_AUTH_ENABLED;
    else process.env.FLEX_AUTH_ENABLED=prev;
  }
});
test('no platform token issuance, public signups or implicit admin grants',()=>{
 const s=readFileSync(new URL('../auth/identity-enabled.mjs',import.meta.url),'utf8');
 assert.match(s,/disableSignUp:true/);
 assert.match(s,/requireEmailVerification:true/);
 assert.match(s,/twoFactor\(/);
 assert.doesNotMatch(s,/amr\s*:|SUPER_ADMIN\s*=|signJWT\(|createAccessToken\(/);
});

test('pinned Better Auth TOTP staging module can import without creating sessions',async()=>{
  const staging=await import('../auth/identity-enabled.mjs');
  assert.equal(typeof staging.handleEnabledIdentity,'function');
});

test('schema generator imports the canonical Better Auth config, no drift',()=>{
 const s=readFileSync(new URL('../auth/schema-config.mjs',import.meta.url),'utf8');
 assert.match(s,/createFlexAuthConfig/);
 assert.match(s,/FLEX_AUTH_SCHEMA_DRY_RUN/);
 assert.doesNotMatch(s,/\bcreate\s+table\b/i);
});
