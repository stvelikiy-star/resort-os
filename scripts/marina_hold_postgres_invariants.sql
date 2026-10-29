-- Disposable CI database only. Transaction rolls back synthetic hotel/room/hold.
BEGIN;
INSERT INTO properties (id,code,name,"updatedAt") VALUES
('11111111-1111-4111-8111-111111111111','HOLD_CI_A','HOLD CI A',now()),
('22222222-2222-4222-8222-222222222222','HOLD_CI_B','HOLD CI B',now());
INSERT INTO room_types (id,"propertyId",code,name,"capacityAdults","updatedAt") VALUES
('11111111-1111-4111-8111-111111111112','11111111-1111-4111-8111-111111111111','STANDARD','Standard',2,now()),
('22222222-2222-4222-8222-222222222223','22222222-2222-4222-8222-222222222222','STANDARD','Standard',2,now());
INSERT INTO rooms (id,"propertyId","roomTypeId",code,name,"updatedAt") VALUES
('11111111-1111-4111-8111-111111111113','11111111-1111-4111-8111-111111111111','11111111-1111-4111-8111-111111111112','HOLD01','Hold room A',now()),
('22222222-2222-4222-8222-222222222222','22222222-2222-4222-8222-222222222222','22222222-2222-4222-8222-222222222223','HOLD01','Hold room B',now());
INSERT INTO inventory_blocks (id,"roomId","blockType","startDate","endDate",active,reason,"updatedAt") VALUES
('11111111-1111-4111-8111-111111111114','11111111-1111-4111-8111-111111111113','MANUAL',current_date+1,current_date+3,true,'HOLD CI A',now()),
('22222222-2222-4222-8222-222222222224','22222222-2222-4222-8222-222222222222','MANUAL',current_date+1,current_date+3,true,'HOLD CI B',now());
INSERT INTO marina_reservation_holds (id,"propertyId","roomId","inventoryBlockId","createdBy","checkIn","checkOut","guestName","guestPhone") VALUES
('11111111-1111-4111-8111-111111111115','11111111-1111-4111-8111-111111111111','11111111-1111-4111-8111-111111111113','11111111-1111-4111-8111-111111111114','11111111-1111-4111-8111-111111111116',current_date+1,current_date+3,'Test A','+996700000001'),
('22222222-2222-4222-8222-222222222225','22222222-2222-4222-8222-222222222222','22222222-2222-4222-8222-222222222222','22222222-2222-4222-8222-222222222224','22222222-2222-4222-8222-222222222226',current_date+1,current_date+3,'Test B','+996700000002');
DO $hold$
DECLARE remaining int;
BEGIN
  SELECT count(*) INTO remaining FROM marina_reservation_holds WHERE "releasedAt" IS NULL AND "expiresAt" > now();
  IF remaining < 2 THEN RAISE EXCEPTION 'both active holds must exist'; END IF;
  IF EXISTS (SELECT 1 FROM marina_reservation_holds WHERE "propertyId"='11111111-1111-4111-8111-111111111111' AND "guestName"='Test B') THEN
    RAISE EXCEPTION 'cross-property hold leaked';
  END IF;
END
$hold$;
-- Conflict must be rejected by inventory exclusion constraint.
DO $hold$
BEGIN
  BEGIN
    INSERT INTO inventory_blocks (id,"roomId","blockType","startDate","endDate",active,"updatedAt")
    VALUES ('11111111-1111-4111-8111-111111111117','11111111-1111-4111-8111-111111111113','MANUAL',current_date+2,current_date+4,true,now());
    RAISE EXCEPTION 'overlapping hold was accepted';
  EXCEPTION WHEN exclusion_violation THEN NULL;
  END;
END
$hold$;
UPDATE marina_reservation_holds SET "releasedAt"=now() WHERE id='11111111-1111-4111-8111-111111111115';
UPDATE inventory_blocks SET active=false,"updatedAt"=now() WHERE id='11111111-1111-4111-8111-111111111114';
DO $hold$
BEGIN
  IF EXISTS (SELECT 1 FROM inventory_blocks WHERE id='11111111-1111-4111-8111-111111111114' AND active) THEN
    RAISE EXCEPTION 'released HOLD still occupies inventory';
  END IF;
END
$hold$;
ROLLBACK;
