import {createHash} from 'node:crypto';

// Recovery token is issued only by a verified out-of-band mailbox workflow.
// Never expose a public endpoint that generates tokens or reveals account existence.
export async function redeemRecovery(database,token,newPassword,hashPassword) {
  if(typeof token!=='string' || !/^[A-Za-z0-9_-]{43}$/.test(token) ||
     typeof newPassword!=='string' || newPassword.length<12 || newPassword.length>128) return false;
  const digest=createHash('sha256').update(token).digest('hex');
  const client=await database.connect();
  try {
    await client.query('BEGIN');
    await client.query("SELECT pg_advisory_xact_lock(hashtext('flex:password-recovery'))");
    const proof=await client.query(
      'DELETE FROM flex_auth.verification WHERE identifier=$1 AND "expiresAt">clock_timestamp() RETURNING value',
      ['flex-recovery:'+digest]
    );
    if(proof.rowCount!==1){await client.query('ROLLBACK');return false;}
    const identity=await client.query(
      'SELECT id FROM flex_auth."user" WHERE email=$1 AND "emailVerified"=true FOR UPDATE',
      [proof.rows[0].value]
    );
    if(identity.rowCount!==1){await client.query('ROLLBACK');return false;}
    const userId=identity.rows[0].id;
    const passwordHash=await hashPassword(newPassword);
    const update=await client.query(
      'UPDATE flex_auth.account SET password=$1,"updatedAt"=now() WHERE "userId"=$2 AND "providerId"=$3',
      [passwordHash,userId,'credential']
    );
    if(update.rowCount!==1){await client.query('ROLLBACK');return false;}
    await client.query('DELETE FROM flex_auth.session WHERE "userId"=$1',[userId]);
    await client.query('COMMIT');
    return true;
  }catch(err){await client.query('ROLLBACK');throw err;}finally{client.release();}
}
