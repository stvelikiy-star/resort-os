// CI-only: resolves Better Auth's EXACT production plugin/schema config.
// This dummy localhost pool is never opened by schema generation.
// Do not use this configuration to deploy, serve requests or migrate Neon.
import pg from 'pg';
import {createFlexAuthConfig} from './identity-enabled.mjs';
if(process.env.FLEX_AUTH_SCHEMA_DRY_RUN !== 'true')
  throw new Error('FLEX_AUTH_SCHEMA_DRY_RUN_REQUIRED');
const dummy=new pg.Pool({
  connectionString:'postgresql://ci_no_login:ci_no_secret@127.0.0.1:55449/flex_ci',
  options:'-c search_path=flex_auth,pg_catalog'
});
export const auth=createFlexAuthConfig({
  database:dummy,
  baseURL:'http://127.0.0.1:3407'
});
