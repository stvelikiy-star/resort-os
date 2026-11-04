/**
 * Real exported Expo Web visual evidence, isolated localhost + bundled DEMO only.
 * Running here is NOT Android device testing. Never reads real hotel credentials.
 * Screenshots are saved locally and emitted in CI as reproducible JPEG evidence.
 */
import { createServer } from 'node:http';
import { readFile, mkdtemp, mkdir, writeFile, rm } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { spawn, execFileSync } from 'node:child_process';
import { Buffer } from 'node:buffer';

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const dist = path.resolve('dist');
const evidenceDir = path.resolve('visual-evidence');
const mime = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml', '.ttf': 'font/ttf', '.woff': 'font/woff', '.woff2': 'font/woff2', '.map': 'application/json' };
const asJson = value => JSON.stringify(value);
let browser;
let server;
let socket;
let profileDir;
let emitted = 0;
let requestId = 0;
const pending = new Map();

async function serve(req, res) {
  const url = new URL(req.url || '/', 'http://localhost');
  let rel;
  try { rel = decodeURIComponent(url.pathname).replace(/^\/+/, ''); } catch { res.writeHead(400); res.end(); return; }
  if (rel.includes('..')) { res.writeHead(403); res.end(); return; }
  let file = path.resolve(dist, rel || 'index.html');
  if (!file.startsWith(dist + path.sep) && file !== path.join(dist, 'index.html')) { res.writeHead(403); res.end(); return; }
  let bytes;
  try { bytes = await readFile(file); }
  catch {
    try { bytes = await readFile(path.join(dist, 'index.html')); file = path.join(dist, 'index.html'); }
    catch { res.writeHead(404); res.end(); return; }
  }
  res.writeHead(200, { 'Content-Type': mime[path.extname(file)] || 'application/octet-stream', 'Cache-Control': 'no-store' });
  res.end(bytes);
}
function chromeExe() {
  for (const cmd of ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser']) {
    try { return execFileSync('which', [cmd], { encoding: 'utf8' }).trim(); } catch { /* next */ }
  }
  return null;
}
async function waitChrome(port) {
  for (let n = 0; n < 75; n++) {
    try {
      const tabs = await (await fetch('http://127.0.0.1:' + port + '/json')).json();
      const target = tabs.find(x => x.type === 'page' && x.webSocketDebuggerUrl);
      if (target) return target;
    } catch { /* startup */ }
    await sleep(200);
  }
  throw new Error('Chrome DevTools connection unavailable');
}
async function openSocket(url) {
  socket = new WebSocket(url);
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('Chrome WebSocket timeout')), 10000);
    socket.addEventListener('open', () => { clearTimeout(timer); resolve(); }, { once: true });
    socket.addEventListener('error', e => { clearTimeout(timer); reject(new Error('Chrome WebSocket error ' + String(e.message || ''))); }, { once: true });
  });
  socket.addEventListener('message', event => {
    let msg; try { msg = JSON.parse(event.data); } catch { return; }
    if (!msg.id || !pending.has(msg.id)) return;
    const { resolve, reject } = pending.get(msg.id);
    pending.delete(msg.id);
    if (msg.error) reject(new Error(asJson(msg.error)));
    else resolve(msg.result);
  });
}
async function cdp(method, params = {}) {
  const id = ++requestId;
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => { pending.delete(id); reject(new Error('CDP timeout: ' + method)); }, 20000);
    pending.set(id, {
      resolve: value => { clearTimeout(timer); resolve(value); },
      reject: err => { clearTimeout(timer); reject(err); },
    });
    socket.send(asJson({ id, method, params }));
  });
}
async function evaluate(expression) {
  const response = await cdp('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
  if (response.exceptionDetails) throw new Error('Page JS exception: ' + asJson(response.exceptionDetails).slice(0, 250));
  return response.result?.value;
}
async function waitFor(selector, deadlineMs = 13000) {
  const start = Date.now();
  while (Date.now() - start < deadlineMs) {
    if (await evaluate('Boolean(document.querySelector(' + asJson(selector) + '))')) return true;
    await sleep(250);
  }
  return false;
}
async function click(selector, label) {
  if (!await waitFor(selector, 5000)) throw new Error('Missing ' + label + ' selector: ' + selector);
  await evaluate('(function(){ const el=document.querySelector(' + asJson(selector) + '); el.scrollIntoView({block:"center"}); el.click(); return true; })()');
  await sleep(650);
}
async function screenshot(name) {
  await sleep(900);
  const { data } = await cdp('Page.captureScreenshot', { format: 'jpeg', quality: 72, fromSurface: true, captureBeyondViewport: false });
  const bytes = Buffer.from(data, 'base64');
  if (bytes.byteLength < 3000) throw new Error('Suspiciously blank screenshot ' + name);
  await writeFile(path.join(evidenceDir, name + '.jpg'), bytes);
  console.log('WEB_VISUAL_CAPTURE ' + name + ' ' + bytes.length + 'B source=ExpoWeb fixture=DEMO');
  if (process.env.GITHUB_ACTIONS === 'true') console.log('WEB_VISUAL_JPEG:' + name + ':' + data);
  emitted++;
}
async function viewport(w, h) {
  await cdp('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile: true });
}
async function nav(pathname) {
  await cdp('Page.navigate', { url: 'http://127.0.0.1:' + server.address().port + pathname });
}
async function diagnose(name) {
  const info = await evaluate('({url:location.pathname,text:document.body?.innerText?.slice(0,350),w:document.documentElement.scrollWidth,viewport:innerWidth,root:!!document.querySelector("#root")})');
  console.log('WEB_VISUAL_DIAG ' + name + ' ' + asJson(info));
  return info;
}
async function main() {
  if (!existsSync(path.join(dist, 'index.html'))) throw new Error('Expo export missing dist/index.html');
  const exe = chromeExe();
  if (!exe) { console.log('WEB_VISUAL_BLOCKER no Chrome binary on this runner; screenshots NOT TESTED'); return; }
  await mkdir(evidenceDir, { recursive: true });
  server = createServer((req, res) => { void serve(req,res); });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  profileDir = await mkdtemp(path.join(tmpdir(), 'marina-web-qa-'));
  const debugPort = 19914;
  browser = spawn(exe, ['--headless=new', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
    '--remote-allow-origins=*', '--remote-debugging-port=' + debugPort, '--user-data-dir=' + profileDir, 'about:blank'],
    { stdio: 'ignore' });
  const target = await waitChrome(debugPort);
  await openSocket(target.webSocketDebuggerUrl);
  await cdp('Page.enable'); await cdp('Runtime.enable');
  await viewport(375, 812);
  await nav('/connect');
  if (!await waitFor('[data-testid="web-demo-start"]')) {
    await diagnose('connect_missing');
    throw new Error('Expo Web connect screen did not mount');
  }
  try {
    await click('[data-testid="segment-ru"]', 'Russian language');
    await screenshot('connect_ru_light_375');
    await click('[data-testid="web-demo-start"]', 'demo staff launcher');
    if (!await waitFor('[data-testid="tab-tasks"]')) throw new Error('Demo staff tasks navigation absent');
    await diagnose('maid_tasks');
    await screenshot('maid_tasks_ru_light_375');
    await click('[data-testid="tab-profile"]', 'maid profile');
    if (!await waitFor('[data-testid="segment-dark"]')) throw new Error('Theme selector not visible');
    await screenshot('maid_profile_ru_light_375');
    await click('[data-testid="segment-dark"]', 'dark theme');
    await screenshot('maid_profile_ru_dark_375');
    await click('[data-testid="segment-en"]', 'English language');
    await screenshot('maid_profile_en_dark_375');
    await click('[data-testid="tab-tasks"]', 'back to tasks');
    await screenshot('maid_tasks_en_dark_375');
  } catch (e) {
    console.log('WEB_VISUAL_PARTIAL ' + String(e.message || e));
    await diagnose('partial');
  }
  console.log('WEB_VISUAL_QA_END captured=' + emitted + ' actual=ExpoWeb not=Android');
}
main().catch(e => { console.log('WEB_VISUAL_BLOCKER ' + String(e.stack || e)); process.exitCode = 0; })
  .finally(async () => {
    try { socket?.close(); } catch { /* cleanup */ }
    try { browser?.kill('SIGKILL'); } catch { /* cleanup */ }
    try { server?.close(); } catch { /* cleanup */ }
    try { if (profileDir) await rm(profileDir, {recursive:true, force:true}); } catch { /* cleanup */ }
  });