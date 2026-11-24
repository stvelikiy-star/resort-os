// This module is imported ONLY when audited auth data and explicit QA flags
// exist. It NEVER issues a platform JWT or grants SUPER ADMIN by a session.
import {betterAuth} from 'better-auth';
import {twoFactor} from 'better-auth/plugins';
import {toNodeHandler} from 'better-auth/node';
import pg from 'pg';
import {verifiedLogin} from './mfa-bridge.mjs';
import {hashPassword} from 'better-auth/crypto';
import {redeemFirstInvite} from './first-invite.mjs';
import {identityReadiness} from './identity-gate.mjs';
export const passwordMode=()=>process.env.FLEX_ENVIRONMENT==='qa' && process.env.VERCEL_ENV==='preview' && process.env.FLEX_QA_PASSWORD_LOGIN==='true';
export function createFlexAuthConfig({database,baseURL}) {
  return betterAuth({
    appName:'MARINA SMART FLEX',
    baseURL,basePath:'/api/identity',database,
    emailAndPassword:{
      enabled:true,disableSignUp:true,requireEmailVerification:true,
      minPasswordLength:12,maxPasswordLength:128
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
export async function handleEnabledIdentity(req,res,issueSessionCookie) {
  const {database,handler,auth}=await getHandler();
  if(new URL(req.url,'http://localhost').pathname==='/api/identity/first-invite'){
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
    return respond(await redeemFirstInvite(database,body?.token,body?.password,hashPassword)?204:403);
  }
  const path=req.url.split('?')[0];
  if(issueSessionCookie && (path==='/api/identity/two-factor/verify-totp' || (passwordMode() && path==='/api/identity/sign-in/email'))){
    const origin=new URL(process.env.BETTER_AUTH_URL).origin;
    return toNodeHandler(request=>verifiedLogin(auth,request,origin,issueSessionCookie,passwordMode()))(req,res);
  }
  return handler(req,res);
}
