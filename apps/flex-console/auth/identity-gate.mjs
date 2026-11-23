// MARINA SMART FLEX only; disabled until audited Neon auth schema and MFA.
function validDatabase(value) {
  try {
    const u=new URL(value);
    return ['postgres:','postgresql:'].includes(u.protocol) &&
      u.username==='flex_auth_runtime' && u.pathname==='/flex_qa' &&
      u.hostname.endsWith('.neon.tech') && Boolean(u.password) &&
      ['require','verify-ca','verify-full'].includes(u.searchParams.get('sslmode'));
  } catch { return false; }
}
export function identityReadiness(env=process.env) {
  if(env.FLEX_ENVIRONMENT!=='qa'||env.FLEX_AUTH_ENABLED!=='true') return {ready:false,reason:'DISABLED'};
  if(env.FLEX_AUTH_SCHEMA_READY!=='true') return {ready:false,reason:'SCHEMA_NOT_ACCEPTED'};
  try {
    const u=new URL(env.BETTER_AUTH_URL);
    if(u.protocol!=='https:'||u.pathname!=='/'||u.search||u.hash) throw Error('origin');
  } catch { return {ready:false,reason:'INVALID_ORIGIN'}; }
  if(typeof env.BETTER_AUTH_SECRET!=='string'||env.BETTER_AUTH_SECRET.length<43)
    return {ready:false,reason:'MISSING_SECRET'};
  if(!validDatabase(env.FLEX_AUTH_DATABASE_URL))
    return {ready:false,reason:'INVALID_AUTH_DATABASE'};
  return {ready:true,reason:'STAGING_ONLY'};
}
export async function validatePasswordSession(req,subject){
  if(!identityReadiness(process.env).ready)return false;
  const {verifiedPasswordSession}=await import('./identity-enabled.mjs');
  return verifiedPasswordSession(req,subject);
}
export async function handleFlexIdentity(req,res,issueSessionCookie) {
  if(!identityReadiness(process.env).ready) {
    res.writeHead(503,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'private, no-store',
      'X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY'});
    return res.end('{"error":"FLEX_IDENTITY_NOT_ENABLED"}');
  }
  const {handleEnabledIdentity}=await import('./identity-enabled.mjs');
  return handleEnabledIdentity(req,res,issueSessionCookie);
}
