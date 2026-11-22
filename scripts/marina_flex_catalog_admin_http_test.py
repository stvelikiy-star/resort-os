#!/usr/bin/env python3
"""Real PostgreSQL16 + Ed25519/MFA HTTP checks against isolated FLEX catalog admin.

Runs only in GitHub disposable flex_ci database. No operational PMS or payment
API ever receives a request. Test JWTs and keys exist in process memory only.
"""
from __future__ import annotations
import asyncio
import json
import os
import sys
import time
import unittest
import uuid
from datetime import datetime, timedelta, timezone, date
from pathlib import Path

import asyncpg
import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"services"/"api"))
from app.flex_catalog_admin import app  # noqa: E402

HOTEL_A="00000000-0000-0000-0000-00000000000a"
HOTEL_B="00000000-0000-0000-0000-00000000000b"


class ActualDatabaseAdminHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.environ.get("FLEX_ENVIRONMENT")!="qa" or os.environ.get(
            "FLEX_ENABLE_QA_CATALOG_DRAFTS"
        )!="true" or not os.environ.get("FLEX_DATABASE_URL"):
            raise RuntimeError("Disposable isolated FLEX QA preflight required")
        cls.private=Ed25519PrivateKey.generate()
        public=cls.private.public_key().public_bytes(
            Encoding.PEM,PublicFormat.SubjectPublicKeyInfo
        ).decode()
        cls.previous={name:os.environ.get(name) for name in (
            "FLEX_AUTH_PUBLIC_KEYS_JSON","FLEX_AUTH_ISSUER","FLEX_AUTH_AUDIENCE"
        )}
        os.environ.update({
            "FLEX_AUTH_PUBLIC_KEYS_JSON":json.dumps({"ci-admin":public}),
            "FLEX_AUTH_ISSUER":"marina-flex-catalog-ci",
            "FLEX_AUTH_AUDIENCE":"marina-flex-catalog-ci-audience",
        })
        cls.ctx=TestClient(app)
        cls.client=cls.ctx.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.ctx.__exit__(None,None,None)
        for name,prev in cls.previous.items():
            if prev is None:os.environ.pop(name,None)
            else:os.environ[name]=prev

    @classmethod
    def auth(cls,who="administrator",mfa=True,inject=None):
        now=int(time.time())
        token={
            "sub":who,"iss":"marina-flex-catalog-ci",
            "aud":"marina-flex-catalog-ci-audience",
            "iat":now,"nbf":now-1,"exp":now+600,
            "jti":str(uuid.uuid4()),"amr":["mfa"] if mfa else ["pwd"]
        }
        if inject:token.update(inject)
        return {"Authorization":"Bearer "+jwt.encode(
            token,cls.private,algorithm="EdDSA",headers={"kid":"ci-admin"}
        )}

    def get(self,path,who="administrator",mfa=True):
        return self.client.get(path,headers=self.auth(who,mfa))

    def post(self,path,payload,who="administrator",mfa=True):
        return self.client.post(path,json=payload,headers=self.auth(who,mfa))

    def test_01_explicit_super_admin_mfa_only(self):
        base={"sku":"EXTRA_QA_CI","title":"QA add-on 1","capability_key":"qa.extra.feature"}
        self.assertEqual(self.client.post("/v1/platform/catalog/skus",json=base).status_code,401)
        for who,mfa in [("owner-a",True),("owner-b",True),("investor-1",True),
                        ("sales-1",True),("administrator",False),("unknown",True)]:
            with self.subTest(role=who,mfa=mfa):
                r=self.post("/v1/platform/catalog/skus",base,who,mfa)
                self.assertIn(r.status_code,{403},r.text)
        self.assertEqual(self.get("/v1/platform/catalog",who="owner-a").status_code,403)
        self.assertEqual(self.get("/v1/platform/subscription-drafts",mfa=False).status_code,403)

    def test_02_planned_sku_append_and_price_version(self):
        sku={"sku":"EXTRA_QA_CI","title":"QA add-on 1","capability_key":"qa.extra.feature"}
        made=self.post("/v1/platform/catalog/skus",sku)
        self.assertEqual(made.status_code,201,made.text)
        self.assertEqual(made.json()["status"],"PLANNED")
        self.assertEqual(made.json()["entitlement_changed"],False)
        self.assertEqual(self.post("/v1/platform/catalog/skus",sku).status_code,409)
        self.assertEqual(self.post("/v1/platform/catalog/skus",{**sku,"is_core":True}).status_code,422)
        catalog=self.get("/v1/platform/catalog")
        self.assertEqual(catalog.status_code,200,catalog.text)
        planned=[r for r in catalog.json() if r["sku"]=="EXTRA_QA_CI"]
        self.assertEqual(len(planned),1)
        self.assertEqual(planned[0]["status"],"PLANNED")

        t1=datetime.now(timezone.utc)+timedelta(days=3)
        t2=t1+timedelta(days=2)
        def price(when,amount):
            return {"monthly_price":amount,"currency":"KGS","valid_from":when.isoformat()}
        path="/v1/platform/catalog/skus/EXTRA_QA_CI/prices"
        version1=self.post(path,price(t1,"1200.00"))
        self.assertEqual(version1.status_code,201,version1.text)
        self.assertEqual(version1.json()["version"],1)
        self.assertFalse(version1.json()["payment_collected"])
        version2=self.post(path,price(t2,"1300.00"))
        self.assertEqual(version2.status_code,201,version2.text)
        self.assertEqual(version2.json()["version"],2)
        self.assertEqual(self.post(path,price(t1+timedelta(hours=1),"999.00")).status_code,409)
        history=self.get("/v1/platform/catalog/skus/EXTRA_QA_CI/versions")
        self.assertEqual(history.status_code,200,history.text)
        self.assertEqual([v["version"] for v in history.json()["versions"]],[2,1])
        self.assertEqual(history.json()["versions"][1]["monthly_price"],"1200.00")
        self.assertEqual(self.post(path,{**price(t2+timedelta(days=2),"1"),"paid":True}).status_code,422)
        self.assertEqual(self.get("/v1/platform/catalog/skus/EXTRA_QA_CI/versions","owner-a").status_code,403)

    def test_03_draft_configuration_is_not_subscription(self):
        start=date.today()+timedelta(days=4)
        end=start+timedelta(days=30)
        path="/v1/platform/subscription-drafts"
        payload={
            "hotel_id":HOTEL_A,
            "title":"QA seasonal configuration",
            "period_start":start.isoformat(),"period_end":end.isoformat(),
            "skus":["AI_ASSISTANT"],
        }
        self.assertEqual(self.post(path,payload,"owner-a").status_code,403)
        self.assertEqual(self.post(path,{**payload,"enforcement":"ENFORCE"}).status_code,422)
        created=self.post(path,payload)
        self.assertEqual(created.status_code,201,created.text)
        result=created.json()
        self.assertEqual(result["state"],"DRAFT")
        self.assertEqual(result["enforcement"],"OFF")
        self.assertEqual(result["subscription_activated"],False)
        self.assertEqual(result["payments_enabled"],False)
        self.assertEqual(result["proposed_monthly_total"],"4000.00")
        self.assertEqual(len(result["items"]),1)
        self.assertEqual(result["items"][0]["sku"],"AI_ASSISTANT")
        self.assertEqual(self.post(path,{**payload,"skus":["UNFINISHED_MODULE"]}).status_code,422)
        self.assertEqual(self.post(path,{**payload,"skus":["AI_ASSISTANT","AI_ASSISTANT"]}).status_code,422)
        for hotel_id,length in [(HOTEL_A,1),(HOTEL_B,0)]:
            rows=self.get(path+"?hotel_id="+hotel_id)
            self.assertEqual(rows.status_code,200,rows.text)
            self.assertEqual(len(rows.json()),length)
            if length:
                self.assertEqual(rows.json()[0]["hotel_id"],HOTEL_A)
                self.assertEqual(rows.json()[0]["enforcement"],"OFF")
        self.assertEqual(self.get(path+"?hotel_id="+HOTEL_A,"owner-b").status_code,403)
        # Assert no effect on operational commercial state using disposable DB OWNER.
        async def verify_tables():
            con=await asyncpg.connect(os.environ["FLEX_TEST_DB_OWNER_URL"])
            try:
                active=await con.fetch(
                    "SELECT hotel_id,status,enforcement FROM flex_subscriptions ORDER BY hotel_id"
                )
                self.assertEqual(len(active),2)
                self.assertEqual([r["enforcement"] for r in active],["OFF","OFF"])
                self.assertEqual(await con.fetchval(
                    "SELECT count(*) FROM flex_confirmed_payments"
                ),0)
                self.assertEqual(await con.fetchval(
                    "SELECT count(*) FROM flex_payment_intents"
                ),0)
                self.assertEqual(await con.fetchval(
                    "SELECT count(*) FROM flex_subscription_configuration_drafts"
                ),1)
            finally:await con.close()
        asyncio.run(verify_tables())


if __name__=="__main__":
    unittest.main(verbosity=2)
