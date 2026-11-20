\set ON_ERROR_STOP on
BEGIN;
DO $audit$
DECLARE
  pid uuid;
  item_id uuid := gen_random_uuid();
  other_pid uuid := gen_random_uuid();
  other_tid uuid := gen_random_uuid();
  other_item uuid := gen_random_uuid();
  target_id uuid;
  planned integer;
  prepared integer;
  rejected boolean := false;
BEGIN
  SELECT id INTO STRICT pid FROM properties WHERE code='MARINA_FULL_CI';
  INSERT INTO kitchen_menu_items
    (id,"propertyId",code,category,"nameRu","nameKg","nameKz","nameEn",
     "priceKgs","isActive","isDraft","sortOrder")
    VALUES(item_id,pid,'CHEF_QA_DISH','MAIN','Тестовое блюдо','Сыноо тамак',
           'Сынақ тағам','Test dish',0,true,false,999);

  INSERT INTO kitchen_production_targets
    (id,"propertyId","menuItemId","serviceDate","mealType",
     "plannedQuantity","preparedQuantity",notes)
  VALUES(gen_random_uuid(),pid,item_id,current_date,'LUNCH',20,8,'QA_ROLLBACK_ONLY')
  RETURNING id INTO target_id;
  SELECT "plannedQuantity","preparedQuantity" INTO planned,prepared
    FROM kitchen_production_targets WHERE id=target_id;
  IF planned<>20 OR prepared<>8 OR planned-prepared<>12 THEN
    RAISE EXCEPTION 'FAIL planned/prepared/remaining';
  END IF;
  RAISE NOTICE 'PASS 1/10 production target stores 20 planned, 8 prepared, 12 remaining';

  INSERT INTO kitchen_production_targets
    (id,"propertyId","menuItemId","serviceDate","mealType",
     "plannedQuantity","preparedQuantity")
  VALUES(gen_random_uuid(),pid,item_id,current_date,'LUNCH',22,9)
    ON CONFLICT ("propertyId","menuItemId","serviceDate","mealType")
    DO UPDATE SET "plannedQuantity"=EXCLUDED."plannedQuantity",
                  "preparedQuantity"=EXCLUDED."preparedQuantity";
  IF (SELECT count(*) FROM kitchen_production_targets WHERE "propertyId"=pid)<>1
    THEN RAISE EXCEPTION 'FAIL unique target'; END IF;
  RAISE NOTICE 'PASS 2/10 idempotent date/dish/meal uniqueness';

  BEGIN
    INSERT INTO kitchen_production_targets
      (id,"propertyId","menuItemId","serviceDate","mealType",
       "plannedQuantity","preparedQuantity")
    VALUES(gen_random_uuid(),pid,item_id,current_date,'BREAKFAST',5,6);
  EXCEPTION WHEN check_violation THEN rejected:=true;
  END;
  IF NOT rejected THEN RAISE EXCEPTION 'FAIL prepared exceeds planned'; END IF;
  RAISE NOTICE 'PASS 3/10 prepared count cannot exceed planned';
  rejected:=false;

  BEGIN
    INSERT INTO kitchen_production_targets
      (id,"propertyId","menuItemId","serviceDate","mealType",
       "plannedQuantity","preparedQuantity")
    VALUES(gen_random_uuid(),pid,item_id,current_date,'BREAKFAST',-1,0);
  EXCEPTION WHEN check_violation THEN rejected:=true;
  END;
  IF NOT rejected THEN RAISE EXCEPTION 'FAIL negative target allowed'; END IF;
  RAISE NOTICE 'PASS 4/10 negative quantity rejected';
  rejected:=false;

  BEGIN
    INSERT INTO kitchen_production_targets
      (id,"propertyId","menuItemId","serviceDate","mealType",
       "plannedQuantity","preparedQuantity")
    VALUES(gen_random_uuid(),pid,item_id,current_date,'INVALID',1,0);
  EXCEPTION WHEN check_violation THEN rejected:=true;
  END;
  IF NOT rejected THEN RAISE EXCEPTION 'FAIL invalid meal accepted'; END IF;
  RAISE NOTICE 'PASS 5/10 invalid meal type rejected';
  rejected:=false;

  BEGIN
    INSERT INTO kitchen_production_targets
      (id,"propertyId","menuItemId","serviceDate","mealType",
       "plannedQuantity","preparedQuantity",notes)
    VALUES(gen_random_uuid(),pid,item_id,current_date,'DINNER',1,0,repeat('N',501));
  EXCEPTION WHEN check_violation THEN rejected:=true;
  END;
  IF NOT rejected THEN RAISE EXCEPTION 'FAIL overlong note'; END IF;
  RAISE NOTICE 'PASS 6/10 notes length constrained';
  rejected:=false;

  INSERT INTO tenants(id,code,name,status,"createdAt","updatedAt")
    VALUES(other_tid,'qa_tenant_other','QA OTHER','ACTIVE',now(),now());
  INSERT INTO properties(id,"tenantId",code,name,timezone,currency,"createdAt","updatedAt")
    VALUES(other_pid,other_tid,'QA_OTHER','QA OTHER','Asia/Bishkek','KGS',now(),now());
  INSERT INTO kitchen_menu_items
    (id,"propertyId",code,category,"nameRu","nameKg","nameKz","nameEn",
     "priceKgs","isActive","isDraft","sortOrder")
  VALUES(other_item,other_pid,'QA_OTHER_DISH','MAIN','QA','QA','QA','QA',0,true,false,0);
  BEGIN
    INSERT INTO kitchen_production_targets
      (id,"propertyId","menuItemId","serviceDate","mealType",
       "plannedQuantity","preparedQuantity")
    VALUES(gen_random_uuid(),pid,other_item,current_date,'LUNCH',1,0);
  EXCEPTION WHEN foreign_key_violation THEN rejected:=true;
  END;
  IF NOT rejected THEN RAISE EXCEPTION 'FAIL foreign item allowed'; END IF;
  RAISE NOTICE 'PASS 7/10 cross-property dish reference forbidden';
  rejected:=false;

  BEGIN
    INSERT INTO kitchen_production_targets
      (id,"propertyId","menuItemId","serviceDate","mealType",
       "plannedQuantity","preparedQuantity")
    VALUES(gen_random_uuid(),other_pid,item_id,current_date,'LUNCH',1,0);
  EXCEPTION WHEN foreign_key_violation THEN rejected:=true;
  END;
  IF NOT rejected THEN RAISE EXCEPTION 'FAIL foreign property allowed'; END IF;
  RAISE NOTICE 'PASS 8/10 opposite cross-property reference forbidden';

  IF (SELECT count(*) FROM kitchen_production_targets WHERE "propertyId"=pid)<>1
    THEN RAISE EXCEPTION 'FAIL target scope'; END IF;
  RAISE NOTICE 'PASS 9/10 scoped query excludes other property';

  IF (SELECT count(*) FROM _prisma_migrations WHERE finished_at IS NOT NULL)<>40
    THEN RAISE EXCEPTION 'FAIL migration ledger count'; END IF;
  RAISE NOTICE 'PASS 10/10 exact 40 migrated schema accepted';
END $audit$;
ROLLBACK;
SELECT
  (SELECT count(*) FROM kitchen_production_targets) AS targets_after_rollback,
  (SELECT count(*) FROM kitchen_menu_items) AS menus_after_rollback,
  (SELECT count(*) FROM properties) AS hotels_after_rollback;
