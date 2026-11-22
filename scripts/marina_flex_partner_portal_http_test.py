#!/usr/bin/env python3
"""JWT-signed agent/investor dashboards with two-hotel RLS, ephemeral DB only."""
from __future__ import annotations

import json
import os
import sys
import time
import unittest
import uuid
from pathlib import Path

import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from fastapi.testclient import TestClient

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"services"/"api"))
from app.flex_partner_portal import app


class ScopedCommercialParticipants(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.environ.get("FLEX_DATABASE_URL"):
            raise RuntimeError("Use disposable FLEX CI database only")
        cls.private=Ed25519PrivateKey.generate()
        public=cls.private.public_key().public_bytes(
            Encoding.PEM,PublicFormat.SubjectPublicKeyInfo
        ).decode()
        cls.saved={k:os.environ.get(k) for k in (
            "FLEX_AUTH_PUBLIC_KEYS_JSON","FLEX_AUTH_ISSUER","FLEX_AUTH_AUDIENCE"
        )}
        os.environ.update({
            "FLEX_AUTH_PUBLIC_KEYS_JSON":json.dumps({"qa-investor":public}),
            "FLEX_AUTH_ISSUER":"marina-flex-qa-income",
            "FLEX_AUTH_AUDIENCE":"marina-flex-qa-income",
        })
        cls.client_context=TestClient(app)
        cls.client=cls.client_context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client_context.__exit__(None,None,None)
        for k,v in cls.saved.items():
            if v is None: os.environ.pop(k,None)
            else: os.environ[k]=v

    @classmethod
    def token(cls,subject,mfa=False,role_claim=None):
        now=int(time.time())
        data={
            "sub":subject,"iss":"marina-flex-qa-income",
            "aud":"marina-flex-qa-income","iat":now,"nbf":now-1,
            "exp":now+300,"jti":str(uuid.uuid4()),"amr":["mfa"] if mfa else ["pwd"],
        }
        if role_claim: data["role"]=role_claim
        return jwt.encode(data,cls.private,algorithm="EdDSA",headers={"kid":"qa-investor"})

    def get(self,path,subject,mfa=False,role_claim=None):
        return self.client.get(path,headers={
            "Authorization":"Bearer "+self.token(subject,mfa=mfa,role_claim=role_claim)
        })

    def test_agent_a_b_are_completely_isolated(self):
        a=self.get("/v1/partner/me/earnings?period=day","sales-1")
        b=self.get("/v1/partner/me/earnings?period=day","sales-2")
        self.assertEqual(a.status_code,200,a.text)
        self.assertEqual(b.status_code,200,b.text)
        self.assertEqual(a.json()["role"],"SALES_AGENT")
        self.assertEqual(a.json()["net_accrued_kg"],"8.00")
        self.assertEqual(a.json()["reversed_kg"],"2.00")
        self.assertEqual(b.json()["net_accrued_kg"],"20.00")
        self.assertEqual(b.json()["reversed_kg"],"0.00")
        self.assertEqual(a.json()["data_provenance"],"QA_ONLY_NOT_BANK_RECONCILED")
        self.assertIsNone(a.json()["actual_paid_kg"])

    def test_investors_require_mfa_and_never_view_other_investor(self):
        no_mfa=self.get("/v1/partner/me/earnings","investor-1")
        self.assertEqual(no_mfa.status_code,403)
        a=self.get("/v1/partner/me/earnings?period=week","investor-1",mfa=True)
        b=self.get("/v1/partner/me/earnings?period=month","investor-2",mfa=True)
        self.assertEqual(a.status_code,200,a.text)
        self.assertEqual(b.status_code,200,b.text)
        self.assertEqual(a.json()["net_accrued_kg"],"24.00")
        self.assertEqual(b.json()["net_accrued_kg"],"50.00")
        self.assertEqual(a.json()["payout_status"],"NOT_IMPLEMENTED")
        self.assertIsNone(a.json()["actual_paid_kg"])

    def test_roles_from_token_ignored_and_hotel_owner_forbidden(self):
        injected=self.get(
            "/v1/partner/me/earnings?period=month",
            "sales-1",mfa=True,role_claim="SUPER_ADMIN"
        )
        self.assertEqual(injected.status_code,200,injected.text)
        self.assertEqual(injected.json()["role"],"SALES_AGENT")
        self.assertEqual(self.get("/v1/partner/me/earnings","owner-a").status_code,403)
        self.assertEqual(self.get("/v1/partner/me/earnings","administrator",mfa=True).status_code,403)
        self.assertEqual(self.client.get("/v1/partner/me/earnings").status_code,401)
        self.assertEqual(self.get("/v1/partner/me/earnings","unknown").status_code,403)

    def test_platform_admin_only_with_mfa(self):
        self.assertEqual(self.get("/v1/platform/partner-earnings-summary",
                                  "administrator").status_code,403)
        self.assertEqual(self.get("/v1/platform/partner-earnings-summary",
                                  "sales-1").status_code,403)
        self.assertEqual(self.get("/v1/platform/partner-earnings-summary",
                                  "investor-1",mfa=True).status_code,403)
        summary=self.get("/v1/platform/partner-earnings-summary?period=month",
                         "administrator",mfa=True)
        self.assertEqual(summary.status_code,200,summary.text)
        rows={r["role"]:r for r in summary.json()["groups"]}
        self.assertEqual(rows["SALES_AGENT"]["net_accrued_kg"],"28.00")
        self.assertEqual(rows["INVESTOR"]["net_accrued_kg"],"74.00")
        self.assertFalse(summary.json()["payouts_enabled"])

    def test_read_only_and_period_validation(self):
        self.assertEqual(self.get("/v1/partner/me/earnings?period=year",
                                  "sales-1").status_code,422)
        self.assertIn(self.client.post("/v1/partner/me/earnings",
            headers={"Authorization":"Bearer "+self.token("investor-1",mfa=True)},
            json={"amount":9999}).status_code,(404,405))
        self.assertEqual(self.client.get("/health").json()["payouts_enabled"],False)


if __name__=="__main__":
    unittest.main(verbosity=2)
