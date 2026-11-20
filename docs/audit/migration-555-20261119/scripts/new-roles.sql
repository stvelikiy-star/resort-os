-- Only run after before/after snapshots on the disposable clone.
INSERT INTO staff_users(id,"propertyId",username,"displayName","passwordHash",role,"updatedAt")
SELECT gen_random_uuid(),u."propertyId",lower(r),r,u."passwordHash",r::"StaffRole",now()
FROM staff_users u CROSS JOIN unnest(ARRAY['AGENT','COOK','WAITER']) r
WHERE u.role='OWNER' AND u."propertyId"=(SELECT id FROM properties WHERE code='ALPHA');
