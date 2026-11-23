import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';

test('isolated Vercel QA uses Node HTTP entrypoint and fails closed without backend',()=>{
  const config=JSON.parse(readFileSync(new URL('../vercel.json',import.meta.url),'utf8'));
  assert.equal(config.functions['server.js'].includeFiles,'public/**');
  assert.ok(!config.rewrites,'No unexpected rewrites to external systems');
  const h=config.headers[0].headers;
  assert.ok(h.some(x=>x.key==='Cache-Control'&&x.value.includes('no-store')));
  assert.ok(h.some(x=>x.key==='Content-Security-Policy'&&x.value.includes("connect-src 'self'")));
  const server=readFileSync(new URL('../server.js',import.meta.url),'utf8');
  assert.ok(server.includes('createServer(handler)'));
  assert.ok(server.includes("from './server.mjs'"));
  assert.ok(!server.includes('.listen('), 'Vercel must own the listener');
  assert.ok(!server.includes('/v1/payments'));
});

test('importing QA handler for Vercel does not start an accidental TCP listener',()=>{
  const dir=new URL('..',import.meta.url).pathname;
  const cmd=spawnSync(process.execPath,['--input-type=module','-e',
   "import('./server.mjs').then(()=>process.stdout.write('OK'))"],{
    cwd:dir,timeout:5000,encoding:'utf8',
    env:{...process.env,NODE_ENV:'production',PORT:'0',FLEX_ENVIRONMENT:'qa'}
  });
  assert.equal(cmd.error?.code,undefined,'Import must exit without live TCP server');
  assert.equal(cmd.status,0,cmd.stderr);
  assert.equal(cmd.stdout,'OK');
});

test('Vercel production entrypoint exports a server but never binds to TCP',()=>{
  const dir=new URL('..',import.meta.url).pathname;
  const cmd=spawnSync(process.execPath,['--input-type=module','-e',
   "import('./server.js').then(({default:server})=> { if(server.listening)process.exit(2); process.stdout.write('UNBOUND') })"],{
    cwd:dir,timeout:5000,encoding:'utf8',
    env:{...process.env,NODE_ENV:'production',PORT:'0',FLEX_ENVIRONMENT:'qa'}
  });
  assert.equal(cmd.error?.code,undefined,'Vercel import must not keep the Node event loop alive');
  assert.equal(cmd.status,0,cmd.stderr);
  assert.equal(cmd.stdout,'UNBOUND');
});
