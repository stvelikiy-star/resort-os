import {createHash, randomUUID} from 'node:crypto';

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
