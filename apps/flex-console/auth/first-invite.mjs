import {createHash, randomUUID, randomBytes} from 'node:crypto';

// The operator delivers 32 random bytes (base64url) only to the intended
// mailbox. Store its SHA-256 hex digest as verification.identifier with
// prefix flex-first:, the normalized email as value and a short expiresAt.
export async function redeemFirstInvite(database, token, password, hashPassword, options = {}) {
  if (typeof token !== 'string' || !/^[A-Za-z0-9_-]{43}$/.test(token) ||
      typeof password !== 'string' || password.length < 12 || password.length > 128) return false;
  const digest = createHash('sha256').update(token).digest('hex');
  const client = await database.connect();
  try {
    await client.query('BEGIN');
    await client.query("SELECT pg_advisory_xact_lock(hashtext('flex:first-identity'))");
    const invitation = await client.query(
      'DELETE FROM flex_auth.verification WHERE identifier=$1 AND "expiresAt">clock_timestamp() RETURNING value',
      ['flex-first:' + digest]
    );
    let email, userId;
    if (invitation.rowCount === 1) {
      // Bootstrap semantics stay unchanged: never create another first admin.
      if ((await client.query('SELECT 1 FROM flex_auth."user" LIMIT 1')).rowCount) {
        await client.query('ROLLBACK');
        return false;
      }
      email = invitation.rows[0].value;
      userId = randomUUID();
    } else if (invitation.rowCount === 0 && options.allowOwnerInvite === true) {
      // Only an operator-created, one-time owner invitation can reach this path.
      // Its subject is pre-authorized in flex_private by the operator; the
      // identity runtime never writes memberships or hotel grants.
      const ownerInvite = await client.query(
        'DELETE FROM flex_auth.verification WHERE identifier=$1 AND "expiresAt">clock_timestamp() RETURNING value',
        ['flex-owner:' + digest]
      );
      let payload;
      try { payload = ownerInvite.rowCount === 1 ? JSON.parse(ownerInvite.rows[0].value) : null; } catch { payload = null; }
      if (!payload || payload.kind !== 'QA_HOTEL_OWNER' ||
          typeof payload.subject !== 'string' ||
          !/^qa-owner:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(payload.subject) ||
          typeof payload.email !== 'string' || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(payload.email) ||
          typeof options.email !== 'string' || options.email.trim().toLowerCase() !== payload.email ||
          (await client.query('SELECT 1 FROM flex_auth."user" WHERE id=$1 OR lower(email)=$2 LIMIT 1',
            [payload.subject, payload.email])).rowCount) {
        await client.query('ROLLBACK');
        return false;
      }
      email = payload.email;
      userId = payload.subject;
    } else {
      await client.query('ROLLBACK');
      return false;
    }
    const hash = await hashPassword(password);
    await client.query(
      'INSERT INTO flex_auth."user"(id,name,email,"emailVerified","twoFactorEnabled","updatedAt") VALUES ($1,$2,$2,true,false,now())',
      [userId, email]
    );
    await client.query(
      `INSERT INTO flex_auth.account(id,"accountId","providerId","userId",password,"updatedAt") VALUES ($1,$2,\'credential\',$2,$3,now())`,
      [randomUUID(), userId, hash]
    );
    await client.query('COMMIT');
    return true;
  } catch (error) {
    await client.query('ROLLBACK');
    throw error;
  } finally {
    client.release();
  }
}

// Self-service delivery retry for an already provisioned QA owner. No signup,
// identity creation, membership mutation, or disclosure of invitation status.
// Only the previously approved mailbox can receive the replacement link.
export async function resendOwnerInvite(database, emailInput, deliver, {allowOwnerInvite=false}={}) {
  const email=typeof emailInput==='string'?emailInput.trim().toLowerCase():'';
  if (!allowOwnerInvite || email.length>254 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return;
  const client=await database.connect();
  let delivery=null;
  try {
    await client.query('BEGIN');
    await client.query("SELECT pg_advisory_xact_lock(hashtext('flex:first-identity'))");
    // Short recovery window for a pending operator-issued invite, even if its
    // original 30-minute link expired. Max 3 deliveries, 2-minute cooldown.
    const pending=await client.query(
      `SELECT id,value FROM flex_auth.verification
       WHERE (CASE WHEN identifier ~ '^flex-owner:[a-f0-9]{64}$'
         THEN value::jsonb->>'email' END)=$1
         AND "createdAt">clock_timestamp()-interval '24 hours'
         AND "updatedAt"<clock_timestamp()-interval '2 minutes'
       LIMIT 2 FOR UPDATE`,[email]);
    if(pending.rowCount===1){
      const p=JSON.parse(pending.rows[0].value);
      const n=p.resendCount??0;
      if(p.kind==='QA_HOTEL_OWNER' && p.email===email &&
        typeof p.subject==='string' && /^qa-owner:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(p.subject) &&
        Number.isInteger(n) && n>=0 && n<3 &&
        !(await client.query('SELECT 1 FROM flex_auth."user" WHERE id=$1 OR lower(email)=$2 LIMIT 1',[p.subject,email])).rowCount){
        const token=randomBytes(32).toString('base64url');
        const digest=createHash('sha256').update(token).digest('hex');
        await client.query(`UPDATE flex_auth.verification SET identifier=$1,value=$2,
          "expiresAt"=clock_timestamp()+interval '30 minutes',"updatedAt"=clock_timestamp()
          WHERE id=$3`,['flex-owner:'+digest,JSON.stringify({...p,resendCount:n+1}),pending.rows[0].id]);
        delivery={email,token};
      }
    }
    await client.query('COMMIT');
  } catch(error) {
    await client.query('ROLLBACK');
    throw error;
  } finally {client.release();}
  // Commit before external mail: a delivered link can never race an uncommitted
  // record. A failed delivery consumes one attempt; a later retry rotates it.
  if(delivery) await deliver(delivery.email,delivery.token);
}
