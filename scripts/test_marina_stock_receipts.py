"""Request contract tests; concurrency and persistence are covered separately in PostgreSQL CI."""
import sys
import unittest
import uuid
from contextlib import asynccontextmanager
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'services/api'))
from app import auth,kitchen_stock
PID,ITEM,USER,KEY=[uuid.uuid4() for _ in range(4)]
class Connection:
    def __init__(self):self.rows={};self.cost=Decimal('2.5');self.calls=[]
    @asynccontextmanager
    async def transaction(self):yield
    async def execute(self,query,*args):self.calls.append(query)
    async def fetchrow(self,query,*args):
        if 'FROM kitchen_stock_movements m' in query:return self.rows.get(args[0])
        return {'id':ITEM,'costPerUnitKgs':self.cost} if args[0]==ITEM else None
    async def fetchval(self,query,*args):
        rid,pid,item,quantity,cost,actor,notes=args
        if rid in self.rows:return None
        self.rows[rid]={'propertyId':pid,'stockItemId':item,'kind':'RECEIPT','quantity':quantity,'unitCostKgs':cost,'createdById':actor,'notes':notes,'procurement':False}
        return rid
class Pool:
    def __init__(self,conn):self.conn=conn
    @asynccontextmanager
    async def acquire(self):yield self.conn
class ReceiptContracts(unittest.TestCase):
    def setUp(self):
        self.conn=Connection();self.user={'id':str(USER),'role':'STORE_STAFF','module_permissions':['DINING']}
        app=FastAPI();app.include_router(kitchen_stock.router);app.state.db=Pool(self.conn)
        app.dependency_overrides[auth.current_user]=lambda:self.user
        self.client=TestClient(app)
        self.pid=patch.object(kitchen_stock,'trusted_property_id',return_value=PID);self.pid.start();self.addCleanup(self.pid.stop)
        self.payload={'movement_id':str(KEY),'stock_item_id':str(ITEM),'quantity':'10','notes':'Receipt'}
    def post(self,**changes):return self.client.post('/api/v1/kitchen/stock/receipts',json={**self.payload,**changes})
    def test_replay_returns_original_cost_and_one_movement(self):
        first=self.post();self.assertEqual(first.status_code,201,first.text);self.assertFalse(first.json()['already_processed'])
        self.conn.cost=Decimal(99)
        again=self.post(quantity='10.000000');self.assertEqual(again.status_code,201);self.assertTrue(again.json()['already_processed'])
        self.assertEqual(Decimal(again.json()['unit_cost_kgs']),Decimal('2.5'));self.assertEqual(len(self.conn.rows),1)
        self.assertTrue(any('pg_advisory_xact_lock' in q for q in self.conn.calls))
    def test_payload_actor_or_procurement_collision_returns_conflict(self):
        self.assertEqual(self.post().status_code,201)
        for change in ({'quantity':'11'},{'notes':'Other'},{'stock_item_id':str(uuid.uuid4())}):
            self.assertEqual(self.post(**change).status_code,409)
        self.conn.rows[KEY]['createdById']=str(uuid.uuid4());self.assertEqual(self.post().status_code,409)
        self.conn.rows[KEY]['createdById']=str(USER);self.conn.rows[KEY]['procurement']=True;self.assertEqual(self.post().status_code,409)
    def test_missing_id_and_invalid_quantity_never_write(self):
        p={k:v for k,v in self.payload.items() if k!='movement_id'}
        self.assertEqual(self.client.post('/api/v1/kitchen/stock/receipts',json=p).status_code,422)
        self.assertEqual(self.post(quantity='0').status_code,422);self.assertFalse(self.conn.rows)
    def test_custom_dining_grant_does_not_promote_cook(self):
        self.user.update(role='COOK',module_permissions_custom=True)
        self.assertEqual(self.post().status_code,403);self.assertFalse(self.conn.rows)
if __name__=='__main__':unittest.main()
