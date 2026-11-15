"""Explicit kitchen inventory. Planning is not consumption; consumption is atomic and idempotent."""
from decimal import Decimal
from typing import Literal
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from .auth import require_roles, trusted_property_id
from .kitchen_recipes import read_recipe

router = APIRouter(prefix='/api/v1/kitchen/stock', tags=['kitchen-stock'])
read_access = require_roles('OWNER', 'MANAGER', 'COOK', 'STORE_STAFF')
manage_access = require_roles('OWNER', 'MANAGER')
receipt_access = require_roles('OWNER', 'MANAGER', 'STORE_STAFF', module_grant=False)
consume_access = require_roles('MANAGER', 'COOK')
loss_access = require_roles('OWNER', 'MANAGER', 'COOK', 'STORE_STAFF')


class ItemWrite(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    unit: Literal['KG','L','PCS']
    cost_per_unit_kgs: Decimal = Field(ge=0, max_digits=14, decimal_places=4)
    is_sample: bool = True
    @field_validator('name')
    @classmethod
    def normalize_name(cls, value: str):
        v = ' '.join(value.split())
        if not v: raise ValueError('Name required')
        return v

class ReceiptWrite(BaseModel):
    movement_id: uuid.UUID
    stock_item_id: uuid.UUID
    quantity: Decimal = Field(gt=0, max_digits=16, decimal_places=6)
    notes: str | None = Field(default=None, max_length=500)

class ConsumeWrite(BaseModel):
    production_target_id: uuid.UUID

class LossWrite(BaseModel):
    # Client-generated UUID allows safe retries after an uncertain network result.
    movement_id: uuid.UUID
    stock_item_id: uuid.UUID
    kind: Literal['WASTE', 'SPOILAGE']
    quantity: Decimal = Field(gt=0, max_digits=16, decimal_places=6)
    reason: str = Field(min_length=3, max_length=500)

    @field_validator('reason')
    @classmethod
    def canonical_reason(cls, value: str) -> str:
        normalized = ' '.join(value.split())
        if len(normalized) < 3:
            raise ValueError('A meaningful reason is required')
        return normalized


def enforce_loss_staff(user):
    if user['role'] not in {'OWNER', 'MANAGER', 'COOK', 'STORE_STAFF'}:
        raise HTTPException(403, detail={'code': 'KITCHEN_LOSS_ROLE_REQUIRED'})


async def snapshot(conn, pid):
    rows = await conn.fetch('''SELECT i.id,i.name,i.unit,i."costPerUnitKgs",i."isSample",
      COALESCE(SUM(CASE WHEN m.kind='RECEIPT' THEN m.quantity ELSE -m.quantity END),0) AS balance
      FROM kitchen_stock_items i LEFT JOIN kitchen_stock_movements m ON m."stockItemId"=i.id AND m."propertyId"=i."propertyId"
      WHERE i."propertyId"=$1 GROUP BY i.id ORDER BY i.name,i.unit''',pid)
    expense = await conn.fetchval('''SELECT COALESCE(SUM(quantity*"unitCostKgs"),0) FROM kitchen_stock_movements
      WHERE "propertyId"=$1 AND kind='PRODUCTION' ''',pid)
    return {'items':[{'id':str(r['id']),'name':r['name'],'unit':r['unit'],
          'cost_per_unit_kgs':str(r['costPerUnitKgs']),'is_sample':r['isSample'],
          'balance':str(r['balance'])} for r in rows],
          'production_cost_kgs':str(expense),'production_cost_is_payment':False,
          'inventory_deducted_only_on_explicit_consume':True,
          'new_loss_movement_id':str(uuid.uuid4()),
          'new_receipt_movement_id':str(uuid.uuid4())}

@router.get('')
async def read_stock(request: Request, user=Depends(read_access)):
    async with request.app.state.db.acquire() as conn:
        return await snapshot(conn,await trusted_property_id(conn,user))

@router.post('/items',status_code=201)
async def create_item(body: ItemWrite, request: Request, user=Depends(manage_access)):
    async with request.app.state.db.acquire() as conn:
        pid=await trusted_property_id(conn,user)
        row=await conn.fetchrow('''INSERT INTO kitchen_stock_items
        (id,"propertyId",name,"nameKey",unit,"costPerUnitKgs","isSample")
        VALUES ($1,$2,$3,$4,$5,$6,$7) ON CONFLICT ("propertyId","nameKey",unit) DO NOTHING RETURNING id''',
        uuid.uuid4(),pid,body.name,body.name.casefold(),body.unit,body.cost_per_unit_kgs,body.is_sample)
        if row is None: raise HTTPException(409,'Ingredient already exists for this property')
        return {'id':str(row['id']),'status':'CREATED'}

@router.post('/receipts',status_code=201)
async def create_receipt(body: ReceiptWrite, request: Request, user=Depends(receipt_access)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid=await trusted_property_id(conn,user)
            # Global operation lock, before item locking: the same key with
            # different items/properties must yield a conflict, never a PK 500.
            await conn.execute('SELECT pg_advisory_xact_lock(hashtextextended($1,0))',
                               'kitchen-direct-receipt:'+str(body.movement_id))
            prior=await conn.fetchrow('''SELECT m."propertyId",m."stockItemId",m.kind,
                m.quantity,m."unitCostKgs",m.notes,m."createdById",
                EXISTS(SELECT 1 FROM kitchen_procurement_receipts p WHERE p.id=m.id) AS procurement
                FROM kitchen_stock_movements m WHERE m.id=$1''',body.movement_id)
            if prior:
                if (prior['propertyId']!=pid or prior['stockItemId']!=body.stock_item_id
                    or prior['kind']!='RECEIPT' or prior['procurement']
                    or prior['quantity']!=body.quantity or prior['notes']!=body.notes
                    or str(prior['createdById'])!=str(user['id'])):
                    raise HTTPException(409,detail={'code':'KITCHEN_RECEIPT_IDEMPOTENCY_CONFLICT'})
                return {'id':str(body.movement_id),'stock_item_id':str(body.stock_item_id),
                        'quantity':str(prior['quantity']),'already_processed':True,
                        'unit_cost_kgs':str(prior['unitCostKgs']),'payment_created':False}
            item=await conn.fetchrow('''SELECT id,"costPerUnitKgs" FROM kitchen_stock_items
              WHERE id=$1 AND "propertyId"=$2 FOR UPDATE''',body.stock_item_id,pid)
            if not item: raise HTTPException(404,'Stock item not found')
            rid=body.movement_id
            inserted=await conn.fetchval('''INSERT INTO kitchen_stock_movements
              (id,"propertyId","stockItemId",kind,quantity,"unitCostKgs","createdById",notes)
              VALUES ($1,$2,$3,'RECEIPT',$4,$5,$6,$7)
              ON CONFLICT (id) DO NOTHING RETURNING id''',
              rid,pid,item['id'],body.quantity,item['costPerUnitKgs'],user['id'],body.notes)
            if not inserted:
                raise HTTPException(409,detail={'code':'KITCHEN_RECEIPT_IDEMPOTENCY_CONFLICT'})
            return {'id':str(rid),'stock_item_id':str(body.stock_item_id),
                    'quantity':str(body.quantity),'already_processed':False,
                    'unit_cost_kgs':str(item['costPerUnitKgs']),'payment_created':False}

@router.get('/losses')
async def list_losses(request: Request, user=Depends(loss_access)):
    enforce_loss_staff(user)
    async with request.app.state.db.acquire() as conn:
        pid = await trusted_property_id(conn, user)
        rows = await conn.fetch(
            '''SELECT m.id,m."stockItemId",i.name,i.unit,i."isSample",
                      m.kind,m.quantity,m."unitCostKgs",m.notes,m."createdById",m."createdAt"
               FROM kitchen_stock_movements m
               JOIN kitchen_stock_items i ON i.id=m."stockItemId" AND i."propertyId"=m."propertyId"
               WHERE m."propertyId"=$1 AND m.kind IN ('WASTE','SPOILAGE')
               ORDER BY m."createdAt" DESC,m.id DESC LIMIT 100''', pid)
    return {'items': [
        {'id':str(row['id']), 'stock_item_id':str(row['stockItemId']),
         'stock_name':row['name'], 'unit':row['unit'], 'is_sample':row['isSample'],
         'kind':row['kind'], 'quantity':str(row['quantity']),
         'unit_cost_kgs':str(row['unitCostKgs']),
         'cost_kgs':str(row['quantity']*row['unitCostKgs']),
         'reason':row['notes'], 'created_by_id':str(row['createdById']) if row['createdById'] else None,
         'created_at':row['createdAt'].isoformat()}
        for row in rows
    ], 'financial_truth':'INVENTORY_LOSS_NOT_PAYMENT'}


@router.post('/losses',status_code=201)
async def create_loss(body: LossWrite, request: Request, user=Depends(loss_access)):
    enforce_loss_staff(user)
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid=await trusted_property_id(conn,user)
            item=await conn.fetchrow(
                '''SELECT id,"costPerUnitKgs","isSample" FROM kitchen_stock_items
                   WHERE id=$1 AND "propertyId"=$2 FOR UPDATE''',
                body.stock_item_id,pid)
            if not item:
                raise HTTPException(404,detail={'code':'KITCHEN_STOCK_ITEM_NOT_FOUND'})
            # Item lock serializes replay checks and independent concurrent deductions.
            prior=await conn.fetchrow(
                '''SELECT "propertyId","stockItemId",kind,quantity,"unitCostKgs",notes
                   FROM kitchen_stock_movements WHERE id=$1''',body.movement_id)
            if prior:
                if (prior['propertyId'] != pid or prior['stockItemId'] != body.stock_item_id
                    or prior['kind'] != body.kind or prior['quantity'] != body.quantity
                    or prior['notes'] != body.reason):
                    raise HTTPException(409,detail={'code':'KITCHEN_LOSS_IDEMPOTENCY_CONFLICT'})
                return {'id':str(body.movement_id), 'already_processed':True,
                        'quantity':str(prior['quantity']),
                        'cost_kgs':str(prior['quantity']*prior['unitCostKgs']),
                        'payment_created':False}
            balance=await conn.fetchval(
                '''SELECT COALESCE(SUM(CASE WHEN kind='RECEIPT' THEN quantity ELSE -quantity END),0)
                   FROM kitchen_stock_movements
                   WHERE "propertyId"=$1 AND "stockItemId"=$2''',pid,item['id'])
            if balance < body.quantity:
                raise HTTPException(409,detail={'code':'KITCHEN_LOSS_INSUFFICIENT_STOCK'})
            await conn.execute(
                '''INSERT INTO kitchen_stock_movements
                   (id,"propertyId","stockItemId",kind,quantity,"unitCostKgs",
                    "createdById",notes)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8)''',
                body.movement_id,pid,item['id'],body.kind,body.quantity,
                item['costPerUnitKgs'],uuid.UUID(user['id']),body.reason)
            return {'id':str(body.movement_id),'already_processed':False,
                    'quantity':str(body.quantity),
                    'cost_kgs':str(body.quantity*item['costPerUnitKgs']),
                    'payment_created':False}


@router.post('/consume',status_code=200)
async def consume_production(body: ConsumeWrite, request: Request, user=Depends(consume_access)):
    async with request.app.state.db.acquire() as conn:
        async with conn.transaction():
            pid=await trusted_property_id(conn,user)
            # Serialize target processing, even concurrent users on separate API replicas.
            target=await conn.fetchrow('''SELECT t.id,t."preparedQuantity",m.recipe
              FROM kitchen_production_targets t JOIN kitchen_menu_items m
              ON m.id=t."menuItemId" AND m."propertyId"=t."propertyId"
              WHERE t.id=$1 AND t."propertyId"=$2 FOR UPDATE OF t''',body.production_target_id,pid)
            if not target: raise HTTPException(404,'Production target not found')
            recipe=read_recipe(target['recipe'])
            if not recipe or recipe['status']!='APPROVED':
                raise HTTPException(409,'Approved recipe required')
            if recipe['is_sample']:
                # Sample recipes may only debit sample ingredient stock.
                sample_only=True
            else: sample_only=False
            progress=await conn.fetchrow('''SELECT "deductedPortions" FROM kitchen_stock_production_progress
              WHERE "productionTargetId"=$1 AND "propertyId"=$2 FOR UPDATE''',target['id'],pid)
            previous=progress['deductedPortions'] if progress else 0
            prepared=target['preparedQuantity']
            if prepared<previous: raise HTTPException(409,'Prepared portions decreased since last deduction')
            delta=prepared-previous
            if delta==0:return {'consumed_portions':0,'already_processed':True,'cost_kgs':'0','payment_created':False}
            requirements={}
            for ing in recipe['ingredients']:
                key=(ing['name'].casefold(),ing['unit'])
                requirements[key]=Decimal(ing['quantity_per_portion'])*delta
            # Resolve and lock in deterministic order. Missing/insufficient items abort all deductions.
            total=Decimal(0)
            for (name,unit),quantity in sorted(requirements.items()):
                item=await conn.fetchrow('''SELECT id,"costPerUnitKgs","isSample" FROM kitchen_stock_items
                  WHERE "propertyId"=$1 AND "nameKey"=$2 AND unit=$3 FOR UPDATE''',pid,name,unit)
                if not item:raise HTTPException(409,f'Missing stock item: {name} ({unit})')
                if sample_only != item['isSample']:
                    raise HTTPException(409,'Sample and real inventory cannot be mixed')
                balance=await conn.fetchval('''SELECT COALESCE(SUM(CASE WHEN kind='RECEIPT' THEN quantity ELSE -quantity END),0)
                  FROM kitchen_stock_movements WHERE "propertyId"=$1 AND "stockItemId"=$2''',pid,item['id'])
                if balance<quantity:raise HTTPException(409,f'Insufficient stock: {name}')
                await conn.execute('''INSERT INTO kitchen_stock_movements
                  (id,"propertyId","stockItemId",kind,quantity,"unitCostKgs","productionTargetId",
                   "preparedFrom","preparedTo","createdById",notes)
                  VALUES ($1,$2,$3,'PRODUCTION',$4,$5,$6,$7,$8,$9,'Explicit production consumption')''',
                  uuid.uuid4(),pid,item['id'],quantity,item['costPerUnitKgs'],target['id'],previous,prepared,user['id'])
                total+=quantity*item['costPerUnitKgs']
            await conn.execute('''INSERT INTO kitchen_stock_production_progress
              ("propertyId","productionTargetId","deductedPortions") VALUES ($1,$2,$3)
              ON CONFLICT ("productionTargetId") DO UPDATE SET "deductedPortions"=EXCLUDED."deductedPortions", "updatedAt"=now()''',
              pid,target['id'],prepared)
            return {'consumed_portions':delta,'already_processed':False,
                    'cost_kgs':str(total),'payment_created':False}
