import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { randomBytes, createHash, createCipheriv, createDecipheriv, createPublicKey, verify, timingSafeEqual } from 'node:crypto';

const root = dirname(fileURLToPath(import.meta.url));
const port = Number(process.env.PORT || 3407);
const host = process.env.HOST || '127.0.0.1';
const publicOrigin = (process.env.FLEX_PUBLIC_ORIGIN || '').replace(/\/$/, '');
const issuer = (process.env.FLEX_OIDC_ISSUER || '').replace(/\/$/, '');
const clientId = process.env.FLEX_OIDC_CLIENT_ID || '';
const apiAudience = process.env.FLEX_API_AUDIENCE || '';
const apiOrigin = (process.env.FLEX_API_ORIGIN || '').replace(/\/$/, '');
const partnerApiOrigin = (process.env.FLEX_PARTNER_API_ORIGIN || apiOrigin).replace(/\/$/, '');
const rawSecret = process.env.FLEX_SESSION_KEY || '';
const secret = rawSecret ? Buffer.from(rawSecret, 'base64') : null;
const configured = Boolean(publicOrigin && issuer && clientId && apiAudience && apiOrigin && partnerApiOrigin && secret?.length === 32);
const localOrigin = publicOrigin === 'http://127.0.0.1:' + port || publicOrigin === 'http://localhost:' + port;
if (configured && (!publicOrigin.startsWith('https://') && !localOrigin)) throw new Error('FLEX_PUBLIC_ORIGIN must use HTTPS outside localhost');
if (configured && (![issuer, apiOrigin, partnerApiOrigin].every(v => v.startsWith('https://') || (localOrigin && /^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(v))))) {
  throw new Error('OIDC and FLEX backend endpoints require HTTPS outside localhost');
}
const secureCookie = publicOrigin.startsWith('https://');
const cookies = { login: 'flex_login', session: 'flex_session' };
const noStore = { 'Cache-Control': 'no-store, private', 'Pragma': 'no-cache', 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer', 'X-Frame-Options': 'DENY', 'Cross-Origin-Resource-Policy': 'same-origin', 'Permissions-Policy': 'camera=(), microphone=(), geolocation=()' };

function json(res, status, body, headers={}) { res.writeHead(status, { ...noStore, 'Content-Type':'application/json; charset=utf-8', ...headers }); res.end(JSON.stringify(body)); }
function redirect(res, location, headers={}) { res.writeHead(302, { ...noStore, Location:location, ...headers }); res.end(); }
function cookie(name, value, maxAge=900, path='/') { return name + '=' + encodeURIComponent(value) + '; HttpOnly; SameSite=Lax; Path=' + path + '; Max-Age=' + maxAge + (secureCookie?'; Secure':''); }
function cookiesFrom(req) { return Object.fromEntries((req.headers.cookie || '').split(';').map(x=>x.trim()).filter(Boolean).map(p=>{const i=p.indexOf('='); return [p.slice(0,i),decodeURIComponent(p.slice(i+1))]})); }
function seal(obj) {
  const iv=randomBytes(12), cipher=createCipheriv('aes-256-gcm',secret,iv);
  const input=Buffer.from(JSON.stringify(obj));
  const enc=Buffer.concat([cipher.update(input),cipher.final()]);
  return Buffer.concat([iv,cipher.getAuthTag(),enc]).toString('base64url');
}
function unseal(value) {
  try {
    if (!configured || !value) return null;
    const raw=Buffer.from(value,'base64url'); if(raw.length < 29) return null;
    const decipher=createDecipheriv('aes-256-gcm',secret,raw.subarray(0,12));
    decipher.setAuthTag(raw.subarray(12,28));
    const o=JSON.parse(Buffer.concat([decipher.update(raw.subarray(28)),decipher.final()]).toString());
    return Number.isFinite(o.exp) && o.exp > Date.now() ? o : null;
  } catch { return null; }
}
function fixedEqual(a,b) { const x=Buffer.from(String(a)), y=Buffer.from(String(b)); return x.length===y.length && timingSafeEqual(x,y); }
function b64u(b) { return Buffer.from(b).toString('base64url'); }
function sha256(text) { return b64u(createHash('sha256').update(text).digest()); }
async function discover() {
  const url=issuer + '/.well-known/openid-configuration';
  const res=await fetch(url,{signal:AbortSignal.timeout(8000)});
  if(!res.ok) throw new Error('OIDC discovery failed');
  const doc=await res.json();
  if(doc.issuer!==issuer) throw new Error('OIDC issuer mismatch');
  for(const key of ['authorization_endpoint','token_endpoint','jwks_uri']) {
    const u=new URL(doc[key]); if(u.protocol!=='https:' && !localOrigin) throw new Error('Insecure OIDC endpoint');
  }
  return doc;
}
async function verifyJwt(token, doc, audience, nonce) {
  if(typeof token!=='string'||token.split('.').length!==3) throw new Error('Expected signed JWT');
  const [h,p,s] = token.split('.');
  const header=JSON.parse(Buffer.from(h,'base64url').toString());
  const claims=JSON.parse(Buffer.from(p,'base64url').toString());
  if(!['RS256','EdDSA'].includes(header.alg) || !header.kid) throw new Error('Unsupported JWT signature');
  const aud=Array.isArray(claims.aud)?claims.aud:[claims.aud];
  const now=Math.floor(Date.now()/1000);
  if(claims.iss!==issuer||!aud.includes(audience)||!(claims.exp>now)|| (claims.nbf && claims.nbf>now+30)) throw new Error('Invalid issuer/audience/lifetime');
  if(nonce && !fixedEqual(claims.nonce,nonce)) throw new Error('OIDC nonce mismatch');
  const keysResponse=await fetch(doc.jwks_uri,{signal:AbortSignal.timeout(8000)});
  if(!keysResponse.ok) throw new Error('JWKS not available');
  const keys=(await keysResponse.json()).keys || [];
  const jwk=keys.find(k=>k.kid===header.kid && (!k.alg||k.alg===header.alg));
  if(!jwk) throw new Error('Unknown JWT signing key');
  const key=createPublicKey({key:jwk,format:'jwk'});
  const ok=verify(header.alg==='EdDSA'?null:'RSA-SHA256',Buffer.from(h+'.'+p),key,Buffer.from(s,'base64url'));
  if(!ok) throw new Error('JWT signature invalid');
  return claims;
}
async function authLogin(res) {
  if(!configured) return json(res,503,{error:'QA_IDENTITY_NOT_CONFIGURED'});
  const doc=await discover();
  const state=b64u(randomBytes(32)),nonce=b64u(randomBytes(32)),verifier=b64u(randomBytes(32));
  const query=new URLSearchParams({ response_type:'code',client_id:clientId, redirect_uri:publicOrigin+'/api/auth/callback',scope:'openid profile',state,nonce,code_challenge:sha256(verifier),code_challenge_method:'S256' });
  redirect(res,doc.authorization_endpoint+'?'+query,{ 'Set-Cookie':cookie(cookies.login,seal({state,nonce,verifier,exp:Date.now()+600000}),600,'/api/auth') });
}
async function authCallback(req,res,url) {
  const payload=unseal(cookiesFrom(req)[cookies.login]);
  if(!payload || !fixedEqual(payload.state,url.searchParams.get('state') || '')) return json(res,401,{error:'OIDC_STATE_INVALID'});
  if(!url.searchParams.get('code')||url.searchParams.get('error')) return json(res,401,{error:'OIDC_AUTH_DENIED'});
  const doc=await discover();
  const params=new URLSearchParams({ grant_type:'authorization_code',code:url.searchParams.get('code'),redirect_uri:publicOrigin+'/api/auth/callback',client_id:clientId,code_verifier:payload.verifier });
  if(process.env.FLEX_OIDC_CLIENT_SECRET) params.set('client_secret',process.env.FLEX_OIDC_CLIENT_SECRET);
  const reply=await fetch(doc.token_endpoint,{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:params,signal:AbortSignal.timeout(8000)});
  if(!reply.ok) return json(res,401,{error:'OIDC_TOKEN_EXCHANGE_FAILED'});
  const data=await reply.json();
  if(!data.id_token || !data.access_token) return json(res,401,{error:'OIDC_TOKENS_MISSING'});
  await verifyJwt(data.id_token,doc,clientId,payload.nonce);
  const claims=await verifyJwt(data.access_token,doc,apiAudience);
  const expiresMs=Math.min(Number(data.expires_in||900)*1000,(claims.exp*1000)-Date.now(),900000);
  if(expiresMs<10000) return json(res,401,{error:'OIDC_TOKEN_EXPIRED'});
  const session=seal({ token:data.access_token, exp:Date.now()+expiresMs });
  redirect(res,'/',{ 'Set-Cookie':[cookie(cookies.login,'',0,'/api/auth'),cookie(cookies.session,session,Math.floor(expiresMs/1000))] });
}
const hotelPattern=/^\/v1\/hotels\/[0-9a-fA-F-]{36}\/(subscription|invoices)$/;
function routeAllowed(path, search) {
  if(search && [...search.keys()].some(k=>k!=='period')) return null;
  if(['/v1/me','/v1/hotels','/v1/catalog'].includes(path) && !search.size) return 'core';
  if(hotelPattern.test(path) && !search.size) return 'core';
  if(['/v1/partner/me/earnings','/v1/platform/partner-earnings-summary'].includes(path)
     && (!search.size || (search.size===1 && ['day','week','month'].includes(search.get('period'))))) return 'partner';
  return null;
}
async function proxy(req,res,url) {
  if(!configured) return json(res,503,{error:'QA_BACKEND_NOT_CONFIGURED'});
  const session=unseal(cookiesFrom(req)[cookies.session]);
  if(!session) return json(res,401,{error:'LOGIN_REQUIRED'});
  const path=url.pathname.replace(/^\/api\/data/,'');
  const target=routeAllowed(path,url.searchParams);
  if(!target) return json(res,404,{error:'READ_ONLY_ENDPOINT_NOT_AVAILABLE'});
  const backend=(target==='partner'?partnerApiOrigin:apiOrigin)+path+url.search;
  const upstream=await fetch(backend,{method:'GET',headers:{'Authorization':'Bearer '+session.token,'Accept':'application/json'},redirect:'manual',signal:AbortSignal.timeout(10000)});
  if(upstream.status>=300 && upstream.status<400) return json(res,502,{error:'UNEXPECTED_UPSTREAM_REDIRECT'});
  const contentType=upstream.headers.get('content-type')||'';
  if(!contentType.includes('application/json')) return json(res,502,{error:'UPSTREAM_NON_JSON'});
  const body=await upstream.text();
  if(body.length>500000) return json(res,502,{error:'UPSTREAM_TOO_LARGE'});
  res.writeHead(upstream.status,{...noStore,'Content-Type':'application/json; charset=utf-8'}); res.end(body);
}
async function staticFile(res, pathname) {
  const files={'/':'index.html','/app.js':'app.js','/styles.css':'styles.css'};
  const f=files[pathname]; if(!f) return json(res,404,{error:'NOT_FOUND'});
  const data=await readFile(join(root,'public',f));
  const mime=f.endsWith('.js')?'application/javascript; charset=utf-8':f.endsWith('.css')?'text/css; charset=utf-8':'text/html; charset=utf-8';
  const csp="default-src 'none'; base-uri 'none'; form-action 'self'; connect-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; frame-ancestors 'none'";
  res.writeHead(200,{...noStore,'Content-Type':mime,'Content-Security-Policy':csp});
  res.end(data);
}
export async function handler(req,res) {
  try {
    const url=new URL(req.url,'http://localhost');
    if(req.method!=='GET') return json(res,405,{error:'READ_ONLY'});
    if(url.pathname==='/api/status') return json(res,200,{configured,mode:'READ_ONLY_QA',payments_enabled:false,payouts_enabled:false});
    if(url.pathname==='/api/auth/login') return await authLogin(res);
    if(url.pathname==='/api/auth/callback') return await authCallback(req,res,url);
    if(url.pathname==='/api/auth/logout') return redirect(res,'/',{'Set-Cookie':cookie(cookies.session,'',0)});
    if(url.pathname.startsWith('/api/data/')) return await proxy(req,res,url);
    return await staticFile(res,url.pathname);
  } catch(e) { console.error('FLEX console error:',e.message); return json(res,502,{error:'QA_SERVICE_UNAVAILABLE'}); }
}
if(process.env.NODE_ENV!=='test') createServer(handler).listen(port,host,()=>console.log('MARINA FLEX Console READ-ONLY listening on http://'+host+':'+port));
export const testRouteAllowed=routeAllowed;
