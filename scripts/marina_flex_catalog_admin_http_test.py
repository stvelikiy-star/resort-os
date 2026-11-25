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
from decimal import Decimal
from datetime import datetime, timedelta, timezone, date, time as clock_time
from zoneinfo import ZoneInfo
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

    def test_01a_commercial_policy_is_admin_scoped_and_persisted(self):
        path = "/v1/platform/commercial-policy"
        self.assertEqual(self.get(path, who="owner-a").status_code, 403)
        response = self.get(path)
        self.assertEqual(response.status_code, 200, response.text)
        approved = json.loads((Path(__file__).resolve().parents[1] / "docs/flex/commercial-policy-20261124.json").read_text())
        self.assertEqual(response.json()["version"], 1)
        self.assertEqual(response.json()["policy"], approved)

    def test_01b_initial_base_launch_offer(self):
        async def seed():
            con=await asyncpg.connect(os.environ["FLEX_TEST_DB_OWNER_URL"])
            try:
                self.assertEqual(await con.fetchval("SELECT current_database()"),"flex_ci")
                hotel=uuid.uuid4()
                await con.execute("INSERT INTO flex_hotels(id,display_name) VALUES($1,$2)",hotel,"Synthetic initial BASE")
                return str(hotel)
            finally: await con.close()
        hotel=asyncio.run(seed())
        path="/v1/platform/launch-offer"
        self.assertEqual(self.get(path,who="owner-a").status_code,403)
        before=self.get(path)
        self.assertEqual(before.status_code,200,before.text)
        self.assertEqual(before.json()["available"],50)
        made=self.post("/v1/platform/tariff-packages",{
            "hotel_id":hotel,"package_kind":"BASE","title":"Initial BASE launch",
            "period_start":datetime.now(ZoneInfo("Asia/Bishkek")).date().isoformat(),
            "skus":[],"commercial_policy_version":1,"discount_pct":"0",
            "trial_days":5,"custom_monthly_price":None,"term_months":12,
            "standard_term_discount":False,"include_implementation":True,"launch_offer":True})
        self.assertEqual(made.status_code,201,made.text)
        row=made.json()
        self.assertEqual(Decimal(row["subscription_term_total"]),Decimal("36000"))
        self.assertEqual(Decimal(row["implementation_total"]),Decimal("25000"))
        after=self.get(path)
        self.assertEqual(after.status_code,200,after.text)
        data=after.json()
        self.assertEqual((data["capacity"],data["reserved"],data["available"]),(50,1,49))
        self.assertEqual(str(data["reservations"][0]["hotel_id"]),hotel)
        self.assertEqual(str(data["reservations"][0]["offer_id"]),row["id"])
        self.assertEqual(Decimal(str(data["reservations"][0]["subscription_term_total"])),Decimal("36000"))
        self.assertFalse(data["payments_enabled"])

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
        start=datetime.now(ZoneInfo('Asia/Bishkek')).date()+timedelta(days=4)
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
        # A new version starts at 20:00 on the first contract day. It must NOT
        # replace the version in force at 00:00 Asia/Bishkek on that same day.
        in_day=datetime.combine(start,clock_time(hour=20),ZoneInfo('Asia/Bishkek')).astimezone(timezone.utc)
        scheduled=self.post('/v1/platform/catalog/skus/AI_ASSISTANT/prices',{
            'monthly_price':'15000.00','currency':'KGS','valid_from':in_day.isoformat()
        })
        self.assertEqual(scheduled.status_code,201,scheduled.text)
        self.assertEqual(scheduled.json()['version'],2)
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


    def test_04_tariff_package_versions_are_immutable_off_only(self):
        path="/v1/platform/tariff-packages"
        start=datetime.now(ZoneInfo('Asia/Bishkek')).date()+timedelta(days=4)
        data={"hotel_id":HOTEL_A,"package_kind":"BUSINESS",
              "title":"QA Business bundle","period_start":start.isoformat(),
              "skus":["AI_ASSISTANT"],"discount_pct":"10.00",
              "trial_days":14}
        self.assertEqual(self.post(path,data,"owner-a").status_code,403)
        self.assertEqual(self.post(path,data,mfa=False).status_code,403)
        for forbidden in [{"paid":True},{"state":"ACTIVE"},{"enforcement":"ENFORCE"}]:
            self.assertEqual(self.post(path,{**data,**forbidden}).status_code,422)
        first=self.post(path,data)
        self.assertEqual(first.status_code,201,first.text)
        row=first.json()
        self.assertEqual(row["state"],"DRAFT")
        self.assertEqual(row["enforcement"],"OFF")
        self.assertFalse(row["subscription_activated"])
        self.assertFalse(row["payments_enabled"])
        self.assertEqual(row["version"],1)
        self.assertEqual(row["list_monthly_total"],"4000.00")
        self.assertEqual(row["proposed_monthly_total"],"3600.00")
        self.assertEqual(row["trial_days"],14)
        again=self.post(path,{**data,"title":"QA Business v2","trial_days":7})
        self.assertEqual(again.status_code,201,again.text)
        self.assertEqual(again.json()["version"],2)
        self.assertEqual(self.get(path+"?hotel_id="+HOTEL_A).status_code,200)
        self.assertEqual(len(self.get(path+"?hotel_id="+HOTEL_A).json()),2)
        self.assertEqual(self.get(path+"?hotel_id="+HOTEL_B).json(),[])
        self.assertEqual(self.get(path+"?hotel_id="+HOTEL_A,who="owner-a").status_code,403)
        custom=self.post(path,{**data,"package_kind":"CUSTOM","title":"QA custom",
                          "discount_pct":"0","custom_monthly_price":"2999.00"})
        self.assertEqual(custom.status_code,201,custom.text)
        self.assertEqual(custom.json()["proposed_monthly_total"],"2999.00")
        self.assertEqual(self.post(path,{**data,"package_kind":"CUSTOM","custom_monthly_price":"2999.00"}).status_code,422)
        async def verify_unchanged():
            con=await asyncpg.connect(os.environ["FLEX_TEST_DB_OWNER_URL"])
            try:
                self.assertEqual(await con.fetchval("SELECT count(*) FROM flex_tariff_package_versions WHERE hotel_id=$1",uuid.UUID(HOTEL_A)),3)
                self.assertEqual(await con.fetchval("SELECT count(*) FROM flex_confirmed_payments"),0)
                self.assertEqual(await con.fetchval("SELECT count(*) FROM flex_payment_intents"),0)
                self.assertEqual(await con.fetchval("SELECT count(*) FROM flex_subscription_configuration_drafts"),1)
                self.assertEqual(await con.fetchval("SELECT count(*) FROM flex_subscriptions"),2)
            finally:await con.close()
        asyncio.run(verify_unchanged())


    def test_05_reuse_template_across_hotels_with_own_terms(self):
        templates = "/v1/platform/tariff-templates"
        packages = "/v1/platform/tariff-packages"
        start = datetime.now(ZoneInfo("Asia/Bishkek")).date() + timedelta(days=8)
        proposal = {"hotel_id": HOTEL_A, "package_kind": "BASE", "title": "Hotel A only",
                    "skus": ["AI_ASSISTANT"], "period_start": start.isoformat(),
                    "discount_pct": "25", "trial_days": 30}
        source = self.post(packages, proposal)
        self.assertEqual(source.status_code, 201, source.text)
        publish = {"package_id": source.json()["id"]}
        self.assertEqual(self.post(templates, publish, "owner-a").status_code, 403)
        self.assertEqual(self.get(templates, mfa=False).status_code, 403)
        first = self.post(templates, publish)
        self.assertEqual(first.status_code, 201, first.text)
        expected = {"id": publish["package_id"], "revision": 1,
                    "package_kind": "BASE", "skus": ["AI_ASSISTANT"]}
        self.assertEqual(first.json(), expected)
        self.assertEqual(self.post(templates, publish).json(), expected)
        self.assertEqual(self.get(templates).json(), [expected])
        reuse = {**proposal, "hotel_id": HOTEL_B, "title": "Hotel B",
                 "discount_pct": "0", "trial_days": 0, "source_template_id": expected["id"]}
        self.assertEqual(self.post(packages, {**reuse, "skus": ["EXTRA_QA_CI"]}).status_code, 422)
        self.assertEqual(self.post(packages, {**reuse, "package_kind": "PREMIUM"}).status_code, 422)
        second = self.post(packages, reuse)
        self.assertEqual(second.status_code, 201, second.text)
        self.assertEqual(second.json()["proposed_monthly_total"], "15000.00")
        self.assertEqual(second.json()["source_template_id"], expected["id"])
        self.assertEqual(second.json()["state"], "DRAFT")
        self.assertFalse(second.json()["subscription_activated"])
        self.assertFalse(second.json()["payments_enabled"])
        new_template = self.post(templates, {"package_id": second.json()["id"]})
        self.assertEqual(new_template.json()["revision"], 2)
        self.assertEqual(self.get(templates).json(), [new_template.json()])
        saved = self.get(packages + "?hotel_id=" + HOTEL_B).json()[0]
        self.assertEqual(saved["source_template_id"], expected["id"])
        individual = self.post(packages, {**proposal, "package_kind": "CUSTOM"})
        self.assertEqual(self.post(templates, {"package_id": individual.json()["id"]}).status_code, 422)



    def test_06_commercial_price_revision(self):
        path="/v1/platform/commercial-policy"
        payload={"expected_version":1,"price_kind":"PACKAGE","code":"BASE","monthly_price":"5500.00"}
        self.assertEqual(self.post(path,payload,"owner-a").status_code,403)
        self.assertEqual(self.post(path,{**payload,"monthly_price":"0"}).status_code,422)
        self.assertEqual(self.post(path,{**payload,"code":"UNKNOWN"}).status_code,422)
        first=self.post(path,payload)
        self.assertEqual(first.status_code,201,first.text)
        self.assertEqual(first.json()["version"],2)
        self.assertEqual(first.json()["policy"]["monthly_packages"]["CUSTOM"]["minimum"],"5500.00")
        self.assertFalse(first.json()["payment_collected"])
        self.assertEqual(self.post(path,payload).status_code,409)
        second=self.post(path,{"expected_version":2,"price_kind":"MODULE","code":"QR_ZONE","monthly_price":"2200"})
        self.assertEqual(second.status_code,201,second.text)
        self.assertEqual(self.get(path).json()["policy"]["module_monthly_prices"]["QR_ZONE"],"2200.00")
        async def verify_history():
            con=await asyncpg.connect(os.environ["FLEX_TEST_DB_OWNER_URL"])
            try:
                self.assertEqual(await con.fetchval("SELECT policy#>>'{monthly_packages,BASE,price}' FROM flex_commercial_policy_versions WHERE version=1"),"5000")
                self.assertEqual(await con.fetchval("SELECT count(*) FROM flex_commercial_policy_versions"),3)
                self.assertEqual(await con.fetchval("SELECT count(*) FROM flex_confirmed_payments"),0)
            finally:await con.close()
        asyncio.run(verify_history())



    def test_07_approved_hotel_package_prices(self):
        path="/v1/platform/tariff-packages"
        base={"hotel_id":HOTEL_A,"package_kind":"BUSINESS","title":"Approved business",
              "period_start":(datetime.now(ZoneInfo("Asia/Bishkek")).date()+timedelta(days=4)).isoformat(),
              "skus":["QR_ZONE","MULTI_HOTEL"],"commercial_policy_version":3,
              "discount_pct":"10","trial_days":5,"custom_monthly_price":None}
        self.assertEqual(self.post(path,base,"owner-a").status_code,403)
        self.assertEqual(self.post(path,{**base,"commercial_policy_version":1}).status_code,409)
        self.assertEqual(self.post(path,{**base,"skus":["UNKNOWN_MODULE"]}).status_code,422)
        made=self.post(path,base)
        self.assertEqual(made.status_code,201,made.text)
        row=made.json()
        self.assertEqual(Decimal(row["list_monthly_total"]),Decimal("20000"))
        self.assertEqual(Decimal(row["proposed_monthly_total"]),Decimal("18000"))
        self.assertFalse(row["subscription_activated"])
        items={i["sku"]:i for i in row["items"]}
        self.assertEqual(Decimal(items["QR_ZONE"]["monthly_price"]),Decimal(0))
        self.assertEqual(items["BASE_PMS"]["commercial_policy_version"],3)
        other=self.post(path,{**base,"hotel_id":HOTEL_B,"package_kind":"BASE","skus":[],"discount_pct":"0"})
        self.assertEqual(other.status_code,201,other.text)
        self.assertEqual(Decimal(other.json()["proposed_monthly_total"]),Decimal("5500"))
        self.assertEqual(self.post(path,{**base,"package_kind":"CUSTOM","discount_pct":"0",
            "custom_monthly_price":"4999"}).status_code,422)
        history=self.get(path+"?hotel_id="+HOTEL_A).json()
        self.assertEqual(history[0]["id"],row["id"])
        self.assertEqual(Decimal(history[0]["proposed_monthly_total"]),Decimal("18000"))



    def test_08_commercial_term_and_implementation_snapshot(self):
        path="/v1/platform/tariff-packages"
        start=(datetime.now(ZoneInfo("Asia/Bishkek")).date()+timedelta(days=4)).isoformat()
        data={"hotel_id":HOTEL_B,"package_kind":"BUSINESS","title":"Business annual",
              "period_start":start,"skus":[],"commercial_policy_version":3,
              "discount_pct":"0","trial_days":5,"custom_monthly_price":None,
              "term_months":12,"standard_term_discount":True,"include_implementation":True}
        made=self.post(path,data)
        self.assertEqual(made.status_code,201,made.text)
        row=made.json()
        self.assertEqual(row["term_months"],12)
        self.assertEqual(Decimal(row["discount_pct"]),Decimal("30"))
        self.assertEqual(Decimal(row["subscription_term_total"]),Decimal("126000"))
        self.assertEqual(Decimal(row["implementation_total"]),Decimal("25000"))
        self.assertEqual(row["period_start"],start)
        self.assertFalse(row["subscription_activated"])
        saved=next(x for x in self.get(path+"?hotel_id="+HOTEL_B).json() if x["id"]==row["id"])
        self.assertEqual(saved["subscription_term_total"],row["subscription_term_total"])
        self.assertEqual(saved["commercial_policy_version"],3)
        self.assertEqual(self.post(path,{**data,"term_months":2}).status_code,422)
        self.assertEqual(self.post(path,{**data,"discount_pct":"10"}).status_code,422)



    def test_10_launch_offer_atomic_and_admin_only(self):
        from concurrent.futures import ThreadPoolExecutor
        path="/v1/platform/tariff-packages"
        data={"hotel_id":HOTEL_A,"package_kind":"BUSINESS","title":"Launch offer",
              "period_start":datetime.now(ZoneInfo("Asia/Bishkek")).date().isoformat(),
              "skus":[],"commercial_policy_version":3,"discount_pct":"0",
              "trial_days":5,"custom_monthly_price":None,"term_months":12,
              "standard_term_discount":False,"include_implementation":True,"launch_offer":True}
        self.assertEqual(self.post(path,data,"owner-a").status_code,403)
        for bad in ({"term_months":6},{"standard_term_discount":True},{"discount_pct":"10"},
                    {"package_kind":"CUSTOM"},{"skus":["MULTI_HOTEL"]}):
            self.assertEqual(self.post(path,{**data,**bad}).status_code,422)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:self.post(path,data),range(2)))
        self.assertEqual(sorted(x.status_code for x in results),[201,409])
        row=next(x.json() for x in results if x.status_code==201)
        self.assertEqual(Decimal(row["subscription_term_total"]),Decimal("108000"))
        self.assertEqual(Decimal(row["implementation_total"]),Decimal("25000"))
        self.assertTrue(row["launch_offer_reserved"])
        self.assertFalse(row["payments_enabled"])
        self.assertFalse(row["subscription_activated"])
        self.assertEqual(self.post(path,data).status_code,409)
        premium=self.post(path,{**data,"hotel_id":HOTEL_B,"package_kind":"PREMIUM"})
        self.assertEqual(premium.status_code,201,premium.text)
        self.assertEqual(Decimal(premium.json()["subscription_term_total"]),Decimal("180000"))
        self.assertNotEqual(row["launch_offer_slot"],premium.json()["launch_offer_slot"])
        async def verify():
            con=await asyncpg.connect(os.environ["FLEX_TEST_DB_OWNER_URL"])
            try:
                self.assertEqual(await con.fetchval("SELECT count(*) FROM flex_launch_offer_reservations"),3)
                self.assertEqual(await con.fetchval("SELECT count(*) FROM flex_confirmed_payments"),0)
            finally:await con.close()
        asyncio.run(verify())

    def test_11_launch_capacity_and_base_price(self):
        from concurrent.futures import ThreadPoolExecutor
        async def seed():
            con=await asyncpg.connect(os.environ["FLEX_TEST_DB_OWNER_URL"])
            try:
                self.assertEqual(await con.fetchval("SELECT current_database()"),"flex_ci")
                ids=[uuid.uuid4() for _ in range(48)]
                await con.executemany("INSERT INTO flex_hotels(id,display_name) VALUES($1,$2)",
                                      [(i,"Synthetic launch capacity") for i in ids])
                return [str(i) for i in ids]
            finally: await con.close()
        ids=asyncio.run(seed())
        path="/v1/platform/tariff-packages"
        data={"package_kind":"BASE","title":"Launch capacity",
              "period_start":datetime.now(ZoneInfo("Asia/Bishkek")).date().isoformat(),
              "skus":[],"commercial_policy_version":3,"discount_pct":"0",
              "trial_days":5,"custom_monthly_price":None,"term_months":12,
              "standard_term_discount":False,"include_implementation":True,"launch_offer":True}
        with ThreadPoolExecutor(max_workers=6) as pool:
            results=list(pool.map(lambda i:self.post(path,{**data,"hotel_id":i}),ids))
        self.assertEqual(sorted(x.status_code for x in results),[201]*47+[409])
        accepted=[x.json() for x in results if x.status_code==201]
        self.assertEqual(len({x["launch_offer_slot"] for x in accepted}),47)
        for row in accepted:
            self.assertEqual(Decimal(row["subscription_term_total"]),Decimal("39600"))
            self.assertEqual(Decimal(row["implementation_total"]),Decimal("25000"))
        async def verify():
            con=await asyncpg.connect(os.environ["FLEX_TEST_DB_OWNER_URL"])
            try:
                self.assertEqual(await con.fetchval("SELECT count(*) FROM flex_launch_offer_reservations"),50)
                self.assertEqual(await con.fetchval("SELECT count(DISTINCT slot) FROM flex_launch_offer_reservations"),50)
                self.assertEqual(await con.fetchval("SELECT count(*) FROM flex_confirmed_payments"),0)
            finally: await con.close()
        asyncio.run(verify())
        status=self.get("/v1/platform/launch-offer")
        self.assertEqual(status.status_code,200,status.text)
        summary=status.json()
        self.assertEqual((summary["capacity"],summary["reserved"],summary["available"]),(50,50,0))
        self.assertEqual({x["slot"] for x in summary["reservations"]},set(range(1,51)))
        self.assertEqual(len({x["hotel_id"] for x in summary["reservations"]}),50)
        self.assertFalse(summary["payments_enabled"])

    def test_09_installation_trial_is_one_time_and_admin_only(self):
        path="/v1/platform/installation-trial"
        data={"hotel_id":HOTEL_A}
        self.assertEqual(self.post(path,data,"owner-a").status_code,403)
        self.assertEqual(self.get(path+"?hotel_id="+HOTEL_A).json(),None)
        first=self.post(path,data)
        self.assertEqual(first.status_code,201,first.text)
        row=first.json()
        self.assertEqual(date.fromisoformat(row["trial_end_exclusive"])-date.fromisoformat(row["trial_start"]),timedelta(days=5))
        self.assertEqual(self.post(path,data).json(),row)
        self.assertFalse(row["entitlement_changed"])
        self.assertEqual(self.get(path+"?hotel_id="+HOTEL_B).json(),None)
        self.assertEqual(self.get(path+"?hotel_id="+HOTEL_A,who="owner-b").status_code,403)


    def test_12_customer_profile_contract_and_preview(self):
        profile="/v1/platform/customer-profile"
        agreement="/v1/platform/agreement-drafts"
        preview="/v1/platform/invoice-previews"
        data={"hotel_id":HOTEL_A,"expected_version":0,"contact_name":"Synthetic contact",
              "contact_email":"qa@example.test","contact_phone":"+996000000000","responsible_name":"Synthetic responsible"}
        self.assertEqual(self.get(profile+"?hotel_id="+HOTEL_A,who="owner-a").status_code,403)
        self.assertEqual(self.post(profile,data,"owner-a").status_code,403)
        self.assertEqual(self.post(profile,{**data,"contact_email":"bad"}).status_code,422)
        made=self.post(profile,data)
        self.assertEqual(made.status_code,201,made.text)
        self.assertEqual(made.json()["version"],1)
        self.assertEqual(self.post(profile,data).status_code,409)
        updated=self.post(profile,{**data,"expected_version":1,"contact_name":"Updated synthetic"})
        self.assertEqual(updated.status_code,201,updated.text)
        history=self.get(profile+"?hotel_id="+HOTEL_A).json()
        self.assertEqual([x["version"] for x in history["history"]],[2,1])
        self.assertEqual(history["current"]["contact_name"],"Updated synthetic")
        self.assertIsNone(self.get(profile+"?hotel_id="+HOTEL_B).json()["current"])
        offers=self.get("/v1/platform/tariff-packages?hotel_id="+HOTEL_A).json()
        offer=next(x for x in offers if x["commercial_policy_version"]==3 and Decimal(str(x["discount_pct"]))==40)
        a={"hotel_id":HOTEL_A,"offer_id":offer["id"]}
        self.assertEqual(self.post(agreement,a,"owner-a").status_code,403)
        self.assertEqual(self.post(agreement,{**a,"hotel_id":HOTEL_B}).status_code,404)
        self.assertEqual(self.post(agreement,{**a,"state":"SIGNED"}).status_code,422)
        made=self.post(agreement,a)
        self.assertEqual(made.status_code,201,made.text)
        contract=made.json()
        self.assertEqual(contract["state"],"DRAFT")
        self.assertIsNone(contract["signed_at"])
        self.assertEqual(contract["terms"]["source_offer_id"],offer["id"])
        self.assertEqual(Decimal(contract["terms"]["subscription_term_total"]),Decimal("108000"))
        self.assertEqual(self.post(agreement,a).json()["id"],contract["id"])
        p={"hotel_id":HOTEL_A,"agreement_id":contract["id"]}
        self.assertEqual(self.post(preview,{**p,"hotel_id":HOTEL_B}).status_code,404)
        self.assertEqual(self.post(preview,{**p,"amount":1}).status_code,422)
        made=self.post(preview,p)
        self.assertEqual(made.status_code,201,made.text)
        document=made.json()
        self.assertEqual(document["status"],"NON_ISSUABLE")
        self.assertEqual(document["tax_status"],"NOT_CALCULATED")
        self.assertEqual(Decimal(str(document["amount_before_unresolved_taxes"])),Decimal("133000"))
        self.assertEqual(self.post(preview,p).json()["id"],document["id"])
        history=self.get(agreement+"?hotel_id="+HOTEL_A).json()
        self.assertTrue(any(x["id"]==contract["id"] for x in history["agreements"]))
        self.assertTrue(any(x["id"]==document["id"] for x in history["previews"]))
        async def verify():
            con=await asyncpg.connect(os.environ["FLEX_TEST_DB_OWNER_URL"])
            try:
                self.assertEqual(await con.fetchval("SELECT count(*) FROM flex_confirmed_payments"),0)
                self.assertEqual(await con.fetchval("SELECT count(*) FROM flex_subscriptions"),2)
                self.assertEqual(await con.fetchval("SELECT count(*) FROM flex_commercial_agreement_versions WHERE source_offer_id=$1",uuid.UUID(offer["id"])),1)
                self.assertEqual(await con.fetchval("SELECT count(*) FROM flex_non_issuable_invoice_previews WHERE agreement_version_id=$1",uuid.UUID(contract["id"])),1)
            finally: await con.close()
        asyncio.run(verify())


    def test_13_financial_reconciliation_excludes_drafts_and_denies_other_roles(self):
        path="/v1/platform/financial-reconciliation?hotel_id="
        self.assertEqual(self.get(path+HOTEL_A,who="owner-a").status_code,403)
        self.assertEqual(self.get(path+HOTEL_A,mfa=False).status_code,403)
        for hotel in (HOTEL_A,HOTEL_B):
            reply=self.get(path+hotel)
            self.assertEqual(reply.status_code,200,reply.text)
            data=reply.json()
            self.assertEqual(data["hotel_id"],hotel)
            self.assertEqual(data["invoice_count"],0)
            self.assertEqual(data["invoices"],[])
            self.assertTrue(data["reconciled"])
            self.assertFalse(data["payments_enabled"])
            self.assertFalse(data["payouts_enabled"])
            self.assertTrue(all(Decimal(v)==0 for v in data["totals"].values()))


    def test_14_internal_approval_and_subscription_plan(self):
        read="/v1/platform/subscription-plans?hotel_id="
        path="/v1/platform/agreement-internal-approvals"
        contract=self.get("/v1/platform/agreement-drafts?hotel_id="+HOTEL_A).json()["agreements"][0]
        body={"hotel_id":HOTEL_A,"agreement_id":contract["id"],
              "terms_digest":contract["terms_digest"],"acknowledged":True}
        self.assertEqual(self.get(read+HOTEL_A).json(),[])
        self.assertEqual(self.get(read+HOTEL_A,who="owner-a").status_code,403)
        self.assertEqual(self.post(path,body,"owner-a").status_code,403)
        self.assertEqual(self.post(path,body,mfa=False).status_code,403)
        self.assertEqual(self.post(path,{**body,"hotel_id":HOTEL_B}).status_code,404)
        self.assertEqual(self.post(path,{**body,"terms_digest":"0"*64}).status_code,409)
        self.assertEqual(self.post(path,{**body,"acknowledged":False}).status_code,422)
        self.assertEqual(self.post(path,{**body,"client_signed":True}).status_code,422)
        result=self.post(path,body)
        self.assertEqual(result.status_code,201,result.text)
        saved=result.json()
        self.assertEqual(saved["state"],"INTERNALLY_APPROVED")
        self.assertFalse(saved["client_signed"])
        self.assertFalse(saved["subscription_activated"])
        self.assertFalse(saved["payments_enabled"])
        self.assertEqual(self.post(path,body).json(),saved)
        plans=self.get(read+HOTEL_A).json()
        self.assertEqual(len(plans),1)
        plan=plans[0]
        self.assertEqual(plan["agreement_id"],contract["id"])
        self.assertEqual(plan["terms_digest"],contract["terms_digest"])
        self.assertEqual(plan["term_months"],12)
        self.assertEqual(Decimal(plan["subscription_term_total"]),Decimal("108000"))
        self.assertEqual(Decimal(plan["implementation_total"]),Decimal("25000"))
        self.assertEqual((plan["state"],plan["enforcement"]),("PLAN_ONLY","OFF"))
        self.assertFalse(plan["subscription_activated"])
        self.assertEqual(self.get(read+HOTEL_B).json(),[])
        history=self.get("/v1/platform/agreement-drafts?hotel_id="+HOTEL_A).json()
        self.assertEqual(len(history["approvals"]),1)
        self.assertEqual(history["agreements"][0]["state"],"DRAFT")
        async def verify():
            con=await asyncpg.connect(os.environ["FLEX_TEST_DB_OWNER_URL"])
            try:
                self.assertEqual(await con.fetchval("SELECT count(*) FROM flex_agreement_internal_approvals"),1)
                self.assertEqual(await con.fetchval("SELECT count(*) FROM flex_commercial_agreement_versions WHERE state='SIGNED'"),0)
                self.assertEqual(await con.fetchval("SELECT count(*) FROM flex_confirmed_payments"),0)
                self.assertEqual(await con.fetchval("SELECT count(*) FROM flex_subscriptions"),2)
            finally: await con.close()
        asyncio.run(verify())


    def test_15_customer_acceptance_only_exact_approved_own_terms(self):
        path="/v1/platform/customer-agreement-acceptances"
        history=self.get("/v1/platform/agreement-drafts?hotel_id="+HOTEL_A).json()
        contract=history["agreements"][0]
        data={"hotel_id":HOTEL_A,"agreement_id":contract["id"],
            "terms_digest":contract["terms_digest"],"acknowledged":True}
        self.assertEqual(self.get(path+"?hotel_id="+HOTEL_A,who="administrator").status_code,404)
        self.assertEqual(self.get(path+"?hotel_id="+HOTEL_A,who="owner-b").status_code,404)
        self.assertEqual(self.get(path+"?hotel_id="+HOTEL_A,who="owner-a",mfa=False).status_code,403)
        own=self.get(path+"?hotel_id="+HOTEL_A,who="owner-a")
        self.assertEqual(own.status_code,200,own.text)
        self.assertEqual(len(own.json()),1)
        self.assertEqual(own.json()[0]["state"],"AWAITING_CUSTOMER")
        self.assertEqual(own.json()[0]["terms"],contract["terms"])
        self.assertEqual(self.post(path,data,"administrator").status_code,404)
        self.assertEqual(self.post(path,data,"owner-b").status_code,404)
        self.assertEqual(self.post(path,{**data,"hotel_id":HOTEL_B},"owner-b").status_code,404)
        self.assertEqual(self.post(path,data,"owner-a",mfa=False).status_code,403)
        self.assertEqual(self.post(path,{**data,"terms_digest":"0"*64},"owner-a").status_code,409)
        self.assertEqual(self.post(path,{**data,"acknowledged":False},"owner-a").status_code,422)
        result=self.post(path,data,"owner-a")
        self.assertEqual(result.status_code,201,result.text)
        evidence=result.json()
        self.assertEqual(evidence["state"],"CUSTOMER_ACCEPTED")
        self.assertFalse(evidence["client_signed"])
        self.assertFalse(evidence["subscription_activated"])
        self.assertFalse(evidence["payments_enabled"])
        self.assertEqual(self.post(path,data,"owner-a").json(),evidence)
        self.assertEqual(self.get(path+"?hotel_id="+HOTEL_B,who="owner-b").json(),[])
        history=self.get("/v1/platform/agreement-drafts?hotel_id="+HOTEL_A).json()
        self.assertEqual(len(history["acceptances"]),1)
        self.assertEqual(history["acceptances"][0]["accepted_by"],"owner-a")
        async def verify():
            con=await asyncpg.connect(os.environ["FLEX_TEST_DB_OWNER_URL"])
            try:
                self.assertEqual(await con.fetchval("SELECT count(*) FROM flex_customer_agreement_acceptances"),1)
                self.assertEqual(await con.fetchval("SELECT count(*) FROM flex_commercial_agreement_versions WHERE state='SIGNED'"),0)
                self.assertEqual(await con.fetchval("SELECT count(*) FROM flex_subscriptions"),2)
                self.assertEqual(await con.fetchval("SELECT count(*) FROM flex_confirmed_payments"),0)
            finally: await con.close()
        asyncio.run(verify())


    def test_16_synthetic_finance_replay_does_not_write_ledger(self):
        path="/v1/platform/finance-simulation"
        contract=self.get("/v1/platform/agreement-drafts?hotel_id="+HOTEL_A).json()["agreements"][0]
        data={"hotel_id":HOTEL_A,"agreement_id":contract["id"],"events":[
            {"kind":"PAYMENT","event_id":"p1","amount":"100000"},
            {"kind":"PAYMENT","event_id":"p2","amount":"40000"},
            {"kind":"REFUND","event_id":"r1","payment_id":"p2","amount":"10000"}]}
        self.assertEqual(self.post(path,data,"owner-a").status_code,403)
        self.assertEqual(self.post(path,{**data,"hotel_id":HOTEL_B}).status_code,404)
        response=self.post(path,data)
        self.assertEqual(response.status_code,201,response.text)
        r=response.json()
        self.assertEqual(r["mode"],"SYNTHETIC_ONLY")
        self.assertEqual(Decimal(r["amount_before_unresolved_taxes"]),Decimal("133000"))
        self.assertEqual(Decimal(r["net_simulated_cash"]),Decimal("130000"))
        self.assertEqual(Decimal(r["outstanding"]),Decimal("3000"))
        self.assertEqual(Decimal(r["credit"]),Decimal("0"))
        self.assertEqual(Decimal(r["discrepancy"]),Decimal("0"))
        self.assertFalse(r["persisted"])
        self.assertFalse(r["payments_enabled"])
        self.assertFalse(r["launch_offer_finalized"])
        self.assertEqual(self.post(path,data).json(),r)
        invalid={**data,"events":[{"kind":"REFUND","event_id":"r","payment_id":"missing","amount":"1"}]}
        self.assertEqual(self.post(path,invalid).status_code,422)
        async def verify():
            con=await asyncpg.connect(os.environ["FLEX_TEST_DB_OWNER_URL"])
            try:
                self.assertEqual(await con.fetchval("SELECT count(*) FROM flex_confirmed_payments"),0)
                self.assertEqual(await con.fetchval("SELECT count(*) FROM flex_payment_reversals"),0)
                self.assertEqual(await con.fetchval("SELECT count(*) FROM flex_subscriptions"),2)
            finally: await con.close()
        asyncio.run(verify())


if __name__=="__main__":
    unittest.main(verbosity=2)
