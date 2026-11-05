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
async function waitChrome(profile, child, readStderr) {
  // The ephemeral CDP port is written by Chrome inside its own isolated profile.
  // A fixed port occasionally collides with another process on CI runners.
  for (let n = 0; n < 120; n++) {
    if (child.exitCode !== null || child.signalCode !== null) {
      throw new Error('Chrome exited during startup: ' + readStderr().slice(-1500));
    }
    try {
      const [port] = (await readFile(path.join(profile, 'DevToolsActivePort'), 'utf8')).split(/\r?\n/);
      if (/^\d+$/.test(port)) {
        const response = await fetch('http://127.0.0.1:' + port + '/json', { signal: AbortSignal.timeout(1500) });
        const tabs = await response.json();
        const target = tabs.find(x => x.type === 'page' && x.webSocketDebuggerUrl);
        if (target) return target;
      }
    } catch { /* Chrome may still be initializing the isolated profile */ }
    await sleep(200);
  }
  throw new Error('Chrome DevTools did not become available: ' + readStderr().slice(-2000));
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
  if (!exe) {
    const message = 'WEB_VISUAL_BLOCKER no Chrome binary on this runner; screenshots NOT TESTED';
    if (process.env.GITHUB_ACTIONS === 'true') throw new Error(message);
    console.log(message);
    return;
  }
  await mkdir(evidenceDir, { recursive: true });
  server = createServer((req, res) => { void serve(req,res); });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  profileDir = await mkdtemp(path.join(tmpdir(), 'marina-web-qa-'));
  let browserLog = '';
  browser = spawn(exe, ['--headless=new', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
    '--remote-allow-origins=*', '--remote-debugging-port=0', '--user-data-dir=' + profileDir, 'about:blank'],
    { stdio: ['ignore', 'ignore', 'pipe'] });
  browser.stderr?.on('data', chunk => { browserLog = (browserLog + String(chunk)).slice(-6000); });
  const target = await waitChrome(profileDir, browser, () => browserLog);
  await openSocket(target.webSocketDebuggerUrl);
  await cdp('Page.enable'); await cdp('Runtime.enable');
  await viewport(375, 812);
  await nav('/connect');
  if (!await waitFor('[data-testid="web-demo-start"]')) {
    await diagnose('connect_missing');
    throw new Error('Expo Web connect screen did not mount');
  }
  try {
    // This is the ACTUAL exported Expo Web application with synthetic DEMO staff.
    // These images are not Android screenshots and never use a real hotel/API.
    await viewport(1440, 900);
    const desktop = await evaluate('(() => { const node=document.querySelector(\'[data-testid="mobile-web-viewport"]\'); const r=node?.getBoundingClientRect(); return {width:r?.width??0,x:r?.x??0,viewport:innerWidth,translate:document.documentElement.getAttribute("translate")} })()');
    if (desktop.width < 300 || desktop.width > 444 || Math.abs(desktop.x + desktop.width/2 - desktop.viewport/2) > 5)
      throw new Error('Desktop mobile frame not centered: '+JSON.stringify(desktop));
    if (desktop.translate !== 'no') throw new Error('Missing browser auto-translation protection');
    await screenshot('connect_ru_desktop_1440');
    await viewport(375,812);
    await click('[data-testid="segment-ru"]','Russian language');
    await screenshot('connect_ru_light_375');
    await click('[data-testid="web-demo-start"]','one-tap synthetic owner showroom');
    if (!await waitFor('[data-testid="tab-overview"]',6000)) throw new Error('Owner dashboard missing');
    await screenshot('owner_overview_ru_light_375');
    await click('[data-testid="tab-pms"]','owner PMS');
    if (!await waitFor('[data-testid="pms-next"]')) throw new Error('PMS 7-day grid missing');
    await screenshot('owner_pms_ru_light_375');
    await click('[data-testid="pms-next"]','week navigation');
    await screenshot('owner_pms_nextweek_ru_light_375');
    await click('[data-testid="tab-reception"]','guest arrivals');
    await screenshot('owner_reception_ru_light_375');
    await click('[data-testid="tab-inbox"]','synthetic WhatsApp list');
    if (!await waitFor('[data-testid="conversation-demo-chat-01"]')) throw new Error('DEMO inbox empty');
    await screenshot('owner_inbox_ru_light_375');
    await click('[data-testid="conversation-demo-chat-01"]','synthetic chat detail');
    await screenshot('owner_conversation_ru_light_375');
    await click('[aria-label="Закрыть"]','back to inbox');
    await click('[data-testid="tab-more"]','owner More');
    await screenshot('owner_more_ru_light_375');
    await click('[data-testid="more-profile"]','owner profile');
    await screenshot('owner_profile_ru_light_375');
    await click('[data-testid="segment-dark"]','dark theme');
    await screenshot('owner_profile_ru_dark_375');
    await click('[data-testid="segment-kg"]','Kyrgyz language');
    await screenshot('owner_profile_kg_dark_375');
    await click('[data-testid="segment-kz"]','Kazakh language');
    await screenshot('owner_profile_kz_dark_375');
    await click('[data-testid="segment-en"]','English language');
    await screenshot('owner_profile_en_dark_375');
    await click('[data-testid="switch-demo-role"]','switch synthetic role');
    await screenshot('login_en_dark_375');
    await viewport(1440,900);
    const loginFrame=await evaluate('(() => { const r=document.querySelector(\'[data-testid="mobile-web-viewport"]\')?.getBoundingClientRect(); return {width:r?.width??0,x:r?.x??0,viewport:innerWidth} })()');
    if (loginFrame.width < 300 || loginFrame.width > 444) throw new Error('Desktop login overstretched: '+JSON.stringify(loginFrame));
    await screenshot('login_en_dark_desktop_1440');
    await viewport(375,812);
    await click('[data-testid="demo-manager"]','synthetic manager role');
    if (!await waitFor('[data-testid="tab-overview"]')) throw new Error('Manager overview missing');
    await screenshot('manager_overview_en_dark_375');
    await click('[data-testid="tab-more"]','manager More');
    await click('[data-testid="more-admin"]','manager team');
    if (!await waitFor('[data-testid="open-assign-t8"]')) throw new Error('Manager task allocation missing');
    await screenshot('manager_team_en_dark_375');
    await viewport(320,640);
    await screenshot('manager_team_en_dark_320');
    await viewport(430,932);
    await click('[data-testid="open-assign-t8"]','open staff picker (no write)');
    if (!await waitFor('[data-testid="assign-u-maid"]')) throw new Error('Staff picker did not appear');
    await screenshot('manager_assign_en_dark_430');
    await viewport(375,812);
    await click('[data-testid="tab-more"]','manager More');
    await click('[data-testid="more-tasks"]','manager tasks');
    await screenshot('manager_tasks_en_dark_375');
    await click('[data-testid="tab-more"]','manager More');
    await click('[data-testid="more-profile"]','manager profile');
    await click('[data-testid="switch-demo-role"]','reception role selector');
    await click('[data-testid="demo-reception"]','reception role');
    if (!await waitFor('[data-testid="tab-reception"]')) throw new Error('Reception workspace missing');
    await screenshot('reception_en_dark_375');
    await click('[data-testid="segment-arrivals"]','arrival filter');
    await screenshot('reception_arrivals_en_dark_375');
    await click('[data-testid="tab-inbox"]','reception WhatsApp');
    await screenshot('reception_inbox_en_dark_375');
    await click('[data-testid="tab-profile"]','reception profile');
    await click('[data-testid="switch-demo-role"]','maid role selector');
    await click('[data-testid="demo-maid"]','maid role');
    if (!await waitFor('[data-testid="task-t2"]')) throw new Error('MAID task fixture missing');
    await screenshot('maid_tasks_en_dark_375');
    await click('[data-testid="task-t2"]','housekeeping checklist');
    await screenshot('maid_housekeeping_en_dark_375');
    await click('[aria-label="Back"]','task detail back');
    await click('[data-testid="tab-rooms"]','maid rooms');
    await screenshot('maid_rooms_en_dark_375');
    await click('[data-testid="room-r1"]','maid room detail');
    await screenshot('maid_room_detail_en_dark_375');
    await click('[aria-label="Back"]','room detail back');
    await click('[data-testid="tab-profile"]','maid profile');
    await click('[data-testid="switch-demo-role"]','technician role selector');
    await click('[data-testid="demo-tech"]','technician role');
    await screenshot('technician_tasks_en_dark_375');
    await click('[data-testid="tab-requests"]','maintenance list');
    await screenshot('technician_repairs_en_dark_375');
    await click('[data-testid="new-request-btn"]','maintenance form');
    await viewport(320,640);
    await screenshot('technician_new_request_en_dark_320');
    await viewport(375,812);
    await click('[aria-label="Cancel"]','return to repairs');
    await click('[data-testid="tab-profile"]','technician profile');
    await click('[data-testid="switch-demo-role"]','cook selector');
    await click('[data-testid="demo-cook"]','cook role');
    if (!await waitFor('[data-testid="order-d-order-01"]')) throw new Error('Cook kitchen showroom missing');
    await screenshot('cook_orders_en_dark_375');
    await click('[data-testid="tab-profile"]','cook profile');
    await click('[data-testid="switch-demo-role"]','waiter selector');
    await click('[data-testid="demo-waiter"]','waiter role');
    await screenshot('waiter_tables_en_dark_375');
    await click('[data-testid="tab-profile"]','waiter profile');
    await click('[data-testid="switch-demo-role"]','agent selector');
    await click('[data-testid="demo-agent"]','agent role');
    await screenshot('agent_pms_en_dark_375');
  } catch (e) {
    console.log('WEB_VISUAL_PARTIAL ' + String(e.message || e));
    await diagnose('partial');
    if (process.env.GITHUB_ACTIONS === 'true') throw e;
  }
  console.log('WEB_VISUAL_QA_END captured=' + emitted + ' actual=ExpoWeb not=Android');
}
main().catch(e => {
  console.log('WEB_VISUAL_BLOCKER ' + String(e.stack || e));
  // A failed screenshot run is NOT a visual QA pass. Never hide this in CI.
  process.exitCode = process.env.GITHUB_ACTIONS === 'true' ? 1 : 0;
})
  .finally(async () => {
    try { socket?.close(); } catch { /* cleanup */ }
    try { browser?.kill('SIGKILL'); } catch { /* cleanup */ }
    try { server?.close(); } catch { /* cleanup */ }
    try { if (profileDir) await rm(profileDir, {recursive:true, force:true}); } catch { /* cleanup */ }
  });