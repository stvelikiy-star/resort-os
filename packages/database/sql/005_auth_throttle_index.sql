-- Login throttling reuses the append-only audit log as durable state.
-- Keep the lookup bounded as audit history grows; no raw username/IP data is stored.
CREATE INDEX IF NOT EXISTS audit_logs_auth_throttle_lookup_idx
ON audit_logs ("propertyId", "resourceId", action, "createdAt")
WHERE resource = 'AuthThrottle';
