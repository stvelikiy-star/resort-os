#!/usr/bin/env python3
"""Source and isolated execution tests for safe booking acquiring preflight.

No provider credentials, payment events or real database required.
"""
import ast
import asyncio
from pathlib import Path
import uuid
import unittest

ROOT=Path(__file__).resolve().parents[1]
SRC=(ROOT/"services/api/app/reservation_payments.py").read_text()
UI=(ROOT/"apps/admin/components/ReservationFolioPanel.tsx").read_text()
tree=ast.parse(SRC)
functions={n.name:n for n in tree.body if isinstance(n,ast.AsyncFunctionDef)}

class HttpException(Exception):
    def __init__(self,status_code,detail):
        super().__init__(str(detail))
        self.status_code=status_code

class Connection:
    def __init__(self,visible,paid,total=9000,status="HELD"):
        self.visible=visible
        self.paid=paid
        self.total=total
        self.status=status
        self.queries=[]
    async def fetchval(self,q,*params):
        self.queries.append((q,params))
        if "properties" in q:return self.property_id
        raise AssertionError("unexpected query")
    async def fetchrow(self,q,*params):
        self.queries.append((q,params))
        if not self.visible:return None
        return {"id":params[0],"bookingNumber":"DEMO-101","status":self.status,"totalKgs":self.total}
    property_id=uuid.uuid4()

class Pool:
    def __init__(self,conn):self.conn=conn
    def acquire(self):return self
    async def __aenter__(self):return self.conn
    async def __aexit__(self,*args):pass

async def totals(conn, rid):
    return {"total_kgs":conn.total,"paid_kgs":conn.paid,"remaining_kgs":max(conn.total-conn.paid,0),"overpaid_kgs":max(conn.paid-conn.total,0)}

namespace={"uuid":uuid,"Any":object,"HTTPException":HttpException,
"Request":object,"Depends":lambda x:None,"payment_access":object,"_totals":totals}
fn=functions["reservation_acquiring_readiness"]
fn.decorator_list=[]
exec(compile(ast.Module(body=[fn],type_ignores=[]),str(ROOT), "exec"),namespace)
readiness=namespace["reservation_acquiring_readiness"]

class TestAcquiringReadiness(unittest.TestCase):
    def invoke(self,conn,code="hotel01"):
        return asyncio.run(readiness(uuid.uuid4(),type("Request",(),{"app":type("App",(),{"state":type("State",(),{"db":Pool(conn)})()})()})(),{"property_code":code}))
    def test_eligible_outstanding_but_no_bank_link(self):
        conn=Connection(True,4000)
        result=self.invoke(conn)
        self.assertEqual(result["remaining_kgs"],5000)
        self.assertEqual(result["remaining_tyiyn"],500000)
        self.assertTrue(result["payment_collection_eligible"])
        self.assertIsNone(result["payment_link"])
        self.assertFalse(result["provider_connected"])
        self.assertEqual(result["acquiring_status"],"NOT_CONFIGURED")
        self.assertIn('"propertyId"=$2',str(conn.queries))
    def test_cancelled_and_fully_paid_block_collection(self):
        self.assertFalse(self.invoke(Connection(True,0,status="CANCELLED"))["payment_collection_eligible"])
        self.assertFalse(self.invoke(Connection(True,9000))["payment_collection_eligible"])
    def test_foreign_reservation_returns_not_found(self):
        with self.assertRaises(HttpException) as caught:self.invoke(Connection(False,0))
        self.assertEqual(caught.exception.status_code,404)
    def test_no_side_effects_and_ui_is_honest(self):
        body=ast.get_source_segment(SRC,functions["reservation_acquiring_readiness"])
        self.assertNotIn("conn.execute(",body)
        self.assertIn('canManagePayments &&',UI)
        self.assertIn("Банковский эквайринг пока не подключён",UI)
        self.assertIn("acquiring-readiness",UI)

if __name__=="__main__":unittest.main()
