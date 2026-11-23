// This module is imported ONLY when audited auth data and explicit QA flags
// exist. It NEVER issues a platform JWT or grants SUPER ADMIN by a session.
import {betterAuth} from 'better-auth';
import {twoFactor} from 'better-auth/plugins';
import {toNodeHandler} from 'better-auth/node';
import pg from 'pg';
import {identityReadiness} from './identity-gate.mjs';
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
    plugins:[twoFactor({issuer:'MARINA SMART FLEX'})]
  });
}
let handler;
function getHandler() {
  if(!identityReadiness(process.env).ready) throw Error('FLEX_IDENTITY_NOT_READY');
  if(handler) return handler;
  const database=new pg.Pool({
    connectionString:process.env.FLEX_AUTH_DATABASE_URL,
    options:'-c search_path=flex_auth,pg_catalog',
    max:3,
    ssl:{rejectUnauthorized:true}
  });
  const auth=createFlexAuthConfig({database,baseURL:process.env.BETTER_AUTH_URL});
  handler=toNodeHandler(auth);
  return handler;
}
export async function handleEnabledIdentity(req,res) {
  return getHandler()(req,res);
}
