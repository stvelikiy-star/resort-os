// Operator-only FLEX QA owner invitation; no public signup and no password handling.
// Execute from a clean accepted checkout with its existing console dependencies installed.
// Required environment: FLEX_MIGRATION_DATABASE_URL, FLEX_RESEND_API_KEY, FLEX_RECOVERY_FROM.
import {createRequire} from 'node:module';
import {execFileSync} from 'node:child_process';
import {randomBytes,randomUUID,createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {parseArgs} from 'node:util';
const require=createRequire(new URL('../apps/flex-console/package.json',import.meta.url));
const {Pool}=require('pg');
const {values}=parseArgs({options:{'approve-qa':{type:'string'},'hotel-id':{type:'string'},email:{type:'string'},'admin-email':{type:'string'}},strict:true});
const root=fileURLToPath(new URL('..',import.meta.url));
const release=execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).trim();
const clean=execFileSync('git',['status','--porcelain','--','apps/flex-console','scripts/marina_flex_issue_qa_owner_invite.mjs','docs/flex/sql'],{cwd:root,encoding:'utf8'}).trim();
const email=values.email?.trim().toLowerCase(),adminEmail=values['admin-email']?.trim().toLowerCase();
const validEmail=v=>typeof v==='string' && v.length<=254 && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);
const hotels=new Map([['d36a9069-e64e-4655-9776-968ec7eeba65','FLEX QA · Гостиница А'],['f9d9402c-c932-4a94-9165-4133eb60f855','FLEX QA · Гостиница Б']]);
const hotel=values['hotel-id'];
const origin='https://marina-smart-flex-qa-git-qa-flex-pilot-20261124-ai-prof-kg.vercel.app';
if(clean || values['approve-qa']!==release || !/^[0-9a-f]{40}$/.test(release) || !hotels.has(hotel) || !validEmail(email) || !validEmail(adminEmail) || email===adminEmail) throw Error('Explicit approved QA commit, existing admin and distinct test mailbox/hotel required');
const dsn=new URL(process.env.FLEX_MIGRATION_DATABASE_URL||'');
if(dsn.protocol!=='postgresql:' || dsn.username!=='flex_qa_owner' || dsn.pathname!=='/flex_qa' || !/^ep-blue-pine-bapioek5\.[a-z0-9.-]+\.neon\.tech$/.test(dsn.hostname) || !['require','verify-full','verify-ca'].includes(dsn.searchParams.get('sslmode')))throw Error('Wrong QA target');
const key=process.env.FLEX_RESEND_API_KEY,from=process.env.FLEX_RECOVERY_FROM;
if(!key||!from)throw Error('Existing FLEX mail configuration required');
const pool=new Pool({connectionString:dsn.href,max:1,connectionTimeoutMillis:10000,ssl:{rejectUnauthorized:true}});
const client=await pool.connect();
let committed=false;
try {
 await client.query('BEGIN');
 await client.query("SET LOCAL lock_timeout='5s'");
 await client.query("SET LOCAL statement_timeout='20s'");
 await client.query("SELECT pg_advisory_xact_lock(hashtext('flex:first-identity'))");
 const guard=await client.query(`SELECT current_database()='flex_qa' AND current_user='flex_qa_owner' AND
 (SELECT count(*) FROM flex_private.flex_schema_migrations)=31 AND
 (SELECT disposition FROM flex_private.flex_schema_migrations WHERE migration_id=9)='SKIPPED_PAYMENT_FREEZE' AND
 NOT EXISTS(SELECT 1 FROM flex_private.flex_confirmed_payments) AND
 NOT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname IN ('auth','storage','realtime','supabase_functions')) AS ok`);
 if(guard.rows[0]?.ok!==true)throw Error('FLEX QA guard rejected');
 const admin=await client.query(`SELECT m.subject_id FROM flex_private.flex_platform_memberships m JOIN flex_auth."user" u ON u.id=m.subject_id
 WHERE m.role='SUPER_ADMIN' AND m.active AND u."emailVerified" AND lower(u.email)=$1`,[adminEmail]);
 if(admin.rowCount!==1)throw Error('Existing verified SUPER_ADMIN required');
 const target=await client.query('SELECT id FROM flex_private.flex_hotels WHERE id=$1 AND display_name=$2',[hotel,hotels.get(hotel)]);
 if(target.rowCount!==1)throw Error('Expected test hotel required');
 const collision=await client.query(`SELECT 1 FROM flex_auth."user" WHERE lower(email)=$1 UNION ALL
 SELECT 1 FROM flex_auth.verification WHERE identifier LIKE 'flex-owner:%' AND "expiresAt">now() AND value::jsonb->>'email'=$1`,[email]);
 if(collision.rowCount)throw Error('Email already used or pending');
 if((await client.query(`SELECT 1 FROM flex_private.flex_platform_hotel_grants g JOIN flex_private.flex_platform_memberships m ON m.subject_id=g.subject_id WHERE g.hotel_id=$1 AND m.role='HOTEL_OWNER' AND m.active`,[hotel])).rowCount)throw Error('Test hotel already has active owner');
 const subject='qa-owner:'+randomUUID(),token=randomBytes(32).toString('base64url'),identifier='flex-owner:'+createHash('sha256').update(token).digest('hex');
 await client.query("INSERT INTO flex_private.flex_platform_memberships(subject_id,role,active) VALUES($1,'HOTEL_OWNER',true)",[subject]);
 await client.query('INSERT INTO flex_private.flex_platform_hotel_grants(subject_id,hotel_id,granted_by) VALUES($1,$2,$3)',[subject,hotel,admin.rows[0].subject_id]);
 await client.query(`INSERT INTO flex_auth.verification(id,identifier,value,"expiresAt","createdAt","updatedAt") VALUES($1,$2,$3,now()+interval '30 minutes',now(),now())`,[randomUUID(),identifier,JSON.stringify({kind:'QA_HOTEL_OWNER',subject,email})]);
 await client.query(`INSERT INTO flex_private.flex_audit_events(platform_subject_id,action,resource_type,resource_id,metadata) VALUES($1,'QA_OWNER_INVITE','hotel',$2,jsonb_build_object('role','HOTEL_OWNER','subject_id',$3,'release_sha',$4))`,[admin.rows[0].subject_id,hotel,subject,release]);
 const link=new URL('/enroll',origin);link.hash=token;
 const response=await fetch('https://api.resend.com/emails',{method:'POST',headers:{Authorization:'Bearer '+key,'Content-Type':'application/json'},body:JSON.stringify({from,to:[email],subject:'MARINA SMART FLEX · Приглашение / Чакыруу / Invitation',text:'Создайте пароль для тестового кабинета владельца гостиницы.\nСыноо мейманкана кабинетине сырсөз түзүңүз.\nSet your password for the test hotel-owner account.\n'+link.href+'\n30 минут / 30 мүнөт / 30 minutes'}),signal:AbortSignal.timeout(10000)});
 if(!response.ok)throw Error('Invitation mail rejected');
 await client.query('COMMIT');committed=true;
 console.log('PASS: single QA hotel owner invitation issued and mail accepted; token not logged');
} catch {
 if(!committed)await client.query('ROLLBACK').catch(()=>{});
 console.error('QA invitation not confirmed. Verify state before retrying; no credentials logged.');
 process.exitCode=1;
} finally {client.release();await pool.end();}
