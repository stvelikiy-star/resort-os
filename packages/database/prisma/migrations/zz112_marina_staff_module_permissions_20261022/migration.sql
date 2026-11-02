ALTER TABLE staff_users
  ADD COLUMN "modulePermissions" jsonb;

ALTER TABLE staff_users
  ADD CONSTRAINT staff_users_module_permissions_array_check
  CHECK ("modulePermissions" IS NULL OR jsonb_typeof("modulePermissions") = 'array');
