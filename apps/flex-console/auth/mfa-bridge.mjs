import {createPrivateKey,randomUUID,sign} from 'node:crypto';

export function createMfaSigner(env){
  if(env.FLEX_ENVIRONMENT!=='qa'||env.FLEX_MFA_BRIDGE_ENABLED!=='true')return null;
  const {FLEX_MFA_PRIVATE_KEY: pem,FLEX_MFA_KEY_ID: kid,BETTER_AUTH_URL: origin,FLEX_API_AUDIENCE: audience}=env;
  if(!/^[A-Za-z0-9_-]{2,80}$/.test(kid||'') || !origin || new URL(origin).protocol!=='https:' || !audience)
    throw Error('Incomplete MFA issuer settings');
  const key=createPrivateKey(pem);
  if(key.asymmetricKeyType!=='ed25519')throw Error('FLEX issuer requires Ed25519');
  const issuer=new URL(origin).origin;
  const encode=value=>Buffer.from(JSON.stringify(value)).toString('base64url');
  return (subject,method='totp')=>{
    if(typeof subject!=='string'||!/^[a-zA-Z0-9_:.@/-]{2,180}$/.test(subject))throw Error('Invalid subject');
    const now=Math.floor(Date.now()/1000);
    const exp=now+300;
    const claims={iss:issuer,aud:audience,sub:subject,iat:now,nbf:now,exp,jti:randomUUID(),amr:method==='password'?['pwd']:['pwd','otp','mfa']};
    const input=encode({alg:'EdDSA',kid,typ:'JWT'})+'.'+encode(claims);
    return {token:input+'.'+sign(null,Buffer.from(input),key).toString('base64url'),exp:exp*1000};
  };
}

// Inspect only the actual response to a fresh password-login TOTP challenge.
// Never exchange an existing identity session, an enrollment, or a client assertion.
export async function verifiedLogin(auth,request,origin,issueSessionCookie,passwordMode=false){
  const url=new URL(request.url);
  const passwordLogin=passwordMode && request.method==='POST' && url.pathname==='/api/identity/sign-in/email' && request.headers.get('origin')===origin;
  const checking=request.method==='POST' && url.pathname==='/api/identity/two-factor/verify-totp' &&
    request.headers.get('origin')===origin && request.headers.get('cookie') &&
    !await auth.api.getSession({headers:request.headers});
  const response=await auth.handler(request);
  if((!checking && !passwordLogin) || response.status!==200)return response;
  const result=await response.clone().json();
  if(result.user?.emailVerified!==true || typeof result.token!=='string' || !result.token)return response;
  const headers=new Headers(response.headers);
  headers.append('Set-Cookie',issueSessionCookie(result.user.id,passwordLogin?'password':'totp'));
  headers.delete('content-length');
  return Response.json({verified:true,platform_session:true},{headers});
}
